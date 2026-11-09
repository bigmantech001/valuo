# Valuo web terminal (`web/`)

Next.js 15 (App Router, TypeScript, Tailwind v4) Investment Committee terminal for `$NEAR`. It renders
the artifacts produced by the Python quant engine in `../quant` and exposes two live endpoints
(a quote race across NEAR Intents 1Click / Relay / LI.FI / Across, and a chain-head freshness check).
Nothing is mocked: with no `artifacts/latest_snapshot.json` the page shows the reproduction
instructions instead of numbers.

## Run

```bash
# 1. produce the artifacts (zero API keys)
cd .. && make reproduce            # == cd quant && uv run python -m valuo.reproduce

# 2. run the terminal
cd web
npm install
npm run dev                        # http://localhost:3000
npm run build && npm start         # production
npm run lint                       # eslint (next/core-web-vitals + next/typescript)
```

## Environment

Read from `process.env` first, then the repo-root `.env` (same precedence as `quant/valuo/config.py`).
None are required.

| variable | default | purpose |
| --- | --- | --- |
| `VALUO_ARTIFACTS_DIR` | `<repo>/artifacts` | where `latest_snapshot.json`, `manifest.json`, `IC_MEMO.md` are read |
| `VALUO_REPO_ROOT` | `<web>/..` | repo root (for `.env` and `quant/`) |
| `VALUO_QUANT_DIR` | `<repo>/quant` | cwd for the reproduce job |
| `VALUO_ALLOW_REPRODUCE` | unset | `1` enables `POST /api/reproduce` (spawns `uv run python -m valuo.reproduce`) and the bar's re-run button |
| `NEAR_RPC_URL` | `https://free.rpc.fastnear.com` | freshness check (`block` finality=final, 5 s timeout) |
| `ONECLICK_API_BASE`, `RELAY_API_BASE`, `LIFI_API_BASE`, `ACROSS_API_BASE` | as in `config.py` | venue endpoints for the live race |
| `ONECLICK_JWT` | unset | optional bearer for 1Click |
| `VALUO_EVM_ADDRESS`, `VALUO_SOL_ADDRESS`, `VALUO_BTC_ADDRESS` | as in `config.py` | dry-quote recipients / refund targets (nothing is sent) |
| `VALUO_BENCH_TIMEOUT_MS` | `12000` | per-venue timeout in the live race |

## API routes

| route | behaviour |
| --- | --- |
| `GET /api/snapshot` | `{snapshot, manifest, freshness, integrity, error}`; `freshness` = live head vs snapshot block (null fields on RPC failure); `integrity` = sha256 of the snapshot file vs `manifest.snapshot_sha256` |
| `GET /api/snapshot?format=freshness` | freshness + integrity only (polled by the provenance bar) |
| `GET /api/snapshot?format=memo` | downloads `artifacts/IC_MEMO.md` |
| `GET /api/snapshot?format=json` | downloads the exact `latest_snapshot.json` bytes |
| `POST /api/live-benchmark` `{corridor_id, clip_usd}` | concurrent 1Click / Relay / LI.FI / Across quotes with the payloads in `docs/LIVE_ENDPOINT_FACTS.md`; returns a `CorridorClipResult` + per-venue `RawRecord`s (sha256 of each raw response) |
| `GET /api/live-benchmark` | corridor catalogue, default clips, recipients |
| `POST /api/reproduce` `{args?: string[]}` | starts a reproduce job (403 unless `VALUO_ALLOW_REPRODUCE=1`, 409 if one is running); only the CLI's own flags are accepted |
| `GET /api/reproduce`, `GET /api/reproduce/status?id=` | job list / job state (stdout and stderr tails) |

Corridor ids match the quant collector: `eth_usdc_sol_usdc` (cross_vm), `eth_usdc_btc` (native_btc),
`base_usdc_arb_usdc` (evm_l2). Status mapping: `ok | no_liquidity | unsupported_route | error | skipped`.
Headroom = min competitor friction - 1Click friction; raw-unit friction on same-asset corridors,
venue-reported USD friction otherwise (`ranking_basis` in the response).

## Layout

```
src/lib/        types.ts (1:1 mirror of quant/valuo/schemas.py), format.ts, snapshot.ts (server), corridors.ts,
                manifestIndex.ts, liveBenchmark.ts (server), nearRpc.ts (server), reproduceJobs.ts (server),
                env.ts (server), hash.ts (server), theme.ts, cn.ts
src/components/ui/          Card, Stat, Badge, Table, Tabs, Tooltip, Drawer, Button, Toggle, Slider, Skeleton, EmptyState
src/components/provenance/  ProvenanceBar, ProvenanceDrawer, ProvenanceBadge, ManifestProvider, ReproduceButton
src/components/charts/      LineChart, FanChart, BarShare, Heatmap, Gauge, Waterfall (hand-rolled SVG, no chart libs)
src/components/tabs/        Tab1Thesis .. Tab5BearCase (placeholders receiving {snapshot, manifest})
src/app/                    layout.tsx, page.tsx, api/snapshot, api/live-benchmark, api/reproduce(/status)
```

Theme: obsidian `#090B0E`, surface `#0F1217`, border `#1E2430`, ink `#E6EAF0`, muted `#8B94A7`,
emerald `#10B981`, amber `#F59E0B`, crimson `#EF4444`, cyan `#06B6D4`; Geist Mono with
`font-variant-numeric: tabular-nums` (`.tnum`).
