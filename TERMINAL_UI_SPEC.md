# TERMINAL_UI_SPEC.md — Institutional IC Research Terminal (`web/`)

> **Status: original pre-build brief (Oct 2026), kept for the record.** The shipped terminal differs where the evidence or the design review required it: a light research-report theme instead of the dark palette below, six sections (a History section was added) in a left sidebar, and every number read from `artifacts/latest_snapshot.json`. This file quotes no live figures; where it names a metric, the current value is the snapshot field given in brackets. Where this brief and the artifacts disagree, the artifacts are right.

## 1. Visual & UX Direction (`NetLayerLabs` Institutional Quant Standard)
Design **Valuo** like an internal **Dragonfly / Electric Capital / Blockworks Research Quantitative Terminal**—NOT a generic purple crypto landing page:
- **Palette:** Crisp deep obsidian (`#090B0E`) or clean institutional slate surface (`#0F1217`), `1px` hairline borders (`#1E2430`), high-contrast tabular typography (`JetBrains Mono` / `Geist Mono` with `font-variant-numeric: tabular-nums` on every number), semantic precision accents: Emerald (`#10B981`) for verified surplus/deflation, Amber (`#F59E0B`) for threshold warnings, Crimson (`#EF4444`) for dilution/bear stress, Cyan (`#06B6D4`) for NEAR Intents telemetry.
- **Persistent Top Data Provenance Bar:** Displays live NEAR Mainnet `Block Height` [`near_rpc.block_height`], `Total Supply` [`near_rpc.total_supply_near`], `Protocol Inflation Cap` [`near_rpc.max_inflation_rate`], `intents.near` state lock [`near_rpc.tracked_sinks`], snapshot UTC timestamp, and a clickable **"Verify SHA-256 Manifest"** drawer + **"Export IC Memo (.md / .json)"** button.

---

## 2. The Terminal Sections (5 in the brief; a sixth, History, was added)

### Tab 1: Executive Thesis & Evidence Scorecard
- **The Quantitative Verdict Banner:** Summarizes Base-Case `P50` 36-Month Implied Valuation, `P10–P90` Confidence Interval, Current Annualized Intents Fee Run-Rate, and Exact Daily Intents Volume Required for Net Deflation under `2.5%` vs `1.6%` issuance.
- **Causal Chain Diagram / Flow Cards (Micro $\rightarrow$ Moat $\rightarrow$ Supply $\rightarrow$ SOTP):** Shows live verified numbers flowing from Execution Spread Advantage $\rightarrow$ Sustainable Buyback Capture $\rightarrow$ Issuance Offset $\rightarrow$ SOTP Multiple.
- **Evidence vs. Conviction Scorecard:** Table grading 6 core claims with `VERIFIED ON-CHAIN`, exact RPC/API source, and statistical confidence.

### Tab 2: Execution Alpha & Solver Microstructure Lab *(Idea 1 Live Engine)*
- **"Run Live Quote Race" Interactive Widget (`/api/live-benchmark`):**
  - Judge selects Corridor (`ETH USDC -> SOL USDC`, `ETH USDC -> Native BTC`, `Base USDC -> Arbitrum USDC`) and Clip Size (`$500`, `$50,000`, `$250,000`) and clicks **"Execute Live Quote Benchmark"**.
  - Fires live concurrent requests to **NEAR Intents (`1Click`)**, **Relay**, **LI.FI**, and **Across**, rendering net output, effective friction in `bps`, estimated settlement seconds, and **NEAR Pricing-Power Headroom (`+bps`)** in real time.
- **Corridor Moat Matrix:** Shows, per corridor archetype, whether 1Click out-delivers the best competitor on destination units [`execution_bench.headroom_by_archetype_bps`]. The brief assumed 1Click would dominate cross-VM and native-BTC routes. The live race does not support that for native BTC: 1Click leads on cross-VM (`ETH USDC -> SOL USDC`) and trails Relay on native BTC and on EVM L2, and the terminal grades those claims accordingly (native BTC: `NOT_SUPPORTED`). Across cannot route native BTC/SOL, so it is recorded as unsupported there, not as a loss.
- **On-Chain `intents.near` Actor & Solver Audit:** Displays empirical Caller Concentration (`HHI` gauge + Lorenz/share bar chart) and highlights live programmatic **AI Escrow (`escrow.ai.near`)** activity directly from `api.nearblocks.io` with clickable NearBlocks transaction links.

### Tab 3: Token Supply Physics & State-Lock Sink *(On-Chain Accounting)*
- **Interactive Issuance Regime Toggle:** Instant switch between:
  1. `Status Quo (2.50% max inflation)` [`near_rpc.gross_daily_issuance_near`]
  2. `SVRN Governance Glidepath (2.50% -> 1.60% over 24m)` [`near_rpc.gross_daily_issuance_svrn_near`]
  3. `Custom Governance Cap Slider (0.50% – 3.00%)`
- **36-Month Supply Trajectory & Net-Deflation Crossover Chart:** Plots Cumulative Gross Issuance vs. Cumulative Intents Open-Market Buybacks + L1 Gas Burn + NEP Storage-Staking Locks, pinpointing the exact **Crossover Quarter** where net circulating `$NEAR` turns deflationary.
- **Live NEP Storage-Staking Sink Audit (`1 NEAR per 100 KB`):** Live table from `free.rpc.fastnear.com` showing exact `storage_usage` bytes and locked `$NEAR` across `intents.near`, `aurora`, `wrap.near`, `v1.signer` [`near_rpc.tracked_sinks`, `near_rpc.total_state_locked_near`], plus an interactive **"AI Agent Scale Calculator"** (modeling state-locked `$NEAR` for `100K` to `10M` sub-account vaults).
- **Validator Security Budget Check:** Shows the live staking ratio and validator count [`near_rpc.staked_supply_ratio`, `near_rpc.active_validator_count`] and the nominal validator APR under 2.5% and under the 1.6% SVRN cut [`near_rpc.nominal_staking_apr_current`, `near_rpc.nominal_staking_apr_svrn_1_6`].

### Tab 4: 3-Engine SOTP Valuation & 10,000-Path Monte Carlo *(Idea 2 Live Engine)*
- **Interactive Parameter Sliders (Client + Server Synced):**
  - Public Intents YoY Volume Growth (`-20%` to `+150%`)
  - Blended Public Fee Capture (`1 bps` to `20 bps` — bounded with a visual marker showing Collector 2's live measured competitive ceiling!)
  - Confidential Shard Dark-Pool Share (`5%` to `35%` at `15–25 bps`)
  - Buyback Allocation Ratio (`0%` to `50%`)
  - Issuance Schedule (`2.5%` vs `1.6%`)
- **Monte Carlo Fan Chart (`P10 / P25 / P50 / P75 / P90`):** 36-month stochastic fan chart calibrated to historical `$NEAR` volatility.
- **Sum-of-the-Parts Valuation Waterfall & Peer Comps Table:** Compares `$NEAR` against live `DefiLlama` metrics for **Solana (`SOL`)**, **Ethereum (`ETH`)**, and **Hyperliquid (`HYPE`)** on `FDV / Annualized Gross Fees` and `FDV / Holder Revenue`.
- **$5 \times 5$ Sensitivity Heatmap:** `Daily Intents Volume ($100M -> $1.5B/day)` $\times$ `Net Protocol Take-Rate (2 bps -> 18 bps)` highlighting Net-Deflationary cells in emerald border.

### Tab 5: Steel-Manned Bear Case & Falsifiability Matrix
- *"Judged on evidence, not conviction"* means explicitly proving what would **invalidate** our thesis.
- Renders **4 Quantified Stress Scenarios** (*Fee Race to 1 Pip*, *Governance Rejects 1.6% Cut*, *Post-`NEAR@3.33` Incentive Cliff*, *Solver Cartelization `HHI > 3,500`*), showing exact drawdown impact on SOTP fair value and the **On-Chain Early Warning Triggers** an institutional desk should monitor weekly.
