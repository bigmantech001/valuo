# TERMINAL_UI_SPEC.md — Institutional IC Research Terminal (`web/`)

## 1. Visual & UX Direction (`NetLayerLabs` Institutional Quant Standard)
Design **Valuo** like an internal **Dragonfly / Electric Capital / Blockworks Research Quantitative Terminal**—NOT a generic purple crypto landing page:
- **Palette:** Crisp deep obsidian (`#090B0E`) or clean institutional slate surface (`#0F1217`), `1px` hairline borders (`#1E2430`), high-contrast tabular typography (`JetBrains Mono` / `Geist Mono` with `font-variant-numeric: tabular-nums` on every number), semantic precision accents: Emerald (`#10B981`) for verified surplus/deflation, Amber (`#F59E0B`) for threshold warnings, Crimson (`#EF4444`) for dilution/bear stress, Cyan (`#06B6D4`) for NEAR Intents telemetry.
- **Persistent Top Data Provenance Bar:** Displays live NEAR Mainnet `Block Height` (e.g. `#221,435,028`), `Total Supply` (`1.31B NEAR`), `Protocol Inflation Cap` (`2.50%`), `intents.near State Lock` (`129,607 NEAR`), snapshot UTC timestamp, and a clickable **"Verify SHA-256 Manifest"** drawer + **"Export IC Memo (.md / .json)"** button.

---

## 2. The 5 Interactive Terminal Tabs

### Tab 1: Executive Thesis & Evidence Scorecard
- **The Quantitative Verdict Banner:** Summarizes Base-Case `P50` 36-Month Implied Valuation, `P10–P90` Confidence Interval, Current Annualized Intents Fee Run-Rate, and Exact Daily Intents Volume Required for Net Deflation under `2.5%` vs `1.6%` issuance.
- **Causal Chain Diagram / Flow Cards (Micro $\rightarrow$ Moat $\rightarrow$ Supply $\rightarrow$ SOTP):** Shows live verified numbers flowing from Execution Spread Advantage $\rightarrow$ Sustainable Buyback Capture $\rightarrow$ Issuance Offset $\rightarrow$ SOTP Multiple.
- **Evidence vs. Conviction Scorecard:** Table grading 6 core claims with `VERIFIED ON-CHAIN`, exact RPC/API source, and statistical confidence.

### Tab 2: Execution Alpha & Solver Microstructure Lab *(Idea 1 Live Engine)*
- **"Run Live Quote Race" Interactive Widget (`/api/live-benchmark`):**
  - Judge selects Corridor (`ETH USDC -> SOL USDC`, `ETH USDC -> Native BTC`, `Base USDC -> Arbitrum USDC`) and Clip Size (`$500`, `$50,000`, `$250,000`) and clicks **"Execute Live Quote Benchmark"**.
  - Fires live concurrent requests to **NEAR Intents (`1Click`)**, **Relay**, **LI.FI**, and **Across**, rendering net output, effective friction in `bps`, estimated settlement seconds, and **NEAR Pricing-Power Headroom (`+bps`)** in real time.
- **Corridor Moat Matrix:** Visualizes why `Across` wins/ties inside EVM-L2 (`~1.1 bps`), while **NEAR Intents dominates Cross-VM (`ETH <-> SOL`) and Native `BTC` / `ZEC` / `NEAR` corridors** where EVM-only intent bridges cannot settle.
- **On-Chain `intents.near` Actor & Solver Audit:** Displays empirical Caller Concentration (`HHI` gauge + Lorenz/share bar chart) and highlights live programmatic **AI Escrow (`escrow.ai.near`)** activity directly from `api.nearblocks.io` with clickable NearBlocks transaction links.

### Tab 3: Token Supply Physics & State-Lock Sink *(On-Chain Accounting)*
- **Interactive Issuance Regime Toggle:** Instant switch between:
  1. `Status Quo (2.50% Max Inflation — ~89,654 NEAR/day)`
  2. `SVRN Governance Glidepath (2.50% -> 1.60% over 24m — ~57,378 NEAR/day)`
  3. `Custom Governance Cap Slider (0.50% – 3.00%)`
- **36-Month Supply Trajectory & Net-Deflation Crossover Chart:** Plots Cumulative Gross Issuance vs. Cumulative Intents Open-Market Buybacks + L1 Gas Burn + NEP Storage-Staking Locks, pinpointing the exact **Crossover Quarter** where net circulating `$NEAR` turns deflationary.
- **Live NEP Storage-Staking Sink Audit (`1 NEAR per 100 KB`):** Live table from `free.rpc.fastnear.com` showing exact `storage_usage` bytes and permanently locked `$NEAR` across `intents.near` (`129,607+ NEAR`), `aurora` (`143,577+ NEAR`), `wrap.near`, `v1.signer`, plus an interactive **"AI Agent Scale Calculator"** (modeling state-locked `$NEAR` for `100K` to `10M` sub-account vaults).
- **Validator Security Budget Check:** Shows live staking ratio (`~45.3%` across `392` validators) and how real staking yield (`Nominal APR - Inflation`) actually *improves* for holders under the `1.6%` cut + buyback accrual while maintaining `~3.53%` nominal validator APR.

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
