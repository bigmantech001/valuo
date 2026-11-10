"""Three-engine sum-of-the-parts (SOTP) valuation of NEAR with a seeded Monte Carlo.

Pure numpy, deterministic, no network. Consumes the collector outputs (``NearOnchainTruth``,
``IntentsForensics``, ``PeerComps``, optional ``ExecutionBenchmark``), the deterministic
``SupplyPhysics`` model and the labeled assumption registry, and returns a ``SotpValuation``
(docs/MODEL_DESIGN.md section 4.2).

Take-rate basis (read before porting to web/src/lib/quantClient.ts):
  * ``tau_pub_bps`` / ``tau_conf_bps`` are GROSS take-rates (fees / volume): the user-facing fee
    that is comparable to competitor friction and to the benchmark's competitive ceiling.
  * ``alpha_capture`` is the share of gross fees swept to NEAR revenue wallets (DefiLlama
    ``dailyRevenue / fees`` for near-intents, the live capture ratio).
  * Holder revenue = V x tau x alpha. The "net take" quoted elsewhere (5.6 bps class) is
    tau x alpha. This keeps the SOTP on the same basis as supply_physics' breakeven
    V* = (issuance - burns) x P / (tau_gross x alpha), and reproduces DefiLlama's 30d holder
    revenue at month 0.
  * The public take at t=0 is reconciled to live fees:
    tau_pub_0 = (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d x 1e4,
    so modelled month-0 fees equal measured fees whatever the confidential-take assumption.
  * Volume, fees and holders revenue come from intents_forensics' ONE aligned calendar window
    (``fees.take_rate_window``); the nearstats public/confidential split only supplies the share.

Issuance compounds exactly as supply_physics.trajectory does (S_t = S_{t-1} + S_{t-1} x i_t / 12), so
the SOTP's horizon float and the supply model's trajectories agree to floating point.

GBM convention (mean-matching, Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so
E[V_t] = V_0 (1+g)^t and the labeled ``public_volume_growth_yoy`` is the EXPECTED (mean) growth, which is
also the deterministic path. The MEDIAN simulated path is lower by exp(-sigma^2 t / 2), a large factor at
the measured monthly volume sigma; ``calibration`` reports both the mean and the median terminal volume
(``volume_terminal_mean_usd_day`` / ``volume_terminal_median_usd_day``) so the P50 FDV is read against
the right path. The same convention holds for the price GBM (zero drift => E[P_t] = P_0).

Fallbacks (each labeled source="assumption" in ``inputs`` and warned; the run never exits for them):
peer FDV/revenue median null -> peer FDV/fees median -> ``terminal_multiple_fallback``; price sigma
null -> ``price_sigma_annual_fallback``; volume sigma null (DefiLlama dexs chart outage) ->
``volume_sigma_monthly_fallback``; nearstats public/confidential split null -> confidential volume 0
(Engine 2 reported as not measured). Volume itself missing from every source is still fatal.

Everything stochastic is drawn once, up front, from ``numpy.random.default_rng(seed)`` in a fixed
order (public-volume shocks, confidential-volume shocks, price shocks), so results are
bit-reproducible for a given snapshot of inputs.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from valuo import assumptions as A
from valuo import config
from valuo.schemas import (
    PERCENTILE_KEYS,
    Assumption,
    EngineValue,
    ExecutionBenchmark,
    IntentsForensics,
    NearOnchainTruth,
    PeerComps,
    SotpValuation,
    SupplyPhysics,
)

__all__ = [
    "DAYS_PER_MONTH",
    "HARD_FLOOR_BPS",
    "HEATMAP_VOLUMES_USD",
    "HEATMAP_NET_TAKE_BPS",
    "REGIME_STATUS_QUO",
    "REGIME_GLIDEPATH",
    "GBM_CONVENTION",
    "percentiles",
    "compound_issuance",
    "deterministic_sotp",
    "build_inputs",
    "simulate_paths",
    "mc_fdv_p50",
    "run_sotp",
]

# 365.25 / 12. MODEL_DESIGN writes "30.4"; the exact value is used so monthly x 12 == annual.
DAYS_PER_MONTH: float = 365.25 / 12.0
# MODEL_DESIGN 4.2: tau_floor = max(hard floor, min(live take, cross-VM headroom)). The hard floor is the
# registry assumption ``public_take_floor_bps`` (default 0.5 bps); this constant mirrors its default.
HARD_FLOOR_BPS: float = A.get("public_take_floor_bps").value
HEATMAP_VOLUMES_USD: tuple[float, ...] = (1e8, 2.5e8, 5e8, 1e9, 1.5e9)
HEATMAP_NET_TAKE_BPS: tuple[float, ...] = (2.0, 6.0, 10.0, 14.0, 18.0)
REGIME_STATUS_QUO = "status_quo"
REGIME_GLIDEPATH = "svrn_glidepath"
_PCT_VALUES: tuple[float, ...] = (10.0, 25.0, 50.0, 75.0, 90.0)
GBM_CONVENTION = (
    "mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; "
    "public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path "
    "is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM "
    "uses the same convention (zero drift => E[P_t] = P_0)"
)


# ============================================================================ small helpers
def percentiles(arr: Sequence[float] | np.ndarray) -> dict[str, float]:
    """``{"p10","p25","p50","p75","p90"}`` of ``arr`` (numpy linear interpolation), as Python floats."""
    a = np.asarray(arr, dtype=float).ravel()
    if a.size == 0:
        raise ValueError("percentiles: empty array")
    vals = np.percentile(a, _PCT_VALUES)
    return {k: float(v) for k, v in zip(PERCENTILE_KEYS, vals, strict=True)}


def _num(d: Mapping[str, Any] | None, *keys: str) -> float | None:
    """First finite numeric value among ``keys`` in ``d`` (None when absent/null/non-numeric)."""
    if not d:
        return None
    for k in keys:
        v = d.get(k)
        if isinstance(v, bool) or v is None:
            continue
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(f):
            return f
    return None


def _point(key: str, value: float, unit: str, source: str, justification: str) -> Assumption:
    """A measured/derived input recorded in the same shape as a slider assumption (range = point)."""
    v = float(value)
    return Assumption(key=key, value=v, unit=unit, low=v, high=v, source=source, justification=justification)  # type: ignore[arg-type]


def _first_crossover(net_float: np.ndarray) -> np.ndarray:
    """Per path: first 1-based month with net float change <= 0, or 0 when the path never crosses."""
    mask = net_float <= 0.0
    crossed = mask.any(axis=1)
    return np.where(crossed, mask.argmax(axis=1) + 1, 0).astype(int)


def _crossover_summary(first: np.ndarray, horizon: int) -> dict[str, Any]:
    """Distribution of run-rate crossover months over paths (``first`` = 0 means never)."""
    crossed = first > 0
    p = float(crossed.mean()) if first.size else 0.0
    months = first[crossed]
    pct = percentiles(months) if months.size else {k: None for k in PERCENTILE_KEYS}
    return {
        f"p_crossover_within_{horizon}m": p,
        "p10_month": pct["p10"],
        "p50_month": pct["p50"],
        "p90_month": pct["p90"],
        "n_paths_crossed": int(crossed.sum()),
    }


# ============================================================================ core engine math
def _value_paths(
    *,
    v_pub: np.ndarray,
    v_conf: np.ndarray,
    v_pub0: float,
    tau_pub_bps: np.ndarray,
    tau_conf_bps: np.ndarray,
    price: np.ndarray,
    alpha: float,
    discount_rate: float,
    terminal_multiple: float,
    conf_haircut: float,
    gas_burn_near_day0: float,
    state_lock_near_day0: float,
    issuance_near_month: np.ndarray,
    total_supply: float,
) -> dict[str, np.ndarray]:
    """Vectorized engine math shared by ``deterministic_sotp`` (1 path) and the Monte Carlo (n paths).

    Shapes: ``v_pub``, ``v_conf``, ``price`` are (n, H); ``tau_*`` are (H,) or (n, H);
    ``issuance_near_month`` is (H,). Formulas are documented in ``deterministic_sotp``.
    """
    n, horizon = v_pub.shape
    t = np.arange(1, horizon + 1, dtype=float)
    df = (1.0 + discount_rate) ** (-t / 12.0)
    # Activity index: L1 gas burn and state-lock growth scale with public volume (MODEL_DESIGN 4.2
    # "grown with V_pub"). With zero starting volume the sinks are held at their measured level.
    activity = v_pub / v_pub0 if v_pub0 > 0 else np.ones_like(v_pub)

    rev_pub = v_pub * (tau_pub_bps / 1e4) * DAYS_PER_MONTH * alpha
    rev_conf = v_conf * (tau_conf_bps / 1e4) * DAYS_PER_MONTH * alpha
    gas_burn_near = gas_burn_near_day0 * DAYS_PER_MONTH * activity
    gas_burn_usd = gas_burn_near * price
    state_lock_near = state_lock_near_day0 * DAYS_PER_MONTH * activity
    buyback_near = (rev_pub + rev_conf) / price
    net_float = issuance_near_month[None, :] - buyback_near - gas_burn_near - state_lock_near

    k = min(12, horizon)
    annualizer = 12.0 / k
    tv_pub = rev_pub[:, -k:].sum(axis=1) * annualizer * terminal_multiple
    tv_conf = rev_conf[:, -k:].sum(axis=1) * annualizer * terminal_multiple * conf_haircut
    tv_gas = gas_burn_usd[:, -k:].sum(axis=1) * annualizer * terminal_multiple

    pv_pub = (rev_pub * df).sum(axis=1)
    pv_conf = (rev_conf * df).sum(axis=1)
    pv_gas = (gas_burn_usd * df).sum(axis=1)
    pv_lock = (state_lock_near * price * df).sum(axis=1)

    e1 = pv_pub + tv_pub * df[-1]
    e2 = pv_conf + tv_conf * df[-1]
    e3 = pv_gas + tv_gas * df[-1] + pv_lock
    fdv = e1 + e2 + e3

    # Running mark: the FDV a peer-multiple investor would pay at month t for the month-t run-rate.
    running_fdv = terminal_multiple * 12.0 * (rev_pub + conf_haircut * rev_conf + gas_burn_usd)
    cum_rev = np.cumsum(rev_pub + rev_conf, axis=1)
    return {
        "rev_pub": rev_pub, "rev_conf": rev_conf, "gas_burn_near": gas_burn_near, "gas_burn_usd": gas_burn_usd,
        "state_lock_near": state_lock_near, "buyback_near": buyback_near, "net_float": net_float, "df": df,
        "pv_pub": pv_pub, "tv_pub": tv_pub, "pv_conf": pv_conf, "tv_conf": tv_conf,
        "pv_gas": pv_gas, "tv_gas": tv_gas, "pv_lock": pv_lock,
        "e1": e1, "e2": e2, "e3": e3, "fdv": fdv, "running_fdv": running_fdv, "cum_rev": cum_rev,
        "supply_h": total_supply + net_float.sum(axis=1), "first_crossover": _first_crossover(net_float),
    }


def _tau_path(tau0: float, floor: float, lam: float, horizon: int) -> np.ndarray:
    """tau_t = floor + (tau_0 - floor) x (1 - lambda)^t, t = 1..H (geometric reversion to the floor)."""
    t = np.arange(1, horizon + 1, dtype=float)
    return floor + (tau0 - floor) * (1.0 - lam) ** t


_MISSING: Any = object()


def _in(inputs: Mapping[str, Any], *keys: str, default: Any = _MISSING) -> Any:
    """First non-null value among ``keys`` (spec name first, then bear_case.py's canonical aliases)."""
    for k in keys:
        v = inputs.get(k)
        if v is not None:
            return v
    if default is not _MISSING:
        return default
    raise KeyError(f"deterministic_sotp: missing input {keys[0]!r} (aliases {keys[1:]})")


def _issuance_path(inputs: Mapping[str, Any], horizon: int) -> np.ndarray:
    """Effective annual inflation per month (length H).

    ``issuance_rate_path`` (list, or a scalar meaning a flat regime) is used unless
    ``svrn_target_inflation`` is non-null, in which case the glidepath is rebuilt exactly as
    supply_physics does, 0-based: i_m = i0 + (target - i0) x min(m - 1, G) / G for m = 1..H with
    i0 = ``max_inflation_rate`` and G = ``svrn_glidepath_months``, times ``issuance_scale`` (measured /
    nominal issuance, default 1). This lets bear_case.py force the status quo by setting the target
    to the live rate without knowing the path layout.
    """
    target = inputs.get("svrn_target_inflation")
    if target is not None:
        i0 = float(_in(inputs, "max_inflation_rate"))
        g = max(1.0, float(_in(inputs, "svrn_glidepath_months")))
        scale = float(inputs.get("issuance_scale") or 1.0)
        t = np.arange(1, horizon + 1, dtype=float)
        return (i0 + (float(target) - i0) * np.minimum(t - 1.0, g) / g) * scale
    path = np.asarray(_in(inputs, "issuance_rate_path"), dtype=float)
    if path.ndim == 0:
        path = np.full(horizon, float(path))
    if path.shape != (horizon,):
        raise ValueError(f"issuance_rate_path must have length {horizon}, got {path.shape}")
    return path


def compound_issuance(annual_rates: np.ndarray, total_supply: float) -> np.ndarray:
    """Monthly NEAR issued when supply compounds: iss_t = S_{t-1} x i_t / 12, S_t = S_{t-1} + iss_t.

    Identical to supply_physics.trajectory (growth factor r_t = 1 + i_t x D / 365.25 with D = 365.25 / 12),
    so the two models' cumulative issuance and horizon float agree. ``annual_rates`` are the effective
    (realization-scaled) annual rates per month.
    """
    rates = np.asarray(annual_rates, dtype=float)
    r = 1.0 + rates / 12.0
    supply_start = float(total_supply) * np.concatenate(([1.0], np.cumprod(r)[:-1]))
    return supply_start * (r - 1.0)


def deterministic_sotp(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Deterministic three-engine SOTP at fixed inputs (no randomness). Port this verbatim to TS.

    Required ``inputs`` keys
      v_pub_usd_day, v_conf_usd_day       starting daily public / confidential volume (USD/day)
      tau_pub_bps, tau_conf_bps           starting GROSS take-rates (bps of volume)
      alpha_capture                       share of gross fees reaching holders (0..1)
      discount_rate                       annual, e.g. 0.25
      terminal_multiple                   FDV / annual holder revenue multiple (already clipped)
      conf_haircut                        multiplier on Engine 2's terminal multiple (0..1)
      gas_burn_usd_day                    L1 gas burned at t=0, USD/day (= NEAR/day x price)
      state_lock_near_day                 new state-locked NEAR per day at t=0
      price_usd                           NEAR spot price
      total_supply                        NEAR total supply at t=0
      issuance_rate_path                  H annual inflation rates (effective: already scaled so
                                          that month-1 issuance equals the measured daily issuance)
      growth_monthly_pub, growth_monthly_conf   deterministic monthly volume growth rates
      lambda_pub, lambda_conf             monthly take-rate compression speeds (0..1)
      tau_floor_bps                       competitive floor both takes revert to
      horizon_months                      H (36)
    Optional: price_drift_annual (default 0.0); supply_at_horizon (override for the implied-price
    denominator; default = internal float at H); svrn_target_inflation (non-null -> rebuild the
    issuance path from max_inflation_rate, svrn_glidepath_months and issuance_scale, see
    ``_issuance_path``; bear_case.py uses this for governance_stalemate). bear_case.py's canonical
    names are accepted as fallbacks when the spec key is absent: v_pub_daily_usd, v_conf_daily_usd,
    fee_compression_lambda_monthly (-> lambda_pub).

    Month index t = 1..H, D = DAYS_PER_MONTH = 365.25/12, df_t = (1 + r)^(-t/12).
      V_pub_t   = v_pub x (1 + g_pub)^t          (= E[V_pub_t] of the mean-matching GBM in simulate_paths)
      V_conf_t  = v_conf x (1 + g_conf)^t
      tau_pub_t = floor + (tau_pub - floor) x (1 - lambda_pub)^t
      tau_conf_t= floor + (tau_conf - floor) x (1 - lambda_conf)^t
      P_t       = price x (1 + d)^(t/12)
      a_t       = V_pub_t / v_pub                      (activity index; 1 if v_pub == 0)
      rev_pub_t = V_pub_t x tau_pub_t / 1e4 x D x alpha           (USD, holder revenue)
      rev_conf_t= V_conf_t x tau_conf_t / 1e4 x D x alpha
      gas_near_t= gas_burn_usd_day / price x D x a_t             (NEAR burned)
      gas_usd_t = gas_near_t x P_t
      lock_t    = state_lock_near_day x D x a_t                   (NEAR newly state-locked)
      buyback_t = (rev_pub_t + rev_conf_t) / P_t                  (NEAR bought back)
      iss_t     = S_{t-1} x i_t / 12,  S_t = S_{t-1} + iss_t      (NEAR issued, compounding as supply_physics)
      dF_t      = iss_t - buyback_t - gas_near_t - lock_t         (net float change, NEAR)
      k = min(12, H); yr3(x) = sum(x_{H-k+1..H}) x 12 / k          (year-3 annualized run-rate)
      E1 = sum_t rev_pub_t df_t  + yr3(rev_pub)  x M x df_H
      E2 = sum_t rev_conf_t df_t + yr3(rev_conf) x M x h x df_H
      E3 = sum_t gas_usd_t df_t  + yr3(gas_usd)  x M x df_H + sum_t lock_t x P_t x df_t
      fdv_total = E1 + E2 + E3;  fdv_ex_monetary = E1 + E2
      S_H = total_supply + sum_t dF_t;  implied_price = fdv_total / (supply_at_horizon or S_H)
      crossover_month = min{t : dF_t <= 0} or None; net_deflation = crossover_month is not None
      running_fdv_t = M x 12 x (rev_pub_t + h x rev_conf_t + gas_usd_t)
    Engine 3's state-lock term is a demand-flow proxy (forced structural demand), not a cash flow.
    """
    horizon = int(inputs["horizon_months"])
    if horizon < 1:
        raise ValueError("horizon_months must be >= 1")
    path = _issuance_path(inputs, horizon)
    v_pub0 = float(_in(inputs, "v_pub_usd_day", "v_pub_daily_usd"))
    v_conf0 = float(_in(inputs, "v_conf_usd_day", "v_conf_daily_usd"))
    price0 = float(inputs["price_usd"])
    if price0 <= 0:
        raise ValueError("price_usd must be > 0")
    total_supply = float(inputs["total_supply"])
    t = np.arange(1, horizon + 1, dtype=float)

    v_pub = (v_pub0 * (1.0 + float(inputs["growth_monthly_pub"])) ** t)[None, :]
    v_conf = (v_conf0 * (1.0 + float(inputs["growth_monthly_conf"])) ** t)[None, :]
    price = (price0 * (1.0 + float(inputs.get("price_drift_annual") or 0.0)) ** (t / 12.0))[None, :]
    floor = float(inputs["tau_floor_bps"])
    lambda_pub = float(_in(inputs, "lambda_pub", "fee_compression_lambda_monthly"))
    tau_pub = _tau_path(float(inputs["tau_pub_bps"]), floor, lambda_pub, horizon)
    tau_conf = _tau_path(float(inputs["tau_conf_bps"]), floor, float(inputs["lambda_conf"]), horizon)

    issuance = compound_issuance(path, total_supply)
    out = _value_paths(
        v_pub=v_pub, v_conf=v_conf, v_pub0=v_pub0, tau_pub_bps=tau_pub, tau_conf_bps=tau_conf, price=price,
        alpha=float(inputs["alpha_capture"]), discount_rate=float(inputs["discount_rate"]),
        terminal_multiple=float(inputs["terminal_multiple"]), conf_haircut=float(inputs["conf_haircut"]),
        gas_burn_near_day0=float(inputs["gas_burn_usd_day"]) / price0,
        state_lock_near_day0=float(inputs["state_lock_near_day"]),
        issuance_near_month=issuance, total_supply=total_supply,
    )
    first = int(out["first_crossover"][0])
    crossover = first if first > 0 else None
    supply_internal = float(out["supply_h"][0])
    override = inputs.get("supply_at_horizon")
    # The override is the glidepath float from supply_physics. When the caller rebuilt the issuance path through
    # ``svrn_target_inflation`` (bear_case governance_stalemate) the sinks are unchanged and only issuance differs,
    # so the horizon float shifts by exactly the extra NEAR issued relative to the explicit path (both compounding).
    adjustment = 0.0
    if override is not None and inputs.get("svrn_target_inflation") is not None and inputs.get("issuance_rate_path") is not None:
        explicit = np.asarray(inputs["issuance_rate_path"], dtype=float)
        if explicit.ndim == 0:
            explicit = np.full(horizon, float(explicit))
        if explicit.shape == path.shape:
            adjustment = float((issuance - compound_issuance(explicit, total_supply)).sum())
    supply_h = float(override) + adjustment if override is not None else supply_internal
    fdv_total = float(out["fdv"][0])
    return {
        "engine_clearinghouse": float(out["e1"][0]),
        "engine_confidential": float(out["e2"][0]),
        "engine_monetary": float(out["e3"][0]),
        "fdv_total": fdv_total,
        "fdv_ex_monetary": float(out["e1"][0] + out["e2"][0]),
        "implied_price": fdv_total / supply_h if supply_h > 0 else float("nan"),
        "net_deflation": crossover is not None,
        "crossover_month": crossover,
        "monthly_holder_revenue": (out["rev_pub"][0] + out["rev_conf"][0]).tolist(),
        "monthly_net_float_change_near": out["net_float"][0].tolist(),
        "monthly_running_fdv": out["running_fdv"][0].tolist(),
        "monthly_tau_pub_bps": tau_pub.tolist(),
        "monthly_tau_conf_bps": tau_conf.tolist(),
        "pv_public": float(out["pv_pub"][0]), "tv_public": float(out["tv_pub"][0]),
        "pv_confidential": float(out["pv_conf"][0]), "tv_confidential": float(out["tv_conf"][0]),
        "pv_gas_burn": float(out["pv_gas"][0]), "tv_gas_burn": float(out["tv_gas"][0]),
        "pv_state_lock": float(out["pv_lock"][0]),
        "cum_holder_revenue_usd": float(out["cum_rev"][0, -1]),
        "cum_buyback_near": float(out["buyback_near"][0].sum()),
        "cum_issuance_near": float(issuance.sum()),
        "net_float_change_cum_near": float(out["net_float"][0].sum()),
        "supply_at_horizon_internal": supply_internal,
        "supply_at_horizon_used": supply_h,
        "supply_at_horizon_adjustment_near": adjustment,
        "supply_at_horizon_near": supply_h,  # name bear_case.py reads
        "issuance_rate_path_used": path.tolist(),
        "horizon_months": horizon,
        "days_per_month": DAYS_PER_MONTH,
    }


# ============================================================================ input assembly
def _regime_paths(
    supply: SupplyPhysics, truth: NearOnchainTruth, assumptions: Mapping[str, Assumption], horizon: int, warnings: list[str]
) -> dict[str, np.ndarray]:
    """Annual inflation paths (length H) for status_quo and svrn_glidepath from ``supply.regimes``.

    A regime missing from supply_physics is rebuilt from the live max_inflation_rate and the registry
    (linear glidepath over ``svrn_glidepath_months`` to ``svrn_target_inflation``) and a warning is
    recorded; paths of the wrong length are truncated or padded with their last value.
    """
    found: dict[str, np.ndarray] = {}
    for r in supply.regimes or []:
        key = r.key.strip().lower()
        if key in (REGIME_STATUS_QUO, REGIME_GLIDEPATH) and key not in found:
            found[key] = np.asarray(r.inflation_path_annual, dtype=float)
    i0 = float(truth.max_inflation_rate)
    t = np.arange(1, horizon + 1, dtype=float)
    if REGIME_STATUS_QUO not in found:
        warnings.append("sotp: supply_physics has no 'status_quo' regime; rebuilt as flat live max_inflation_rate")
        found[REGIME_STATUS_QUO] = np.full(horizon, i0)
    if REGIME_GLIDEPATH not in found:
        warnings.append("sotp: supply_physics has no 'svrn_glidepath' regime; rebuilt linearly from registry assumptions")
        target = A.value("svrn_target_inflation", assumptions)
        g = max(1.0, A.value("svrn_glidepath_months", assumptions))
        # 0-based month index, matching supply_physics (month 1 is still the live rate).
        found[REGIME_GLIDEPATH] = i0 + (target - i0) * np.minimum(t - 1.0, g) / g
    for key, p in list(found.items()):
        if p.shape[0] != horizon:
            warnings.append(f"sotp: regime {key} path length {p.shape[0]} != horizon {horizon}; resized")
            found[key] = p[:horizon] if p.shape[0] > horizon else np.concatenate([p, np.full(horizon - p.shape[0], p[-1])])
    return found


def _supply_at_horizon(
    supply: SupplyPhysics, truth: NearOnchainTruth, regime: str, horizon: int
) -> float | None:
    """S_0 + gross issuance - buybacks - gas burn - state lock at month H from the supply trajectory.

    Recomputed from the component series so the sign convention of ``net_float_change_cum`` is
    irrelevant. None when the regime has no trajectory.
    """
    for traj in supply.trajectories or []:
        if traj.regime.strip().lower() != regime:
            continue
        idx = min(horizon, len(traj.gross_issuance_cum)) - 1
        if idx < 0:
            return None
        return float(
            truth.total_supply_near + traj.gross_issuance_cum[idx] - traj.buyback_cum[idx]
            - traj.gas_burn_cum[idx] - traj.state_lock_cum[idx]
        )
    return None


def _volumes_30d(
    forensics: IntentsForensics, assumptions: Mapping[str, Assumption], warnings: list[str]
) -> tuple[float, float, dict[str, Any]]:
    """(public, confidential, meta) 30d volume in USD on the canonical take-rate window.

    The total is the aligned-window volume from ``forensics.fees`` (the same days as the fees), falling
    back to nearstats' 30d total. The confidential share comes from nearstats' public/confidential split;
    when that split is unavailable (nearstats outage) the confidential volume is set to 0 with a warning
    and Engine 2 is reported as not measured (``meta["confidential_engine_measured"] = False``), so a
    single host outage degrades the run instead of aborting it and nothing is invented.
    """
    vol = forensics.volume or {}
    fees = forensics.fees or {}
    total = _num(fees, "volume_30d_usd")
    total_src = "intents_forensics.fees.volume_30d_usd (aligned take-rate window)"
    if total is None or total <= 0:
        total = _num(vol, "30d", "volume30dUsd", "total30d")
        total_src = "nearstats intents.totals.volume30dUsd"
    pub_ns = _num(vol, "public30d", "public_30d_usd", "public30dUsd")
    conf_ns = _num(vol, "confidential30d", "confidential_30d_usd", "confidential30dUsd")
    share = _num(vol, "confidential_share_30d")
    if share is None and pub_ns is not None and conf_ns is not None and pub_ns + conf_ns > 0:
        share = conf_ns / (pub_ns + conf_ns)
    share_src = "measured: nearstats intents.totalsBreakdown confidential / total 30d"
    if total is None and pub_ns is not None and conf_ns is not None:
        total, total_src = pub_ns + conf_ns, "nearstats public30d + confidential30d"
    if total is None or total <= 0:
        raise ValueError(
            "sotp: 30d intents volume is null in every source (fees.volume_30d_usd, volume.30d, volume.public30d + "
            "volume.confidential30d); the revenue engines cannot be sized"
        )
    status = vol.get("confidential_share_status")
    measured = share is not None
    if share is not None and status == "implausible_fallback":
        # intents_forensics.confidential_split_guard rejected nearstats' split and substituted the registry assumption
        # confidential_share: the volume is sized, but the share is an assumption and Engine 2 is not measured.
        measured = False
        share_src = str(vol.get("confidential_share_source") or "assumption: registry confidential_share (nearstats split implausible)")
        reported = _num(vol, "confidential_share_30d_reported")
        warnings.append(
            f"sotp: confidential share is the registry ASSUMPTION confidential_share = {share:.0%}, not a measurement "
            + (f"(nearstats reported {reported:.4%}, rejected as implausible by confidential_split_guard)" if reported is not None
               else "(nearstats split rejected as implausible by confidential_split_guard)")
            + "; Engine 2 rests on that assumption and is reported as NOT MEASURED"
        )
    elif share is None:
        share = 0.0
        share_src = "not measured: nearstats public/confidential split unavailable; confidential volume credited 0 (Engine 2 not measured)"
        warnings.append(
            "sotp: nearstats public/confidential split is null; confidential share set to 0 (no confidential volume credited) and "
            "Engine 2 is reported as not measured; all 30d volume is treated as public"
        )
    conf = total * share
    pub = total - conf
    meta = {"volume_30d_total_usd": total, "volume_30d_source": total_src, "confidential_share_source": share_src,
            "confidential_share_assumed": not measured, "confidential_engine_measured": measured,
            "confidential_share_status": status or ("measured" if measured else "unavailable")}
    return max(pub, 0.0), max(conf, 0.0), meta


def _fees_30d(forensics: IntentsForensics, v_total_30d: float) -> float:
    """Gross 30d fees in USD: ``gross_fees_30d_usd`` or ``gross_take_bps`` x 30d volume."""
    fees = forensics.fees or {}
    f = _num(fees, "gross_fees_30d_usd", "fees_30d_usd")
    if f is None:
        take = _num(fees, "gross_take_bps")
        if take is not None:
            f = take / 1e4 * v_total_30d
    if f is None:
        raise ValueError(f"sotp: forensics.fees needs gross_fees_30d_usd or gross_take_bps; got keys {sorted(fees)}")
    return f


def _capture_ratio(forensics: IntentsForensics, fees_30d: float, assumptions: Mapping[str, Assumption]) -> tuple[float, str]:
    """alpha: registry override when >= 0, else live holders_revenue / fees (DefiLlama)."""
    override = A.value("buyback_capture_ratio_override", assumptions)
    if override >= 0.0:
        return min(override, 1.0), "assumption:buyback_capture_ratio_override"
    fees = forensics.fees or {}
    # Holder revenue (DefiLlama dailyHoldersRevenue) is the buyback-directed flow; the generic
    # capture_ratio (net revenue / fees) is the same number live and serves as the fallback.
    alpha = _num(fees, "holders_capture_ratio", "capture_ratio")
    if alpha is None:
        hr = _num(fees, "holders_revenue_30d_usd", "net_revenue_30d_usd")
        if hr is not None and fees_30d > 0:
            alpha = hr / fees_30d
    if alpha is None:
        raise ValueError("sotp: forensics.fees needs capture_ratio or holders_revenue_30d_usd (live DefiLlama); none present")
    return float(min(max(alpha, 0.0), 1.0)), "measured:defillama near-intents dailyHoldersRevenue / fees"


def _sigmas(forensics: IntentsForensics, warnings: list[str], assumptions: Mapping[str, Assumption] | None = None) -> dict[str, Any]:
    """Monthly price and volume sigmas from forensics.volatility.

    Price sigma: measured 1y daily-close sigma (nearstats, else the coins.llama.fi chart recorded by the
    collector); when both series failed the labeled ``price_sigma_annual_fallback`` assumption is used with a
    warning (``sigma_price_source = "assumption:price_sigma_annual_fallback"``). Volume sigma: the measured
    monthly log-return sigma of 30-day aggregates, else daily sigma x sqrt(30) (derived, warned), else - when the
    DefiLlama dexs chart was unavailable altogether (the 30-day volume then comes from nearstats) - the labeled
    ``volume_sigma_monthly_fallback`` assumption with a warning (``sigma_volume_source =
    "assumption:volume_sigma_monthly_fallback"``). A single-source chart outage never aborts the run.
    """
    reg = assumptions if assumptions is not None else A.ASSUMPTIONS
    vol = forensics.volatility or {}
    sig_p_annual = _num(vol, "annualized_sigma", "price_annualized_sigma")
    price_source = vol.get("source")
    price_measured = True
    if sig_p_annual is None:
        daily = _num(vol, "daily_sigma", "price_daily_sigma")
        if daily is not None:
            sig_p_annual = daily * math.sqrt(365.0)
    if sig_p_annual is None:
        sig_p_annual = A.value("price_sigma_annual_fallback", reg)
        price_source = "assumption:price_sigma_annual_fallback"
        price_measured = False
        warnings.append(
            "sotp: price volatility unmeasured (nearstats price-history and the coins.llama.fi chart both unavailable); "
            f"price GBM sigma set to the labeled assumption price_sigma_annual_fallback = {sig_p_annual:g} (not measured)"
        )
    sig_v_month = _num(vol, "volume_monthly_sigma")
    source = "measured: monthly log-return sigma of 30-day volume aggregates"
    volume_measured = True
    if sig_v_month is None:
        daily = _num(vol, "volume_daily_sigma")
        if daily is not None:
            sig_v_month = daily * math.sqrt(30.0)
            source = "derived: volume_daily_sigma x sqrt(30) (fallback)"
            warnings.append(
                "sotp: volume_monthly_sigma missing; using volume_daily_sigma x sqrt(30) = "
                f"{sig_v_month:.3f}. Daily volume is mean-reverting, so this overstates monthly dispersion; "
                "intents_forensics should publish volume_monthly_sigma from 30-day aggregates."
            )
        else:
            sig_v_month = A.value("volume_sigma_monthly_fallback", reg)
            source = "assumption:volume_sigma_monthly_fallback"
            volume_measured = False
            warnings.append(
                "sotp: volume volatility unmeasured (DefiLlama dexs chart unavailable: volume_monthly_sigma and volume_daily_sigma "
                f"both null); volume GBM sigma set to the labeled assumption volume_sigma_monthly_fallback = {sig_v_month:g} per month "
                "(not measured)"
            )
    return {
        "sigma_price_annual": float(sig_p_annual),
        "sigma_price_monthly": float(sig_p_annual) / math.sqrt(12.0),
        "sigma_price_measured": price_measured,
        "sigma_volume_monthly": float(sig_v_month),
        "sigma_volume_source": source,
        "sigma_volume_measured": volume_measured,
        "sigma_price_source": price_source,
        "volatility_window": vol.get("window"),
        "volatility_n_obs": vol.get("n_obs"),
        # Sensitivity of the volume sigma to its thin sample: n monthly returns, the returns themselves and the
        # sigma without the three oldest (incentive-program) windows. Reported, not used: the measured value drives the MC.
        "sigma_volume_monthly_n_obs": vol.get("volume_monthly_n_obs"),
        "sigma_volume_monthly_log_returns": vol.get("volume_monthly_log_returns"),
        "sigma_volume_monthly_ex_first_3": _num(vol, "volume_monthly_sigma_ex_first_3"),
    }


def _tau_floor(
    bench: ExecutionBenchmark | None, tau_pub0: float, assumptions: Mapping[str, Assumption], warnings: list[str]
) -> tuple[float, Assumption, dict[str, Any]]:
    """tau_floor = max(public_take_floor_bps, min(tau_pub_0, cross-VM headroom)); the registry floor alone when unmeasured."""
    hard = A.value("public_take_floor_bps", assumptions)
    hard_assumption = assumptions.get("public_take_floor_bps") or A.get("public_take_floor_bps")
    headroom = None
    ceiling = None
    if bench is not None:
        headroom = _num(bench.headroom_by_archetype_bps or {}, "cross_vm")
        ceiling = bench.competitive_fee_ceiling_bps
    if headroom is not None:
        floor = max(hard, min(tau_pub0, headroom))
        a = _point(
            "tau_floor_bps", floor, "bps", "derived",
            f"max({hard:g} bps, min(live public take, live cross-VM headroom)) from the execution benchmark "
            f"(headroom_by_archetype_bps.cross_vm = {headroom:.2f} bps).",
        )
    else:
        floor = hard
        warnings.append(
            "sotp: execution benchmark unavailable (no cross-VM headroom); public take floor set to the registry "
            f"assumption public_take_floor_bps = {hard:g} bps (not measured)"
        )
        a = hard_assumption.model_copy()
    meta = {"headroom_cross_vm_bps": headroom, "competitive_fee_ceiling_bps": ceiling, "public_take_floor_bps": hard}
    return floor, a, meta


def _terminal_multiple(comps: PeerComps, assumptions: Mapping[str, Assumption], warnings: list[str]) -> tuple[float, dict[str, Any]]:
    """Terminal FDV/revenue multiple, clipped to [terminal_multiple_floor, terminal_multiple_cap].

    Fallback chain (a CoinGecko 429/outage must never abort the reproduction): peer median FDV/revenue
    ex-NEAR (``terminal_multiple_source = "derived"``) -> peer median FDV/fees ex-NEAR (``"derived_fdv_to_fees"``,
    a lower bound on FDV/revenue since fees >= revenue, warned) -> the labeled registry assumption
    ``terminal_multiple_fallback`` (``"assumption"``, loud warning, Engine 1 flagged assumption-heavy).
    The source used is recorded in ``calibration.terminal_multiple_source``.
    """
    lo = A.value("terminal_multiple_floor", assumptions)
    hi = A.value("terminal_multiple_cap", assumptions)

    def _valid(x: Any) -> bool:
        return x is not None and math.isfinite(float(x)) and float(x) > 0

    raw_rev, raw_fees = comps.median_fdv_to_revenue_ex_near, comps.median_fdv_to_fees_ex_near
    if _valid(raw_rev):
        raw, source = float(raw_rev), "derived"
        basis = f"peer median FDV / annualized revenue ex-NEAR (n = {comps.n_peers_in_revenue_median}), clipped to [{lo:g}, {hi:g}]"
    elif _valid(raw_fees):
        raw, source = float(raw_fees), "derived_fdv_to_fees"
        basis = (
            f"peer median FDV / annualized FEES ex-NEAR (n = {comps.n_peers_in_fees_median}) standing in for FDV/revenue, "
            f"which is null (CoinGecko FDV or revenue run-rates unavailable); fees >= revenue so this understates the multiple; clipped to [{lo:g}, {hi:g}]"
        )
        warnings.append(
            f"sotp: comps.median_fdv_to_revenue_ex_near is null; terminal multiple falls back to the peer median FDV/fees {raw:.1f}x "
            "(a lower bound on FDV/revenue); terminal_multiple_source = derived_fdv_to_fees"
        )
    else:
        fb = A.value("terminal_multiple_fallback", assumptions)
        warnings.append(
            "sotp: WARNING peer multiples unavailable (comps.median_fdv_to_revenue_ex_near and median_fdv_to_fees_ex_near are both null: "
            f"CoinGecko FDV outage/429); terminal multiple set to the labeled registry assumption terminal_multiple_fallback = {fb:g}x, "
            "terminal_multiple_source = assumption, Engine 1 flagged assumption-heavy. Re-run when CoinGecko answers to replace it."
        )
        return float(fb), {
            "terminal_multiple_raw": None, "terminal_multiple_used": float(fb), "terminal_multiple_clipped": False,
            "terminal_multiple_source": "assumption",
            "terminal_multiple_basis": "registry assumption terminal_multiple_fallback (peer FDV/revenue and FDV/fees medians both null)",
        }
    used = min(max(raw, lo), hi)
    clipped = used != raw
    if clipped:
        warnings.append(f"sotp: peer median {'FDV/revenue' if source == 'derived' else 'FDV/fees'} {raw:.1f}x clipped to {used:.1f}x (guardrails [{lo:g}, {hi:g}])")
    return used, {
        "terminal_multiple_raw": raw, "terminal_multiple_used": used, "terminal_multiple_clipped": clipped,
        "terminal_multiple_source": source, "terminal_multiple_basis": basis,
    }


def build_inputs(
    truth: NearOnchainTruth,
    forensics: IntentsForensics,
    comps: PeerComps,
    supply: SupplyPhysics,
    assumptions: Mapping[str, Assumption] | None = None,
    *,
    bench: ExecutionBenchmark | None = None,
    horizon_months: int = config.HORIZON_MONTHS,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Assumption]]:
    """Assemble the base ``deterministic_sotp`` input dict from live collector outputs.

    Returns ``(inputs, calibration, labeled_inputs)``. ``inputs`` carries, besides the keys
    ``deterministic_sotp`` reads, ``issuance_rate_paths`` for both regimes and ``supply_at_horizon``
    per regime so bear_case.py can switch regimes by perturbing the dict. ``calibration`` records
    every measured/derived parameter and a ``warnings`` list. Raises ``ValueError`` when a required
    live input is null (nothing is invented).
    """
    reg = assumptions if assumptions is not None else A.ASSUMPTIONS
    warnings: list[str] = []
    horizon = int(horizon_months)

    v_pub_30d, v_conf_30d, vol_meta = _volumes_30d(forensics, reg, warnings)
    v_total_30d = v_pub_30d + v_conf_30d
    window_days = _num(forensics.fees or {}, "take_rate_window_days") or 30.0
    if v_total_30d <= 0:
        warnings.append("sotp: 30d intents volume is zero; revenue engines will be zero")
    fees_30d = _fees_30d(forensics, v_total_30d)
    alpha, alpha_source = _capture_ratio(forensics, fees_30d, reg)
    tau_conf0 = A.value("confidential_take_bps", reg)
    tau_conf_source = "assumption: registry confidential_take_bps (1Click confidential quotes need partner authentication)"
    conf_q = getattr(bench, "confidential_quote", None) if bench is not None else None
    prem = _num(conf_q or {}, "premium_bps") if isinstance(conf_q, dict) and conf_q.get("status") == "measured" else None
    if prem is not None and v_total_30d > 0:
        # Measured: what a confidential quote costs over the public quote on the same trade, added to the blended
        # gross take NEAR Intents earns today (DefiLlama fees / volume).
        tau_conf0 = max(0.0, fees_30d / v_total_30d * 1e4 + prem)
        tau_conf_source = (f"measured: blended gross take {fees_30d / v_total_30d * 1e4:.2f} bps + live confidential premium {prem:.2f} bps "
                           "(1Click dry quotes, same trade, public vs confidentiality=advanced)")

    # Reconcile the public take so month-0 modelled fees equal DefiLlama's 30d fees.
    blended_gross_bps = fees_30d / v_total_30d * 1e4 if v_total_30d > 0 else 0.0
    if v_pub_30d > 0:
        tau_pub0 = (fees_30d - v_conf_30d * tau_conf0 / 1e4) / v_pub_30d * 1e4
        tau_pub_method = "reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d"
        if tau_pub0 < HARD_FLOOR_BPS:
            warnings.append(
                f"sotp: confidential take {tau_conf0:g} bps on {v_conf_30d / v_total_30d:.0%} of volume exceeds live fees; "
                f"public take falls back to the blended gross take {blended_gross_bps:.2f} bps"
            )
            tau_pub0 = blended_gross_bps
            tau_pub_method = "blended gross take (reconciliation infeasible)"
    else:
        tau_pub0 = blended_gross_bps
        tau_pub_method = "blended gross take (no public volume)"

    floor, floor_assumption, floor_meta = _tau_floor(bench, tau_pub0, reg, warnings)
    multiple, mult_meta = _terminal_multiple(comps, reg, warnings)
    sig = _sigmas(forensics, warnings, reg)
    # MODEL_DESIGN 4.2: widen the confidential-volume sigma while the shard's TVL is unverified. The factor is a
    # labeled registry assumption (default 1.0 = no widening); the verified flag comes from nearstats.
    conf_sigma_mult = 1.0 if forensics.confidential_tvl_verified else A.value("confidential_volume_sigma_multiplier", reg)

    # Price: the one supply_physics already resolved (nearstats, else the comps coins.llama.fi price), so a
    # nearstats outage does not abort the SOTP and both models convert USD to NEAR at the same number.
    price_input = (supply.inputs or {}).get("near_price_usd")
    price = float(price_input.value) if price_input is not None and price_input.value > 0 else None
    price_src = price_input.justification if price_input is not None else None
    if price is None:
        price = _num(forensics.price or {}, "current_usd", "price_usd")
        price_src = "intents_forensics.price.current_usd (nearstats)"
    if price is None or price <= 0:
        raise ValueError("sotp: NEAR price is null in supply_physics.inputs.near_price_usd and forensics.price.current_usd; cannot convert buybacks to NEAR")
    # Current FDV on the model's own basis: the same spot price x the on-chain total supply at the snapshot block.
    # The CoinGecko fdvUsd relayed by nearstats was struck at a different instant and implies a different price; it is
    # kept separately as current_fdv_coingecko_usd (alias current_fdv_nearstats_usd) for the cross-check only.
    fdv_now = price * truth.total_supply_near
    fdv_nearstats = _num(forensics.price or {}, "fdv_usd")

    sinks = supply.current_daily_sinks_near or {}
    gas_burn_near_day = _num(sinks, "gas_burn")
    if gas_burn_near_day is None:
        raise ValueError("sotp: supply.current_daily_sinks_near.gas_burn is null (live near chain revenue / epoch burn)")
    state_lock_near_day = _num(sinks, "state_lock")
    if state_lock_near_day is None:
        state_lock_near_day = A.value("state_lock_growth_fallback_near_per_day", reg)
        warnings.append(
            "sotp: supply.current_daily_sinks_near.state_lock is null; using registry fallback "
            f"state_lock_growth_fallback_near_per_day = {state_lock_near_day:g} NEAR/day (no credit by default)"
        )

    regimes = _regime_paths(supply, truth, reg, horizon, warnings)
    sq0 = float(regimes[REGIME_STATUS_QUO][0])
    issuance_scale = (
        float(supply.current_daily_issuance_near) * 365.25 / (truth.total_supply_near * sq0) if sq0 > 0 else 1.0
    )
    effective_paths = {k: (p * issuance_scale).tolist() for k, p in regimes.items()}

    supply_h = {k: _supply_at_horizon(supply, truth, k, horizon) for k in regimes}
    for k, v in supply_h.items():
        if v is None:
            warnings.append(f"sotp: supply_physics has no '{k}' trajectory; implied price uses the model's internal float at H")

    g_yoy = A.value("public_volume_growth_yoy", reg)
    if g_yoy <= -1.0:
        raise ValueError("public_volume_growth_yoy must be > -1")
    g_pub = (1.0 + g_yoy) ** (1.0 / 12.0) - 1.0
    s0 = v_conf_30d / v_total_30d if v_total_30d > 0 else 0.0
    s_target = min(max(A.value("confidential_share_target", reg), 0.0), 0.99)
    if 0.0 < s0 < 1.0 and v_pub_30d > 0:
        # Median confidential path: share moves linearly to the target, so odds scale by odds_H / odds_0.
        odds0 = s0 / (1.0 - s0)
        odds_h = s_target / (1.0 - s_target)
        g_conf = ((1.0 + g_pub) ** horizon * odds_h / odds0) ** (1.0 / horizon) - 1.0
    else:
        g_conf = g_pub
        if s0 == 0.0:
            warnings.append("sotp: confidential volume starts at zero; multiplicative model keeps it at zero")

    lam = A.value("fee_compression_lambda_monthly", reg)
    lam_conf = lam / max(A.value("confidential_compression_divisor", reg), 1e-9)

    inputs: dict[str, Any] = {
        "v_pub_usd_day": v_pub_30d / window_days,
        "v_conf_usd_day": v_conf_30d / window_days,
        "tau_pub_bps": tau_pub0,
        "tau_conf_bps": tau_conf0,
        "alpha_capture": alpha,
        "discount_rate": A.value("discount_rate", reg),
        "terminal_multiple": multiple,
        "conf_haircut": A.value("confidential_multiple_haircut", reg),
        "gas_burn_usd_day": gas_burn_near_day * price,
        "state_lock_near_day": state_lock_near_day,
        "price_usd": price,
        "total_supply": float(truth.total_supply_near),
        "issuance_rate_path": effective_paths[REGIME_GLIDEPATH],
        "growth_monthly_pub": g_pub,
        "growth_monthly_conf": g_conf,
        "lambda_pub": lam,
        "lambda_conf": lam_conf,
        "tau_floor_bps": floor,
        "horizon_months": horizon,
        "price_drift_annual": A.value("near_price_drift_annual", reg),
        "supply_at_horizon": supply_h[REGIME_GLIDEPATH],
        # Extras for regime switching (bear_case.py) and the crossover distribution.
        "regime": REGIME_GLIDEPATH,
        "issuance_rate_paths": effective_paths,
        "supply_at_horizon_by_regime": supply_h,
        # Regime parameters: svrn_target_inflation is None so the explicit path above is used; a caller
        # (bear_case governance_stalemate) that sets it non-null makes deterministic_sotp rebuild the path.
        "svrn_target_inflation": None,
        "max_inflation_rate": sq0,
        "svrn_glidepath_months": A.value("svrn_glidepath_months", reg),
        "issuance_scale": issuance_scale,
        "current_fdv_usd": fdv_now,
        "sigma_volume_monthly": sig["sigma_volume_monthly"],
        "sigma_price_monthly": sig["sigma_price_monthly"],
        "confidential_sigma_multiplier": conf_sigma_mult,
    }
    sig_v = sig["sigma_volume_monthly"]
    v_pub_day = v_pub_30d / window_days
    mean_h = v_pub_day * (1.0 + g_pub) ** horizon
    calibration: dict[str, Any] = {
        "take_basis": "tau = gross fees / volume (bps); alpha = holders revenue / fees; holder revenue = V x tau x alpha",
        "take_rate_window": (forensics.fees or {}).get("take_rate_window"), "take_rate_window_days": window_days,
        "take_rate_window_note": (
            "ONE canonical window from intents_forensics.fees (last 30 complete UTC days common to the DefiLlama fees, revenue and "
            "volume daily charts); gross_take_bps / net_take_bps / capture_ratio / volume_30d_usd are consumed, not recomputed"
        ),
        "gross_take_bps": _num(forensics.fees or {}, "gross_take_bps"), "net_take_bps": _num(forensics.fees or {}, "net_take_bps"),
        "v_pub_30d_usd": v_pub_30d, "v_conf_30d_usd": v_conf_30d, "gross_fees_30d_usd": fees_30d, **vol_meta,
        "blended_gross_take_bps": blended_gross_bps,
        "gbm_convention": GBM_CONVENTION,
        "volume_mean_to_median_12m": math.exp(sig_v**2 * 12.0 / 2.0),
        "volume_mean_to_median_horizon": math.exp(sig_v**2 * horizon / 2.0),
        # Analytic terminal public volume under the mean-matching GBM: mean = deterministic path, median = mean x exp(-sigma^2 H / 2).
        "volume_terminal_mean_usd_day": mean_h,
        "volume_terminal_median_usd_day": mean_h * math.exp(-(sig_v**2) * horizon / 2.0),
        "volume_start_usd_day": v_pub_day,
        "price_source": price_src, "current_fdv_basis": "spot price x on-chain total_supply at the snapshot block",
        "current_fdv_coingecko_usd": fdv_nearstats,
        "current_fdv_nearstats_usd": fdv_nearstats,
        "current_fdv_nearstats_gap_pct": ((fdv_nearstats / fdv_now - 1.0) * 100.0) if (fdv_nearstats and fdv_now) else None,
        "tau_pub_start_bps": tau_pub0, "tau_pub_start_method": tau_pub_method,
        "tau_conf_start_bps": tau_conf0,
        "tau_conf_source": tau_conf_source,
        "net_take_start_bps": blended_gross_bps * alpha,
        "alpha_capture": alpha, "alpha_source": alpha_source,
        "tau_floor_bps": floor, "tau_floor_source": floor_assumption.source, **floor_meta,
        **mult_meta, **sig,
        "lambda_pub_monthly": lam, "lambda_conf_monthly": lam_conf,
        "growth_monthly_pub": g_pub, "growth_monthly_conf": g_conf,
        "confidential_share_start": s0, "confidential_share_target": s_target,
        "confidential_sigma_multiplier": conf_sigma_mult,
        "sigma_volume_monthly_conf": sig["sigma_volume_monthly"] * conf_sigma_mult,
        "confidential_tvl_verified": bool(forensics.confidential_tvl_verified),
        "issuance_scale_measured_over_path": issuance_scale,
        "regime_inflation_paths_annual": {k: p.tolist() for k, p in regimes.items()},
        "supply_at_horizon_near": supply_h[REGIME_GLIDEPATH],
        "supply_at_horizon_by_regime": supply_h,
        "price_basis": "fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory)",
        "gas_burn_near_day": gas_burn_near_day, "state_lock_near_day": state_lock_near_day,
        "price_usd": price, "current_fdv_usd": fdv_now, "days_per_month": DAYS_PER_MONTH,
        "crossover_basis": "first month whose net float change (issuance - buyback - gas burn - state lock) <= 0",
        "warnings": warnings,
    }
    labeled: dict[str, Assumption] = {
        k: reg[k].model_copy() for k in (
            "public_volume_growth_yoy", "confidential_share_target", "confidential_take_bps",
            "fee_compression_lambda_monthly", "confidential_compression_divisor", "discount_rate",
            "terminal_multiple_floor", "terminal_multiple_cap", "confidential_multiple_haircut",
            "buyback_capture_ratio_override", "near_price_drift_annual",
        ) if k in reg
    }
    if not forensics.confidential_tvl_verified and "confidential_volume_sigma_multiplier" in reg:
        labeled["confidential_volume_sigma_multiplier"] = reg["confidential_volume_sigma_multiplier"].model_copy()
    if state_lock_near_day == A.value("state_lock_growth_fallback_near_per_day", reg) and _num(sinks, "state_lock") is None:
        labeled["state_lock_growth_fallback_near_per_day"] = reg["state_lock_growth_fallback_near_per_day"].model_copy()
    labeled[floor_assumption.key] = floor_assumption
    labeled["tau_pub_start_bps"] = _point(
        "tau_pub_start_bps", tau_pub0, "bps", "derived",
        f"{tau_pub_method}; blended live gross take {blended_gross_bps:.2f} bps (DefiLlama daily fees / daily volume summed over the "
        f"aligned take-rate window: {(forensics.fees or {}).get('take_rate_window')}).",
    )
    labeled["alpha_capture"] = _point("alpha_capture", alpha, "ratio", "measured" if alpha_source.startswith("measured") else "assumption", alpha_source)
    if mult_meta["terminal_multiple_source"] == "assumption":
        labeled["terminal_multiple_fallback"] = reg["terminal_multiple_fallback"].model_copy()
        labeled["terminal_multiple"] = _point(
            "terminal_multiple", multiple, "x_fdv_to_revenue", "assumption",
            "peer FDV/revenue and FDV/fees medians both unavailable (CoinGecko FDV null); registry assumption terminal_multiple_fallback used, Engine 1 assumption-heavy.",
        )
    else:
        labeled["terminal_multiple"] = _point(
            "terminal_multiple", multiple, "x_fdv_to_revenue", "derived",
            f"{mult_meta['terminal_multiple_basis']}; raw {mult_meta['terminal_multiple_raw']:.1f}x.",
        )
    if vol_meta.get("confidential_share_status") == "implausible_fallback":
        labeled["confidential_share_start"] = _point(
            "confidential_share_start", s0, "ratio", "assumption",
            f"assumption:confidential_share - {vol_meta.get('confidential_share_source')}. The nearstats public/confidential split failed the plausibility guard, so the "
            "starting confidential share is the registry assumption confidential_share (Engine 2 not measured this run).",
        )
        if "confidential_share" in reg:
            labeled["confidential_share"] = reg["confidential_share"].model_copy()
    elif vol_meta.get("confidential_share_assumed"):
        labeled["confidential_share_start"] = _point(
            "confidential_share_start", s0, "ratio", "assumption",
            "nearstats public/confidential split unavailable; confidential volume credited 0 (Engine 2 not measured this run).",
        )
    if not sig.get("sigma_price_measured", True):
        labeled["price_sigma_annual_fallback"] = reg["price_sigma_annual_fallback"].model_copy()
    labeled["sigma_price_annual"] = _point(
        "sigma_price_annual", sig["sigma_price_annual"], "ratio_annual", "measured" if sig.get("sigma_price_measured", True) else "assumption",
        f"{sig.get('sigma_price_source') or 'price series'}: 1y daily closes, log-return sigma x sqrt(365)."
        if sig.get("sigma_price_measured", True) else
        "price series unavailable from nearstats and coins.llama.fi; labeled registry fallback price_sigma_annual_fallback (not measured).",
    )
    vol_src = sig["sigma_volume_source"]
    if vol_src.startswith("assumption"):
        labeled["volume_sigma_monthly_fallback"] = reg["volume_sigma_monthly_fallback"].model_copy()
        labeled["sigma_volume_monthly"] = _point(
            "sigma_volume_monthly", sig["sigma_volume_monthly"], "ratio_monthly", "assumption",
            "DefiLlama dexs chart unavailable (no monthly or daily volume sigma); labeled registry fallback volume_sigma_monthly_fallback (not measured).",
        )
    else:
        labeled["sigma_volume_monthly"] = _point("sigma_volume_monthly", sig["sigma_volume_monthly"], "ratio_monthly", "measured" if vol_src.startswith("measured") else "derived", vol_src)
    return inputs, calibration, labeled


# ============================================================================ Monte Carlo
def simulate_paths(inputs: Mapping[str, Any], *, seed: int, n_paths: int) -> dict[str, Any]:
    """Vectorized Monte Carlo over ``n_paths`` x H months from a ``build_inputs`` dict.

    Shocks are drawn once with ``default_rng(seed)`` in the order public volume, confidential volume,
    price (each (n_paths, H) standard normals). Paths use the mean-matching (Ito) convention so the
    EXPECTED path equals the deterministic one and the labeled growth is a mean growth:
      log V_pub_t  = log v_pub  + t x (ln(1 + g_pub)  - sigma_v^2 / 2)      + sigma_v x sum_{s<=t} z_pub_s
      log V_conf_t = log v_conf + t x (ln(1 + g_conf) - sigma_vc^2 / 2)     + sigma_vc x sum_{s<=t} z_conf_s
      log P_t      = log price  + t x (ln(1 + d) / 12 - sigma_p^2 / 2)      + sigma_p x sum_{s<=t} z_price_s
    so E[V_t] = v (1+g)^t and E[P_t] = price (1+d)^(t/12); the median path is exp(-sigma^2 t / 2) lower.
    Take-rates are deterministic (no measured dispersion exists; nothing is invented). Net float and
    crossover are evaluated under both regimes (only issuance differs). Returns per-path arrays.
    """
    if n_paths < 1:
        raise ValueError("n_paths must be >= 1")
    horizon = int(inputs["horizon_months"])
    rng = np.random.default_rng(seed)
    z_pub = rng.standard_normal((n_paths, horizon))
    z_conf = rng.standard_normal((n_paths, horizon))
    z_price = rng.standard_normal((n_paths, horizon))

    t = np.arange(1, horizon + 1, dtype=float)
    sig_v = float(inputs["sigma_volume_monthly"])
    # Confidential leg: same measured sigma times the (labeled) widening factor used while TVL is unverified.
    sig_v_conf = sig_v * float(inputs.get("confidential_sigma_multiplier") or 1.0)
    sig_p = float(inputs["sigma_price_monthly"])
    v_pub0 = float(_in(inputs, "v_pub_usd_day", "v_pub_daily_usd"))
    v_conf0 = float(_in(inputs, "v_conf_usd_day", "v_conf_daily_usd"))
    price0 = float(inputs["price_usd"])

    def _gbm(x0: float, log_growth_monthly: float, sigma: float, z: np.ndarray) -> np.ndarray:
        """Mean-matching GBM: log x_t = log x0 + t (mu - sigma^2/2) + sigma W_t, so E[x_t] = x0 exp(mu t)."""
        if x0 <= 0:
            return np.zeros_like(z)
        drift = t * (log_growth_monthly - 0.5 * sigma * sigma)
        return np.exp(math.log(x0) + drift[None, :] + sigma * np.cumsum(z, axis=1))

    v_pub = _gbm(v_pub0, math.log1p(float(inputs["growth_monthly_pub"])), sig_v, z_pub)
    v_conf = _gbm(v_conf0, math.log1p(float(inputs["growth_monthly_conf"])), sig_v_conf, z_conf)
    d = float(inputs.get("price_drift_annual") or 0.0)
    price = _gbm(price0, math.log1p(d) / 12.0, sig_p, z_price)

    floor = float(inputs["tau_floor_bps"])
    lambda_pub = float(_in(inputs, "lambda_pub", "fee_compression_lambda_monthly"))
    tau_pub = _tau_path(float(inputs["tau_pub_bps"]), floor, lambda_pub, horizon)
    tau_conf = _tau_path(float(inputs["tau_conf_bps"]), floor, float(inputs["lambda_conf"]), horizon)
    total_supply = float(inputs["total_supply"])
    regime = str(inputs.get("regime", REGIME_GLIDEPATH))
    paths: dict[str, Any] = dict(inputs.get("issuance_rate_paths") or {})
    # The valuation regime always follows what deterministic_sotp would use (explicit path or the
    # svrn_target_inflation rebuild), so a caller that swaps only that still gets a consistent crossover.
    paths[regime] = _issuance_path(inputs, horizon)
    iss = {k: compound_issuance(np.asarray(p, dtype=float), total_supply) for k, p in paths.items()}

    out = _value_paths(
        v_pub=v_pub, v_conf=v_conf, v_pub0=v_pub0, tau_pub_bps=tau_pub, tau_conf_bps=tau_conf, price=price,
        alpha=float(inputs["alpha_capture"]), discount_rate=float(inputs["discount_rate"]),
        terminal_multiple=float(inputs["terminal_multiple"]), conf_haircut=float(inputs["conf_haircut"]),
        gas_burn_near_day0=float(inputs["gas_burn_usd_day"]) / price0,
        state_lock_near_day0=float(inputs["state_lock_near_day"]),
        issuance_near_month=iss[regime], total_supply=total_supply,
    )
    # Net float under every regime: identical sinks, regime-specific issuance.
    net_float = {k: out["net_float"] + (iss[k] - iss[regime])[None, :] for k in iss}
    out["net_float_by_regime"] = net_float
    out["first_crossover_by_regime"] = {k: _first_crossover(v) for k, v in net_float.items()}
    out["v_pub"], out["v_conf"], out["price"] = v_pub, v_conf, price
    out["tau_pub"], out["tau_conf"] = tau_pub, tau_conf
    return out


def _engine_shares_on_median_path(sim: Mapping[str, Any]) -> dict[str, float]:
    """Engine values on the path whose total FDV is the sample median (an additive decomposition of one path).

    Percentiles per engine do not add up to the total's percentile, so the memo needs one path where they do.
    """
    fdv = np.asarray(sim["fdv"])
    idx = int(np.argsort(fdv)[fdv.size // 2])
    total = float(fdv[idx])
    return {
        "path_index": idx, "fdv_total": total,
        "clearinghouse": float(sim["e1"][idx]), "confidential": float(sim["e2"][idx]), "monetary": float(sim["e3"][idx]),
        "clearinghouse_share": float(sim["e1"][idx] / total) if total else None,
        "confidential_share": float(sim["e2"][idx] / total) if total else None,
        "monetary_share": float(sim["e3"][idx] / total) if total else None,
    }


def mc_fdv_p50(inputs: Mapping[str, Any], *, seed: int, n_paths: int) -> float:
    """Median total FDV over ``n_paths`` seeded paths for an arbitrary (e.g. bear-perturbed) input dict."""
    return float(np.median(simulate_paths(inputs, seed=seed, n_paths=n_paths)["fdv"]))


def _heatmap(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """5x5 run-rate sensitivity: daily volume x blended NET take, held constant for H months.

    Rows follow ``y`` (net take bps), columns follow ``x`` (daily volume USD). Each cell calls
    ``deterministic_sotp`` with alpha = 1 and tau_pub = tau_conf = y (so holder revenue is exactly
    V x y), zero growth, zero compression, zero price drift, under the svrn_glidepath regime; the
    live confidential share splits the volume between the two engines.
    """
    v_pub0 = float(inputs["v_pub_usd_day"])
    v_conf0 = float(inputs["v_conf_usd_day"])
    tot = v_pub0 + v_conf0
    share = v_conf0 / tot if tot > 0 else 0.0
    fdv: list[list[float]] = []
    defl: list[list[bool]] = []
    for y in HEATMAP_NET_TAKE_BPS:
        row_f: list[float] = []
        row_d: list[bool] = []
        for x in HEATMAP_VOLUMES_USD:
            cell = dict(inputs)
            cell.update({
                "v_pub_usd_day": x * (1.0 - share), "v_conf_usd_day": x * share,
                "tau_pub_bps": y, "tau_conf_bps": y, "alpha_capture": 1.0, "tau_floor_bps": y,
                "growth_monthly_pub": 0.0, "growth_monthly_conf": 0.0, "lambda_pub": 0.0, "lambda_conf": 0.0,
                "price_drift_annual": 0.0, "regime": REGIME_GLIDEPATH,
                "issuance_rate_path": (inputs.get("issuance_rate_paths") or {}).get(REGIME_GLIDEPATH, inputs["issuance_rate_path"]),
            })
            res = deterministic_sotp(cell)
            row_f.append(res["fdv_total"])
            row_d.append(bool(res["net_deflation"]))
        fdv.append(row_f)
        defl.append(row_d)
    return {
        "x": list(HEATMAP_VOLUMES_USD), "y": list(HEATMAP_NET_TAKE_BPS),
        "x_label": "daily_intents_volume_usd", "y_label": "blended_net_take_bps",
        "fdv_p50": fdv, "net_deflation": defl,
        "basis": "held constant for the horizon; alpha folded into the net take; regime svrn_glidepath",
        "confidential_share_used": share, "regime": REGIME_GLIDEPATH,
    }


def run_sotp(
    truth: NearOnchainTruth,
    forensics: IntentsForensics,
    comps: PeerComps,
    supply: SupplyPhysics,
    assumptions: Mapping[str, Assumption] | None = None,
    *,
    seed: int = config.SEED,
    n_paths: int = config.MC_PATHS,
    horizon_months: int = config.HORIZON_MONTHS,
    bench: ExecutionBenchmark | None = None,
) -> SotpValuation:
    """Build inputs from live collector outputs, run the seeded Monte Carlo and assemble ``SotpValuation``.

    Percentiles are over paths; ``price_percentiles`` = ``fdv_percentiles`` / supply at H under the
    svrn_glidepath trajectory from ``supply`` (internal float when the trajectory is absent). The fan
    chart holds monthly p10..p90 of the running implied FDV (``fdv_*``) and of cumulative holder
    revenue (``rev_*``). ``calibration["deterministic_base"]`` is ``deterministic_sotp`` at the same
    inputs; with zero sigmas the Monte Carlo collapses onto it exactly.
    """
    inputs, calibration, labeled = build_inputs(
        truth, forensics, comps, supply, assumptions, bench=bench, horizon_months=horizon_months
    )
    horizon = int(inputs["horizon_months"])
    sim = simulate_paths(inputs, seed=seed, n_paths=n_paths)
    det = deterministic_sotp(inputs)

    fdv_pct = percentiles(sim["fdv"])
    supply_h = inputs.get("supply_at_horizon")
    if supply_h is None:
        supply_h = det["supply_at_horizon_internal"]
    price_pct = {k: v / supply_h for k, v in fdv_pct.items()}
    current_fdv = float(inputs["current_fdv_usd"])

    multiple_source = calibration.get("terminal_multiple_source")
    multiple_assumed = multiple_source == "assumption"
    conf_measured = bool(calibration.get("confidential_engine_measured", True))
    engines = [
        EngineValue(
            key="clearinghouse", label="Engine 1: cross-chain clearinghouse (public intents holder revenue)",
            **percentiles(sim["e1"]),
            method="PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus "
            "year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor."
            + (" Terminal multiple is the registry assumption terminal_multiple_fallback (peer medians unavailable this run)." if multiple_assumed else "")
            + (" Terminal multiple is the peer FDV/fees median standing in for FDV/revenue (null this run)." if multiple_source == "derived_fdv_to_fees" else ""),
            assumption_heavy=multiple_assumed,
        ),
        EngineValue(
            key="confidential", label="Engine 2: confidential execution franchise (dark-pool holder revenue)",
            **percentiles(sim["e2"]),
            method="Same construction on confidential volume at the assumed confidential take; terminal multiple x "
            "confidential_multiple_haircut because nearstats flags confidential TVL as unverified."
            + ("" if conf_measured else (
                f" NOT MEASURED this run: the nearstats public/confidential split failed the plausibility guard; the starting confidential "
                f"share is the registry assumption confidential_share ({calibration.get('confidential_share_start', 0.0):.0%}), so this engine "
                "values an assumed volume, not a measured one."
                if calibration.get("confidential_share_status") == "implausible_fallback" else
                " NOT MEASURED this run: the nearstats public/confidential split was unavailable, confidential volume is 0 and this engine is 0."
            )),
            assumption_heavy=True,
        ),
        EngineValue(
            key="monetary", label="Engine 3: monetary / supply-sink premium (gas burn + state-lock demand flow)",
            **percentiles(sim["e3"]),
            method="PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value "
            "of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.",
            assumption_heavy=True,
        ),
    ]

    months = list(range(1, horizon + 1))
    fan: dict[str, list[float]] = {"months": [float(m) for m in months]}
    for k in PERCENTILE_KEYS:
        fan[f"fdv_{k}"] = []
        fan[f"rev_{k}"] = []
    fdv_cols = np.percentile(sim["running_fdv"], _PCT_VALUES, axis=0)
    rev_cols = np.percentile(sim["cum_rev"], _PCT_VALUES, axis=0)
    for i, k in enumerate(PERCENTILE_KEYS):
        fan[f"fdv_{k}"] = [float(x) for x in fdv_cols[i]]
        fan[f"rev_{k}"] = [float(x) for x in rev_cols[i]]

    crossover: dict[str, Any] = {
        k: _crossover_summary(v, horizon) for k, v in sim["first_crossover_by_regime"].items()
    }
    for k, nf in sim["net_float_by_regime"].items():
        crossover[k]["p_deflationary_at_horizon"] = float((nf[:, -1] <= 0.0).mean())
        crossover[k]["median_cum_net_float_change_near"] = float(np.median(nf.sum(axis=1)))
    crossover["basis"] = calibration["crossover_basis"]
    crossover["deterministic_crossover_month"] = det["crossover_month"]
    crossover["note"] = (
        "Path probabilities reflect the dispersion of the volume and price GBMs (a path crosses when "
        "holder revenue / price outruns issuance); compare with deterministic_crossover_month (the expected-volume "
        "path) and with supply_physics.breakeven_daily_volume_usd before quoting a crossover."
    )

    calibration = dict(calibration)
    calibration["deterministic_base"] = {
        "fdv_total": det["fdv_total"], "fdv_ex_monetary": det["fdv_ex_monetary"],
        "engine_clearinghouse": det["engine_clearinghouse"], "engine_confidential": det["engine_confidential"],
        "engine_monetary": det["engine_monetary"], "implied_price": det["implied_price"],
        "crossover_month": det["crossover_month"], "cum_holder_revenue_usd": det["cum_holder_revenue_usd"],
    }
    calibration["monthly_tau_pub_bps"] = det["monthly_tau_pub_bps"]
    calibration["monthly_tau_conf_bps"] = det["monthly_tau_conf_bps"]
    calibration["mc_mean_fdv"] = float(sim["fdv"].mean())
    calibration["mc_mean_fdv_note"] = (
        "mean over paths; exceeds the P50 by lognormal convexity (mean-matching GBM: the deterministic path is the EXPECTED volume "
        "path, the P50 path sits below it, see gbm_convention) and is not a base case"
    )
    calibration["mc_mean_to_p50_fdv"] = float(sim["fdv"].mean() / fdv_pct["p50"]) if fdv_pct["p50"] > 0 else None
    # Sampled terminal public volume: mean should track the analytic volume_terminal_mean_usd_day, median the analytic median.
    calibration["volume_terminal_mean_usd_day_mc"] = float(sim["v_pub"][:, -1].mean())
    calibration["volume_terminal_median_usd_day_mc"] = float(np.median(sim["v_pub"][:, -1]))
    calibration["engine_shares_on_median_total_path"] = _engine_shares_on_median_path(sim)
    calibration["engine_percentiles_note"] = (
        "engine percentiles are taken per engine over paths and are NOT additive: the P50s of the three engines do not sum to the "
        "total P50; engine_shares_on_median_total_path is the additive decomposition of the one path whose total is the sample median"
    )
    calibration["supply_at_horizon_used"] = float(supply_h)

    return SotpValuation(
        seed=int(seed),
        n_paths=int(n_paths),
        horizon_months=horizon,
        discount_rate=float(inputs["discount_rate"]),
        inputs=labeled,
        engines=engines,
        fdv_percentiles=fdv_pct,
        price_percentiles=price_pct,
        fdv_ex_monetary_percentiles=percentiles(sim["e1"] + sim["e2"]),
        current_fdv_usd=current_fdv,
        upside_p50_pct=(fdv_pct["p50"] / current_fdv - 1.0) * 100.0 if current_fdv > 0 else float("nan"),
        fan_chart=fan,
        crossover_month_distribution=crossover,
        sensitivity_heatmap=_heatmap(inputs),
        calibration=calibration,
    )
