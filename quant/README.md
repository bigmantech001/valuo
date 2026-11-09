# Valuo quant engine (`quant/`)

Reproducible Python 3.11+ pipeline that fetches live NEAR mainnet state and router quotes, hashes every
raw payload, and feeds the verified numbers into the supply-physics, SOTP Monte Carlo and bear-case models.
No paid API keys are required.

## Run

```bash
cd quant
uv sync                                   # creates .venv from pyproject.toml (python 3.12 via .python-version)
uv run python -m valuo.reproduce          # full default run -> ../artifacts/{latest_snapshot.json,manifest.json,IC_MEMO.md,valuo.duckdb,raw/} + README findings block
uv run python -m valuo.reproduce --skip-bench --paths 2000   # faster smoke (execution_bench = null) -> ../artifacts/dev/ (canonical files untouched)
uv run pytest -q                          # offline tests + tests/test_invariants.py against ../artifacts
VALUO_LIVE_TESTS=1 uv run pytest -q -m live   # opt-in network tests
```

Or from the repo root: `make reproduce`, `make reproduce-fast`, `make test`, `make invariants`, `make bench`, `make clean`, `make clean-dev`.

### `valuo.reproduce` flags

| flag | default | effect |
| --- | --- | --- |
| `--skip-bench` | off | skip the live 1Click / Relay / LI.FI / Across quote race; `execution_bench` is `null` and the SOTP floor falls back to the labeled `public_take_floor_bps` |
| `--paths N` | 10000 (`VALUO_MC_PATHS`) | Monte Carlo paths |
| `--seed S` | 20261114 (`VALUO_MC_SEED`) | `numpy.random.default_rng` seed |
| `--no-archival` | off | skip archival RPC lookback; state-lock growth becomes `null` with a warning (no fallback number) |
| `--clips a,b,c` | `500,50000,250000` | USD clip sizes for the quote race |
| `--nearblocks-pages N` | 8 | receipt pages (25 rows each); NearBlocks rate-limits unauthenticated bursts. Changes the solver sample, so any other value writes to `artifacts/dev/` |
| `--nearblocks-delay S` | unset -> `VALUO_NEARBLOCKS_PAGE_DELAY_S` (0.8) | spacing between NearBlocks calls; the flag overrides the env knob only when given |
| `--bench-budget S` | 45 | wall-clock budget for the quote race; a shorter budget drops cells, so any other value writes to `artifacts/dev/` |
| `--horizon M` | 36 | model horizon in months |
| `--preset base\|bull\|bear` | base | assumption preset from `valuo/assumptions.py` |
| `--out DIR` | unset | output directory; default `artifacts/` for a full default run, `artifacts/dev/` for any other flag combination |
| `--no-duckdb`, `--quiet` | off | skip the DuckDB convenience file; suppress progress lines |

Only a FULL DEFAULT run (no `--skip-bench`, default paths/seed/horizon/clips/preset/nearblocks-pages/bench-budget, archival on)
writes the canonical `artifacts/` and rewrites the block between `<!-- VALUO:FINDINGS:START -->` / `END` in the repo-root
`README.md`; `--nearblocks-delay`, `--quiet` and `--no-duckdb` change pacing or placement only and keep the run canonical.
After the manifest is written, files in that run's `raw/` directory not referenced by the manifest are deleted (nothing
outside `raw/` is touched).

Exit codes: `0` snapshot written; `2` NEAR RPC collector failed; `3` intents.near forensics failed (no receipts or
no 30d volume); `4` a model could not be calibrated from live inputs; `1` unexpected error. An execution-benchmark
failure is not fatal (`execution_bench = null` + warning). CoinGecko, nearstats and price-series outages degrade to
labeled fallbacks (`terminal_multiple_fallback`, confidential share 0 / Engine 2 not measured, or the registry
`confidential_share` when the nearstats split is implausible, `price_sigma_annual_fallback`) with warnings; they never
exit 4. `market_implied`, `sensitivity` and `relative_value` never fail a run: a model that raises leaves its snapshot
key null with a warning.

## Layout

| path | role |
| --- | --- |
| `valuo/config.py` | endpoints (overridable via repo-root `.env`), seed `20261114`, `MC_PATHS=10000`, artifact paths |
| `valuo/provenance.py` | `fetch_json` / `near_rpc_call` with retries, SHA-256 of raw bytes, `ProvenanceLedger` |
| `valuo/schemas.py` | every pydantic model in `docs/MODEL_DESIGN.md` section 3 (`Snapshot`, `Manifest`, ...) |
| `valuo/assumptions.py` | the single registry of labeled assumptions (default, range, justification), incl. `bear_*` stress definitions |
| `valuo/collectors/` | `near_rpc`, `execution_bench`, `intents_forensics`, `comps` |
| `valuo/models/` | `supply_physics`, `sotp_valuation`, `bear_case`; over the finished snapshot: `market_implied` (reverse valuation), `sensitivity` (tornado), `relative_value` (peer multiples, security budget) |
| `valuo/history.py` | append-only `artifacts/history/` store (`snapshot`, `bench`, `summary`, `verify`, `merge` subcommands); canonical runs append automatically |
| `valuo/memo_generator.py` | `render_memo(snapshot, manifest) -> Markdown` (`artifacts/IC_MEMO.md`) |
| `valuo/reproduce.py` | CLI entrypoint: collectors -> models -> evidence scorecard -> artifacts |
| `tests/` | offline unit tests (recorded fixtures) + `test_invariants.py` against generated artifacts |

## Rules

- Every number is live, derived, or a labeled assumption from `valuo/assumptions.py`. If a fetch fails after
  retries the field is `null` and a warning is recorded; nothing is substituted silently.
- Take rates come from ONE canonical window (`intents_forensics.fees.take_rate_window`: the last 30 complete UTC days
  common to the DefiLlama fees, revenue and volume charts); `supply_physics` and `sotp` consume those fields.
- Quote-race headroom and 1Click rank are on destination units delivered for the identical raw input
  (`headroom_basis = "dest_units"`); USD frictions value every venue in a cell at one common price (`price_basis`).
- Two concentration populations: `hhi_external` (deposit/caller) and `solver_concentration.hhi_solver` (execute_intents
  signers), each with a bootstrap 90% CI; the cartelization trigger reads the latter, grades it on the CI, and is `null`
  ("not measured" or "inconclusive") when it is unavailable, its CI straddles 3,500, or the solver sample spans less than
  `solver_sample_min_span_s` (3,600 s).
- Monte Carlo GBMs are mean-matching (Ito drift), so `public_volume_growth_yoy` is the expected growth; the median path
  is lower by `exp(-sigma^2 t / 2)` (`sotp.calibration.volume_terminal_median_usd_day`).
- Raw payloads land in `artifacts/raw/<source>__<name>.json`; `artifacts/manifest.json` lists their SHA-256 and the
  SHA-256 of the exact `latest_snapshot.json` bytes (`shasum -a 256 artifacts/latest_snapshot.json`).
- Monte Carlo uses `numpy.random.default_rng(seed)`; identical inputs give identical percentiles
  (`tests/test_invariants.py::test_monte_carlo_determinism` re-runs the model on the snapshot's own inputs).
