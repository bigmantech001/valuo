# Valuo IC Memo: NEAR at block 224,174,242

*NEAR Intents clearinghouse + NEAR L1. Generated 2026-11-12T06:05:03.441Z UTC from live mainnet RPC and key-free public APIs; every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section 13.*

| Provenance | Value |
| :--- | :--- |
| NEAR block | 224,174,242 (`G4aqhtzTMJvjgHFLT29VANxhVwsqYYsjeihF2PFjo25h`), 2026-11-12T06:05:01.555Z |
| RPC endpoint | https://free.rpc.fastnear.com |
| Snapshot generated | 2026-11-12T06:05:03.441Z UTC, runtime 781.2 s, valuo 0.1.0, schema 1.0.0 |
| Snapshot SHA-256 | `f201d830075e3451cb4aaadcd502ee1c393c84b7e01b5a33e0646b25e173c11e` |
| Monte Carlo | seed 20261114, 10,000 paths, 36 months |
| Raw records | 140 HTTP/RPC exchanges hashed, 5 non-2xx/failed (every one listed in manifest.json) |


## 1. The long-term case, made falsifiable

The long-term case for NEAR at $4.63B: 3 of 8 measured conditions are on track. It holds if the market keeps an L1 multiple (135x revenue needed against a 2,512x peer median) while Intents grows into it; it fails if volume growth stays near 22% a year against the 127% the price implies.

| Condition | Required | Live | Trend | Status |
| :--- | ---: | ---: | :--- | :--- |
| Intents volume compounds fast enough to grow into the price | 127% a year | 22% a year | +89% (30-day volume vs 90 days earlier) | **Behind** |
| Holder revenue (buybacks) scales to support the price at the model's multiple | $165.2M a year | $22.0M a year | +289% (30-day holder revenue vs 90 days earlier) | **Behind** |
| The market keeps valuing NEAR like an L1, not like a fee-only app | 135x | 2,512x | n/a | **On track** |
| 1Click keeps a pricing edge where it competes (cross-VM routes) | > 0 | +2.25 bps | n/a | **On track** |
| Confidential (private) flow keeps growing | > 0 | $14.1M | +372% (confidential TVL vs 90 days earlier) | **On track** |
| Fees retire more NEAR than issuance creates | $409.1M a day | $124.4M a day | n/a | **Behind** |
| Governance cuts issuance from 2.5% to 1.6% | 1.6% | 2.5% | n/a | **Behind** |
| Solver competition stays broad enough to keep spreads tight | <= 3,500 | 4,324 | n/a | **Against** |


How to read it: each requirement is what the market price needs if that condition alone carries the case (from the reverse valuation in section 3), or the threshold the bear case watches (section 11). An investor holding NEAR long-term is betting that the conditions marked Behind close; the ones marked Against are where the case is currently losing. Re-run `make reproduce` to re-grade every row against live data.

## 2. Executive summary

**Model value vs market value.** Market FDV is $4.63B (spot price x on-chain total supply at block 224,174,242). The model's expected-path FDV is $2.11B and its 10,000-path Monte Carlo gives P10 / P50 / P90 = $134.7M / $689.1M / $4.17B. The market sits above the expected path (2.2x it) and at 6.7x the Monte Carlo P50. The model capitalises NEAR Intents holder revenue, L1 gas burn and state-lock flow over 36 months at a 25% discount rate and a 60x terminal multiple; the question below is which input would have to change for it to reach the market price, and whether the evidence allows that.

**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in section 3).

| Input | Base | Required for market FDV | Evidence | Inside evidence |
| :--- | ---: | ---: | ---: | :--- |
| Expected annual public-volume growth (3-year path) | 67.5% | 127.4% | 21.8% | no |
| Starting gross public take rate | 14.91 bps | 56.99 bps | 3.00 bps | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 135x | 2,512x | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $4.08B) | 10.0% | n/a |
| Confidential share of volume at month 36 | 40.0% | 76.1% | 11.5% | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $72.3M/yr | $165.2M/yr | $22.0M/yr | no |


**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple (135x needed; live peer FDV/revenue HYPE 81x, SOL 2,512x, ETH 3,296x, median 2,512x over n = 3 peers). No discount rate closes the gap: even at 0% the model reaches $4.08B against the market's $4.63B, because the terminal multiple is capped at 60x. The gap is a multiple question, not a discount-rate question. The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on Intents cash flow at the model's 60x terminal cap. On cash flow alone (multiple held at the model's 60x), the market price requires 127%/yr expected public-volume growth for 3 years (trailing 12 months: +21.8%), or a 57 bps starting public take (today 14.91 bps, live competitive ceiling 3.00 bps), or $165.2M of annualised holder revenue in year 3 (7.5x today's $22.0M); none of these is inside its measured evidence. Whether NEAR keeps an L1 multiple is the investment question; this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token.

**What you have to believe** (section 4). The three inputs that move FDV most are Expected annual public-volume growth (8.6% to 158.5%: $710.2M-$6.45B); Terminal FDV / holder-revenue multiple (8.00x to 150x: $369.2M-$5.13B); Public take compression speed (per month) (0.0%/month to 15.0%/month: $847.9M-$3.53B). Together they carry 86% of the swing-squared variance proxy. 2 of 17 single-input ranges reach the market FDV.

**Relative value** (section 5). NEAR trades at 64x annualised fees against a peer median of 257x (rank 2 of 4, lowest multiple first; inside the peer range); at peer FDV/fees multiples NEAR's fees map to $11.50B-$46.25B (cross-check, not a fair value; n = 3 peers); holder revenue covers 20% of the $115.4M/yr security budget.

**Evidence quality flags.**

- Confidential share: ESTIMATED ON-CHAIN at 11.5% (band 11.5%-14.8%). nearstats reported 0.0000%, which its own payload contradicts, so the share is read from the Confidential Intents Treasury instead: 24h inflow $14.7M, outflow $16.7M, against 24h volume $113.1M. Same-hour netting and in-shard turnover bias it down, solver inventory up; one 24h window. Engine 2 ($862.9M of the $2.11B expected-path FDV) is valued on this estimate, not on the 40% registry assumption. On-chain cross-check: the Confidential Intents treasury (`51e8f94d...de7cbe` in `intents.near`) holds $136.6M at block 224,174,254 (204 tokens, 30 unpriced); net 30-day boundary flow $14.1M at today's prices; over 24h at least $14.7M entered and $16.7M left (hourly snapshots, lower bounds), an inflow of 11.5% of 24h volume. Confidential swaps settle on a private chain whose RPC needs authentication, so swap volume itself cannot be read; boundary inflow is a proxy, not the share (it nets same-hour flows and includes solver inventory).
- Deposit/caller HHI 2,450 (bootstrap 90% CI 1,500-3,550) over 20 external receipts spanning 39 s; a point sample, not a market-share estimate.
- Solver HHI 4,324 (bootstrap 90% CI 3,757-4,816) over 87 fill participations spanning 17,341 s. Cartel trigger: BREACHED (sample: 87 solver fill participations over 17,341 s).
- Bear case: 2 of 4 graded early-warning triggers breached. Combined-worst deterministic FDV $214.5M (-90%).

## 3. What the market is pricing (reverse valuation)

Basis: deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base. Solver: scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12. Market FDV $4.63B; expected-path model FDV $2.11B (gap 2.2x); Monte Carlo P50 $689.1M (gap 6.7x). Every required value is the expected-path requirement; the P50 sits lower by lognormal convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).

| Input | Base | Required for market FDV | Evidence | Evidence basis | Inside evidence |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Expected annual public-volume growth (3-year path) | 67.5% | 127.4% | 21.8% | trailing-12-month NEAR Intents 30-day volume growth | no |
| Starting gross public take rate | 14.91 bps | 56.99 bps | 3.00 bps | live competitive fee ceiling (median best-competitor friction, cross-VM cells) | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 135x | 2,512x | peer median FDV / annualised revenue ex-NEAR (unclipped) | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $4.08B) | 10.0% | low end of the registry discount-rate range (10%-40%) | n/a |
| Confidential share of volume at month 36 | 40.0% | 76.1% | 11.5% | on-chain estimate of the confidential share (Confidential Intents Treasury 24h boundary flow / 24h volume) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $72.3M/yr | $165.2M/yr | $22.0M/yr | current annualised holder revenue (30-day window x 365.25/30) | no |

- Justifying $4.63B needs 127% expected annual public-volume growth for 3 years (base 68%); trailing-12-month Intents volume growth was 22%.
- Justifying $4.63B needs a starting gross public take of 57.0 bps (decaying to the 2.25 bps floor at 3%/month) versus 14.91 bps today; the live competitive fee ceiling is 3.00 bps.
- Justifying $4.63B needs a 135x terminal FDV/holder-revenue multiple; the live peer median is 2,512x (HYPE 81x, SOL 2,512x, ETH 3,296x) and the model caps it at 60x.
- Even a 0% discount rate gives $4.08B, short of $4.63B: the gap is not a discount-rate question.
- Justifying $4.63B needs the confidential share to reach 76% by month 36; the on-chain estimate today is 12% (band 12%-15%).
- Justifying $4.63B at the 60x base multiple needs $165M of annualised holder revenue in year 3 (2.3x the base path's $72M), versus $22M today (96%/yr compounded).

Headline: Market FDV $4.63B is 2.2x the model's expected-path FDV $2.11B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 135x (evidence 2,512x).

Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the joint requirement is smaller than any single one; section 4 shows which inputs carry the variance.

## 4. What you have to believe (one-at-a-time sensitivity)

Basis: deterministic_sotp expected path; one input at its low / high, all others at the snapshot base. Base expected-path FDV $2.11B against a $4.63B market FDV. Variance share: swing^2 / sum(swing^2): first-order share for independent inputs, an approximation. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).

| # | Input | Source | Range | Base | FDV at low | FDV at high | Swing | Variance share |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Expected annual public-volume growth | assumption | 8.6% - 158.5% | 67.5% | $710.2M | $6.45B | $5.74B | 44.9% |
| 2 | Terminal FDV / holder-revenue multiple | derived | 8.00x - 150x | 60x | $369.2M | $5.13B | $4.76B | 30.8% |
| 3 | Public take compression speed (per month) | assumption | 0.0%/month - 15.0%/month | 3.0%/month | $3.53B | $847.9M | $2.68B | 9.8% |
| 4 | Confidential share at month 36 | assumption | 5.0% - 60.0% | 40.0% | $1.35B | $3.00B | $1.65B | 3.7% |
| 5 | Annual discount rate | assumption | 10.0% - 40.0% | 25.0% | $3.08B | $1.51B | $1.56B | 3.3% |
| 6 | Starting 30-day Intents volume (public + confidential) | measured | 0.71x - 1.40x | 1.00x | $1.55B | $2.90B | $1.35B | 2.5% |
| 7 | Holder capture (revenue / gross fees) | measured | 13.2% - 31.2% | 31.2% | $982.0M | $2.11B | $1.13B | 1.7% |
| 8 | NEAR price drift (gas-burn and state-lock USD value) | assumption | -50.0% - 100.0% | 0.0% | $1.99B | $2.87B | $883.0M | 1.1% |
| 9 | Confidential multiple haircut | assumption | 30.0% - 100.0% | 70.0% | $1.64B | $2.47B | $826.1M | 0.9% |
| 10 | Confidential gross take (public take re-reconciled to live fees) | assumption | 10.00 bps - 30.00 bps | 20.00 bps | $1.77B | $2.45B | $672.7M | 0.6% |
| 11 | Confidential compression divisor | assumption | 1.00x - 10x | 3.00x | $1.77B | $2.29B | $524.9M | 0.4% |
| 12 | Blended gross take (public take re-reconciled) | measured | 12.40 bps - 16.94 bps | 15.50 bps | $1.90B | $2.21B | $307.4M | 0.1% |
| 13 | Public take hard floor | assumption | 0.00 bps - 5.00 bps | 0.50 bps | $2.11B | $2.40B | $291.3M | 0.1% |
| 14 | Cross-VM headroom (sets the public take floor) | measured | 1.69 bps - 2.81 bps | 2.25 bps | $2.05B | $2.17B | $119.3M | 0.0% |
| 15 | NEAR spot price (USD value of gas burn and state lock) | measured | $2.63 - $4.75 | $3.53 | $2.07B | $2.16B | $91.2M | 0.0% |
| 16 | L1 gas burn (NEAR/day) | measured | 725 NEAR/day - 1,208 NEAR/day | 966 NEAR/day | $2.07B | $2.15B | $74.8M | 0.0% |
| 17 | State-lock growth (NEAR/day) | measured | 253 NEAR/day - 422 NEAR/day | 337 NEAR/day | $2.11B | $2.11B | $1.1M | 0.0% |

Top three inputs carry 86% of the variance proxy. 2 of 17 single-input ranges reach the market FDV at either end.

Headline: public_volume_growth_yoy, terminal_multiple, fee_compression_lambda_monthly carry 86% of the swing-squared variance proxy; public_volume_growth_yoy alone moves FDV from $710M to $6.45B across its range, and 2 of 17 single-input ranges reach the $4.63B market FDV.

Excluded (move issuance and implied price, not FDV): svrn_target_inflation (issuance path only: moves supply at horizon and implied price, not FDV); svrn_glidepath_months (issuance path only: moves supply at horizon and implied price, not FDV).

## 5. Relative value: peer cash-flow multiples and the security budget

Basis: live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR.

### 5.1 NEAR cash-flow coverage against the peer set
| Metric | NEAR | Peer median | Peer P25 - P75 | NEAR rank | Position |
| :--- | ---: | ---: | ---: | ---: | :--- |
| FDV / annualised fees (30-day run-rate) | 64x | 257x | 160x - 643x | 2 of 4 | inside the peer range |
| FDV / annualised revenue (30-day run-rate) | 200x | 2,512x | 1,297x - 2,904x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day fees | 84x | 229x | 152x - 827x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day revenue | 452x | 2,089x | 1,094x - 3,654x | 2 of 4 | inside the peer range |

| Protocol | FDV | Fees (ann.) | Revenue (ann.) | FDV/fees | FDV/revenue | FDV/fees 1y | FDV/revenue 1y | Revenue/fees |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SOL (solana) | $52.84B | $205.5M | $21.0M | 257x | 2,512x | 229x | 2,089x | 10% |
| ETH (ethereum) | $249.99B | $243.2M | $75.8M | 1,028x | 3,296x | 1,424x | 5,219x | 31% |
| HYPE (hyperliquid) | $67.97B | $1.09B | $837.4M | 62x | 81x | 76x | 100x | 77% |
| NEAR (near_combined) | $4.61B | $72.0M | $23.1M | 64x | 200x | 84x | 452x | 32% |
| NEAR (near) | $4.61B | $1.6M | $1.1M | 2,827x | 4,038x | 3,979x | 5,680x | 70% |
| NEAR (near-intents) | $4.61B | $70.3M | $21.9M | 66x | 210x | 86x | 491x | 31% |

The model's terminal multiple is 60x; 0 of 3 peers trade at or below it on FDV/revenue.

### 5.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)
| Cash flow | NEAR (ann.) | at peer P25 | at peer median | at peer P75 | Peers | Basis |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| fees | $72.0M | $11.50B | $18.51B | $46.25B | 3 | comps.near_combined.annualized_fees_usd x peer FDV / annualised fees (30-day run-rate) |
| revenue | $23.1M | $29.93B | $57.98B | $67.03B | 3 | comps.near_combined.annualized_revenue_usd x peer FDV / annualised revenue (30-day run-rate) |

relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution; market FDV $4.63B.

### 5.3 Staking and security budget
- Security budget: 32,701,161 NEAR/yr of issuance (2.49%) x $3.53 = $115.4M/yr (2.50% of FDV).
- Against it: $72.0M/yr of fees (62% of the budget) and $23.1M/yr of holder revenue (20%); net dilution $92.4M/yr.
- Staked 44.4% of supply; nominal staking APR 5.63%. Basis: security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate.

### 5.4 Findings
- NEAR trades at 64x annualised fees versus a peer median of 257x (rank 2 of 4, lowest first; inside the peer range); on revenue it is 200x versus 2,512x (inside the peer range).
- 0 of 3 peers trade at or below the model's 60x terminal FDV/revenue multiple; NEAR itself trades at 200x.
- At the peer FDV/fees distribution, NEAR's $72M of annualised fees maps to $11.50B-$46.25B (median $18.51B, n = 3) against a $4.63B market FDV; a relative-value cross-check, not a fair value.
- NEAR issues $115M a year to validators and delegators (2.5% of FDV) against $72M of annualised fees and $23M of holder revenue (gas burn + Intents buyback): revenue covers 20% of the security budget.
- At 2.5% inflation stakers earn 5.63% nominal and 3.61% real including buybacks; non-stakers lose 2.03% a year to dilution net of buybacks.

Caveat: Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples compare different cash-flow definitions; with n = 3 peers the median is a reference point, not a distribution.

## 6. Model valuation detail

**Base case.** 10,000-path SOTP (seed 20261114): P10 / P50 / P90 FDV = $134.7M / **$689.1M** / $4.17B; implied price $0.10 / **$0.50** / $3.05 per NEAR against spot $3.53. The P50 sits 85.1% below the current FDV of $4.63B. The deterministic SOTP at the labeled inputs (the expected-volume path) is $2.11B: engines $1.10B clearinghouse + $862.9M confidential + $151.8M monetary; the Monte Carlo mean is $2.00B. Ex-monetary P50: $653.9M.

**Volume growth is measured, not assumed.** Trend growth of NEAR Intents daily volume over 2025-11-12 to 2026-11-11 (365 days, DefiLlama): +67.5%/yr, 90% CI +9% to +158% (OLS of log volume on time, Newey-West errors). The model uses it as public_volume_growth_yoy, with the CI as its range; it is the median trend, so reading it as expected growth is conservative. Cross-checks, not used: yoy trailing 30d +53%, mean monthly log return 12m +30%.



**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled +68% YoY volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of 0.338 the MEDIAN simulated path ends month 36 at 12.9% of the expected path ($66.5M/day vs $517.3M/day), which is what pulls the P50 FDV below the mean. The dispersion is measured from 11 monthly volume log-returns (sigma excluding the three oldest, incentive-era windows: 0.323); a thin sample, reported as such.

**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation; section 3 solves which single input would: Market FDV $4.63B is 2.2x the model's expected-path FDV $2.11B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 135x (evidence 2,512x). The P90 ($4.17B) comes from volume paths, not from take-rate expansion (the public take only compresses in this model).

**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** 6 bps net take needs >= $1.00B/day; 10 bps net take needs >= $500.0M/day; 14 bps net take needs >= $500.0M/day; 18 bps net take needs >= $250.0M/day. Live run-rate: $124.4M/day at 4.83 bps net (15.50 bps gross x capture 31.2%).

**Net-float crossover.** Today sinks cover 20.5% of measured issuance (18,329 NEAR/day vs 89,531 NEAR/day). status quo (cap flat): deterministic flow crossover none within horizon at run-rate volume, none within horizon with the +68% YoY growth assumption; Monte Carlo P(crossover within 36m) = 65.6%, P(deflationary at horizon) = 47.8%; breakeven volume V* = $644.5M/day (5.2x today). SVRN glidepath: deterministic flow crossover none within horizon at run-rate volume, month 30 with the +68% YoY growth assumption; Monte Carlo P(crossover within 36m) = 73.0%, P(deflationary at horizon) = 56.0%; breakeven volume V* = $409.1M/day (3.3x today). The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price outruns issuance); the deterministic path (the expected-volume path) is the one to quote.

**Falsification.** Four stress scenarios (section 11) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo percentile) at $214.5M (-90% vs the deterministic base $2.11B); 2 of 4 measured early-warning triggers are breached in this snapshot (breached: governance_stalemate (max_inflation_rate now 2.50% vs > 1.60%); solver_cartelization (hhi_solver now 4,324 vs > 3,500)). The on-chain inflation cap reads 2.50%; the SVRN cut is a proposal, not protocol state.

## 7. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)

Executable quotes fetched 2026-11-12T06:05:10.633Z UTC (29 ok of 36; 1Click token universe 230 assets on 39 chains). Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input (headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price (`price_basis`: oneclick_token_list_oracle); raw-unit friction is exact for USDC -> USDC. Positive headroom means 1Click paid out more after all fees.

| Corridor | Clip | Venue | Status | Out | Friction | ETA | Route |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | 1click | ok | 499.955320 | 0.89 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $500 | relay | ok | 499.829839 | 3.40 bps (raw) | 1 s | relay |
| ETH USDC -> SOL USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $500 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $50,000 | 1click | ok | 49,996.231269 | 0.75 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $50,000 | relay | ok | 49,984.979839 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $50,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $250,000 | 1click | ok | 249,949.492595 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $250,000 | relay | ok | 249,924.979839 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $250,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | 1click | ok | 0.006764 | 44.62 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $500 | relay | ok | 0.006776 | 27.27 bps (usd) | 292 s | relay |
| ETH USDC -> native BTC | $500 | lifi | ok | 0.006770 | 35.39 bps (usd) | 402 s | layerswap |
| ETH USDC -> native BTC | $500 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | 1click | ok | 0.678253 | 17.19 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $50,000 | relay | ok | 0.678259 | 17.10 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $50,000 | lifi | ok | 0.677976 | 21.26 bps (usd) | 417 s | layerswap |
| ETH USDC -> native BTC | $50,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | 1click | ok | 3.386311 | 31.77 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $250,000 | relay | no_liquidity: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | lifi | ok | 3.382045 | 44.33 bps (usd) | 1,392 s | near (= NEAR Intents resold via LI.FI) |
| ETH USDC -> native BTC | $250,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | 1click | ok | 499.897757 | 2.04 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $500 | relay | ok | 499.927523 | 1.45 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $500 | across | ok | 499.942703 | 1.15 bps (raw) | 2 s | across |
| Base USDC -> Arbitrum USDC | $50,000 | 1click | ok | 49,989.895220 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $50,000 | relay | ok | 49,994.977523 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $50,000 | across | ok | 49,994.992703 | 1.00 bps (raw) | 120 s | across |
| Base USDC -> Arbitrum USDC | $250,000 | 1click | ok | 249,949.497300 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $250,000 | relay | ok | 249,974.977529 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $250,000 | across | ok | 249,974.992703 | 1.00 bps (raw) | 900 s | across |


| Corridor | Clip | Headroom | Basis | 1Click rank | Reading |
| :--- | ---: | ---: | :--- | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | +2.51 bps | dest_units | 1/3 | 1Click delivers 2.51 bps more than relay |
| ETH USDC -> SOL USDC | $50,000 | +2.25 bps | dest_units | 1/3 | 1Click delivers 2.25 bps more than relay |
| ETH USDC -> SOL USDC | $250,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> native BTC | $500 | -17.40 bps | dest_units | 3/3 | 1Click trails relay by 17.40 bps |
| ETH USDC -> native BTC | $50,000 | -0.09 bps | dest_units | 2/3 | 1Click trails relay by 0.09 bps |
| ETH USDC -> native BTC | $250,000 | +12.61 bps | dest_units | 1/2 | 1Click delivers 12.61 bps more than lifi |
| Base USDC -> Arbitrum USDC | $500 | -0.90 bps | dest_units | 3/4 | 1Click trails across by 0.90 bps |
| Base USDC -> Arbitrum USDC | $50,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |
| Base USDC -> Arbitrum USDC | $250,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |


- cross_vm: median headroom +2.25 bps over 3 comparable cells
- native_btc: median headroom -0.09 bps over 3 comparable cells
- evm_l2: median headroom -1.02 bps over 3 comparable cells
- competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = 3; per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding): 3.00 bps. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not.

- Where 1Click loses (destination units): eth_usdc_btc at $500 trails relay by 17.40 bps; eth_usdc_btc at $50,000 trails relay by 0.09 bps; base_usdc_arb_usdc at $500 trails across by 0.90 bps; base_usdc_arb_usdc at $50,000 trails across by 1.02 bps; base_usdc_arb_usdc at $250,000 trails across by 1.02 bps.
- Oracle caveat: on eth_usdc_sol_usdc at $500, eth_usdc_sol_usdc at $50,000, eth_usdc_sol_usdc at $250,000, eth_usdc_btc at $500, eth_usdc_btc at $50,000, base_usdc_arb_usdc at $500, base_usdc_arb_usdc at $50,000, base_usdc_arb_usdc at $250,000 the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg comparison there would have been decided by oracles, which is why the ranking uses units.
- Structurally unsupported routes: across on eth_usdc_btc (declared), across on eth_usdc_sol_usdc (ROUTE_NOT_ENABLED).
- LI.FI's quote on eth_usdc_btc $250,000 routes through NEAR Intents itself (tool `near`), so it is 1Click execution plus LI.FI's fee, not an independent price.
- Collector summary: cross_vm (ETH USDC -> SOL USDC): $500: 1Click delivers 2.51 bps more than relay (rank 1/3, destination units); $50,000: 1Click delivers 2.25 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); unsupported: across (ROUTE_NOT_ENABLED). native_btc (ETH USDC -> native BTC): $500: 1Click trails 17.40 bps behind relay (rank 3/3, destination units); $50,000: 1Click trails 0.09 bps behind relay (rank 2/3, destination units); $250,000: 1Click delivers 12.61 bps more than lifi (rank 1/2, destination units); unsupported: across (Across is EVM-only; no Bitcoin route); relay no_liquidity at $250,000. evm_l2 (Base USDC -> Arbitrum USDC): $500: 1Click trails 0.90 bps behind across (rank 3/4, destination units); $50,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units); $250,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units).

## 8. Concentration and agents on intents.near (NearBlocks receipts)

- Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = **2,450** (bootstrap 90% CI 1,500-3,550) (N_eff = 4.08); over all predecessors 3,699; ex-AI-agent 1,405 (N_eff 7.12). These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.
- (b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = **4,324** (bootstrap 90% CI 3,757-4,816) (N_eff 2.31) across 87 fill participations in 86 fills (1 atomic token_diff fills, 85 solver-to-settlement-hub legs), 6 distinct solvers; 441 execute_intents receipts decoded, 0 unresolved; the solver sample spans 17,341 s. This is the population the solver_cartelization trigger reads; trigger status: breached.
- AI-agent share of external receipts 45.0% is a NAME-PATTERN classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. Bridge / token-contract share 35.0%; 10 unique external callers in 20 external receipts.
- Sample: 137 unique receipts over 8 NearBlocks pages, blocks 224,174,189-224,174,258, a 39 s window; lifetime receipts on intents.near 156,860,546. A window this short is a point sample, not a market-share estimate; both HHIs move by hundreds of points between runs.
- Method mix: TRANSFER 61, execute_intents 41, ft_resolve_withdraw 8, ft_on_transfer 7, ft_transfer_call 4, ft_transfer 4, storage_deposit 3, do_storage_deposit 3, near_withdraw 3, mt_resolve_withdraw 1.

### 8.1 Deposit / caller concentration (external predecessors)
| Caller | Class | Receipts | Share | Example tx |
| :--- | :--- | ---: | ---: | :--- |
| escrow.ai.near | AI agent | 9 | 45.0% | [3nwTqqKPjsTg...](https://nearblocks.io/txns/3nwTqqKPjsTg4wSAsCm9TBF7Jw5z2GGpaAkgBmZdZeaZ) |
| wrap.near | named account | 3 | 15.0% | [ErVR3nzhhCd7...](https://nearblocks.io/txns/ErVR3nzhhCd7VXtRfCbwGULE7EuiPjxMGZSdyRMBJztq) |
| avax-0xb97ef9ef8734c71904d8002f8b6bc66dd9c48a6e.omdep.near | bridge / token contract | 1 | 5.0% | [5X5ya2mserFY...](https://nearblocks.io/txns/5X5ya2mserFYmhFoikFvQHhy3Gc8p82WJYeHHETXXvjh) |
| blockzen-1-main.near | named account | 1 | 5.0% | [7djVsQggWpmm...](https://nearblocks.io/txns/7djVsQggWpmmyRY5vyrR3635GcSDVx6VHWr5xpmkC38G) |
| bnb-0x55d398326f99059ff775485246999027b3197955.omdep.near | bridge / token contract | 1 | 5.0% | [9kUNEKx3TepD...](https://nearblocks.io/txns/9kUNEKx3TepDqk2afgWqTLaKpLHa8ftNFW8jSXwFx7NH) |
| eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near | bridge / token contract | 1 | 5.0% | [D6UXkPGhsEHQ...](https://nearblocks.io/txns/D6UXkPGhsEHQg1RDshS6hosFBmdBG8HLFbQDuwPKr9hM) |
| eth-0xdac17f958d2ee523a2206206994597c13d831ec7.omft.near | bridge / token contract | 1 | 5.0% | [BTKeejQHMx3S...](https://nearblocks.io/txns/BTKeejQHMx3SYi1FLNDr3NhFeJskHQV8FQE59EWZm9c) |
| eth.omft.near | bridge / token contract | 1 | 5.0% | [2Zyy4QWVnWzx...](https://nearblocks.io/txns/2Zyy4QWVnWzxwuko1K7LymsLX2ZAqmw8f948PJs86soD) |
| xrp.omft.near | bridge / token contract | 1 | 5.0% | [F3apej1NBMJu...](https://nearblocks.io/txns/F3apej1NBMJufighgABsUf7yuVADjHkjctYumE4L5x6q) |
| zec.omft.near | bridge / token contract | 1 | 5.0% | [HEp67SLZdxms...](https://nearblocks.io/txns/HEp67SLZdxmsnjuhrse6tf2iDFYxcWrTAh7WKUs4E9yJ) |

### 8.2 Solver concentration (execute_intents signers)
| Solver account | Fill participations | Share | Example tx |
| :--- | ---: | ---: | :--- |
| solver-priv-liq.near | 49 | 56.3% | [2zxkghyWnbuq...](https://nearblocks.io/txns/2zxkghyWnbuqfcwyjDof42fyRuN8VWKtuKAmbjsVwK2t) |
| solver-multichain-asset.near | 29 | 33.3% | [EdzfSHsAn8uW...](https://nearblocks.io/txns/EdzfSHsAn8uWxRgMjjoC9Yrxdj3i7NXRehG3S8xq6brv) |
| 6247d9c671ca6a80cf2c75e26edb8cd75ebf00fcd3c56c39107d6ca20c9cfb29 | 5 | 5.7% | [B6qoWHZZ62vQ...](https://nearblocks.io/txns/B6qoWHZZ62vQsKVGioP7eS2mseBCc7BJ2DYEtWUPZCek) |
| solver-multichain-asset-3.near | 2 | 2.3% | [2zxkghyWnbuq...](https://nearblocks.io/txns/2zxkghyWnbuqfcwyjDof42fyRuN8VWKtuKAmbjsVwK2t) |
| solver-multichain-asset-2.near | 1 | 1.1% | [BKNN2yMBMGgK...](https://nearblocks.io/txns/BKNN2yMBMGgKMcLDRdRQn8FgA2m7q3huAZQuxgewCbZk) |
| solver-taler.near | 1 | 1.1% | [26nBHWqFhUum...](https://nearblocks.io/txns/26nBHWqFhUumY3CFSqxTmCSWQ3b2iGNzzRzxqbbhnNak) |

Attribution: fill participation = (a) the solver side of an atomic execute_intents fill (>= 2 token_diff signers; solver = pure token_diff signer when the counterparty bundles a withdrawal, else a signer whose name matches (*solver*, *-liq*, market maker) or that the structure rule identified elsewhere in the sample, else the named account facing an implicit 1Click deposit address), or (b) a transfer intent from a solver to the settlement hub (see settlement_hub.rule); HHI over participations per solver account; transfers that are not solver-to-hub legs are inventory or user moves, not fills. hhi_solver_ci90 is a bias-corrected bootstrap (bootstrap_method): a block bootstrap by NearBlocks page when the sample is stratified in time (bootstrap_resampling = block_by_page), else over sampled units

## 9. Supply physics

### 9.1 Issuance: measured vs nominal
- Measured: 26,438.74 NEAR minted at epoch start 224,135,537 (previous jump 26,224.43 NEAR at 224,092,337); epoch wall time 7.087 h = 1,236.9 epochs/yr; implied annual issuance **32,701,161 NEAR** = 2.4935% of supply.
- Nominal: max_inflation_rate 2.50% x total supply 1,311,473,244 NEAR = 32,786,831 NEAR/yr; measured minus nominal -85,670 NEAR/yr (-0.26%). Daily: measured 89,531 NEAR vs nominal 89,765 NEAR; treasury share 0.0% (validators receive the rest).
- Within-epoch supply drift (net gas burn) -285.37 NEAR/epoch; measured block time 0.591 s. Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.

### 9.2 Daily sinks (NEAR/day, live)
| Sink | NEAR/day | Source | Basis |
| :--- | ---: | :--- | :--- |
| Buyback (holders revenue / price) | 17,025.5 NEAR | measured | $124.4M/day x 15.50 bps gross x alpha 31.2% / $3.53 |
| L1 gas burn | 966.4 NEAR | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| NEP state-lock growth | 337.2 NEAR | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| Total sinks | 18,329.1 NEAR |  | coverage 20.5% of measured issuance; net float 71,202 NEAR/day |


### 9.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)
| Regime (terminal rate) | V* at live take | vs today | V* at competitive ceiling |
| :--- | ---: | ---: | ---: |
| status quo (cap flat) | $644.5M | 5.2x | $3.32B |
| SVRN glidepath | $409.1M | 3.3x | $2.11B |

Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.

### 9.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)
| Regime | Volume path | Issuance/day m1 | Issuance/day m36 | Gross issuance 36m | Sinks 36m | Net float 36m | Flow crossover | Cumulative crossover |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| status quo (cap flat) | run-rate volume | 89,531 NEAR | 96,277 NEAR | 101,756,295 NEAR | 20,084,079 NEAR | 81,672,216 NEAR | none within horizon | none within horizon |
| status quo (cap flat) | +68% YoY volume | 89,531 NEAR | 96,277 NEAR | 101,756,295 NEAR | 45,079,887 NEAR | 56,676,408 NEAR | none within horizon | none within horizon |
| SVRN glidepath | run-rate volume | 89,531 NEAR | 60,591 NEAR | 77,173,358 NEAR | 20,084,079 NEAR | 57,089,279 NEAR | none within horizon | none within horizon |
| SVRN glidepath | +68% YoY volume | 89,531 NEAR | 60,591 NEAR | 77,173,358 NEAR | 45,079,887 NEAR | 32,093,471 NEAR | month 30 | none within horizon |


### 9.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)
| Account | Contract | storage_usage bytes | Locked | Growth B/day | Growth NEAR/day | Window |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| intents.near | yes | 13,603,518,865 | 136,035.2 NEAR | 30,489,517 | 304.90 NEAR | 29.9 d |
| aurora | yes | 14,382,126,304 | 143,821.3 NEAR | 3,234,954 | 32.35 NEAR | 29.9 d |
| wrap.near | yes | 168,900,513 | 1,689.0 NEAR | n/a | n/a | n/a |
| v1.signer | yes | 1,164,606 | 11.6 NEAR | n/a | n/a | n/a |
| escrow.ai.near | no | 428 | 0.0 NEAR | n/a | n/a | n/a |
| treasury.near | yes | 357,895 | 3.6 NEAR | n/a | n/a | n/a |
| meme-cooking.near | yes | 5,957,847 | 59.6 NEAR | n/a | n/a | n/a |
| v2.ref-finance.near | yes | 111,293,366 | 1,112.9 NEAR | n/a | n/a | n/a |

- Total state-locked across 8 tracked contracts: **282,733 NEAR** at 0.01 NEAR/KB (storage_amount_per_byte 10,000,000,000,000,000,000 yocto). Measured lock growth 337.2 NEAR/day over intents.near, aurora (archival available).

### 9.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)
| Regime | Inflation | Nominal APR | Real APR | Buyback accrual | Real APR + accrual | Non-staker real |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| status quo (cap flat) | 2.50% | 5.63% | 3.13% | 0.474% | 3.61% | -2.03% |
| SVRN glidepath | 1.60% | 3.61% | 2.01% | 0.474% | 2.48% | -1.13% |

Live: 340 validators, 581,994,836 NEAR staked = 44.38% of supply.

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
| 10,000,000 | 20 KB | 2,000,000 NEAR | 22.3 | 0.153% |
| 10,000,000 | 50 KB | 5,000,000 NEAR | 55.8 | 0.381% |


### 9.8 Chain Signatures (v1.signer): a second usage engine?
Sampled from 12 NearBlocks windows (1,200 receipts, 362 sign requests) over the trailing 30 days, v1.signer handled 15,730 sign requests/day over 7 days (SE 2,784) and 11,523/day over 30 days (SE 1,320). Over the 8 windows taken at 00:00 UTC (same time of day), the ln-rate trend is +207% per 30 days (t = 3.19; growing). Callers are concentrated: omni.bridge.near 40%, fast-auth.near 25%, btc-connector.bridge.near 13% of sampled requests; accounts under bridge.near send 61%, so much of this usage is bridging that overlaps Intents' cross-chain flow. A request attaches 1 yoctoNEAR, so the signer earns no fee; requesters pay gas, 0.0026 NEAR per request across sign, respond and callback receipts, 29.4 NEAR/day ($103.85/day), 100% of it burnt (live burnt_gas_reward 0% to the contract), 3.0% of the network gas burn and 0.03% of measured daily issuance (part of the L1 gas burn sink above, not an addition to it). The contract's storage lock is 11.6 NEAR. NearBlocks counts 26,401,762 cumulative v1.signer receipts; the rates are sample estimates, not exact counts.

## 10. Sum-of-the-parts valuation and peer comparables

### 10.1 Engines (percentiles over paths, USD; discounted to today)
| Engine | P10 | P25 | P50 | P75 | P90 | Assumption-heavy |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| clearinghouse | $32.4M | $81.6M | $234.7M | $707.4M | $1.93B | no |
| confidential | $20.4M | $54.0M | $170.6M | $573.6M | $1.71B | yes |
| monetary | $1.2M | $3.0M | $10.9M | $44.7M | $169.9M | yes |

| Total | P10 | P25 | P50 | P75 | P90 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| FDV (all engines) | $134.7M | $279.7M | $689.1M | $1.76B | $4.17B |
| FDV ex-monetary | $127.3M | $265.4M | $653.9M | $1.65B | $3.92B |
| Implied price / NEAR | $0.10 | $0.20 | $0.50 | $1.29 | $3.05 |

Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse $596.3M (87%) + confidential $68.9M (10%) + monetary $24.0M (3%) = $689.2M.

- PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor.
- Same construction on confidential volume at the assumed confidential take; terminal multiple x confidential_multiple_haircut because nearstats flags confidential TVL as unverified. Starting confidential share 11.5% is an on-chain estimate from Confidential Intents Treasury boundary flows (intents_forensics.volume.confidential_share_estimate), not nearstats' rejected split.
- PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.

### 10.2 Calibration (what the engines were fed)
| Parameter | Value | Source / basis |
| :--- | :--- | :--- |
| Public take t=0 (gross) | 14.91 bps | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d |
| Blended gross take / net take | 15.50 bps / 4.83 bps | DefiLlama near-intents fees / volume; net = gross x alpha |
| Capture ratio alpha | 31.18% | measured:defillama near-intents dailyHoldersRevenue / fees |
| Confidential take t=0 | 20 bps | assumption: registry confidential_take_bps (1Click confidential quotes need partner authentication) |
| Public take floor | 2.25 bps | derived; cross-VM headroom +2.25 bps, competitor ceiling 3.00 bps |
| Compression lambda (public / confidential) | 0.030 / 0.010 per month | geometric reversion to the floor |
| Volume growth (public / confidential, monthly) | 4.39% / 9.24% | confidential share 11.5% -> 40% target (start share ESTIMATED ON-CHAIN from Confidential Intents Treasury boundary flows) |
| Sigma: price (annual) / volume (monthly) | 1.025 / 0.338 | measured: monthly log-return sigma of 30-day volume aggregates; confidential sigma x 1.00 |
| Terminal multiple (FDV / annual holder revenue) | 60.0x (raw 2,512.3x) | source derived: peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; clipped to registry guardrails |
| Discount rate | 25% | assumption |
| Supply at horizon (glidepath) | 1,368,562,523 NEAR | fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory) |
| Current FDV | $4.63B | spot price x on-chain total_supply at the snapshot block; CoinGecko FDV via nearstats $4.63B (0.02% gap, struck at a different instant; cross-check only) |
| GBM convention | mean-matching (Ito) | mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM uses the same convention (zero drift => E[P_t] = P_0) |
| Terminal public volume, month H | mean $517.3M/day; median $66.5M/day | start $110.1M/day; MC sample mean $461.3M, median $64.4M; the labeled YoY growth is the growth of the MEAN path |


### 10.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)
| Protocol | Fees 30d | Revenue 30d | FDV | FDV/fees | FDV/revenue | Revenue methodology (live text) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| SOL (solana) | $16.9M | $1.7M | $52.84B | 257.1x | 2,512.3x | Transaction base fees paid by users |
| ETH (ethereum) | $20.0M | $6.2M | $249.99B | 1,027.9x | 3,296.0x | Amount of ETH burned — base fees plus blob fees (both are permanently burned, accruing to no proposer) |
| HYPE (hyperliquid) | $89.6M | $68.8M | $67.97B | 62.4x | 81.2x | Parent aggregates child protocols. Hyperliquid Perps: 99% of fees go to Assistance Fund for buying HYPE tokens |
| NEAR (near) | $134,174 | $93,923 | $4.61B | 2,826.9x | 4,038.4x | 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract developers |
| NEAR (near-intents) | $5.8M | $1.8M | $4.61B | 65.6x | 210.4x | NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.ne |
| NEAR (near_combined) | $5.9M | $1.9M | $4.61B | 64.1x | 200.0x | near: 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract deve |

- Median ex-NEAR FDV / annualized revenue 2,512.3x (n = 3); FDV / annualized fees 257.1x (n = 3). annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)
- `revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live methodology text is carried in the table so the multiple is read with its definition.

### 10.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take (SVRN glidepath; * = net-deflationary)
| Net take \ Volume/day | $100.0M | $250.0M | $500.0M | $1.00B | $1.50B |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2 bps | $274.4M | $623.1M | $1.20B | $2.37B | $3.53B* |
| 6 bps | $739.4M | $1.79B | $3.53B* | $7.02B* | $10.50B* |
| 10 bps | $1.20B | $2.95B* | $5.85B* | $11.67B* | $17.48B* |
| 14 bps | $1.67B | $4.11B* | $8.18B* | $16.32B* | $24.45B* |
| 18 bps | $2.13B | $5.27B* | $10.50B* | $20.97B* | $31.43B* |

Current FDV $4.63B; confidential share used in the split 11.5%. Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).

### 10.5 Out-of-sample backtest of the volume engine
At each of 20 monthly origins from 2025-03-21 to 2026-10-12 the volume GBM was re-calibrated on data up to the origin only (trailing 30-day volume, sigma from the trailing 365 days, drift = public_volume_growth_yoy 68%) and its P10-P90 band for 30-day volume was compared with what happened (defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json), 2024-12-10 to 2026-11-11). The test of 80% coverage fails at 1m, 3m, 6m (exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10). At 1 month the median realized volume is 1.37x the forecast median: the model under-predicts. Split at the middle origin (2026-01-15), coverage before: 1m 30% (n = 10), 3m 20% (n = 10), 6m 30% (n = 10); from it: 1m 90% (n = 10), 3m 100% (n = 7), 6m 100% (n = 4). 22 of the 23 misses come from origins before the split; 23 of 23 are realized volume above P90. With the drift replaced by the trailing mean log return (no registry input) coverage is 1m 60%, 3m 41%, 6m 14%. Not backtested: fee take rate (public and confidential) and its compression toward the floor; holder capture ratio alpha; confidential share of volume and its drift to the target share; terminal FDV/revenue multiple and discount rate; NEAR price and supply paths. 3- and 6-month forecasts from monthly origins overlap, so their errors are correlated and the binomial interval overstates the precision.

| Horizon | n | P10-P90 coverage [90% Wilson] | Binomial p vs 80% | Below P10 / above P90 | Median realized / P50 | PIT histogram (5 bins) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 1 month | 20 | 60% [42%-76%] | 0.04 | 0 / 8 | 1.37x | 1 4 2 2 11 |
| 3 months | 17 | 53% [34%-71%] | 0.01 | 0 / 8 | 1.86x | 0 2 2 4 9 |
| 6 months | 14 | 50% [30%-70%] | 0.01 | 0 / 7 | 3.89x | 1 0 3 1 9 |


## 11. Bear case and early-warning triggers

Value basis: deterministic at median inputs; not a Monte Carlo percentile. Base deterministic FDV (median inputs) $2.11B, implied price $1.54; the Monte Carlo P50 of section 10 is a different statistic and is not what the drawdowns below are measured against. drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed

| Scenario | Deterministic FDV (median inputs) | FDV drawdown | Implied price | Price drawdown | Flow crossover |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fee_race_to_zero | $360.5M | -82.9% | $0.26 | -82.9% | none within horizon |
| governance_stalemate | $2.11B | +0.0% | $1.52 | -1.8% | none within horizon |
| post_incentive_decay | $849.2M | -59.8% | $0.62 | -59.8% | none within horizon |
| solver_cartelization | $1.37B | -35.0% | $1.00 | -35.0% | month 36 |
| combined worst | $214.5M | -89.8% | $0.15 | -90.0% | none within horizon |


### 11.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)
| Scenario | Metric | Now | Trigger | Status | Monitor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| fee_race_to_zero | net_take_bps_30d | 4.83 bps | < 3.00 bps | not breached | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue (sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days). |
| governance_stalemate | max_inflation_rate | 2.50% | > 1.60% | **BREACHED** | https://free.rpc.fastnear.com (EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)). Note: breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted |
| post_incentive_decay | volume_30d_vs_record_30d | -22.8% | <= -40.0% | not breached | https://nearstats.org/api/near/summary (intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1). |
| solver_cartelization | hhi_solver | 4,324 | > 3,500 | **BREACHED** | https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50 (HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)); secondary headroom_cross_vm_bps +2.25 bps < 0 bps (not breached). Note: sample: 87 solver fill participations over 17,341 s; HHI_solver 4,324, bootstrap 90% CI [3,757, 4,816] (CI lower bound 3,757 > 3,500: breached); deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = 2,450 |


### 11.2 Scenario narratives
**Aggregator bypass: public take races to 1 pip.** Third-party frontends route around near.com and the public gross take collapses from 14.9 bps to 0.01 bps (the bare intents.near contract fee); confidential execution reprices from 20 bps to 5 bps. Capture ratio alpha is held at 31%, so the hit is price, not allocation. Deterministic (median-input) FDV -82.9% to $360.5M; implied price $0.26. Evidence against it: live cross-VM headroom is +2.3 bps, so a bypassing frontend must first give up that execution edge. Trigger: DefiLlama 30d net take (gross x alpha) below 3.0 bps (now 4.8 bps).

**Governance stalemate: 2.5% issuance forever.** Validators never enact the SVRN cut: max_inflation_rate stays at 2.50% for the full horizon instead of gliding to 1.60%. Protocol cash flows do not change, so FDV moves +0.0%; the damage is dilution: 24,582,937 more NEAR outstanding at the horizon and a per-token value of $1.52 (-1.8% vs base). Net-float crossover: none within horizon (base: month 31). This scenario is live today: the on-chain cap reads 2.50% and no cut has been enacted.

**Post-incentive volume decay (NEAR@3.33 unwind).** Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume $110.1M -> $44.0M (-60%), confidential $14.3M -> $4.3M (-70%) and confidential TVL x0.3 (nearstats flags that TVL unverified). Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV -59.8% to $849.2M; implied price $0.62. Current 30d volume $3.73B is 77% of the 30d record $4.84B; the trigger fires at -40%.

**Solver cartelization: HHI_solver > 3,500, 1Click loses the spread.** Two market makers take most fills (HHI_solver > 3,500) and spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM (headroom -2 bps). Keeping flow costs the same 2 bps of take (14.9 bps -> 12.9 bps) while compression runs at 0.15/month. Deterministic (median-input) FDV -35.0% to $1.37B; implied price $1.00. Live: HHI over solver fill participations 4,324 (2.3 effective solvers across 87 fill participations), bootstrap 90% CI [3,757, 4,816]; deposit-source HHI over external predecessors 2,450 (not a solver measure); cross-VM headroom +2.3 bps; trigger at HHI_solver > 3,500 or headroom < 0.

### 11.3 Falsification summary
fee_race_to_zero: public gross take at 0.01 bps and confidential at 5 bps puts the deterministic FDV at $360.5M (-82.9%); watch DefiLlama near-intents 30d net take weekly, trigger < 3.0 bps, now 4.8 bps (not breached). governance_stalemate: no SVRN cut (cap 2.50% for 36 months) leaves the deterministic FDV at $2.11B (+0.0%) but dilutes per-token value to $1.52 (-1.8%) with crossover none within horizon; watch max_inflation_rate in EXPERIMENTAL_protocol_config, trigger > 1.60%, now 2.50% (BREACHED). post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at $849.2M (-59.8%); watch nearstats 30d volume against its 30d record weekly, trigger <= -40%, now -22.8% (not breached). solver_cartelization: HHI_solver > 3,500 with cross-VM headroom at -2 bps puts the deterministic FDV at $1.37B (-35.0%); watch the execute_intents solver HHI (now 4,324) and the live quote-race headroom (now +2.3 bps) weekly (BREACHED). All four at once: deterministic FDV $214.5M (-89.8% vs base $2.11B); 2 of 4 measured triggers currently breached, and the thesis is falsified if any trigger holds for 30 consecutive days.

## 12. Evidence scorecard

| Claim | Status | Value | Source | Confidence | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB) | **VERIFIED_ON_CHAIN** | intents.near storage_usage 13,603,518,865 bytes = 136,035 NEAR locked; 282,733 NEAR across 8 tracked contracts | near_rpc/view_account:intents.near sha256 d115613cc604... @ block 224,174,242; storage_amount_per_byte from EXPERIMENTAL_protocol_config | high | growth 30,489,517 B/day = 304.9 NEAR/day over 29.9 d (archival); a 0.01 NEAR/KB lock is released if state is deleted, so it is a sink while state grows |
| Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap | **VERIFIED_ON_CHAIN** | 26,438.74 NEAR minted at epoch start 224,135,537 x 1,236.9 epochs/yr = 32,701,161 NEAR/yr (2.4935%), -0.26% vs nominal 32,786,831 | near_rpc/block:224135537 sha256 bf929c65d676... and its predecessor by prev_hash; previous epoch start 224092337 | high | second independent jump 26,224.43 NEAR; within-epoch drift -285.37 NEAR/epoch is the net gas burn |
| Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC | **VERIFIED_LIVE_API** | median headroom +2.25 bps over 3 comparable cells (dest_units); competitor ceiling 3.00 bps | oneclick/relay/lifi/across quote records 2026-11-12T06:05:10.633Z | medium | $500: +2.51 bps vs relay (rank 1/3); $50,000: +2.25 bps vs relay (rank 1/3); $250,000: +0.98 bps vs relay (rank 1/3); no 1Click capacity failures |
| Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC | **NOT_SUPPORTED** | 1Click delivers LESS BTC per USDC than the best competitor (relay): median headroom -0.09 bps over 3 cells (dest_units); the claim is not supported by this run | oneclick/lifi/relay quote records 2026-11-12T06:05:10.633Z | medium | clip-dependent: $500: -17.40 bps vs relay (rank 3/3); $50,000: -0.09 bps vs relay (rank 2/3); $250,000: +12.61 bps vs lifi (rank 1/2); LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used |
| EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative) | **VERIFIED_LIVE_API** | median headroom -1.02 bps over 3 cells (dest_units; 1Click trails) | oneclick/across/relay/lifi quote records 2026-11-12T06:05:10.633Z | medium | $500: -0.90 bps vs across (rank 3/4); $50,000: -1.02 bps vs across (rank 3/4); $250,000: -1.02 bps vs across (rank 3/4); the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins |
| Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material | **DERIVED** | deposit/caller HHI_external 2,450 [90% CI 1,500-3,550] (N_eff 4.08), ex-AI-agent 1,405; AI-agent share 45.0% (>= 10% materiality line), bridge share 35.0% | nearblocks/txns:intents.near:p1 sha256 3e95d68a8fbe... ... p8 | low | 137 unique receipts over 39 s; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources (bridge callbacks, direct callers), not solvers |
| Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers | **VERIFIED_LIVE_API** | HHI_solver 4,324 [90% CI 3,757-4,816] (N_eff 2.31) over 87 fill participations in 86 fills (1 atomic token_diff fills, 85 hub-settled legs), 6 distinct solvers; CI entirely above the 3,500 cartel threshold | nearblocks/txns:intents.near:p1 sha256 3e95d68a8fbe... ... p8 + 8 method-filtered execute_intents page(s); args.signed[].payload.message (NEP-413 signer_id) | medium | 441 execute_intents receipts decoded; settlement hub 51e8f94d77b5... (137 counterparties) routes most swaps via transfer legs; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty |
| Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume | **DERIVED** | 11.5% (band 11.5%-14.8%) estimated on-chain: Confidential Intents Treasury 24h inflow $14.7M / outflow $16.7M against 24h volume $113.1M; >= 10% materiality line | near_rpc/confidential:balances:head sha256 a59ddc39f1cf... treasury balances in intents.near (NEAR mainnet RPC) | low | nearstats' split was rejected by the plausibility guard; the share is estimated from the public treasury boundary instead. Biases: same-hour shield/unshield netting and in-shard turnover push it down, solver inventory pushes it up; 24h window |
| Confidential TVL backs the dark-pool engine (Engine 2) | **VERIFIED_ON_CHAIN** | $136.6M TVL read on-chain from the Confidential Intents treasury in intents.near (NEAR-reported via nearstats: $140.8M) | near_rpc/confidential:balances:head sha256 a59ddc39f1cf... intents.near mt_batch_balance_of (treasury) | high | Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut (0.7); the confidential take (20 bps) is an assumption |
| Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink | **DERIVED** | alpha 31.2%; gross take 15.50 bps, net take 4.83 bps; buyback sink 17,025 NEAR/day = 20.5% coverage incl. burn and lock | defillama/fees:near-intents:dailyHoldersRevenue sha256 cc3a4d7ed699... / defillama/fees:near-intents sha256 66689499af27... | medium | DefiLlama revenue methodology: NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.near.org and the on-chain buyback). Split by destination wallet into front-end affiliate revenue and Other. Transfers between those wallets are excluded. |
| Chain Signatures (v1.signer) is a growing second usage engine beyond Intents | **DERIVED** | 15,730 sign requests/day (7d) vs 11,523/day (30d); ln-trend +207% per 30 d [90% CI +72% to +447%], t = 3.19; top caller omni.bridge.near 40% of 362 sampled sign receipts, *.bridge.near callers 61%; gas 0.0026 NEAR per request | nearblocks/txns:v1.signer:before_block:* (12 windows of 100 receipts, 1,200 receipts) + nearblocks/txns:v1.signer:count | medium | sampled estimate: each window covers minutes; bridge callers serve cross-chain transfers that overlap Intents settlement, so the engine is not fully independent of Intents; storage lock 11.6 NEAR is small. sign() attaches 1 yoctoNEAR (median of sampled requests), so the contract takes no material per-request fee; the requester's cost is gas. |
| The volume engine (GBM with measured sigma) is calibrated out of sample: P10-P90 covers ~80% of realized 30-day volume | **NOT_SUPPORTED** | 1m 12/20 = 60% inside P10-P90 (binomial p 0.04); 3m 9/17 = 53% inside P10-P90 (binomial p 0.01); 6m 7/14 = 50% inside P10-P90 (binomial p 0.01); 1m median realized / forecast median 1.37x (under-prediction); 1m coverage 30% for origins before 2026-01-15, 90% from it; 20 monthly origins 2025-03-21 to 2026-10-12 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 2fc4816f19c4... | low | Tests the volume distribution only; the take rate, holder capture, confidential share, multiple and discount rate are not backtested. 3m and 6m forecasts from monthly origins overlap, so their effective sample is smaller than n. |


## 13. Assumptions register

### 13.1 Labeled assumptions (slider inputs; never presented as measured)
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


### 13.2 Measured and derived model inputs (point values with their source)
| Key | Value | Unit | Source | Basis |
| :--- | :--- | :--- | :--- | :--- |
| total_supply_near | 1,311,473,244 | NEAR | measured | RPC block header total_supply at height 224174242 |
| current_max_inflation_rate | 0.025 | ratio_annual | measured | RPC EXPERIMENTAL_protocol_config.max_inflation_rate |
| treasury_share | 0 | ratio | measured | RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this) |
| staked_supply_ratio | 0.443772 | ratio | measured | RPC validators current stake / total_supply (340 validators) |
| annual_issuance_near | 32,701,161 | NEAR_per_year | measured | minted_per_epoch 26438.74386188156 NEAR x epochs_per_year 1236.865151874273 from total_supply jumps at epoch starts 224092337 -> 224135537 |
| issuance_realization_factor | 0.997387 | ratio | measured | measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path |
| near_price_usd | 3.53 | USD | measured | nearstats price.currentUsd via intents_forensics.price.current_usd |
| daily_volume_usd | 124,378,500 | USD_per_day | measured | intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window (aligned daily charts, 30 complete UTC day |
| gross_take_bps | 15.4954 | bps | measured | intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window (aligned daily charts, 30 complete UTC |
| capture_ratio | 0.311834 | ratio | measured | intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window (aligned daily charts, 30 complete  |
| gas_burn_near_per_day | 966.368 | NEAR_per_day | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| state_lock_growth_near_per_day | 337.2447 | NEAR_per_day | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| public_volume_growth_yoy | 0.675075 | ratio_yoy | measured | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-12 to 2026-11-11 (365 days, DefiLlama dexs/near-intents): +67.5%/yr, 90% CI +8.6% to +158.5% (Newey |
| competitive_fee_ceiling_bps | 3.004 | bps | derived | median over cross-VM cells of the best competitor's friction (per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding); the lowest-fric |
| tau_floor_bps | 2.251 | bps | derived | max(0.5 bps, min(live public take, live cross-VM headroom)) from the execution benchmark (headroom_by_archetype_bps.cross_vm = 2.25 bps). |
| tau_pub_start_bps | 14.9092 | bps | derived | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d; blended live gross take 15.50 bps (DefiLlama daily fees / daily volume summed over the a |
| alpha_capture | 0.311834 | ratio | measured | measured:defillama near-intents dailyHoldersRevenue / fees |
| terminal_multiple | 60 | x_fdv_to_revenue | derived | peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; raw 2512.3x. |
| confidential_share_start | 0.115155 | ratio | derived | on-chain estimate: Confidential Intents Treasury 24h inflow / (24h volume + inflow) = 11.5% (band 11.5%-14.8%); nearstats split implausible. Estimated from the  |
| sigma_price_annual | 1.0254 | ratio_annual | measured | nearstats:price-history: 1y daily closes, log-return sigma x sqrt(365). |
| sigma_volume_monthly | 0.337579 | ratio_monthly | measured | measured: monthly log-return sigma of 30-day volume aggregates |


## 14. Reproduction

```bash
# from the repo root; no API keys; ~20-60 s wall clock
make reproduce          # == cd quant && uv run python -m valuo.reproduce   (canonical artifacts/)
make test               # offline unit tests + invariant checks against artifacts/
# this snapshot was produced by: cd quant && uv run python -m valuo.reproduce
# faster smoke (no quote race, 2,000 paths) writes to artifacts/dev/, never over the canonical files:
make reproduce-fast     # == cd quant && uv run python -m valuo.reproduce --skip-bench --paths 2000
# verify the artifact bytes against the manifest:
shasum -a 256 artifacts/latest_snapshot.json   # must equal manifest.json: snapshot_sha256
```

Determinism: `numpy.random.default_rng(20261114)` draws every shock up front; re-running the Monte Carlo on this snapshot's inputs reproduces every percentile bit-for-bit (tests/test_invariants.py::test_monte_carlo_determinism). Live inputs change block to block, so a fresh run moves the numbers; the memo always states its block and timestamp.

## 15. Data provenance

140 raw exchanges (135 ok, 5 failed), 6,710,495 bytes hashed; raw bodies persisted under `artifacts/raw` and listed with SHA-256 in `manifest.json`.

| Source | Records |
| :--- | ---: |
| across | 6 |
| coingecko | 1 |
| defillama | 15 |
| lifi | 9 |
| near_rpc | 41 |
| near_rpc_archival | 14 |
| nearblocks | 32 |
| nearstats | 2 |
| oneclick | 11 |
| relay | 9 |


Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):
| Source | Name | HTTP | Error |
| :--- | :--- | :--- | :--- |
| across | quote:eth_usdc_sol_usdc:50000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:500 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:250000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| relay | quote:eth_usdc_btc:250000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $152, |
| nearblocks | txns:v1.signer:before_block:223266836 |  | ReadTimeout:  |


### 15.1 Methodology warnings recorded during the run (13)
- execution_bench: eth_usdc_sol_usdc $500: venue USD oracles disagree with the cell's common price by more than the +2.51 bps headroom (1click +0.0 bps, relay +2.6 bps, lifi +17.9 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the +2.25 bps headroom (1click +0.0 bps, relay +2.6 bps, lifi +17.9 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +2.6 bps, lifi +17.9 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $500: venue USD oracles disagree with the cell's common price by more than the -17.40 bps headroom (1click +0.0 bps, relay -18.7 bps, lifi +0.3 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $50,000: venue USD oracles disagree with the cell's common price by more than the -0.09 bps headroom (1click +0.0 bps, relay -18.7 bps, lifi +0.3 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $500: venue USD oracles disagree with the cell's common price by more than the -0.90 bps headroom (1click +0.0 bps, relay +2.6 bps, lifi -5.8 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click -0.0 bps, relay +2.6 bps, lifi -5.8 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +2.6 bps, lifi -5.8 bps); headroom is measured on destination units, not USD legs
- intents_forensics: confidential split: nearstats reports confidential 30d $0.00 (0.0000%), rejected (tvl_without_volume: confidential TVL $136.55M but all-time confidential volume $0.09 of $38.38B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'). Share ESTIMATED ON-CHAIN from the Confidential Intents Treasury: 11.5% (band 11.5%-14.8%; 24h inflow $14.72M, outflow $16.72M, volume $113.12M), replacing the registry assumption 40%
- intents_forensics: nearblocks: 63 duplicate receipt(s) seen on overlapping pages were counted once (id-based cursor vs time-ordered rows); unique receipts sampled = 137
- chain_signatures: retry pass recovered 1 of 1 window(s) after a 45 s cool-down
- sotp: confidential share 11.5% is an ON-CHAIN ESTIMATE from Confidential Intents Treasury boundary flows (band 11.5%-14.8%), not nearstats' split (rejected as implausible); 24h window, biases listed in intents_forensics.volume.confidential_share_estimate
- sotp: peer median FDV/revenue 2512.3x clipped to 60.0x (guardrails [8, 60])
