# Valuo IC Memo: NEAR at block 223,672,128

*NEAR Intents clearinghouse + NEAR L1. Generated 2026-11-08T21:24:23.730Z UTC from live mainnet RPC and key-free public APIs; every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section 12.*

| Provenance | Value |
| :--- | :--- |
| NEAR block | 223,672,128 (`6WamcNDEjyxTmBUVkwK8Bsu1DCQeoSysL1vFb4CmpZjN`), 2026-11-08T21:24:21.779Z |
| RPC endpoint | https://free.rpc.fastnear.com |
| Snapshot generated | 2026-11-08T21:24:23.730Z UTC, runtime 217.1 s, valuo 0.1.0, schema 1.0.0 |
| Snapshot SHA-256 | `7110830afd1354558b334dba4687e9d841e6520ada7fc518155510ed18951c00` |
| Monte Carlo | seed 20261114, 10,000 paths, 36 months |
| Raw records | 91 HTTP/RPC exchanges hashed, 9 non-2xx/failed (every one listed in manifest.json) |


## 1. Executive summary

**Model value vs market value.** Market FDV is $4.76B (spot price x on-chain total supply at block 223,672,128). The model's expected-path FDV is $817.9M and its 10,000-path Monte Carlo gives P10 / P50 / P90 = $57.2M / $262.9M / $1.65B. The market sits above the expected path (5.8x it) and at 18.1x the Monte Carlo P50. The model capitalises NEAR Intents holder revenue, L1 gas burn and state-lock flow over 36 months at a 25% discount rate and a 60x terminal multiple; the question below is which input would have to change for it to reach the market price, and whether the evidence allows that.

**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in section 2).

| Input | Base | Required for market FDV | Evidence | Inside evidence |
| :--- | ---: | ---: | ---: | :--- |
| Expected annual public-volume growth (3-year path) | 30.0% | 160.9% | 19.5% | no |
| Starting gross public take rate | 12.10 bps | 178.34 bps | 3.00 bps | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 372x | 2,265x | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $1.56B) | 10.0% | n/a |
| Confidential share of volume at month 36 | 40.0% | 91.3% | 40.0% (ASSUMED, not measured) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $27.8M/yr | $175.3M/yr | $23.6M/yr | no |


**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple (372x needed; live peer FDV/revenue HYPE 89x, SOL 2,265x, ETH 3,579x, median 2,265x over n = 3 peers). No discount rate closes the gap: even at 0% the model reaches $1.56B against the market's $4.76B, because the terminal multiple is capped at 60x. The gap is a multiple question, not a discount-rate question. The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on Intents cash flow at the model's 60x terminal cap. On cash flow alone (multiple held at the model's 60x), the market price requires 161%/yr expected public-volume growth for 3 years (trailing 12 months: +19.5%), or a 178 bps starting public take (today 12.10 bps, live competitive ceiling 3.00 bps), or $175.3M of annualised holder revenue in year 3 (7.4x today's $23.6M); none of these is inside its measured evidence. Whether NEAR keeps an L1 multiple is the investment question; this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token.

**What you have to believe** (section 3). The three inputs that move FDV most are Expected annual public-volume growth (-20.0% to 150.0%: $254.7M-$4.26B); Terminal FDV / holder-revenue multiple (8.00x to 150x: $161.6M-$1.95B); Public take compression speed (per month) (0.0%/month to 15.0%/month: $289.6M-$1.34B). Together they carry 91% of the swing-squared variance proxy. 0 of 17 single-input ranges reach the market FDV.

**Relative value** (section 4). NEAR trades at 64x annualised fees against a peer median of 255x (rank 1 of 4, lowest multiple first; below every peer); at peer FDV/fees multiples NEAR's fees map to $12.03B-$50.72B (cross-check, not a fair value; n = 3 peers); holder revenue covers 21% of the $118.9M/yr security budget.

**Evidence quality flags.**

- Confidential share: NOT MEASURED this run. nearstats reported 0.0000% of 30d volume as confidential, which its own payload contradicts (tvl_without_volume: confidential TVL $143.16M but all-time confidential volume $0.00 of $37.86B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok); the model uses the registry assumption confidential_share = 40% (range 15%-60%), so Engine 2 ($422.0M of the $817.9M expected-path FDV) values an assumed volume.
- Deposit/caller HHI 3,555 (bootstrap 90% CI 2,383-5,000) over 32 external receipts spanning 73 s; a point sample, not a market-share estimate.
- Solver HHI 6,256 (bootstrap 90% CI 5,037-7,537) over 77 fill participations spanning 17,567 s. Cartel trigger: BREACHED (sample: 77 solver fill participations over 17,567 s).
- Bear case: 2 of 4 graded early-warning triggers breached. Combined-worst deterministic FDV $105.9M (-87%).

## 2. What the market is pricing (reverse valuation)

Basis: deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base. Solver: scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12. Market FDV $4.76B; expected-path model FDV $817.9M (gap 5.8x); Monte Carlo P50 $262.9M (gap 18.1x). Every required value is the expected-path requirement; the P50 sits lower by lognormal convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).

| Input | Base | Required for market FDV | Evidence | Evidence basis | Inside evidence |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Expected annual public-volume growth (3-year path) | 30.0% | 160.9% | 19.5% | trailing-12-month NEAR Intents 30-day volume growth | no |
| Starting gross public take rate | 12.10 bps | 178.34 bps | 3.00 bps | live competitive fee ceiling (median best-competitor friction, cross-VM cells) | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 372x | 2,265x | peer median FDV / annualised revenue ex-NEAR (unclipped) | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $1.56B) | 10.0% | low end of the registry discount-rate range (10%-40%) | n/a |
| Confidential share of volume at month 36 | 40.0% | 91.3% | 40.0% (ASSUMED, not measured) | ASSUMED confidential share (registry confidential_share; the nearstats split was not measured this run) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $27.8M/yr | $175.3M/yr | $23.6M/yr | current annualised holder revenue (30-day window x 365.25/30) | no |

- Justifying $4.76B needs 161% expected annual public-volume growth for 3 years (base 30%); trailing-12-month Intents volume growth was 20%.
- Justifying $4.76B needs a starting gross public take of 178.3 bps (decaying to the 0.98 bps floor at 3%/month) versus 12.10 bps today; the live competitive fee ceiling is 3.00 bps.
- Justifying $4.76B needs a 372x terminal FDV/holder-revenue multiple; the live peer median is 2,265x (HYPE 89x, SOL 2,265x, ETH 3,579x) and the model caps it at 60x.
- Even a 0% discount rate gives $1.56B, short of $4.76B: the gap is not a discount-rate question.
- Justifying $4.76B needs the confidential share to reach 91% by month 36; the share is NOT MEASURED this run (the model assumes 40%, registry confidential_share).
- Justifying $4.76B at the 60x base multiple needs $175M of annualised holder revenue in year 3 (6.3x the base path's $28M), versus $24M today (95%/yr compounded).

Headline: Market FDV $4.76B is 5.8x the model's expected-path FDV $818M; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 372x (evidence 2,265x).

Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the joint requirement is smaller than any single one; section 3 shows which inputs carry the variance.

## 3. What you have to believe (one-at-a-time sensitivity)

Basis: deterministic_sotp expected path; one input at its low / high, all others at the snapshot base. Base expected-path FDV $817.9M against a $4.76B market FDV. Variance share: swing^2 / sum(swing^2): first-order share for independent inputs, an approximation. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).

| # | Input | Source | Range | Base | FDV at low | FDV at high | Swing | Variance share |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Expected annual public-volume growth | assumption | -20.0% - 150.0% | 30.0% | $254.7M | $4.26B | $4.01B | 72.1% |
| 2 | Terminal FDV / holder-revenue multiple | derived | 8.00x - 150x | 60x | $161.6M | $1.95B | $1.79B | 14.4% |
| 3 | Public take compression speed (per month) | assumption | 0.0%/month - 15.0%/month | 3.0%/month | $1.34B | $289.6M | $1.06B | 5.0% |
| 4 | Confidential share at month 36 | assumption | 5.0% - 60.0% | 40.0% | $454.1M | $1.22B | $770.6M | 2.7% |
| 5 | Annual discount rate | assumption | 10.0% - 40.0% | 25.0% | $1.18B | $590.8M | $593.8M | 1.6% |
| 6 | Starting 30-day Intents volume (public + confidential) | measured | 0.71x - 1.42x | 1.00x | $598.9M | $1.13B | $529.6M | 1.3% |
| 7 | Holder capture (revenue / gross fees) | measured | 12.9% - 32.7% | 32.7% | $368.5M | $817.9M | $449.5M | 0.9% |
| 8 | NEAR price drift (gas-burn and state-lock USD value) | assumption | -50.0% - 100.0% | 0.0% | $757.4M | $1.18B | $422.5M | 0.8% |
| 9 | Confidential multiple haircut | assumption | 30.0% - 100.0% | 70.0% | $595.7M | $984.6M | $388.9M | 0.7% |
| 10 | Confidential compression divisor | assumption | 1.00x - 10x | 3.00x | $640.5M | $909.9M | $269.4M | 0.3% |
| 11 | Public take hard floor | assumption | 0.00 bps - 5.00 bps | 0.50 bps | $817.9M | $987.6M | $169.6M | 0.1% |
| 12 | Blended gross take (public take re-reconciled) | measured | 13.04 bps - 16.95 bps | 15.26 bps | $729.9M | $884.7M | $154.8M | 0.1% |
| 13 | Confidential gross take (public take re-reconciled to live fees) | assumption | 10.00 bps - 30.00 bps | 20.00 bps | $768.6M | $867.3M | $98.8M | 0.0% |
| 14 | NEAR spot price (USD value of gas burn and state lock) | measured | $2.69 - $4.89 | $3.63 | $798.7M | $843.9M | $45.2M | 0.0% |
| 15 | L1 gas burn (NEAR/day) | measured | 655 NEAR/day - 1,091 NEAR/day | 873 NEAR/day | $799.7M | $836.2M | $36.6M | 0.0% |
| 16 | Cross-VM headroom (sets the public take floor) | measured | 0.74 bps - 1.23 bps | 0.98 bps | $807.6M | $828.3M | $20.7M | 0.0% |
| 17 | State-lock growth (NEAR/day) | measured | 246 NEAR/day - 409 NEAR/day | 328 NEAR/day | $817.6M | $818.3M | $692,350 | 0.0% |

Top three inputs carry 91% of the variance proxy. 0 of 17 single-input ranges reach the market FDV at either end.

Headline: public_volume_growth_yoy, terminal_multiple, fee_compression_lambda_monthly carry 91% of the swing-squared variance proxy; public_volume_growth_yoy alone moves FDV from $255M to $4.26B across its range, and 0 of 17 single-input ranges reach the $4.76B market FDV.

Excluded (move issuance and implied price, not FDV): svrn_target_inflation (issuance path only: moves supply at horizon and implied price, not FDV); svrn_glidepath_months (issuance path only: moves supply at horizon and implied price, not FDV).

## 4. Relative value: peer cash-flow multiples and the security budget

Basis: live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR.

### 4.1 NEAR cash-flow coverage against the peer set
| Metric | NEAR | Peer median | Peer P25 - P75 | NEAR rank | Position |
| :--- | ---: | ---: | ---: | ---: | :--- |
| FDV / annualised fees (30-day run-rate) | 64x | 255x | 162x - 684x | 1 of 4 | below every peer |
| FDV / annualised revenue (30-day run-rate) | 189x | 2,265x | 1,177x - 2,922x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day fees | 86x | 244x | 163x - 891x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day revenue | 471x | 2,217x | 1,162x - 3,933x | 2 of 4 | inside the peer range |

| Protocol | FDV | Fees (ann.) | Revenue (ann.) | FDV/fees | FDV/revenue | FDV/fees 1y | FDV/revenue 1y | Revenue/fees |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SOL (solana) | $56.73B | $222.2M | $25.0M | 255x | 2,265x | 244x | 2,217x | 11% |
| ETH (ethereum) | $271.89B | $244.4M | $76.0M | 1,112x | 3,579x | 1,538x | 5,649x | 31% |
| HYPE (hyperliquid) | $72.46B | $1.05B | $813.2M | 69x | 89x | 81x | 107x | 77% |
| NEAR (near_combined) | $4.72B | $74.2M | $25.1M | 64x | 189x | 86x | 471x | 34% |
| NEAR (near) | $4.72B | $2.1M | $1.5M | 2,279x | 3,255x | 3,989x | 5,694x | 70% |
| NEAR (near-intents) | $4.72B | $72.1M | $23.6M | 66x | 200x | 88x | 513x | 33% |

The model's terminal multiple is 60x; 0 of 3 peers trade at or below it on FDV/revenue.

### 4.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)
| Cash flow | NEAR (ann.) | at peer P25 | at peer median | at peer P75 | Peers | Basis |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| fees | $74.2M | $12.03B | $18.93B | $50.72B | 3 | comps.near_combined.annualized_fees_usd x peer FDV / annualised fees (30-day run-rate) |
| revenue | $25.1M | $29.49B | $56.76B | $73.22B | 3 | comps.near_combined.annualized_revenue_usd x peer FDV / annualised revenue (30-day run-rate) |

relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution; market FDV $4.76B.

### 4.3 Staking and security budget
- Security budget: 32,748,205 NEAR/yr of issuance (2.50%) x $3.63 = $118.9M/yr (2.52% of FDV).
- Against it: $74.2M/yr of fees (62% of the budget) and $25.1M/yr of holder revenue (21%); net dilution $93.8M/yr.
- Staked 44.4% of supply; nominal staking APR 5.64%. Basis: security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate.

### 4.4 Findings
- NEAR trades at 64x annualised fees versus a peer median of 255x (rank 1 of 4, lowest first; below every peer); on revenue it is 189x versus 2,265x (inside the peer range).
- 0 of 3 peers trade at or below the model's 60x terminal FDV/revenue multiple; NEAR itself trades at 189x.
- At the peer FDV/fees distribution, NEAR's $74M of annualised fees maps to $12.03B-$50.72B (median $18.93B, n = 3) against a $4.76B market FDV; a relative-value cross-check, not a fair value.
- NEAR issues $119M a year to validators and delegators (2.5% of FDV) against $74M of annualised fees and $25M of holder revenue (gas burn + Intents buyback): revenue covers 21% of the security budget.
- At 2.5% inflation stakers earn 5.64% nominal and 3.63% real including buybacks; non-stakers lose 2.00% a year to dilution net of buybacks.

Caveat: Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples compare different cash-flow definitions; with n = 3 peers the median is a reference point, not a distribution.

## 5. Model valuation detail

**Base case.** 10,000-path SOTP (seed 20261114): P10 / P50 / P90 FDV = $57.2M / **$262.9M** / $1.65B; implied price $0.04 / **$0.19** / $1.21 per NEAR against spot $3.63. The P50 sits 94.5% below the current FDV of $4.76B. The deterministic SOTP at the labeled inputs (the expected-volume path) is $817.9M: engines $321.4M clearinghouse + $422.0M confidential + $74.5M monetary; the Monte Carlo mean is $786.3M. Ex-monetary P50: $244.0M.

**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled +30% YoY volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of 0.349 the MEDIAN simulated path ends month 36 at 11.2% of the expected path ($19.0M/day vs $170.6M/day), which is what pulls the P50 FDV below the mean. The dispersion is measured from 11 monthly volume log-returns (sigma excluding the three oldest, incentive-era windows: 0.293); a thin sample, reported as such.

**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation; section 2 solves which single input would: Market FDV $4.76B is 5.8x the model's expected-path FDV $818M; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 372x (evidence 2,265x). The P90 ($1.65B) comes from volume paths, not from take-rate expansion (the public take only compresses in this model).

**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** 6 bps net take needs >= $1.00B/day; 10 bps net take needs >= $500.0M/day; 14 bps net take needs >= $500.0M/day; 18 bps net take needs >= $250.0M/day. Live run-rate: $129.4M/day at 5.00 bps net (15.26 bps gross x capture 32.7%).

**Net-float crossover.** Today sinks cover 21.2% of measured issuance (19,017 NEAR/day vs 89,660 NEAR/day). status quo (cap flat): deterministic flow crossover none within horizon at run-rate volume, none within horizon with the +30% YoY growth assumption; Monte Carlo P(crossover within 36m) = 48.6%, P(deflationary at horizon) = 27.4%; breakeven volume V* = $642.6M/day (5.0x today). SVRN glidepath: deterministic flow crossover none within horizon at run-rate volume, none within horizon with the +30% YoY growth assumption; Monte Carlo P(crossover within 36m) = 56.7%, P(deflationary at horizon) = 34.0%; breakeven volume V* = $408.1M/day (3.2x today). The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price outruns issuance); the deterministic path (the expected-volume path) is the one to quote.

**Falsification.** Four stress scenarios (section 10) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo percentile) at $105.9M (-87% vs the deterministic base $817.9M); 2 of 4 measured early-warning triggers are breached in this snapshot (breached: governance_stalemate (max_inflation_rate now 2.50% vs > 1.60%); solver_cartelization (hhi_solver now 6,256 vs > 3,500)). The on-chain inflation cap reads 2.50%; the SVRN cut is a proposal, not protocol state.

## 6. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)

Executable quotes fetched 2026-11-08T21:24:31.888Z UTC (24 ok of 36; 1Click token universe 216 assets on 39 chains). Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input (headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price (`price_basis`: oneclick_token_list_oracle); raw-unit friction is exact for USDC -> USDC. Positive headroom means 1Click paid out more after all fees.

| Corridor | Clip | Venue | Status | Out | Friction | ETA | Route |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | 1click | ok | 499.914758 | 1.70 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $500 | relay | ok | 499.829987 | 3.40 bps (raw) | 1 s | relay |
| ETH USDC -> SOL USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $500 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $50,000 | 1click | ok | 49,989.890488 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $50,000 | relay | ok | 49,984.979987 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $50,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $250,000 | 1click | ok | 249,949.492568 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $250,000 | relay | ok | 249,924.979987 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $250,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | 1click | ok | 0.006572 | 45.55 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $500 | relay | ok | 0.006581 | 31.53 bps (usd) | 170 s | relay |
| ETH USDC -> native BTC | $500 | lifi | error: Rate limit exceeded, retry in 1 hour | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | 1click | ok | 0.658430 | 26.56 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $50,000 | relay | ok | 0.658804 | 20.89 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $50,000 | lifi | error: Rate limit exceeded, retry in 1 hour | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | 1click | ok | 3.291752 | 27.76 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $250,000 | relay | ok | 3.290218 | 32.41 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $250,000 | lifi | error: Rate limit exceeded, retry in 1 hour | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | 1click | ok | 499.946813 | 1.06 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $500 | relay | ok | 499.927312 | 1.45 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $500 | lifi | error: Rate limit exceeded, retry in 1 hour | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | across | ok | 499.942058 | 1.16 bps (raw) | 2 s | across |
| Base USDC -> Arbitrum USDC | $50,000 | 1click | ok | 49,989.895220 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $50,000 | relay | ok | 49,994.977312 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $50,000 | lifi | error: Rate limit exceeded, retry in 1 hour | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $50,000 | across | ok | 49,994.992049 | 1.00 bps (raw) | 120 s | across |
| Base USDC -> Arbitrum USDC | $250,000 | 1click | ok | 249,949.497300 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $250,000 | relay | ok | 249,974.977312 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $250,000 | lifi | error: Rate limit exceeded, retry in 1 hour | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $250,000 | across | ok | 249,974.992058 | 1.00 bps (raw) | 900 s | across |


| Corridor | Clip | Headroom | Basis | 1Click rank | Reading |
| :--- | ---: | ---: | :--- | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | +1.70 bps | dest_units | 1/3 | 1Click delivers 1.70 bps more than relay |
| ETH USDC -> SOL USDC | $50,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> SOL USDC | $250,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> native BTC | $500 | -14.07 bps | dest_units | 2/2 | 1Click trails relay by 14.07 bps |
| ETH USDC -> native BTC | $50,000 | -5.68 bps | dest_units | 2/2 | 1Click trails relay by 5.68 bps |
| ETH USDC -> native BTC | $250,000 | +4.66 bps | dest_units | 1/2 | 1Click delivers 4.66 bps more than relay |
| Base USDC -> Arbitrum USDC | $500 | +0.10 bps | dest_units | 1/3 | 1Click delivers 0.10 bps more than across |
| Base USDC -> Arbitrum USDC | $50,000 | -1.02 bps | dest_units | 3/3 | 1Click trails across by 1.02 bps |
| Base USDC -> Arbitrum USDC | $250,000 | -1.02 bps | dest_units | 3/3 | 1Click trails across by 1.02 bps |


- cross_vm: median headroom +0.98 bps over 3 comparable cells
- native_btc: median headroom -5.68 bps over 3 comparable cells
- evm_l2: median headroom -1.02 bps over 3 comparable cells
- competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = 3; per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding): 3.00 bps. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not.

- Where 1Click loses (destination units): eth_usdc_btc at $500 trails relay by 14.07 bps; eth_usdc_btc at $50,000 trails relay by 5.68 bps; base_usdc_arb_usdc at $50,000 trails across by 1.02 bps; base_usdc_arb_usdc at $250,000 trails across by 1.02 bps.
- Oracle caveat: on eth_usdc_sol_usdc at $500, eth_usdc_sol_usdc at $50,000, eth_usdc_sol_usdc at $250,000, eth_usdc_btc at $50,000, eth_usdc_btc at $250,000, base_usdc_arb_usdc at $500, base_usdc_arb_usdc at $50,000, base_usdc_arb_usdc at $250,000 the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg comparison there would have been decided by oracles, which is why the ranking uses units.
- Structurally unsupported routes: across on eth_usdc_btc (declared), across on eth_usdc_sol_usdc (ROUTE_NOT_ENABLED).
- Collector summary: cross_vm (ETH USDC -> SOL USDC): $500: 1Click delivers 1.70 bps more than relay (rank 1/3, destination units); $50,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); unsupported: across (ROUTE_NOT_ENABLED). native_btc (ETH USDC -> native BTC): $500: 1Click trails 14.07 bps behind relay (rank 2/2, destination units); $50,000: 1Click trails 5.68 bps behind relay (rank 2/2, destination units); $250,000: 1Click delivers 4.66 bps more than relay (rank 1/2, destination units); unsupported: across (Across is EVM-only; no Bitcoin route); lifi error at $500; lifi error at $50,000; lifi error at $250,000. evm_l2 (Base USDC -> Arbitrum USDC): $500: 1Click delivers 0.10 bps more than across (rank 1/3, destination units); $50,000: 1Click trails 1.02 bps behind across (rank 3/3, destination units); $250,000: 1Click trails 1.02 bps behind across (rank 3/3, destination units); lifi error at $500; lifi error at $50,000; lifi error at $250,000.

## 7. Concentration and agents on intents.near (NearBlocks receipts)

- Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = **3,555** (bootstrap 90% CI 2,383-5,000) (N_eff = 2.81); over all predecessors 3,579; ex-AI-agent 2,041 (N_eff 4.90). These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.
- (b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = **6,256** (bootstrap 90% CI 5,037-7,537) (N_eff 1.60) across 77 fill participations in 77 fills (0 atomic token_diff fills, 77 solver-to-settlement-hub legs), 4 distinct solvers; 454 execute_intents receipts decoded, 0 unresolved; the solver sample spans 17,567 s. This is the population the solver_cartelization trigger reads; trigger status: breached.
- AI-agent share of external receipts 56.2% is a NAME-PATTERN classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. Bridge / token-contract share 31.2%; 9 unique external callers in 32 external receipts.
- Sample: 183 unique receipts over 8 NearBlocks pages, blocks 223,672,019-223,672,146, a 73 s window; lifetime receipts on intents.near 156,751,143. A window this short is a point sample, not a market-share estimate; both HHIs move by hundreds of points between runs.
- Method mix: TRANSFER 89, execute_intents 54, ft_resolve_withdraw 10, ft_on_transfer 9, ft_transfer 7, storage_deposit 3, ft_transfer_call 2, do_storage_deposit 2, near_withdraw 2, mt_on_transfer 1.

### 7.1 Deposit / caller concentration (external predecessors)
| Caller | Class | Receipts | Share | Example tx |
| :--- | :--- | ---: | ---: | :--- |
| escrow.ai.near | AI agent | 18 | 56.2% | [Abz8sFxw4mzA...](https://nearblocks.io/txns/Abz8sFxw4mzA9q6iafLNASRvTunYv4UW5XokMR7JAtdg) |
| sol.omft.near | bridge / token contract | 5 | 15.6% | [HVURwogBtzUm...](https://nearblocks.io/txns/HVURwogBtzUmCfKTF1qiMc2BvXxiUfKYvdzpBKMrgZq6) |
| wrap.near | named account | 3 | 9.4% | [BHZuvPtFSugi...](https://nearblocks.io/txns/BHZuvPtFSugiSFegLkYM6eHDghHpBfGD6aLHN1ca1C48) |
| arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near | bridge / token contract | 1 | 3.1% | [2xDAH8Hatyew...](https://nearblocks.io/txns/2xDAH8Hatyewwo9kKYRRjKCGrzrdifjfwnX4jRzyjSm9) |
| eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near | bridge / token contract | 1 | 3.1% | [E3sY9KtZK2m3...](https://nearblocks.io/txns/E3sY9KtZK2m353dJA2zEWmkhxxz3997vN8QyNdu4uePM) |
| eth-0xdac17f958d2ee523a2206206994597c13d831ec7.omft.near | bridge / token contract | 1 | 3.1% | [8nGojYa5W5SW...](https://nearblocks.io/txns/8nGojYa5W5SW45mBA6godHHDmnC4W57zTCc57BnVPUCs) |
| orderbook.fi.tg | named account | 1 | 3.1% | [57EzVKGRwTa9...](https://nearblocks.io/txns/57EzVKGRwTa9sLRpGcrG1GrtsDqXNV5vdUgMCeZ5uT8K) |
| token.sweat | bridge / token contract | 1 | 3.1% | [4fihPfsb7TfA...](https://nearblocks.io/txns/4fihPfsb7TfA6iHwqHrDhxb4g1mmGs7xZGyKDyppQYgU) |
| v2_1.omni.hot.tg | bridge / token contract | 1 | 3.1% | [6kKJjrdP2k3K...](https://nearblocks.io/txns/6kKJjrdP2k3Kk58qX4ccmJ62V9JC6gQUNJJDbhbgeZtM) |

### 7.2 Solver concentration (execute_intents signers)
| Solver account | Fill participations | Share | Example tx |
| :--- | ---: | ---: | :--- |
| solver-priv-liq.near | 60 | 77.9% | [J2BeuAxbFMKN...](https://nearblocks.io/txns/J2BeuAxbFMKNjCER3fXX9G2MM6BVHkDVe19voCYAaaXb) |
| solver-multichain-asset.near | 8 | 10.4% | [7nMaTuaYr9bZ...](https://nearblocks.io/txns/7nMaTuaYr9bZb49ygBGDn9b7iusfqNuMZFTkSePDfno1) |
| solver-multichain-asset-escrow.near | 6 | 7.8% | [6NqweqMZtoQi...](https://nearblocks.io/txns/6NqweqMZtoQi6NVJczAiKPzT4y5JP2t5tBR87SszS2Y2) |
| 6247d9c671ca6a80cf2c75e26edb8cd75ebf00fcd3c56c39107d6ca20c9cfb29 | 3 | 3.9% | [GM2t6i6ovm9F...](https://nearblocks.io/txns/GM2t6i6ovm9FgafxDNCw8eo8aqniAqNDqACvSx5BwzgC) |

Attribution: fill participation = (a) the solver side of an atomic execute_intents fill (>= 2 token_diff signers; solver = pure token_diff signer when the counterparty bundles a withdrawal, else a signer whose name matches (*solver*, *-liq*, market maker) or that the structure rule identified elsewhere in the sample, else the named account facing an implicit 1Click deposit address), or (b) a transfer intent from a solver to the settlement hub (see settlement_hub.rule); HHI over participations per solver account; transfers that are not solver-to-hub legs are inventory or user moves, not fills. hhi_solver_ci90 is a bias-corrected bootstrap (bootstrap_method): a block bootstrap by NearBlocks page when the sample is stratified in time (bootstrap_resampling = block_by_page), else over sampled units

## 8. Supply physics

### 8.1 Issuance: measured vs nominal
- Measured: 25,772.98 NEAR minted at epoch start 223,660,337 (previous jump 25,450.53 NEAR at 223,617,137); epoch wall time 6.899 h = 1,270.6 epochs/yr; implied annual issuance **32,748,205 NEAR** = 2.4976% of supply.
- Nominal: max_inflation_rate 2.50% x total supply 1,311,190,966 NEAR = 32,779,774 NEAR/yr; measured minus nominal -31,569 NEAR/yr (-0.10%). Daily: measured 89,660 NEAR vs nominal 89,746 NEAR; treasury share 0.0% (validators receive the rest).
- Within-epoch supply drift (net gas burn) -250.89 NEAR/epoch; measured block time 0.575 s. Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.

### 8.2 Daily sinks (NEAR/day, live)
| Sink | NEAR/day | Source | Basis |
| :--- | ---: | :--- | :--- |
| Buyback (holders revenue / price) | 17,817.2 NEAR | measured | $129.4M/day x 15.26 bps gross x alpha 32.7% / $3.63 |
| L1 gas burn | 872.8 NEAR | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| NEP state-lock growth | 327.5 NEAR | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| Total sinks | 19,017.5 NEAR |  | coverage 21.2% of measured issuance; net float 70,642 NEAR/day |


### 8.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)
| Regime (terminal rate) | V* at live take | vs today | V* at competitive ceiling |
| :--- | ---: | ---: | ---: |
| status quo (cap flat) | $642.6M | 5.0x | $3.26B |
| SVRN glidepath | $408.1M | 3.2x | $2.07B |

Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.

### 8.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)
| Regime | Volume path | Issuance/day m1 | Issuance/day m36 | Gross issuance 36m | Sinks 36m | Net float 36m | Flow crossover | Cumulative crossover |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| status quo (cap flat) | run-rate volume | 89,660 NEAR | 96,428 NEAR | 101,908,878 NEAR | 20,838,376 NEAR | 81,070,502 NEAR | none within horizon | none within horizon |
| status quo (cap flat) | +30% YoY volume | 89,660 NEAR | 96,428 NEAR | 101,908,878 NEAR | 30,682,375 NEAR | 71,226,503 NEAR | none within horizon | none within horizon |
| SVRN glidepath | run-rate volume | 89,660 NEAR | 60,684 NEAR | 77,287,963 NEAR | 20,838,376 NEAR | 56,449,588 NEAR | none within horizon | none within horizon |
| SVRN glidepath | +30% YoY volume | 89,660 NEAR | 60,684 NEAR | 77,287,963 NEAR | 30,682,375 NEAR | 46,605,589 NEAR | none within horizon | none within horizon |


### 8.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)
| Account | Contract | storage_usage bytes | Locked | Growth B/day | Growth NEAR/day | Window |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| intents.near | yes | 13,481,595,534 | 134,816.0 NEAR | 29,095,572 | 290.96 NEAR | 30.8 d |
| aurora | yes | 14,376,593,834 | 143,765.9 NEAR | 3,655,646 | 36.56 NEAR | 30.8 d |
| wrap.near | yes | 168,492,949 | 1,684.9 NEAR | n/a | n/a | n/a |
| v1.signer | yes | 1,201,113 | 12.0 NEAR | n/a | n/a | n/a |
| escrow.ai.near | no | 428 | 0.0 NEAR | n/a | n/a | n/a |
| treasury.near | yes | 357,895 | 3.6 NEAR | n/a | n/a | n/a |
| meme-cooking.near | yes | 5,979,557 | 59.8 NEAR | n/a | n/a | n/a |
| v2.ref-finance.near | yes | 111,232,634 | 1,112.3 NEAR | n/a | n/a | n/a |

- Total state-locked across 8 tracked contracts: **281,455 NEAR** at 0.01 NEAR/KB (storage_amount_per_byte 10,000,000,000,000,000,000 yocto). Measured lock growth 327.5 NEAR/day over intents.near, aurora (archival available).

### 8.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)
| Regime | Inflation | Nominal APR | Real APR | Buyback accrual | Real APR + accrual | Non-staker real |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| status quo (cap flat) | 2.50% | 5.64% | 3.14% | 0.496% | 3.63% | -2.00% |
| SVRN glidepath | 1.60% | 3.61% | 2.01% | 0.496% | 2.50% | -1.10% |

Live: 352 validators, 581,691,894 NEAR staked = 44.36% of supply.

### 8.7 Agent-scale state lock (locked = agents x KB x 0.01 NEAR/KB; default 20 KB per vault is an assumption)
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


## 9. Sum-of-the-parts valuation and peer comparables

### 9.1 Engines (percentiles over paths, USD; discounted to today)
| Engine | P10 | P25 | P50 | P75 | P90 | Assumption-heavy |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| clearinghouse | $10.8M | $24.6M | $66.4M | $199.8M | $549.8M | no |
| confidential | $14.4M | $31.5M | $87.7M | $280.4M | $824.5M | yes |
| monetary | $804,218 | $1.8M | $5.5M | $21.2M | $79.9M | yes |

| Total | P10 | P25 | P50 | P75 | P90 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| FDV (all engines) | $57.2M | $111.9M | $262.9M | $657.4M | $1.65B |
| FDV ex-monetary | $52.8M | $104.0M | $244.0M | $604.9M | $1.51B |
| Implied price / NEAR | $0.04 | $0.08 | $0.19 | $0.48 | $1.21 |

Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse $7.7M (3%) + confidential $253.8M (97%) + monetary $1.4M (1%) = $262.9M.

- PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor.
- Same construction on confidential volume at the assumed confidential take; terminal multiple x confidential_multiple_haircut because nearstats flags confidential TVL as unverified. NOT MEASURED this run: the nearstats public/confidential split failed the plausibility guard; the starting confidential share is the registry assumption confidential_share (40%), so this engine values an assumed volume, not a measured one.
- PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.

### 9.2 Calibration (what the engines were fed)
| Parameter | Value | Source / basis |
| :--- | :--- | :--- |
| Public take t=0 (gross) | 12.10 bps | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d |
| Blended gross take / net take | 15.26 bps / 5.00 bps | DefiLlama near-intents fees / volume; net = gross x alpha |
| Capture ratio alpha | 32.74% | measured:defillama near-intents dailyHoldersRevenue / fees |
| Confidential take t=0 | 20 bps | assumption (no live confidential fee series) |
| Public take floor | 0.98 bps | derived; cross-VM headroom +0.98 bps, competitor ceiling 3.00 bps |
| Compression lambda (public / confidential) | 0.030 / 0.010 per month | geometric reversion to the floor |
| Volume growth (public / confidential, monthly) | 2.21% / 2.21% | confidential share 40.0% -> 40% target (start share ASSUMED: registry confidential_share; nearstats split failed the plausibility guard) |
| Sigma: price (annual) / volume (monthly) | 1.034 / 0.349 | measured: monthly log-return sigma of 30-day volume aggregates; confidential sigma x 1.00 |
| Terminal multiple (FDV / annual holder revenue) | 60.0x (raw 2,265.0x) | source derived: peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; clipped to registry guardrails |
| Discount rate | 25% | assumption |
| Supply at horizon (glidepath) | 1,367,640,554 NEAR | fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory) |
| Current FDV | $4.76B | spot price x on-chain total_supply at the snapshot block; CoinGecko FDV via nearstats $4.75B (-0.31% gap, struck at a different instant; cross-check only) |
| GBM convention | mean-matching (Ito) | mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM uses the same convention (zero drift => E[P_t] = P_0) |
| Terminal public volume, month H | mean $170.6M/day; median $19.0M/day | start $77.7M/day; MC sample mean $150.3M, median $18.4M; the labeled YoY growth is the growth of the MEAN path |


### 9.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)
| Protocol | Fees 30d | Revenue 30d | FDV | FDV/fees | FDV/revenue | Revenue methodology (live text) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| SOL (solana) | $18.3M | $2.1M | $56.73B | 255.3x | 2,265.0x | Transaction base fees paid by users |
| ETH (ethereum) | $20.1M | $6.2M | $271.89B | 1,112.3x | 3,579.2x | Amount of ETH burned — base fees plus blob fees (both are permanently burned, accruing to no proposer) |
| HYPE (hyperliquid) | $86.3M | $66.8M | $72.46B | 69.0x | 89.1x | Parent aggregates child protocols. Hyperliquid Perps: 99% of fees go to Assistance Fund for buying HYPE tokens |
| NEAR (near) | $170,376 | $119,263 | $4.72B | 2,278.7x | 3,255.2x | 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract developers |
| NEAR (near-intents) | $5.9M | $1.9M | $4.72B | 65.5x | 200.1x | NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.ne |
| NEAR (near_combined) | $6.1M | $2.1M | $4.72B | 63.7x | 188.5x | near: 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract deve |

- Median ex-NEAR FDV / annualized revenue 2,265.0x (n = 3); FDV / annualized fees 255.3x (n = 3). annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)
- `revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live methodology text is carried in the table so the multiple is read with its definition.

### 9.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take (SVRN glidepath; * = net-deflationary)
| Net take \ Volume/day | $100.0M | $250.0M | $500.0M | $1.00B | $1.50B |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2 bps | $252.3M | $572.3M | $1.11B | $2.17B | $3.24B* |
| 6 bps | $678.9M | $1.64B | $3.24B* | $6.44B* | $9.64B* |
| 10 bps | $1.11B | $2.71B* | $5.37B* | $10.70B* | $16.04B* |
| 14 bps | $1.53B | $3.77B* | $7.50B* | $14.97B* | $22.44B* |
| 18 bps | $1.96B | $4.84B* | $9.64B* | $19.24B* | $28.84B* |

Current FDV $4.76B; confidential share used in the split 40.0%. Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).

## 10. Bear case and early-warning triggers

Value basis: deterministic at median inputs; not a Monte Carlo percentile. Base deterministic FDV (median inputs) $817.9M, implied price $0.60; the Monte Carlo P50 of section 9 is a different statistic and is not what the drawdowns below are measured against. drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed

| Scenario | Deterministic FDV (median inputs) | FDV drawdown | Implied price | Price drawdown | Flow crossover |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fee_race_to_zero | $178.9M | -78.1% | $0.13 | -78.1% | none within horizon |
| governance_stalemate | $817.9M | +0.0% | $0.59 | -1.8% | none within horizon |
| post_incentive_decay | $329.7M | -59.7% | $0.24 | -59.7% | none within horizon |
| solver_cartelization | $562.3M | -31.3% | $0.41 | -31.3% | none within horizon |
| combined worst | $105.9M | -87.1% | $0.08 | -87.3% | none within horizon |


### 10.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)
| Scenario | Metric | Now | Trigger | Status | Monitor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| fee_race_to_zero | net_take_bps_30d | 5.00 bps | < 3.00 bps | not breached | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue (sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days). |
| governance_stalemate | max_inflation_rate | 2.50% | > 1.60% | **BREACHED** | https://free.rpc.fastnear.com (EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)). Note: breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted |
| post_incentive_decay | volume_30d_vs_record_30d | -19.7% | <= -40.0% | not breached | https://nearstats.org/api/near/summary (intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1). |
| solver_cartelization | hhi_solver | 6,256 | > 3,500 | **BREACHED** | https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50 (HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)); secondary headroom_cross_vm_bps +0.98 bps < 0 bps (not breached). Note: sample: 77 solver fill participations over 17,567 s; HHI_solver 6,256, bootstrap 90% CI [5,037, 7,537] (CI lower bound 5,037 > 3,500: breached); deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = 3,555 |


### 10.2 Scenario narratives
**Aggregator bypass: public take races to 1 pip.** Third-party frontends route around near.com and the public gross take collapses from 12.1 bps to 0.01 bps (the bare intents.near contract fee); confidential execution reprices from 20 bps to 5 bps. Capture ratio alpha is held at 33%, so the hit is price, not allocation. Deterministic (median-input) FDV -78.1% to $178.9M; implied price $0.13. Evidence against it: live cross-VM headroom is +1.0 bps, so a bypassing frontend must first give up that execution edge. Trigger: DefiLlama 30d net take (gross x alpha) below 3.0 bps (now 5.0 bps).

**Governance stalemate: 2.5% issuance forever.** Validators never enact the SVRN cut: max_inflation_rate stays at 2.50% for the full horizon instead of gliding to 1.60%. Protocol cash flows do not change, so FDV moves +0.0%; the damage is dilution: 24,620,914 more NEAR outstanding at the horizon and a per-token value of $0.59 (-1.8% vs base). Net-float crossover: none within horizon (base: none within horizon). This scenario is live today: the on-chain cap reads 2.50% and no cut has been enacted.

**Post-incentive volume decay (NEAR@3.33 unwind).** Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume $77.7M -> $31.1M (-60%), confidential $51.8M -> $15.5M (-70%) and confidential TVL x0.3 (nearstats flags that TVL unverified). Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV -59.7% to $329.7M; implied price $0.24. Current 30d volume $3.88B is 80% of the 30d record $4.84B; the trigger fires at -40%.

**Solver cartelization: HHI_solver > 3,500, 1Click loses the spread.** Two market makers take most fills (HHI_solver > 3,500) and spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM (headroom -2 bps). Keeping flow costs the same 2 bps of take (12.1 bps -> 10.1 bps) while compression runs at 0.15/month. Deterministic (median-input) FDV -31.3% to $562.3M; implied price $0.41. Live: HHI over solver fill participations 6,256 (1.6 effective solvers across 77 fill participations), bootstrap 90% CI [5,037, 7,537]; deposit-source HHI over external predecessors 3,555 (not a solver measure); cross-VM headroom +1.0 bps; trigger at HHI_solver > 3,500 or headroom < 0.

### 10.3 Falsification summary
fee_race_to_zero: public gross take at 0.01 bps and confidential at 5 bps puts the deterministic FDV at $178.9M (-78.1%); watch DefiLlama near-intents 30d net take weekly, trigger < 3.0 bps, now 5.0 bps (not breached). governance_stalemate: no SVRN cut (cap 2.50% for 36 months) leaves the deterministic FDV at $817.9M (+0.0%) but dilutes per-token value to $0.59 (-1.8%) with crossover none within horizon; watch max_inflation_rate in EXPERIMENTAL_protocol_config, trigger > 1.60%, now 2.50% (BREACHED). post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at $329.7M (-59.7%); watch nearstats 30d volume against its 30d record weekly, trigger <= -40%, now -19.7% (not breached). solver_cartelization: HHI_solver > 3,500 with cross-VM headroom at -2 bps puts the deterministic FDV at $562.3M (-31.3%); watch the execute_intents solver HHI (now 6,256) and the live quote-race headroom (now +1.0 bps) weekly (BREACHED). All four at once: deterministic FDV $105.9M (-87.1% vs base $817.9M); 2 of 4 measured triggers currently breached, and the thesis is falsified if any trigger holds for 30 consecutive days.

## 11. Evidence scorecard

| Claim | Status | Value | Source | Confidence | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB) | **VERIFIED_ON_CHAIN** | intents.near storage_usage 13,481,595,534 bytes = 134,816 NEAR locked; 281,455 NEAR across 8 tracked contracts | near_rpc/view_account:intents.near sha256 cd020a2a1373... @ block 223,672,128; storage_amount_per_byte from EXPERIMENTAL_protocol_config | high | growth 29,095,572 B/day = 291.0 NEAR/day over 30.8 d (archival); a 0.01 NEAR/KB lock is released if state is deleted, so it is a sink while state grows |
| Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap | **VERIFIED_ON_CHAIN** | 25,772.98 NEAR minted at epoch start 223,660,337 x 1,270.6 epochs/yr = 32,748,205 NEAR/yr (2.4976%), -0.10% vs nominal 32,779,774 | near_rpc/block:223660337 sha256 99b5955e5c8c... and its predecessor by prev_hash; previous epoch start 223617137 | high | second independent jump 25,450.53 NEAR; within-epoch drift -250.89 NEAR/epoch is the net gas burn |
| Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC | **VERIFIED_LIVE_API** | median headroom +0.98 bps over 3 comparable cells (dest_units); competitor ceiling 3.00 bps | oneclick/relay/lifi/across quote records 2026-11-08T21:24:31.888Z | medium | $500: +1.70 bps vs relay (rank 1/3); $50,000: +0.98 bps vs relay (rank 1/3); $250,000: +0.98 bps vs relay (rank 1/3); no 1Click capacity failures |
| Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC | **NOT_SUPPORTED** | 1Click delivers LESS BTC per USDC than the best competitor (relay): median headroom -5.68 bps over 3 cells (dest_units); the claim is not supported by this run | oneclick/lifi/relay quote records 2026-11-08T21:24:31.888Z | medium | clip-dependent: $500: -14.07 bps vs relay (rank 2/2); $50,000: -5.68 bps vs relay (rank 2/2); $250,000: +4.66 bps vs relay (rank 1/2); LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used |
| EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative) | **VERIFIED_LIVE_API** | median headroom -1.02 bps over 3 cells (dest_units; 1Click trails) | oneclick/across/relay/lifi quote records 2026-11-08T21:24:31.888Z | medium | $500: +0.10 bps vs across (rank 1/3); $50,000: -1.02 bps vs across (rank 3/3); $250,000: -1.02 bps vs across (rank 3/3); the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins |
| Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material | **DERIVED** | deposit/caller HHI_external 3,555 [90% CI 2,383-5,000] (N_eff 2.81), ex-AI-agent 2,041; AI-agent share 56.2% (>= 10% materiality line), bridge share 31.2% | nearblocks/txns:intents.near:p1 sha256 32b12f89b40e... ... p8 | low | 183 unique receipts over 73 s; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources (bridge callbacks, direct callers), not solvers |
| Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers | **VERIFIED_LIVE_API** | HHI_solver 6,256 [90% CI 5,037-7,537] (N_eff 1.60) over 77 fill participations in 77 fills (0 atomic token_diff fills, 77 hub-settled legs), 4 distinct solvers; CI entirely above the 3,500 cartel threshold | nearblocks/txns:intents.near:p1 sha256 32b12f89b40e... ... p8 + 8 method-filtered execute_intents page(s); args.signed[].payload.message (NEP-413 signer_id) | medium | 454 execute_intents receipts decoded; settlement hub 51e8f94d77b5... (151 counterparties) routes most swaps via transfer legs; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty |
| Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume | **ASSUMPTION** | NOT MEASURED this run: nearstats reported 0.00% (implausible); the model uses the registry assumption confidential_share = 40% | nearstats/summary sha256 99e3b178998c... intents.totalsBreakdown (basis public+confidential) | none | split rejected by the plausibility guard (share_below_floor: reported 0.0000% < 1%; tvl_without_volume: confidential TVL $143.16M but all-time confidential volume $0.00 of $37.86B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'); raw fields in intents_forensics.volume.split_reported. Engine 2 rests on an assumption this run |
| Confidential TVL backs the dark-pool engine (Engine 2) | **VERIFIED_LIVE_API** | $143.2M TVL, nearstats sourceStatus = verified | nearstats/summary sha256 99e3b178998c... intents.protocolMetrics.confidentialTvlObservation | low | Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut (0.7); the confidential take (20 bps) is an assumption |
| Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink | **DERIVED** | alpha 32.7%; gross take 15.26 bps, net take 5.00 bps; buyback sink 17,817 NEAR/day = 21.2% coverage incl. burn and lock | defillama/fees:near-intents:dailyHoldersRevenue sha256 f96518a888a5... / defillama/fees:near-intents sha256 2838d4605dc8... | medium | DefiLlama revenue methodology: NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.near.org and the on-chain buyback). Split by destination wallet into front-end affiliate revenue and Other. Transfers between those wallets are excluded. |


## 12. Assumptions register

### 12.1 Labeled assumptions (slider inputs; never presented as measured)
| Key | Default | Unit | Range | Justification |
| :--- | :--- | :--- | :--- | :--- |
| svrn_target_inflation | 0.016 | ratio_annual | [0.005, 0.03] | SVRN governance proposal to cut the protocol max_inflation_rate from 2.5% to 1.6%; not enacted on-chain (live EXPERIMENTAL_protocol_config.max_inflation_rate is still [1, 40]). |
| svrn_glidepath_months | 24 | months | [6, 48] | QUANT_PIPELINE_SPEC and TERMINAL_UI_SPEC model the 2.5% -> 1.6% cut as a linear 24-month (730-day) glidepath; the proposal itself does not fix the phasing. |
| public_volume_growth_yoy | 0.3 | ratio_yoy | [-0.2, 1.5] | EXPECTED (mean) public-volume growth: the volume GBM carries the Ito drift ln(1+g) - sigma^2/2 per month, so E[V_t] = V_0 (1+g)^(t/12) and 30% YoY is the growth of the MEAN path (= the deterministic path); the Monte Carlo MEDIAN path is lower by exp(-sigma^2 t/2) at the measured monthly sigma (see sotp.calibration.gbm_convention and volume_terminal_median_usd_day). Default 30% is set well below the trailing-1y DefiLlama near-intents volume growth, which included incentive-driven months (NEAR@3.33); the slider range spans decay to -20% and 2.5x growth. |
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


### 12.2 Measured and derived model inputs (point values with their source)
| Key | Value | Unit | Source | Basis |
| :--- | :--- | :--- | :--- | :--- |
| total_supply_near | 1,311,190,966 | NEAR | measured | RPC block header total_supply at height 223672128 |
| current_max_inflation_rate | 0.025 | ratio_annual | measured | RPC EXPERIMENTAL_protocol_config.max_inflation_rate |
| treasury_share | 0 | ratio | measured | RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this) |
| staked_supply_ratio | 0.443636 | ratio | measured | RPC validators current stake / total_supply (352 validators) |
| annual_issuance_near | 32,748,205 | NEAR_per_year | measured | minted_per_epoch 25772.978416874335 NEAR x epochs_per_year 1270.6410793312305 from total_supply jumps at epoch starts 223617137 -> 223660337 |
| issuance_realization_factor | 0.999037 | ratio | measured | measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path |
| near_price_usd | 3.63 | USD | measured | nearstats price.currentUsd via intents_forensics.price.current_usd |
| daily_volume_usd | 129,424,263 | USD_per_day | measured | intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window (aligned daily charts, 30 complete UTC day |
| gross_take_bps | 15.2627 | bps | measured | intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window (aligned daily charts, 30 complete UTC |
| capture_ratio | 0.327414 | ratio | measured | intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window (aligned daily charts, 30 complete  |
| gas_burn_near_per_day | 872.789 | NEAR_per_day | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| state_lock_growth_near_per_day | 327.5122 | NEAR_per_day | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| competitive_fee_ceiling_bps | 3.004 | bps | derived | median over cross-VM cells of the best competitor's friction (per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding); the lowest-fric |
| tau_floor_bps | 0.982395 | bps | derived | max(0.5 bps, min(live public take, live cross-VM headroom)) from the execution benchmark (headroom_by_archetype_bps.cross_vm = 0.98 bps). |
| tau_pub_start_bps | 12.1046 | bps | derived | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d; blended live gross take 15.26 bps (DefiLlama daily fees / daily volume summed over the a |
| alpha_capture | 0.327414 | ratio | measured | measured:defillama near-intents dailyHoldersRevenue / fees |
| terminal_multiple | 60 | x_fdv_to_revenue | derived | peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; raw 2265.0x. |
| sigma_price_annual | 1.0341 | ratio_annual | measured | nearstats:price-history: 1y daily closes, log-return sigma x sqrt(365). |
| sigma_volume_monthly | 0.349032 | ratio_monthly | measured | measured: monthly log-return sigma of 30-day volume aggregates |


## 13. Reproduction

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

## 14. Data provenance

91 raw exchanges (82 ok, 9 failed), 3,615,448 bytes hashed; raw bodies persisted under `artifacts/raw` and listed with SHA-256 in `manifest.json`.

| Source | Records |
| :--- | ---: |
| across | 6 |
| coingecko | 1 |
| defillama | 15 |
| lifi | 9 |
| near_rpc | 15 |
| near_rpc_archival | 6 |
| nearblocks | 18 |
| nearstats | 2 |
| oneclick | 10 |
| relay | 9 |


Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):
| Source | Name | HTTP | Error |
| :--- | :--- | :--- | :--- |
| across | quote:eth_usdc_sol_usdc:500 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:50000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:250000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| lifi | quote:eth_usdc_btc:500 | 429 | HTTP 429: Rate limit exceeded, retry in 1 hour |
| lifi | quote:eth_usdc_btc:50000 | 429 | HTTP 429: Rate limit exceeded, retry in 1 hour |
| lifi | quote:eth_usdc_btc:250000 | 429 | HTTP 429: Rate limit exceeded, retry in 1 hour |
| lifi | quote:base_usdc_arb_usdc:500 | 429 | HTTP 429: Rate limit exceeded, retry in 1 hour |
| lifi | quote:base_usdc_arb_usdc:50000 | 429 | HTTP 429: Rate limit exceeded, retry in 1 hour |
| lifi | quote:base_usdc_arb_usdc:250000 | 429 | HTTP 429: Rate limit exceeded, retry in 1 hour |


### 14.1 Methodology warnings recorded during the run (12)
- execution_bench: eth_usdc_sol_usdc $500: venue USD oracles disagree with the cell's common price by more than the +1.70 bps headroom (1click +0.0 bps, relay +2.4 bps, lifi -11.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +2.4 bps, lifi -11.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +2.4 bps, lifi -11.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $50,000: venue USD oracles disagree with the cell's common price by more than the -5.68 bps headroom (1click +0.0 bps, relay -10.9 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $250,000: venue USD oracles disagree with the cell's common price by more than the +4.66 bps headroom (1click +0.0 bps, relay -10.9 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $500: venue USD oracles disagree with the cell's common price by more than the +0.10 bps headroom (1click +0.0 bps, relay +2.3 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +2.3 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +2.3 bps); headroom is measured on destination units, not USD legs
- intents_forensics: CONFIDENTIAL SPLIT IMPLAUSIBLE - NOT MEASURED: nearstats reports confidential 30d $0.26 (0.0000% of 30d volume) while tvl_without_volume: confidential TVL $143.16M but all-time confidential volume $0.00 of $37.86B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'. The public tile appears to include confidential flow (source change). public/confidential fields set to null (raw kept in volume.split_reported); confidential_share_30d = 40% from the registry assumption confidential_share (source=assumption)
- intents_forensics: nearblocks: 17 duplicate receipt(s) seen on overlapping pages were counted once (id-based cursor vs time-ordered rows); unique receipts sampled = 183
- sotp: confidential share is the registry ASSUMPTION confidential_share = 40%, not a measurement (nearstats reported 0.0000%, rejected as implausible by confidential_split_guard); Engine 2 rests on that assumption and is reported as NOT MEASURED
- sotp: peer median FDV/revenue 2265.0x clipped to 60.0x (guardrails [8, 60])
