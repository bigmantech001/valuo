# Valuo IC Memo: NEAR at block 224,186,938

*NEAR Intents clearinghouse + NEAR L1. Generated 2026-11-12T08:05:22.348Z UTC from live mainnet RPC and key-free public APIs; every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section 14.*

| Provenance | Value |
| :--- | :--- |
| NEAR block | 224,186,938 (`5c3Znz53wUQberz5EEcVCAmeNmFNhzGNHDCavfyEmtCk`), 2026-11-12T08:05:20.527Z |
| RPC endpoint | https://free.rpc.fastnear.com |
| Snapshot generated | 2026-11-12T08:05:22.348Z UTC, runtime 469.7 s, valuo 0.1.0, schema 1.0.0 |
| Snapshot SHA-256 | `14c76062482ec8fd0f9e4294d1e7d5a8902c7c81f84266a6cc098d7536e3a562` |
| Monte Carlo | seed 20261114, 10,000 paths, 36 months |
| Raw records | 223 HTTP/RPC exchanges hashed, 31 non-2xx/failed (every one listed in manifest.json) |


## 1. The long-term case, made falsifiable

The long-term case for NEAR at $4.60B: 3 of 8 measured conditions are on track. It holds if the market keeps an L1 multiple (140x revenue needed against a 2,514x peer median) while Intents grows into it; it fails if volume growth stays near 22% a year against the 130% the price implies.

| Condition | Required | Live | Trend | Status |
| :--- | ---: | ---: | :--- | :--- |
| Intents volume compounds fast enough to grow into the price | 130% a year | 22% a year | +89% (30-day volume vs 90 days earlier) | **Behind** |
| Holder revenue (buybacks) scales to support the price at the model's multiple | $165.6M a year | $22.1M a year | +289% (30-day holder revenue vs 90 days earlier) | **Behind** |
| The market keeps valuing NEAR like an L1, not like a fee-only app | 140x | 2,514x | n/a | **On track** |
| 1Click keeps a pricing edge where it competes (cross-VM routes) | > 0 | +2.14 bps | n/a | **On track** |
| Confidential (private) flow keeps growing | > 0 | $13.3M | +372% (confidential TVL vs 90 days earlier) | **On track** |
| Fees retire more NEAR than issuance creates | $408.9M a day | $124.4M a day | n/a | **Behind** |
| Governance cuts issuance from 2.5% to 1.6% | 1.6% | 2.5% | n/a | **Behind** |
| Solver competition stays broad enough to keep spreads tight | <= 3,500 | 5,349 | n/a | **Against** |


How to read it: each requirement is what the market price needs if that condition alone carries the case (from the reverse valuation in section 3), or the threshold the bear case watches (section 11). An investor holding NEAR long-term is betting that the conditions marked Behind close; the ones marked Against are where the case is currently losing. Re-run `make reproduce` to re-grade every row against live data.

## 2. Executive summary

**Model value vs market value.** Market FDV is $4.60B (spot price x on-chain total supply at block 224,186,938). The model's expected-path FDV is $2.03B and its 10,000-path Monte Carlo gives P10 / P50 / P90 = $131.0M / $668.5M / $4.04B. The market sits above the expected path (2.3x it) and at 6.9x the Monte Carlo P50. The model capitalises NEAR Intents holder revenue, L1 gas burn and state-lock flow over 36 months at a 25% discount rate and a 60x terminal multiple; the question below is which input would have to change for it to reach the market price, and whether the evidence allows that.

**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in section 3).

| Input | Base | Required for market FDV | Evidence | Inside evidence |
| :--- | ---: | ---: | ---: | :--- |
| Expected annual public-volume growth (3-year path) | 67.5% | 130.3% | 21.8% | no |
| Starting gross public take rate | 15.24 bps | 59.64 bps | 3.00 bps | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 140x | 2,514x | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $3.93B) | 10.0% | n/a |
| Confidential share of volume at month 36 | 40.0% | 76.7% | 13.1% | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $70.8M/yr | $165.6M/yr | $22.1M/yr | no |


**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple (140x needed; live peer FDV/revenue HYPE 81x, SOL 2,514x, ETH 3,303x, median 2,514x over n = 3 peers). No discount rate closes the gap: even at 0% the model reaches $3.93B against the market's $4.60B, because the terminal multiple is capped at 60x. The gap is a multiple question, not a discount-rate question. The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on Intents cash flow at the model's 60x terminal cap. On cash flow alone (multiple held at the model's 60x), the market price requires 130%/yr expected public-volume growth for 3 years (trailing 12 months: +21.8%), or a 60 bps starting public take (today 15.24 bps, live competitive ceiling 3.00 bps), or $165.6M of annualised holder revenue in year 3 (7.5x today's $22.1M); none of these is inside its measured evidence. Whether NEAR keeps an L1 multiple is the investment question; this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token.

**What you have to believe** (section 4). The three inputs that move FDV most are Expected annual public-volume growth (8.6% to 158.5%: $685.0M-$6.21B); Terminal FDV / holder-revenue multiple (8.00x to 150x: $357.0M-$4.93B); Public take compression speed (per month) (0.0%/month to 15.0%/month: $774.4M-$3.45B). Together they carry 86% of the swing-squared variance proxy. 2 of 17 single-input ranges reach the market FDV.

**Relative value** (section 5). NEAR trades at 64x annualised fees against a peer median of 257x (rank 2 of 4, lowest multiple first; inside the peer range); at peer FDV/fees multiples NEAR's fees map to $11.50B-$46.33B (cross-check, not a fair value; n = 3 peers); holder revenue covers 20% of the $115.0M/yr security budget.

**Evidence quality flags.**

- Confidential share: ESTIMATED ON-CHAIN at 13.1% (band 11.6%-14.8%). nearstats reported 0.0000%, which its own payload contradicts, so the share is read from the Confidential Intents Treasury instead: 24h inflow $14.8M, outflow $16.7M, against 24h volume $113.1M. Same-hour netting and in-shard turnover bias it down, solver inventory up; one 24h window. Engine 2 ($849.7M of the $2.03B expected-path FDV) is valued on this estimate, not on the 40% registry assumption. On-chain cross-check: the Confidential Intents treasury (`51e8f94d...de7cbe` in `intents.near`) holds $136.7M at block 224,186,953 (204 tokens, 30 unpriced); net 30-day boundary flow $13.3M at today's prices; over 24h at least $14.8M entered and $16.7M left (hourly snapshots, lower bounds), an inflow of 11.6% of 24h volume. Confidential swaps settle on a private chain whose RPC needs authentication, so swap volume itself cannot be read; boundary inflow is a proxy, not the share (it nets same-hour flows and includes solver inventory).
- Deposit/caller HHI 2,687 (bootstrap 90% CI 1,690-3,961) over 19 external receipts spanning 34 s; a point sample, not a market-share estimate.
- Solver HHI 5,349 (bootstrap 90% CI 4,831-5,913) over 85 fill participations spanning 34,896 s. Cartel trigger: BREACHED (sample: 85 solver fill participations over 34,896 s).
- Bear case: 2 of 4 graded early-warning triggers breached. Combined-worst deterministic FDV $176.0M (-91%).

## 3. What the market is pricing (reverse valuation)

Basis: deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base. Solver: scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12. Market FDV $4.60B; expected-path model FDV $2.03B (gap 2.3x); Monte Carlo P50 $668.5M (gap 6.9x). Every required value is the expected-path requirement; the P50 sits lower by lognormal convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).

| Input | Base | Required for market FDV | Evidence | Evidence basis | Inside evidence |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Expected annual public-volume growth (3-year path) | 67.5% | 130.3% | 21.8% | trailing-12-month NEAR Intents 30-day volume growth | no |
| Starting gross public take rate | 15.24 bps | 59.64 bps | 3.00 bps | live competitive fee ceiling (median best-competitor friction, cross-VM cells) | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 140x | 2,514x | peer median FDV / annualised revenue ex-NEAR (unclipped) | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $3.93B) | 10.0% | low end of the registry discount-rate range (10%-40%) | n/a |
| Confidential share of volume at month 36 | 40.0% | 76.7% | 13.1% | on-chain estimate of the confidential share (Confidential Intents Treasury 24h boundary flow / 24h volume) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $70.8M/yr | $165.6M/yr | $22.1M/yr | current annualised holder revenue (30-day window x 365.25/30) | no |

- Justifying $4.60B needs 130% expected annual public-volume growth for 3 years (base 68%); trailing-12-month Intents volume growth was 22%.
- Justifying $4.60B needs a starting gross public take of 59.6 bps (decaying to the 2.14 bps floor at 3%/month) versus 15.24 bps today; the live competitive fee ceiling is 3.00 bps.
- Justifying $4.60B needs a 140x terminal FDV/holder-revenue multiple; the live peer median is 2,514x (HYPE 81x, SOL 2,514x, ETH 3,303x) and the model caps it at 60x.
- Even a 0% discount rate gives $3.93B, short of $4.60B: the gap is not a discount-rate question.
- Justifying $4.60B needs the confidential share to reach 77% by month 36; the on-chain estimate today is 13% (band 12%-15%).
- Justifying $4.60B at the 60x base multiple needs $166M of annualised holder revenue in year 3 (2.3x the base path's $71M), versus $22M today (96%/yr compounded).

Headline: Market FDV $4.60B is 2.3x the model's expected-path FDV $2.03B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 140x (evidence 2,514x).

Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the joint requirement is smaller than any single one; section 4 shows which inputs carry the variance.

## 4. What you have to believe (one-at-a-time sensitivity)

Basis: deterministic_sotp expected path; one input at its low / high, all others at the snapshot base. Base expected-path FDV $2.03B against a $4.60B market FDV. Variance share: swing^2 / sum(swing^2): first-order share for independent inputs, an approximation. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).

| # | Input | Source | Range | Base | FDV at low | FDV at high | Swing | Variance share |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Expected annual public-volume growth | measured | 8.6% - 158.5% | 67.5% | $685.0M | $6.21B | $5.52B | 44.5% |
| 2 | Terminal FDV / holder-revenue multiple | derived | 8.00x - 150x | 60x | $357.0M | $4.93B | $4.58B | 30.6% |
| 3 | Public take compression speed (per month) | assumption | 0.0%/month - 15.0%/month | 3.0%/month | $3.45B | $774.4M | $2.68B | 10.5% |
| 4 | Confidential share at month 36 | assumption | 5.0% - 60.0% | 40.0% | $1.28B | $2.90B | $1.62B | 3.8% |
| 5 | Annual discount rate | assumption | 10.0% - 40.0% | 25.0% | $2.96B | $1.46B | $1.50B | 3.3% |
| 6 | Starting 30-day Intents volume (public + confidential) | measured | 0.71x - 1.40x | 1.00x | $1.48B | $2.80B | $1.32B | 2.5% |
| 7 | Holder capture (revenue / gross fees) | measured | 13.2% - 31.2% | 30.5% | $945.8M | $2.08B | $1.13B | 1.9% |
| 8 | Confidential multiple haircut | assumption | 30.0% - 100.0% | 70.0% | $1.57B | $2.38B | $812.5M | 1.0% |
| 9 | NEAR price drift (gas-burn and state-lock USD value) | assumption | -50.0% - 100.0% | 0.0% | $1.94B | $2.60B | $662.6M | 0.6% |
| 10 | Confidential gross take (public take re-reconciled to live fees) | assumption | 10.00 bps - 30.00 bps | 20.00 bps | $1.71B | $2.35B | $642.8M | 0.6% |
| 11 | Confidential compression divisor | assumption | 1.00x - 10x | 3.00x | $1.69B | $2.21B | $520.1M | 0.4% |
| 12 | Blended gross take (public take re-reconciled) | measured | 12.40 bps - 16.94 bps | 15.86 bps | $1.80B | $2.11B | $302.7M | 0.1% |
| 13 | Public take hard floor | assumption | 0.00 bps - 5.00 bps | 0.50 bps | $2.03B | $2.33B | $293.7M | 0.1% |
| 14 | Cross-VM headroom (sets the public take floor) | measured | 1.61 bps - 2.68 bps | 2.14 bps | $1.98B | $2.09B | $110.0M | 0.0% |
| 15 | NEAR spot price (USD value of gas burn and state lock) | measured | $2.61 - $4.72 | $3.51 | $2.00B | $2.07B | $68.5M | 0.0% |
| 16 | L1 gas burn (NEAR/day) | measured | 545 NEAR/day - 909 NEAR/day | 727 NEAR/day | $2.01B | $2.06B | $56.0M | 0.0% |
| 17 | State-lock growth (NEAR/day) | measured | 252 NEAR/day - 421 NEAR/day | 336 NEAR/day | $2.03B | $2.03B | $1.0M | 0.0% |

Top three inputs carry 86% of the variance proxy. 2 of 17 single-input ranges reach the market FDV at either end.

Headline: public_volume_growth_yoy, terminal_multiple, fee_compression_lambda_monthly carry 86% of the swing-squared variance proxy; public_volume_growth_yoy alone moves FDV from $685M to $6.21B across its range, and 2 of 17 single-input ranges reach the $4.60B market FDV.

Excluded (move issuance and implied price, not FDV): svrn_target_inflation (issuance path only: moves supply at horizon and implied price, not FDV); svrn_glidepath_months (issuance path only: moves supply at horizon and implied price, not FDV).

## 5. Relative value: peer cash-flow multiples and the security budget

Basis: live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR.

### 5.1 NEAR cash-flow coverage against the peer set
| Metric | NEAR | Peer median | Peer P25 - P75 | NEAR rank | Position |
| :--- | ---: | ---: | ---: | ---: | :--- |
| FDV / annualised fees (30-day run-rate) | 64x | 257x | 160x - 644x | 2 of 4 | inside the peer range |
| FDV / annualised revenue (30-day run-rate) | 199x | 2,514x | 1,298x - 2,909x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day fees | 84x | 229x | 152x - 828x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day revenue | 450x | 2,090x | 1,095x - 3,660x | 2 of 4 | inside the peer range |

| Protocol | FDV | Fees (ann.) | Revenue (ann.) | FDV/fees | FDV/revenue | FDV/fees 1y | FDV/revenue 1y | Revenue/fees |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SOL (solana) | $52.88B | $205.5M | $21.0M | 257x | 2,514x | 229x | 2,090x | 10% |
| ETH (ethereum) | $250.54B | $243.2M | $75.8M | 1,030x | 3,303x | 1,428x | 5,230x | 31% |
| HYPE (hyperliquid) | $67.95B | $1.09B | $837.4M | 62x | 81x | 76x | 100x | 77% |
| NEAR (near_combined) | $4.60B | $72.0M | $23.1M | 64x | 199x | 84x | 450x | 32% |
| NEAR (near) | $4.60B | $1.6M | $1.1M | 2,818x | 4,025x | 3,966x | 5,661x | 70% |
| NEAR (near-intents) | $4.60B | $70.3M | $21.9M | 65x | 210x | 85x | 489x | 31% |

The model's terminal multiple is 60x; 0 of 3 peers trade at or below it on FDV/revenue.

### 5.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)
| Cash flow | NEAR (ann.) | at peer P25 | at peer median | at peer P75 | Peers | Basis |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| fees | $72.0M | $11.50B | $18.52B | $46.33B | 3 | comps.near_combined.annualized_fees_usd x peer FDV / annualised fees (30-day run-rate) |
| revenue | $23.1M | $29.95B | $58.02B | $67.13B | 3 | comps.near_combined.annualized_revenue_usd x peer FDV / annualised revenue (30-day run-rate) |

relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution; market FDV $4.60B.

### 5.3 Staking and security budget
- Security budget: 32,766,005 NEAR/yr of issuance (2.50%) x $3.51 = $115.0M/yr (2.50% of FDV).
- Against it: $72.0M/yr of fees (63% of the budget) and $23.1M/yr of holder revenue (20%); net dilution $91.9M/yr.
- Staked 44.4% of supply; nominal staking APR 5.63%. Basis: security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate.

### 5.4 Findings
- NEAR trades at 64x annualised fees versus a peer median of 257x (rank 2 of 4, lowest first; inside the peer range); on revenue it is 199x versus 2,514x (inside the peer range).
- 0 of 3 peers trade at or below the model's 60x terminal FDV/revenue multiple; NEAR itself trades at 199x.
- At the peer FDV/fees distribution, NEAR's $72M of annualised fees maps to $11.50B-$46.33B (median $18.52B, n = 3) against a $4.60B market FDV; a relative-value cross-check, not a fair value.
- NEAR issues $115M a year to validators and delegators (2.5% of FDV) against $72M of annualised fees and $23M of holder revenue (gas burn + Intents buyback): revenue covers 20% of the security budget.
- At 2.5% inflation stakers earn 5.63% nominal and 3.61% real including buybacks; non-stakers lose 2.02% a year to dilution net of buybacks.

Caveat: Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples compare different cash-flow definitions; with n = 3 peers the median is a reference point, not a distribution.

## 6. Model valuation detail

**Base case.** 10,000-path SOTP (seed 20261114): P10 / P50 / P90 FDV = $131.0M / **$668.5M** / $4.04B; implied price $0.10 / **$0.49** / $2.95 per NEAR against spot $3.51. The P50 sits 85.5% below the current FDV of $4.60B. The deterministic SOTP at the labeled inputs (the expected-volume path) is $2.03B: engines $1.07B clearinghouse + $849.7M confidential + $114.1M monetary; the Monte Carlo mean is $1.93B. Ex-monetary P50: $641.6M.

**Volume growth is measured, not assumed.** Trend growth of NEAR Intents daily volume over 2025-11-12 to 2026-11-11 (365 days, DefiLlama): +67.5%/yr, 90% CI +9% to +158% (OLS of log volume on time, Newey-West errors). The model uses it as public_volume_growth_yoy, with the CI as its range; it is the median trend, so reading it as expected growth is conservative. Cross-checks, not used: yoy trailing 30d +53%, mean monthly log return 12m +30%.



**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled +68% YoY volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of 0.338 the MEDIAN simulated path ends month 36 at 12.9% of the expected path ($65.8M/day vs $511.5M/day), which is what pulls the P50 FDV below the mean. The dispersion is measured from 11 monthly volume log-returns (sigma excluding the three oldest, incentive-era windows: 0.323); a thin sample, reported as such.

**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation; section 3 solves which single input would: Market FDV $4.60B is 2.3x the model's expected-path FDV $2.03B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 140x (evidence 2,514x). The P90 ($4.04B) comes from volume paths, not from take-rate expansion (the public take only compresses in this model).

**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** 6 bps net take needs >= $1.00B/day; 10 bps net take needs >= $500.0M/day; 14 bps net take needs >= $500.0M/day; 18 bps net take needs >= $250.0M/day. Live run-rate: $125.3M/day at 4.84 bps net (15.86 bps gross x capture 30.5%).

**Net-float crossover.** Today sinks cover 20.4% of measured issuance (18,325 NEAR/day vs 89,708 NEAR/day). status quo (cap flat): deterministic flow crossover none within horizon at run-rate volume, none within horizon with the +68% YoY growth assumption; Monte Carlo P(crossover within 36m) = 65.3%, P(deflationary at horizon) = 47.3%; breakeven volume V* = $643.3M/day (5.1x today). SVRN glidepath: deterministic flow crossover none within horizon at run-rate volume, month 30 with the +68% YoY growth assumption; Monte Carlo P(crossover within 36m) = 72.6%, P(deflationary at horizon) = 55.3%; breakeven volume V* = $408.9M/day (3.3x today). The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price outruns issuance); the deterministic path (the expected-volume path) is the one to quote.

**Falsification.** Four stress scenarios (section 11) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo percentile) at $176.0M (-91% vs the deterministic base $2.03B); 2 of 4 measured early-warning triggers are breached in this snapshot (breached: governance_stalemate (max_inflation_rate now 2.50% vs > 1.60%); solver_cartelization (hhi_solver now 5,349 vs > 3,500)). The on-chain inflation cap reads 2.50%; the SVRN cut is a proposal, not protocol state.

## 7. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)

Executable quotes fetched 2026-11-12T08:05:30.847Z UTC (29 ok of 36; 1Click token universe 230 assets on 39 chains). Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input (headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price (`price_basis`: oneclick_token_list_oracle); raw-unit friction is exact for USDC -> USDC. Positive headroom means 1Click paid out more after all fees.

| Corridor | Clip | Venue | Status | Out | Friction | ETA | Route |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | 1click | ok | 499.950145 | 1.00 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $500 | relay | ok | 499.829683 | 3.41 bps (raw) | 1 s | relay |
| ETH USDC -> SOL USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $500 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $50,000 | 1click | ok | 49,995.683396 | 0.86 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $50,000 | relay | ok | 49,984.979683 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $50,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $250,000 | 1click | ok | 249,949.492624 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $250,000 | relay | ok | 249,924.979683 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $250,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | 1click | ok | 0.006760 | 45.58 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $500 | relay | ok | 0.006776 | 23.15 bps (usd) | 332 s | relay |
| ETH USDC -> native BTC | $500 | lifi | ok | 0.006764 | 40.19 bps (usd) | 1,177 s | layerswap |
| ETH USDC -> native BTC | $500 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | 1click | ok | 0.677910 | 18.09 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $50,000 | relay | ok | 0.678259 | 12.96 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $50,000 | lifi | ok | 0.677605 | 22.60 bps (usd) | 1,192 s | layerswap |
| ETH USDC -> native BTC | $50,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | 1click | ok | 3.384225 | 33.78 bps (usd) | 492 s | 1click-solver-network |
| ETH USDC -> native BTC | $250,000 | relay | no_liquidity: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | lifi | ok | 3.380813 | 43.83 bps (usd) | 1,392 s | near (= NEAR Intents resold via LI.FI) |
| ETH USDC -> native BTC | $250,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | 1click | ok | 499.913199 | 1.74 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $500 | relay | ok | 499.927522 | 1.45 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $500 | across | ok | 499.942684 | 1.15 bps (raw) | 2 s | across |
| Base USDC -> Arbitrum USDC | $50,000 | 1click | ok | 49,990.280084 | 1.94 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $50,000 | relay | ok | 49,994.977521 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $50,000 | across | ok | 49,994.992684 | 1.00 bps (raw) | 120 s | across |
| Base USDC -> Arbitrum USDC | $250,000 | 1click | ok | 249,949.497300 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $250,000 | relay | ok | 249,974.977524 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $250,000 | across | ok | 249,974.992684 | 1.00 bps (raw) | 900 s | across |


| Corridor | Clip | Headroom | Basis | 1Click rank | Reading |
| :--- | ---: | ---: | :--- | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | +2.41 bps | dest_units | 1/3 | 1Click delivers 2.41 bps more than relay |
| ETH USDC -> SOL USDC | $50,000 | +2.14 bps | dest_units | 1/3 | 1Click delivers 2.14 bps more than relay |
| ETH USDC -> SOL USDC | $250,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> native BTC | $500 | -22.48 bps | dest_units | 3/3 | 1Click trails relay by 22.48 bps |
| ETH USDC -> native BTC | $50,000 | -5.14 bps | dest_units | 2/3 | 1Click trails relay by 5.14 bps |
| ETH USDC -> native BTC | $250,000 | +10.09 bps | dest_units | 1/2 | 1Click delivers 10.09 bps more than lifi |
| Base USDC -> Arbitrum USDC | $500 | -0.59 bps | dest_units | 3/4 | 1Click trails across by 0.59 bps |
| Base USDC -> Arbitrum USDC | $50,000 | -0.94 bps | dest_units | 3/4 | 1Click trails across by 0.94 bps |
| Base USDC -> Arbitrum USDC | $250,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |


- cross_vm: median headroom +2.14 bps over 3 comparable cells
- native_btc: median headroom -5.14 bps over 3 comparable cells
- evm_l2: median headroom -0.94 bps over 3 comparable cells
- competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = 3; per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding): 3.00 bps. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not.

- Where 1Click loses (destination units): eth_usdc_btc at $500 trails relay by 22.48 bps; eth_usdc_btc at $50,000 trails relay by 5.14 bps; base_usdc_arb_usdc at $500 trails across by 0.59 bps; base_usdc_arb_usdc at $50,000 trails across by 0.94 bps; base_usdc_arb_usdc at $250,000 trails across by 1.02 bps.
- Oracle caveat: on eth_usdc_sol_usdc at $500, eth_usdc_sol_usdc at $50,000, eth_usdc_sol_usdc at $250,000, eth_usdc_btc at $50,000, base_usdc_arb_usdc at $500, base_usdc_arb_usdc at $50,000, base_usdc_arb_usdc at $250,000 the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg comparison there would have been decided by oracles, which is why the ranking uses units.
- Structurally unsupported routes: across on eth_usdc_btc (declared), across on eth_usdc_sol_usdc (ROUTE_NOT_ENABLED).
- LI.FI's quote on eth_usdc_btc $250,000 routes through NEAR Intents itself (tool `near`), so it is 1Click execution plus LI.FI's fee, not an independent price.
- Collector summary: cross_vm (ETH USDC -> SOL USDC): $500: 1Click delivers 2.41 bps more than relay (rank 1/3, destination units); $50,000: 1Click delivers 2.14 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); unsupported: across (ROUTE_NOT_ENABLED). native_btc (ETH USDC -> native BTC): $500: 1Click trails 22.48 bps behind relay (rank 3/3, destination units); $50,000: 1Click trails 5.14 bps behind relay (rank 2/3, destination units); $250,000: 1Click delivers 10.09 bps more than lifi (rank 1/2, destination units); unsupported: across (Across is EVM-only; no Bitcoin route); relay no_liquidity at $250,000. evm_l2 (Base USDC -> Arbitrum USDC): $500: 1Click trails 0.59 bps behind across (rank 3/4, destination units); $50,000: 1Click trails 0.94 bps behind across (rank 3/4, destination units); $250,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units).

## 8. Concentration and agents on intents.near (NearBlocks receipts)

- Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = **2,687** (bootstrap 90% CI 1,690-3,961) (N_eff = 3.72); over all predecessors 4,027; ex-AI-agent 1,600 (N_eff 6.25). These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.
- (b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = **5,349** (bootstrap 90% CI 4,831-5,913) (N_eff 1.87) across 85 fill participations in 83 fills (3 atomic token_diff fills, 80 solver-to-settlement-hub legs), 4 distinct solvers; 445 execute_intents receipts decoded, 0 unresolved; the solver sample spans 34,896 s. This is the population the solver_cartelization trigger reads; trigger status: breached.
- AI-agent share of external receipts 47.4% is a NAME-PATTERN classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. Bridge / token-contract share 36.8%; 9 unique external callers in 19 external receipts.
- Sample: 173 unique receipts over 8 NearBlocks pages, blocks 224,186,895-224,186,956, a 34 s window; lifetime receipts on intents.near 156,862,746. A window this short is a point sample, not a market-share estimate; both HHIs move by hundreds of points between runs.
- Method mix: TRANSFER 88, execute_intents 45, ft_resolve_withdraw 11, ft_transfer 8, ft_on_transfer 6, ft_transfer_call 3, near_withdraw 3, storage_deposit 2, do_storage_deposit 2, <no action> 1.

### 8.1 Deposit / caller concentration (external predecessors)
| Caller | Class | Receipts | Share | Example tx |
| :--- | :--- | ---: | ---: | :--- |
| escrow.ai.near | AI agent | 9 | 47.4% | [8cAA6Tcbq6xQ...](https://nearblocks.io/txns/8cAA6Tcbq6xQkUoJyGgLa1FQnhE35QtkciQYwvUpL4oG) |
| wrap.near | named account | 3 | 15.8% | [BKraWJuyrV9q...](https://nearblocks.io/txns/BKraWJuyrV9qgVRnd2an93HsGUfuPvfDxHvRuVpbGs89) |
| bnb-0x55d398326f99059ff775485246999027b3197955.omdep.near | bridge / token contract | 1 | 5.3% | [2gpYbBN4Yj24...](https://nearblocks.io/txns/2gpYbBN4Yj243QdYBZgyCD2hQpfaoETPLg2EQz9bi2Ev) |
| eth-0xdac17f958d2ee523a2206206994597c13d831ec7.omft.near | bridge / token contract | 1 | 5.3% | [HzMWw88EV8b9...](https://nearblocks.io/txns/HzMWw88EV8b9vT4mPw69QfFo1PuWtwZfiKiEsb54k2yp) |
| qtc.omft.near | bridge / token contract | 1 | 5.3% | [GMhRLsAhfVsu...](https://nearblocks.io/txns/GMhRLsAhfVsuqenZzkse6uJeNGwTgo4GorqDznsvug2d) |
| sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near | bridge / token contract | 1 | 5.3% | [GtK7FiC314A9...](https://nearblocks.io/txns/GtK7FiC314A9Fo9iJtaVgZZuabk68fmfm8riUmHHy7vA) |
| sol.omft.near | bridge / token contract | 1 | 5.3% | [4TpDxwYaToAw...](https://nearblocks.io/txns/4TpDxwYaToAwCJj2szeGvkdQ64FxGFUh9E2pAyhfXKhw) |
| tron-d28a265909efecdcee7c5028585214ea0b96f015.omft.near | bridge / token contract | 1 | 5.3% | [GuFrwh94LWWq...](https://nearblocks.io/txns/GuFrwh94LWWq4XUvsK8ySJ7JLjdHVo8bm3hAktc8ZxSd) |
| v2_1.omni.hot.tg | bridge / token contract | 1 | 5.3% | [CRGDCoKjB9LM...](https://nearblocks.io/txns/CRGDCoKjB9LMWyw8STFtVeGiFdJb756NTg2kbSnpaoML) |

### 8.2 Solver concentration (execute_intents signers)
| Solver account | Fill participations | Share | Example tx |
| :--- | ---: | ---: | :--- |
| solver-priv-liq.near | 58 | 68.2% | [271YhThLTDzj...](https://nearblocks.io/txns/271YhThLTDzjo9wqsozdLhUxkx5a5wfyh6UsyFyixa12) |
| solver-multichain-asset.near | 22 | 25.9% | [91sEhLf5wgEt...](https://nearblocks.io/txns/91sEhLf5wgEtc6FbiDcrmUfQTQPwNtjmsh9CfyKfo4TH) |
| 6247d9c671ca6a80cf2c75e26edb8cd75ebf00fcd3c56c39107d6ca20c9cfb29 | 4 | 4.7% | [9iCbViyaLJNS...](https://nearblocks.io/txns/9iCbViyaLJNSyGKG9JA5oQqQb673GRZYfDFQuynVZoJc) |
| solver-multichain-asset-3.near | 1 | 1.2% | [9URdQ2JS6YjV...](https://nearblocks.io/txns/9URdQ2JS6YjVYMcRcn1oYm8G121UrurgubrjD7tm1MMM) |

Attribution: fill participation = (a) the solver side of an atomic execute_intents fill (>= 2 token_diff signers; solver = pure token_diff signer when the counterparty bundles a withdrawal, else a signer whose name matches (*solver*, *-liq*, market maker) or that the structure rule identified elsewhere in the sample, else the named account facing an implicit 1Click deposit address), or (b) a transfer intent from a solver to the settlement hub (see settlement_hub.rule); HHI over participations per solver account; transfers that are not solver-to-hub legs are inventory or user moves, not fills. hhi_solver_ci90 is a bias-corrected bootstrap (bootstrap_method): a block bootstrap by NearBlocks page when the sample is stratified in time (bootstrap_resampling = block_by_page), else over sampled units

## 9. Supply physics

### 9.1 Issuance: measured vs nominal
- Measured: 25,454.65 NEAR minted at epoch start 224,178,737 (previous jump 26,438.74 NEAR at 224,135,537); epoch wall time 6.810 h = 1,287.2 epochs/yr; implied annual issuance **32,766,005 NEAR** = 2.4984% of supply.
- Nominal: max_inflation_rate 2.50% x total supply 1,311,498,639 NEAR = 32,787,466 NEAR/yr; measured minus nominal -21,461 NEAR/yr (-0.07%). Daily: measured 89,708 NEAR vs nominal 89,767 NEAR; treasury share 0.0% (validators receive the rest).
- Within-epoch supply drift (net gas burn) -206.35 NEAR/epoch; measured block time 0.567 s. Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.

### 9.2 Daily sinks (NEAR/day, live)
| Sink | NEAR/day | Source | Basis |
| :--- | ---: | :--- | :--- |
| Buyback (holders revenue / price) | 17,260.9 NEAR | measured | $125.3M/day x 15.86 bps gross x alpha 30.5% / $3.51 |
| L1 gas burn | 727.2 NEAR | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| NEP state-lock growth | 336.5 NEAR | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| Total sinks | 18,324.5 NEAR |  | coverage 20.4% of measured issuance; net float 71,384 NEAR/day |


### 9.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)
| Regime (terminal rate) | V* at live take | vs today | V* at competitive ceiling |
| :--- | ---: | ---: | ---: |
| status quo (cap flat) | $643.3M | 5.1x | $3.40B |
| SVRN glidepath | $408.9M | 3.3x | $2.16B |

Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.

### 9.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)
| Regime | Volume path | Issuance/day m1 | Issuance/day m36 | Gross issuance 36m | Sinks 36m | Net float 36m | Flow crossover | Cumulative crossover |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| status quo (cap flat) | run-rate volume | 89,708 NEAR | 96,482 NEAR | 101,965,428 NEAR | 20,079,118 NEAR | 81,886,310 NEAR | none within horizon | none within horizon |
| status quo (cap flat) | +68% YoY volume | 89,708 NEAR | 96,482 NEAR | 101,965,428 NEAR | 45,420,522 NEAR | 56,544,906 NEAR | none within horizon | none within horizon |
| SVRN glidepath | run-rate volume | 89,708 NEAR | 60,718 NEAR | 77,330,643 NEAR | 20,079,118 NEAR | 57,251,525 NEAR | none within horizon | none within horizon |
| SVRN glidepath | +68% YoY volume | 89,708 NEAR | 60,718 NEAR | 77,330,643 NEAR | 45,420,522 NEAR | 31,910,120 NEAR | month 30 | none within horizon |


### 9.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)
| Account | Contract | storage_usage bytes | Locked | Growth B/day | Growth NEAR/day | Window |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| intents.near | yes | 13,605,979,376 | 136,059.8 NEAR | 30,249,135 | 302.49 NEAR | 31.2 d |
| aurora | yes | 14,382,199,329 | 143,822.0 NEAR | 3,396,687 | 33.97 NEAR | 31.2 d |
| wrap.near | yes | 168,904,442 | 1,689.0 NEAR | n/a | n/a | n/a |
| v1.signer | yes | 1,164,606 | 11.6 NEAR | n/a | n/a | n/a |
| escrow.ai.near | no | 428 | 0.0 NEAR | n/a | n/a | n/a |
| treasury.near | yes | 357,895 | 3.6 NEAR | n/a | n/a | n/a |
| meme-cooking.near | yes | 5,957,847 | 59.6 NEAR | n/a | n/a | n/a |
| v2.ref-finance.near | yes | 111,293,440 | 1,112.9 NEAR | n/a | n/a | n/a |

- Total state-locked across 8 tracked contracts: **282,759 NEAR** at 0.01 NEAR/KB (storage_amount_per_byte 10,000,000,000,000,000,000 yocto). Measured lock growth 336.5 NEAR/day over intents.near, aurora (archival available).

### 9.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)
| Regime | Inflation | Nominal APR | Real APR | Buyback accrual | Real APR + accrual | Non-staker real |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| status quo (cap flat) | 2.50% | 5.63% | 3.13% | 0.481% | 3.61% | -2.02% |
| SVRN glidepath | 1.60% | 3.60% | 2.00% | 0.481% | 2.48% | -1.12% |

Live: 354 validators, 582,691,226 NEAR staked = 44.43% of supply.

### 9.7 Agent-scale state lock (locked = agents x KB x 0.01 NEAR/KB; default 20 KB per vault is an assumption)
| Agents | KB/agent | Locked | Days of issuance absorbed | Share of supply |
| ---: | ---: | ---: | ---: | ---: |
| 100,000 | 5 KB | 5,000 NEAR | 0.1 | 0.000% |
| 100,000 | 20 KB | 20,000 NEAR | 0.2 | 0.002% |
| 100,000 | 50 KB | 50,000 NEAR | 0.6 | 0.004% |
| 1,000,000 | 5 KB | 50,000 NEAR | 0.6 | 0.004% |
| 1,000,000 | 20 KB | 200,000 NEAR | 2.2 | 0.015% |
| 1,000,000 | 50 KB | 500,000 NEAR | 5.6 | 0.038% |
| 10,000,000 | 5 KB | 500,000 NEAR | 5.6 | 0.038% |
| 10,000,000 | 20 KB | 2,000,000 NEAR | 22.3 | 0.152% |
| 10,000,000 | 50 KB | 5,000,000 NEAR | 55.7 | 0.381% |


### 9.8 Chain Signatures (v1.signer): a second usage engine?
Sampled from 6 NearBlocks windows (600 receipts, 188 sign requests) over the trailing 30 days, v1.signer handled 16,754 sign requests/day over 7 days (SE 3,940) and 10,704/day over 30 days (SE 1,681). No trend was fitted (too few 00:00 UTC windows). Callers are concentrated: omni.bridge.near 45%, fast-auth.near 30%, btc-connector.bridge.near 7% of sampled requests; accounts under bridge.near send 58%, so much of this usage is bridging that overlaps Intents' cross-chain flow. A request attaches 1 yoctoNEAR, so the signer earns no fee; requesters pay gas, 0.0022 NEAR per request across sign, respond and callback receipts, 26.4 NEAR/day ($92.64/day), 100% of it burnt (live burnt_gas_reward 0% to the contract), 3.6% of the network gas burn and 0.03% of measured daily issuance (part of the L1 gas burn sink above, not an addition to it). The contract's storage lock is 11.6 NEAR. NearBlocks counts 26,402,136 cumulative v1.signer receipts; the rates are sample estimates, not exact counts.

## 10. Sum-of-the-parts valuation and peer comparables

### 10.1 Engines (percentiles over paths, USD; discounted to today)
| Engine | P10 | P25 | P50 | P75 | P90 | Assumption-heavy |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| clearinghouse | $31.8M | $79.8M | $229.1M | $690.5M | $1.89B | no |
| confidential | $20.5M | $54.1M | $169.3M | $566.8M | $1.68B | yes |
| monetary | $973,853 | $2.4M | $8.3M | $33.8M | $127.9M | yes |

| Total | P10 | P25 | P50 | P75 | P90 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| FDV (all engines) | $131.0M | $272.6M | $668.5M | $1.70B | $4.04B |
| FDV ex-monetary | $125.5M | $261.1M | $641.6M | $1.62B | $3.84B |
| Implied price / NEAR | $0.10 | $0.20 | $0.49 | $1.24 | $2.95 |

Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse $510.7M (76%) + confidential $101.0M (15%) + monetary $56.9M (9%) = $668.6M.

- PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor.
- Same construction on confidential volume at the assumed confidential take; terminal multiple x confidential_multiple_haircut because nearstats flags confidential TVL as unverified. Starting confidential share 13.1% is an on-chain estimate from Confidential Intents Treasury boundary flows (intents_forensics.volume.confidential_share_estimate), not nearstats' rejected split.
- PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.

### 10.2 Calibration (what the engines were fed)
| Parameter | Value | Source / basis |
| :--- | :--- | :--- |
| Public take t=0 (gross) | 15.24 bps | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d |
| Blended gross take / net take | 15.86 bps / 4.84 bps | DefiLlama near-intents fees / volume; net = gross x alpha |
| Capture ratio alpha | 30.49% | measured:defillama near-intents dailyHoldersRevenue / fees |
| Confidential take t=0 | 20 bps | assumption: registry confidential_take_bps (1Click confidential quotes need partner authentication) |
| Public take floor | 2.14 bps | derived; cross-VM headroom +2.14 bps, competitor ceiling 3.00 bps |
| Compression lambda (public / confidential) | 0.030 / 0.010 per month | geometric reversion to the floor |
| Volume growth (public / confidential, monthly) | 4.39% / 8.79% | confidential share 13.1% -> 40% target (start share ESTIMATED ON-CHAIN from Confidential Intents Treasury boundary flows) |
| Sigma: price (annual) / volume (monthly) | 1.025 / 0.338 | measured: monthly log-return sigma of 30-day volume aggregates; confidential sigma x 1.00 |
| Terminal multiple (FDV / annual holder revenue) | 60.0x (raw 2,513.9x) | source derived: peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; clipped to registry guardrails |
| Discount rate | 25% | assumption |
| Supply at horizon (glidepath) | 1,368,750,163 NEAR | fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory) |
| Current FDV | $4.60B | spot price x on-chain total_supply at the snapshot block; CoinGecko FDV via nearstats $4.61B (0.21% gap, struck at a different instant; cross-check only) |
| GBM convention | mean-matching (Ito) | mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM uses the same convention (zero drift => E[P_t] = P_0) |
| Terminal public volume, month H | mean $511.5M/day; median $65.8M/day | start $108.8M/day; MC sample mean $456.2M, median $63.7M; the labeled YoY growth is the growth of the MEAN path |


### 10.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)
| Protocol | Fees 30d | Revenue 30d | FDV | FDV/fees | FDV/revenue | Revenue methodology (live text) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| SOL (solana) | $16.9M | $1.7M | $52.88B | 257.3x | 2,513.9x | Transaction base fees paid by users |
| ETH (ethereum) | $20.0M | $6.2M | $250.54B | 1,030.2x | 3,303.2x | Amount of ETH burned — base fees plus blob fees (both are permanently burned, accruing to no proposer) |
| HYPE (hyperliquid) | $89.6M | $68.8M | $67.95B | 62.3x | 81.1x | Parent aggregates child protocols. Hyperliquid Perps: 99% of fees go to Assistance Fund for buying HYPE tokens |
| NEAR (near) | $134,174 | $93,923 | $4.60B | 2,817.7x | 4,025.2x | 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract developers |
| NEAR (near-intents) | $5.8M | $1.8M | $4.60B | 65.4x | 209.7x | NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.ne |
| NEAR (near_combined) | $5.9M | $1.9M | $4.60B | 63.9x | 199.3x | near: 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract deve |

- Median ex-NEAR FDV / annualized revenue 2,513.9x (n = 3); FDV / annualized fees 257.3x (n = 3). annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)
- `revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live methodology text is carried in the table so the multiple is read with its definition.

### 10.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take (SVRN glidepath; * = net-deflationary)
| Net take \ Volume/day | $100.0M | $250.0M | $500.0M | $1.00B | $1.50B |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2 bps | $263.0M | $610.1M | $1.19B | $2.35B | $3.50B* |
| 6 bps | $725.8M | $1.77B | $3.50B* | $6.97B* | $10.44B* |
| 10 bps | $1.19B | $2.92B* | $5.82B* | $11.60B* | $17.39B* |
| 14 bps | $1.65B | $4.08B* | $8.13B* | $16.23B* | $24.33B* |
| 18 bps | $2.11B | $5.24B* | $10.44B* | $20.86B* | $31.27B* |

Current FDV $4.60B; confidential share used in the split 13.1%. Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).

### 10.5 Out-of-sample backtest of the volume engine
At each of 20 monthly origins from 2025-03-21 to 2026-10-12 the volume GBM was re-calibrated on data up to the origin only (trailing 30-day volume, sigma from the trailing 365 days, drift = public_volume_growth_yoy 68%) and its P10-P90 band for 30-day volume was compared with what happened (defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json), 2024-12-10 to 2026-11-11). The test of 80% coverage fails at 1m, 3m, 6m (exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10). At 1 month the median realized volume is 1.37x the forecast median: the model under-predicts. Split at the middle origin (2026-01-15), coverage before: 1m 30% (n = 10), 3m 20% (n = 10), 6m 30% (n = 10); from it: 1m 90% (n = 10), 3m 100% (n = 7), 6m 100% (n = 4). 22 of the 23 misses come from origins before the split; 23 of 23 are realized volume above P90. With the drift replaced by the trailing mean log return (no registry input) coverage is 1m 60%, 3m 41%, 6m 14%. Not backtested: fee take rate (public and confidential) and its compression toward the floor; holder capture ratio alpha; confidential share of volume and its drift to the target share; terminal FDV/revenue multiple and discount rate; NEAR price and supply paths. 3- and 6-month forecasts from monthly origins overlap, so their errors are correlated and the binomial interval overstates the precision.

| Horizon | n | P10-P90 coverage [90% Wilson] | Binomial p vs 80% | Below P10 / above P90 | Median realized / P50 | PIT histogram (5 bins) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 1 month | 20 | 60% [42%-76%] | 0.04 | 0 / 8 | 1.37x | 1 4 2 2 11 |
| 3 months | 17 | 53% [34%-71%] | 0.01 | 0 / 8 | 1.86x | 0 2 2 4 9 |
| 6 months | 14 | 50% [30%-70%] | 0.01 | 0 / 7 | 3.89x | 1 0 3 1 9 |


## 11. Bear case and early-warning triggers

Value basis: deterministic at median inputs; not a Monte Carlo percentile. Base deterministic FDV (median inputs) $2.03B, implied price $1.49; the Monte Carlo P50 of section 10 is a different statistic and is not what the drawdowns below are measured against. drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed

| Scenario | Deterministic FDV (median inputs) | FDV drawdown | Implied price | Price drawdown | Flow crossover |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fee_race_to_zero | $320.1M | -84.3% | $0.23 | -84.3% | none within horizon |
| governance_stalemate | $2.03B | +0.0% | $1.46 | -1.8% | none within horizon |
| post_incentive_decay | $796.9M | -60.8% | $0.58 | -60.8% | none within horizon |
| solver_cartelization | $1.29B | -36.3% | $0.95 | -36.3% | none within horizon |
| combined worst | $176.0M | -91.3% | $0.13 | -91.5% | none within horizon |


### 11.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)
| Scenario | Metric | Now | Trigger | Status | Monitor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| fee_race_to_zero | net_take_bps_30d | 4.84 bps | < 3.00 bps | not breached | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue (sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days). |
| governance_stalemate | max_inflation_rate | 2.50% | > 1.60% | **BREACHED** | https://free.rpc.fastnear.com (EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)). Note: breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted |
| post_incentive_decay | volume_30d_vs_record_30d | -22.8% | <= -40.0% | not breached | https://nearstats.org/api/near/summary (intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1). |
| solver_cartelization | hhi_solver | 5,349 | > 3,500 | **BREACHED** | https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50 (HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)); secondary headroom_cross_vm_bps +2.14 bps < 0 bps (not breached). Note: sample: 85 solver fill participations over 34,896 s; HHI_solver 5,349, bootstrap 90% CI [4,831, 5,913] (CI lower bound 4,831 > 3,500: breached); deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = 2,687 |


### 11.2 Scenario narratives
**Aggregator bypass: public take races to 1 pip.** Third-party frontends route around near.com and the public gross take collapses from 15.2 bps to 0.01 bps (the bare intents.near contract fee); confidential execution reprices from 20 bps to 5 bps. Capture ratio alpha is held at 30%, so the hit is price, not allocation. Deterministic (median-input) FDV -84.3% to $320.1M; implied price $0.23. Evidence against it: live cross-VM headroom is +2.1 bps, so a bypassing frontend must first give up that execution edge. Trigger: DefiLlama 30d net take (gross x alpha) below 3.0 bps (now 4.8 bps).

**Governance stalemate: 2.5% issuance forever.** Validators never enact the SVRN cut: max_inflation_rate stays at 2.50% for the full horizon instead of gliding to 1.60%. Protocol cash flows do not change, so FDV moves +0.0%; the damage is dilution: 24,634,786 more NEAR outstanding at the horizon and a per-token value of $1.46 (-1.8% vs base). Net-float crossover: none within horizon (base: month 32). This scenario is live today: the on-chain cap reads 2.50% and no cut has been enacted.

**Post-incentive volume decay (NEAR@3.33 unwind).** Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume $108.8M -> $43.5M (-60%), confidential $16.4M -> $4.9M (-70%) and confidential TVL x0.3 (nearstats flags that TVL unverified). Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV -60.8% to $796.9M; implied price $0.58. Current 30d volume $3.73B is 77% of the 30d record $4.84B; the trigger fires at -40%.

**Solver cartelization: HHI_solver > 3,500, 1Click loses the spread.** Two market makers take most fills (HHI_solver > 3,500) and spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM (headroom -2 bps). Keeping flow costs the same 2 bps of take (15.2 bps -> 13.2 bps) while compression runs at 0.15/month. Deterministic (median-input) FDV -36.3% to $1.29B; implied price $0.95. Live: HHI over solver fill participations 5,349 (1.9 effective solvers across 85 fill participations), bootstrap 90% CI [4,831, 5,913]; deposit-source HHI over external predecessors 2,687 (not a solver measure); cross-VM headroom +2.1 bps; trigger at HHI_solver > 3,500 or headroom < 0.

### 11.3 Falsification summary
fee_race_to_zero: public gross take at 0.01 bps and confidential at 5 bps puts the deterministic FDV at $320.1M (-84.3%); watch DefiLlama near-intents 30d net take weekly, trigger < 3.0 bps, now 4.8 bps (not breached). governance_stalemate: no SVRN cut (cap 2.50% for 36 months) leaves the deterministic FDV at $2.03B (+0.0%) but dilutes per-token value to $1.46 (-1.8%) with crossover none within horizon; watch max_inflation_rate in EXPERIMENTAL_protocol_config, trigger > 1.60%, now 2.50% (BREACHED). post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at $796.9M (-60.8%); watch nearstats 30d volume against its 30d record weekly, trigger <= -40%, now -22.8% (not breached). solver_cartelization: HHI_solver > 3,500 with cross-VM headroom at -2 bps puts the deterministic FDV at $1.29B (-36.3%); watch the execute_intents solver HHI (now 5,349) and the live quote-race headroom (now +2.1 bps) weekly (BREACHED). All four at once: deterministic FDV $176.0M (-91.3% vs base $2.03B); 2 of 4 measured triggers currently breached, and the thesis is falsified if any trigger holds for 30 consecutive days.

## 12. Further evidence: take-rate history, size limits, fee share, wider peers

### 12.1 Fee-pool share against competing cross-chain routers

**NEAR Intents takes 20.0% of the six-protocol cross-chain fee pool over the 30 days to 2026-11-10, rank 2 of 6 behind Relay at 56.8%; its rolling 30-day share moved from 35.0% to 20.0% over 171 days (low 2.5% on 2026-09-13, high 45.3% on 2026-07-04) and the linear trend (-6.70 pp per 30 days, 90% interval -9.59 to -3.81) is falling, with the interval excluding zero.**

Cuts against the bull case: NEAR Intents is losing share of the fees these routers collect, so fee growth has to come from the pool growing, not from share capture. It is overturned by a positive share trend whose 90% interval excludes zero. Relay collects 2.8x NEAR Intents' fees under its own adapter's definition. NEAR Intents' own 30-day fees went from $2.90M to $5.96M over the window; the pool went from $8.30M to $29.81M. With Relay excluded the share is 46.3% against 48.8% at the start of the window (-0.83 pp per 30 days, 90% interval -1.56 to -0.11).

| Rank | Protocol | 30d fees | Share | 90d fees | Days of data | Fee definition (adapter text) |
| ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| 1 | Relay | $16.92M | 56.8% | $262.79M | 202 | Platform fees, integrator app fees and swap costs paid by users on Relay bridges and swaps, excluding execution costs (network gas). |
| 2 | **NEAR Intents** | $5.96M | 20.0% | $18.76M | 550 | Gross fees charged on NEAR Intents swaps - the protocol fee plus the affiliate (distribution) fee each frontend collects, summed across all integra... |
| 3 | THORChain DEX | $3.53M | 11.8% | $8.07M | 2040 | Slip-based liquidity (swap) fees paid by users on each chain's THORChain pools, gross outbound fees and slashing fees paid into the Reserve, and af... |
| 4 | Chainflip | $2.84M | 9.5% | $6.10M | 1043 | Chainflip AMM: Includes Swap, Broker, Ingress, Egress and Network Fees for Buy/Burn Mechanism |
| 5 | deBridge | $455.7K | 1.5% | $1.58M | 1320 | All fees paid by users for swap and bridge tokens via deBridge. |
| 6 | Across | $102.2K | 0.3% | $291.0K | 1288 | Total fees paid by users for bridge txs. |


| NEAR Intents rolling 30d share | Now | 30 days ago | 90 days ago | Window start |
| :--- | ---: | ---: | ---: | ---: |
| All included protocols | 20.0% (2026-11-10) | 9.5% (2026-10-11) | 16.0% (2026-08-12) | 35.0% (2026-05-23) |
| Relay excluded | 46.3% (2026-11-10) | 59.2% (2026-10-11) | 55.9% (2026-08-12) | 48.8% (2026-05-23) |


Trend of the rolling share: -6.70 pp per 30 days, 90% interval -9.59 to -3.81 (172 points, Newey-West 60 lags, R^2 0.62). Relay excluded: -0.83 pp per 30 days, 90% interval -1.56 to -0.11. Daily share, no overlap: -4.80 pp per 30 days, 90% interval -7.27 to -2.33. Excluding THORChain DEX (zero-fee run in the window): share 22.7% now against 41.6% at window start, trend -6.99 pp per 30 days, 90% interval -10.05 to -3.93.

Window: 2026-04-24 to 2026-11-10 (201 days common to all 6 protocols, set by Relay's first day). Trailing days left out as not final: 2026-11-11, 2026-11-12. Source: DefiLlama `summary/fees/<slug>?dataType=dailyFees`; records `defillama/fee_pool:<slug>:dailyFees` in the manifest.

Limits:

- Fee share is not volume share: a router charging more per dollar routed has a larger fee share at the same volume. DefiLlama's bridge-volume API is paid, so no volume-side comparison is made here.
- Adapter fee definitions differ, so the pool sums unlike quantities; each adapter's own text is quoted next to its protocol (`protocols[].methodology_fees`). The ex-Relay share is published because Relay's adapter counts integrator app fees and swap costs.
- The common window is 201 days (2026-04-24 to 2026-11-10), set by Relay's first day; the trend describes these months only.
- Routers outside DefiLlama's fee coverage (LI.FI and other aggregators) are absent, so the pool is these six protocols, not the cross-chain market.
- Rolling 30-day points overlap by 29 days; the interval uses a Newey-West error with 60 lags, and the daily non-overlapping share trend is reported as a cross-check.
- THORChain is measured by DefiLlama's `thorchain-dex` adapter (swap, outbound and affiliate fees); the `thorchain` slug is the chain's native transaction fee and is not a routing fee.
- The share path is not a line: it ranged from 2.5% (2026-09-13) to 45.3% (2026-07-04) and the linear trend explains 62% of its variance. Read the slope as the average drift over the window, not as a forecast.
- Relay's 30-day fees peaked at $205.95M on 2026-09-22, 13.4x its window median of $15.34M. NEAR Intents' share around that date moves with that surge in the denominator, not with a change in its own fees. Whether the surge is user-paid routing fees or an adapter artefact cannot be settled from this endpoint.
- THORChain DEX reports zero fees on 38 days of the window (longest run 37 days, 2026-05-16 to 2026-06-21). The zeros are kept as reported; if they are an adapter gap, the other protocols' shares are overstated for rolling windows that include those days. See the robustness share excluding it.

### 12.2 Size limits: the largest clip each router quotes

**1Click stops quoting at a smaller size than a competitor on 2 of 3 corridors: ETH USDC -> SOL USDC, $500K against LI.FI $2.5M; Base USDC -> Arbitrum USDC, $500K against Relay $2.5M.**

Dry quotes at $1K, $10K, $50K, $250K, $500K, $1M, $2.5M, $5M on each benchmarked corridor, run 2026-11-12T08:05:34.865Z: 54 quoted, 20 refused, 6 errors, 0 not attempted, 8 on routes the venue does not serve (88 cells, 39.837 s against a 75.0 s budget).

| Corridor | Venue | Largest size quoted | Cost at $250K | Cost at largest size | First size refused |
| :--- | :--- | ---: | ---: | ---: | ---: |
| ETH USDC -> SOL USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| ETH USDC -> SOL USDC | Relay | $1M | 3.00 bps | 3.00 bps | $2.5M |
| ETH USDC -> SOL USDC | LI.FI | $2.5M | 25.00 bps | 25.00 bps | none on the ladder |
| ETH USDC -> SOL USDC | Across | does not route | n/a | n/a | n/a |
| ETH USDC -> native BTC | 1Click | $1M | 33.56 bps | 35.43 bps | $2.5M |
| ETH USDC -> native BTC | Relay | $50K | n/a | 12.96 bps | $250K |
| ETH USDC -> native BTC | LI.FI | $500K | 43.92 bps | 44.41 bps via NEAR Intents | none on the ladder |
| Base USDC -> Arbitrum USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| Base USDC -> Arbitrum USDC | Relay | $2.5M | 1.00 bps | 1.00 bps | $5M |
| Base USDC -> Arbitrum USDC | LI.FI | $1M | 25.00 bps | 25.00 bps | none on the ladder |
| Base USDC -> Arbitrum USDC | Across | $250K | 1.00 bps | 1.00 bps | $500K |


Cost: (amount in - amount out) / amount in x 1e4: on raw units where both legs are the same stablecoin, else on USD legs valued at one common price per cell (1Click token-list oracle, else the median of the venues' implied prices), as in execution_bench.

On this run 1Click quoted at least $1M on 1 of 3 corridors and stopped below a competitor on 2. That cuts against the case that the solver network already carries institutional clips on those routes: fee growth there has to come from retail-size flow until solver inventory deepens. On ETH USDC -> native BTC the largest competitor quote (LI.FI $500K) is 1Click execution resold; the largest quote on an independent route was $50K (Relay). Repeated runs in which 1Click quotes the same rungs its competitors do would overturn this reading.

Limits:
- A dry 'no liquidity' reflects the solvers' quoting policy at that moment. It is not proven hard depth, and a dry quote is not a fill.
- One run is one observation. Solver inventory and venue limits move within minutes; re-run before relying on a rung.
- Every figure is the largest size quoted on an eight-rung ladder ($1K to $5M), not depth. Sizes between two rungs were not observed.
- Cells marked not attempted did not complete inside the time budget. They carry no information about liquidity.

Raw responses: ledger records `ladder:<venue>:<corridor_id>:<size_usd>`; data in `snapshot.liquidity_ladder`.

### 12.3 Wider peer set: FDV to revenue across the top revenue chains

**The 60x terminal multiple cap sits at the 13th percentile of 15 peers (2 of 15 trade at or below it) on FDV to annualised 30-day revenue; the wide median is 539x (bootstrap 90% interval 249x to 1,032x), and NEAR on L1 gas revenue alone trades at 4,025x, the 87th percentile.**

The cap is at or below the upper quartile of the set (1,773x), so the model's terminal value does not rest on a multiple richer than what the market pays for chain revenue today. On L1 gas revenue alone NEAR (4,025x) is priced above the wide median (539x), so NEAR is not cheap on chain revenue; the long-term case has to be carried by Intents revenue, not by the L1 multiple. This reading is overturned if a re-run puts the cap above the 75th percentile of the set (peer multiples compressing toward 60x) or if the set shrinks below 8 peers.

| Chain | Token | Revenue, 30d | Revenue, annualised | FDV | FDV / revenue | Note |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| Quai | QUAI | $218,839 | $2.7M | $7.8M | 2.9x | revenue is merged-mining block rewards earned on other chains and spent on QUAI buyback and burn (the adapter's own Fees text), not gas paid on Quai |
| **Model floor** |  |  |  |  | **8x** | terminal_multiple_floor (assumption) |
| Polygon | POL | $1.7M | $20.2M | $916.8M | 45.5x |  |
| **Model cap** |  |  |  |  | **60x** | terminal_multiple_cap (assumption); the multiple the model uses |
| Tron | TRX | $24.7M | $300.8M | $30.11B | 100x |  |
| **NEAR (L1 + Intents, the model's basis)** | NEAR | $1.9M | $23.1M | $4.60B | **199x** | comps.near_combined; not like for like (no peer row includes app revenue) |
| Arbitrum | ARB | $532,532 | $6.5M | $1.49B | 230x | L2 governance token: sequencer revenue accrues to the DAO treasury, not to ARB by protocol rule |
| Starknet | STRK | $123,502 | $1.5M | $373.8M | 249x | L2 token: sequencer revenue accrues to the operator and foundation, not to STRK by protocol rule |
| Injective | INJ | $152,740 | $1.9M | $743.8M | 400x |  |
| Aptos | APT | $124,589 | $1.5M | $673.2M | 444x |  |
| Monad | MON | $251,032 | $3.1M | $1.65B | 539x |  |
| ICP | ICP | $175,735 | $2.1M | $1.43B | 667x |  |
| Avalanche | AVAX | $338,567 | $4.1M | $4.06B | 986x |  |
| Filecoin | FIL | $116,405 | $1.4M | $1.46B | 1,032x |  |
| Solana | SOL | $1.7M | $21.0M | $52.88B | 2,514x |  |
| Ethereum | ETH | $6.2M | $75.8M | $250.54B | 3,303x |  |
| **NEAR (L1 gas revenue only)** | NEAR | $93,923 | $1.1M | $4.60B | **4,025x** | subject, not counted in the set |
| BSC | BNB | $1.2M | $14.4M | $88.60B | 6,173x | exchange-linked token: BNB's FDV also prices Binance exchange utility, not only BNB Chain's fee burn |
| Hyperliquid L1 | HYPE | $838,006 | $10.2M | $67.95B | 6,664x | chain row covers HyperEVM gas only; HYPE's FDV is priced mostly on the HyperCore exchange, whose revenue DefiLlama books under separate Hyperliquid protocols (the model's three-peer set uses that parent) |

Distribution of FDV / revenue across 15 peers: median 539x (bootstrap 90% interval 249x to 1,032x; 10,000 resamples, seed 20261114), P25 239x, P75 1,773x, IQR 1,533x, range 2.9x to 6,664x. The 60x cap: 2 of 15 peers at or below it (13th percentile). The 8x floor: 1 of 15 (7th percentile). NEAR on L1 gas revenue only: 4,025x, the 87th percentile; on the model's combined L1 + Intents basis 199x, which would be the 20th percentile (not like for like).

Without the 5 flagged rows (10 peers): median 603x, P25 411x, P75 1,020x; 1 at or below the cap. For contrast, the three-peer median the model uses (Solana, Ethereum, Hyperliquid) is 2,514x (comps.median_fdv_to_revenue_ex_near), which the model clips to the 60x cap.

Inclusion rules (fixed before any multiple was computed):
- Universe: every DefiLlama fees-overview row with category 'Chain' and 30-day revenue (dataType=dailyRevenue) above zero.
- Ranking: by 30-day revenue, highest first. No chain is added or removed by hand after seeing its multiple.
- Peers: the first 15 chains in that ranking that have their own token with a CoinGecko fully diluted valuation.
- Excluded, each listed with its reason: chains with no native token; chains whose token has no FDV on CoinGecko; chains not in the chain-to-token mapping table (configuration in wide_peers.py); a second row for a token already counted.
- Flagged, not dropped: L2 tokens, exchange-linked tokens, rows whose adapter books something other than chain gas revenue and rows whose DefiLlama adapter is not typed 'chain'. They stay in the distribution; a sensitivity without them is reported next to it.
- NEAR is the subject. It is positioned against the set on the same basis (its own chain row and CoinGecko FDV) and is not counted in it.
- Multiple: FDV / (30-day revenue x 365 / 30). Percentile of a value: share of peers with a multiple at or below it.

Excluded inside the cut (2); 51 further chains rank below the last peer and were not evaluated:
- Base (rank 3 by revenue, $2.6M in 30 days): no native token: Coinbase-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.
- Robinhood Chain (rank 7 by revenue, $1.1M in 30 days): no native token: Robinhood-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.

Caveats:
- FDV to revenue on 30 days annualised is noisy: one busy or quiet month moves a chain's multiple by a large factor.
- Revenue definitions differ by chain adapter (burned base fees, sequencer profit, treasury share, buyback and burn); the adapter's own text is carried per row.
- Token FDV for an L2 or an exchange-linked token does not accrue chain revenue the way an L1 gas token does; those rows are flagged and a sensitivity without them is shown.
- Selection: ranking by revenue picks the chains with the most revenue, which pulls their multiples down relative to the long tail of low-revenue chains.
- NEAR's multiple here uses L1 gas revenue only. The model values NEAR on L1 plus Intents revenue (comps.near_combined), which no peer row here has an equivalent of.
- One snapshot. Nothing here is a time series, and the cap's position will move with token prices and monthly fee volume.

Sources: `defillama/overview:fees:dailyRevenue` sha256 `f22a47710a6f726e`, `coingecko/coins_markets_wide` sha256 `c023be889d7b39ae`; fetched 2026-11-12T08:05:30.847Z. Field: `snapshot.wide_peers`.

### 12.4 Take-rate history

Gross take compressed over the trailing year: the rolling 30-day rate is 15.9 bps on 2026-11-10 against 16.6 bps a year earlier, while average daily volume went from $81M to $125M; the trailing-365d log-linear trend is -30% per year (90% CI -42% to -16%), which excludes zero, and the trailing-180d trend, +20% per year (90% CI -15% to +69%), does not show the decline continuing.

| Window | Days (UTC) | Gross take (bps) | Net take (bps) | Holder take (bps) | Avg daily volume |
| :--- | :--- | ---: | ---: | ---: | ---: |
| last 30d | 2026-10-12 to 2026-11-10 | 15.86 | 4.84 | 4.84 | $125M |
| 30-60d ago | 2026-09-12 to 2026-10-11 | 16.85 | 4.69 | 4.69 | $158M |
| 60-90d ago | 2026-08-13 to 2026-09-11 | 13.34 | 2.88 | 2.88 | $120M |
| 150-180d ago | 2026-05-15 to 2026-06-13 | 12.47 | 3.48 | 3.48 | $82M |
| 330-360d ago | 2025-11-16 to 2025-12-15 | 24.39 | 1.36 | 0.00 | $91M |


- **Trend, trailing 365 days** (2025-11-11 to 2026-11-10, 365 rolling points): -30.3% per year, 90% CI -42.2% to -16.0% (excludes zero; Newey-West, 60-day lag).
- **Trend, trailing 180 days** (2026-05-15 to 2026-11-10, 180 rolling points): +19.8% per year, 90% CI -15.0% to +68.8% (includes zero; Newey-West, 60-day lag).
- **Trend, full history** (2025-06-08 to 2026-11-10, 521 rolling points): +87.0% per year, 90% CI -2.1% to +257.3% (includes zero; Newey-West, 60-day lag). Dominated by the 2025 fee ramp from zero; not a competition signal.
- **Robustness of the trailing-365d trend** (reported, not graded): 30-day lag -41.9% to -16.5%; 120-day lag -40.9% to -17.8%; 13 non-overlapping 30-day windows -26.6% per year, Student-t 90% CI -42.6% to -6.0%.
- **Elasticity to volume, trailing 365 days** (365 days, 0 dropped for zero fees or volume): a 1% rise in daily volume goes with a -0.04% change in daily gross take, 90% CI -0.13 to +0.04 (includes zero; R2 0.00).
- **Elasticity to volume, full history** (541 days, 9 dropped for zero fees or volume): a 1% rise in daily volume goes with a +0.70% change in daily gross take, 90% CI +0.20 to +1.20 (excludes zero; R2 0.36).
- **Regime break** (first aligned day with dailyHoldersRevenue > 0): 2026-02-23. Pooled gross take 17.49 bps over the 289 days before (18.93 bps over the 104 of those inside the trailing year) and 15.46 bps over the 261 days since; net take 1.49 bps before (trailing year) and 3.36 bps since.
- **Range, trailing 365 rolling points**: gross take high 24.49 bps (2025-12-16), low 11.82 bps (2026-06-22).
- **Floor read** (trailing 365 rolling points): gross take was below the 0.5 bps model floor on 0 of them (minimum 11.82 bps, 2026-06-22); net take was below the 3 bps fee-race trigger on 282 (minimum 0.00 bps, 2025-12-31), and on 149 of the 232 windows that start after the regime break.

**Read.** This cuts against the bull case: gross take fell at 30% per year over the trailing year with an interval that excludes zero (non-overlapping check: -27% per year, 90% CI -43% to -6%, also excludes zero), so the claim that pricing power has held while volume grew is not supported by the fee history; the level is still 32x the 0.5 bps model floor. The trailing-180d trend is +20% per year (90% CI -15% to +69%): the decline is not visible in the last six months. A trailing-365d interval that includes zero again would overturn this read; a 180d interval wholly below zero would show compression still in progress. NEAR's captured (net) take went from 1.7 bps to 4.8 bps over the same span and sat under the 3 bps fee-race trigger on 282 of 365 trailing rolling points.

Data: 550 aligned settled days 2025-05-10 to 2026-11-10 (raw); unsettled trailing day(s) excluded: 2026-11-11. Source: defillama/fees:near-intents:dailyFees sha256 66689499af27...; defillama/fees:near-intents:dailyRevenue sha256 8293ba464a81...; defillama/fees:near-intents:dailyHoldersRevenue sha256 cc3a4d7ed699...; defillama/dexs:near-intents sha256 2fc4816f19c4....

Limits:
- Early history mixes fee regimes: the DefiLlama fee chart ramps from zero in mid-2025 and net revenue is zero until the first sweep, so the full-history trend measures fees being switched on. Read the trailing-365d figures.
- Fees, revenue and holders revenue follow DefiLlama's near-intents adapter definitions: gross fees include the affiliate fee each frontend keeps; revenue is NEAR swept into the revenue wallets and is booked on the sweep day, so net take is lumpy and can exceed fees on single days. An adapter revision restates the whole series.
- Rolling 30-day points overlap (29 of 30 days shared), so about 12 independent observations sit in a year. A Newey-West interval on such points is too narrow at this sample size: in the seeded null simulation in quant/tests/test_take_rate_series.py a trendless series is flagged well above the nominal 10% of the time. The non-overlapping 30-day check (Student-t) stays near its nominal size and is the stricter read: treat a trend as established only when both intervals exclude zero. An interval that includes zero means no decline was detected, not that none exists.
- The elasticity regresses fees/volume on volume: noise in daily volume enters both sides and pushes the estimate negative.

### 12.5 Volume engine: GBM against a block bootstrap, out of sample

The block bootstrap does not repair the volume engine: P10-P90 coverage (1m 20/20 (100%, p 0.02), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33)) is rejected against 80% for over-coverage at 1m and 3m; the pass at 6m rests on 14 overlapping forecasts, which is weak evidence; its band is 3.3x to 7.3x the GBM's log width, so it covers by being wide, not by being sharp; the GBM is rejected at 3 of 3 horizons (1m 12/20 (60%, p 0.04), 3m 9/17 (53%, p 0.01), 6m 7/14 (50%, p 0.01)), so the two engines bracket realized dispersion and neither is calibrated.

| Engine | Horizon | n | Inside | Coverage | Binomial p vs 80% | Below P10 / above P90 | Realized / median | Band width, ln(P90/P10) | Verdict |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| GBM, registry drift (valuation engine) | 1m | 20 | 12/20 | 60% | 0.04 | 0 / 8 | 1.37x | 0.84 | 80% rejected |
| GBM, registry drift (valuation engine) | 3m | 17 | 9/17 | 53% | 0.01 | 0 / 8 | 1.86x | 1.18 | 80% rejected |
| GBM, registry drift (valuation engine) | 6m | 14 | 7/14 | 50% | 0.01 | 0 / 7 | 3.89x | 1.40 | 80% rejected |
| Block bootstrap, resampled drift | 1m | 20 | 20/20 | 100% | 0.02 | 0 / 0 | 0.72x | 2.76 | 80% rejected |
| Block bootstrap, resampled drift | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.40x | 6.38 | 80% rejected |
| Block bootstrap, resampled drift | 6m | 14 | 13/14 | 93% | 0.33 | 1 / 0 | 0.09x | 10.20 | 80% not rejected |
| Block bootstrap, registry drift (shape only) | 1m | 20 | 13/20 | 65% | 0.10 | 0 / 7 | 2.30x | 2.64 | 80% rejected |
| Block bootstrap, registry drift (shape only) | 3m | 17 | 6/17 | 35% | <0.001 | 0 / 11 | 40.14x | 6.33 | 80% rejected |
| Block bootstrap, registry drift (shape only) | 6m | 14 | 0/14 | 0% | <0.001 | 0 / 14 | 3783.83x | 10.16 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 1m | 20 | 20/20 | 100% | 0.02 | 0 / 0 | 0.68x | 3.06 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.36x | 7.79 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 6m | 14 | 14/14 | 100% | 0.09 | 0 / 0 | 0.07x | 12.84 | 80% rejected |


Target coverage 80%; verdict rule: exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10. Bootstrap: 10,000 paths per origin, seed 20261114, mean block length 7 to 58 days across origins (median 11). At 1 month the bootstrap band is 3.28x the GBM band in log width. At 3 months the bootstrap band is 5.42x the GBM band in log width. At 6 months the bootstrap band is 7.26x the GBM band in log width.

Power at one month (n = 20): the test accepts 14 to 19 forecasts inside the band. A model whose true coverage is 60% would be rejected 75% of the time and one at 70% only 39% of the time, so a pass does not separate a calibrated engine from a mildly miscalibrated one.

Valuation effect, volume. The valuation uses the GBM; this is unchanged. From the latest origin (2026-11-11, trailing 30-day volume $3.73B), 30-day volume 12 months ahead as a multiple of current, P10 / P50 / P90: GBM 0.19x / 0.85x / 3.78x; bootstrap with the same expected path 0.05x / 0.43x / 3.35x; bootstrap with its own resampled drift 0.08x / 0.69x / 5.36x.

Valuation effect, FDV. Feeding bootstrap volume paths (same expected path, same price, take-rate and issuance paths, 10,000 paths) through the Monte Carlo gives FDV P10 / P50 / P90 of $29M / $202M / $2.38B against the base $131M / $669M / $4.04B (0.22x / 0.30x / 0.59x of base). The base run reproduces `sotp.fdv_percentiles` exactly. The bootstrap run holds the mean volume path fixed, so its lower median is the convexity cost of a wider distribution. These are variant figures; no headline number uses them.

The valuation uses the GBM. At the same expected path the bootstrap puts 30-day volume 12 months out at 0.05x / 0.43x / 3.35x of current (P10 / P50 / P90) against the GBM's 0.19x / 0.85x / 3.78x, a band 1.4x as wide in log terms; through the same Monte Carlo FDV P10 / P50 / P90 becomes 0.22x / 0.30x / 0.59x of the base. The backtest rejects the bootstrap for over-coverage, so read this as a stress bound on volume dispersion (with the mean path held fixed, a wider distribution lowers the median), not as a better central estimate.

Caveats:
- Nothing in the bootstrap is tuned to reach 80% coverage. With about 20 origins, choosing block length, lookback or path count by coverage would be overfitting; the block rule and path count were fixed first and the n^(1/3) block rule is shown only as a sensitivity.
- Low power: the exact binomial test on about 20 one-month origins accepts a wide range of true coverage, and 3- and 6-month forecasts overlap, so a pass is weak evidence of calibration, not proof.
- A bootstrap can only replay changes that occurred in the lookback. It widens the band where the past year was volatile and cannot anticipate a regime the lookback did not contain.
- Daily volume carries day-to-day noise that reverses. Blocks shorter than that reversal overstate horizon variance, so part of any coverage gain can come from a wider band, not a better-shaped one; the band-width ratio is reported for that reason.
- The path starts at the origin day's volume, one noisy observation, and the registry-drift form holds the mean path fixed, so a wider distribution mechanically lowers its median. Both are stated properties of the design, not fitted choices.
- No second design was tried after these results. Resampling changes of the 30-day sum instead of daily volume would remove the day-to-day noise, but choosing between engine designs on about 20 origins is the tuning this test rules out; it is left as a stated next test.
- The valuation still runs on the GBM. The bootstrap is a parallel variant; no headline figure uses it.

## 13. Evidence scorecard

| Claim | Status | Value | Source | Confidence | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB) | **VERIFIED_ON_CHAIN** | intents.near storage_usage 13,605,979,376 bytes = 136,060 NEAR locked; 282,759 NEAR across 8 tracked contracts | near_rpc/view_account:intents.near sha256 6cf906e8a341... @ block 224,186,938; storage_amount_per_byte from EXPERIMENTAL_protocol_config | high | growth 30,249,135 B/day = 302.5 NEAR/day over 31.2 d (archival); a 0.01 NEAR/KB lock is released if state is deleted, so it is a sink while state grows |
| Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap | **VERIFIED_ON_CHAIN** | 25,454.65 NEAR minted at epoch start 224,178,737 x 1,287.2 epochs/yr = 32,766,005 NEAR/yr (2.4984%), -0.07% vs nominal 32,787,466 | near_rpc/block:224178737 sha256 0ec8c9ea9191... and its predecessor by prev_hash; previous epoch start 224135537 | high | second independent jump 26,438.74 NEAR; within-epoch drift -206.35 NEAR/epoch is the net gas burn |
| Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC | **VERIFIED_LIVE_API** | median headroom +2.14 bps over 3 comparable cells (dest_units); competitor ceiling 3.00 bps | oneclick/relay/lifi/across quote records 2026-11-12T08:05:30.847Z | medium | $500: +2.41 bps vs relay (rank 1/3); $50,000: +2.14 bps vs relay (rank 1/3); $250,000: +0.98 bps vs relay (rank 1/3); no 1Click capacity failures |
| Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC | **NOT_SUPPORTED** | 1Click delivers LESS BTC per USDC than the best competitor (relay): median headroom -5.14 bps over 3 cells (dest_units); the claim is not supported by this run | oneclick/lifi/relay quote records 2026-11-12T08:05:30.847Z | medium | clip-dependent: $500: -22.48 bps vs relay (rank 3/3); $50,000: -5.14 bps vs relay (rank 2/3); $250,000: +10.09 bps vs lifi (rank 1/2); LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used |
| EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative) | **VERIFIED_LIVE_API** | median headroom -0.94 bps over 3 cells (dest_units; 1Click trails) | oneclick/across/relay/lifi quote records 2026-11-12T08:05:30.847Z | medium | $500: -0.59 bps vs across (rank 3/4); $50,000: -0.94 bps vs across (rank 3/4); $250,000: -1.02 bps vs across (rank 3/4); the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins |
| Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material | **DERIVED** | deposit/caller HHI_external 2,687 [90% CI 1,690-3,961] (N_eff 3.72), ex-AI-agent 1,600; AI-agent share 47.4% (>= 10% materiality line), bridge share 36.8% | nearblocks/txns:intents.near:p1 sha256 8ed4221a9667... ... p8 | low | 173 unique receipts over 34 s; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources (bridge callbacks, direct callers), not solvers |
| Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers | **VERIFIED_LIVE_API** | HHI_solver 5,349 [90% CI 4,831-5,913] (N_eff 1.87) over 85 fill participations in 83 fills (3 atomic token_diff fills, 80 hub-settled legs), 4 distinct solvers; CI entirely above the 3,500 cartel threshold | nearblocks/txns:intents.near:p1 sha256 8ed4221a9667... ... p8 + 8 method-filtered execute_intents page(s); args.signed[].payload.message (NEP-413 signer_id) | medium | 445 execute_intents receipts decoded; settlement hub 51e8f94d77b5... (157 counterparties) routes most swaps via transfer legs; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty |
| Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume | **DERIVED** | 13.1% (band 11.6%-14.8%) estimated on-chain: Confidential Intents Treasury 24h inflow $14.8M / outflow $16.7M against 24h volume $113.1M; >= 10% materiality line | near_rpc/confidential:balances:head sha256 6adfe28a0896... treasury balances in intents.near (NEAR mainnet RPC) | low | nearstats' split was rejected by the plausibility guard; the share is estimated from the public treasury boundary instead. Biases: same-hour shield/unshield netting and in-shard turnover push it down, solver inventory pushes it up; 24h window |
| Confidential TVL backs the dark-pool engine (Engine 2) | **VERIFIED_ON_CHAIN** | $136.7M TVL read on-chain from the Confidential Intents treasury in intents.near (NEAR-reported via nearstats: $140.8M) | near_rpc/confidential:balances:head sha256 6adfe28a0896... intents.near mt_batch_balance_of (treasury) | high | Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut (0.7); the confidential take (20 bps) is an assumption |
| Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink | **DERIVED** | alpha 30.5%; gross take 15.86 bps, net take 4.84 bps; buyback sink 17,261 NEAR/day = 20.4% coverage incl. burn and lock | defillama/fees:near-intents:dailyHoldersRevenue sha256 cc3a4d7ed699... / defillama/fees:near-intents sha256 66689499af27... | medium | DefiLlama revenue methodology: NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.near.org and the on-chain buyback). Split by destination wallet into front-end affiliate revenue and Other. Transfers between those wallets are excluded. |
| Chain Signatures (v1.signer) is a growing second usage engine beyond Intents | **VERIFIED_LIVE_API** | usage only: 26,402,136 cumulative v1.signer receipts; growth not measured this run | nearblocks/txns:v1.signer:count | low | the sampled rate/trend failed this run; the level is counted, the growth claim is not supported |
| The volume engine (GBM with measured sigma) is calibrated out of sample: P10-P90 covers ~80% of realized 30-day volume | **NOT_SUPPORTED** | 1m 12/20 = 60% inside P10-P90 (binomial p 0.04); 3m 9/17 = 53% inside P10-P90 (binomial p 0.01); 6m 7/14 = 50% inside P10-P90 (binomial p 0.01); 1m median realized / forecast median 1.37x (under-prediction); 1m coverage 30% for origins before 2026-01-15, 90% from it; 20 monthly origins 2025-03-21 to 2026-10-12 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 2fc4816f19c4... | low | Tests the volume distribution only; the take rate, holder capture, confidential share, multiple and discount rate are not backtested. 3m and 6m forecasts from monthly origins overlap, so their effective sample is smaller than n. |
| A block-bootstrap volume engine (fat tails, autocorrelation) is calibrated out of sample where GBM is not | **NOT_SUPPORTED** | block bootstrap 1m 20/20 (100%, p 0.02), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33); GBM 1m 12/20 (60%, p 0.04), 3m 9/17 (53%, p 0.01), 6m 7/14 (50%, p 0.01); bootstrap at the GBM's expected path (shape only) 1m 13/20 (65%, p 0.10), 3m 6/17 (35%, p <0.01), 6m 0/14 (0%, p <0.01); bootstrap band 3.3x the GBM's log width at 1m; 20 monthly origins 2025-03-21 to 2026-10-12 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 2fc4816f19c4...; valuo.models.volume_bootstrap (seed 20261114, 10000 paths per origin) | low | Inside P10-P90 against an 80% target, exact two-sided binomial p. Low power: at n = 20 the test accepts 14 to 19 hits and rejects a 70%-coverage engine only 39% of the time; 3m and 6m forecasts overlap. Block length (Politis-White) and path count were fixed before coverage was computed; nothing is tuned. The valuation still uses the GBM; this row grades a parallel variant and tests the volume distribution only. |
| NEAR Intents' realized gross take rate is not trending to zero as volume grows | **NOT_SUPPORTED** | rolling 30d gross take 15.86 bps on 2026-11-10 vs 16.64 bps on 2025-11-11; trend -30.3%/yr, 90% CI -42.2% to -16.0% (excludes zero; Newey-West 60d lag, 365 overlapping points); floor 0.5 bps, 0 of 365 trailing points below it; non-overlapping 30d windows (n=13) -26.6%/yr, Student-t 90% CI -42.6% to -6.0%; trailing 180d trend +19.8%/yr, CI -15.0% to +68.8% | defillama/fees:near-intents:dailyFees sha256 66689499af27...; defillama/fees:near-intents:dailyRevenue sha256 8293ba464a81...; defillama/fees:near-intents:dailyHoldersRevenue sha256 cc3a4d7ed699...; defillama/dexs:near-intents sha256 2fc4816f19c4... | low | Graded on the trailing-365d trend only: a decline is counted when the Newey-West 90% interval and the non-overlapping-window Student-t interval both sit below zero; DERIVED needs no such decline and a latest rolling take above the model floor. Gross take includes affiliate fees kept by frontends; NEAR's captured share is the net / holder take. Rolling points overlap, so an interval that includes zero is not proof of a floor. The full-history trend is not used (fee ramp from zero in 2025). |
| 1Click quotes institutional size: at least $1M on every benchmarked corridor | **NOT_SUPPORTED** | ETH USDC -> SOL USDC: 1Click $500K, best competitor LI.FI $2.5M; ETH USDC -> native BTC: 1Click $1M, best competitor LI.FI $500K (routed through NEAR Intents); Base USDC -> Arbitrum USDC: 1Click $500K, best competitor Relay $2.5M (1 of 3 corridors with an attempted 1Click rung at or above $1M) | 1Click, Relay, LI.FI, Across dry quotes; ledger records ladder:<venue>:<corridor_id>:<size_usd> (81 responses), run 2026-11-12T08:05:34.865Z | low | Largest size quoted on an eight-rung ladder of dry quotes, one run. A dry 'no liquidity' is solver quoting policy at that moment, not proven depth, and a dry quote is not a fill. |
| NEAR Intents is gaining share of cross-chain routing fees | **NOT_SUPPORTED** | 20.0% of the six-protocol fee pool (30 days to 2026-11-10), rank 2 of 6 behind Relay at 56.8%; share at window start 35.0% (201-day common window); trend -6.70 pp per 30 days, 90% interval -9.59 to -3.81; ex-Relay 46.3%, trend -0.83 pp per 30 days, 90% interval -1.56 to -0.11 (share is falling) | defillama summary/fees dailyFees: near-intents, relay, across, debridge, chainflip, thorchain-dex | low | Fee share, not volume share; adapter fee definitions differ; the pool is the protocols DefiLlama covers. A share trend is DERIVED from live fee series, never VERIFIED. |
| The model's terminal multiple cap sits inside the observed peer range of FDV/revenue | **DERIVED** | cap 60x vs 15 chain tokens: 2 of 15 trade at or below it (13th percentile); P25 239x, median 539x [bootstrap 90% 249x to 1,032x], P75 1,773x, range 2.9x to 6,664x; NEAR L1-only 4,025x (87th percentile); without flagged rows: median 603x, n 10 | defillama/overview:fees:dailyRevenue sha256 f22a47710a6f... + coingecko/coins_markets_wide sha256 c023be889d7b... | medium | Rule: DERIVED when the cap is at or below the 75th percentile of the wide set and n_peers >= 8. Here the cap is inside the observed range and at or below its upper quartile. FDV/revenue on 30 days annualised, one snapshot; revenue definitions differ by chain adapter; peers ranked by revenue and fixed before any multiple was computed (inclusion_rules, excluded). |


## 14. Assumptions register

### 14.1 Labeled assumptions (slider inputs; never presented as measured)
| Key | Default | Unit | Range | Justification |
| :--- | :--- | :--- | :--- | :--- |
| svrn_target_inflation | 0.016 | ratio_annual | [0.005, 0.03] | SVRN governance proposal to cut the protocol max_inflation_rate from 2.5% to 1.6%; not enacted on-chain (live EXPERIMENTAL_protocol_config.max_inflation_rate is still [1, 40]). |
| svrn_glidepath_months | 24 | months | [6, 48] | QUANT_PIPELINE_SPEC and TERMINAL_UI_SPEC model the 2.5% -> 1.6% cut as a linear 24-month (730-day) glidepath; the proposal itself does not fix the phasing. |
| public_volume_growth_yoy | 0.675075 | ratio_yoy | [0.0856145, 1.5846] | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-12 to 2026-11-11 (365 days, DefiLlama dexs/near-intents): +67.5%/yr, 90% CI +8.6% to +158.5% (Newey-West, 30-day lags). Range = that CI. Median trend growth used as EXPECTED growth (conservative). Replaces the registry default +30%. Cross-checks (not used): yoy_trailing_30d +53%; mean_monthly_log_return_12m +30%. |
| confidential_share_target | 0.4 | ratio | [0.05, 0.6] | nearstats intents.totalsBreakdown shows confidential ~39% of 30d volume (derived as NEAR total minus public); 40% holds the mix flat rather than extrapolating growth. |
| confidential_take_bps | 20 | bps | [10, 30] | QUANT_PIPELINE_SPEC's institutional MEV-protected shard fee band is 15-25 bps; 20 is the midpoint and no live confidential fee series exists to verify it. |
| fee_compression_lambda_monthly | 0.03 | per_month | [0, 0.15] | Monthly mean-reversion speed of the public take toward the competitive floor; 3%/month is a ~23-month half-life, in line with bridge-fee compression observed across Across/Relay since 2023. |
| confidential_compression_divisor | 3 | x | [1, 10] | MODEL_DESIGN section 4.2 sets lambda_conf = lambda / 3: confidential execution competes on privacy rather than price, so fees compress slower than public routing. |
| discount_rate | 0.25 | ratio_annual | [0.1, 0.4] | 25% is a venture-stage crypto hurdle rate; Dragonfly / Electric Capital style memos use 20-30% for pre-maturity protocol cash flows. |
| terminal_multiple_floor | 8 | x_fdv_to_revenue | [2, 20] | Guardrail on the live peer-median FDV/revenue multiple: 8x is roughly a mature L1 fee multiple floor; clipping is logged in SotpValuation.calibration. |
| terminal_multiple_cap | 60 | x_fdv_to_revenue | [20, 150] | Guardrail so a single high-multiple peer (ETH/SOL trade above 100x revenue on DefiLlama) cannot drive the terminal value; 60x caps the peer median. |
| terminal_multiple_fallback | 30 | x_fdv_to_revenue | [8, 60] | Used ONLY when the live peer FDV/revenue median AND the FDV/fees median are both null (CoinGecko outage / 429): 30x is the midpoint of listed-exchange and L1 REV multiples (roughly 8x mature L1 fee multiples to 60x the guardrail cap); the run records a warning, calibration.terminal_multiple_source = 'assumption' and Engine 1 is flagged assumption-heavy. Never used when a live multiple exists. |
| price_sigma_annual_fallback | 1 | ratio_annual | [0.6, 1.6] | Used ONLY when both price series (nearstats price-history 1y and the coins.llama.fi daily chart) are unavailable: 100% annualized volatility is the centre of the 60-160% band large-cap alt-L1 tokens have realized over 1y windows; the run records a warning and sotp.inputs.sigma_price_annual is labeled source 'assumption'. |
| volume_sigma_monthly_fallback | 0.35 | ratio_monthly | [0.15, 0.6] | Used ONLY when the DefiLlama near-intents dexs chart is unavailable and neither volume_monthly_sigma nor volume_daily_sigma could be measured (the 30-day volume itself then comes from nearstats): 0.35 is the class of the measured monthly log-return sigma of 30-day volume aggregates (0.27-0.36 across windows in the committed snapshots); the run records a warning and sotp.inputs.sigma_volume_monthly is labeled source 'assumption'. A chart outage never exits the run. |
| confidential_multiple_haircut | 0.7 | ratio | [0.3, 1] | nearstats flags intents.protocolMetrics.confidentialTvlUsd as sourceStatus 'unverified'; a 30% haircut on Engine 2's terminal multiple prices that verification risk. |
| kb_per_agent_vault | 20 | KB | [5, 50] | A NEAR account with a few access keys and small contract state costs 5-50 KB; at storage_amount_per_byte = 1e19 yocto 20 KB locks 0.2 NEAR per agent vault. |
| state_lock_growth_fallback_near_per_day | 0 | NEAR_per_day | [0, 10000] | Used ONLY if the archival measurement of storage growth fails; default 0 gives no credit to the sink and the run records a warning rather than inventing a number. |
| buyback_capture_ratio_override | -1 | ratio | [-1, 1] | -1 means use the live DefiLlama near-intents dailyHoldersRevenue / fees capture ratio (~35%, reconciles with revenue.near.org); any value in [0, 1] overrides it for slider scenarios. |
| near_price_drift_annual | 0 | ratio_annual | [-0.5, 1] | Zero drift: the model does not forecast NEAR price to value the token; price enters only to convert USD buybacks into NEAR units (MODEL_DESIGN section 4.2). |
| public_take_floor_bps | 0.5 | bps | [0, 5] | MODEL_DESIGN 4.2 hard floor for the public take: tau_floor = max(this, min(live public take, live cross-VM headroom)). It is the floor on its own only when the execution benchmark did not run, and the run then records a warning. |
| confidential_volume_sigma_multiplier | 1 | x | [1, 3] | Multiplier on the confidential-volume GBM sigma applied while nearstats flags confidentialTvlUsd as unverified (MODEL_DESIGN 4.2). Default 1.0 = no widening, because no measured dispersion factor exists; Engine 2 stays assumption_heavy regardless. |
| bear_fee_race_tau_pub_bps | 0.01 | bps | [0, 1] | 1 pip is the bare intents.near contract fee once third-party frontends route around near.com and its 25 bps / 10-20 bps partner fees (QUANT_PIPELINE_SPEC Model C.1, MODEL_DESIGN 4.3.1). |
| bear_fee_race_tau_conf_bps | 5 | bps | [0, 10] | Confidential execution repriced to 5 bps, a quarter of the 20 bps default, once public routing is free (MODEL_DESIGN 4.3.1). |
| bear_fee_race_trigger_net_take_bps | 3 | bps | [1, 5] | Early warning: DefiLlama near-intents 30d net take below 3 bps (live ~5.6 bps class) means compression is already past the mid-point to zero (MODEL_DESIGN 4.3.1). |
| bear_decay_v_pub_multiplier | 0.4 | ratio | [0.1, 1] | Public volume -60%: QUANT_PIPELINE_SPEC Model C.3 sizes the NEAR@3.33 mercenary-liquidity unwind at -60% of 30d volume. |
| bear_decay_v_conf_multiplier | 0.3 | ratio | [0.1, 1] | Confidential volume -70%: the shard's TVL is flagged unverified by nearstats, so its volume is assumed more incentive-dependent than public flow (MODEL_DESIGN 4.3.3). |
| bear_decay_tvl_multiplier | 0.3 | ratio | [0.1, 1] | Confidential TVL -70% (QUANT_PIPELINE_SPEC Model C.3). |
| bear_decay_trigger_volume_drawdown | -0.4 | ratio | [-0.8, -0.1] | Early warning: 30d volume more than 40% below the 30d record (nearstats records.max30dUsd) (MODEL_DESIGN 4.3.3). |
| bear_cartel_hhi_external | 3500 | hhi | [2500, 10000] | HHI 3,500 is two actors at ~40% each plus a tail; the US horizontal-merger guideline calls > 2,500 highly concentrated (QUANT_PIPELINE_SPEC Model C.4). |
| bear_cartel_headroom_bps | -2 | bps | [-10, 0] | Cartel spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM; 1Click must give the same 2 bps of take back to keep flow (MODEL_DESIGN 4.3.4). |
| bear_tau_floor_bps | 0.5 | bps | [0, 2] | Floor on the cartel scenario's public take give-back: max(0.5 bps, live public take - 2 bps) (MODEL_DESIGN 4.2 competitive floor). |
| bear_cartel_lambda_monthly | 0.15 | per_month | [0, 0.15] | Compression speed set to the registry's high bound for fee_compression_lambda_monthly (0.15/month): losing the spread means order flow leaves at the fastest plausible rate. |
| sensitivity_measured_lookback_windows | 6 | windows | [3, 12] | Tornado range for measured Intents ratios (gross take, holder capture): min..max over this many trailing non-overlapping 30-day windows of the DefiLlama daily series. Six windows covers the period since the 2026-02-23 buyback start; earlier windows mix a different revenue regime. |
| sensitivity_unmeasured_band | 0.25 | ratio | [0.1, 0.5] | Tornado range (+/- this fraction of the measured value) for live inputs that have no measured dispersion in the snapshot (L1 gas burn, state-lock growth, cross-VM headroom). A labeled width, not a confidence interval. |
| confidential_share | 0.4 | ratio | [0.15, 0.6] | FALLBACK ONLY, used when the live nearstats public/confidential split is implausible (intents_forensics.volume.confidential_share_status = implausible_fallback). The last plausible split, nearstats totalsBreakdown as of 2026-10-31, read $1.58B confidential of $3.86B 30d (40.9%); from the 2026-11-07 split onward the explorer public tile equals the NEAR total and confidential all-time volume reads $0 while confidential TVL is ~$143M, i.e. a source change, not a measurement. Range: the bear preset target (15%) to confidential_share_target's high bound (60%). |
| confidential_share_plausibility_floor | 0.01 | ratio | [0.001, 0.05] | A reported confidential 30d share below 1% is treated as a broken split (not a measurement) when nearstats' own payload contradicts it: confidential TVL > 0 with ~zero all-time confidential volume, the confidential stream reporting ok, or a split check whose detail says the split is withheld. With ~$140M of confidential TVL a <1% share would mean the shard turns over less than ~0.3x its TVL per month. |
| solver_sample_min_span_s | 3600 | seconds | [900, 86400] | Minimum wall-clock span of the solver sample before the cartelization trigger may grade HHI_solver breached or clear. The method-filtered execute_intents pages and settlement-hub legs typically cover a window of minutes; fills inside a 2-minute window are serially correlated (the same solvers quote consecutive blocks), and the bootstrap CI resamples only within that window, so it measures within-window noise, not how concentration varies across hours. One hour is the shortest span that spans several quoting cycles; the range runs from 15 minutes to one day. |
| solver_sample_pages | 8 | pages | [2, 10] | Number of method-filtered NearBlocks execute_intents pages (50 receipts each) in the stratified solver sample: the newest page plus pages placed at even time offsets back to solver_sample_target_span_s. Each page is one block of the page-block bootstrap, so more pages tighten the HHI_solver CI. Unauthenticated NearBlocks served 5 solver calls after the caller walk and refused the 6th (HTTP 429, 2026-11-08), so the walk runs in chunks of 5 one rate window apart: 6 to 10 pages cost the same single extra ~62 s window, and 8 = 5 + 3 leaves headroom in the second window. ~400 receipts spread over hours versus the 4 contiguous pages (~3 minutes) used before. |
| solver_sample_target_span_s | 21600 | seconds | [3600, 43200] | Target time depth of the deepest solver-sample page (6 h), reached by jumping NearBlocks' id cursor rather than walking page=N (page >= 2 without a cursor answered HTTP 520 after 50 s on 2026-11-08). Deeper cursors cost latency: 1.4 s at ~5 h, 2.0 s at ~11 h, 14 s at ~41 h, 40 s at ~7 days (measured 2026-11-08). 6 h is 6x the solver_sample_min_span_s floor, so a misaimed cursor still clears it, and spans the Asia/Europe/US session hand-offs inside one run; the range runs from the 1 h minimum to 12 h (latency still ~2 s). |
| evidence_materiality_share | 0.1 | ratio | [0.05, 0.25] | Scorecard threshold: a flow share (confidential volume, AI-agent-labeled receipts) is called 'material' at >= 10% of the measured total; below it the claim is graded NOT_SUPPORTED. A conventional materiality line, not a fitted value. |


### 14.2 Measured and derived model inputs (point values with their source)
| Key | Value | Unit | Source | Basis |
| :--- | :--- | :--- | :--- | :--- |
| total_supply_near | 1,311,498,639 | NEAR | measured | RPC block header total_supply at height 224186938 |
| current_max_inflation_rate | 0.025 | ratio_annual | measured | RPC EXPERIMENTAL_protocol_config.max_inflation_rate |
| treasury_share | 0 | ratio | measured | RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this) |
| staked_supply_ratio | 0.444294 | ratio | measured | RPC validators current stake / total_supply (354 validators) |
| annual_issuance_near | 32,766,005 | NEAR_per_year | measured | minted_per_epoch 25454.651403393877 NEAR x epochs_per_year 1287.2305496960403 from total_supply jumps at epoch starts 224135537 -> 224178737 |
| issuance_realization_factor | 0.999345 | ratio | measured | measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path |
| near_price_usd | 3.51 | USD | measured | nearstats price.currentUsd via intents_forensics.price.current_usd |
| daily_volume_usd | 125,257,736 | USD_per_day | measured | intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window (aligned daily charts, 30 complete UTC day |
| gross_take_bps | 15.8627 | bps | measured | intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window (aligned daily charts, 30 complete UTC |
| capture_ratio | 0.304921 | ratio | measured | intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window (aligned daily charts, 30 complete  |
| gas_burn_near_per_day | 727.2301 | NEAR_per_day | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| state_lock_growth_near_per_day | 336.4582 | NEAR_per_day | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| public_volume_growth_yoy | 0.675075 | ratio_yoy | measured | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-12 to 2026-11-11 (365 days, DefiLlama dexs/near-intents): +67.5%/yr, 90% CI +8.6% to +158.5% (Newey |
| competitive_fee_ceiling_bps | 3.0041 | bps | derived | median over cross-VM cells of the best competitor's friction (per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding); the lowest-fric |
| tau_floor_bps | 2.1414 | bps | derived | max(0.5 bps, min(live public take, live cross-VM headroom)) from the execution benchmark (headroom_by_archetype_bps.cross_vm = 2.14 bps). |
| tau_pub_start_bps | 15.2383 | bps | derived | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d; blended live gross take 15.86 bps (DefiLlama daily fees / daily volume summed over the a |
| alpha_capture | 0.304921 | ratio | measured | measured:defillama near-intents dailyHoldersRevenue / fees |
| terminal_multiple | 60 | x_fdv_to_revenue | derived | peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; raw 2513.9x. |
| confidential_share_start | 0.131131 | ratio | derived | on-chain estimate: Confidential Intents Treasury 24h inflow / (24h volume + inflow) = 13.1% (band 11.6%-14.8%); nearstats split implausible. Estimated from the  |
| sigma_price_annual | 1.0255 | ratio_annual | measured | nearstats:price-history: 1y daily closes, log-return sigma x sqrt(365). |
| sigma_volume_monthly | 0.337579 | ratio_monthly | measured | measured: monthly log-return sigma of 30-day volume aggregates |


## 15. Reproduction

```bash
# from the repo root; no API keys; about 8 minutes wall clock (the live quote race and rate-limited NearBlocks sampling dominate)
make reproduce          # == cd quant && uv run python -m valuo.reproduce   (canonical artifacts/)
make test               # offline unit tests + invariant checks against artifacts/
# this snapshot was produced by: cd quant && uv run python -m valuo.reproduce
# faster smoke (no quote race, 2,000 paths) writes to artifacts/dev/, never over the canonical files:
make reproduce-fast     # == cd quant && uv run python -m valuo.reproduce --skip-bench --paths 2000
# verify the artifact bytes against the manifest:
shasum -a 256 artifacts/latest_snapshot.json   # must equal manifest.json: snapshot_sha256
```

Determinism: `numpy.random.default_rng(20261114)` draws every shock up front; re-running the Monte Carlo on this snapshot's inputs reproduces every percentile bit-for-bit (tests/test_invariants.py::test_monte_carlo_determinism). Live inputs change block to block, so a fresh run moves the numbers; the memo always states its block and timestamp.

## 16. Data provenance

223 raw exchanges (192 ok, 31 failed), 13,413,307 bytes hashed; raw bodies persisted under `artifacts/raw` and listed with SHA-256 in `manifest.json`.

| Source | Records |
| :--- | ---: |
| across | 15 |
| coingecko | 2 |
| defillama | 22 |
| lifi | 33 |
| near_rpc | 36 |
| near_rpc_archival | 19 |
| nearblocks | 25 |
| nearstats | 2 |
| oneclick | 36 |
| relay | 33 |


Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):
| Source | Name | HTTP | Error |
| :--- | :--- | :--- | :--- |
| across | quote:eth_usdc_sol_usdc:50000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:500 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:250000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| relay | quote:eth_usdc_btc:250000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $160, |
| across | ladder:across:eth_usdc_sol_usdc:1000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | ladder:across:base_usdc_arb_usdc:500000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 433017.692629 US |
| relay | ladder:relay:eth_usdc_btc:250000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $160, |
| across | ladder:across:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 433017.692629 US |
| across | ladder:across:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 433017.692629 US |
| relay | ladder:relay:eth_usdc_btc:500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $160, |
| relay | ladder:relay:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,40 |
| across | ladder:across:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 433017.692629 US |
| relay | ladder:relay:eth_usdc_btc:1000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $160, |
| relay | ladder:relay:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,40 |
| relay | ladder:relay:eth_usdc_btc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $160, |
| relay | ladder:relay:eth_usdc_btc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $160, |
| relay | ladder:relay:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Quote amount exceeds the maximum for this pair |
| oneclick | ladder:1click:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| lifi | ladder:lifi:base_usdc_arb_usdc:2500000 | 429 | HTTP 429: Rate limit exceeded, retry in 2 hours |
| lifi | ladder:lifi:eth_usdc_sol_usdc:5000000 | 429 | HTTP 429: Rate limit exceeded, retry in 2 hours |
| lifi | ladder:lifi:eth_usdc_btc:1000000 | 429 | HTTP 429: Rate limit exceeded, retry in 2 hours |
| lifi | ladder:lifi:base_usdc_arb_usdc:5000000 | 429 | HTTP 429: Rate limit exceeded, retry in 2 hours |
| lifi | ladder:lifi:eth_usdc_btc:2500000 | 429 | HTTP 429: Rate limit exceeded, retry in 2 hours |
| lifi | ladder:lifi:eth_usdc_btc:5000000 | 429 | HTTP 429: Rate limit exceeded, retry in 2 hours |


### 16.1 Methodology warnings recorded during the run (15)
- fee_pool: across: 3 malformed, negative or duplicate chart rows skipped
- execution_bench: eth_usdc_sol_usdc $500: venue USD oracles disagree with the cell's common price by more than the +2.41 bps headroom (1click -0.0 bps, relay +2.2 bps, lifi +4.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the +2.14 bps headroom (1click +0.0 bps, relay +2.2 bps, lifi +4.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +2.2 bps, lifi +4.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $50,000: venue USD oracles disagree with the cell's common price by more than the -5.14 bps headroom (1click +0.0 bps, relay -10.7 bps, lifi -9.7 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $500: venue USD oracles disagree with the cell's common price by more than the -0.59 bps headroom (1click -0.0 bps, relay +2.2 bps, lifi -3.7 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the -0.94 bps headroom (1click +0.0 bps, relay +2.2 bps, lifi -3.7 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +2.2 bps, lifi -3.7 bps); headroom is measured on destination units, not USD legs
- intents_forensics: confidential split: nearstats reports confidential 30d $0.00 (0.0000%), rejected (tvl_without_volume: confidential TVL $136.73M but all-time confidential volume $0.09 of $38.38B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'). Share ESTIMATED ON-CHAIN from the Confidential Intents Treasury: 13.1% (band 11.6%-14.8%; 24h inflow $14.83M, outflow $16.73M, volume $113.12M), replacing the registry assumption 40%
- intents_forensics: take-rate window leaves out 2026-11-11: DefiLlama reports revenue above fees for that day, so its fee figure is not final; the window ends the day before
- intents_forensics: nearblocks: 27 duplicate receipt(s) seen on overlapping pages were counted once (id-based cursor vs time-ordered rows); unique receipts sampled = 173
- chain_signatures: 240 s sampling budget spent (NearBlocks rate limits) in pass 1 with 6 window(s) left; set VALUO_CHAINSIG_BUDGET_S to sample them
- chain_signatures: 6 of 12 sample windows failed; rates use the 6 that returned
- sotp: confidential share 13.1% is an ON-CHAIN ESTIMATE from Confidential Intents Treasury boundary flows (band 11.6%-14.8%), not nearstats' split (rejected as implausible); 24h window, biases listed in intents_forensics.volume.confidential_share_estimate
- sotp: peer median FDV/revenue 2513.9x clipped to 60.0x (guardrails [8, 60])
