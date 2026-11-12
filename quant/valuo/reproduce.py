"""One-command reproduction: ``uv run python -m valuo.reproduce``.

Order (docs/MODEL_DESIGN.md section 5): near_rpc -> (execution_bench || intents_forensics || comps on one
asyncio loop) -> supply_physics -> sotp -> bear_case -> evidence scorecard -> market_implied / sensitivity /
relative_value (over the snapshot dict; a failure nulls the key with a warning) -> write
``artifacts/latest_snapshot.json`` (SHA-256 over the exact bytes written), ``artifacts/manifest.json``,
``artifacts/IC_MEMO.md``, ``artifacts/raw/*.json`` and ``artifacts/valuo.duckdb``.

Exit codes
    0  snapshot written
    2  NEAR RPC collector failed (block / protocol_config / validators)      - thesis cannot be built
    3  intents.near forensics failed (no receipts or no 30d volume)         - thesis cannot be built
    4  a model could not be calibrated from live inputs (ValueError)        - nothing is invented
    1  unexpected error
An execution-benchmark failure is not fatal: ``execution_bench`` is null and a warning is recorded. Peer-data
(CoinGecko), nearstats and price-series outages degrade to labeled fallbacks with warnings, never exit 4.

Output location. Only a FULL DEFAULT run (no --skip-bench, default paths/seed/horizon/clips/preset, archival on)
writes the canonical ``artifacts/``; any other run writes to ``artifacts/dev/`` unless ``--out DIR`` is given,
so a smoke run can never overwrite the committed snapshot. After the manifest is written, files in the run's
``raw/`` directory that the manifest does not reference are deleted (only inside that raw/ directory). A
canonical run also rewrites the findings block between ``<!-- VALUO:FINDINGS:START/END -->`` in README.md.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import time
import traceback
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import httpx

from valuo import __version__, assumptions, config
from valuo.collectors.chain_signatures import attach_context as attach_chain_signatures_context
from valuo.models.backtest import load_dexs_chart
from valuo.models.volume_growth import apply_measured_growth, measure_volume_growth
from valuo.collectors.chain_signatures import PER_PAGE as PER_PAGE_CS, collect_chain_signatures
from valuo.collectors.comps import collect_comps_async, multiple
from valuo.collectors.execution_bench import collect_execution_bench
from valuo.collectors.fee_pool import collect_fee_pool, scorecard_claim as fee_pool_claim
from valuo.collectors.liquidity_ladder import collect_liquidity_ladder, scorecard_claim as liquidity_ladder_claim
from valuo.collectors.intents_forensics import (
    IntentsForensicsError,
    collect_intents_forensics_async,
)
from valuo.collectors.near_rpc import collect_near_rpc
from valuo.collectors.wide_peers import collect_wide_peers, scorecard_claim as wide_peers_claim
from valuo.memo_generator import (
    README_FINDINGS_END,
    README_FINDINGS_START,
    competitive_ceiling_note,
    fmt_bps,
    fmt_near,
    fmt_pct,
    fmt_usd,
    render_memo,
    render_readme_findings,
)
from valuo import history
from valuo.models.backtest import backtest_from_raw, bootstrap_claim
from valuo.models.bear_case import THIN_SOLVER_SAMPLE_FILLS, live_metrics, run_bear_case
from valuo.models.market_implied import run_market_implied
from valuo.models.relative_value import run_relative_value
from valuo.models.bull_case import run_bull_case
from valuo.models.sensitivity import run_sensitivity
from valuo.models.sotp_valuation import build_inputs, deterministic_sotp, run_sotp
from valuo.models.supply_physics import run_supply_physics
from valuo.models.take_rate_series import run_take_rate_series, scorecard_claim as take_rate_series_claim
from valuo.provenance import FetchError, ProvenanceLedger, sha256_bytes, utc_now_iso
from valuo.schemas import (
    EvidenceClaim,
    ExecutionBenchmark,
    IntentsForensics,
    Manifest,
    NearOnchainTruth,
    PeerComps,
    Snapshot,
    SotpValuation,
    SupplyPhysics,
)

__all__ = [
    "EXIT_OK", "EXIT_NEAR_RPC", "EXIT_FORENSICS", "EXIT_MODEL", "EXIT_UNEXPECTED",
    "DEFAULT_CLIPS", "parse_args", "is_default_run", "resolve_out_dir", "run_pipeline", "build_evidence_scorecard",
    "backfill_near_fdv", "attach_derived_models", "sanitize_json", "write_snapshot", "write_duckdb", "prune_raw_dir", "update_readme_findings",
    "competitive_ceiling_note", "console_summary", "main", "chain_signatures_claim", "CHAIN_SIGNATURES_CLAIM",
]

EXIT_OK, EXIT_UNEXPECTED, EXIT_NEAR_RPC, EXIT_FORENSICS, EXIT_MODEL = 0, 1, 2, 3, 4
# ~200 receipts (system refunds and self-receipts are most of them). 12 pages at 0.4 s spacing tripped NearBlocks'
# unauthenticated 429 limit in testing; 8 pages did not. The spacing comes from VALUO_NEARBLOCKS_PAGE_DELAY_S (0.8 s)
# unless --nearblocks-delay is given. Raise pages with --nearblocks-pages when NEARBLOCKS_API_KEY is set.
DEFAULT_NEARBLOCKS_PAGES = 8
DEFAULT_BENCH_BUDGET_S = 45.0
DEFAULT_CLIPS = "500,50000,250000"
DEV_SUBDIR = "dev"


# ============================================================================ CLI
def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="valuo.reproduce", description="Reproduce the Valuo NEAR IC snapshot from live, key-free sources.")
    p.add_argument("--skip-bench", action="store_true", help="skip the live 1Click/Relay/LI.FI/Across quote race (execution_bench = null); writes to artifacts/dev/")
    p.add_argument("--paths", type=int, default=config.MC_PATHS, help=f"Monte Carlo paths (default {config.MC_PATHS}; any other value writes to artifacts/dev/)")
    p.add_argument("--seed", type=int, default=config.SEED, help=f"Monte Carlo seed (default {config.SEED})")
    p.add_argument("--no-archival", action="store_true", help="skip archival RPC lookback (state-lock growth becomes null + warning)")
    p.add_argument("--clips", default=DEFAULT_CLIPS, help="comma-separated USD clip sizes for the quote race")
    p.add_argument("--quiet", action="store_true", help="suppress progress lines (summary still printed)")
    p.add_argument("--nearblocks-pages", type=int, default=DEFAULT_NEARBLOCKS_PAGES, help=f"NearBlocks receipt pages (25 rows each; default {DEFAULT_NEARBLOCKS_PAGES}; any other value writes to artifacts/dev/)")
    p.add_argument(
        "--nearblocks-delay", type=float, default=None,
        help=f"seconds between NearBlocks calls (default: VALUO_NEARBLOCKS_PAGE_DELAY_S = {config.NEARBLOCKS_PAGE_DELAY_S:g})",
    )
    p.add_argument("--bench-budget", type=float, default=DEFAULT_BENCH_BUDGET_S, help=f"wall-clock budget for the quote race in seconds (default {DEFAULT_BENCH_BUDGET_S:g}; any other value writes to artifacts/dev/)")
    p.add_argument("--horizon", type=int, default=config.HORIZON_MONTHS, help="model horizon in months")
    p.add_argument("--preset", default="base", choices=sorted(assumptions.SCENARIO_PRESETS), help="assumption preset")
    p.add_argument("--no-duckdb", action="store_true", help="do not write valuo.duckdb")
    p.add_argument("--out", default=None, help="output directory (default: artifacts/ for a full default run, artifacts/dev/ otherwise)")
    args = p.parse_args(argv)
    args.argv_used = list(argv) if argv is not None else list(sys.argv[1:])
    if args.paths < 1:
        p.error("--paths must be >= 1")
    if args.horizon < 1:
        p.error("--horizon must be >= 1")
    try:
        args.clip_values = [float(c) for c in args.clips.split(",") if c.strip()]
    except ValueError:
        p.error("--clips must be comma-separated numbers")
    if not args.clip_values or any(c <= 0 for c in args.clip_values):
        p.error("--clips must contain positive numbers")
    if args.nearblocks_delay is not None and args.nearblocks_delay < 0:
        p.error("--nearblocks-delay must be >= 0")
    args.is_default_run = is_default_run(args)
    args.out_dir = resolve_out_dir(args)
    return args


def is_default_run(args: argparse.Namespace) -> bool:
    """True only for the canonical configuration whose artifacts belong in artifacts/ (make reproduce).

    Every flag that changes WHAT is sampled or modelled counts: fewer NearBlocks pages thin the solver sample (a
    different HHI_solver and possibly a "not measured" cartel trigger) and a shorter quote-race budget drops cells,
    so those runs go to artifacts/dev/ like any other non-default run. --nearblocks-delay, --quiet, --no-duckdb and
    --out only change pacing and output placement, not the data.
    """
    default_clips = [float(c) for c in DEFAULT_CLIPS.split(",")]
    return bool(
        not args.skip_bench and args.paths == config.MC_PATHS and args.seed == config.SEED and args.horizon == config.HORIZON_MONTHS
        and args.preset == "base" and not args.no_archival and list(args.clip_values) == default_clips
        and args.nearblocks_pages == DEFAULT_NEARBLOCKS_PAGES and float(args.bench_budget) == DEFAULT_BENCH_BUDGET_S
    )


def resolve_out_dir(args: argparse.Namespace) -> Path:
    """--out DIR when given; else artifacts/ for a full default run, artifacts/dev/ for anything else."""
    if getattr(args, "out", None):
        return Path(args.out).expanduser().resolve()
    return config.ARTIFACTS_DIR if is_default_run(args) else config.ARTIFACTS_DIR / DEV_SUBDIR


class _Log:
    def __init__(self, quiet: bool) -> None:
        self.quiet = quiet
        self.t0 = time.perf_counter()

    def __call__(self, msg: str) -> None:
        if not self.quiet:
            print(f"[{time.perf_counter() - self.t0:6.1f}s] {msg}", file=sys.stderr, flush=True)


# ============================================================================ stage 2: concurrent API collectors
async def _collect_apis(
    ledger: ProvenanceLedger, args: argparse.Namespace, log: _Log,
) -> tuple[ExecutionBenchmark | None, Any, PeerComps, dict[str, Any] | None, dict[str, Any]]:
    """Run bench (optional), forensics, comps, the Chain Signatures audit and EXTRA_COLLECTORS on one event loop and one client.

    Bench failure -> None. The Chain Signatures audit also reads NearBlocks, so it waits for forensics to finish
    (the two would share NearBlocks' unauthenticated per-minute quota) and then runs while bench/comps continue.
    """
    timeout = max(config.HTTP_TIMEOUT_S, 25.0)
    forensics_done = asyncio.Event()
    bench_done = asyncio.Event()
    events = {"bench_done": bench_done, "forensics_done": forensics_done}
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        async def forensics_task() -> Any:
            try:
                # page_delay_s=None lets the collector read VALUO_NEARBLOCKS_PAGE_DELAY_S; the flag overrides it only when given.
                return await collect_intents_forensics_async(ledger, client=client, nearblocks_pages=args.nearblocks_pages, page_delay_s=args.nearblocks_delay)
            finally:
                forensics_done.set()

        # --- Chain Signatures (v1.signer) usage audit: evidence only, never fatal (failure -> warning + nulls).
        async def chain_signatures_task() -> dict[str, Any] | None:
            await forensics_done.wait()
            t0 = time.perf_counter()
            cs_warnings: list[str] = []
            try:
                cs = await collect_chain_signatures(client, ledger, cs_warnings)
            except Exception as exc:  # noqa: BLE001 - the collector already swallows; kept for safety
                cs_warnings.append(f"chain_signatures: failed ({type(exc).__name__}: {exc}); chain_signatures is null")
                cs = None
            for w in cs_warnings:
                ledger.warn(w)
            if cs is not None:
                cs["elapsed_s"] = round(time.perf_counter() - t0, 3)
            log(f"chain_signatures done: status {(cs or {}).get('status')}, {(cs or {}).get('windows_ok', 0)} windows")
            return cs

        async def bench_task() -> ExecutionBenchmark | None:
            try:
                if args.skip_bench:
                    ledger.warn("reproduce: execution benchmark skipped (--skip-bench); execution_bench is null")
                    return None
                try:
                    return await collect_execution_bench(ledger, clips_usd=args.clip_values, client=client, budget_s=args.bench_budget)
                except Exception as exc:  # the race is evidence, not a prerequisite; record and carry on
                    ledger.warn(f"reproduce: execution benchmark failed ({type(exc).__name__}: {exc}); execution_bench is null")
                    log(f"execution_bench failed: {type(exc).__name__}: {exc}")
                    return None
            finally:
                bench_done.set()

        async def extra_task(key: str, fn: Any) -> Any:
            t0 = time.perf_counter()
            try:
                out = await fn(client, ledger, args, log, events)
            except Exception as exc:  # noqa: BLE001 - evidence, not a prerequisite
                ledger.warn(f"reproduce: {key} failed ({type(exc).__name__}: {exc}); snapshot.{key} is null")
                log(f"{key} failed: {type(exc).__name__}: {exc}")
                return None
            if isinstance(out, dict):
                out.setdefault("elapsed_s", round(time.perf_counter() - t0, 3))
            log(f"{key} done in {time.perf_counter() - t0:.1f}s")
            return out

        bench, forensics, comps, chain_sigs, *extra_results = await asyncio.gather(
            bench_task(),
            forensics_task(),
            collect_comps_async(ledger, client=client),
            chain_signatures_task(),
            *(extra_task(key, fn) for key, fn in EXTRA_COLLECTORS),
            return_exceptions=True,
        )
    extras = {key: (None if isinstance(res, BaseException) else res) for (key, _fn), res in zip(EXTRA_COLLECTORS, extra_results)}
    if isinstance(bench, BaseException):  # cannot happen (bench_task swallows), kept for safety
        ledger.warn(f"reproduce: execution benchmark failed ({bench!r}); execution_bench is null")
        bench = None
    if isinstance(comps, BaseException):
        raise comps
    if isinstance(chain_sigs, BaseException):
        ledger.warn(f"reproduce: chain_signatures failed ({chain_sigs!r}); chain_signatures is null")
        chain_sigs = None
    return bench, forensics, comps, chain_sigs, extras


# ============================================================================ stage 3: comps backfill
def backfill_near_fdv(comps: PeerComps, forensics: IntentsForensics, ledger: ProvenanceLedger) -> PeerComps:
    """When CoinGecko failed, price NEAR's rows from nearstats ``price.facts`` (fdvUsd / marketCapUsd), labeled ``fdv_source="nearstats"``.

    Peer rows are never backfilled (no key-free FDV for SOL/ETH/HYPE outside CoinGecko); the ex-NEAR medians are unaffected.
    """
    fdv = forensics.price.get("fdv_usd")
    mcap = forensics.price.get("market_cap_usd")
    if comps.near_combined.fdv_usd is not None or not isinstance(fdv, (int, float)) or not math.isfinite(fdv) or fdv <= 0:
        return comps
    rows = [comps.near_combined, *comps.near_components]
    for row in rows:
        row.fdv_usd = float(fdv)
        row.market_cap_usd = float(mcap) if isinstance(mcap, (int, float)) and math.isfinite(mcap) else None
        row.fdv_source = "nearstats"
        row.fdv_to_fees = multiple(row.fdv_usd, row.annualized_fees_usd)
        row.fdv_to_revenue = multiple(row.fdv_usd, row.annualized_revenue_usd)
        row.mcap_to_fees = multiple(row.market_cap_usd, row.annualized_fees_usd)
        row.mcap_to_revenue = multiple(row.market_cap_usd, row.annualized_revenue_usd)
    ledger.warn("reproduce: CoinGecko FDV unavailable; NEAR rows in comps backfilled from nearstats price.facts.fdvUsd (fdv_source=nearstats)")
    return comps


# ============================================================================ stage 7: evidence scorecard
def _claim(claim: str, status: str, value: str, source: str, confidence: str, note: str = "") -> EvidenceClaim:
    return EvidenceClaim(claim=claim, status=status, value=value, source=source, confidence=confidence, note=note)  # type: ignore[arg-type]


def _record_ref(ledger: ProvenanceLedger | None, source: str, name: str) -> str:
    rec = ledger.get(source, name) if ledger is not None else None
    return f"{source}/{name} sha256 {rec.sha256[:12]}..." if rec is not None else f"{source}/{name}"


def _ci_txt(ci: Any) -> str:
    """' [lo-hi 90% CI]' for a two-number bootstrap interval, else ''."""
    if isinstance(ci, (list, tuple)) and len(ci) == 2 and all(isinstance(x, (int, float)) for x in ci):
        return f" [90% CI {ci[0]:,.0f}-{ci[1]:,.0f}]"
    return ""


def _cells(bench: ExecutionBenchmark, archetype: str):
    ids = {c.corridor_id for c in bench.corridors if c.archetype == archetype}
    return [r for r in bench.results if r.corridor_id in ids]


def build_evidence_scorecard(
    truth: NearOnchainTruth,
    bench: ExecutionBenchmark | None,
    forensics: IntentsForensics,
    supply: SupplyPhysics,
    sotp: SotpValuation,
    comps: PeerComps,
    ledger: ProvenanceLedger | None = None,
    chain_signatures: dict[str, Any] | None = None,
) -> list[EvidenceClaim]:
    """The claims of MODEL_DESIGN 4.4, graded from the numbers actually in the snapshot (never from the thesis).

    ``chain_signatures`` (the v1.signer audit) adds one claim when given; None leaves the card as before.
    """
    claims: list[EvidenceClaim] = []
    intents = next((s for s in truth.tracked_sinks if s.account_id == "intents.near"), None)

    # 1. NEP storage lock measured on-chain.
    if intents is not None and isinstance(intents.storage_locked_near, (int, float)) and intents.storage_locked_near > 0:
        growth = (
            f"growth {intents.growth_bytes_per_day:,.0f} B/day = {intents.growth_locked_near_per_day:,.1f} NEAR/day over {intents.growth_window_days:.1f} d (archival)"
            if intents.growth_locked_near_per_day is not None else "growth unmeasured this run (archival lookback unavailable or disabled)"
        )
        claims.append(_claim(
            "NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB)", "VERIFIED_ON_CHAIN",
            f"intents.near storage_usage {intents.storage_bytes:,} bytes = {intents.storage_locked_near:,.0f} NEAR locked; "
            f"{truth.total_state_locked_near:,.0f} NEAR across {len(truth.tracked_sinks)} tracked contracts",
            f"{_record_ref(ledger, 'near_rpc', 'view_account:intents.near')} @ block {truth.block_height:,}; storage_amount_per_byte from EXPERIMENTAL_protocol_config",
            "high", f"{growth}; a {truth.storage_near_per_kb:.2f} NEAR/KB lock is released if state is deleted, so it is a sink while state grows",
        ))
    else:
        claims.append(_claim("NEP storage staking is a measured on-chain supply sink", "NOT_SUPPORTED",
                             "intents.near view_account unavailable" if intents is None else "intents.near storage lock reads 0 NEAR",
                             "near_rpc", "low", "collector could not read a positive clearinghouse storage lock this run"))

    # 2. Realized issuance measured per epoch.
    ei = truth.epoch_issuance
    if ei.implied_annual_issuance_near is not None and ei.implied_annual_issuance_near > 0:
        gap_pct = (ei.measured_minus_nominal_annual_near or 0.0) / ei.nominal_annual_issuance_near * 100 if ei.nominal_annual_issuance_near else 0.0
        claims.append(_claim(
            "Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap", "VERIFIED_ON_CHAIN",
            f"{ei.minted_per_epoch_near:,.2f} NEAR minted at epoch start {ei.epoch_start_height:,} x {ei.epochs_per_year:,.1f} epochs/yr = "
            f"{ei.implied_annual_issuance_near:,.0f} NEAR/yr ({ei.implied_annual_inflation_rate * 100 if ei.implied_annual_inflation_rate else float('nan'):.4f}%), "
            f"{gap_pct:+.2f}% vs nominal {ei.nominal_annual_issuance_near:,.0f}",
            f"{_record_ref(ledger, 'near_rpc', f'block:{ei.epoch_start_height}')} and its predecessor by prev_hash; previous epoch start {ei.prev_epoch_start_height}",
            "high", f"second independent jump {ei.prev_minted_per_epoch_near:,.2f} NEAR; within-epoch drift {ei.net_burn_per_epoch_near:,.2f} NEAR/epoch is the net gas burn",
        ))
    else:
        claims.append(_claim(
            "Realized issuance is measured from epoch-boundary supply jumps", "DERIVED",
            f"nominal only: {ei.nominal_annual_issuance_near:,.0f} NEAR/yr = max_inflation_rate x total_supply", "near_rpc EXPERIMENTAL_protocol_config + block",
            "medium", "epoch boundary blocks unavailable this run; models used the nominal rate with a warning",
        ))

    # 3-4b. Benchmark-dependent claims. Headroom and rank are on DESTINATION UNITS (BTC out per USDC in), never on each
    # venue's own USD oracle; the statements below follow that ranking even where 1Click loses.
    if bench is None:
        for claim in (
            "Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC",
            "Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC",
            "EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC",
        ):
            claims.append(_claim(claim, "ASSUMPTION", "benchmark not run (--skip-bench)", "execution_bench (none)", "none",
                                 "no live quotes this snapshot; the public-take floor fell back to the registry assumption"))
    else:
        hb = bench.headroom_by_archetype_bps or {}
        hn = bench.headroom_n_by_archetype or {}
        basis = getattr(bench, "headroom_basis", None) or "dest_units"

        def per_clip(archetype: str) -> str:
            return "; ".join(
                f"${r.clip_usd:,.0f}: {('%+.2f bps vs ' % r.headroom_bps) + str(r.best_competitor) + ' (rank %s/%d)' % (r.oneclick_rank, (r.n_competitors_ok or 0) + 1) if r.headroom_bps is not None else '1Click ' + next((q.status for q in r.quotes if q.venue == '1click'), 'n/a')}"
                for r in _cells(bench, archetype)
            )

        no_liq = [f"{r.corridor_id} ${r.clip_usd:,.0f}" for r in bench.results for q in r.quotes if q.venue == "1click" and q.status == "no_liquidity"]
        cap_note = f"capacity ceiling: 1Click `No liquidity available` on {', '.join(no_liq)} while competitors filled" if no_liq else "no 1Click capacity failures"

        cv = hb.get("cross_vm")
        ceiling_txt = f"; competitor ceiling {bench.competitive_fee_ceiling_bps:.2f} bps" if bench.competitive_fee_ceiling_bps is not None else ""
        claims.append(_claim(
            "Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC",
            "VERIFIED_LIVE_API" if (cv is not None and cv > 0) else "NOT_SUPPORTED",
            f"median headroom {cv:+.2f} bps over {hn.get('cross_vm', 0)} comparable cells ({basis}){ceiling_txt}" if cv is not None
            else "no comparable cell (1Click and a competitor both ok)",
            f"oneclick/relay/lifi/across quote records {bench.ran_at_utc}", "medium" if cv is not None else "low",
            f"{per_clip('cross_vm')}; {cap_note}",
        ))
        nb = hb.get("native_btc")
        btc_cells = [r for r in _cells(bench, "native_btc") if r.headroom_bps is not None]
        winners = sorted({str(r.best_competitor) for r in btc_cells if r.headroom_bps is not None and r.headroom_bps < 0})
        if nb is None:
            nb_value, nb_note = "no comparable cell", "1Click and at least one competitor must both return an ok BTC quote"
        elif nb > 0:
            nb_value = f"1Click delivers {nb:+.2f} bps more BTC per USDC (median over {hn.get('native_btc', 0)} cells, {basis}; no USD oracle in the ranking)"
            nb_note = f"clip-dependent: {per_clip('native_btc')}"
        else:
            nb_value = (
                f"1Click delivers LESS BTC per USDC than the best competitor ({', '.join(winners) or 'competitor'}): median headroom {nb:+.2f} bps over "
                f"{hn.get('native_btc', 0)} cells ({basis}); the claim is not supported by this run"
            )
            nb_note = f"clip-dependent: {per_clip('native_btc')}"
        claims.append(_claim(
            "Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC",
            "VERIFIED_LIVE_API" if (nb is not None and nb > 0) else "NOT_SUPPORTED",
            nb_value, f"oneclick/lifi/relay quote records {bench.ran_at_utc}", "medium" if nb is not None else "low",
            f"{nb_note}; LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used",
        ))
        l2 = hb.get("evm_l2")
        claims.append(_claim(
            "EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative)",
            # Grade follows the value: no comparable cell is "not measured" (NOT_SUPPORTED), not an assumption.
            "VERIFIED_LIVE_API" if (l2 is not None and l2 <= 0) else "NOT_SUPPORTED",
            f"median headroom {l2:+.2f} bps over {hn.get('evm_l2', 0)} cells ({basis}; 1Click {'trails' if l2 is not None and l2 < 0 else 'leads'})" if l2 is not None else "no comparable cell",
            f"oneclick/across/relay/lifi quote records {bench.ran_at_utc}", "medium" if l2 is not None else "low",
            f"{per_clip('evm_l2')}; the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins",
        ))

    # 5. Deposit/caller concentration and the AI-agent name-pattern share (DERIVED: a heuristic label, not a verified class).
    cs = forensics.caller_sample or {}
    sc = forensics.solver_concentration or {}
    span = cs.get("sample_span_s")
    ex_ai = cs.get("hhi_external_ex_ai_agent")
    sample_txt = f"{forensics.receipts_sampled} unique receipts over {span:,.0f} s" if isinstance(span, (int, float)) else f"{forensics.receipts_sampled} unique receipts"
    materiality = assumptions.get("evidence_materiality_share").value
    ext_ci = _ci_txt(cs.get("hhi_external_ci90"))
    ai_material = isinstance(forensics.ai_agent_share, (int, float)) and forensics.ai_agent_share >= materiality
    claims.append(_claim(
        "Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material",
        # DERIVED (name-pattern heuristic) when the AI-agent share clears the materiality line; below it the claim fails.
        "DERIVED" if ai_material else "NOT_SUPPORTED",
        (f"deposit/caller HHI_external {forensics.hhi_external:,.0f}{ext_ci} (N_eff {forensics.n_eff_external:.2f}), ex-AI-agent {ex_ai:,.0f}; " if isinstance(ex_ai, (int, float)) else
         f"deposit/caller HHI_external {forensics.hhi_external:,.0f}{ext_ci} (N_eff {forensics.n_eff_external:.2f}); ")
        + f"AI-agent share {forensics.ai_agent_share:.1%} ({'>=' if ai_material else '<'} {materiality:.0%} materiality line), bridge share {forensics.bridge_share:.1%}",
        f"{_record_ref(ledger, 'nearblocks', 'txns:intents.near:p1')} ... p{forensics.pages_fetched}",
        "low",
        f"{sample_txt}; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification "
        "(*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources "
        "(bridge callbacks, direct callers), not solvers",
    ))
    # 5b. Solver concentration (the population the cartelization trigger reads). VERIFIED_LIVE_API only when the audit says
    # "measured" (>= SOLVER_MIN_PARTICIPATIONS participations), a bootstrap 90% CI exists and at least THIN_SOLVER_SAMPLE_FILLS
    # fills/legs were sampled; a measured but small sample is DERIVED (confidence low); thin or absent is NOT_SUPPORTED.
    hhi_s = sc.get("hhi_solver")
    n_fills_s = sc.get("n_fills")
    status_s = sc.get("measurement_status") or ("measured" if isinstance(hhi_s, (int, float)) else "not_measured")
    hhi_measured = isinstance(hhi_s, (int, float)) and status_s == "measured"
    ci_s = sc.get("hhi_solver_ci90")
    thin_sample = hhi_measured and (not isinstance(n_fills_s, (int, float)) or n_fills_s < THIN_SOLVER_SAMPLE_FILLS or not ci_s)
    cartel_threshold = assumptions.get("bear_cartel_hhi_external").value
    ci_verdict = ""
    if ci_s and hhi_measured:
        lo, hi = ci_s
        ci_verdict = (f"; CI entirely above the {cartel_threshold:,.0f} cartel threshold" if lo > cartel_threshold else
                      f"; CI entirely below the {cartel_threshold:,.0f} cartel threshold" if hi < cartel_threshold else
                      f"; CI straddles the {cartel_threshold:,.0f} cartel threshold (inconclusive)")
    span_s = sc.get("sample_span_s")
    min_span = assumptions.get("solver_sample_min_span_s").value
    if hhi_measured and (not isinstance(span_s, (int, float)) or span_s < min_span):
        ci_verdict += (f"; sample spans {span_s:,.0f} s (< {min_span:,.0f} s solver_sample_min_span_s), so the cartel trigger is "
                       "inconclusive regardless of the CI" if isinstance(span_s, (int, float)) else
                       "; sample span unknown, so the cartel trigger is inconclusive")
    modes = (f" ({sc.get('n_fills_atomic', 0)} atomic token_diff fills, {sc.get('n_fills_hub_legs', 0)} hub-settled legs)"
             if sc.get("n_fills_hub_legs") is not None else "")
    hub = sc.get("settlement_hub") or {}
    sample = sc.get("sample") or {}
    claims.append(_claim(
        "Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers",
        "VERIFIED_LIVE_API" if (hhi_measured and not thin_sample) else ("DERIVED" if hhi_measured else "NOT_SUPPORTED"),
        (
            f"HHI_solver {hhi_s:,.0f}{_ci_txt(ci_s)} (N_eff {sc.get('n_eff_solver') or float('nan'):.2f}) over {sc.get('n_fills_attributed')} fill participations "
            f"in {n_fills_s} fills{modes}, {sc.get('unique_solvers')} distinct solvers{ci_verdict}"
            + (f"; small sample (< {THIN_SOLVER_SAMPLE_FILLS} fills or no CI): not a market-share measure" if thin_sample else "")
        ) if hhi_measured else (
            f"not measured: {sc.get('n_fills_attributed') or 0} solver fill participations (< {sc.get('min_participations_for_measured', 10)}) "
            f"in {sc.get('n_execute_intents_receipts')} decoded execute_intents receipts"
        ),
        f"{_record_ref(ledger, 'nearblocks', 'txns:intents.near:p1')} ... p{forensics.pages_fetched}"
        + (f" + {sample.get('execute_intents_pages_ok')} method-filtered execute_intents page(s)" if sample.get("execute_intents_pages_ok") else "")
        + "; args.signed[].payload.message (NEP-413 signer_id)",
        "medium" if (hhi_measured and not thin_sample and isinstance(span_s, (int, float)) and span_s >= min_span) else "low",
        f"{sc.get('n_execute_intents_receipts')} execute_intents receipts decoded"
        + (f"; settlement hub {str(hub.get('account_id'))[:12]}... ({hub.get('distinct_counterparties')} counterparties) routes most swaps via transfer legs" if hub else "")
        + "; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty",
    ))

    # 6-7. Confidential share and TVL. The grade follows the value AND its measurement status: a fallback or an unavailable split
    # is never VERIFIED, and a measured share below the materiality line does not support "material".
    vol = forensics.volume
    share = vol.get("confidential_share_30d")
    share_status = vol.get("confidential_share_status") or ("measured" if isinstance(share, (int, float)) else "unavailable")
    reported = vol.get("confidential_share_30d_reported", share)
    split_src = f"{_record_ref(ledger, 'nearstats', 'summary')} intents.totalsBreakdown (basis {vol.get('split_basis')})"
    if share_status == "measured" and isinstance(share, (int, float)):
        material = share >= materiality
        claims.append(_claim(
            "Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume",
            "VERIFIED_LIVE_API" if material else "NOT_SUPPORTED",
            f"{share:.1%} of {fmt_usd(vol.get('30d'))} 30d volume (public {fmt_usd(vol.get('public30d'))}, confidential {fmt_usd(vol.get('confidential30d'))}); "
            f"{'>=' if material else '<'} {materiality:.0%} materiality line",
            split_src, "medium" if material else "low",
            "nearstats derives confidential volume as the NEAR-reported total minus explorer-visible public volume; DefiLlama agrees with the total day-for-day",
        ))
    elif share_status == "onchain_estimate" and isinstance(share, (int, float)):
        material = share >= materiality
        lo, hi = vol.get("confidential_share_low"), vol.get("confidential_share_high")
        est = vol.get("confidential_share_estimate") or {}
        band = f" (band {lo:.1%}-{hi:.1%})" if isinstance(lo, (int, float)) and isinstance(hi, (int, float)) else ""
        claims.append(_claim(
            "Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume",
            "DERIVED" if material else "NOT_SUPPORTED",
            f"{share:.1%}{band} estimated on-chain: Confidential Intents Treasury 24h inflow {fmt_usd(est.get('flow_in_24h_usd'))} / outflow "
            f"{fmt_usd(est.get('flow_out_24h_usd'))} against 24h volume {fmt_usd(est.get('volume_24h_usd'))}; {'>=' if material else '<'} {materiality:.0%} materiality line",
            f"{_record_ref(ledger, 'near_rpc', 'confidential:balances:head')} treasury balances in intents.near (NEAR mainnet RPC)", "low",
            "nearstats' split was rejected by the plausibility guard; the share is estimated from the public treasury boundary instead. "
            "Biases: same-hour shield/unshield netting and in-shard turnover push it down, solver inventory pushes it up; 24h window",
        ))
    elif share_status == "implausible_fallback":
        reasons = "; ".join(vol.get("confidential_share_reason") or [])
        claims.append(_claim(
            "Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume", "ASSUMPTION",
            f"NOT MEASURED this run: nearstats reported {reported:.2%} (implausible); the model uses the registry assumption confidential_share = "
            f"{share:.0%}" if isinstance(reported, (int, float)) and isinstance(share, (int, float)) else "NOT MEASURED this run: split implausible",
            split_src, "none",
            f"split rejected by the plausibility guard ({reasons}); raw fields in intents_forensics.volume.split_reported. Engine 2 rests on an assumption this run",
        ))
    else:
        claims.append(_claim(
            "Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume", "NOT_SUPPORTED",
            "split unavailable (not measured)", split_src, "none",
            "nearstats public/confidential split missing; SOTP credits no confidential volume and reports Engine 2 as not measured",
        ))
    tvl_status = forensics.confidential_tvl_source_status or ("verified" if forensics.confidential_tvl_verified else "unknown")
    tvl_ok = isinstance(forensics.confidential_tvl_usd, (int, float)) and forensics.confidential_tvl_usd > 0
    onchain_tvl = tvl_status == "onchain_measured"
    reported_tvl = getattr(forensics, "confidential_tvl_reported_usd", None)
    claims.append(_claim(
        "Confidential TVL backs the dark-pool engine (Engine 2)",
        ("VERIFIED_ON_CHAIN" if onchain_tvl else "VERIFIED_LIVE_API" if forensics.confidential_tvl_verified else "ASSUMPTION") if tvl_ok else "NOT_SUPPORTED",
        (f"{fmt_usd(forensics.confidential_tvl_usd)} TVL read on-chain from the Confidential Intents treasury in intents.near"
         + (f" (NEAR-reported via nearstats: {fmt_usd(reported_tvl)})" if isinstance(reported_tvl, (int, float)) else "")
         if onchain_tvl else f"{fmt_usd(forensics.confidential_tvl_usd)} TVL, nearstats sourceStatus = {tvl_status}"),
        (f"{_record_ref(ledger, 'near_rpc', 'confidential:balances:head')} intents.near mt_batch_balance_of (treasury)"
         if onchain_tvl else f"{_record_ref(ledger, 'nearstats', 'summary')} intents.protocolMetrics.confidentialTvlObservation"),
        "high" if onchain_tvl else "low",
        f"Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut "
        f"({assumptions.get('confidential_multiple_haircut').value:g}); the confidential take ({assumptions.get('confidential_take_bps').value:g} bps) is an assumption",
    ))

    # 8. Buyback capture.
    cal = sotp.calibration or {}
    fees = forensics.fees
    alpha = cal.get("alpha_capture")
    alpha_ok = isinstance(alpha, (int, float)) and alpha > 0 and isinstance(fees.get("gross_take_bps"), (int, float))
    claims.append(_claim(
        "Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink",
        "DERIVED" if alpha_ok else "NOT_SUPPORTED",
        f"alpha {fmt_pct(cal.get('alpha_capture'), 1)}; gross take {fmt_bps(fees.get('gross_take_bps'))}, net take {fmt_bps(fees.get('net_take_bps'))}; "
        f"buyback sink {fmt_near(supply.current_daily_sinks_near.get('buyback'), 0)}/day = {fmt_pct(supply.sink_coverage_ratio, 1)} coverage incl. burn and lock",
        f"{_record_ref(ledger, 'defillama', 'fees:near-intents:dailyHoldersRevenue')} / {_record_ref(ledger, 'defillama', 'fees:near-intents')}", "medium",
        f"DefiLlama revenue methodology: {(fees.get('methodology') or {}).get('revenue') or 'n/a'}",
    ))
    if chain_signatures is not None:
        claims.append(chain_signatures_claim(chain_signatures))
    return claims


# --- Chain Signatures claim (v1.signer audit; collectors/chain_signatures.py).
CHAIN_SIGNATURES_CLAIM = "Chain Signatures (v1.signer) is a growing second usage engine beyond Intents"


def chain_signatures_claim(cs: dict[str, Any]) -> EvidenceClaim:
    """DERIVED when sampled sign requests show a positive ln-rate trend with t >= 2; NOT_SUPPORTED otherwise.

    The rate is a sample estimate (time-stratified NearBlocks windows), so even a significant trend is DERIVED, not
    VERIFIED. VERIFIED_LIVE_API is used only for usage that the API counts exactly (cumulative receipts) when the
    sampled trend could not be measured; that grades the usage level, never the growth.
    """
    claim = CHAIN_SIGNATURES_CLAIM
    rate7, rate30 = cs.get("sign_per_day_7d"), cs.get("sign_per_day_30d")
    trend = cs.get("trend") or {}
    callers = (cs.get("callers") or {}).get("top") or []
    top = callers[0] if callers else None
    bridge = (cs.get("callers") or {}).get("bridge_share")
    top_txt = f"; top caller {top['account_id']} {top['share']:.0%} of {cs['callers']['n_sign_sampled']:,} sampled sign receipts" if top else ""
    top_txt += f", *.bridge.near callers {bridge:.0%}" if isinstance(bridge, (int, float)) else ""
    gas_txt = f"; gas {cs['gas_near_per_sign']:.4f} NEAR per request" if isinstance(cs.get("gas_near_per_sign"), (int, float)) else ""
    src = (f"nearblocks/txns:v1.signer:before_block:* ({cs.get('windows_ok', 0)} windows of {PER_PAGE_CS} receipts, "
           f"{cs.get('receipts_sampled', 0):,} receipts) + nearblocks/txns:v1.signer:count")
    note = ("sampled estimate: each window covers minutes; bridge callers serve cross-chain transfers that overlap Intents settlement, "
            "so the engine is not fully independent of Intents; storage lock "
            f"{fmt_near(((cs.get('storage') or {}).get('storage_locked_near')), 1)} is small. ") + (cs.get("fee_note") or "")
    if isinstance(rate30, (int, float)) and rate30 > 0 and trend.get("growth_30d") is not None:
        g, t_stat, status = trend["growth_30d"], trend.get("t_stat"), cs.get("growth_status")
        ci = trend.get("growth_30d_ci90")
        ci_txt = f" [90% CI {ci[0]:+.0%} to {ci[1]:+.0%}]" if isinstance(ci, list) and len(ci) == 2 else ""
        value = (f"{rate7:,.0f} sign requests/day (7d) vs {rate30:,.0f}/day (30d); ln-trend {g:+.0%} per 30 d{ci_txt}, "
                 f"t = {t_stat:.2f}{top_txt}{gas_txt}" if isinstance(rate7, (int, float)) and isinstance(t_stat, (int, float)) else
                 f"{rate30:,.0f} sign requests/day (30d); trend {g:+.0%} per 30 d{top_txt}{gas_txt}")
        if status == "growing":
            return _claim(claim, "DERIVED", value, src, "medium", note)
        return _claim(claim, "NOT_SUPPORTED", value + f" ({status}: growth not shown at t >= 2)", src, "low", note)
    cum = cs.get("cumulative_receipts")
    if isinstance(cum, int) and cum > 0:
        return _claim(claim, "VERIFIED_LIVE_API", f"usage only: {cum:,} cumulative v1.signer receipts; growth not measured this run",
                      "nearblocks/txns:v1.signer:count", "low", "the sampled rate/trend failed this run; the level is counted, the growth claim is not supported")
    return _claim(claim, "NOT_SUPPORTED", "not measured: NearBlocks v1.signer endpoints unavailable this run", "nearblocks (none)", "none",
                  "; ".join(cs.get("not_measured") or []))


# ============================================================================ writing
def sanitize_json(obj: Any, path: str = "$", hits: list[str] | None = None) -> Any:
    """Replace non-finite floats with None (JSON has no NaN); record the JSON paths touched in ``hits``."""
    if isinstance(obj, float):
        if math.isfinite(obj):
            return obj
        if hits is not None:
            hits.append(path)
        return None
    if isinstance(obj, dict):
        return {k: sanitize_json(v, f"{path}.{k}", hits) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_json(v, f"{path}[{i}]", hits) for i, v in enumerate(obj)]
    return obj


def write_snapshot(snapshot: Snapshot, path: Path) -> tuple[bytes, str]:
    """Serialize with indent=2, write, and return (bytes, sha256 of exactly those bytes)."""
    payload = sanitize_json(snapshot.model_dump(mode="json"))
    data = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data, sha256_bytes(data)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(config.REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def prune_raw_dir(raw_dir: Path, manifest: Manifest) -> list[str]:
    """Delete files in ``raw_dir`` (and only there) that the manifest does not reference; returns the deleted names.

    Payloads from earlier runs would otherwise accumulate next to the hashed set and look like evidence.
    Nothing outside ``raw_dir`` is touched; subdirectories are left alone.
    """
    raw_dir = raw_dir.resolve()
    if not raw_dir.is_dir():
        return []
    keep: set[Path] = set()
    for rec in manifest.records:
        if not rec.raw_path:
            continue
        p = Path(rec.raw_path)
        p = p if p.is_absolute() else config.REPO_ROOT / p
        try:
            keep.add(p.resolve())
        except OSError:
            continue
    deleted: list[str] = []
    for child in sorted(raw_dir.iterdir()):
        if child.is_file() and child.resolve() not in keep and child.resolve().parent == raw_dir:
            child.unlink()
            deleted.append(child.name)
    return deleted


def update_readme_findings(readme_path: Path, block: str) -> bool:
    """Replace the text between the README findings markers with ``block`` (which carries the markers itself).

    Returns False (and changes nothing) when the file or either marker is missing, so a judge's edited README is
    never clobbered.
    """
    if not readme_path.exists():
        return False
    text = readme_path.read_text(encoding="utf-8")
    start, end = text.find(README_FINDINGS_START), text.find(README_FINDINGS_END)
    if start < 0 or end < 0 or end < start:
        return False
    end += len(README_FINDINGS_END)
    new_text = text[:start] + block + text[end:]
    if new_text != text:
        readme_path.write_text(new_text, encoding="utf-8")
    return True


def write_duckdb(path: Path, snapshot: Snapshot, manifest: Manifest) -> None:
    """Convenience tables (JSON is canonical): raw_payloads, quotes, callers, mc_percentiles, fan_chart, assumptions, evidence."""
    import duckdb  # local import: optional convenience layer

    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    try:
        con.execute(
            "CREATE TABLE raw_payloads (source VARCHAR, name VARCHAR, url VARCHAR, method VARCHAR, http_status INTEGER, ok BOOLEAN, error VARCHAR, "
            "fetched_at_utc VARCHAR, latency_ms DOUBLE, bytes BIGINT, sha256 VARCHAR, raw_path VARCHAR, attempts INTEGER)"
        )
        con.executemany(
            "INSERT INTO raw_payloads VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(r.source, r.name, r.url, r.method, r.http_status, r.ok, r.error, r.fetched_at_utc, r.latency_ms, r.bytes, r.sha256, r.raw_path, r.attempts)
             for r in manifest.records],
        )
        con.execute(
            "CREATE TABLE quotes (ran_at_utc VARCHAR, corridor_id VARCHAR, archetype VARCHAR, clip_usd DOUBLE, venue VARCHAR, status VARCHAR, supported BOOLEAN, "
            "amount_in_usd DOUBLE, amount_out_formatted DOUBLE, amount_out_usd DOUBLE, friction_bps_usd DOUBLE, friction_bps_raw DOUBLE, time_estimate_s DOUBLE, "
            "route_tool VARCHAR, error_message VARCHAR, latency_ms DOUBLE, raw_record_sha256 VARCHAR, cell_headroom_bps DOUBLE, cell_oneclick_rank INTEGER)"
        )
        bench = snapshot.execution_bench
        if bench is not None:
            arch = {c.corridor_id: c.archetype for c in bench.corridors}
            con.executemany(
                "INSERT INTO quotes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(bench.ran_at_utc, r.corridor_id, arch.get(r.corridor_id), r.clip_usd, q.venue, q.status, q.supported, q.amount_in_usd, q.amount_out_formatted,
                  q.amount_out_usd, q.friction_bps_usd, q.friction_bps_raw, q.time_estimate_s, q.route_tool, q.error_message, q.latency_ms, q.raw_record_sha256,
                  r.headroom_bps, r.oneclick_rank)
                 for r in bench.results for q in r.quotes],
            )
        con.execute("CREATE TABLE callers (account_id VARCHAR, cls VARCHAR, receipts INTEGER, share DOUBLE, example_tx_hash VARCHAR)")
        con.executemany(
            "INSERT INTO callers VALUES (?, ?, ?, ?, ?)",
            [(c.account_id, c.cls.value, c.receipts, c.share, c.example_tx_hash) for c in snapshot.intents_forensics.callers],
        )
        con.execute("CREATE TABLE mc_percentiles (series VARCHAR, p10 DOUBLE, p25 DOUBLE, p50 DOUBLE, p75 DOUBLE, p90 DOUBLE)")
        series = [("fdv_usd", snapshot.sotp.fdv_percentiles), ("price_usd", snapshot.sotp.price_percentiles), ("fdv_ex_monetary_usd", snapshot.sotp.fdv_ex_monetary_percentiles)]
        series += [(f"engine_{e.key}", {"p10": e.p10, "p25": e.p25, "p50": e.p50, "p75": e.p75, "p90": e.p90}) for e in snapshot.sotp.engines]
        con.executemany("INSERT INTO mc_percentiles VALUES (?, ?, ?, ?, ?, ?)", [(k, d.get("p10"), d.get("p25"), d.get("p50"), d.get("p75"), d.get("p90")) for k, d in series])
        fan = snapshot.sotp.fan_chart
        con.execute("CREATE TABLE fan_chart (month INTEGER, fdv_p10 DOUBLE, fdv_p25 DOUBLE, fdv_p50 DOUBLE, fdv_p75 DOUBLE, fdv_p90 DOUBLE, rev_p10 DOUBLE, rev_p25 DOUBLE, rev_p50 DOUBLE, rev_p75 DOUBLE, rev_p90 DOUBLE)")
        n = len(fan.get("fdv_p50") or [])
        con.executemany(
            "INSERT INTO fan_chart VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [(i + 1, *[fan.get(f"fdv_{k}", [None] * n)[i] for k in ("p10", "p25", "p50", "p75", "p90")], *[fan.get(f"rev_{k}", [None] * n)[i] for k in ("p10", "p25", "p50", "p75", "p90")]) for i in range(n)],
        )
        con.execute("CREATE TABLE assumptions (key VARCHAR, value DOUBLE, unit VARCHAR, low DOUBLE, high DOUBLE, source VARCHAR, justification VARCHAR)")
        con.executemany("INSERT INTO assumptions VALUES (?, ?, ?, ?, ?, ?, ?)", [(a.key, a.value, a.unit, a.low, a.high, a.source, a.justification) for a in snapshot.assumptions])
        con.execute("CREATE TABLE evidence (claim VARCHAR, status VARCHAR, value VARCHAR, source VARCHAR, confidence VARCHAR, note VARCHAR)")
        con.executemany("INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?)", [(c.claim, c.status, c.value, c.source, c.confidence, c.note) for c in snapshot.evidence_scorecard])
        con.execute("CREATE TABLE snapshot_meta (key VARCHAR, value VARCHAR)")
        con.executemany("INSERT INTO snapshot_meta VALUES (?, ?)", [
            ("generated_at_utc", snapshot.generated_at_utc), ("block_height", str(snapshot.near_rpc.block_height)), ("block_hash", snapshot.near_rpc.block_hash),
            ("snapshot_sha256", manifest.snapshot_sha256), ("seed", str(snapshot.seed)), ("valuo_version", snapshot.valuo_version),
        ])
    finally:
        con.close()


def _merge_warnings(*groups: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for group in groups:
        for w in group:
            if w and w not in seen:
                seen.add(w)
                out.append(w)
    return out


# ============================================================================ console summary
def console_summary(snapshot: Snapshot, manifest: Manifest, paths: dict[str, Path]) -> str:
    t, s, sp, f = snapshot.near_rpc, snapshot.sotp, snapshot.supply_physics, snapshot.intents_forensics
    ei = t.epoch_issuance
    lines = [
        "=" * 96,
        f"Valuo snapshot  block {t.block_height:,} {t.block_hash}  {t.timestamp_utc}  runtime {snapshot.runtime_s:.1f} s",
        f"  supply {fmt_near(t.total_supply_near)}  staked {fmt_pct(t.staked_supply_ratio, 2)} ({t.active_validator_count} validators)  cap {fmt_pct(t.max_inflation_rate, 2)}",
        f"  issuance measured {fmt_near(ei.implied_annual_issuance_near)}/yr ({fmt_pct(ei.implied_annual_inflation_rate, 4)}) vs nominal {fmt_near(ei.nominal_annual_issuance_near)}/yr; "
        f"minted/epoch {fmt_near(ei.minted_per_epoch_near, 2)}, {fmt_near(sp.current_daily_issuance_near)}/day",
        f"  state lock {fmt_near(t.total_state_locked_near)} over {len(t.tracked_sinks)} sinks; growth {fmt_near(t.measured_state_lock_growth_near_per_day, 1)}/day; "
        f"sinks {fmt_near(sp.current_daily_sinks_near.get('total'), 0)}/day = {fmt_pct(sp.sink_coverage_ratio, 1)} of issuance",
    ]
    if snapshot.execution_bench is not None:
        b = snapshot.execution_bench
        for r in b.results:
            h = f"{r.headroom_bps:+.2f} bps [{r.headroom_basis}] rank {r.oneclick_rank} vs {r.best_competitor}" if r.headroom_bps is not None else "n/a (" + next((q.status for q in r.quotes if q.venue == "1click"), "?") + ")"
            lines.append(f"  headroom {r.corridor_id:<20} ${r.clip_usd:>9,.0f}  {h}")
        lines.append(f"  headroom by archetype {b.headroom_by_archetype_bps}  competitor ceiling {fmt_bps(b.competitive_fee_ceiling_bps)}")
    else:
        lines.append("  execution_bench: null (skipped)")
    cs = f.caller_sample or {}
    ex_ai = cs.get("hhi_external_ex_ai_agent")
    ex_ai_txt = f"{ex_ai:,.0f}" if isinstance(ex_ai, (int, float)) else "n/a"
    breakeven_txt = ", ".join(f"{k}: {fmt_usd(v)}" for k, v in sp.breakeven_daily_volume_usd.items())
    crossover_txt = ", ".join(f"{tr.regime}: {tr.crossover_month}" for tr in sp.trajectories)
    p_key = f"p_crossover_within_{s.horizon_months}m"
    mc_txt = ", ".join(
        f"{k}: {fmt_pct(v.get(p_key), 1)}" for k, v in s.crossover_month_distribution.items() if isinstance(v, dict)
    )
    lines += [
        f"  HHI external {f.hhi_external:,.0f} (N_eff {f.n_eff_external:.2f}; ex-AI {ex_ai_txt})  AI share {fmt_pct(f.ai_agent_share, 1)}  "
        f"{f.receipts_sampled} receipts / {f.pages_fetched} pages",
        f"  volume 30d {fmt_usd(f.volume.get('30d'))} (confidential {fmt_pct(f.volume.get('confidential_share_30d'), 1)})  gross take {fmt_bps(f.fees.get('gross_take_bps'))}  "
        f"net take {fmt_bps(f.fees.get('net_take_bps'))}  price {fmt_usd(f.price.get('current_usd'), compact=False, decimals=2)}",
        f"  SOTP FDV P10/P50/P90 {fmt_usd(s.fdv_percentiles['p10'])} / {fmt_usd(s.fdv_percentiles['p50'])} / {fmt_usd(s.fdv_percentiles['p90'])}  "
        f"price P50 {fmt_usd(s.price_percentiles['p50'], compact=False, decimals=2)}  current FDV {fmt_usd(s.current_fdv_usd)} ({s.upside_p50_pct:+.1f}%)",
        f"  breakeven V*/day {{{breakeven_txt}}}  flow crossover {{{crossover_txt}}}  MC P(cross<={s.horizon_months}m) {{{mc_txt}}}",
        f"  bear combined worst {fmt_usd(snapshot.bear_case.combined_worst_fdv)} ({fmt_pct(snapshot.bear_case.combined_drawdown_pct, 0, signed=True)}); triggers breached {snapshot.bear_case.triggers_breached}/{snapshot.bear_case.triggers_evaluated} graded",
        _chain_signatures_console_line(getattr(snapshot, "chain_signatures", None)),
        f"  records {len(manifest.records)} ({manifest.failures} non-2xx)  warnings {len(snapshot.warnings)}",
        f"  artifacts -> {paths['dir']} ({'CANONICAL full default run' if (snapshot.run_config or {}).get('canonical') else 'DEV run: non-default flags; canonical artifacts/ untouched'})",
        f"  wrote {paths['snapshot']} (sha256 {manifest.snapshot_sha256[:16]}...), {paths['manifest']}, {paths['memo']}" + (f", {paths['duckdb']}" if "duckdb" in paths else ""),
    ]
    if paths.get("readme") is not None:
        lines.append(f"  README findings block rewritten in {paths['readme']}")
    pruned = (snapshot.run_config or {}).get("raw_files_pruned")
    if pruned:
        lines.append(f"  pruned {pruned} stale file(s) from {paths['raw']}")
    lines.append("=" * 96)
    return "\n".join(lines)


def _chain_signatures_console_line(cs: Any) -> str:
    if not isinstance(cs, dict) or cs.get("status") != "measured":
        return f"  chain signatures (v1.signer): {(cs or {}).get('status', 'null') if isinstance(cs, dict) else 'null'}"
    trend = cs.get("trend") or {}
    g = trend.get("growth_30d")
    return (f"  chain signatures (v1.signer): {cs.get('sign_per_day_7d') or float('nan'):,.0f} sign/day 7d, {cs.get('sign_per_day_30d') or float('nan'):,.0f} 30d; "
            f"trend {f'{g:+.0%}' if isinstance(g, (int, float)) else 'n/a'}/30d ({cs.get('growth_status')}); {cs.get('windows_ok')} windows")


# ============================================================================ derived views over the snapshot
DERIVED_MODELS: tuple[tuple[str, Any], ...] = (
    ("market_implied", run_market_implied), ("sensitivity", run_sensitivity), ("relative_value", run_relative_value),
    ("bull_case", run_bull_case),  # reads market_implied, so it runs after it
)

# Derived views that also read the run's persisted raw payloads: (snapshot key, fn(snap_dict, raw_dir) -> dict).
# They run after the backtest, in list order. A failure nulls the key and adds a warning. One entry per view.
RAW_DERIVED_MODELS: list[tuple[str, Any]] = [
    ("take_rate_series", run_take_rate_series),
]

# Extra evidence collectors run inside _collect_apis on the shared client:
# (snapshot key, async fn(client, ledger, args, log, events) -> dict | None), events = {"bench_done", "forensics_done"}
# (asyncio.Event). A collector that calls the quote venues waits for bench_done so it never competes with the race.
# Never fatal: an exception becomes a ledger warning and a null key. One entry per collector.
EXTRA_COLLECTORS: list[tuple[str, Any]] = [
    ("fee_pool_share", collect_fee_pool),
    ("liquidity_ladder", collect_liquidity_ladder),
    ("wide_peers", collect_wide_peers),
]

# Graded scorecard rows from the views above: (snapshot key, fn(data) -> claim dict | None). Appended after the backtest
# row, in list order. A view that is null, declines to grade (None) or raises adds no row; a raise adds a warning.
EXTRA_CLAIMS: list[tuple[str, Any]] = [
    ("backtest", bootstrap_claim),
    ("take_rate_series", take_rate_series_claim),
    ("liquidity_ladder", liquidity_ladder_claim),
    ("fee_pool_share", fee_pool_claim),
    ("wide_peers", wide_peers_claim),
]
_CLAIM_FIELDS = ("claim", "status", "value", "source", "confidence", "note")


def extra_claims(snap_dict: Mapping[str, Any]) -> tuple[list[EvidenceClaim], list[str]]:
    """(claims, warnings) from EXTRA_CLAIMS for the keys present and non-null in ``snap_dict``."""
    claims: list[EvidenceClaim] = []
    warns: list[str] = []
    for key, fn in EXTRA_CLAIMS:
        data = snap_dict.get(key)
        if not data:
            continue
        try:
            row = fn(data)
            if row:
                claims.append(_claim(**{f: str(row.get(f) or "") for f in _CLAIM_FIELDS}))
        except Exception as exc:  # noqa: BLE001 - a scorecard row, not a prerequisite
            warns.append(f"reproduce: scorecard row for {key} failed ({type(exc).__name__}: {exc}); row omitted")
    return claims, warns


def attach_derived_models(snapshot: Snapshot, timings: dict[str, float] | None = None, log: Any = None, raw_dir: Path | None = None) -> list[str]:
    """Run market_implied / sensitivity / relative_value on the snapshot's JSON dict and attach them as top-level keys.

    A model that raises leaves its key null and adds a warning (returned and merged into ``snapshot.warnings``);
    the run is never aborted by a derived view. Each model's wall time goes into ``timings`` under its key.
    The volume backtest (``snapshot.backtest``) reads the run's persisted DefiLlama dexs payload from ``raw_dir``
    (else the 365-day series in the snapshot) and appends its graded claim to the evidence scorecard.
    """
    snap_dict = sanitize_json(snapshot.model_dump(mode="json"))
    out: list[str] = []
    for key, fn in DERIVED_MODELS:
        t0 = time.perf_counter()
        try:
            setattr(snapshot, key, fn(snap_dict))
            snap_dict[key] = sanitize_json(getattr(snapshot, key))  # later views may read earlier ones
        except Exception as exc:  # noqa: BLE001 - a derived view, not a prerequisite
            setattr(snapshot, key, None)
            out.append(f"reproduce: {key} failed ({type(exc).__name__}: {exc}); snapshot.{key} is null")
            if log is not None:
                log(f"{key} failed: {type(exc).__name__}: {exc}")
        if timings is not None:
            timings[key] = round(time.perf_counter() - t0, 3)
    # ---- backtest (begin): out-of-sample test of the volume engine + its scorecard claim
    t0 = time.perf_counter()
    try:
        bt = backtest_from_raw(snap_dict, raw_dir)
        snapshot.backtest = bt  # type: ignore[attr-defined]  # extra field (OpenModel allows extras)
        snapshot.evidence_scorecard = [*snapshot.evidence_scorecard, backtest_claim(bt)]
    except Exception as exc:  # noqa: BLE001 - a derived view, not a prerequisite
        snapshot.backtest = None  # type: ignore[attr-defined]
        out.append(f"reproduce: backtest failed ({type(exc).__name__}: {exc}); snapshot.backtest is null")
        if log is not None:
            log(f"backtest failed: {type(exc).__name__}: {exc}")
    if timings is not None:
        timings["backtest"] = round(time.perf_counter() - t0, 3)
    # ---- backtest (end)
    for key, fn in RAW_DERIVED_MODELS:
        t0 = time.perf_counter()
        try:
            setattr(snapshot, key, fn(snap_dict, raw_dir))
            snap_dict[key] = sanitize_json(getattr(snapshot, key))
        except Exception as exc:  # noqa: BLE001 - a derived view, not a prerequisite
            setattr(snapshot, key, None)
            out.append(f"reproduce: {key} failed ({type(exc).__name__}: {exc}); snapshot.{key} is null")
            if log is not None:
                log(f"{key} failed: {type(exc).__name__}: {exc}")
        if timings is not None:
            timings[key] = round(time.perf_counter() - t0, 3)
    snap_dict["backtest"] = sanitize_json(getattr(snapshot, "backtest", None))
    for key, _fn in EXTRA_COLLECTORS:  # collector outputs are already on the snapshot; make sure the dict has them
        snap_dict.setdefault(key, sanitize_json(getattr(snapshot, key, None)))
    claims, claim_warns = extra_claims(snap_dict)
    if claims:
        snapshot.evidence_scorecard = [*snapshot.evidence_scorecard, *claims]
    out.extend(claim_warns)
    if out:
        snapshot.warnings = _merge_warnings(snapshot.warnings, out)
    return out


def backtest_claim(bt: Mapping[str, Any]) -> EvidenceClaim:
    """Scorecard row for the volume backtest: DERIVED only when P10-P90 coverage is not rejected at every horizon."""
    by_h = bt.get("by_horizon") or {}
    scored = {h: s for h, s in by_h.items() if s.get("n")}
    cov = "; ".join(
        f"{h}m {s['inside']}/{s['n']} = {s['coverage_p10_p90']:.0%} inside P10-P90 (binomial p {s['binom_p_vs_80']:.2f})" for h, s in scored.items()
    ) or "no scored forecasts"
    r1 = (by_h.get("1") or {}).get("median_ratio_realized_to_p50")
    bias = "" if r1 is None else f"; 1m median realized / forecast median {r1:.2f}x ({'under' if r1 > 1 else 'over'}-prediction)"
    per = bt.get("by_period") or {}
    split = ""
    e, late = (per.get("early") or {}).get("1") or {}, (per.get("late") or {}).get("1") or {}
    if e.get("n") and late.get("n"):
        split = f"; 1m coverage {e['coverage_p10_p90']:.0%} for origins before {per['split_origin_date']}, {late['coverage_p10_p90']:.0%} from it"
    ok = bool((bt.get("calibrated") or {}).get("all")) and bool(scored)
    return _claim(
        "The volume engine (GBM with measured sigma) is calibrated out of sample: P10-P90 covers ~80% of realized 30-day volume",
        "DERIVED" if ok else "NOT_SUPPORTED",
        f"{cov}{bias}{split}; {bt.get('n_origins', 0)} monthly origins {bt.get('first_origin')} to {bt.get('last_origin')}",
        f"{bt.get('source')}" + (f" sha256 {str(bt['source_sha256'])[:12]}..." if bt.get("source_sha256") else ""),
        "medium" if ok else "low",
        "Tests the volume distribution only; the take rate, holder capture, confidential share, multiple and discount rate are not "
        "backtested. 3m and 6m forecasts from monthly origins overlap, so their effective sample is smaller than n.",
    )


# ============================================================================ pipeline
def run_pipeline(args: argparse.Namespace, log: _Log | None = None) -> tuple[Snapshot, Manifest, str, dict[str, Path]]:
    """Collect, model, write. Raises FetchError / IntentsForensicsError / ValueError for the fatal exits."""
    log = log or _Log(quiet=True)
    t_start = time.perf_counter()
    started_utc = utc_now_iso()
    out_dir: Path = getattr(args, "out_dir", None) or resolve_out_dir(args)
    canonical = bool(getattr(args, "is_default_run", is_default_run(args))) and out_dir == config.ARTIFACTS_DIR
    paths = config.artifact_paths(out_dir)
    paths["raw"].mkdir(parents=True, exist_ok=True)
    log(f"artifacts -> {out_dir} ({'canonical full default run' if canonical else 'dev run; canonical artifacts/ untouched'})")
    ledger = ProvenanceLedger(raw_dir=paths["raw"])
    registry = assumptions.preset(args.preset)
    timings: dict[str, float] = {}

    log(f"near_rpc: block/protocol/validators/sinks/epoch issuance (archival={'off' if args.no_archival else 'on'})")
    t0 = time.perf_counter()
    truth = collect_near_rpc(ledger, use_archival=not args.no_archival)
    timings["near_rpc"] = round(time.perf_counter() - t0, 3)
    log(f"near_rpc done: block {truth.block_height:,}, supply {truth.total_supply_near:,.0f} NEAR, {len(ledger.records)} records")

    log(f"api collectors: execution_bench({'skip' if args.skip_bench else 'live'}) || intents_forensics({args.nearblocks_pages} pages) || comps")
    t0 = time.perf_counter()
    bench, forensics, comps, chain_sigs, extras = asyncio.run(_collect_apis(ledger, args, log))
    timings["api_collectors"] = round(time.perf_counter() - t0, 3)
    if isinstance(forensics, BaseException):
        raise forensics
    log(f"api collectors done: bench={'ok' if bench is not None else 'null'}, forensics {forensics.receipts_sampled} receipts, comps median FDV/rev {comps.median_fdv_to_revenue_ex_near}")
    comps = backfill_near_fdv(comps, forensics, ledger)
    # Chain Signatures: reuse near_rpc's v1.signer storage row and price NEAR quantities at the snapshot price.
    chain_sigs = attach_chain_signatures_context(
        chain_sigs, storage_sink=next((s for s in truth.tracked_sinks if s.account_id == "v1.signer"), None),
        near_price_usd=forensics.price.get("current_usd"),
    )

    # Volume growth: measured from the DefiLlama daily chart this run fetched, replacing the registry's fixed 30%/yr.
    # Only the base preset; the bull/bear presets are deliberate scenarios and keep their fixed values.
    growth_warnings: list[str] = []
    chart, chart_src, chart_sha = load_dexs_chart(paths["raw"], {"intents_forensics": {"fees": forensics.fees}})
    volume_growth = measure_volume_growth(chart, source=chart_src, source_sha256=chart_sha)
    if args.preset == "base":
        registry, used = apply_measured_growth(registry, volume_growth)
        volume_growth["used_in_model"] = used
        if used:
            ci = volume_growth["ci90"]
            log(f"volume growth MEASURED: {volume_growth['growth_yoy']:+.1%}/yr (90% CI {ci[0]:+.1%} to {ci[1]:+.1%}, {volume_growth['n_days']} days)")
        else:
            growth_warnings.append(f"volume growth not measured ({volume_growth.get('note') or volume_growth['status']}); "
                                   f"public_volume_growth_yoy stays the registry assumption {assumptions.value('public_volume_growth_yoy'):+.0%}")
    else:
        volume_growth["used_in_model"] = False
        volume_growth["note"] = f"preset {args.preset!r} fixes public_volume_growth_yoy; the measurement is reported, not used"

    log("models: supply_physics -> sotp -> bear_case")
    t0 = time.perf_counter()
    supply = run_supply_physics(
        truth, forensics, comps, registry,
        competitive_ceiling_bps=bench.competitive_fee_ceiling_bps if bench is not None else None,
        competitive_ceiling_note=competitive_ceiling_note(bench), horizon_months=args.horizon,
    )
    timings["supply_physics"] = round(time.perf_counter() - t0, 3)
    t0 = time.perf_counter()
    sotp = run_sotp(truth, forensics, comps, supply, registry, seed=args.seed, n_paths=args.paths, horizon_months=args.horizon, bench=bench)
    timings["sotp"] = round(time.perf_counter() - t0, 3)
    t0 = time.perf_counter()
    base_inputs, _cal, _labeled = build_inputs(truth, forensics, comps, supply, registry, bench=bench, horizon_months=args.horizon)
    bear = run_bear_case(base_inputs, deterministic_sotp(base_inputs), live_metrics(forensics, truth, bench))
    timings["bear_case"] = round(time.perf_counter() - t0, 3)
    scorecard = build_evidence_scorecard(truth, bench, forensics, supply, sotp, comps, ledger, chain_signatures=chain_sigs)

    warnings = _merge_warnings(ledger.warnings, growth_warnings, supply.warnings, [f"sotp: {w}" if not w.startswith("sotp") else w for w in (sotp.calibration or {}).get("warnings", [])])
    nan_hits: list[str] = []
    runtime = time.perf_counter() - t_start
    snapshot = Snapshot(
        generated_at_utc=started_utc, seed=args.seed, runtime_s=round(runtime, 3), valuo_version=__version__,
        near_rpc=truth, execution_bench=bench, intents_forensics=forensics, comps=comps, supply_physics=supply, sotp=sotp, bear_case=bear,
        evidence_scorecard=scorecard, assumptions=assumptions.as_list(registry), warnings=warnings, provenance_summary=ledger.summary(),
        volume_growth=volume_growth,  # extra field: the measured growth fit (and whether the model used it)
        chain_signatures=chain_sigs,  # extra field (OpenModel extra="allow"); null when the audit failed
        **extras,  # EXTRA_COLLECTORS outputs, one top-level key each (null when the collector failed)
        run_config={
            "argv": list(getattr(args, "argv_used", [])), "skip_bench": args.skip_bench, "paths": args.paths, "seed": args.seed,
            "no_archival": args.no_archival, "clips_usd": args.clip_values, "nearblocks_pages": args.nearblocks_pages,
            # Effective spacing: the flag when given, else VALUO_NEARBLOCKS_PAGE_DELAY_S (the collector reads the same value).
            "nearblocks_delay_s": args.nearblocks_delay if args.nearblocks_delay is not None else config.NEARBLOCKS_PAGE_DELAY_S,
            "nearblocks_delay_source": "cli" if args.nearblocks_delay is not None else "env:VALUO_NEARBLOCKS_PAGE_DELAY_S",
            "bench_budget_s": args.bench_budget,
            "horizon_months": args.horizon, "preset": args.preset, "endpoints": config.as_dict(),
            "canonical": canonical, "artifacts_dir": config.repo_relative(out_dir) or "<outside repository>",
        },
        timings_s=timings,
    )
    # Reverse valuation, tornado and relative value read the snapshot as JSON (the same dict the web and the CLIs see).
    # A failure here never aborts the run: the key is null and a warning says why.
    attach_derived_models(snapshot, timings, log, raw_dir=paths["raw"])
    snapshot.timings_s = timings
    sanitize_json(snapshot.model_dump(mode="json"), hits=nan_hits)
    if nan_hits:
        snapshot.warnings = _merge_warnings(snapshot.warnings, [f"reproduce: {len(nan_hits)} non-finite value(s) written as null: {', '.join(nan_hits[:10])}"])

    data, snapshot_sha = write_snapshot(snapshot, paths["snapshot"])
    manifest = Manifest(
        generated_at_utc=snapshot.generated_at_utc, block_height=truth.block_height, block_hash=truth.block_hash,
        snapshot_sha256=snapshot_sha, snapshot_path=_rel(paths["snapshot"]), records=list(ledger.records), sources=ledger.sources(),
        failures=len(ledger.failures()), valuo_version=__version__, seed=args.seed, snapshot_bytes=len(data), memo_path=_rel(paths["memo"]),
        raw_dir=_rel(paths["raw"]), warnings=list(snapshot.warnings), run_config={k: v for k, v in snapshot.run_config.items() if k != "endpoints"},
    )
    memo = render_memo(snapshot, manifest)
    paths["memo"].write_bytes(memo.encode("utf-8"))
    manifest.memo_sha256 = sha256_bytes(memo.encode("utf-8"))
    if not args.no_duckdb:
        try:
            write_duckdb(paths["duckdb"], snapshot, manifest)
            manifest.duckdb_path = _rel(paths["duckdb"])
        except Exception as exc:  # convenience layer only; JSON is canonical
            log(f"duckdb write failed: {type(exc).__name__}: {exc}")
            manifest.warnings = _merge_warnings(manifest.warnings, [f"reproduce: duckdb write failed ({type(exc).__name__}: {exc})"])
            paths.pop("duckdb", None)
    else:
        paths.pop("duckdb", None)
    paths["manifest"].write_bytes(json.dumps(sanitize_json(manifest.model_dump(mode="json")), indent=2, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    # Only files this manifest references may stay in raw/ (stale payloads from earlier runs are not evidence).
    pruned = prune_raw_dir(paths["raw"], manifest)
    snapshot.run_config["raw_files_pruned"] = len(pruned)
    if pruned:
        log(f"pruned {len(pruned)} stale raw payload(s) not referenced by the manifest from {paths['raw']}")
    paths["readme"] = None
    if canonical:
        readme = config.REPO_ROOT / "README.md"
        if update_readme_findings(readme, render_readme_findings(snapshot, manifest)):
            paths["readme"] = readme
            log(f"rewrote the findings block in {readme}")
        else:
            log(f"README findings markers not found in {readme}; README left untouched")
        # Append this canonical run to artifacts/history/ (idempotent: de-duplicated by snapshot sha256).
        t0 = time.perf_counter()
        try:
            rec = history.record_canonical_run(paths["dir"])
            log("history: canonical run recorded in artifacts/history/snapshots.jsonl" if rec is not None else "history: snapshot not recorded (missing or not canonical)")
        except Exception as exc:  # noqa: BLE001 - the history store must never fail a reproduction
            log(f"history: record_canonical_run failed ({type(exc).__name__}: {exc})")
        snapshot.timings_s["history"] = round(time.perf_counter() - t0, 3)
    log(f"wrote snapshot ({len(data):,} bytes, sha256 {snapshot_sha[:16]}...), manifest, memo" + (", duckdb" if "duckdb" in paths else ""))
    return snapshot, manifest, memo, paths


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    log = _Log(args.quiet)
    try:
        snapshot, manifest, _memo, paths = run_pipeline(args, log)
    except FetchError as exc:
        print(f"FATAL near_rpc: {exc}", file=sys.stderr)
        return EXIT_NEAR_RPC
    except IntentsForensicsError as exc:
        print(
            f"FATAL intents_forensics: {exc}\n"
            "  If NearBlocks answered HTTP 429 (unauthenticated quota), wait a minute and re-run, lower --nearblocks-pages, "
            "or set NEARBLOCKS_API_KEY in the repo-root .env.",
            file=sys.stderr,
        )
        return EXIT_FORENSICS
    except ValueError as exc:
        print(f"FATAL model calibration: {exc} (a required live input is null; nothing is invented)", file=sys.stderr)
        return EXIT_MODEL
    except Exception as exc:  # noqa: BLE001 - report and exit non-zero
        traceback.print_exc()
        print(f"FATAL unexpected: {type(exc).__name__}: {exc}", file=sys.stderr)
        return EXIT_UNEXPECTED
    print(console_summary(snapshot, manifest, paths))
    if snapshot.warnings and not args.quiet:
        print(f"warnings ({len(snapshot.warnings)}):")
        for w in snapshot.warnings:
            print(f"  - {w}")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
