# Valuo

**Reproducible Investment-Committee terminal and quant engine for `$NEAR`. One question, answered from measured data: what does NEAR's market value require, and does the evidence support it?**

Valuo values the cash flows NEAR holders can point to (NEAR Intents holder revenue, L1 gas burn, NEP storage-staking lock demand) with a seeded three-engine sum-of-the-parts Monte Carlo, then inverts it. Holding everything else at base, it solves for the volume growth, starting take rate, terminal multiple, discount rate, confidential share and holder revenue at which the model equals the market FDV, and sets each requirement next to its live evidence: trailing Intents volume growth, the competitor fee ceiling from a live 1Click / Relay / LI.FI / Across quote race, and the peer FDV/revenue distribution. The output is not a price target. It states which input the market price depends on, whether that input is measured or assumed, and what the measured cash flows support on their own; a tornado ranks what you have to believe, a peer table ranks NEAR's cash-flow multiples, and four falsification triggers say when the case breaks. The findings block below carries the current answer and the block it was measured at.

Built for `[ 02 / INV ] Investment Thesis` at the NEAR Hackathon (`nearhackathon.com`). Judged on evidence, not conviction: every number in the terminal, the IC memo and this README is fetched live from NEAR mainnet RPC and key-free public APIs, hashed, and written to `artifacts/` by one command. Nothing is hardcoded; the findings block below is regenerated from `artifacts/latest_snapshot.json` on every canonical run and states the block it was measured at.

---

## Reproduce every claim in 60 seconds (no API keys)

```bash
# prerequisites: python >= 3.11 with uv (https://docs.astral.sh/uv/), node >= 20 for the terminal
make sync        # cd quant && uv sync
make reproduce   # live NEAR RPC + 1Click/Relay/LI.FI/Across quote race + NearBlocks/nearstats/DefiLlama ->
                 # 10,000-path Monte Carlo (seed 20261114) -> artifacts/{latest_snapshot.json,manifest.json,IC_MEMO.md}
make test        # offline unit tests + the five invariant checks against artifacts/
shasum -a 256 artifacts/latest_snapshot.json   # must equal manifest.json: snapshot_sha256
cd web && npm install && npm run dev            # the IC terminal reads ../artifacts
```

Time series (optional, also key-free). `make reproduce` appends every canonical run to `artifacts/history/snapshots.jsonl` (de-duplicated by snapshot SHA-256) and rebuilds `artifacts/history/summary.json`; a VPS runs the daily snapshot and an hourly quote race on cron and commits them back (`docs/VPS.md`, `ops/vps/`); the targets below drive the store directly:

```bash
make history          # append the current canonical snapshot to artifacts/history/ (no-op if already recorded)
make bench-history    # one live quote race: gzip raw responses + SHA-256 -> artifacts/history/bench.jsonl
make history-summary  # rebuild artifacts/history/summary.json from the JSONL files
make history-verify   # gunzip and re-hash every raw payload referenced by bench.jsonl
```

`npm run dev` writes to `web/.next-dev` and `npm run build && npm start` to `web/.next` (`next.config.ts` `distDir`), so a dev server left running cannot rewrite a production build's route manifests and 404 its API routes. Stop any dev server you are not using before judging the production build; two servers on one port is still an error.

What `make reproduce` does, in order: (1) NEAR mainnet RPC: block header supply, `EXPERIMENTAL_protocol_config`, validators, `view_account` storage of the tracked contracts, and realized issuance measured from `total_supply` jumps at epoch boundaries (archival RPC for storage growth); (2) the live quote race, 1Click `dry` quotes against Relay, LI.FI and Across on three corridors (`ETH USDC -> SOL USDC`, `ETH USDC -> native BTC`, `Base USDC -> Arbitrum USDC`) at three clips, ranked on destination units delivered for the identical input; (3) `intents.near` forensics: nearstats public/confidential volume split, DefiLlama fees/revenue/volume on one aligned calendar window, NearBlocks receipts for deposit/caller concentration and execute_intents signer payloads for solver concentration; (4) supply physics, three-engine SOTP Monte Carlo and the four bear scenarios; (5) the reverse valuation (`market_implied`), the one-at-a-time tornado (`sensitivity`) and the peer cash-flow coverage (`relative_value`), computed from the snapshot itself; (6) `artifacts/latest_snapshot.json`, `manifest.json` (SHA-256 of every raw payload and of the snapshot bytes), `IC_MEMO.md`, the findings block below, and one appended record in `artifacts/history/`.

A smoke run (`make reproduce-fast`: no quote race, 2,000 paths) writes to `artifacts/dev/` and never overwrites the canonical files. Exit codes and flags: `quant/README.md`.

### Do X, see Y (terminal)

1. **Do:** Tab 2, Execution Lab: pick a corridor and clip, run the live quote race. **See:** executable quotes from 1Click, Relay, LI.FI and Across with destination units, friction in bps at one common price, settlement estimate and 1Click's headroom (positive or negative) per cell, alongside the committed benchmark.
2. **Do:** Tab 3, Supply Physics: toggle the issuance regime between the live protocol cap and the SVRN glidepath. **See:** measured daily issuance netted against measured buybacks, L1 gas burn and NEP storage-staking lock growth, the breakeven daily volume per regime and the month, if any, where the float turns deflationary.
3. **Do:** Tabs 4 and 5: move the sliders; read the bear case. **See:** the P10/P50/P90 band recomputed client-side with the same formulas as `quant/valuo/models`, and the four falsification triggers with their live values and "not measured" where a source was down.

---

<!-- VALUO:FINDINGS:START -->
## Findings as of the committed snapshot (NEAR block 223,672,128, 2026-11-08T21:24:21.779Z UTC)

Generated by `python -m valuo.reproduce` from `artifacts/latest_snapshot.json` (SHA-256 `7110830afd1354558b334dba4687e9d841e6520ada7fc518155510ed18951c00`, 2026-11-08T21:24:23.730Z UTC, valuo 0.1.0). Every figure is a live fetch, an arithmetic derivation or a labeled assumption; `n/a` means the source was unavailable in this run and nothing was substituted. `make reproduce` regenerates this block.

| Finding | Value | Basis |
| :--- | :--- | :--- |
| NEAR block / total supply | 223,672,128 / 1,311,190,966 NEAR | RPC `block` header at 2026-11-08T21:24:21.779Z |
| Market FDV vs model (expected path / MC P50) | $4.76B vs $817.9M / $262.9M (market = 5.8x the expected path) | model capitalises Intents holder revenue + gas burn + state lock, 36 m, 25% discount, 60x terminal cap |
| What the market FDV requires (one input at a time) | expected volume growth 160.9% (evidence 19.5%; outside); starting public take 178.34 bps (evidence 3.00 bps; outside); terminal multiple 372x (evidence 2,265x; inside) | brentq solve on the expected path, others at base; evidence = trailing-12m Intents volume growth, live competitive fee ceiling, peer median FDV/revenue (`market_implied`) |
| Relative value: FDV / annualised fees | NEAR 64x vs peer median 255x; rank 1 of 4 (lowest first, below every peer) | peer-multiple band $12.03B-$50.72B is a cross-check, not a fair value; n = 3 peers (`relative_value`) |
| Top FDV drivers (tornado) | public_volume_growth_yoy $254.7M-$4.26B; terminal_multiple $161.6M-$1.95B; fee_compression_lambda_monthly $289.6M-$1.34B (91% of swing-squared variance) | 17 inputs at registry / measured ranges; 0 reach the market FDV (`sensitivity`) |
| Protocol inflation cap / measured issuance | 2.50% cap; measured 32,748,205 NEAR/yr = 2.498% (89,660 NEAR/day) | `EXPERIMENTAL_protocol_config`; total_supply jumps at epoch starts |
| Validators / staked ratio | 352 / 44.36% (581,691,894 NEAR) | RPC `validators` |
| intents.near NEP state lock | 13,481,595,534 bytes = 134,816 NEAR locked; growth 291.0 NEAR/day over 30.8 d | `view_account` + storage_amount_per_byte (0.01 NEAR/KB); archival lookback for growth |
| NEAR Intents 30d volume (public / confidential) | $3.88B (n/a / n/a; confidential share 40.0%) | confidential share status `implausible_fallback`: NOT MEASURED; assumption: registry confidential_share = 40% (nearstats split implausible; not a measurement) |
| Gross take / net take / capture ratio | 15.26 bps / 5.00 bps / 32.7% | ONE canonical window: aligned daily charts, 30 complete UTC days 2026-10-09..2026-11-07 |
| Daily sinks vs issuance | buyback 17,817 NEAR + gas burn 873 NEAR + state lock 328 NEAR = 21.2% of 89,660 NEAR/day | supply_physics; buyback = V x tau x alpha / P |
| Breakeven daily volume V* (status quo / SVRN glidepath) | $642.6M / $408.1M per day (today $129.4M/day) | V* = (I - G - L) x P / (tau x alpha) at the regime's terminal rate |
| Live quote race, 1Click headroom vs best competitor (destination units) | ETH USDC -> SOL USDC: +0.98 bps median over 3 cells; ETH USDC -> native BTC: -5.68 bps median over 3 cells; Base USDC -> Arbitrum USDC: -1.02 bps median over 3 cells | 1Click vs Relay / LI.FI / Across at $500, $50,000, $250,000; competitor ceiling 3.00 bps on cross-VM; 2026-11-08T21:24:31.888Z |
| Deposit/caller HHI / solver HHI on intents.near | 3,555 (bootstrap 90% CI 2,383-5,000) / 6,256 (bootstrap 90% CI 5,037-7,537) (77 fill participations over 17,567 s); cartel trigger breached | NearBlocks receipts: 183 over 8 pages; AI-agent (name-pattern) share 56.2% |
| SOTP FDV P10 / P50 / P90 (36 m, discounted) | $57.2M / $262.9M / $1.65B vs current FDV $4.76B (-94.5% at P50) | 10,000 paths, seed 20261114; terminal multiple 60.0x (derived); deterministic (expected-path) FDV $817.9M |
| Bear case, combined worst (deterministic, median inputs) | $105.9M (-87%); triggers breached 2 of 4 measured | four falsification scenarios through deterministic_sotp; live early-warning metrics |
| Evidence scorecard | ASSUMPTION 1, DERIVED 2, NOT_SUPPORTED 1, VERIFIED_LIVE_API 4, VERIFIED_ON_CHAIN 2 | 10 graded claims in `IC_MEMO.md` section 11 |

12 methodology warning(s) recorded in this run; see `IC_MEMO.md` section 14.1.
<!-- VALUO:FINDINGS:END -->

---

## What this answers that the dashboards do not

`revenue.near.org`, `nearstats.org` and `svrn.net` already show headline NEAR Intents volume and cumulative fees. Valuo treats those as inputs and works on the questions an investment committee actually has to answer:

1. **What does the market price require?** The model is inverted one input at a time (brentq on the expected path): the growth, take, multiple, discount rate, confidential share or holder revenue that would make it equal the market FDV, each next to its evidence and marked inside or outside it. A tornado ranks the inputs by FDV swing, and a peer table ranks NEAR's FDV/fees and FDV/revenue against the live L1 set together with the staking security budget.
2. **Will competing routers compress the public take-rate to zero?** Measured, not argued: live executable quotes on the same corridor and clip, ranked on destination units delivered (BTC out per USDC in), with the competitor fee ceiling and 1Click's headroom per cell, including the cells where 1Click loses or returns no liquidity.
3. **Who actually settles on `intents.near`?** Two separately labeled populations: deposit/caller concentration over external predecessors (bridge callbacks, direct callers, name-pattern AI agents) and solver concentration decoded from `execute_intents` signer payloads, each as an HHI with a bootstrap 90% CI and the sample size and time span that bound it.
4. **What is the complete supply picture?** Issuance measured per epoch from `total_supply` jumps (not assumed from the cap), buybacks from DefiLlama holders revenue over the same window as the take-rate, L1 gas burn from within-epoch supply drift, and the NEP storage-staking lock (`storage_amount_per_byte` from protocol config) with growth measured from archival state.
5. **Under what conditions is the thesis wrong?** Four stress scenarios priced through the same deterministic SOTP, each with a live weekly early-warning metric and an explicit threshold; a metric that was not measured is reported as such, never as "not breached".

## Pillars

| Pillar | Live source (key-free) | Output |
| :--- | :--- | :--- |
| Execution microstructure | `1click.chaindefuser.com/v0/quote` (dry), `api.relay.link/quote`, `li.quest/v1/quote`, `app.across.to/api/suggested-fees` | per-cell headroom on destination units, one common price per cell for USD friction, competitor fee ceiling, capacity failures |
| Actor and solver forensics | `api.nearblocks.io` receipts, `nearstats.org` summary, `api.llama.fi` fees/revenue/dexs | deposit/caller HHI, solver HHI from NEP-413 payloads, canonical 30-day take-rate window, confidential share |
| Supply physics | `free.rpc.fastnear.com` (`block`, `validators`, `view_account`, protocol config), archival RPC | measured issuance, sinks, breakeven volume per regime, 36-month float trajectories, staking yield by regime |
| SOTP and bear case | DefiLlama peer fees/revenue, coins.llama.fi and CoinGecko valuations, the models above | three-engine SOTP, 10,000-path Monte Carlo (mean-matching GBM), 5x5 sensitivity grid, four falsification scenarios |
| Market-implied, tornado, relative value | the snapshot itself (no extra fetch) | input values the market FDV requires vs evidence, one-at-a-time FDV tornado over every ranged input, peer FDV/fees and FDV/revenue rank, security budget coverage |

## Method notes a reviewer should know

- Take rates (gross, net, capture ratio) are computed once, on the last 30 complete UTC days common to the DefiLlama fees, revenue and volume charts; every model consumes those fields instead of recomputing them.
- The Monte Carlo volume and price processes carry the Ito drift correction, so the labeled YoY growth is the growth of the expected path; the calibration block reports both the mean and the median terminal volume.
- Bear-case FDVs are deterministic values at median inputs, labeled as such (`bear_case.value_basis`); they are not Monte Carlo percentiles.
- Fallbacks are explicit, labeled `source: assumption` and warned: peer multiple (CoinGecko outage), price sigma (price-series outage), volume sigma (DefiLlama dexs-chart outage), confidential share (nearstats outage, or a nearstats split that its own payload contradicts: `intents_forensics.volume.confidential_share_status = implausible_fallback`, in which case the registry assumption `confidential_share` sizes Engine 2 and the memo, scorecard and README say NOT MEASURED). A missing 30-day volume or an unreachable NEAR RPC is fatal by design.
- The solver HHI (cartelization trigger) is graded on its bootstrap 90% CI (breached only if the lower bound clears 3,500, clear only if the upper bound is below it) and only when the solver sample spans at least `solver_sample_min_span_s` (3,600 s). A window of minutes is serially correlated and its CI covers within-window noise only, so a shorter sample grades the trigger `inconclusive`, never "not breached"; the cross-VM headroom condition can still breach it on its own.
- The reverse valuation solves on the deterministic expected path; the Monte Carlo P50 is lower by lognormal convexity, so every requirement it prints is the smaller (expected-path) one.
- Design and field contract: `docs/MODEL_DESIGN.md`; endpoint facts: `docs/LIVE_ENDPOINT_FACTS.md`; terminal spec: `TERMINAL_UI_SPEC.md`.

## Stack

- `quant/`: Python 3.11+, `httpx`, `pydantic` v2, `numpy`, `scipy`, `duckdb`, `pytest`; `uv` for the environment.
- `artifacts/`: `latest_snapshot.json` (canonical), `manifest.json` (SHA-256 of every raw payload and of the snapshot bytes, block height and hash), `IC_MEMO.md`, `raw/` payloads, `valuo.duckdb` convenience tables, `history/` (append-only run records and quote-race time series).
- `web/`: Next.js 15 (App Router), TypeScript, Tailwind, hand-rolled SVG charts, `/api/snapshot` and `/api/live-benchmark`.
