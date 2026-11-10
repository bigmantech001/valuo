# Valuo — Model Design & Build Contract

Read `docs/LIVE_ENDPOINT_FACTS.md` first; it overrides stale numbers in `CLAUDE.md`/`README.md`.
This document fixes the modeling decisions and the module contracts so that modules built in parallel fit together.

## 0. Principles (non-negotiable)
1. **Every number in the snapshot is either (a) fetched live with a provenance record, (b) derived arithmetically from (a), or (c) an explicitly labeled assumption with a `source: "assumption"` tag, a default, a plausible range, and a one-line justification.** Assumptions are inputs to sliders; they are never presented as measured.
2. **No fabricated fallbacks.** If a fetch fails after retries, the field is `null` and `status` records the failure. Models must degrade (skip the component, widen uncertainty) and the memo must say what was missing. Never substitute a "typical" value silently.
3. **Determinism.** `numpy.random.default_rng(seed)` with `seed=20261114`; MC results are bit-reproducible for a given snapshot of inputs.
4. **Prose style.** Dragonfly / Electric Capital research memo: terse, numerical, skeptical, no marketing adjectives, no "revolutionize / delve / seamless / unlock / leverage (verb)".
5. Toolchain: Python ≥3.11 via `uv` (`quant/pyproject.toml`, `uv sync`, `uv run …`). Deps: `httpx`, `pydantic>=2`, `numpy`, `scipy`, `duckdb`, `python-dotenv`, `pytest`. Keep it to these unless truly needed.
6. Artifacts live in repo-root `artifacts/` (resolve via `config.ARTIFACTS_DIR` = `Path(__file__).resolve().parents[2] / "artifacts"`, overridable by `VALUO_ARTIFACTS_DIR`). Also persist the raw payloads in `artifacts/raw/<source>__<name>.json` and a DuckDB file `artifacts/valuo.duckdb` with tables `raw_payloads`, `quotes`, `callers`, `mc_percentiles` (DuckDB is a convenience; JSON is canonical).

## 1. Package layout (file ownership — one owner per file during parallel build)
```
quant/
  pyproject.toml, README.md
  valuo/__init__.py            (version)
  valuo/config.py              env-driven endpoints (see .env.example), SEED, PATHS, MC_PATHS=10000, HORIZON_MONTHS=36, timeouts
  valuo/provenance.py          fetch helpers + ProvenanceLedger (see §2)
  valuo/schemas.py             ALL pydantic models (collector outputs, model outputs, Snapshot, Manifest) (see §3)
  valuo/collectors/near_rpc.py           collect_near_rpc(ledger) -> NearOnchainTruth
  valuo/collectors/execution_bench.py    collect_execution_bench(ledger, clips=…, corridors=…) -> ExecutionBenchmark   (async httpx, concurrent)
  valuo/collectors/intents_forensics.py  collect_intents_forensics(ledger) -> IntentsForensics
  valuo/collectors/comps.py              collect_comps(ledger) -> PeerComps
  valuo/models/supply_physics.py         run_supply_physics(truth, forensics, comps, assumptions) -> SupplyPhysics
  valuo/models/sotp_valuation.py         run_sotp(truth, forensics, comps, supply, assumptions, seed, n_paths) -> SotpValuation
  valuo/models/bear_case.py              run_bear_case(base_inputs, base_sotp_fn, live_metrics) -> BearCase
  valuo/assumptions.py         the single registry of labeled assumptions (defaults, ranges, justification) + scenario presets   [owned by foundation]
  valuo/memo_generator.py      render_memo(snapshot, manifest) -> str (Markdown)                                                   [integration]
  valuo/reproduce.py           CLI: python -m valuo.reproduce [--skip-bench] [--paths N] [--seed S] [--no-archival]                 [integration]
  tests/test_<module>.py       per-module unit tests (owner = module owner; must not need network except where marked `@pytest.mark.live`)
  tests/test_invariants.py     the 5 mandated invariant tests, run against artifacts/ (integration)
```
Web (`web/`) is Next.js 15 App Router + TypeScript + Tailwind; see §7.

## 2. Provenance layer (`provenance.py`)
```python
class RawRecord(BaseModel):
    source: str           # "near_rpc" | "oneclick" | "relay" | "lifi" | "across" | "nearstats" | "nearblocks" | "defillama" | "coingecko"
    name: str             # e.g. "block_final", "quote:eth_usdc->sol_usdc:50000", "fees:near-intents:dailyRevenue"
    url: str; method: str; request_body_sha256: str | None
    http_status: int | None; ok: bool; error: str | None
    fetched_at_utc: str   # ISO-8601 Z
    latency_ms: float; bytes: int; sha256: str   # sha256 of the exact raw response bytes
    raw_path: str | None  # artifacts/raw/… relative to repo root
class ProvenanceLedger: records: list[RawRecord]; def add(...); def by_source(...); def summary()
async def fetch_json(client, ledger, *, source, name, method, url, json=None, params=None, headers=None, timeout=20, retries=3, backoff=0.6) -> tuple[Any|None, RawRecord]
def fetch_json_sync(...)  # thin wrapper for collectors that are sync
async def near_rpc_call(client, ledger, method, params, name) -> tuple[Any|None, RawRecord]   # primary→fallback; for block_id queries to GC'd blocks, retries on archival
```
Non-2xx responses are still hashed and recorded (`ok=False`, `error=<message from body if JSON>`), and the parsed JSON body is **returned** so collectors can read `message`/`errorCode`.

## 3. Snapshot schema (`schemas.py`) — the contract
Field names are final; add fields freely but do not rename/remove these.

```python
class Assumption(BaseModel): key: str; value: float; unit: str; low: float; high: float; source: Literal["assumption","derived","measured"]; justification: str

class EpochIssuanceMeasurement(BaseModel):
    epoch_start_height: int; epoch_start_hash: str; prev_epoch_start_height: int | None
    minted_per_epoch_near: float | None          # supply jump at epoch boundary
    epoch_duration_hours: float | None; epochs_per_year: float | None
    net_burn_per_epoch_near: float | None        # within-epoch supply drift (negative = burn)
    implied_annual_issuance_near: float | None; implied_annual_inflation_rate: float | None
    nominal_annual_issuance_near: float          # max_inflation_rate × total_supply
    method_note: str

class ContractSinkSnapshot(BaseModel):
    account_id: str; label: str; has_contract: bool
    storage_bytes: int; storage_locked_near: float; liquid_balance_near: float; total_balance_near: float; staked_near: float
    history: list[dict]            # [{block_height, timestamp_utc, storage_bytes}] from archival (may be empty)
    growth_bytes_per_day: float | None; growth_locked_near_per_day: float | None; growth_window_days: float | None

class NearOnchainTruth(BaseModel):
    block_height: int; block_hash: str; timestamp_ns: int; timestamp_utc: str
    total_supply_near: float; gas_price_yocto: int
    max_inflation_rate: float; protocol_reward_rate: float; storage_amount_per_byte_yocto: int; storage_near_per_kb: float
    num_blocks_per_year: int; epoch_length_blocks: int; protocol_version: int
    active_validator_count: int; total_staked_near: float; staked_supply_ratio: float
    nominal_staking_apr_current: float      # max_inflation_rate × (1 − protocol_reward_rate) / staked_ratio
    nominal_staking_apr_svrn_1_6: float
    gross_daily_issuance_near: float; gross_daily_issuance_svrn_near: float
    epoch_issuance: EpochIssuanceMeasurement
    tracked_sinks: list[ContractSinkSnapshot]; total_state_locked_near: float; measured_state_lock_growth_near_per_day: float | None
    rpc_endpoint_used: str; archival_available: bool

class VenueQuote(BaseModel):
    venue: Literal["1click","relay","lifi","across"]; supported: bool; status: Literal["ok","no_liquidity","unsupported_route","error","skipped"]
    error_message: str | None; amount_in_raw: str; amount_in_usd: float | None
    amount_out_raw: str | None; amount_out_formatted: float | None; amount_out_usd: float | None
    friction_bps_usd: float | None      # (in_usd − out_usd)/in_usd × 1e4
    friction_bps_raw: float | None      # same-asset corridors only
    time_estimate_s: float | None; route_tool: str | None; fee_breakdown_usd: dict[str, float]; latency_ms: float; fetched_at_utc: str; raw_record_sha256: str

class CorridorClipResult(BaseModel):
    corridor_id: str; clip_usd: float; quotes: list[VenueQuote]
    best_competitor: str | None; headroom_bps: float | None   # (out_1click − out_best_competitor) / out_best_competitor × 1e4 on DESTINATION UNITS for the identical raw input (positive = 1Click delivers more); no oracle enters the ranking
    oneclick_rank: int | None; n_venues_ok: int                # rank = 1 + competitors delivering strictly more destination units
    headroom_basis: str | None                                 # "dest_units" (null when the cell is not comparable)
    price_basis: dict                                          # the ONE price every venue's USD friction in the cell is valued at: {source: "oneclick_token_list_oracle" | "median_venue_oracle" | None, dest_price_usd, origin_price_usd, n_venue_oracles}

class Corridor(BaseModel): corridor_id: str; label: str; archetype: Literal["cross_vm","native_btc","evm_l2","native_zec"]; origin: dict; destination: dict; venues_attempted: list[str]

class ExecutionBenchmark(BaseModel):
    ran_at_utc: str; clips_usd: list[float]; corridors: list[Corridor]; results: list[CorridorClipResult]
    headroom_by_archetype_bps: dict[str, float | None]          # median destination-unit headroom per archetype over cells with 1Click ok and ≥1 competitor ok
    competitive_fee_ceiling_bps: float | None                   # median over cross_vm cells of the BEST competitor's friction (the "ceiling" a public take-rate can't exceed); per-venue medians in competitor_friction_by_venue_bps
    # extras: headroom_basis = "dest_units", headroom_definition, usd_friction_basis ("oneclick_token_list_oracle" | "median_venue_oracle"), competitor_friction_by_venue_bps
    oneclick_1y_token_universe: int; oneclick_blockchains: list[str]; summary_note: str

class CallerClass(str, Enum): ai_agent, bridge_relayer, implicit_account, named_account, self_internal, system
class CallerShare(BaseModel): account_id: str; cls: CallerClass; receipts: int; share: float; example_tx_hash: str | None
class IntentsForensics(BaseModel):
    volume: dict          # {allTimeUsd, 24h, 7d, 30d, public30d, confidential30d, confidential_share_30d, weekOverWeek: [...], records: {...}}
    fees: dict            # ONE canonical window: {gross_fees_30d_usd, net_revenue_30d_usd, holders_revenue_30d_usd, volume_30d_usd, gross_take_bps, net_take_bps, capture_ratio,
                          #  holders_capture_ratio, take_rate_window, take_rate_window_days, take_rate_window_start_utc/end_utc, defillama_total30d (cross-check only),
                          #  cumulative_fees_usd, daily_series: [[ts, fees, revenue, volume]]} — sums over the last 30 COMPLETE UTC days common to the fees, revenue,
                          #  holders-revenue and volume daily charts (partial current day excluded); supply_physics and sotp CONSUME these ratios, never recompute them
    confidential_tvl_usd: float | None; confidential_tvl_verified: bool; unique_users_7d: int | None
    price: dict           # {current_usd, fdv_usd, market_cap_usd, circulating_supply, total_supply, perf: {...}, ath_usd, price_nearblocks_usd (third price source)}
    volatility: dict      # {window: "1y", source, n_obs, daily_sigma, annualized_sigma, volume_daily_sigma, volume_annualized_sigma, volume_monthly_sigma, ...}
    callers: list[CallerShare]; hhi_external: float; n_eff_external: float; hhi_all: float; ai_agent_share: float; bridge_share: float; method_mix: dict[str,int]
                          # hhi_external = DEPOSIT / CALLER concentration over external predecessors (bridge token-contract callbacks, direct callers); it is NOT
                          # solver concentration: execute_intents fills are relayer self-receipts (predecessor intents.near). ai_agent_share is a NAME-PATTERN class
                          # (*.ai.near, *.agent.near; escrow.ai.near has no contract) and is graded DERIVED in the scorecard.
    solver_concentration: dict  # {hhi_solver, n_eff_solver, n_fills, n_fills_attributed, n_fills_unresolved, unique_solvers, solvers: [{account_id, fills, share, example_tx_hash}],
                          #  taker_class_mix, attribution_rules, method} — solvers decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id,
                          #  token_diff legs); hhi_solver null when no fill could be attributed. The cartelization trigger reads THIS population.
                          #  Added: hhi_solver_ci90 / n_eff_solver_ci90 (bootstrap, section 4.8), n_fills_atomic, n_fills_hub_legs, settlement_hub
                          #  {account_id, distinct_counterparties, ...}, measurement_status (measured|thin|not_measured), sample_span_s, sample.
    # volume (after confidential_split_guard): confidential_share_status = measured | implausible_fallback | unavailable,
    #   confidential_share_source, confidential_share_reason[], confidential_share_30d_reported, confidential_share_fallback_chain[],
    #   split_reported (raw nearstats fields when the split was rejected). caller_sample adds hhi_external_ci90, n_eff_external_ci90,
    #   hhi_external_ex_ai_agent_ci90, bootstrap_draws, bootstrap_method.
    receipts_sampled: int; pages_fetched: int; lifetime_receipts: int | None; sample_block_range: list[int]; explorer_base: str
class PeerComp(BaseModel): slug: str; symbol: str; fees_30d_usd: float|None; revenue_30d_usd: float|None; fees_1y_usd: float|None; revenue_1y_usd: float|None; fdv_usd: float|None; market_cap_usd: float|None; price_usd: float|None; annualized_fees_usd: float|None; annualized_revenue_usd: float|None; fdv_to_fees: float|None; fdv_to_revenue: float|None; revenue_methodology: str|None
class PeerComps(BaseModel): peers: list[PeerComp]; near_combined: PeerComp; median_fdv_to_revenue_ex_near: float|None; median_fdv_to_fees_ex_near: float|None; fetched_at_utc: str

class Regime(BaseModel): key: str; label: str; inflation_path_annual: list[float]  # 36 monthly values
class SupplyTrajectory(BaseModel): regime: str; months: list[int]; gross_issuance_cum: list[float]; buyback_cum: list[float]; gas_burn_cum: list[float]; state_lock_cum: list[float]; net_float_change_cum: list[float]; crossover_month: int | None; daily_issuance_start: float; daily_issuance_end: float
class SupplyPhysics(BaseModel):
    inputs: dict[str, Assumption]; regimes: list[Regime]; trajectories: list[SupplyTrajectory]
    breakeven_daily_volume_usd: dict[str, float]      # per regime: V* where ΔS ≤ 0 at current price & take & α
    current_daily_sinks_near: dict[str, float]        # {buyback, gas_burn, state_lock, total}
    current_daily_issuance_near: float; sink_coverage_ratio: float   # sinks / issuance
    staking_yield_table: list[dict]                   # per regime: nominal_apr, real_apr (nominal − inflation), with buyback accrual
    agent_scale_table: list[dict]                     # [{agents, kb_per_agent, locked_near}]

class EngineValue(BaseModel): key: Literal["clearinghouse","confidential","monetary"]; label: str; p10: float; p25: float; p50: float; p75: float; p90: float; method: str; assumption_heavy: bool
class SotpValuation(BaseModel):
    seed: int; n_paths: int; horizon_months: int; discount_rate: float
    inputs: dict[str, Assumption]
    engines: list[EngineValue]
    fdv_percentiles: dict[str, float]            # {"p10":…, "p25", "p50", "p75", "p90"} total implied FDV at horizon, discounted to today
    price_percentiles: dict[str, float]          # FDV / projected total supply
    fdv_ex_monetary_percentiles: dict[str, float]
    current_fdv_usd: float; upside_p50_pct: float
    fan_chart: dict[str, list[float]]            # monthly cumulative holder-revenue (or implied FDV) paths p10..p90, length 36
    crossover_month_distribution: dict[str, float]   # {"p_crossover_within_36m": …, "p10_month":…, "p50_month":…, "p90_month":…} under glidepath and status quo
    sensitivity_heatmap: dict                    # {"x": [daily volume usd ×5], "y": [take bps ×5], "fdv_p50": [[…]], "net_deflation": [[bool]]}
    calibration: dict                            # sigmas used, fee-compression lambda, peer multiple used, etc.

class BearScenario(BaseModel): key: str; title: str; narrative: str; perturbations: dict[str, float]; sotp_fdv_p50: float; drawdown_pct: float; price_p50: float; crossover_month: int | None; early_warning_metric: str; current_value: float | None; trigger_threshold: float; trigger_breached: bool | None; monitor_source: str
    # sotp_fdv_p50 keeps its name for compatibility but is the DETERMINISTIC FDV at median inputs (see BearCase.value_basis), not a Monte Carlo percentile.
    # trigger_breached is None (JSON null) when the metric was not measured this run or the sample is too thin (trigger_evaluated False); the memo prints "not measured", never "not breached".
    # extras: trigger_evaluated, trigger_note, secondary_* (headroom condition for solver_cartelization; secondary_breached also bool | None), mc_fdv_p50, fdv_basis
class BearCase(BaseModel): base_fdv_p50: float; scenarios: list[BearScenario]; combined_worst_fdv: float; combined_drawdown_pct: float; falsification_summary: str
    # extras: value_basis = "deterministic at median inputs; not a Monte Carlo percentile"; triggers_breached (count of True), triggers_evaluated, triggers_unevaluated: list[str]

class EvidenceClaim(BaseModel): claim: str; status: Literal["VERIFIED_ON_CHAIN","VERIFIED_LIVE_API","DERIVED","ASSUMPTION","NOT_SUPPORTED"]; value: str; source: str; confidence: str; note: str
class Snapshot(BaseModel):
    schema_version: str; generated_at_utc: str; seed: int; runtime_s: float; valuo_version: str
    near_rpc: NearOnchainTruth; execution_bench: ExecutionBenchmark | None; intents_forensics: IntentsForensics; comps: PeerComps
    supply_physics: SupplyPhysics; sotp: SotpValuation; bear_case: BearCase; evidence_scorecard: list[EvidenceClaim]
    assumptions: list[Assumption]; warnings: list[str]; provenance_summary: dict
    run_config: dict; timings_s: dict[str, float]   # timings include market_implied / sensitivity / relative_value (and history, in memory only)
    market_implied: dict | None    # models/market_implied.run_market_implied(snapshot_dict); null + warning if it raised (section 4.5)
    sensitivity: dict | None       # models/sensitivity.run_sensitivity(snapshot_dict) (section 4.6)
    relative_value: dict | None    # models/relative_value.run_relative_value(snapshot_dict) (section 4.7)
class Manifest(BaseModel): generated_at_utc: str; block_height: int; block_hash: str; snapshot_sha256: str; snapshot_path: str; records: list[RawRecord]; sources: dict[str, int]; failures: int
```

## 4. Modeling decisions

### 4.1 Issuance & supply physics
- **Measured** issuance from epoch-boundary supply jumps (see FACTS §1). Daily gross issuance for the model = `minted_per_epoch × epochs_per_year / 365.25` if measured, else nominal `max_inflation_rate × total_supply / 365.25`. Store both and the gap.
- Treasury share = live `protocol_reward_rate` (currently 0). Validator share = 1 − that.
- Regimes: (1) `status_quo` 2.50% flat; (2) `svrn_glidepath` linear 2.50% → 1.60% over 24 months then flat (governance proposal, `source: assumption`); (3) `custom_cap` used by the web slider (0.5%–3.0%).
- Sinks (NEAR/day): `buyback = V × τ_gross × α / P` where `V`, `τ_gross` (= `fees.gross_take_bps`) and `α` (= `fees.holders_capture_ratio`) are READ from the canonical take-rate window published by `intents_forensics.fees` (same N complete UTC days for fees, holders revenue and volume), so the identity `buyback = holders_revenue_window / window_days / P` holds exactly and the memo cannot show two take rates for one window; `gas_burn = −net_burn_per_epoch × epochs/yr / 365.25` from within-epoch supply drift, cross-checked with DefiLlama near chain dailyRevenue / price (report both, use the on-chain measurement when available); `state_lock = measured growth (archival) across tracked sinks`, else `null` → assumption slider (default 0 with warning, not a made-up number). Price fallback chain: nearstats `price.currentUsd` → coins.llama.fi (comps) → NearBlocks `/stats near_price`; all three null is fatal.
- Breakeven volume `V*` per regime: solve `issuance_daily = V × τ_gross × α / P + gas_burn + state_lock` → `V* = (issuance − gas_burn − state_lock) × P / (τ_gross × α)`. Report with the live canonical-window τ_gross and α, and a second variant at the competitive ceiling from the benchmark. `competitive_fee_ceiling_bps` is labeled `source: derived` (median over cross-VM cells of the BEST competitor's friction, i.e. the lowest-friction venue in each cell: Relay ~3 bps is binding, LI.FI's 25 bps fixed fee is not the ceiling; it depends on the venue set polled, not an observed fee schedule). The label and memo name the binding venue (`memo_generator.competitive_ceiling_note`).
- 36-month trajectories, monthly steps, price held at spot for the deterministic view (MC handles stochastic).
- Staking table: nominal APR = `inflation × (1 − treasury) / staked_ratio`; real APR = nominal − inflation; "buyback-adjusted" adds `buyback_annual / total_supply` as an accrual to all holders.
- Agent-scale table: locked = agents × kb_per_agent / 100; rows for agents ∈ {1e5, 1e6, 1e7} × kb ∈ {5, 20, 50} (labelled assumption).

### 4.2 SOTP + Monte Carlo (`sotp_valuation.py`)
Monthly steps, 36 months, 10,000 paths, `default_rng(20261114)`.
State per path: public daily volume `V_pub`, confidential daily volume `V_conf`, public take `τ_pub`, confidential take `τ_conf`, NEAR price `P` (only used to convert USD buybacks → NEAR units and for supply crossover), storage growth.
- `V_pub`: GBM with the Ito drift correction, `log V_t = log V_0 + t (ln(1+g) − σ²/2) + σ W_t`, so `E[V_t] = V_0 (1+g)^t`: the labeled `public_volume_growth_yoy` is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by `exp(−σ² t / 2)`. `calibration` reports `gbm_convention`, `volume_terminal_mean_usd_day`, `volume_terminal_median_usd_day` (analytic) and their MC-sampled twins. σ_monthly is measured from the DefiLlama daily volume series (non-overlapping 30-day aggregates → monthly log-return σ).
- `V_conf`: starts at the measured confidential share (nearstats `totalsBreakdown`); share drifts toward `confidential_share_target` (assumption); confidential TVL unverified → σ multiplier (assumption, default 1.0) and `assumption_heavy=True` on Engine 2. If the nearstats split is unavailable the confidential volume is 0 with a warning and Engine 2 is reported as NOT MEASURED (`calibration.confidential_engine_measured = False`); nothing is invented and the run does not exit.
- Confidential split guard (`intents_forensics.confidential_split_guard`). A reported 30d confidential share below `confidential_share_plausibility_floor` (1%) is rejected when nearstats' own payload contradicts it (confidential TVL > 0 with ~zero all-time confidential volume, `sourceHealth.confidentialStream.status = ok`, or a split check whose detail says the split is withheld). The public/confidential fields are then nulled (raw kept in `volume.split_reported`), `confidential_share_status = "implausible_fallback"` and `confidential_share_30d` = registry assumption `confidential_share` (0.40, range 0.15–0.60). The SOTP labels this everywhere: `calibration.confidential_share_status = "implausible_fallback"`, `calibration.confidential_share_source` = the forensics source string ("assumption: registry confidential_share ..."), `confidential_share_assumed = True`, `confidential_engine_measured = False`; `sotp.inputs.confidential_share_start` has `source = "assumption"` and a justification starting `assumption:confidential_share`, `sotp.inputs.confidential_share` carries the registry entry; Engine 2's method says NOT MEASURED and that it values an assumed volume; a `sotp:` warning quotes the reported share. The scorecard grades the claim ASSUMPTION (confidence none), `market_implied`'s confidential-share evidence is labelled ASSUMED (`evidence.assumption = true`), and memo / README print NOT MEASURED. Status `unavailable` keeps the older branch (confidential volume 0, Engine 2 zero).
- `τ_pub`: starts at live net take (bps); mean-reverts toward a competitive floor `τ_floor` = max(0, competitive_fee_ceiling_bps from benchmark − 1Click's own friction…) — concretely: floor = `max(0.5 bps, min(live net take, headroom_bps_cross_vm))`; compression speed `λ` (assumption, default 0.03/month, range 0–0.15). If benchmark missing, floor = assumption with warning.
- `τ_conf`: assumption 15–25 bps (default 20), slow compression (λ/3).
- `P`: GBM with σ from 1y daily closes (nearstats price-history, else the coins.llama.fi daily chart), zero drift with the same Ito correction so `E[P_t] = P_0` (we don't forecast price to value the token). If both price series fail, σ = labeled `price_sigma_annual_fallback` (default 1.0, range 0.6–1.6) with a warning, `sotp.inputs.sigma_price_annual.source = "assumption"`. Likewise, if the DefiLlama dexs chart is unavailable (both `volume_monthly_sigma` and `volume_daily_sigma` null; the 30-day volume itself then comes from nearstats), σ_volume = labeled `volume_sigma_monthly_fallback` (default 0.35, range 0.15–0.6) with a warning and `sotp.inputs.sigma_volume_monthly.source = "assumption"`; a single-source chart outage never exits the run.
- Holder revenue per month = (V_pub·τ_pub + V_conf·τ_conf) × 30.4375 × α_capture, with τ the GROSS take and `τ_pub_0` reconciled so month-0 fees equal the canonical-window fees; `current_fdv_usd = spot price × on-chain total_supply` (the CoinGecko FDV relayed by nearstats is kept as `calibration.current_fdv_coingecko_usd`, a cross-check struck at a different instant). Issuance compounds monthly exactly as `supply_physics.trajectory` (`compound_issuance`), so both models report one dilution figure per regime.
- **Engine 1 (clearinghouse)**: PV of 36 months of public holder revenue at `discount_rate` (assumption, default 0.25) + terminal value = year-3 annualized public holder revenue × `terminal_multiple`, discounted. Terminal multiple fallback chain (recorded in `calibration.terminal_multiple_source`): live peer median FDV/revenue ex-NEAR (`derived`; cap 60× / floor 8× guardrails, log when clipped) → peer median FDV/fees ex-NEAR (`derived_fdv_to_fees`, a lower bound, warned) → labeled `terminal_multiple_fallback` (default 30×, range 8–60; `assumption`, loud warning, Engine 1 `assumption_heavy`). A CoinGecko outage never aborts the run.
- **Engine 2 (confidential)**: same on confidential revenue; terminal multiple × `confidential_multiple_haircut` (assumption default 0.7, since TVL unverified).
- **Engine 3 (monetary / supply sink)**: `assumption_heavy=True`. = PV of L1 gas-burn (live near chain revenue, grown with V_pub) valued at the same multiple **plus** the horizon market value of cumulative *new* state-locked NEAR (forced structural demand) `Σ state_lock_t × P_t` — explicitly described as a demand-flow proxy, not an equity cash flow. Report FDV with and without Engine 3.
- Percentiles over paths for each engine and total; implied price = FDV / supply_at_horizon (from the per-path supply trajectory under the **glidepath** regime by default; also compute status quo). Engine percentiles are NOT additive (each is taken over its own paths); `calibration.engine_shares_on_median_total_path` gives the additive decomposition of the path whose total is the sample median, and the memo says so under the engine table.
- Crossover distribution: fraction of paths with net float change ≤ 0 by month m, under both regimes.
- Fan chart: monthly P10/P25/P50/P75/P90 of cumulative holder revenue and of running implied FDV.
- Heatmap 5×5: daily volume ∈ {100M, 250M, 500M, 1B, 1.5B} × net take bps ∈ {2, 6, 10, 14, 18} → deterministic FDV (p50 engine math at those fixed values) and net-deflation boolean under glidepath.
- Expose a pure function `deterministic_sotp(inputs: dict) -> dict` used by heatmap and bear case, and mirror its math in `web/src/lib/quantClient.ts` for sliders (document the formulas in the docstring so the TS port is exact).

### 4.3 Bear case (`bear_case.py`) — four falsification scenarios, each run through `deterministic_sotp` and the supply model
All FDVs here are DETERMINISTIC values at median inputs (`BearCase.value_basis`), never Monte Carlo percentiles; the field name `sotp_fdv_p50` is kept for compatibility only. A trigger whose live metric is null (or whose sample is too thin to grade) has `trigger_breached = null`, is printed "not measured" and is excluded from the "x of y" count.
1. `fee_race_to_zero`: τ_pub (GROSS public take) → 0.01 bps immediately, τ_conf → 5 bps, α unchanged. Early warning: `net_take_bps` (live, canonical window) < 3 bps for 30d.
2. `governance_stalemate`: regime forced to status_quo 2.5% forever; also no SVRN cut. Early warning: no on-chain vote / inflation param unchanged after proposal date (metric: `max_inflation_rate` still 0.025 — currently true, so this scenario is "live" until the vote).
3. `post_incentive_decay`: V_pub −60%, V_conf −70%, confidential TVL −70%. Early warning: 30d volume down >40% from 30d record (`records.max30dUsd`) — compute live.
4. `solver_cartelization`: HHI_solver > 3,500 and headroom → −2 bps (1Click loses). Early warning: live `solver_concentration.hhi_solver` (execute_intents signer population, ≥ 10 attributed fill participations to grade) vs 3,500, secondary `headroom_by_archetype.cross_vm` < 0. The two conditions combine asymmetrically: a breach on either measured condition is a breach; a clear requires the primary HHI_solver to have been graded; an unmeasured or thin HHI_solver with a non-negative (or unmeasured) headroom is `trigger_breached = null` ("not measured"), never "not breached". A graded HHI_solver resting on fewer than `THIN_SOLVER_SAMPLE_FILLS` (30) sampled fills is flagged `sample_thin` and the memo row reads e.g. "not breached (thin sample: 8 fills)". The deposit/caller `hhi_external` is quoted in the note for context only and can never fire this trigger.
   Grading on the interval and the span (added with the bootstrap CI, section 4.8): with `hhi_solver_ci90` present the HHI condition is breached only if the CI lower bound > 3,500 and clear only if the upper bound < 3,500; a straddling CI is `primary_status = "inconclusive"`. Independently, the HHI condition may be graded breached / clear only when the solver sample spans at least `solver_sample_min_span_s` (registry, default 3,600 s, range 900–86,400 s): a window of a few minutes of hub legs is serially correlated (the same solvers quote consecutive blocks) and the bootstrap resamples within that window only, so its CI measures within-window noise, not variation across hours. Below the minimum (or with an unknown span) `primary_status = "short_span"` and, unless the headroom condition breaches on its own, `trigger_breached = null`, `trigger_status = "inconclusive"`; the note quotes the span, the minimum, the point HHI and the CI. Row extras: `trigger_status` (breached | not_breached | inconclusive | not_measured), `primary_status` (breached | clear | inconclusive | short_span | thin | not_measured), `hhi_solver_ci90`, `sample_span_s`, `min_sample_span_s`, `span_sufficient`. An inconclusive row is excluded from the "x of y" count like an unmeasured one and is printed "inconclusive", never "not breached".
Each → `drawdown_pct` vs the deterministic base FDV; `combined_worst` = all four together.

### 4.4 Evidence scorecard (built in `reproduce.py` from the snapshot)
1 NEP storage lock measured on-chain; 2 realized issuance measured per-epoch; 3 cross-VM headroom from live quotes on destination units (NOT_SUPPORTED if 1Click loses — report truthfully); 3b native-BTC corridor on BTC-out-per-USDC-in (the value text names the winner even when it is Relay/LI.FI); 4 EVM-L2 commoditization (Across/Relay ≤ 1Click) — an honest negative; 5 deposit/caller HHI + AI-agent name-pattern share from NearBlocks, graded DERIVED (a heuristic label, not a verified class); 5b solver HHI from execute_intents signers (VERIFIED_LIVE_API when ≥ 30 fills are sampled, DERIVED / confidence low below that because the HHI sits within sampling noise of the 3,500 trigger, NOT_SUPPORTED when no fill is attributed); 6 confidential share of volume (VERIFIED_LIVE_API when measured and ≥ the materiality line; ASSUMPTION, confidence none, under `implausible_fallback`; NOT_SUPPORTED when unavailable) but TVL (ASSUMPTION/unverified); 7 buyback capture (DERIVED). The 5b value text quotes the bootstrap CI, whether it clears / straddles 3,500, and, when the solver sample spans less than `solver_sample_min_span_s`, that the cartel trigger is inconclusive regardless of the CI.

### 4.10 IC memo layout (`memo_generator.py`)
Section numbers live in `memo_generator.SEC`. Order: 1 executive summary (model value vs market value; the market-implied solve table; a conclusion computed from the solves, with conditional wording for a market below the model, a gap closed only by the multiple, or by no input; tornado top three; relative-value rank; evidence-quality flags: confidential-share status, deposit and solver HHIs with CIs, cartel trigger status incl. inconclusive with span, bear triggers), 2 what the market is pricing, 3 what you have to believe, 4 relative value, 5 model valuation detail, 6 microstructure, 7 concentration, 8 supply physics, 9 SOTP, 10 bear case, 11 evidence scorecard, 12 assumptions, 13 reproduction, 14 provenance and warnings (14.1). The README findings block adds rows for model vs market, the market-implied requirements, the FDV/fees rank, the tornado top drivers, HHI CIs with the cartel status, and the confidential-share status.

### 4.5 What the market is pricing (`models/market_implied.py`)
Pure, no network. `primitives_from_snapshot(snapshot)` rebuilds the primitive inputs the run used (calibration + registry values recorded in the snapshot) and `compose_inputs(p)` re-derives every derived input exactly as `build_inputs` (public take reconciled to live fees, take floor, monthly growth, confidential growth to the target share, λ_conf), so `deterministic_sotp(inputs_from_snapshot(s))` reproduces `sotp.calibration.deterministic_base`. `run_market_implied(snapshot)` moves ONE input at a time, all others at base, and finds with `scipy.optimize.brentq` (xtol = rtol = 1e-12) the value at which the deterministic (expected-path) FDV equals `sotp.current_fdv_usd`, inside fixed search bounds (`SEARCH_BOUNDS`; a root outside them is `required_value = null` with `reason`, never extrapolated). Solves: expected public-volume growth (evidence: trailing-12-month Intents 30-day volume growth from the DefiLlama daily series), starting public take (evidence: live competitive fee ceiling), terminal multiple (evidence: unclipped peer median FDV/revenue), discount rate (evidence: low end of the registry range), confidential share at month H (evidence: measured share, or the ASSUMED registry share under the split fallback), year-H holder revenue via a joint volume scale (evidence: current annualised holder revenue). Each row: `base_value`, `required_value`, `reachable`, `reason`, `evidence {value, label, source, ...}`, `required_vs_evidence {ratio, difference, within_evidence}` (within = the required value is no harder than the evidence in the thesis-hostile direction: higher for growth/take/multiple/share/revenue, lower for the discount rate), `fdv_at_required_usd` + `check_rel_error`, `verdict` (a sentence computed from the numbers). Top level: `current_fdv_usd`, `base_fdv_usd`, `base_fdv_mc_p50_usd`, `gap_multiple`, `gap_multiple_vs_mc_p50`, `n_reachable`, `n_within_evidence`, `headline`. The solves invert the expected path; the MC P50 is lower by lognormal convexity, so a P50 requirement would be larger.

### 4.6 What you have to believe (`models/sensitivity.py`)
One-at-a-time tornado over every ranged input, through the same `compose_inputs` + `deterministic_sotp`. Ranges: assumptions use the registry [low, high] the run recorded; the terminal multiple uses the registry guardrails (`terminal_multiple_floor` .. `terminal_multiple_cap` high); measured inputs use a measured dispersion when the snapshot has one (starting volume × exp(±monthly volume σ); spot price × exp(±monthly price σ); gross take and holder capture = min..max over the trailing `sensitivity_measured_lookback_windows` 30-day windows of the DefiLlama daily series), otherwise ± `sensitivity_unmeasured_band` (gas burn, state-lock growth, cross-VM headroom; a labelled width, not a CI). Rows ranked by |FDV_high − FDV_low|; `variance_share = swing² / Σ swing²` (first-order share for independent inputs, labelled an approximation). Output: `rows[] {rank, param, label, source, unit, base, low, high, fdv_low, fdv_high, swing_usd, implied_price_low/high, range_basis, variance_share}`, `top3_share`, `n_rows_reaching_market_fdv`, `excluded` (SVRN target / glidepath move issuance, not FDV), `notes`, `headline`.

### 4.7 Relative value (`models/relative_value.py`)
Reads only `comps`, `supply_physics`, `near_rpc` and `sotp.calibration`. For every peer and for NEAR (combined and per component) recomputes FDV / annualised fees and FDV / annualised revenue on the 30-day run-rate and on trailing-365-day sums; `coverage[metric] = {value, rank (1 = lowest multiple), n, percentile, peer_median, peer_p25, peer_p75, peer_min, peer_max, position, vs_peer_median, label}`. `implied_fdv_band.{fees,revenue}` = NEAR cash flow × peer P25 / median / P75 multiple, labelled "relative-value cross-check, not a fair value". `staking` = security budget (measured daily issuance × 365.25 × price), its share of FDV, fees and holder revenue against it, net dilution, and the supply_physics staking table. `n_peers_at_or_below_model_multiple` compares the model's terminal multiple with the peer set. `findings[]` are computed sentences; `caveat` states that peer "revenue" follows each chain's own DefiLlama methodology and that n is small.

### 4.8 Solver attribution, settlement-hub legs and bootstrap CIs (`collectors/intents_forensics.py`)
The solver audit decodes execute_intents receipts from the caller pages plus NearBlocks' method-filtered list (`?method=execute_intents`), de-duplicated by receipt id. Two settlement modes: (a) atomic `token_diff` fills (≥ 2 token_diff signers in one receipt; the solver side is identified by structure, name pattern or the counterparty of an implicit 1Click deposit address); (b) hub legs: `detect_settlement_hub` finds the account that most `transfer` intents run through (top degree ≥ `HUB_MIN_COUNTERPARTIES` and ≥ `HUB_DOMINANCE_RATIO` × the runner-up; nothing hard-coded), and a solver's transfer to that hub is one fill participation (solvers = hub counterparties identified structurally, by name, or that both pay and are paid by the hub at least twice without signing a withdrawal). Transfers that are not solver-to-hub legs are inventory or user moves and are not counted. `measurement_status` is `measured` at ≥ 10 participations, `thin` below. Solver sample design: a stratified time sample, not a contiguous window. Page 1 is the newest method-filtered page; NearBlocks accepts an arbitrary receipt-id `cursor`, so page K is aimed at the target depth (`solver_sample_target_span_s`, registry, default 21,600 s) using the id-per-second slope measured on page 1, the slope is re-measured between page 1 and page K, and pages 2..K-1 sit at even time offsets of the depth reached (`solver_sample_pages`, registry, default 8). Calls run in chunks of at most 5 per rolling free-tier window, with the waits recorded. `solver_concentration.sample` records the design, each stratum's page, cursor, time range and receipts, the total span and the coverage share; `hhi_solver_by_stratum` gives the HHI and top solver per page. The headline solver CI is a block bootstrap by page (whole pages resampled with replacement, `bootstrap_resampling = "block_by_page"`), which respects serial correlation within a page; the per-unit CI is kept as `hhi_solver_ci90_unit_bootstrap`. Every HHI (solver, deposit/caller external, external ex-AI) carries a bias-corrected percentile bootstrap 90% CI: resample the sampled units (one atomic fill, one hub leg or one deposit receipt each) with replacement, 2,000 draws, `numpy.random.default_rng([20261114, stream])` so it is reproducible; the interval is widened to contain the point estimate (BC cannot reach below a point at the bottom of the bootstrap support) and the plain percentile interval is kept as `*_ci90_percentile`. For the deposit/caller HHIs the CI is within-sample noise only. The cartel trigger additionally requires the solver sample to span at least `solver_sample_min_span_s` (section 4.3), which the stratified design meets by construction when NearBlocks serves the deep pages.

### 4.9 History store (`history.py`, `artifacts/history/`)
Append-only time series. `snapshots.jsonl`: one compact record per canonical run (`record_from_snapshot`: block, timestamps, supply/issuance, sinks, volume and take, HHIs with CIs, confidential-share status, FDV percentiles, trigger statuses), de-duplicated by snapshot SHA-256; `reproduce.py` calls `history.record_canonical_run(artifacts_dir)` at the end of every canonical run (after the README findings update, inside try/except: a history failure is logged and never fails the run), and `make history` does the same by hand (a no-op when the record exists). `bench.jsonl`: one record per standalone quote race (`make bench-history`), every venue response gzip-compressed under `history/raw/<UTC stamp>/` with the SHA-256 of the uncompressed bytes; `make history-verify` re-hashes them. `summary.json` (`make history-summary`): per-metric series with robust statistics (median, MAD, percentile CI of the median when n ≥ 5) for the web history view. Nothing earlier than the first recorded run is back-filled.

### 4.11 Volume-engine backtest (`models/backtest.py`)
Rolling-origin, out-of-sample test of the volume GBM on the run's persisted DefiLlama `dexs/near-intents` daily chart (`raw/defillama__dexs_near-intents.json`, same SHA-256 as the manifest record; fallback: the 365-day `fees.daily_series`). Origins every 30 days anchored at the last complete day, starting once `volume_volatility` yields a measured monthly sigma (90 days). At each origin, using only days up to it: V_0 = trailing 30-day sum / 30; sigma = `volume_volatility(days=365)` through `sotp_valuation._sigmas`; drift = the run's `public_volume_growth_yoy` converted as in `build_inputs`, with the Ito correction of `simulate_paths`. The 30-day volume at h ∈ {1, 3, 6} months is lognormal, so P10/P50/P90 and the PIT are closed-form (a test checks them against `simulate_paths`, seed 20261114); the realized value is the 30-day sum ending round(h × 30.44) days later. Output `snapshot.backtest`: per-forecast rows, per-horizon coverage (Wilson 90% CI, exact binomial p vs 80%), below-P10/above-P90 counts, median log error and realized/median ratio, 5-bin PIT histogram, an early/late split at the middle origin, and a `measured_drift` variant (drift = trailing mean monthly log return, no registry input). Scorecard claim: DERIVED when the binomial test does not reject 80% at any horizon, else NOT_SUPPORTED. Not tested: take rate, capture, confidential share, multiple, discount rate, price, supply.

## 5. `reproduce.py` CLI
`uv run python -m valuo.reproduce [--skip-bench] [--paths 10000] [--seed 20261114] [--no-archival] [--clips 500,50000,250000] [--nearblocks-pages 8] [--nearblocks-delay S] [--out DIR] [--quiet]`
Order: near_rpc → (execution_bench ∥ intents_forensics ∥ comps via asyncio) → supply_physics → sotp → bear_case → scorecard → market_implied / sensitivity / relative_value on the snapshot dict (`reproduce.attach_derived_models`; a model that raises leaves its key null with a `reproduce:` warning, the run continues) → write `latest_snapshot.json`, `manifest.json` (snapshot sha256 computed over the exact bytes written), `IC_MEMO.md`, `raw/*.json`, `valuo.duckdb`. Print a compact console summary (block, supply, issuance measured vs nominal, headroom per corridor, HHIs, P10/P50/P90, crossover, where the artifacts went). Exit non-zero if near_rpc or intents_forensics fail (the thesis can't be built without them); execution_bench failure → snapshot with `execution_bench=null` + warning; CoinGecko / nearstats / price-series outages → labeled fallbacks + warnings (never exit 4).
Output routing: only a FULL DEFAULT run (no `--skip-bench`, default paths/seed/horizon/clips/preset/nearblocks-pages/bench-budget, archival on; `--nearblocks-delay`, `--quiet`, `--no-duckdb` only change pacing or placement) writes the canonical `artifacts/` and rewrites the block between `<!-- VALUO:FINDINGS:START -->` / `END` in `README.md` (`memo_generator.render_readme_findings`); any other run writes to `artifacts/dev/` unless `--out DIR` is given, so a smoke run can never overwrite the committed snapshot. After the manifest is written, files in that run's `raw/` not referenced by the manifest are deleted (only inside `raw/`).
`--nearblocks-delay` defaults to unset so the collector reads `VALUO_NEARBLOCKS_PAGE_DELAY_S` (0.8 s); NearBlocks transport failures (refused connection, timeout) are retried once after 2 s and then the host is marked unavailable for the rest of the run, while the 3+6+12+24 s ladder is reserved for HTTP 429. `run_config.endpoints.artifacts_dir` is stored relative to the repo root (never the author's absolute path).
Target wall-clock < 90 s. Rate-limit NearBlocks (≥400 ms between pages) and CoinGecko (single call).

## 6. Tests
- Per-module tests use recorded fixtures (copy the relevant small probe JSONs into `quant/tests/fixtures/`; **do not** copy the 400 KB validators file — build a trimmed fixture) and pure-math checks. Mark anything touching the network `@pytest.mark.live` (registered in `pyproject.toml`, skipped unless `VALUO_LIVE_TESTS=1`).
- `tests/test_invariants.py` (the five mandated tests) loads `artifacts/latest_snapshot.json` + `manifest.json` and **skips with a clear message if artifacts are absent**: ground-truth bounds (supply > 1e9, 0 < inflation ≤ 0.05, intents.near lock > 50,000, 0.25 < staked ratio < 0.80), benchmark friction identity recomputed exactly from stored legs, HHI bounds and shares sum to 1 ± 1e-6, MC determinism (`run_sotp` twice → identical percentiles and fan p50), manifest SHA-256 hex validity + block hash equality + snapshot sha256 matches file bytes.

## 7. Web terminal contract (Next.js 15 App Router, TS, Tailwind v3/v4 — whatever `create-next-app@15` ships)
- `web/src/lib/types.ts` mirrors `schemas.py` 1:1 (hand-written TS interfaces). `web/src/lib/format.ts` (tabular numbers: `fmtUsd`, `fmtNear`, `fmtBps`, `fmtPct`, `fmtInt`, `fmtCompact`). `web/src/lib/snapshot.ts` server-side loader reading `../artifacts/latest_snapshot.json` + `manifest.json` (path from `process.env.VALUO_ARTIFACTS_DIR` or `path.resolve(process.cwd(), '..', 'artifacts')`).
- `/api/snapshot` → `{snapshot, manifest, freshness: {snapshot_block, live_block, blocks_behind, seconds_behind}}` (live block via one RPC call, 5 s timeout, `null` on failure).
- `/api/live-benchmark` POST `{corridor_id, clip_usd}` → runs the 4 venue quotes concurrently with the exact payloads in FACTS §2–3, returns `CorridorClipResult`-shaped JSON with per-venue latency. Corridor definitions in `web/src/lib/corridors.ts` must match `quant/valuo/collectors/execution_bench.py` (same ids: `eth_usdc_sol_usdc`, `eth_usdc_btc`, `base_usdc_arb_usdc`; same BTC recipient `config.BTC_ADDRESS` and Relay native-BTC currency id `RELAY_NATIVE_BTC`), and the web race must emit the same `headroom_basis = "dest_units"` and a `price_basis` per cell.
- `/api/reproduce` POST → spawns `uv run python -m valuo.reproduce` in `../quant` (non-blocking job id + `/api/reproduce/status`), so the "Refresh" button works in dev. Disable when `VALUO_ALLOW_REPRODUCE!=1`.
- Palette/typography per `TERMINAL_UI_SPEC.md` (obsidian `#090B0E`, borders `#1E2430`, emerald/amber/crimson/cyan accents, JetBrains Mono / Geist Mono, `tabular-nums` everywhere). Charts = hand-rolled SVG components (no chart lib) in `web/src/components/charts/`.
- Every displayed number has a provenance affordance: hover/click → source, URL, sha256 prefix, fetched_at. A `ProvenanceBadge` component takes `record` or `{source, name}` and looks it up in the manifest.
- Five tabs per `TERMINAL_UI_SPEC.md`, each in `web/src/components/tabs/TabN*.tsx` with sub-components in `web/src/components/tabN/`.
