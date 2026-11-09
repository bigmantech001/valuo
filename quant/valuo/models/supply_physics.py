"""Supply physics: issuance regimes, NEAR sinks, breakeven volume and monthly float trajectories.

Pure numpy, deterministic, no network. Every formula is written out here because
``web/src/lib/quantClient.ts`` mirrors this module for the slider recalculation; the two must agree
to floating-point precision on identical inputs.

Notation
    S       total supply (NEAR)
    i       annual protocol max_inflation_rate (ratio; live 1/40 = 0.025)
    t       protocol_reward_rate = treasury share of issuance (ratio; live 0.0)
    f       issuance realization factor = measured annual issuance / nominal (i x S); 1.0 when unmeasured
    P       NEAR price (USD)
    V       daily NEAR Intents volume (USD)
    tau     gross take rate on volume (bps) collected by frontends + protocol
    alpha   capture ratio = holders revenue / gross fees (share swept to NEAR revenue wallets)
    G, L    L1 gas burn and net new NEP storage-stake lock (NEAR/day)
    D       days per model month = 365.25 / 12 = 30.4375
    g       public volume growth (ratio, year over year)

Formulas (all implemented by the public helpers below)
    daily issuance            I(S, i)            = S x i / 365.25                    (x f when realized)
    buyback sink              B(V, tau, alpha, P) = V x (tau / 1e4) x alpha / P
    net float change          dS                 = I - (B + G + L)                   (NEAR/day; <= 0 = net deflation)
    breakeven volume          V*                 = max(0, I - G - L) x P / ((tau / 1e4) x alpha)
    glidepath, month m (0-based)  i_m            = i_0 + (i_T - i_0) x min(m, M_g) / M_g
    status quo / custom cap   i_m                = i_0  /  i_cap                     (constant)
    trajectory step (m = 0..M-1)
        growth factor          r_m   = 1 + i_m x f x D / 365.25
        supply at month start  S_m   = S_0 x prod_{k<m} r_k
        gross issuance         E_m   = S_m x (r_m - 1)
        volume                 V_m   = V_0 x (1 + g)^(m / 12)
        buyback                B_m   = V_m x (tau / 1e4) x alpha / P_m x D
        gas burn, state lock   G_m   = G x D ;  L_m = L x D                            (held at measured run-rate)
        net float change       N_m   = E_m - (B_m + G_m + L_m)
    crossover month           first 1-based m with N_m <= 0 (flow turns deflationary); None if never
    cumulative crossover      first 1-based m with sum_{k<=m} N_k <= 0
    nominal staking APR       i x (1 - t) / staked_ratio
    real staking APR          nominal - i
    buyback accrual APR       B x 365.25 / S                                         (accrues to every holder)
    agent lock                agents x kb_per_agent x storage_near_per_kb

Sources of each input are recorded in ``SupplyPhysics.inputs`` as labeled ``Assumption`` objects
(``source`` = measured | derived | assumption). Missing live inputs are never replaced by invented
numbers: the sink gets zero credit and a warning is appended to the ``warnings`` extra field.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from valuo import assumptions as assumptions_registry
from valuo import config
from valuo.schemas import (
    Assumption,
    IntentsForensics,
    NearOnchainTruth,
    PeerComps,
    Regime,
    SupplyPhysics,
    SupplyTrajectory,
)

__all__ = [
    "DAYS_PER_YEAR",
    "DAYS_PER_MONTH",
    "REGIME_STATUS_QUO",
    "REGIME_SVRN_GLIDEPATH",
    "REGIME_CUSTOM_CAP",
    "daily_issuance_near",
    "inflation_path",
    "daily_sinks_near",
    "net_float_change_near_day",
    "breakeven_daily_volume_usd",
    "trajectory",
    "staking_yield_rows",
    "agent_scale_rows",
    "run_supply_physics",
]

DAYS_PER_YEAR: float = 365.25
DAYS_PER_MONTH: float = DAYS_PER_YEAR / 12.0  # 30.4375; constant month length keeps the TS port trivial

REGIME_STATUS_QUO = "status_quo"
REGIME_SVRN_GLIDEPATH = "svrn_glidepath"
REGIME_CUSTOM_CAP = "custom_cap"

AGENT_COUNTS: tuple[float, ...] = (1e5, 1e6, 1e7)
KB_PER_AGENT_OPTIONS: tuple[float, ...] = (5.0, 20.0, 50.0)

# Measured issuance should sit within a few percent of nominal (epoch timing jitter); a larger gap
# points at a mismeasured epoch boundary and is surfaced as a warning without overriding the data.
_REALIZATION_WARN_BAND = 0.15


# ============================================================================ pure helpers
def daily_issuance_near(total_supply_near: float, annual_rate: float) -> float:
    """Gross daily issuance ``I = S x i / 365.25`` (NEAR/day).

    nearcore scales the epoch reward by elapsed wall time over a nominal year, so the annual
    issuance is ``i x S`` regardless of block time; dividing by 365.25 gives the daily rate.
    """
    return float(total_supply_near) * float(annual_rate) / DAYS_PER_YEAR


def inflation_path(
    regime_key: str,
    months: int,
    start_rate: float,
    target_rate: float,
    glide_months: int,
) -> list[float]:
    """Annual inflation rate in force at the start of each model month (length ``months``).

    status_quo      : ``i_m = start_rate`` for every month.
    svrn_glidepath  : linear ``i_m = start + (target - start) x min(m, M_g) / M_g`` with ``m`` 0-based,
                      so ``i_0 = start`` and ``i_m = target`` for all ``m >= M_g`` (then flat).
    custom_cap      : ``i_m = target_rate`` for every month (the slider value).
    """
    if months < 1:
        raise ValueError("months must be >= 1")
    m = np.arange(months, dtype=float)
    if regime_key == REGIME_STATUS_QUO:
        path = np.full(months, float(start_rate))
    elif regime_key == REGIME_SVRN_GLIDEPATH:
        if glide_months < 1:
            raise ValueError("glide_months must be >= 1")
        frac = np.minimum(m, float(glide_months)) / float(glide_months)
        path = float(start_rate) + (float(target_rate) - float(start_rate)) * frac
    elif regime_key == REGIME_CUSTOM_CAP:
        path = np.full(months, float(target_rate))
    else:
        raise ValueError(f"unknown regime {regime_key!r}")
    return [float(x) for x in path]


def daily_sinks_near(
    volume_usd_day: float,
    gross_take_bps: float,
    capture_ratio: float,
    price_usd: float,
    gas_burn_near_day: float,
    state_lock_near_day: float,
) -> dict[str, float]:
    """NEAR removed from float per day: ``{"buyback", "gas_burn", "state_lock", "total"}``.

    ``buyback = V x (tau / 1e4) x alpha / P``; gas burn and state lock pass through unchanged.
    """
    if price_usd <= 0:
        raise ValueError("price_usd must be > 0")
    buyback = float(volume_usd_day) * (float(gross_take_bps) / 1e4) * float(capture_ratio) / float(price_usd)
    gas = float(gas_burn_near_day)
    lock = float(state_lock_near_day)
    return {"buyback": buyback, "gas_burn": gas, "state_lock": lock, "total": buyback + gas + lock}


def net_float_change_near_day(issuance_near_day: float, sinks: Mapping[str, float]) -> float:
    """``dS = I - sinks["total"]`` (NEAR/day). Negative means the float shrinks."""
    return float(issuance_near_day) - float(sinks["total"])


def breakeven_daily_volume_usd(
    issuance_near_day: float,
    gas_burn: float,
    state_lock: float,
    price: float,
    gross_take_bps: float,
    capture_ratio: float,
) -> float:
    """Daily volume ``V*`` at which ``dS = 0``: ``V* = max(0, I - G - L) x P / ((tau / 1e4) x alpha)``.

    Returns 0 when gas burn and state lock alone already exceed issuance. Raises when the buyback
    channel is closed (``tau x alpha <= 0``), since no finite volume can then offset issuance.
    """
    take = (float(gross_take_bps) / 1e4) * float(capture_ratio)
    if take <= 0:
        raise ValueError("gross_take_bps x capture_ratio must be > 0 for a finite breakeven volume")
    if price <= 0:
        raise ValueError("price must be > 0")
    residual = max(0.0, float(issuance_near_day) - float(gas_burn) - float(state_lock))
    return residual * float(price) / take


def trajectory(
    regime_key: str,
    inflation_path_annual: Sequence[float],
    total_supply_near: float,
    daily_volume_usd: float,
    gross_take_bps: float,
    capture_ratio: float,
    price_usd: float,
    gas_burn_near_day: float,
    state_lock_near_day: float,
    *,
    realization_factor: float = 1.0,
    volume_growth_yoy: float = 0.0,
    price_path: Sequence[float] | None = None,
) -> SupplyTrajectory:
    """Monthly float accounting over ``len(inflation_path_annual)`` months (see module formulas).

    Supply compounds with gross issuance only (``S_{m+1} = S_m + E_m``); gas burn reduces total
    supply by ~0.003%/yr and buybacks move tokens to revenue wallets without burning, so neither
    enters the issuance base. Buybacks use ``price_path[m]`` when supplied, else constant spot.
    Non-buyback sinks are held at their measured run-rate (conservative: no growth credit).
    """
    rates = np.asarray(inflation_path_annual, dtype=float)
    months = rates.shape[0]
    if months < 1:
        raise ValueError("inflation_path_annual must have at least one month")
    if price_path is None:
        prices = np.full(months, float(price_usd))
    else:
        prices = np.asarray(price_path, dtype=float)
        if prices.shape[0] != months:
            raise ValueError("price_path length must equal the number of months")
    if np.any(prices <= 0):
        raise ValueError("prices must be > 0")

    r = 1.0 + rates * float(realization_factor) * DAYS_PER_MONTH / DAYS_PER_YEAR
    supply_start = float(total_supply_near) * np.concatenate(([1.0], np.cumprod(r)[:-1]))
    issuance = supply_start * (r - 1.0)

    m = np.arange(months, dtype=float)
    volume = float(daily_volume_usd) * np.power(1.0 + float(volume_growth_yoy), m / 12.0)
    buyback = volume * (float(gross_take_bps) / 1e4) * float(capture_ratio) / prices * DAYS_PER_MONTH
    gas = np.full(months, float(gas_burn_near_day) * DAYS_PER_MONTH)
    lock = np.full(months, float(state_lock_near_day) * DAYS_PER_MONTH)
    net = issuance - (buyback + gas + lock)

    flow_cross = np.flatnonzero(net <= 0)
    cum_cross = np.flatnonzero(np.cumsum(net) <= 0)
    supply_end = float(supply_start[-1] * r[-1])

    return SupplyTrajectory(
        regime=regime_key,
        months=[int(x) for x in range(1, months + 1)],
        gross_issuance_cum=np.cumsum(issuance).tolist(),
        buyback_cum=np.cumsum(buyback).tolist(),
        gas_burn_cum=np.cumsum(gas).tolist(),
        state_lock_cum=np.cumsum(lock).tolist(),
        net_float_change_cum=np.cumsum(net).tolist(),
        crossover_month=int(flow_cross[0]) + 1 if flow_cross.size else None,
        daily_issuance_start=float(issuance[0] / DAYS_PER_MONTH),
        daily_issuance_end=float(issuance[-1] / DAYS_PER_MONTH),
        # extras (OpenModel): kept for the chart tooltips and the invariant tests
        monthly_net_float_change=net.tolist(),
        cumulative_crossover_month=int(cum_cross[0]) + 1 if cum_cross.size else None,
        supply_end_near=supply_end,
        volume_growth_yoy=float(volume_growth_yoy),
        daily_volume_usd_start=float(volume[0]),
        daily_volume_usd_end=float(volume[-1]),
        realization_factor=float(realization_factor),
    )


def staking_yield_rows(
    regime_terminal_rates: Mapping[str, float],
    *,
    treasury_share: float,
    staked_supply_ratio: float,
    total_supply_near: float,
    buyback_near_per_day: float,
) -> list[dict[str, Any]]:
    """Per regime (at its terminal inflation rate): validator and holder yields.

    nominal_staking_apr          = i x (1 - t) / staked_ratio   (minted NEAR per staked NEAR)
    real_staking_apr             = nominal - i                   (staker gain net of dilution)
    buyback_accrual_apr          = B x 365.25 / S                (float removed per unit of supply)
    real_staking_apr_with_buyback = real + accrual
    real_non_staker_apr          = -i + accrual                  (dilution borne by an unstaked holder)
    """
    if staked_supply_ratio <= 0:
        raise ValueError("staked_supply_ratio must be > 0")
    accrual = float(buyback_near_per_day) * DAYS_PER_YEAR / float(total_supply_near)
    rows: list[dict[str, Any]] = []
    for regime, rate in regime_terminal_rates.items():
        i = float(rate)
        nominal = i * (1.0 - float(treasury_share)) / float(staked_supply_ratio)
        real = nominal - i
        rows.append(
            {
                "regime": regime,
                "inflation_rate": i,
                "nominal_staking_apr": nominal,
                "real_staking_apr": real,
                "buyback_accrual_apr": accrual,
                "real_staking_apr_with_buyback": real + accrual,
                "real_non_staker_apr": -i + accrual,
                "daily_issuance_near": daily_issuance_near(total_supply_near, i),
            }
        )
    return rows


def agent_scale_rows(
    kb_per_agent_default: float,
    storage_near_per_kb: float,
    *,
    daily_issuance_near_: float | None = None,
    total_supply_near: float | None = None,
    agent_counts: Sequence[float] = AGENT_COUNTS,
    kb_options: Sequence[float] = KB_PER_AGENT_OPTIONS,
) -> list[dict[str, Any]]:
    """Permanent state-lock from agent vaults: ``locked = agents x kb_per_agent x storage_near_per_kb``.

    Grid of ``agent_counts x kb_options`` (the labeled default kb is added if absent). Rows carry
    ``days_of_issuance_absorbed = locked / I`` and ``share_of_supply = locked / S`` when those are given.
    """
    kbs = list(dict.fromkeys([float(k) for k in kb_options] + [float(kb_per_agent_default)]))
    rows: list[dict[str, Any]] = []
    for agents in agent_counts:
        for kb in kbs:
            locked = float(agents) * kb * float(storage_near_per_kb)
            row: dict[str, Any] = {
                "agents": int(agents),
                "kb_per_agent": kb,
                "locked_near": locked,
                "is_default_kb": kb == float(kb_per_agent_default),
            }
            if daily_issuance_near_ and daily_issuance_near_ > 0:
                row["days_of_issuance_absorbed"] = locked / float(daily_issuance_near_)
            if total_supply_near and total_supply_near > 0:
                row["share_of_supply"] = locked / float(total_supply_near)
            rows.append(row)
    return rows


# ============================================================================ input resolution
def _labeled(key: str, value: float, unit: str, source: str, justification: str, low: float | None = None, high: float | None = None) -> Assumption:
    v = float(value)
    return Assumption(
        key=key, value=v, unit=unit,
        low=v if low is None else float(low), high=v if high is None else float(high),
        source=source, justification=justification,  # type: ignore[arg-type]
    )


def _num(mapping: Mapping[str, Any] | None, *keys: str) -> float | None:
    """First finite numeric value among ``keys`` in ``mapping`` (None when absent)."""
    if not mapping:
        return None
    for k in keys:
        v = mapping.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and np.isfinite(v):
            return float(v)
    return None


def _peer(comps: PeerComps | None, slug: str):
    """Find a PeerComp by slug in ``peers`` or the collector's extra ``near_components`` list.

    comps.py keeps the NEAR L1 gas row (slug "near") and the near-intents row out of ``peers`` so
    the peer medians exclude NEAR; they are published under ``near_components`` instead.
    """
    if comps is None:
        return None
    components = getattr(comps, "near_components", None) or []
    for p in [*comps.peers, *components]:
        if getattr(p, "slug", None) == slug:
            return p
    return None


def _resolve_price(forensics: IntentsForensics, comps: PeerComps | None, override: float | None) -> tuple[float, str]:
    """NEAR spot, fallback chain: explicit kwarg -> nearstats price.currentUsd -> coins.llama.fi (comps) -> NearBlocks /stats near_price.

    Three independent hosts, so a nearstats outage never aborts the run; the source used is recorded in
    ``inputs.near_price_usd.justification`` and the SOTP reuses the same number.
    """
    if override is not None and override > 0:
        return float(override), "caller-supplied price_usd"
    p = _num(forensics.price, "current_usd")
    if p is not None and p > 0:
        return p, "nearstats price.currentUsd via intents_forensics.price.current_usd"
    for cand in (comps.near_combined if comps is not None else None, _peer(comps, "near")):
        if cand is not None and cand.price_usd is not None and cand.price_usd > 0:
            return float(cand.price_usd), f"comps peer {cand.slug!r} price_usd ({cand.price_source or 'coins.llama.fi'}; nearstats price unavailable)"
    p = _num(forensics.price, "price_nearblocks_usd")
    if p is not None and p > 0:
        return p, "NearBlocks /v1/stats near_price via intents_forensics.price.price_nearblocks_usd (nearstats and coins.llama.fi unavailable)"
    raise ValueError(
        "NEAR price unavailable from nearstats (forensics.price.current_usd), coins.llama.fi (comps NEAR price_usd) and NearBlocks "
        "/stats (forensics.price.price_nearblocks_usd); cannot convert USD sinks to NEAR"
    )


def _resolve_issuance(truth: NearOnchainTruth, warnings: list[str]) -> tuple[float, float, str, str]:
    """(annual issuance NEAR, realization factor f, source, note). Measured per-epoch minting wins."""
    nominal = truth.total_supply_near * truth.max_inflation_rate
    measured = truth.epoch_issuance.implied_annual_issuance_near
    if measured is not None and np.isfinite(measured) and measured > 0:
        f = measured / nominal if nominal > 0 else 1.0
        if abs(f - 1.0) > _REALIZATION_WARN_BAND:
            warnings.append(
                f"measured annual issuance {measured:,.0f} NEAR deviates {100 * (f - 1):+.1f}% from nominal {nominal:,.0f}; "
                "check the epoch-boundary measurement"
            )
        note = (
            f"minted_per_epoch {truth.epoch_issuance.minted_per_epoch_near} NEAR x epochs_per_year "
            f"{truth.epoch_issuance.epochs_per_year} from total_supply jumps at epoch starts "
            f"{truth.epoch_issuance.prev_epoch_start_height} -> {truth.epoch_issuance.epoch_start_height}"
        )
        return float(measured), float(f), "measured", note
    warnings.append("per-epoch issuance measurement unavailable; using nominal max_inflation_rate x total_supply")
    return float(nominal), 1.0, "derived", "nominal: max_inflation_rate x total_supply (epoch measurement unavailable)"


def _resolve_fees(forensics: IntentsForensics, warnings: list[str]) -> tuple[float, float, float, str, str, str]:
    """(daily volume USD, gross take bps, capture ratio, take-source, alpha-source, volume-source), ONE window.

    intents_forensics publishes the canonical take-rate window (``fees.take_rate_window``: the last 30 complete
    UTC days common to the DefiLlama fees, revenue, holders-revenue and volume daily charts) and the ratios
    computed on it: ``gross_take_bps``, ``holders_capture_ratio`` / ``capture_ratio`` and ``volume_30d_usd``.
    This model CONSUMES those fields rather than recomputing them, so the memo cannot show two different
    take rates for the same window; the sums are only used as a fallback when a ratio is absent. ``V x tau x
    alpha / P`` therefore reproduces holders_revenue / window_days / P exactly. Only when the aligned volume
    is absent does V fall back to the nearstats 30d total (warned).
    """
    fees = forensics.fees or {}
    window = str(fees.get("take_rate_window") or "30d")
    days = _num(fees, "take_rate_window_days") or 30.0
    vol30 = _num(fees, "volume_30d_usd")
    if vol30 is not None and vol30 > 0:
        v_src = f"intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window ({window})"
    else:
        vol30 = _num(forensics.volume, "30d", "volume30dUsd")
        v_src = "nearstats intents.totals.volume30dUsd / 30 (canonical window volume unavailable)"
        days = 30.0
        if vol30 is None or vol30 <= 0:
            raise ValueError("30d intents volume unavailable (fees.volume_30d_usd and volume['30d'] are null); supply physics needs a live volume")
        warnings.append("daily volume taken from nearstats 30d total; fees.volume_30d_usd (canonical window) unavailable")
    v_day = vol30 / days

    gross30 = _num(fees, "gross_fees_30d_usd")
    holders30 = _num(fees, "holders_revenue_30d_usd")
    if holders30 is None:
        holders30 = _num(fees, "net_revenue_30d_usd")
        if holders30 is not None:
            warnings.append("holders_revenue_30d_usd missing; buyback sink uses net_revenue_30d_usd (DefiLlama dailyRevenue)")

    tau = _num(fees, "gross_take_bps")
    if tau is not None and tau > 0:
        tau_src = f"intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window ({window})"
    elif gross30 is not None and gross30 > 0:
        tau = gross30 / vol30 * 1e4
        tau_src = f"recomputed: fees.gross_fees_30d_usd / fees.volume_30d_usd x 1e4, same window ({window}); fees.gross_take_bps was null"
    else:
        raise ValueError("gross take unavailable (fees.gross_take_bps and fees.gross_fees_30d_usd are null)")

    alpha = _num(fees, "holders_capture_ratio", "capture_ratio")
    if alpha is not None:
        alpha_src = f"intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window ({window})"
    elif holders30 is not None and gross30 is not None and gross30 > 0:
        alpha = holders30 / gross30
        alpha_src = f"recomputed: fees.holders_revenue_30d_usd / fees.gross_fees_30d_usd, same window ({window}); fees.capture_ratio was null"
    else:
        warnings.append("capture ratio unavailable (no holders revenue, no capture_ratio); buyback sink credited 0")
        alpha, alpha_src = 0.0, "unavailable -> 0 (no buyback credit)"
    return v_day, float(tau), float(alpha), tau_src, alpha_src, v_src


def _resolve_gas_burn(truth: NearOnchainTruth, comps: PeerComps | None, price: float, warnings: list[str]) -> tuple[float, str, str, dict[str, float | None]]:
    """(gas burn NEAR/day, source, note, cross-checks). On-chain within-epoch drift beats DefiLlama."""
    ep = truth.epoch_issuance
    onchain: float | None = None
    if ep.net_burn_per_epoch_near is not None and ep.epochs_per_year is not None and ep.epochs_per_year > 0:
        onchain = -float(ep.net_burn_per_epoch_near) * float(ep.epochs_per_year) / DAYS_PER_YEAR
    llama: float | None = None
    near_chain = _peer(comps, "near")
    if near_chain is not None and near_chain.revenue_30d_usd is not None and near_chain.revenue_30d_usd > 0:
        llama = float(near_chain.revenue_30d_usd) / 30.0 / price
    checks = {"gas_burn_onchain_near_day": onchain, "gas_burn_defillama_near_day": llama}

    if onchain is not None:
        if onchain < 0:
            warnings.append(f"within-epoch supply drift is positive ({-onchain:,.1f} NEAR/day); gas burn credited 0")
            return 0.0, "derived", "on-chain drift positive; no burn credit", checks
        return onchain, "measured", "-net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch)", checks
    if llama is not None:
        warnings.append("on-chain epoch burn unavailable; gas burn uses DefiLlama near chain dailyRevenue (70% of gas fees burned) / price")
        return llama, "derived", "DefiLlama near chain revenue_30d_usd / 30 / price", checks
    warnings.append("gas burn unavailable from both RPC epoch drift and DefiLlama; credited 0")
    return 0.0, "derived", "unavailable -> 0 (no burn credit)", checks


def _resolve_state_lock(truth: NearOnchainTruth, assumptions: Mapping[str, Assumption], warnings: list[str]) -> tuple[float, Assumption]:
    measured = truth.measured_state_lock_growth_near_per_day
    if measured is not None and np.isfinite(measured):
        sinks = ", ".join(s.account_id for s in truth.tracked_sinks if s.growth_locked_near_per_day is not None) or "tracked sinks"
        return float(measured), _labeled(
            "state_lock_growth_near_per_day", measured, "NEAR_per_day", "measured",
            f"archival view_account storage_usage growth across {sinks} x storage_amount_per_byte",
        )
    fallback = assumptions_registry.value("state_lock_growth_fallback_near_per_day", assumptions)
    base = assumptions.get("state_lock_growth_fallback_near_per_day") or assumptions_registry.get("state_lock_growth_fallback_near_per_day")
    warnings.append(
        f"state-lock growth not measured (archival unavailable); using labeled fallback {fallback:g} NEAR/day"
    )
    return float(fallback), base.model_copy(update={"key": "state_lock_growth_near_per_day"})


# ============================================================================ orchestration
def run_supply_physics(
    truth: NearOnchainTruth,
    forensics: IntentsForensics,
    comps: PeerComps,
    assumptions: Mapping[str, Assumption],
    *,
    price_usd: float | None = None,
    custom_cap: float | None = None,
    competitive_ceiling_bps: float | None = None,
    competitive_ceiling_note: str | None = None,
    horizon_months: int = config.HORIZON_MONTHS,
) -> SupplyPhysics:
    """Build the deterministic supply model (MODEL_DESIGN section 4.1).

    Regimes: ``status_quo`` (live max_inflation_rate flat), ``svrn_glidepath`` (linear to the
    ``svrn_target_inflation`` assumption over ``svrn_glidepath_months``), and ``custom_cap`` when a
    slider value is passed. ``trajectories`` hold volume at the trailing-30d run-rate (price at spot);
    the extra ``growth_trajectories`` apply the ``public_volume_growth_yoy`` assumption. Breakeven
    volumes use the live gross take and capture ratio, and again at ``competitive_ceiling_bps``
    (``competitive_ceiling_note`` names the venues behind that median, e.g. "Relay 3.0 bps, LI.FI 25.0 bps").
    """
    warnings: list[str] = []
    inputs: dict[str, Assumption] = {}

    S = float(truth.total_supply_near)
    i0 = float(truth.max_inflation_rate)
    t = float(truth.protocol_reward_rate)
    inputs["total_supply_near"] = _labeled("total_supply_near", S, "NEAR", "measured", f"RPC block header total_supply at height {truth.block_height}")
    inputs["current_max_inflation_rate"] = _labeled("current_max_inflation_rate", i0, "ratio_annual", "measured", "RPC EXPERIMENTAL_protocol_config.max_inflation_rate")
    inputs["treasury_share"] = _labeled("treasury_share", t, "ratio", "measured", "RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this)")
    inputs["staked_supply_ratio"] = _labeled("staked_supply_ratio", truth.staked_supply_ratio, "ratio", "measured", f"RPC validators current stake / total_supply ({truth.active_validator_count} validators)")

    annual, f, iss_src, iss_note = _resolve_issuance(truth, warnings)
    I_now = annual / DAYS_PER_YEAR
    inputs["annual_issuance_near"] = _labeled("annual_issuance_near", annual, "NEAR_per_year", iss_src, iss_note)
    inputs["issuance_realization_factor"] = _labeled(
        "issuance_realization_factor", f, "ratio", iss_src,
        "measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path",
    )

    P, price_src = _resolve_price(forensics, comps, price_usd)
    inputs["near_price_usd"] = _labeled("near_price_usd", P, "USD", "measured", price_src)

    v_day, tau, alpha_live, tau_src, alpha_src, v_src = _resolve_fees(forensics, warnings)
    inputs["daily_volume_usd"] = _labeled("daily_volume_usd", v_day, "USD_per_day", "measured", v_src)
    inputs["gross_take_bps"] = _labeled("gross_take_bps", tau, "bps", "measured", tau_src)
    override = assumptions_registry.value("buyback_capture_ratio_override", assumptions)
    if override >= 0:
        alpha = float(override)
        base = assumptions.get("buyback_capture_ratio_override") or assumptions_registry.get("buyback_capture_ratio_override")
        inputs["capture_ratio"] = base.model_copy(update={"key": "capture_ratio", "value": alpha, "low": 0.0, "high": 1.0})
        warnings.append(f"capture ratio overridden by assumption to {alpha:.3f} (live {alpha_live:.3f})")
    else:
        alpha = alpha_live
        inputs["capture_ratio"] = _labeled("capture_ratio", alpha, "ratio", "measured", alpha_src)

    G, gas_src, gas_note, gas_checks = _resolve_gas_burn(truth, comps, P, warnings)
    inputs["gas_burn_near_per_day"] = _labeled("gas_burn_near_per_day", G, "NEAR_per_day", gas_src, gas_note)
    L, lock_assumption = _resolve_state_lock(truth, assumptions, warnings)
    inputs["state_lock_growth_near_per_day"] = lock_assumption

    for key in ("svrn_target_inflation", "svrn_glidepath_months", "kb_per_agent_vault", "public_volume_growth_yoy"):
        inputs[key] = (assumptions.get(key) or assumptions_registry.get(key)).model_copy()
    target = inputs["svrn_target_inflation"].value
    glide = int(round(inputs["svrn_glidepath_months"].value))
    growth = inputs["public_volume_growth_yoy"].value
    if competitive_ceiling_bps is not None and competitive_ceiling_bps > 0:
        # Derived, not measured: a statistic over quotes (median across cross-VM cells of the BEST competitor's friction,
        # i.e. the lowest-friction venue in each cell), not an observed fee schedule; it depends on which venues were
        # polled. It is NOT the median of all competitor frictions: a higher-fee venue in the set is not the ceiling.
        venues = f" (per-venue medians: {competitive_ceiling_note})" if competitive_ceiling_note else ""
        inputs["competitive_fee_ceiling_bps"] = _labeled(
            "competitive_fee_ceiling_bps", competitive_ceiling_bps, "bps", "derived",
            f"median over cross-VM cells of the best competitor's friction{venues}; the lowest-friction venue polled is the "
            "binding ceiling, a higher venue fee is not; depends on the venue set and clips polled, not an observed fee "
            "schedule; the level a public take-rate cannot exceed long-run",
        )
    if custom_cap is not None:
        inputs["custom_cap_inflation"] = _labeled(
            "custom_cap_inflation", custom_cap, "ratio_annual", "assumption",
            "web slider governance cap scenario (0.5%-3.0%)", low=0.005, high=0.03,
        )

    # --- regimes: key -> (label, rate path, terminal rate)
    regimes: list[tuple[str, str, list[float], float]] = [
        (REGIME_STATUS_QUO, f"Status quo ({i0:.2%} max inflation, flat)", inflation_path(REGIME_STATUS_QUO, horizon_months, i0, i0, glide), i0),
        (REGIME_SVRN_GLIDEPATH, f"SVRN glidepath ({i0:.2%} -> {target:.2%} linear over {glide} months, then flat)", inflation_path(REGIME_SVRN_GLIDEPATH, horizon_months, i0, target, glide), target),
    ]
    if custom_cap is not None:
        regimes.append((REGIME_CUSTOM_CAP, f"Custom cap ({custom_cap:.2%} flat)", inflation_path(REGIME_CUSTOM_CAP, horizon_months, i0, custom_cap, glide), float(custom_cap)))

    sinks_now = daily_sinks_near(v_day, tau, alpha, P, G, L)
    breakeven: dict[str, float] = {}
    breakeven_ceiling: dict[str, float] = {}
    for key, _label, _path, terminal in regimes:
        issuance_terminal = daily_issuance_near(S, terminal) * f
        try:
            breakeven[key] = breakeven_daily_volume_usd(issuance_terminal, G, L, P, tau, alpha)
        except ValueError as exc:
            warnings.append(f"breakeven volume undefined for {key}: {exc}")
        if competitive_ceiling_bps is not None and competitive_ceiling_bps > 0:
            try:
                breakeven_ceiling[key] = breakeven_daily_volume_usd(issuance_terminal, G, L, P, competitive_ceiling_bps, alpha)
            except ValueError as exc:
                warnings.append(f"breakeven volume at ceiling undefined for {key}: {exc}")

    common = dict(total_supply_near=S, daily_volume_usd=v_day, gross_take_bps=tau, capture_ratio=alpha, price_usd=P,
                  gas_burn_near_day=G, state_lock_near_day=L, realization_factor=f)
    trajectories = [trajectory(key, path, **common) for key, _l, path, _t in regimes]
    growth_trajectories = [trajectory(key, path, volume_growth_yoy=growth, **common) for key, _l, path, _t in regimes]

    staking = staking_yield_rows(
        {key: terminal for key, _l, _p, terminal in regimes},
        treasury_share=t, staked_supply_ratio=truth.staked_supply_ratio, total_supply_near=S,
        buyback_near_per_day=sinks_now["buyback"],
    )
    agents = agent_scale_rows(
        inputs["kb_per_agent_vault"].value, truth.storage_near_per_kb,
        daily_issuance_near_=I_now, total_supply_near=S,
    )

    holders30 = _num(forensics.fees, "holders_revenue_30d_usd", "net_revenue_30d_usd")
    window_days = _num(forensics.fees, "take_rate_window_days") or 30.0
    cross_checks: dict[str, float | None] = {
        **gas_checks,
        "buyback_from_holders_revenue_near_day": holders30 / window_days / P if holders30 is not None else None,
        "take_rate_window_days": window_days,
        "gross_take_bps_from_sums": (
            _num(forensics.fees, "gross_fees_30d_usd") / _num(forensics.fees, "volume_30d_usd") * 1e4
            if _num(forensics.fees, "gross_fees_30d_usd") is not None and (_num(forensics.fees, "volume_30d_usd") or 0) > 0 else None
        ),
        "net_take_bps_published": _num(forensics.fees, "net_take_bps"),
        "volume_30d_nearstats_usd": _num(forensics.volume, "30d"),
        "volume_30d_aligned_window_usd": _num(forensics.fees, "volume_30d_usd"),
        "buyback_identity_near_day": sinks_now["buyback"],
        "nominal_annual_issuance_near": S * i0,
        "measured_annual_issuance_near": truth.epoch_issuance.implied_annual_issuance_near,
        "nominal_daily_issuance_near": daily_issuance_near(S, i0),
        "truth_gross_daily_issuance_near": truth.gross_daily_issuance_near,
    }

    return SupplyPhysics(
        inputs=inputs,
        regimes=[Regime(key=key, label=label, inflation_path_annual=path) for key, label, path, _t in regimes],
        trajectories=trajectories,
        breakeven_daily_volume_usd=breakeven,
        current_daily_sinks_near=sinks_now,
        current_daily_issuance_near=I_now,
        sink_coverage_ratio=sinks_now["total"] / I_now if I_now > 0 else 0.0,
        staking_yield_table=staking,
        agent_scale_table=agents,
        # extras (OpenModel)
        warnings=warnings,
        breakeven_daily_volume_usd_at_ceiling=breakeven_ceiling,
        growth_trajectories=growth_trajectories,
        current_net_float_change_near_day=net_float_change_near_day(I_now, sinks_now),
        cross_checks=cross_checks,
        horizon_months=int(horizon_months),
        days_per_month=DAYS_PER_MONTH,
    )
