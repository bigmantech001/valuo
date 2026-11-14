# Valuo IC Memo: NEAR at block 224,473,852

*NEAR Intents clearinghouse + NEAR L1. Generated 2026-11-14T06:05:03.623Z UTC from live mainnet RPC and key-free public APIs; every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section 14.*

| Provenance | Value |
| :--- | :--- |
| NEAR block | 224,473,852 (`2vRsPXzb74RKFSKqMyJCigKPXiYsasWMosV8yZudhptn`), 2026-11-14T06:05:01.299Z |
| RPC endpoint | https://free.rpc.fastnear.com |
| Snapshot generated | 2026-11-14T06:05:03.623Z UTC, runtime 783.6 s, valuo 0.1.0, schema 1.0.0 |
| Snapshot SHA-256 | `951cff146437a3e2e0cba075b5ba3bdaf669372683052c31eda053043b025b21` |
| Monte Carlo | seed 20261114, 10,000 paths, 36 months |
| Raw records | 230 HTTP/RPC exchanges hashed, 27 non-2xx/failed (every one listed in manifest.json) |


## 1. The long-term case, made falsifiable

The long-term case for NEAR at $4.38B: 3 of 8 measured conditions are on track. It holds if the market keeps an L1 multiple (117x revenue needed against a 2,544x peer median) while Intents grows into it; it fails if volume growth stays near 32% a year against the 125% the price implies.

| Condition | Required | Live | Trend | Status |
| :--- | ---: | ---: | :--- | :--- |
| Intents volume compounds fast enough to grow into the price | 125% a year | 32% a year | +100% (30-day volume vs 90 days earlier) | **Behind** |
| Holder revenue (buybacks) scales to support the price at the model's multiple | $155.9M a year | $22.4M a year | +306% (30-day holder revenue vs 90 days earlier) | **Behind** |
| The market keeps valuing NEAR like an L1, not like a fee-only app | 117x | 2,544x | n/a | **On track** |
| 1Click keeps a pricing edge where it competes (cross-VM routes) | > 0 | +1.55 bps | n/a | **On track** |
| Confidential (private) flow keeps growing | > 0 | $13.6M | +376% (confidential TVL vs 90 days earlier) | **On track** |
| Fees retire more NEAR than issuance creates | $383.8M a day | $126.6M a day | n/a | **Behind** |
| Governance cuts issuance from 2.5% to 1.6% | 1.6% | 2.5% | n/a | **Behind** |
| Solver competition stays broad enough to keep spreads tight | <= 3,500 | 4,946 | n/a | **Against** |


How to read it: each requirement is what the market price needs if that condition alone carries the case (from the reverse valuation in section 3), or the threshold the bear case watches (section 11). An investor holding NEAR long-term is betting that the conditions marked Behind close; the ones marked Against are where the case is currently losing. Re-run `make reproduce` to re-grade every row against live data.

## 2. Executive summary

**Model value vs market value.** Market FDV is $4.38B (spot price x on-chain total supply at block 224,473,852). The model's expected-path FDV is $2.30B and its 10,000-path Monte Carlo gives P10 / P50 / P90 = $130.4M / $698.4M / $4.49B. The market sits above the expected path (1.9x it) and at 6.3x the Monte Carlo P50. The model capitalises NEAR Intents holder revenue, L1 gas burn and state-lock flow over 36 months at a 25% discount rate and a 60x terminal multiple; the question below is which input would have to change for it to reach the market price, and whether the evidence allows that.

**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in section 3).

| Input | Base | Required for market FDV | Evidence | Inside evidence |
| :--- | ---: | ---: | ---: | :--- |
| Expected annual public-volume growth (3-year path) | 75.0% | 124.9% | 32.4% | no |
| Starting gross public take rate | 15.57 bps | 46.61 bps | 3.00 bps | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 117x | 2,544x | yes |
| Annual discount rate | 25.0% | 0.5% | 10.0% | no |
| Confidential share of volume at month 36 | 40.0% | 71.6% | 10.2% | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $79.1M/yr | $155.9M/yr | $22.4M/yr | no |


**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple (117x needed; live peer FDV/revenue HYPE 78x, SOL 2,544x, ETH 3,082x, median 2,544x over n = 3 peers). A 0.5% discount rate would also close it (registry range starts at 10%). The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on Intents cash flow at the model's 60x terminal cap. On cash flow alone (multiple held at the model's 60x), the market price requires 125%/yr expected public-volume growth for 3 years (trailing 12 months: +32.4%), or a 47 bps starting public take (today 15.57 bps, live competitive ceiling 3.00 bps), or $155.9M of annualised holder revenue in year 3 (6.9x today's $22.4M); none of these is inside its measured evidence. Whether NEAR keeps an L1 multiple is the investment question; this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token.

**What you have to believe** (section 4). The three inputs that move FDV most are Expected annual public-volume growth (15.8% to 164.6%: $811.9M-$6.68B); Terminal FDV / holder-revenue multiple (8.00x to 150x: $399.9M-$5.59B); Public take compression speed (per month) (0.0%/month to 15.0%/month: $780.0M-$4.04B). Together they carry 85% of the swing-squared variance proxy. 2 of 17 single-input ranges reach the market FDV.

**Relative value** (section 5). NEAR trades at 61x annualised fees against a peer median of 245x (rank 2 of 4, lowest multiple first; inside the peer range); at peer FDV/fees multiples NEAR's fees map to $11.05B-$43.83B (cross-check, not a fair value; n = 3 peers); holder revenue covers 21% of the $109.4M/yr security budget.

**Evidence quality flags.**

- Confidential share: ESTIMATED ON-CHAIN at 10.2% (band 9.2%-11.1%). nearstats reported 0.0000%, which its own payload contradicts, so the share is read from the Confidential Intents Treasury instead: 24h inflow $17.2M, outflow $18.7M, against 24h volume $168.7M. Same-hour netting and in-shard turnover bias it down, solver inventory up; one 24h window. Engine 2 ($940.9M of the $2.30B expected-path FDV) is valued on this estimate, not on the 40% registry assumption. On-chain cross-check: the Confidential Intents treasury (`51e8f94d...de7cbe` in `intents.near`) holds $132.1M at block 224,473,865 (205 tokens, 30 unpriced); net 30-day boundary flow $13.6M at today's prices; over 24h at least $17.2M entered and $18.7M left (hourly snapshots, lower bounds), an inflow of 9.2% of 24h volume. Confidential swaps settle on a private chain whose RPC needs authentication, so swap volume itself cannot be read; boundary inflow is a proxy, not the share (it nets same-hour flows and includes solver inventory).
- Deposit/caller HHI 828 (bootstrap 90% CI 769-828) over 26 external receipts spanning 53 s; a point sample, not a market-share estimate.
- Solver HHI 4,946 (bootstrap 90% CI 4,335-5,523) over 96 fill participations spanning 18,625 s. Cartel trigger: BREACHED (sample: 96 solver fill participations over 18,625 s).
- Bear case: 2 of 4 graded early-warning triggers breached. Combined-worst deterministic FDV $227.8M (-90%).

## 3. What the market is pricing (reverse valuation)

Basis: deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base. Solver: scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12. Market FDV $4.38B; expected-path model FDV $2.30B (gap 1.9x); Monte Carlo P50 $698.4M (gap 6.3x). Every required value is the expected-path requirement; the P50 sits lower by lognormal convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).

| Input | Base | Required for market FDV | Evidence | Evidence basis | Inside evidence |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Expected annual public-volume growth (3-year path) | 75.0% | 124.9% | 32.4% | trailing-12-month NEAR Intents 30-day volume growth | no |
| Starting gross public take rate | 15.57 bps | 46.61 bps | 3.00 bps | live competitive fee ceiling (median best-competitor friction, cross-VM cells) | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 117x | 2,544x | peer median FDV / annualised revenue ex-NEAR (unclipped) | yes |
| Annual discount rate | 25.0% | 0.5% | 10.0% | low end of the registry discount-rate range (10%-40%) | no |
| Confidential share of volume at month 36 | 40.0% | 71.6% | 10.2% | on-chain estimate of the confidential share (Confidential Intents Treasury 24h boundary flow / 24h volume) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $79.1M/yr | $155.9M/yr | $22.4M/yr | current annualised holder revenue (30-day window x 365.25/30) | no |

- Justifying $4.38B needs 125% expected annual public-volume growth for 3 years (base 75%); trailing-12-month Intents volume growth was 32%.
- Justifying $4.38B needs a starting gross public take of 46.6 bps (decaying to the 1.55 bps floor at 3%/month) versus 15.57 bps today; the live competitive fee ceiling is 3.00 bps.
- Justifying $4.38B needs a 117x terminal FDV/holder-revenue multiple; the live peer median is 2,544x (HYPE 78x, SOL 2,544x, ETH 3,082x) and the model caps it at 60x.
- Justifying $4.38B needs a 0.5% discount rate versus 25% base; the registry range is 10%-40%.
- Justifying $4.38B needs the confidential share to reach 72% by month 36; the on-chain estimate today is 10% (band 9%-11%).
- Justifying $4.38B at the 60x base multiple needs $156M of annualised holder revenue in year 3 (2.0x the base path's $79M), versus $22M today (91%/yr compounded).

Headline: Market FDV $4.38B is 1.9x the model's expected-path FDV $2.30B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 117x (evidence 2,544x).

Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the joint requirement is smaller than any single one; section 4 shows which inputs carry the variance.

## 4. What you have to believe (one-at-a-time sensitivity)

Basis: deterministic_sotp expected path; one input at its low / high, all others at the snapshot base. Base expected-path FDV $2.30B against a $4.38B market FDV. Variance share: swing^2 / sum(swing^2): first-order share for independent inputs, an approximation. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).

| # | Input | Source | Range | Base | FDV at low | FDV at high | Swing | Variance share |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Expected annual public-volume growth | measured | 15.8% - 164.6% | 75.0% | $811.9M | $6.68B | $5.87B | 40.5% |
| 2 | Terminal FDV / holder-revenue multiple | derived | 8.00x - 150x | 60x | $399.9M | $5.59B | $5.19B | 31.7% |
| 3 | Public take compression speed (per month) | assumption | 0.0%/month - 15.0%/month | 3.0%/month | $4.04B | $780.0M | $3.26B | 12.5% |
| 4 | Confidential share at month 36 | assumption | 5.0% - 60.0% | 40.0% | $1.47B | $3.27B | $1.80B | 3.8% |
| 5 | Annual discount rate | assumption | 10.0% - 40.0% | 25.0% | $3.35B | $1.65B | $1.70B | 3.4% |
| 6 | Starting 30-day Intents volume (public + confidential) | measured | 0.71x - 1.42x | 1.00x | $1.67B | $3.19B | $1.52B | 2.7% |
| 7 | Holder capture (revenue / gross fees) | measured | 12.9% - 31.0% | 30.5% | $1.07B | $2.34B | $1.27B | 1.9% |
| 8 | NEAR price drift (gas-burn and state-lock USD value) | assumption | -50.0% - 100.0% | 0.0% | $2.17B | $3.10B | $925.7M | 1.0% |
| 9 | Confidential multiple haircut | assumption | 30.0% - 100.0% | 70.0% | $1.79B | $2.69B | $902.6M | 1.0% |
| 10 | Confidential gross take (public take re-reconciled to live fees) | assumption | 10.00 bps - 30.00 bps | 20.00 bps | $1.92B | $2.68B | $762.8M | 0.7% |
| 11 | Confidential compression divisor | assumption | 1.00x - 10x | 3.00x | $1.90B | $2.51B | $604.7M | 0.4% |
| 12 | Public take hard floor | assumption | 0.00 bps - 5.00 bps | 0.50 bps | $2.30B | $2.71B | $410.7M | 0.2% |
| 13 | Blended gross take (public take re-reconciled) | measured | 12.28 bps - 17.03 bps | 16.03 bps | $2.02B | $2.38B | $354.4M | 0.1% |
| 14 | NEAR spot price (USD value of gas burn and state lock) | measured | $2.48 - $4.49 | $3.34 | $2.26B | $2.36B | $95.3M | 0.0% |
| 15 | Cross-VM headroom (sets the public take floor) | measured | 1.16 bps - 1.93 bps | 1.55 bps | $2.25B | $2.35B | $91.9M | 0.0% |
| 16 | L1 gas burn (NEAR/day) | measured | 715 NEAR/day - 1,192 NEAR/day | 953 NEAR/day | $2.26B | $2.34B | $78.2M | 0.0% |
| 17 | State-lock growth (NEAR/day) | measured | 257 NEAR/day - 428 NEAR/day | 342 NEAR/day | $2.30B | $2.30B | $1.1M | 0.0% |

Top three inputs carry 85% of the variance proxy. 2 of 17 single-input ranges reach the market FDV at either end.

Headline: public_volume_growth_yoy, terminal_multiple, fee_compression_lambda_monthly carry 85% of the swing-squared variance proxy; public_volume_growth_yoy alone moves FDV from $812M to $6.68B across its range, and 2 of 17 single-input ranges reach the $4.38B market FDV.

Excluded (move issuance and implied price, not FDV): svrn_target_inflation (issuance path only: moves supply at horizon and implied price, not FDV); svrn_glidepath_months (issuance path only: moves supply at horizon and implied price, not FDV).

## 5. Relative value: peer cash-flow multiples and the security budget

Basis: live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR.

### 5.1 NEAR cash-flow coverage against the peer set
| Metric | NEAR | Peer median | Peer P25 - P75 | NEAR rank | Position |
| :--- | ---: | ---: | ---: | ---: | :--- |
| FDV / annualised fees (30-day run-rate) | 61x | 245x | 152x - 604x | 2 of 4 | inside the peer range |
| FDV / annualised revenue (30-day run-rate) | 192x | 2,544x | 1,311x - 2,813x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day fees | 81x | 210x | 142x - 771x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day revenue | 435x | 1,923x | 1,010x - 3,405x | 2 of 4 | inside the peer range |

| Protocol | FDV | Fees (ann.) | Revenue (ann.) | FDV/fees | FDV/revenue | FDV/fees 1y | FDV/revenue 1y | Revenue/fees |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SOL (solana) | $48.38B | $197.7M | $19.0M | 245x | 2,544x | 210x | 1,923x | 10% |
| ETH (ethereum) | $232.71B | $241.4M | $75.5M | 964x | 3,082x | 1,332x | 4,886x | 31% |
| HYPE (hyperliquid) | $65.92B | $1.10B | $843.5M | 60x | 78x | 74x | 97x | 77% |
| NEAR (near_combined) | $4.44B | $72.5M | $23.1M | 61x | 192x | 81x | 435x | 32% |
| NEAR (near) | $4.44B | $1.6M | $1.1M | 2,816x | 4,024x | 3,856x | 5,505x | 70% |
| NEAR (near-intents) | $4.44B | $71.0M | $22.0M | 63x | 202x | 82x | 472x | 31% |

The model's terminal multiple is 60x; 0 of 3 peers trade at or below it on FDV/revenue.

### 5.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)
| Cash flow | NEAR (ann.) | at peer P25 | at peer median | at peer P75 | Peers | Basis |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| fees | $72.5M | $11.05B | $17.75B | $43.83B | 3 | comps.near_combined.annualized_fees_usd x peer FDV / annualised fees (30-day run-rate) |
| revenue | $23.1M | $30.28B | $58.75B | $64.96B | 3 | comps.near_combined.annualized_revenue_usd x peer FDV / annualised revenue (30-day run-rate) |

relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution; market FDV $4.38B.

### 5.3 Staking and security budget
- Security budget: 32,759,808 NEAR/yr of issuance (2.50%) x $3.34 = $109.4M/yr (2.47% of FDV).
- Against it: $72.5M/yr of fees (66% of the budget) and $23.1M/yr of holder revenue (21%); net dilution $86.3M/yr.
- Staked 44.9% of supply; nominal staking APR 5.57%. Basis: security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate.

### 5.4 Findings
- NEAR trades at 61x annualised fees versus a peer median of 245x (rank 2 of 4, lowest first; inside the peer range); on revenue it is 192x versus 2,544x (inside the peer range).
- 0 of 3 peers trade at or below the model's 60x terminal FDV/revenue multiple; NEAR itself trades at 192x.
- At the peer FDV/fees distribution, NEAR's $73M of annualised fees maps to $11.05B-$43.83B (median $17.75B, n = 3) against a $4.38B market FDV; a relative-value cross-check, not a fair value.
- NEAR issues $109M a year to validators and delegators (2.5% of FDV) against $73M of annualised fees and $23M of holder revenue (gas burn + Intents buyback): revenue covers 21% of the security budget.
- At 2.5% inflation stakers earn 5.57% nominal and 3.58% real including buybacks; non-stakers lose 1.99% a year to dilution net of buybacks.

Caveat: Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples compare different cash-flow definitions; with n = 3 peers the median is a reference point, not a distribution.

## 6. Model valuation detail

**Base case.** 10,000-path SOTP (seed 20261114): P10 / P50 / P90 FDV = $130.4M / **$698.4M** / $4.49B; implied price $0.10 / **$0.51** / $3.28 per NEAR against spot $3.34. The P50 sits 84.1% below the current FDV of $4.38B. The deterministic SOTP at the labeled inputs (the expected-volume path) is $2.30B: engines $1.20B clearinghouse + $940.9M confidential + $158.5M monetary; the Monte Carlo mean is $2.18B. Ex-monetary P50: $663.1M.

**Volume growth is measured, not assumed.** Trend growth of NEAR Intents daily volume over 2025-11-14 to 2026-11-13 (365 days, DefiLlama): +75.0%/yr, 90% CI +16% to +165% (OLS of log volume on time, Newey-West errors). The model uses it as public_volume_growth_yoy, with the CI as its range; it is the median trend, so reading it as expected growth is conservative. Cross-checks, not used: yoy trailing 30d +44%, mean monthly log return 12m +23%.



**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled +75% YoY volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of 0.347 the MEDIAN simulated path ends month 36 at 11.4% of the expected path ($69.1M/day vs $606.1M/day), which is what pulls the P50 FDV below the mean. The dispersion is measured from 11 monthly volume log-returns (sigma excluding the three oldest, incentive-era windows: 0.349); a thin sample, reported as such.

**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation; section 3 solves which single input would: Market FDV $4.38B is 1.9x the model's expected-path FDV $2.30B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 117x (evidence 2,544x). The P90 ($4.49B) comes from volume paths, not from take-rate expansion (the public take only compresses in this model).

**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** 6 bps net take needs >= $1.00B/day; 10 bps net take needs >= $500.0M/day; 14 bps net take needs >= $500.0M/day; 18 bps net take needs >= $250.0M/day. Live run-rate: $125.8M/day at 4.88 bps net (16.03 bps gross x capture 30.5%).

**Net-float crossover.** Today sinks cover 21.9% of measured issuance (19,686 NEAR/day vs 89,691 NEAR/day). status quo (cap flat): deterministic flow crossover none within horizon at run-rate volume, none within horizon with the +75% YoY growth assumption; Monte Carlo P(crossover within 36m) = 67.2%, P(deflationary at horizon) = 49.0%; breakeven volume V* = $604.7M/day (4.8x today). SVRN glidepath: deterministic flow crossover none within horizon at run-rate volume, month 26 with the +75% YoY growth assumption; Monte Carlo P(crossover within 36m) = 74.5%, P(deflationary at horizon) = 57.2%; breakeven volume V* = $383.8M/day (3.1x today). The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price outruns issuance); the deterministic path (the expected-volume path) is the one to quote.

**Falsification.** Four stress scenarios (section 11) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo percentile) at $227.8M (-90% vs the deterministic base $2.30B); 2 of 4 measured early-warning triggers are breached in this snapshot (breached: governance_stalemate (max_inflation_rate now 2.50% vs > 1.60%); solver_cartelization (hhi_solver now 4,946 vs > 3,500)). The on-chain inflation cap reads 2.50%; the SVRN cut is a proposal, not protocol state.

## 7. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)

Executable quotes fetched 2026-11-14T06:05:11.295Z UTC (30 ok of 36; 1Click token universe 231 assets on 39 chains). Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input (headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price (`price_basis`: oneclick_token_list_oracle); raw-unit friction is exact for USDC -> USDC. Positive headroom means 1Click paid out more after all fees.

| Corridor | Clip | Venue | Status | Out | Friction | ETA | Route |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | 1click | ok | 499.926513 | 1.47 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $500 | relay | ok | 499.829833 | 3.40 bps (raw) | 1 s | relay |
| ETH USDC -> SOL USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $500 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $50,000 | 1click | ok | 49,992.707002 | 1.46 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $50,000 | relay | ok | 49,984.979833 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $50,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $250,000 | 1click | ok | 249,949.492596 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $250,000 | relay | ok | 249,924.979833 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $250,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | 1click | ok | 0.007408 | 34.00 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $500 | relay | ok | 0.007416 | 23.99 bps (usd) | 127 s | relay |
| ETH USDC -> native BTC | $500 | lifi | ok | 0.007404 | 39.22 bps (usd) | 823 s | layerswap |
| ETH USDC -> native BTC | $500 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | 1click | ok | 0.742104 | 16.95 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $50,000 | relay | ok | 0.742649 | 9.62 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $50,000 | lifi | ok | 0.741998 | 18.37 bps (usd) | 839 s | layerswap |
| ETH USDC -> native BTC | $50,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | 1click | ok | 3.709921 | 18.56 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $250,000 | relay | ok | 3.696801 | 53.86 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $250,000 | lifi | ok | 3.704598 | 32.89 bps (usd) | 1,392 s | near (= NEAR Intents resold via LI.FI) |
| ETH USDC -> native BTC | $250,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | 1click | ok | 499.893705 | 2.13 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $500 | relay | ok | 499.927685 | 1.45 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $500 | across | ok | 499.943189 | 1.14 bps (raw) | 2 s | across |
| Base USDC -> Arbitrum USDC | $50,000 | 1click | ok | 49,989.895220 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $50,000 | relay | ok | 49,994.977684 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $50,000 | across | ok | 49,994.993189 | 1.00 bps (raw) | 900 s | across |
| Base USDC -> Arbitrum USDC | $250,000 | 1click | ok | 249,949.497300 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $250,000 | relay | ok | 249,974.977698 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $250,000 | across | ok | 249,974.993189 | 1.00 bps (raw) | 900 s | across |


| Corridor | Clip | Headroom | Basis | 1Click rank | Reading |
| :--- | ---: | ---: | :--- | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | +1.93 bps | dest_units | 1/3 | 1Click delivers 1.93 bps more than relay |
| ETH USDC -> SOL USDC | $50,000 | +1.55 bps | dest_units | 1/3 | 1Click delivers 1.55 bps more than relay |
| ETH USDC -> SOL USDC | $250,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> native BTC | $500 | -10.03 bps | dest_units | 2/3 | 1Click trails relay by 10.03 bps |
| ETH USDC -> native BTC | $50,000 | -7.34 bps | dest_units | 2/3 | 1Click trails relay by 7.34 bps |
| ETH USDC -> native BTC | $250,000 | +14.37 bps | dest_units | 1/3 | 1Click delivers 14.37 bps more than lifi |
| Base USDC -> Arbitrum USDC | $500 | -0.99 bps | dest_units | 3/4 | 1Click trails across by 0.99 bps |
| Base USDC -> Arbitrum USDC | $50,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |
| Base USDC -> Arbitrum USDC | $250,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |


- cross_vm: median headroom +1.55 bps over 3 comparable cells
- native_btc: median headroom -7.34 bps over 3 comparable cells
- evm_l2: median headroom -1.02 bps over 3 comparable cells
- competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = 3; per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding): 3.00 bps. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not.

- Where 1Click loses (destination units): eth_usdc_btc at $500 trails relay by 10.03 bps; eth_usdc_btc at $50,000 trails relay by 7.34 bps; base_usdc_arb_usdc at $500 trails across by 0.99 bps; base_usdc_arb_usdc at $50,000 trails across by 1.02 bps; base_usdc_arb_usdc at $250,000 trails across by 1.02 bps.
- Oracle caveat: on eth_usdc_sol_usdc at $500, eth_usdc_sol_usdc at $50,000, eth_usdc_sol_usdc at $250,000, eth_usdc_btc at $500, eth_usdc_btc at $50,000, eth_usdc_btc at $250,000, base_usdc_arb_usdc at $500, base_usdc_arb_usdc at $50,000, base_usdc_arb_usdc at $250,000 the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg comparison there would have been decided by oracles, which is why the ranking uses units.
- Structurally unsupported routes: across on eth_usdc_btc (declared), across on eth_usdc_sol_usdc (ROUTE_NOT_ENABLED).
- LI.FI's quote on eth_usdc_btc $250,000 routes through NEAR Intents itself (tool `near`), so it is 1Click execution plus LI.FI's fee, not an independent price.
- Collector summary: cross_vm (ETH USDC -> SOL USDC): $500: 1Click delivers 1.93 bps more than relay (rank 1/3, destination units); $50,000: 1Click delivers 1.55 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); unsupported: across (ROUTE_NOT_ENABLED). native_btc (ETH USDC -> native BTC): $500: 1Click trails 10.03 bps behind relay (rank 2/3, destination units); $50,000: 1Click trails 7.34 bps behind relay (rank 2/3, destination units); $250,000: 1Click delivers 14.37 bps more than lifi (rank 1/3, destination units); unsupported: across (Across is EVM-only; no Bitcoin route). evm_l2 (Base USDC -> Arbitrum USDC): $500: 1Click trails 0.99 bps behind across (rank 3/4, destination units); $50,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units); $250,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units).

## 8. Concentration and agents on intents.near (NearBlocks receipts)

- Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = **828** (bootstrap 90% CI 769-828) (N_eff = 12.07); over all predecessors 3,809; ex-AI-agent 888 (N_eff 11.26). These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.
- (b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = **4,946** (bootstrap 90% CI 4,335-5,523) (N_eff 2.02) across 96 fill participations in 93 fills (4 atomic token_diff fills, 89 solver-to-settlement-hub legs), 5 distinct solvers; 445 execute_intents receipts decoded, 0 unresolved; the solver sample spans 18,625 s. This is the population the solver_cartelization trigger reads; trigger status: breached.
- AI-agent share of external receipts 11.5% is a NAME-PATTERN classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. Bridge / token-contract share 69.2%; 14 unique external callers in 26 external receipts.
- Sample: 189 unique receipts over 8 NearBlocks pages, blocks 224,473,775-224,473,868, a 53 s window; lifetime receipts on intents.near 156,935,618. A window this short is a point sample, not a market-share estimate; both HHIs move by hundreds of points between runs.
- Method mix: TRANSFER 96, execute_intents 45, ft_on_transfer 18, ft_resolve_withdraw 7, storage_deposit 4, ft_transfer_call 4, do_storage_deposit 3, near_withdraw 3, ft_transfer 3, mt_resolve_withdraw 2.

### 8.1 Deposit / caller concentration (external predecessors)
| Caller | Class | Receipts | Share | Example tx |
| :--- | :--- | ---: | ---: | :--- |
| escrow.ai.near | AI agent | 3 | 11.5% | [FpLStFZBSMwY...](https://nearblocks.io/txns/FpLStFZBSMwYPvJPBLxdAuxjUFTAedXsqFdtiUCZjDqg) |
| eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near | bridge / token contract | 3 | 11.5% | [GbYDDq3z2PpL...](https://nearblocks.io/txns/GbYDDq3z2PpLLLULa7LYSrAYuHQ3dZrvMy7PyDPgBA5x) |
| wrap.near | named account | 3 | 11.5% | [9ve8fk8LRh4z...](https://nearblocks.io/txns/9ve8fk8LRh4z3WxXqT5tWSeKyatTRoZAKzb2hcs6Hg9P) |
| arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near | bridge / token contract | 2 | 7.7% | [7om48ckZt8ti...](https://nearblocks.io/txns/7om48ckZt8ticAFbrM7HPgGJeMP817oQ3xp3QPike8VU) |
| eth.omft.near | bridge / token contract | 2 | 7.7% | [EAnEtknjD6Gv...](https://nearblocks.io/txns/EAnEtknjD6GvpyKtZEKyGo942GuFWr6Udv7TdyCPbPBr) |
| sol.omft.near | bridge / token contract | 2 | 7.7% | [4FMrSTvDkboU...](https://nearblocks.io/txns/4FMrSTvDkboU2PJEQroqbC4dWM4X9M5wGwYtddNC5pms) |
| standin-agent-5705.near | named account | 2 | 7.7% | [FQbBjbaJCBPM...](https://nearblocks.io/txns/FQbBjbaJCBPMV1uAeFUeQQRM858LrZYVeqodqinTXeyx) |
| tron-d28a265909efecdcee7c5028585214ea0b96f015.omft.near | bridge / token contract | 2 | 7.7% | [4MtfuFr5BWXB...](https://nearblocks.io/txns/4MtfuFr5BWXBNdahZiLdEqxveuBFvhB5A7wepDmAXvF5) |
| xrp.omft.near | bridge / token contract | 2 | 7.7% | [FTVMuHbmMk5F...](https://nearblocks.io/txns/FTVMuHbmMk5FNUEkWkCJEus5TY2DRgJZszn6dwUTNacA) |
| arb-0x912ce59144191c1204e64559fe8253a0e49e6548.omft.near | bridge / token contract | 1 | 3.8% | [EkP95EKDgtcP...](https://nearblocks.io/txns/EkP95EKDgtcP7TLtM3Y6Vd6b3pM52UMYCdwRMbFBWAuQ) |
| bnb-0x55d398326f99059ff775485246999027b3197955.omdep.near | bridge / token contract | 1 | 3.8% | [3phUvnbYAo4T...](https://nearblocks.io/txns/3phUvnbYAo4ToqaqNfcKtNGSUuo938Qj4UjiCd1qqLvV) |
| bnb-0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d.omdep.near | bridge / token contract | 1 | 3.8% | [FtNcMX9oiEhF...](https://nearblocks.io/txns/FtNcMX9oiEhFxhEEyP8o5TUdKjtnAkYbQHm7K6DrBDbM) |

### 8.2 Solver concentration (execute_intents signers)
| Solver account | Fill participations | Share | Example tx |
| :--- | ---: | ---: | :--- |
| solver-priv-liq.near | 62 | 64.6% | [55UbdEZCSfaw...](https://nearblocks.io/txns/55UbdEZCSfawJMDKhsAjFhYdf3hnJv8NY4XEAgDRwP4n) |
| solver-multichain-asset.near | 26 | 27.1% | [55UbdEZCSfaw...](https://nearblocks.io/txns/55UbdEZCSfawJMDKhsAjFhYdf3hnJv8NY4XEAgDRwP4n) |
| solver-multichain-asset-2.near | 6 | 6.2% | [HEr8j6p1Kta5...](https://nearblocks.io/txns/HEr8j6p1Kta5Guf3v7siPeo9RnQxmSxTSPpf1JHNP5PU) |
| brlabs-solver.near | 1 | 1.0% | [9bGjNE69AkRo...](https://nearblocks.io/txns/9bGjNE69AkRoUSftp782ygyucoSFrxFi3bFjwhvnDZiU) |
| solver-taler.near | 1 | 1.0% | [6RVhSsjKf3b6...](https://nearblocks.io/txns/6RVhSsjKf3b6A5u4wfsut5DyBvJpnZ2znmBoiZTe5qNV) |

Attribution: fill participation = (a) the solver side of an atomic execute_intents fill (>= 2 token_diff signers; solver = pure token_diff signer when the counterparty bundles a withdrawal, else a signer whose name matches (*solver*, *-liq*, market maker) or that the structure rule identified elsewhere in the sample, else the named account facing an implicit 1Click deposit address), or (b) a transfer intent from a solver to the settlement hub (see settlement_hub.rule); HHI over participations per solver account; transfers that are not solver-to-hub legs are inventory or user moves, not fills. hhi_solver_ci90 is a bias-corrected bootstrap (bootstrap_method): a block bootstrap by NearBlocks page when the sample is stratified in time (bootstrap_resampling = block_by_page), else over sampled units

## 9. Supply physics

### 9.1 Issuance: measured vs nominal
- Measured: 25,683.37 NEAR minted at epoch start 224,437,937 (previous jump 25,685.66 NEAR at 224,394,737); epoch wall time 6.872 h = 1,275.5 epochs/yr; implied annual issuance **32,759,808 NEAR** = 2.4976% of supply.
- Nominal: max_inflation_rate 2.50% x total supply 1,311,650,629 NEAR = 32,791,266 NEAR/yr; measured minus nominal -31,458 NEAR/yr (-0.10%). Daily: measured 89,691 NEAR vs nominal 89,778 NEAR; treasury share 0.0% (validators receive the rest).
- Within-epoch supply drift (net gas burn) -273.01 NEAR/epoch; measured block time 0.573 s. Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.

### 9.2 Daily sinks (NEAR/day, live)
| Sink | NEAR/day | Source | Basis |
| :--- | ---: | :--- | :--- |
| Buyback (holders revenue / price) | 18,389.7 NEAR | measured | $125.8M/day x 16.03 bps gross x alpha 30.5% / $3.34 |
| L1 gas burn | 953.4 NEAR | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| NEP state-lock growth | 342.5 NEAR | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| Total sinks | 19,685.6 NEAR |  | coverage 21.9% of measured issuance; net float 70,006 NEAR/day |


### 9.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)
| Regime (terminal rate) | V* at live take | vs today | V* at competitive ceiling |
| :--- | ---: | ---: | ---: |
| status quo (cap flat) | $604.7M | 4.8x | $3.23B |
| SVRN glidepath | $383.8M | 3.1x | $2.05B |

Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.

### 9.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)
| Regime | Volume path | Issuance/day m1 | Issuance/day m36 | Gross issuance 36m | Sinks 36m | Net float 36m | Flow crossover | Cumulative crossover |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| status quo (cap flat) | run-rate volume | 89,691 NEAR | 96,462 NEAR | 101,944,998 NEAR | 21,570,457 NEAR | 80,374,541 NEAR | none within horizon | none within horizon |
| status quo (cap flat) | +75% YoY volume | 89,691 NEAR | 96,462 NEAR | 101,944,998 NEAR | 52,558,810 NEAR | 49,386,188 NEAR | none within horizon | none within horizon |
| SVRN glidepath | run-rate volume | 89,691 NEAR | 60,705 NEAR | 77,315,355 NEAR | 21,570,457 NEAR | 55,744,898 NEAR | none within horizon | none within horizon |
| SVRN glidepath | +75% YoY volume | 89,691 NEAR | 60,705 NEAR | 77,315,355 NEAR | 52,558,810 NEAR | 24,756,545 NEAR | month 26 | none within horizon |


### 9.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)
| Account | Contract | storage_usage bytes | Locked | Growth B/day | Growth NEAR/day | Window |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| intents.near | yes | 13,691,146,615 | 136,911.5 NEAR | 31,340,173 | 313.40 NEAR | 30.6 d |
| aurora | yes | 14,384,317,587 | 143,843.2 NEAR | 2,907,168 | 29.07 NEAR | 30.6 d |
| wrap.near | yes | 169,043,445 | 1,690.4 NEAR | n/a | n/a | n/a |
| v1.signer | yes | 1,165,054 | 11.7 NEAR | n/a | n/a | n/a |
| escrow.ai.near | no | 428 | 0.0 NEAR | n/a | n/a | n/a |
| treasury.near | yes | 357,895 | 3.6 NEAR | n/a | n/a | n/a |
| meme-cooking.near | yes | 5,958,791 | 59.6 NEAR | n/a | n/a | n/a |
| v2.ref-finance.near | yes | 111,377,110 | 1,113.8 NEAR | n/a | n/a | n/a |

- Total state-locked across 8 tracked contracts: **283,634 NEAR** at 0.01 NEAR/KB (storage_amount_per_byte 10,000,000,000,000,000,000 yocto). Measured lock growth 342.5 NEAR/day over intents.near, aurora (archival available).

### 9.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)
| Regime | Inflation | Nominal APR | Real APR | Buyback accrual | Real APR + accrual | Non-staker real |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| status quo (cap flat) | 2.50% | 5.57% | 3.07% | 0.512% | 3.58% | -1.99% |
| SVRN glidepath | 1.60% | 3.56% | 1.96% | 0.512% | 2.48% | -1.09% |

Live: 343 validators, 588,802,445 NEAR staked = 44.89% of supply.

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
Sampled from 11 NearBlocks windows (1,100 receipts, 344 sign requests) over the trailing 30 days, v1.signer handled 17,543 sign requests/day over 7 days (SE 3,009) and 11,737/day over 30 days (SE 831). Over the 8 windows taken at 00:00 UTC (same time of day), the ln-rate trend is +43% per 30 days (t = 1.18; inconclusive). Callers are concentrated: omni.bridge.near 47%, fast-auth.near 20%, btc-connector.bridge.near 14% of sampled requests; accounts under bridge.near send 69%, so much of this usage is bridging that overlaps Intents' cross-chain flow. A request attaches 1 yoctoNEAR, so the signer earns no fee; requesters pay gas, 0.0022 NEAR per request across sign, respond and callback receipts, 26.2 NEAR/day ($87.51/day), 100% of it burnt (live burnt_gas_reward 0% to the contract), 2.7% of the network gas burn and 0.03% of measured daily issuance (part of the L1 gas burn sink above, not an addition to it). The contract's storage lock is 11.7 NEAR. NearBlocks counts 26,414,399 cumulative v1.signer receipts; the rates are sample estimates, not exact counts.

## 10. Sum-of-the-parts valuation and peer comparables

### 10.1 Engines (percentiles over paths, USD; discounted to today)
| Engine | P10 | P25 | P50 | P75 | P90 | Assumption-heavy |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| clearinghouse | $31.5M | $80.3M | $235.8M | $730.2M | $2.06B | no |
| confidential | $18.7M | $51.5M | $167.9M | $588.1M | $1.81B | yes |
| monetary | $1.2M | $2.8M | $10.3M | $43.3M | $168.7M | yes |

| Total | P10 | P25 | P50 | P75 | P90 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| FDV (all engines) | $130.4M | $276.1M | $698.4M | $1.84B | $4.49B |
| FDV ex-monetary | $123.5M | $262.3M | $663.1M | $1.73B | $4.23B |
| Implied price / NEAR | $0.10 | $0.20 | $0.51 | $1.35 | $3.28 |

Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse $368.7M (53%) + confidential $108.4M (16%) + monetary $221.4M (32%) = $698.5M.

- PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor.
- Same construction on confidential volume at the assumed confidential take; terminal multiple x confidential_multiple_haircut because nearstats flags confidential TVL as unverified. Starting confidential share 10.2% is an on-chain estimate from Confidential Intents Treasury boundary flows (intents_forensics.volume.confidential_share_estimate), not nearstats' rejected split.
- PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.

### 10.2 Calibration (what the engines were fed)
| Parameter | Value | Source / basis |
| :--- | :--- | :--- |
| Public take t=0 (gross) | 15.57 bps | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d |
| Blended gross take / net take | 16.03 bps / 4.88 bps | DefiLlama near-intents fees / volume; net = gross x alpha |
| Capture ratio alpha | 30.47% | measured:defillama near-intents dailyHoldersRevenue / fees |
| Confidential take t=0 | 20 bps | assumption: registry confidential_take_bps (1Click confidential quotes need partner authentication) |
| Public take floor | 1.55 bps | derived; cross-VM headroom +1.55 bps, competitor ceiling 3.00 bps |
| Compression lambda (public / confidential) | 0.030 / 0.010 per month | geometric reversion to the floor |
| Volume growth (public / confidential, monthly) | 4.78% / 10.06% | confidential share 10.2% -> 40% target (start share ESTIMATED ON-CHAIN from Confidential Intents Treasury boundary flows) |
| Sigma: price (annual) / volume (monthly) | 1.026 / 0.347 | measured: monthly log-return sigma of 30-day volume aggregates; confidential sigma x 1.00 |
| Terminal multiple (FDV / annual holder revenue) | 60.0x (raw 2,543.9x) | source derived: peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; clipped to registry guardrails |
| Discount rate | 25% | assumption |
| Supply at horizon (glidepath) | 1,367,395,527 NEAR | fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory) |
| Current FDV | $4.38B | spot price x on-chain total_supply at the snapshot block; CoinGecko FDV via nearstats $4.38B (-0.07% gap, struck at a different instant; cross-check only) |
| GBM convention | mean-matching (Ito) | mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM uses the same convention (zero drift => E[P_t] = P_0) |
| Terminal public volume, month H | mean $606.1M/day; median $69.1M/day | start $113.0M/day; MC sample mean $535.1M, median $66.9M; the labeled YoY growth is the growth of the MEAN path |


### 10.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)
| Protocol | Fees 30d | Revenue 30d | FDV | FDV/fees | FDV/revenue | Revenue methodology (live text) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| SOL (solana) | $16.2M | $1.6M | $48.38B | 244.8x | 2,543.9x | Transaction base fees paid by users |
| ETH (ethereum) | $19.8M | $6.2M | $232.71B | 963.8x | 3,081.7x | Amount of ETH burned — base fees plus blob fees (both are permanently burned, accruing to no proposer) |
| HYPE (hyperliquid) | $90.5M | $69.3M | $65.92B | 59.9x | 78.1x | Parent aggregates child protocols. Hyperliquid Perps: 99% of fees go to Assistance Fund for buying HYPE tokens |
| NEAR (near) | $129,456 | $90,620 | $4.44B | 2,816.5x | 4,023.5x | 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract developers |
| NEAR (near-intents) | $5.8M | $1.8M | $4.44B | 62.5x | 201.7x | NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.ne |
| NEAR (near_combined) | $6.0M | $1.9M | $4.44B | 61.2x | 192.1x | near: 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract deve |

- Median ex-NEAR FDV / annualized revenue 2,543.9x (n = 3); FDV / annualized fees 244.8x (n = 3). annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)
- `revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live methodology text is carried in the table so the multiple is read with its definition.

### 10.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take (SVRN glidepath; * = net-deflationary)
| Net take \ Volume/day | $100.0M | $250.0M | $500.0M | $1.00B | $1.50B |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2 bps | $272.5M | $622.6M | $1.21B | $2.37B* | $3.54B* |
| 6 bps | $739.3M | $1.79B | $3.54B* | $7.04B* | $10.54B* |
| 10 bps | $1.21B | $2.96B* | $5.87B* | $11.71B* | $17.54B* |
| 14 bps | $1.67B | $4.12B* | $8.21B* | $16.38B* | $24.54B* |
| 18 bps | $2.14B | $5.29B* | $10.54B* | $21.04B* | $31.55B* |

Current FDV $4.38B; confidential share used in the split 10.2%. Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).

### 10.5 Out-of-sample backtest of the volume engine
At each of 20 monthly origins from 2025-03-23 to 2026-10-14 the volume GBM was re-calibrated on data up to the origin only (trailing 30-day volume, sigma from the trailing 365 days, drift = public_volume_growth_yoy 75%) and its P10-P90 band for 30-day volume was compared with what happened (defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json), 2024-12-10 to 2026-11-13). The test of 80% coverage fails at 1m, 3m, 6m (exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10). At 1 month the median realized volume is 1.33x the forecast median: the model under-predicts. Split at the middle origin (2026-01-17), coverage before: 1m 20% (n = 10), 3m 20% (n = 10), 6m 30% (n = 10); from it: 1m 90% (n = 10), 3m 100% (n = 7), 6m 100% (n = 4). 23 of the 24 misses come from origins before the split; 24 of 24 are realized volume above P90. With the drift replaced by the trailing mean log return (no registry input) coverage is 1m 60%, 3m 41%, 6m 21%. Not backtested: fee take rate (public and confidential) and its compression toward the floor; holder capture ratio alpha; confidential share of volume and its drift to the target share; terminal FDV/revenue multiple and discount rate; NEAR price and supply paths. 3- and 6-month forecasts from monthly origins overlap, so their errors are correlated and the binomial interval overstates the precision.

| Horizon | n | P10-P90 coverage [90% Wilson] | Binomial p vs 80% | Below P10 / above P90 | Median realized / P50 | PIT histogram (5 bins) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 1 month | 20 | 55% [37%-72%] | 0.01 | 0 / 9 | 1.33x | 1 4 2 2 11 |
| 3 months | 17 | 53% [34%-71%] | 0.01 | 0 / 8 | 1.84x | 0 2 2 4 9 |
| 6 months | 14 | 50% [30%-70%] | 0.01 | 0 / 7 | 3.57x | 1 0 3 1 9 |


## 11. Bear case and early-warning triggers

Value basis: deterministic at median inputs; not a Monte Carlo percentile. Base deterministic FDV (median inputs) $2.30B, implied price $1.68; the Monte Carlo P50 of section 10 is a different statistic and is not what the drawdowns below are measured against. drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed

| Scenario | Deterministic FDV (median inputs) | FDV drawdown | Implied price | Price drawdown | Flow crossover |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fee_race_to_zero | $389.1M | -83.1% | $0.28 | -83.1% | none within horizon |
| governance_stalemate | $2.30B | +0.0% | $1.65 | -1.8% | none within horizon |
| post_incentive_decay | $921.3M | -60.0% | $0.67 | -60.0% | none within horizon |
| solver_cartelization | $1.38B | -39.8% | $1.01 | -39.8% | month 35 |
| combined worst | $227.8M | -90.1% | $0.16 | -90.3% | none within horizon |


### 11.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)
| Scenario | Metric | Now | Trigger | Status | Monitor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| fee_race_to_zero | net_take_bps_30d | 4.88 bps | < 3.00 bps | not breached | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue (sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days). |
| governance_stalemate | max_inflation_rate | 2.50% | > 1.60% | **BREACHED** | https://free.rpc.fastnear.com (EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)). Note: breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted |
| post_incentive_decay | volume_30d_vs_record_30d | -21.5% | <= -40.0% | not breached | https://nearstats.org/api/near/summary (intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1). |
| solver_cartelization | hhi_solver | 4,946 | > 3,500 | **BREACHED** | https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50 (HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)); secondary headroom_cross_vm_bps +1.55 bps < 0 bps (not breached). Note: sample: 96 solver fill participations over 18,625 s; HHI_solver 4,946, bootstrap 90% CI [4,335, 5,523] (CI lower bound 4,335 > 3,500: breached); deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = 828 |


### 11.2 Scenario narratives
**Aggregator bypass: public take races to 1 pip.** Third-party frontends route around near.com and the public gross take collapses from 15.6 bps to 0.01 bps (the bare intents.near contract fee); confidential execution reprices from 20 bps to 5 bps. Capture ratio alpha is held at 30%, so the hit is price, not allocation. Deterministic (median-input) FDV -83.1% to $389.1M; implied price $0.28. Evidence against it: live cross-VM headroom is +1.5 bps, so a bypassing frontend must first give up that execution edge. Trigger: DefiLlama 30d net take (gross x alpha) below 3.0 bps (now 4.9 bps).

**Governance stalemate: 2.5% issuance forever.** Validators never enact the SVRN cut: max_inflation_rate stays at 2.50% for the full horizon instead of gliding to 1.60%. Protocol cash flows do not change, so FDV moves +0.0%; the damage is dilution: 24,629,644 more NEAR outstanding at the horizon and a per-token value of $1.65 (-1.8% vs base). Net-float crossover: none within horizon (base: month 29). This scenario is live today: the on-chain cap reads 2.50% and no cut has been enacted.

**Post-incentive volume decay (NEAR@3.33 unwind).** Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume $113.0M -> $45.2M (-60%), confidential $12.8M -> $3.8M (-70%) and confidential TVL x0.3 (nearstats flags that TVL unverified). Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV -60.0% to $921.3M; implied price $0.67. Current 30d volume $3.80B is 79% of the 30d record $4.84B; the trigger fires at -40%.

**Solver cartelization: HHI_solver > 3,500, 1Click loses the spread.** Two market makers take most fills (HHI_solver > 3,500) and spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM (headroom -2 bps). Keeping flow costs the same 2 bps of take (15.6 bps -> 13.6 bps) while compression runs at 0.15/month. Deterministic (median-input) FDV -39.8% to $1.38B; implied price $1.01. Live: HHI over solver fill participations 4,946 (2.0 effective solvers across 96 fill participations), bootstrap 90% CI [4,335, 5,523]; deposit-source HHI over external predecessors 828 (not a solver measure); cross-VM headroom +1.5 bps; trigger at HHI_solver > 3,500 or headroom < 0.

### 11.3 Falsification summary
fee_race_to_zero: public gross take at 0.01 bps and confidential at 5 bps puts the deterministic FDV at $389.1M (-83.1%); watch DefiLlama near-intents 30d net take weekly, trigger < 3.0 bps, now 4.9 bps (not breached). governance_stalemate: no SVRN cut (cap 2.50% for 36 months) leaves the deterministic FDV at $2.30B (+0.0%) but dilutes per-token value to $1.65 (-1.8%) with crossover none within horizon; watch max_inflation_rate in EXPERIMENTAL_protocol_config, trigger > 1.60%, now 2.50% (BREACHED). post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at $921.3M (-60.0%); watch nearstats 30d volume against its 30d record weekly, trigger <= -40%, now -21.5% (not breached). solver_cartelization: HHI_solver > 3,500 with cross-VM headroom at -2 bps puts the deterministic FDV at $1.38B (-39.8%); watch the execute_intents solver HHI (now 4,946) and the live quote-race headroom (now +1.5 bps) weekly (BREACHED). All four at once: deterministic FDV $227.8M (-90.1% vs base $2.30B); 2 of 4 measured triggers currently breached, and the thesis is falsified if any trigger holds for 30 consecutive days.

## 12. Further evidence: take-rate history, size limits, fee share, wider peers

### 12.1 Fee-pool share against competing cross-chain routers

**NEAR Intents takes 21.0% of the six-protocol cross-chain fee pool over the 30 days to 2026-11-12, rank 2 of 6 behind Relay at 54.2%; its rolling 30-day share moved from 35.0% to 21.0% over 173 days (low 2.5% on 2026-09-13, high 45.3% on 2026-07-04) and the linear trend (-6.47 pp per 30 days, 90% interval -9.42 to -3.53) is falling, with the interval excluding zero.**

Cuts against the bull case: NEAR Intents is losing share of the fees these routers collect, so fee growth has to come from the pool growing, not from share capture. It is overturned by a positive share trend whose 90% interval excludes zero. Relay collects 2.6x NEAR Intents' fees under its own adapter's definition. NEAR Intents' own 30-day fees went from $2.90M to $6.05M over the window; the pool went from $8.30M to $28.85M. With Relay excluded the share is 45.7% against 48.8% at the start of the window (-0.95 pp per 30 days, 90% interval -1.73 to -0.17).

| Rank | Protocol | 30d fees | Share | 90d fees | Days of data | Fee definition (adapter text) |
| ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| 1 | Relay | $15.62M | 54.2% | $260.87M | 204 | Platform fees, integrator app fees and swap costs paid by users on Relay bridges and swaps, excluding execution costs (network gas). |
| 2 | **NEAR Intents** | $6.05M | 21.0% | $19.10M | 552 | Gross fees charged on NEAR Intents swaps - the protocol fee plus the affiliate (distribution) fee each frontend collects, summed across all integra... |
| 3 | THORChain DEX | $3.64M | 12.6% | $8.33M | 2042 | Slip-based liquidity (swap) fees paid by users on each chain's THORChain pools, gross outbound fees and slashing fees paid into the Reserve, and af... |
| 4 | Chainflip | $2.97M | 10.3% | $6.30M | 1045 | Chainflip AMM: Includes Swap, Broker, Ingress, Egress and Network Fees for Buy/Burn Mechanism |
| 5 | deBridge | $458.9K | 1.6% | $1.58M | 1322 | All fees paid by users for swap and bridge tokens via deBridge. |
| 6 | Across | $102.4K | 0.4% | $292.7K | 1290 | Total fees paid by users for bridge txs. |


| NEAR Intents rolling 30d share | Now | 30 days ago | 90 days ago | Window start |
| :--- | ---: | ---: | ---: | ---: |
| All included protocols | 21.0% (2026-11-12) | 11.0% (2026-10-13) | 14.0% (2026-08-14) | 35.0% (2026-05-23) |
| Relay excluded | 45.7% (2026-11-12) | 58.9% (2026-10-13) | 55.2% (2026-08-14) | 48.8% (2026-05-23) |


Trend of the rolling share: -6.47 pp per 30 days, 90% interval -9.42 to -3.53 (174 points, Newey-West 60 lags, R^2 0.59). Relay excluded: -0.95 pp per 30 days, 90% interval -1.73 to -0.17. Daily share, no overlap: -4.62 pp per 30 days, 90% interval -7.10 to -2.14. Excluding THORChain DEX (zero-fee run in the window): share 24.0% now against 41.6% at window start, trend -6.73 pp per 30 days, 90% interval -9.86 to -3.60.

Window: 2026-04-24 to 2026-11-12 (203 days common to all 6 protocols, set by Relay's first day). Trailing days left out as not final: 2026-11-13, 2026-11-14. Source: DefiLlama `summary/fees/<slug>?dataType=dailyFees`; records `defillama/fee_pool:<slug>:dailyFees` in the manifest.

Limits:

- Fee share is not volume share: a router charging more per dollar routed has a larger fee share at the same volume. DefiLlama's bridge-volume API is paid, so no volume-side comparison is made here.
- Adapter fee definitions differ, so the pool sums unlike quantities; each adapter's own text is quoted next to its protocol (`protocols[].methodology_fees`). The ex-Relay share is published because Relay's adapter counts integrator app fees and swap costs.
- The common window is 203 days (2026-04-24 to 2026-11-12), set by Relay's first day; the trend describes these months only.
- Routers outside DefiLlama's fee coverage (LI.FI and other aggregators) are absent, so the pool is these six protocols, not the cross-chain market.
- Rolling 30-day points overlap by 29 days; the interval uses a Newey-West error with 60 lags, and the daily non-overlapping share trend is reported as a cross-check.
- THORChain is measured by DefiLlama's `thorchain-dex` adapter (swap, outbound and affiliate fees); the `thorchain` slug is the chain's native transaction fee and is not a routing fee.
- The share path is not a line: it ranged from 2.5% (2026-09-13) to 45.3% (2026-07-04) and the linear trend explains 59% of its variance. Read the slope as the average drift over the window, not as a forecast.
- Relay's 30-day fees peaked at $205.95M on 2026-09-22, 13.2x its window median of $15.62M. NEAR Intents' share around that date moves with that surge in the denominator, not with a change in its own fees. Whether the surge is user-paid routing fees or an adapter artefact cannot be settled from this endpoint.
- THORChain DEX reports zero fees on 38 days of the window (longest run 37 days, 2026-05-16 to 2026-06-21). The zeros are kept as reported; if they are an adapter gap, the other protocols' shares are overstated for rolling windows that include those days. See the robustness share excluding it.

### 12.2 Size limits: the largest clip each router quotes

**1Click stops quoting at a smaller size than a competitor on 3 of 3 corridors: ETH USDC -> SOL USDC, $500K against LI.FI $5M; ETH USDC -> native BTC, $500K against LI.FI $1M (routed through NEAR Intents); Base USDC -> Arbitrum USDC, $500K against LI.FI $5M.**

Dry quotes at $1K, $10K, $50K, $250K, $500K, $1M, $2.5M, $5M on each benchmarked corridor, run 2026-11-14T06:05:16.718Z: 59 quoted, 21 refused, 0 errors, 0 not attempted, 8 on routes the venue does not serve (88 cells, 33.221 s against a 75.0 s budget).

| Corridor | Venue | Largest size quoted | Cost at $250K | Cost at largest size | First size refused |
| :--- | :--- | ---: | ---: | ---: | ---: |
| ETH USDC -> SOL USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| ETH USDC -> SOL USDC | Relay | $1M | 3.00 bps | 3.00 bps | $2.5M |
| ETH USDC -> SOL USDC | LI.FI | $5M | 25.00 bps | 25.00 bps | none on the ladder |
| ETH USDC -> SOL USDC | Across | does not route | n/a | n/a | n/a |
| ETH USDC -> native BTC | 1Click | $500K | 18.25 bps | 23.17 bps | $1M |
| ETH USDC -> native BTC | Relay | $250K | 33.73 bps | 33.73 bps | $500K |
| ETH USDC -> native BTC | LI.FI | $1M | 32.18 bps | 142.83 bps via NEAR Intents | $2.5M |
| Base USDC -> Arbitrum USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| Base USDC -> Arbitrum USDC | Relay | $2.5M | 1.00 bps | 1.00 bps | $5M |
| Base USDC -> Arbitrum USDC | LI.FI | $5M | 25.00 bps | 25.00 bps | none on the ladder |
| Base USDC -> Arbitrum USDC | Across | $500K | 1.00 bps | 1.00 bps | $1M |


Cost: (amount in - amount out) / amount in x 1e4: on raw units where both legs are the same stablecoin, else on USD legs valued at one common price per cell (1Click token-list oracle, else the median of the venues' implied prices), as in execution_bench.

On this run 1Click quoted at least $1M on 0 of 3 corridors and stopped below a competitor on 3. That cuts against the case that the solver network already carries institutional clips on those routes: fee growth there has to come from retail-size flow until solver inventory deepens. On ETH USDC -> native BTC the largest competitor quote (LI.FI $1M) is 1Click execution resold; the largest quote on an independent route was $250K (Relay). Repeated runs in which 1Click quotes the same rungs its competitors do would overturn this reading.

Limits:
- A dry 'no liquidity' reflects the solvers' quoting policy at that moment. It is not proven hard depth, and a dry quote is not a fill.
- One run is one observation. Solver inventory and venue limits move within minutes; re-run before relying on a rung.
- Every figure is the largest size quoted on an eight-rung ladder ($1K to $5M), not depth. Sizes between two rungs were not observed.
- Cells marked not attempted did not complete inside the time budget. They carry no information about liquidity.

Raw responses: ledger records `ladder:<venue>:<corridor_id>:<size_usd>`; data in `snapshot.liquidity_ladder`.

### 12.3 Wider peer set: FDV to revenue across the top revenue chains

**The 60x terminal multiple cap sits at the 20th percentile of 15 peers (3 of 15 trade at or below it) on FDV to annualised 30-day revenue; the wide median is 521x (bootstrap 90% interval 223x to 968x), and NEAR on L1 gas revenue alone trades at 4,024x, the 87th percentile.**

The cap is at or below the upper quartile of the set (1,756x), so the model's terminal value does not rest on a multiple richer than what the market pays for chain revenue today. On L1 gas revenue alone NEAR (4,024x) is priced above the wide median (521x), so NEAR is not cheap on chain revenue; the long-term case has to be carried by Intents revenue, not by the L1 multiple. This reading is overturned if a re-run puts the cap above the 75th percentile of the set (peer multiples compressing toward 60x) or if the set shrinks below 8 peers.

| Chain | Token | Revenue, 30d | Revenue, annualised | FDV | FDV / revenue | Note |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| Dexalot | ALOT | $109,078 | $1.3M | $3.2M | 2.4x | DefiLlama types this adapter 'protocol', not 'chain': its revenue is not plain chain gas revenue |
| Quai | QUAI | $165,020 | $2.0M | $7.5M | 3.7x | revenue is merged-mining block rewards earned on other chains and spent on QUAI buyback and burn (the adapter's own Fees text), not gas paid on Quai |
| **Model floor** |  |  |  |  | **8x** | terminal_multiple_floor (assumption) |
| Polygon | POL | $1.6M | $19.3M | $888.8M | 46.1x |  |
| **Model cap** |  |  |  |  | **60x** | terminal_multiple_cap (assumption); the multiple the model uses |
| Tron | TRX | $24.5M | $298.0M | $29.71B | 99.7x |  |
| **NEAR (L1 + Intents, the model's basis)** | NEAR | $1.9M | $23.1M | $4.44B | **192x** | comps.near_combined; not like for like (no peer row includes app revenue) |
| Arbitrum | ARB | $521,624 | $6.3M | $1.42B | 223x | L2 governance token: sequencer revenue accrues to the DAO treasury, not to ARB by protocol rule |
| Aptos | APT | $121,805 | $1.5M | $635.4M | 429x |  |
| Injective | INJ | $136,671 | $1.7M | $814.9M | 490x |  |
| Monad | MON | $259,128 | $3.2M | $1.64B | 521x |  |
| ICP | ICP | $172,496 | $2.1M | $1.36B | 646x |  |
| Avalanche | AVAX | $347,711 | $4.2M | $3.82B | 904x |  |
| Filecoin | FIL | $115,298 | $1.4M | $1.36B | 968x |  |
| Solana | SOL | $1.6M | $19.0M | $48.38B | 2,544x |  |
| Ethereum | ETH | $6.2M | $75.5M | $232.71B | 3,082x |  |
| **NEAR (L1 gas revenue only)** | NEAR | $90,620 | $1.1M | $4.44B | **4,024x** | subject, not counted in the set |
| BSC | BNB | $1.2M | $14.4M | $81.59B | 5,683x | exchange-linked token: BNB's FDV also prices Binance exchange utility, not only BNB Chain's fee burn |
| Hyperliquid L1 | HYPE | $859,284 | $10.5M | $65.92B | 6,305x | chain row covers HyperEVM gas only; HYPE's FDV is priced mostly on the HyperCore exchange, whose revenue DefiLlama books under separate Hyperliquid protocols (the model's three-peer set uses that parent) |

Distribution of FDV / revenue across 15 peers: median 521x (bootstrap 90% interval 223x to 968x; 10,000 resamples, seed 20261114), P25 161x, P75 1,756x, IQR 1,594x, range 2.4x to 6,305x. The 60x cap: 3 of 15 peers at or below it (20th percentile). The 8x floor: 2 of 15 (13th percentile). NEAR on L1 gas revenue only: 4,024x, the 87th percentile; on the model's combined L1 + Intents basis 192x, which would be the 27th percentile (not like for like).

Without the 5 flagged rows (10 peers): median 584x, P25 444x, P75 952x; 1 at or below the cap. For contrast, the three-peer median the model uses (Solana, Ethereum, Hyperliquid) is 2,544x (comps.median_fdv_to_revenue_ex_near), which the model clips to the 60x cap.

Inclusion rules (fixed before any multiple was computed):
- Universe: every DefiLlama fees-overview row with category 'Chain' and 30-day revenue (dataType=dailyRevenue) above zero.
- Ranking: by 30-day revenue, highest first. No chain is added or removed by hand after seeing its multiple.
- Peers: the first 15 chains in that ranking that have their own token with a CoinGecko fully diluted valuation.
- Excluded, each listed with its reason: chains with no native token; chains whose token has no FDV on CoinGecko; chains not in the chain-to-token mapping table (configuration in wide_peers.py); a second row for a token already counted.
- Flagged, not dropped: L2 tokens, exchange-linked tokens, rows whose adapter books something other than chain gas revenue and rows whose DefiLlama adapter is not typed 'chain'. They stay in the distribution; a sensitivity without them is reported next to it.
- NEAR is the subject. It is positioned against the set on the same basis (its own chain row and CoinGecko FDV) and is not counted in it.
- Multiple: FDV / (30-day revenue x 365 / 30). Percentile of a value: share of peers with a multiple at or below it.

Excluded inside the cut (2); 52 further chains rank below the last peer and were not evaluated:
- Base (rank 3 by revenue, $2.6M in 30 days): no native token: Coinbase-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.
- Robinhood Chain (rank 7 by revenue, $1.1M in 30 days): no native token: Robinhood-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.

Caveats:
- FDV to revenue on 30 days annualised is noisy: one busy or quiet month moves a chain's multiple by a large factor.
- Revenue definitions differ by chain adapter (burned base fees, sequencer profit, treasury share, buyback and burn); the adapter's own text is carried per row.
- Token FDV for an L2 or an exchange-linked token does not accrue chain revenue the way an L1 gas token does; those rows are flagged and a sensitivity without them is shown.
- Selection: ranking by revenue picks the chains with the most revenue, which pulls their multiples down relative to the long tail of low-revenue chains.
- NEAR's multiple here uses L1 gas revenue only. The model values NEAR on L1 plus Intents revenue (comps.near_combined), which no peer row here has an equivalent of.
- One snapshot. Nothing here is a time series, and the cap's position will move with token prices and monthly fee volume.

Sources: `defillama/overview:fees:dailyRevenue` sha256 `1cad57b758c623e1`, `coingecko/coins_markets_wide` sha256 `08c2fb1442807b5c`; fetched 2026-11-14T06:05:11.296Z. Field: `snapshot.wide_peers`.

### 12.4 Take-rate history

Gross take compressed over the trailing year: the rolling 30-day rate is 16.0 bps on 2026-11-12 against 16.6 bps a year earlier, while average daily volume went from $88M to $126M; the trailing-365d log-linear trend is -30% per year (90% CI -42% to -16%), which excludes zero, and the trailing-180d trend, +25% per year (90% CI -8% to +71%), does not show the decline continuing.

| Window | Days (UTC) | Gross take (bps) | Net take (bps) | Holder take (bps) | Avg daily volume |
| :--- | :--- | ---: | ---: | ---: | ---: |
| last 30d | 2026-10-14 to 2026-11-12 | 16.03 | 4.88 | 4.88 | $126M |
| 30-60d ago | 2026-09-14 to 2026-10-13 | 17.02 | 4.75 | 4.75 | $160M |
| 60-90d ago | 2026-08-15 to 2026-09-13 | 13.29 | 2.93 | 2.93 | $122M |
| 150-180d ago | 2026-05-17 to 2026-06-15 | 12.37 | 3.46 | 3.46 | $84M |
| 330-360d ago | 2025-11-18 to 2025-12-17 | 24.29 | 1.42 | 0.00 | $87M |


- **Trend, trailing 365 days** (2025-11-13 to 2026-11-12, 365 rolling points): -30.3% per year, 90% CI -42.5% to -15.6% (excludes zero; Newey-West, 60-day lag).
- **Trend, trailing 180 days** (2026-05-17 to 2026-11-12, 180 rolling points): +25.2% per year, 90% CI -8.3% to +70.8% (includes zero; Newey-West, 60-day lag).
- **Trend, full history** (2025-06-08 to 2026-11-12, 523 rolling points): +86.3% per year, 90% CI -2.1% to +254.2% (includes zero; Newey-West, 60-day lag). Dominated by the 2025 fee ramp from zero; not a competition signal.
- **Robustness of the trailing-365d trend** (reported, not graded): 30-day lag -41.9% to -16.4%; 120-day lag -41.2% to -17.4%; 13 non-overlapping 30-day windows -26.8% per year, Student-t 90% CI -43.1% to -5.9%.
- **Elasticity to volume, trailing 365 days** (365 days, 0 dropped for zero fees or volume): a 1% rise in daily volume goes with a -0.04% change in daily gross take, 90% CI -0.13 to +0.05 (includes zero; R2 0.00).
- **Elasticity to volume, full history** (543 days, 9 dropped for zero fees or volume): a 1% rise in daily volume goes with a +0.70% change in daily gross take, 90% CI +0.20 to +1.20 (excludes zero; R2 0.36).
- **Regime break** (first aligned day with dailyHoldersRevenue > 0): 2026-02-23. Pooled gross take 17.49 bps over the 289 days before (19.07 bps over the 102 of those inside the trailing year) and 15.48 bps over the 263 days since; net take 1.54 bps before (trailing year) and 3.38 bps since.
- **Range, trailing 365 rolling points**: gross take high 24.49 bps (2025-12-16), low 11.82 bps (2026-06-22).
- **Floor read** (trailing 365 rolling points): gross take was below the 0.5 bps model floor on 0 of them (minimum 11.82 bps, 2026-06-22); net take was below the 3 bps fee-race trigger on 280 (minimum 0.00 bps, 2025-12-31), and on 149 of the 234 windows that start after the regime break.

**Read.** This cuts against the bull case: gross take fell at 30% per year over the trailing year with an interval that excludes zero (non-overlapping check: -27% per year, 90% CI -43% to -6%, also excludes zero), so the claim that pricing power has held while volume grew is not supported by the fee history; the level is still 32x the 0.5 bps model floor. The trailing-180d trend is +25% per year (90% CI -8% to +71%): the decline is not visible in the last six months. A trailing-365d interval that includes zero again would overturn this read; a 180d interval wholly below zero would show compression still in progress. NEAR's captured (net) take went from 2.2 bps to 4.9 bps over the same span and sat under the 3 bps fee-race trigger on 280 of 365 trailing rolling points.

Data: 552 aligned settled days 2025-05-10 to 2026-11-12 (raw); unsettled trailing day(s) excluded: 2026-11-13. Source: defillama/fees:near-intents:dailyFees sha256 9d63a8420453...; defillama/fees:near-intents:dailyRevenue sha256 eece69a9b079...; defillama/fees:near-intents:dailyHoldersRevenue sha256 0e61279bd524...; defillama/dexs:near-intents sha256 ae314ea97a8b....

Limits:
- Early history mixes fee regimes: the DefiLlama fee chart ramps from zero in mid-2025 and net revenue is zero until the first sweep, so the full-history trend measures fees being switched on. Read the trailing-365d figures.
- Fees, revenue and holders revenue follow DefiLlama's near-intents adapter definitions: gross fees include the affiliate fee each frontend keeps; revenue is NEAR swept into the revenue wallets and is booked on the sweep day, so net take is lumpy and can exceed fees on single days. An adapter revision restates the whole series.
- Rolling 30-day points overlap (29 of 30 days shared), so about 12 independent observations sit in a year. A Newey-West interval on such points is too narrow at this sample size: in the seeded null simulation in quant/tests/test_take_rate_series.py a trendless series is flagged well above the nominal 10% of the time. The non-overlapping 30-day check (Student-t) stays near its nominal size and is the stricter read: treat a trend as established only when both intervals exclude zero. An interval that includes zero means no decline was detected, not that none exists.
- The elasticity regresses fees/volume on volume: noise in daily volume enters both sides and pushes the estimate negative.

### 12.5 Volume engine: GBM against a block bootstrap, out of sample

The block bootstrap does not repair the volume engine: P10-P90 coverage (1m 19/20 (95%, p 0.16), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33)) is rejected against 80% for over-coverage at 3m; the pass at 1m and 6m rests on about 20 origins, which is weak evidence; its band is 3.1x to 8.0x the GBM's log width, so it covers by being wide, not by being sharp; the GBM is rejected at 3 of 3 horizons (1m 11/20 (55%, p 0.01), 3m 9/17 (53%, p 0.01), 6m 7/14 (50%, p 0.01)), so the two engines bracket realized dispersion and neither is calibrated.

| Engine | Horizon | n | Inside | Coverage | Binomial p vs 80% | Below P10 / above P90 | Realized / median | Band width, ln(P90/P10) | Verdict |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| GBM, registry drift (valuation engine) | 1m | 20 | 11/20 | 55% | 0.010 | 0 / 9 | 1.33x | 0.88 | 80% rejected |
| GBM, registry drift (valuation engine) | 3m | 17 | 9/17 | 53% | 0.01 | 0 / 8 | 1.84x | 1.11 | 80% rejected |
| GBM, registry drift (valuation engine) | 6m | 14 | 7/14 | 50% | 0.01 | 0 / 7 | 3.57x | 1.25 | 80% rejected |
| Block bootstrap, resampled drift | 1m | 20 | 19/20 | 95% | 0.16 | 0 / 1 | 0.75x | 2.70 | 80% not rejected |
| Block bootstrap, resampled drift | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.39x | 6.40 | 80% rejected |
| Block bootstrap, resampled drift | 6m | 14 | 13/14 | 93% | 0.33 | 1 / 0 | 0.10x | 9.96 | 80% not rejected |
| Block bootstrap, registry drift (shape only) | 1m | 20 | 13/20 | 65% | 0.10 | 0 / 7 | 2.40x | 2.60 | 80% rejected |
| Block bootstrap, registry drift (shape only) | 3m | 17 | 5/17 | 29% | <0.001 | 0 / 12 | 61.97x | 6.32 | 80% rejected |
| Block bootstrap, registry drift (shape only) | 6m | 14 | 0/14 | 0% | <0.001 | 0 / 14 | 22115.22x | 9.93 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 1m | 20 | 19/20 | 95% | 0.16 | 0 / 1 | 0.73x | 3.08 | 80% not rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.38x | 7.89 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 6m | 14 | 14/14 | 100% | 0.09 | 0 / 0 | 0.09x | 12.78 | 80% rejected |


Target coverage 80%; verdict rule: exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10. Bootstrap: 10,000 paths per origin, seed 20261114, mean block length 7 to 58 days across origins (median 11). At 1 month the bootstrap band is 3.07x the GBM band in log width. At 3 months the bootstrap band is 5.75x the GBM band in log width. At 6 months the bootstrap band is 7.96x the GBM band in log width.

Power at one month (n = 20): the test accepts 14 to 19 forecasts inside the band. A model whose true coverage is 60% would be rejected 75% of the time and one at 70% only 39% of the time, so a pass does not separate a calibrated engine from a mildly miscalibrated one.

Valuation effect, volume. The valuation uses the GBM; this is unchanged. From the latest origin (2026-11-13, trailing 30-day volume $3.80B), 30-day volume 12 months ahead as a multiple of current, P10 / P50 / P90: GBM 0.18x / 0.85x / 3.97x; bootstrap with the same expected path 0.08x / 0.51x / 3.49x; bootstrap with its own resampled drift 0.24x / 1.52x / 10.36x.

Valuation effect, FDV. Feeding bootstrap volume paths (same expected path, same price, take-rate and issuance paths, 10,000 paths) through the Monte Carlo gives FDV P10 / P50 / P90 of $53M / $382M / $3.92B against the base $130M / $698M / $4.49B (0.41x / 0.55x / 0.87x of base). The base run reproduces `sotp.fdv_percentiles` exactly. The bootstrap run holds the mean volume path fixed, so its lower median is the convexity cost of a wider distribution. These are variant figures; no headline number uses them.

The valuation uses the GBM. At the same expected path the bootstrap puts 30-day volume 12 months out at 0.08x / 0.51x / 3.49x of current (P10 / P50 / P90) against the GBM's 0.18x / 0.85x / 3.97x, a band 1.2x as wide in log terms; through the same Monte Carlo FDV P10 / P50 / P90 becomes 0.41x / 0.55x / 0.87x of the base. The backtest rejects the bootstrap for over-coverage, so read this as a stress bound on volume dispersion (with the mean path held fixed, a wider distribution lowers the median), not as a better central estimate.

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
| NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB) | **VERIFIED_ON_CHAIN** | intents.near storage_usage 13,691,146,615 bytes = 136,911 NEAR locked; 283,634 NEAR across 8 tracked contracts | near_rpc/view_account:intents.near sha256 e1db87b5a820... @ block 224,473,852; storage_amount_per_byte from EXPERIMENTAL_protocol_config | high | growth 31,340,173 B/day = 313.4 NEAR/day over 30.6 d (archival); a 0.01 NEAR/KB lock is released if state is deleted, so it is a sink while state grows |
| Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap | **VERIFIED_ON_CHAIN** | 25,683.37 NEAR minted at epoch start 224,437,937 x 1,275.5 epochs/yr = 32,759,808 NEAR/yr (2.4976%), -0.10% vs nominal 32,791,266 | near_rpc/block:224437937 sha256 e5c4f116422a... and its predecessor by prev_hash; previous epoch start 224394737 | high | second independent jump 25,685.66 NEAR; within-epoch drift -273.01 NEAR/epoch is the net gas burn |
| Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC | **VERIFIED_LIVE_API** | median headroom +1.55 bps over 3 comparable cells (dest_units); competitor ceiling 3.00 bps | oneclick/relay/lifi/across quote records 2026-11-14T06:05:11.295Z | medium | $500: +1.93 bps vs relay (rank 1/3); $50,000: +1.55 bps vs relay (rank 1/3); $250,000: +0.98 bps vs relay (rank 1/3); no 1Click capacity failures |
| Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC | **NOT_SUPPORTED** | 1Click delivers LESS BTC per USDC than the best competitor (relay): median headroom -7.34 bps over 3 cells (dest_units); the claim is not supported by this run | oneclick/lifi/relay quote records 2026-11-14T06:05:11.295Z | medium | clip-dependent: $500: -10.03 bps vs relay (rank 2/3); $50,000: -7.34 bps vs relay (rank 2/3); $250,000: +14.37 bps vs lifi (rank 1/3); LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used |
| EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative) | **VERIFIED_LIVE_API** | median headroom -1.02 bps over 3 cells (dest_units; 1Click trails) | oneclick/across/relay/lifi quote records 2026-11-14T06:05:11.295Z | medium | $500: -0.99 bps vs across (rank 3/4); $50,000: -1.02 bps vs across (rank 3/4); $250,000: -1.02 bps vs across (rank 3/4); the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins |
| Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material | **DERIVED** | deposit/caller HHI_external 828 [90% CI 769-828] (N_eff 12.07), ex-AI-agent 888; AI-agent share 11.5% (>= 10% materiality line), bridge share 69.2% | nearblocks/txns:intents.near:p1 sha256 60c11235ddcd... ... p8 | low | 189 unique receipts over 53 s; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources (bridge callbacks, direct callers), not solvers |
| Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers | **VERIFIED_LIVE_API** | HHI_solver 4,946 [90% CI 4,335-5,523] (N_eff 2.02) over 96 fill participations in 93 fills (4 atomic token_diff fills, 89 hub-settled legs), 5 distinct solvers; CI entirely above the 3,500 cartel threshold | nearblocks/txns:intents.near:p1 sha256 60c11235ddcd... ... p8 + 8 method-filtered execute_intents page(s); args.signed[].payload.message (NEP-413 signer_id) | medium | 445 execute_intents receipts decoded; settlement hub 51e8f94d77b5... (147 counterparties) routes most swaps via transfer legs; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty |
| Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume | **DERIVED** | 10.2% (band 9.2%-11.1%) estimated on-chain: Confidential Intents Treasury 24h inflow $17.2M / outflow $18.7M against 24h volume $168.7M; >= 10% materiality line | near_rpc/confidential:balances:head sha256 3030c3767483... treasury balances in intents.near (NEAR mainnet RPC) | low | nearstats' split was rejected by the plausibility guard; the share is estimated from the public treasury boundary instead. Biases: same-hour shield/unshield netting and in-shard turnover push it down, solver inventory pushes it up; 24h window |
| Confidential TVL backs the dark-pool engine (Engine 2) | **VERIFIED_ON_CHAIN** | $132.1M TVL read on-chain from the Confidential Intents treasury in intents.near (NEAR-reported via nearstats: $135.1M) | near_rpc/confidential:balances:head sha256 3030c3767483... intents.near mt_batch_balance_of (treasury) | high | Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut (0.7); the confidential take (20 bps) is an assumption |
| Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink | **DERIVED** | alpha 30.5%; gross take 16.03 bps, net take 4.88 bps; buyback sink 18,390 NEAR/day = 21.9% coverage incl. burn and lock | defillama/fees:near-intents:dailyHoldersRevenue sha256 0e61279bd524... / defillama/fees:near-intents sha256 9d63a8420453... | medium | DefiLlama revenue methodology: NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.near.org and the on-chain buyback). Split by destination wallet into front-end affiliate revenue and Other. Transfers between those wallets are excluded. |
| Chain Signatures (v1.signer) is a growing second usage engine beyond Intents | **NOT_SUPPORTED** | 17,543 sign requests/day (7d) vs 11,737/day (30d); ln-trend +43% per 30 d [90% CI -13% to +137%], t = 1.18; top caller omni.bridge.near 47% of 344 sampled sign receipts, *.bridge.near callers 69%; gas 0.0022 NEAR per request (inconclusive: growth not shown at t >= 2) | nearblocks/txns:v1.signer:before_block:* (11 windows of 100 receipts, 1,100 receipts) + nearblocks/txns:v1.signer:count | low | sampled estimate: each window covers minutes; bridge callers serve cross-chain transfers that overlap Intents settlement, so the engine is not fully independent of Intents; storage lock 11.7 NEAR is small. sign() attaches 1 yoctoNEAR (median of sampled requests), so the contract takes no material per-request fee; the requester's cost is gas. |
| The volume engine (GBM with measured sigma) is calibrated out of sample: P10-P90 covers ~80% of realized 30-day volume | **NOT_SUPPORTED** | 1m 11/20 = 55% inside P10-P90 (binomial p 0.01); 3m 9/17 = 53% inside P10-P90 (binomial p 0.01); 6m 7/14 = 50% inside P10-P90 (binomial p 0.01); 1m median realized / forecast median 1.33x (under-prediction); 1m coverage 20% for origins before 2026-01-17, 90% from it; 20 monthly origins 2025-03-23 to 2026-10-14 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 ae314ea97a8b... | low | Tests the volume distribution only; the take rate, holder capture, confidential share, multiple and discount rate are not backtested. 3m and 6m forecasts from monthly origins overlap, so their effective sample is smaller than n. |
| A block-bootstrap volume engine (fat tails, autocorrelation) is calibrated out of sample where GBM is not | **NOT_SUPPORTED** | block bootstrap 1m 19/20 (95%, p 0.16), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33); GBM 1m 11/20 (55%, p 0.01), 3m 9/17 (53%, p 0.01), 6m 7/14 (50%, p 0.01); bootstrap at the GBM's expected path (shape only) 1m 13/20 (65%, p 0.10), 3m 5/17 (29%, p <0.01), 6m 0/14 (0%, p <0.01); bootstrap band 3.1x the GBM's log width at 1m; 20 monthly origins 2025-03-23 to 2026-10-14 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 ae314ea97a8b...; valuo.models.volume_bootstrap (seed 20261114, 10000 paths per origin) | low | Inside P10-P90 against an 80% target, exact two-sided binomial p. Low power: at n = 20 the test accepts 14 to 19 hits and rejects a 70%-coverage engine only 39% of the time; 3m and 6m forecasts overlap. Block length (Politis-White) and path count were fixed before coverage was computed; nothing is tuned. The valuation still uses the GBM; this row grades a parallel variant and tests the volume distribution only. |
| NEAR Intents' realized gross take rate is not trending to zero as volume grows | **NOT_SUPPORTED** | rolling 30d gross take 16.03 bps on 2026-11-12 vs 16.64 bps on 2025-11-13; trend -30.3%/yr, 90% CI -42.5% to -15.6% (excludes zero; Newey-West 60d lag, 365 overlapping points); floor 0.5 bps, 0 of 365 trailing points below it; non-overlapping 30d windows (n=13) -26.8%/yr, Student-t 90% CI -43.1% to -5.9%; trailing 180d trend +25.2%/yr, CI -8.3% to +70.8% | defillama/fees:near-intents:dailyFees sha256 9d63a8420453...; defillama/fees:near-intents:dailyRevenue sha256 eece69a9b079...; defillama/fees:near-intents:dailyHoldersRevenue sha256 0e61279bd524...; defillama/dexs:near-intents sha256 ae314ea97a8b... | low | Graded on the trailing-365d trend only: a decline is counted when the Newey-West 90% interval and the non-overlapping-window Student-t interval both sit below zero; DERIVED needs no such decline and a latest rolling take above the model floor. Gross take includes affiliate fees kept by frontends; NEAR's captured share is the net / holder take. Rolling points overlap, so an interval that includes zero is not proof of a floor. The full-history trend is not used (fee ramp from zero in 2025). |
| 1Click quotes institutional size: at least $1M on every benchmarked corridor | **NOT_SUPPORTED** | ETH USDC -> SOL USDC: 1Click $500K, best competitor LI.FI $5M; ETH USDC -> native BTC: 1Click $500K, best competitor LI.FI $1M (routed through NEAR Intents); Base USDC -> Arbitrum USDC: 1Click $500K, best competitor LI.FI $5M (0 of 3 corridors with an attempted 1Click rung at or above $1M) | 1Click, Relay, LI.FI, Across dry quotes; ledger records ladder:<venue>:<corridor_id>:<size_usd> (81 responses), run 2026-11-14T06:05:16.718Z | low | Largest size quoted on an eight-rung ladder of dry quotes, one run. A dry 'no liquidity' is solver quoting policy at that moment, not proven depth, and a dry quote is not a fill. |
| NEAR Intents is gaining share of cross-chain routing fees | **NOT_SUPPORTED** | 21.0% of the six-protocol fee pool (30 days to 2026-11-12), rank 2 of 6 behind Relay at 54.2%; share at window start 35.0% (203-day common window); trend -6.47 pp per 30 days, 90% interval -9.42 to -3.53; ex-Relay 45.7%, trend -0.95 pp per 30 days, 90% interval -1.73 to -0.17 (share is falling) | defillama summary/fees dailyFees: near-intents, relay, across, debridge, chainflip, thorchain-dex | low | Fee share, not volume share; adapter fee definitions differ; the pool is the protocols DefiLlama covers. A share trend is DERIVED from live fee series, never VERIFIED. |
| The model's terminal multiple cap sits inside the observed peer range of FDV/revenue | **DERIVED** | cap 60x vs 15 chain tokens: 3 of 15 trade at or below it (20th percentile); P25 161x, median 521x [bootstrap 90% 223x to 968x], P75 1,756x, range 2.4x to 6,305x; NEAR L1-only 4,024x (87th percentile); without flagged rows: median 584x, n 10 | defillama/overview:fees:dailyRevenue sha256 1cad57b758c6... + coingecko/coins_markets_wide sha256 08c2fb144280... | medium | Rule: DERIVED when the cap is at or below the 75th percentile of the wide set and n_peers >= 8. Here the cap is inside the observed range and at or below its upper quartile. FDV/revenue on 30 days annualised, one snapshot; revenue definitions differ by chain adapter; peers ranked by revenue and fixed before any multiple was computed (inclusion_rules, excluded). |


## 14. Assumptions register

### 14.1 Labeled assumptions (slider inputs; never presented as measured)
| Key | Default | Unit | Range | Justification |
| :--- | :--- | :--- | :--- | :--- |
| svrn_target_inflation | 0.016 | ratio_annual | [0.005, 0.03] | SVRN governance proposal to cut the protocol max_inflation_rate from 2.5% to 1.6%; not enacted on-chain (live EXPERIMENTAL_protocol_config.max_inflation_rate is still [1, 40]). |
| svrn_glidepath_months | 24 | months | [6, 48] | QUANT_PIPELINE_SPEC and TERMINAL_UI_SPEC model the 2.5% -> 1.6% cut as a linear 24-month (730-day) glidepath; the proposal itself does not fix the phasing. |
| public_volume_growth_yoy | 0.750472 | ratio_yoy | [0.157856, 1.6464] | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-14 to 2026-11-13 (365 days, DefiLlama dexs/near-intents): +75.0%/yr, 90% CI +15.8% to +164.6% (Newey-West, 30-day lags). Range = that CI. Median trend growth used as EXPECTED growth (conservative). Replaces the registry default +30%. Cross-checks (not used): yoy_trailing_30d +44%; mean_monthly_log_return_12m +23%. |
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
| total_supply_near | 1,311,650,629 | NEAR | measured | RPC block header total_supply at height 224473852 |
| current_max_inflation_rate | 0.025 | ratio_annual | measured | RPC EXPERIMENTAL_protocol_config.max_inflation_rate |
| treasury_share | 0 | ratio | measured | RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this) |
| staked_supply_ratio | 0.448902 | ratio | measured | RPC validators current stake / total_supply (343 validators) |
| annual_issuance_near | 32,759,808 | NEAR_per_year | measured | minted_per_epoch 25683.37497374837 NEAR x epochs_per_year 1275.5258165951757 from total_supply jumps at epoch starts 224394737 -> 224437937 |
| issuance_realization_factor | 0.999041 | ratio | measured | measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path |
| near_price_usd | 3.34 | USD | measured | nearstats price.currentUsd via intents_forensics.price.current_usd |
| daily_volume_usd | 125,805,115 | USD_per_day | measured | intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window (aligned daily charts, 30 complete UTC day |
| gross_take_bps | 16.0253 | bps | measured | intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window (aligned daily charts, 30 complete UTC |
| capture_ratio | 0.30466 | ratio | measured | intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window (aligned daily charts, 30 complete  |
| gas_burn_near_per_day | 953.3901 | NEAR_per_day | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| state_lock_growth_near_per_day | 342.4734 | NEAR_per_day | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| public_volume_growth_yoy | 0.750472 | ratio_yoy | measured | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-14 to 2026-11-13 (365 days, DefiLlama dexs/near-intents): +75.0%/yr, 90% CI +15.8% to +164.6% (Newe |
| competitive_fee_ceiling_bps | 3.004 | bps | derived | median over cross-VM cells of the best competitor's friction (per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding); the lowest-fric |
| tau_floor_bps | 1.5459 | bps | derived | max(0.5 bps, min(live public take, live cross-VM headroom)) from the execution benchmark (headroom_by_archetype_bps.cross_vm = 1.55 bps). |
| tau_pub_start_bps | 15.5748 | bps | derived | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d; blended live gross take 16.03 bps (DefiLlama daily fees / daily volume summed over the a |
| alpha_capture | 0.30466 | ratio | measured | measured:defillama near-intents dailyHoldersRevenue / fees |
| terminal_multiple | 60 | x_fdv_to_revenue | derived | peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; raw 2543.9x. |
| confidential_share_start | 0.10181 | ratio | derived | on-chain estimate: Confidential Intents Treasury 24h inflow / (24h volume + inflow) = 10.2% (band 9.2%-11.1%); nearstats split implausible. Estimated from the C |
| sigma_price_annual | 1.0259 | ratio_annual | measured | nearstats:price-history: 1y daily closes, log-return sigma x sqrt(365). |
| sigma_volume_monthly | 0.3473 | ratio_monthly | measured | measured: monthly log-return sigma of 30-day volume aggregates |


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

230 raw exchanges (203 ok, 27 failed), 15,490,039 bytes hashed; raw bodies persisted under `artifacts/raw` and listed with SHA-256 in `manifest.json`.

| Source | Records |
| :--- | ---: |
| across | 15 |
| coingecko | 2 |
| defillama | 22 |
| lifi | 33 |
| near_rpc | 40 |
| near_rpc_archival | 15 |
| nearblocks | 32 |
| nearstats | 2 |
| oneclick | 36 |
| relay | 33 |


Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):
| Source | Name | HTTP | Error |
| :--- | :--- | :--- | :--- |
| across | quote:eth_usdc_sol_usdc:50000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:500 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:250000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | ladder:across:eth_usdc_sol_usdc:1000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | ladder:across:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 613559.470976 US |
| relay | ladder:relay:eth_usdc_btc:500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $320, |
| across | ladder:across:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 613559.470976 US |
| relay | ladder:relay:eth_usdc_btc:1000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $320, |
| relay | ladder:relay:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,47 |
| across | ladder:across:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 613559.470976 US |
| relay | ladder:relay:eth_usdc_btc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $320, |
| relay | ladder:relay:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,47 |
| relay | ladder:relay:eth_usdc_btc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $320, |
| relay | ladder:relay:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Quote amount exceeds the maximum for this pair |
| oneclick | ladder:1click:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:5000000 | 400 | HTTP 400: No liquidity available |
| lifi | ladder:lifi:eth_usdc_btc:2500000 | 404 | HTTP 404: No available quotes for the requested transfer |
| lifi | ladder:lifi:eth_usdc_btc:5000000 | 404 | HTTP 404: No available quotes for the requested transfer |
| nearblocks | txns:v1.signer:before_block:223551496 |  | ReadTimeout:  |
| nearblocks | txns:v1.signer:before_block:223551496:retry |  | ReadTimeout:  |


### 16.1 Methodology warnings recorded during the run (16)
- fee_pool: across: 3 malformed, negative or duplicate chart rows skipped
- execution_bench: eth_usdc_sol_usdc $500: venue USD oracles disagree with the cell's common price by more than the +1.93 bps headroom (1click +0.0 bps, relay +1.9 bps, lifi -8.6 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the +1.55 bps headroom (1click +0.0 bps, relay +1.9 bps, lifi -8.6 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +1.9 bps, lifi -8.6 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $500: venue USD oracles disagree with the cell's common price by more than the -10.03 bps headroom (1click +0.0 bps, relay -14.6 bps, lifi -24.3 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $50,000: venue USD oracles disagree with the cell's common price by more than the -7.34 bps headroom (1click +0.0 bps, relay -14.6 bps, lifi -24.3 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $250,000: venue USD oracles disagree with the cell's common price by more than the +14.37 bps headroom (1click +0.0 bps, relay -14.6 bps, lifi -24.3 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $500: venue USD oracles disagree with the cell's common price by more than the -0.99 bps headroom (1click +0.0 bps, relay +1.9 bps, lifi -16.7 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +1.9 bps, lifi -16.7 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +1.9 bps, lifi -16.7 bps); headroom is measured on destination units, not USD legs
- intents_forensics: confidential split: nearstats reports confidential 30d $0.07 (0.0000%), rejected (tvl_without_volume: confidential TVL $132.08M but all-time confidential volume $0.00 of $38.72B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'). Share ESTIMATED ON-CHAIN from the Confidential Intents Treasury: 10.2% (band 9.2%-11.1%; 24h inflow $17.18M, outflow $18.72M, volume $168.74M), replacing the registry assumption 40%
- intents_forensics: take-rate window leaves out 2026-11-13: DefiLlama reports revenue above fees for that day, so its fee figure is not final; the window ends the day before
- intents_forensics: nearblocks: 11 duplicate receipt(s) seen on overlapping pages were counted once (id-based cursor vs time-ordered rows); unique receipts sampled = 189
- chain_signatures: 1 of 12 sample windows failed; rates use the 11 that returned
- sotp: confidential share 10.2% is an ON-CHAIN ESTIMATE from Confidential Intents Treasury boundary flows (band 9.2%-11.1%), not nearstats' split (rejected as implausible); 24h window, biases listed in intents_forensics.volume.confidential_share_estimate
- sotp: peer median FDV/revenue 2543.9x clipped to 60.0x (guardrails [8, 60])
