# Valuo IC Memo: NEAR at block 225,964,398

*NEAR Intents clearinghouse + NEAR L1. Generated 2026-11-24T06:05:04.108Z UTC from live mainnet RPC and key-free public APIs; every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section 14.*

| Provenance | Value |
| :--- | :--- |
| NEAR block | 225,964,398 (`DUttocVvtsDwiKDM49JF6ikoEo22voFUn8LJSRLyz8Nx`), 2026-11-24T06:05:01.692Z |
| RPC endpoint | https://free.rpc.fastnear.com |
| Snapshot generated | 2026-11-24T06:05:04.108Z UTC, runtime 473.0 s, valuo 0.1.0, schema 1.0.0 |
| Snapshot SHA-256 | `a7aa88ddbb1edcb3e77313e22517d59ad1624eacde1afd48dbe94c9b91b07650` |
| Monte Carlo | seed 20261114, 10,000 paths, 36 months |
| Raw records | 241 HTTP/RPC exchanges hashed, 52 non-2xx/failed (every one listed in manifest.json) |


## 1. The long-term case, made falsifiable

The long-term case for NEAR at $4.00B: 3 of 7 measured conditions are on track. It holds if the market keeps an L1 multiple (78x revenue needed against a 2,480x peer median) while Intents grows into it; it fails if volume growth stays near 105% a year against the 132% the price implies.

| Condition | Required | Live | Trend | Status |
| :--- | ---: | ---: | :--- | :--- |
| Intents volume compounds fast enough to grow into the price | 132% a year | 105% a year | +67% (30-day volume vs 90 days earlier) | **Behind** |
| Holder revenue (buybacks) scales to support the price at the model's multiple | $140.6M a year | $20.5M a year | +172% (30-day holder revenue vs 90 days earlier) | **Behind** |
| The market keeps valuing NEAR like an L1, not like a fee-only app | 78x | 2,480x | n/a | **On track** |
| 1Click keeps a pricing edge where it competes (cross-VM routes) | > 0 | +1.10 bps | n/a | **On track** |
| Confidential (private) flow keeps growing | > 0 | $21.3M | +211% (confidential TVL vs 90 days earlier) | **On track** |
| Fees retire more NEAR than issuance creates | $412.8M a day | $147.0M a day | n/a | **Behind** |
| Governance cuts issuance from 2.5% to 1.6% | 1.6% | 2.5% | n/a | **Behind** |
| Solver competition stays broad enough to keep spreads tight | <= 3,500 | n/a | n/a | **Not measured** |


How to read it: each requirement is what the market price needs if that condition alone carries the case (from the reverse valuation in section 3), or the threshold the bear case watches (section 11). An investor holding NEAR long-term is betting that the conditions marked Behind close; the ones marked Against are where the case is currently losing. Re-run `make reproduce` to re-grade every row against live data.

## 2. Executive summary

**Model value vs market value.** Market FDV is $4.00B (spot price x on-chain total supply at block 225,964,398). The model's expected-path FDV is $3.09B and its 10,000-path Monte Carlo gives P10 / P50 / P90 = $537.8M / $1.80B / $6.31B. The market sits above the expected path (1.3x it) and at 2.2x the Monte Carlo P50. The model capitalises NEAR Intents holder revenue, L1 gas burn and state-lock flow over 36 months at a 25% discount rate and a 60x terminal multiple; the question below is which input would have to change for it to reach the market price, and whether the evidence allows that.

**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in section 3).

| Input | Base | Required for market FDV | Evidence | Inside evidence |
| :--- | ---: | ---: | ---: | :--- |
| Expected annual public-volume growth (3-year path) | 110.3% | 132.3% | 104.8% | no |
| Starting gross public take rate | 18.04 bps | 28.51 bps | 3.00 bps | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 78x | 2,480x | yes |
| Annual discount rate | 25.0% | 14.6% | 10.0% | yes |
| Confidential share of volume at month 36 | 40.0% | 55.8% | 8.7% | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $107.2M/yr | $140.6M/yr | $20.5M/yr | no |


**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple (78x needed; live peer FDV/revenue HYPE 64x, ETH 2,480x, SOL 3,726x, median 2,480x over n = 3 peers). A 14.6% discount rate would also close it (registry range starts at 10%). The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on Intents cash flow at the model's 60x terminal cap. On cash flow alone (multiple held at the model's 60x), the market price requires 132%/yr expected public-volume growth for 3 years (trailing 12 months: +104.8%), or a 29 bps starting public take (today 18.04 bps, live competitive ceiling 3.00 bps), or $140.6M of annualised holder revenue in year 3 (6.9x today's $20.5M); none of these is inside its measured evidence. Whether NEAR keeps an L1 multiple is the investment question; this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token.

**What you have to believe** (section 4). The three inputs that move FDV most are Terminal FDV / holder-revenue multiple (8.00x to 150x: $523.9M-$7.54B); Expected annual public-volume growth (50.7% to 193.4%: $1.32B-$7.35B); Public take compression speed (per month) (0.0%/month to 15.0%/month: $857.2M-$5.78B). Together they carry 83% of the swing-squared variance proxy. 7 of 17 single-input ranges reach the market FDV.

**Relative value** (section 5). NEAR trades at 45x annualised fees against a peer median of 278x (rank 1 of 4, lowest multiple first; below every peer); at peer FDV/fees multiples NEAR's fees map to $14.57B-$50.08B (cross-check, not a fair value; n = 3 peers); holder revenue covers 22% of the $100.0M/yr security budget.

**Evidence quality flags.**

- Confidential share: ESTIMATED ON-CHAIN at 8.7% (band 8.0%-8.8%). nearstats reported 0.0000%, which its own payload contradicts, so the share is read from the Confidential Intents Treasury instead: 24h inflow $17.5M, outflow $17.7M, against 24h volume $201.1M. Same-hour netting and in-shard turnover bias it down, solver inventory up; one 24h window. Engine 2 ($1.20B of the $3.09B expected-path FDV) is valued on this estimate, not on the 40% registry assumption. On-chain cross-check: the Confidential Intents treasury (`51e8f94d...de7cbe` in `intents.near`) holds $125.9M at block 225,964,410 (210 tokens, 31 unpriced); net 30-day boundary flow $21.3M at today's prices; over 24h at least $17.5M entered and $17.7M left (hourly snapshots, lower bounds), an inflow of 8.0% of 24h volume. Confidential swaps settle on a private chain whose RPC needs authentication, so swap volume itself cannot be read; boundary inflow is a proxy, not the share (it nets same-hour flows and includes solver inventory).
- Deposit/caller HHI 1,795 (bootstrap 90% CI 1,471-1,914) over 29 external receipts spanning 36 s; a point sample, not a market-share estimate.
- Solver HHI not measured. Cartel trigger: not measured.
- Bear case: 1 of 3 graded early-warning triggers breached; not graded this run: solver_cartelization. Combined-worst deterministic FDV $268.5M (-91%).

## 3. What the market is pricing (reverse valuation)

Basis: deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base. Solver: scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12. Market FDV $4.00B; expected-path model FDV $3.09B (gap 1.3x); Monte Carlo P50 $1.80B (gap 2.2x). Every required value is the expected-path requirement; the P50 sits lower by lognormal convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).

| Input | Base | Required for market FDV | Evidence | Evidence basis | Inside evidence |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Expected annual public-volume growth (3-year path) | 110.3% | 132.3% | 104.8% | trailing-12-month NEAR Intents 30-day volume growth | no |
| Starting gross public take rate | 18.04 bps | 28.51 bps | 3.00 bps | live competitive fee ceiling (median best-competitor friction, cross-VM cells) | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 78x | 2,480x | peer median FDV / annualised revenue ex-NEAR (unclipped) | yes |
| Annual discount rate | 25.0% | 14.6% | 10.0% | low end of the registry discount-rate range (10%-40%) | yes |
| Confidential share of volume at month 36 | 40.0% | 55.8% | 8.7% | on-chain estimate of the confidential share (Confidential Intents Treasury 24h boundary flow / 24h volume) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $107.2M/yr | $140.6M/yr | $20.5M/yr | current annualised holder revenue (30-day window x 365.25/30) | no |

- Justifying $4.00B needs 132% expected annual public-volume growth for 3 years (base 110%); trailing-12-month Intents volume growth was 105%.
- Justifying $4.00B needs a starting gross public take of 28.5 bps (decaying to the 1.10 bps floor at 3%/month) versus 18.04 bps today; the live competitive fee ceiling is 3.00 bps.
- Justifying $4.00B needs a 78x terminal FDV/holder-revenue multiple; the live peer median is 2,480x (HYPE 64x, ETH 2,480x, SOL 3,726x) and the model caps it at 60x.
- Justifying $4.00B needs a 14.6% discount rate versus 25% base; the registry range is 10%-40%.
- Justifying $4.00B needs the confidential share to reach 56% by month 36; the on-chain estimate today is 9% (band 8%-9%).
- Justifying $4.00B at the 60x base multiple needs $141M of annualised holder revenue in year 3 (1.3x the base path's $107M), versus $20M today (90%/yr compounded).

Headline: Market FDV $4.00B is 1.3x the model's expected-path FDV $3.09B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 78x (evidence 2,480x); discount rate 15% (evidence 10%).

Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the joint requirement is smaller than any single one; section 4 shows which inputs carry the variance.

## 4. What you have to believe (one-at-a-time sensitivity)

Basis: deterministic_sotp expected path; one input at its low / high, all others at the snapshot base. Base expected-path FDV $3.09B against a $4.00B market FDV. Variance share: swing^2 / sum(swing^2): first-order share for independent inputs, an approximation. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).

| # | Input | Source | Range | Base | FDV at low | FDV at high | Swing | Variance share |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Terminal FDV / holder-revenue multiple | derived | 8.00x - 150x | 60x | $523.9M | $7.54B | $7.02B | 37.2% |
| 2 | Expected annual public-volume growth | measured | 50.7% - 193.4% | 110.3% | $1.32B | $7.35B | $6.03B | 27.5% |
| 3 | Public take compression speed (per month) | assumption | 0.0%/month - 15.0%/month | 3.0%/month | $5.78B | $857.2M | $4.92B | 18.3% |
| 4 | Confidential share at month 36 | assumption | 5.0% - 60.0% | 40.0% | $2.03B | $4.35B | $2.32B | 4.1% |
| 5 | Annual discount rate | assumption | 10.0% - 40.0% | 25.0% | $4.52B | $2.22B | $2.30B | 4.0% |
| 6 | Holder capture (revenue / gross fees) | measured | 14.5% - 32.1% | 22.9% | $2.03B | $4.27B | $2.24B | 3.8% |
| 7 | Starting 30-day Intents volume (public + confidential) | measured | 0.79x - 1.27x | 1.00x | $2.47B | $3.88B | $1.41B | 1.5% |
| 8 | Confidential multiple haircut | assumption | 30.0% - 100.0% | 70.0% | $2.43B | $3.59B | $1.16B | 1.0% |
| 9 | NEAR price drift (gas-burn and state-lock USD value) | assumption | -50.0% - 100.0% | 0.0% | $2.95B | $4.01B | $1.06B | 0.8% |
| 10 | Confidential gross take (public take re-reconciled to live fees) | assumption | 10.00 bps - 30.00 bps | 20.00 bps | $2.59B | $3.60B | $1.01B | 0.8% |
| 11 | Confidential compression divisor | assumption | 1.00x - 10x | 3.00x | $2.57B | $3.37B | $804.7M | 0.5% |
| 12 | Public take hard floor | assumption | 0.00 bps - 5.00 bps | 0.50 bps | $3.09B | $3.70B | $608.1M | 0.3% |
| 13 | Blended gross take (public take re-reconciled) | measured | 12.35 bps - 17.41 bps | 18.21 bps | $2.54B | $3.02B | $480.7M | 0.2% |
| 14 | NEAR spot price (USD value of gas burn and state lock) | measured | $2.27 - $4.10 | $3.05 | $3.05B | $3.16B | $107.9M | 0.0% |
| 15 | L1 gas burn (NEAR/day) | measured | 550 NEAR/day - 917 NEAR/day | 734 NEAR/day | $3.05B | $3.14B | $88.0M | 0.0% |
| 16 | Cross-VM headroom (sets the public take floor) | measured | 0.83 bps - 1.38 bps | 1.10 bps | $3.05B | $3.14B | $86.2M | 0.0% |
| 17 | State-lock growth (NEAR/day) | measured | 296 NEAR/day - 494 NEAR/day | 395 NEAR/day | $3.09B | $3.10B | $1.6M | 0.0% |

Top three inputs carry 83% of the variance proxy. 7 of 17 single-input ranges reach the market FDV at either end.

Headline: terminal_multiple, public_volume_growth_yoy, fee_compression_lambda_monthly carry 83% of the swing-squared variance proxy; terminal_multiple alone moves FDV from $524M to $7.54B across its range, and 7 of 17 single-input ranges reach the $4.00B market FDV.

Excluded (move issuance and implied price, not FDV): svrn_target_inflation (issuance path only: moves supply at horizon and implied price, not FDV); svrn_glidepath_months (issuance path only: moves supply at horizon and implied price, not FDV).

## 5. Relative value: peer cash-flow multiples and the security budget

Basis: live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR.

### 5.1 NEAR cash-flow coverage against the peer set
| Metric | NEAR | Peer median | Peer P25 - P75 | NEAR rank | Position |
| :--- | ---: | ---: | ---: | ---: | :--- |
| FDV / annualised fees (30-day run-rate) | 45x | 278x | 164x - 562x | 1 of 4 | below every peer |
| FDV / annualised revenue (30-day run-rate) | 183x | 2,480x | 1,272x - 3,103x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day fees | 73x | 199x | 134x - 707x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day revenue | 379x | 1,855x | 972x - 3,142x | 2 of 4 | inside the peer range |

| Protocol | FDV | Fees (ann.) | Revenue (ann.) | FDV/fees | FDV/revenue | FDV/fees 1y | FDV/revenue 1y | Revenue/fees |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SOL (solana) | $45.65B | $164.1M | $12.3M | 278x | 3,726x | 199x | 1,855x | 7% |
| ETH (ethereum) | $207.73B | $245.5M | $83.7M | 846x | 2,480x | 1,216x | 4,428x | 34% |
| HYPE (hyperliquid) | $60.94B | $1.25B | $947.7M | 49x | 64x | 68x | 89x | 76% |
| NEAR (near_combined) | $3.99B | $89.1M | $21.8M | 45x | 183x | 73x | 379x | 24% |
| NEAR (near) | $3.99B | $1.1M | $905,407 | 3,473x | 4,403x | 3,603x | 5,088x | 79% |
| NEAR (near-intents) | $3.99B | $87.9M | $20.9M | 45x | 191x | 75x | 409x | 24% |

The model's terminal multiple is 60x; 0 of 3 peers trade at or below it on FDV/revenue.

### 5.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)
| Cash flow | NEAR (ann.) | at peer P25 | at peer median | at peer P75 | Peers | Basis |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| fees | $89.1M | $14.57B | $24.79B | $50.08B | 3 | comps.near_combined.annualized_fees_usd x peer FDV / annualised fees (30-day run-rate) |
| revenue | $21.8M | $27.72B | $54.04B | $67.61B | 3 | comps.near_combined.annualized_revenue_usd x peer FDV / annualised revenue (30-day run-rate) |

relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution; market FDV $4.00B.

### 5.3 Staking and security budget
- Security budget: 32,794,304 NEAR/yr of issuance (2.50%) x $3.05 = $100.0M/yr (2.51% of FDV).
- Against it: $89.1M/yr of fees (89% of the budget) and $21.8M/yr of holder revenue (22%); net dilution $78.2M/yr.
- Staked 45.3% of supply; nominal staking APR 5.51%. Basis: security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate.

### 5.4 Findings
- NEAR trades at 45x annualised fees versus a peer median of 278x (rank 1 of 4, lowest first; below every peer); on revenue it is 183x versus 2,480x (inside the peer range).
- 0 of 3 peers trade at or below the model's 60x terminal FDV/revenue multiple; NEAR itself trades at 183x.
- At the peer FDV/fees distribution, NEAR's $89M of annualised fees maps to $14.57B-$50.08B (median $24.79B, n = 3) against a $4.00B market FDV; a relative-value cross-check, not a fair value.
- NEAR issues $100M a year to validators and delegators (2.5% of FDV) against $89M of annualised fees and $22M of holder revenue (gas burn + Intents buyback): revenue covers 22% of the security budget.
- At 2.5% inflation stakers earn 5.51% nominal and 3.52% real including buybacks; non-stakers lose 1.99% a year to dilution net of buybacks.

Caveat: Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples compare different cash-flow definitions; with n = 3 peers the median is a reference point, not a distribution.

## 6. Model valuation detail

**Base case.** 10,000-path SOTP (seed 20261114): P10 / P50 / P90 FDV = $537.8M / **$1.80B** / $6.31B; implied price $0.39 / **$1.31** / $4.61 per NEAR against spot $3.05. The P50 sits 55.1% below the current FDV of $4.00B. The deterministic SOTP at the labeled inputs (the expected-volume path) is $3.09B: engines $1.71B clearinghouse + $1.20B confidential + $179.2M monetary; the Monte Carlo mean is $3.01B. Ex-monetary P50: $1.72B.

**Volume growth is measured, not assumed.** Trend growth of NEAR Intents daily volume over 2025-11-24 to 2026-11-23 (365 days, DefiLlama): +110.3%/yr, 90% CI +51% to +193% (OLS of log volume on time, Newey-West errors). The model uses it as public_volume_growth_yoy, with the CI as its range; it is the median trend, so reading it as expected growth is conservative. Cross-checks, not used: yoy trailing 30d +15%, mean monthly log return 12m +11%.



**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled +110% YoY volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of 0.240 the MEDIAN simulated path ends month 36 at 35.5% of the expected path ($405.8M/day vs $1.14B/day), which is what pulls the P50 FDV below the mean. The dispersion is measured from 11 monthly volume log-returns (sigma excluding the three oldest, incentive-era windows: 0.243); a thin sample, reported as such.

**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation; section 3 solves which single input would: Market FDV $4.00B is 1.3x the model's expected-path FDV $3.09B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 78x (evidence 2,480x); discount rate 15% (evidence 10%). The P90 ($6.31B) comes from volume paths, not from take-rate expansion (the public take only compresses in this model).

**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** 6 bps net take needs >= $1.00B/day; 10 bps net take needs >= $500.0M/day; 14 bps net take needs >= $250.0M/day; 18 bps net take needs >= $250.0M/day. Live run-rate: $134.6M/day at 4.16 bps net (18.21 bps gross x capture 22.9%).

**Net-float crossover.** Today sinks cover 21.7% of measured issuance (19,494 NEAR/day vs 89,786 NEAR/day). status quo (cap flat): deterministic flow crossover none within horizon at run-rate volume, month 28 with the +110% YoY growth assumption; Monte Carlo P(crossover within 36m) = 83.1%, P(deflationary at horizon) = 73.6%; breakeven volume V* = $649.7M/day (4.8x today). SVRN glidepath: deterministic flow crossover none within horizon at run-rate volume, month 22 with the +110% YoY growth assumption; Monte Carlo P(crossover within 36m) = 88.4%, P(deflationary at horizon) = 80.8%; breakeven volume V* = $412.8M/day (3.1x today). The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price outruns issuance); the deterministic path (the expected-volume path) is the one to quote.

**Falsification.** Four stress scenarios (section 11) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo percentile) at $268.5M (-91% vs the deterministic base $3.09B); 1 of 3 measured early-warning triggers are breached in this snapshot (breached: governance_stalemate (max_inflation_rate now 2.50% vs > 1.60%); not measured this run: solver_cartelization). The on-chain inflation cap reads 2.50%; the SVRN cut is a proposal, not protocol state.

## 7. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)

Executable quotes fetched 2026-11-24T06:05:11.696Z UTC (29 ok of 36; 1Click token universe 233 assets on 39 chains). Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input (headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price (`price_basis`: oneclick_token_list_oracle); raw-unit friction is exact for USDC -> USDC. Positive headroom means 1Click paid out more after all fees.

| Corridor | Clip | Venue | Status | Out | Friction | ETA | Route |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | 1click | ok | 499.902860 | 1.94 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $500 | relay | ok | 499.829862 | 3.40 bps (raw) | 1 s | relay |
| ETH USDC -> SOL USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $500 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $50,000 | 1click | ok | 49,990.498802 | 1.90 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $50,000 | relay | ok | 49,984.979862 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $50,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $250,000 | 1click | ok | 249,949.492597 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $250,000 | relay | ok | 249,924.979862 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $250,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | 1click | ok | 0.008244 | 37.32 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $500 | relay | ok | 0.008257 | 21.68 bps (usd) | 120 s | relay |
| ETH USDC -> native BTC | $500 | lifi | ok | 0.008238 | 44.70 bps (usd) | 1,320 s | relaydepository |
| ETH USDC -> native BTC | $500 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | 1click | ok | 0.826336 | 13.79 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $50,000 | relay | ok | 0.826005 | 17.79 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $50,000 | lifi | ok | 0.825096 | 28.77 bps (usd) | 1,390 s | near (= NEAR Intents resold via LI.FI) |
| ETH USDC -> native BTC | $50,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | 1click | ok | 4.129026 | 20.20 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $250,000 | relay | no_liquidity: INSUFFICIENT_LIQUIDITY: Solver has insufficient liquidity for this swa | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | lifi | ok | 4.123044 | 34.66 bps (usd) | 1,390 s | near (= NEAR Intents resold via LI.FI) |
| ETH USDC -> native BTC | $250,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | 1click | ok | 499.945481 | 1.09 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $500 | relay | ok | 499.927945 | 1.44 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $500 | across | ok | 499.943933 | 1.12 bps (raw) | 1 s | across |
| Base USDC -> Arbitrum USDC | $50,000 | 1click | ok | 49,989.895220 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $50,000 | relay | ok | 49,994.977945 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $50,000 | across | ok | 49,994.993925 | 1.00 bps (raw) | 36 s | across |
| Base USDC -> Arbitrum USDC | $250,000 | 1click | ok | 249,949.497300 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $250,000 | relay | ok | 249,974.977951 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $250,000 | across | ok | 249,974.993933 | 1.00 bps (raw) | 900 s | across |


| Corridor | Clip | Headroom | Basis | 1Click rank | Reading |
| :--- | ---: | ---: | :--- | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | +1.46 bps | dest_units | 1/3 | 1Click delivers 1.46 bps more than relay |
| ETH USDC -> SOL USDC | $50,000 | +1.10 bps | dest_units | 1/3 | 1Click delivers 1.10 bps more than relay |
| ETH USDC -> SOL USDC | $250,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> native BTC | $500 | -15.67 bps | dest_units | 2/3 | 1Click trails relay by 15.67 bps |
| ETH USDC -> native BTC | $50,000 | +4.01 bps | dest_units | 1/3 | 1Click delivers 4.01 bps more than relay |
| ETH USDC -> native BTC | $250,000 | +14.51 bps | dest_units | 1/2 | 1Click delivers 14.51 bps more than lifi |
| Base USDC -> Arbitrum USDC | $500 | +0.03 bps | dest_units | 1/4 | 1Click delivers 0.03 bps more than across |
| Base USDC -> Arbitrum USDC | $50,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |
| Base USDC -> Arbitrum USDC | $250,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |


- cross_vm: median headroom +1.10 bps over 3 comparable cells
- native_btc: median headroom +4.01 bps over 3 comparable cells
- evm_l2: median headroom -1.02 bps over 3 comparable cells
- competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = 3; per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding): 3.00 bps. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not.

- Where 1Click loses (destination units): eth_usdc_btc at $500 trails relay by 15.67 bps; base_usdc_arb_usdc at $50,000 trails across by 1.02 bps; base_usdc_arb_usdc at $250,000 trails across by 1.02 bps.
- Oracle caveat: on eth_usdc_sol_usdc at $500, eth_usdc_sol_usdc at $50,000, eth_usdc_sol_usdc at $250,000, eth_usdc_btc at $500, eth_usdc_btc at $50,000, eth_usdc_btc at $250,000, base_usdc_arb_usdc at $500, base_usdc_arb_usdc at $50,000, base_usdc_arb_usdc at $250,000 the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg comparison there would have been decided by oracles, which is why the ranking uses units.
- Structurally unsupported routes: across on eth_usdc_btc (declared), across on eth_usdc_sol_usdc (ROUTE_NOT_ENABLED).
- LI.FI's quote on eth_usdc_btc $250,000, eth_usdc_btc $50,000 routes through NEAR Intents itself (tool `near`), so it is 1Click execution plus LI.FI's fee, not an independent price.
- Collector summary: cross_vm (ETH USDC -> SOL USDC): $500: 1Click delivers 1.46 bps more than relay (rank 1/3, destination units); $50,000: 1Click delivers 1.10 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); unsupported: across (ROUTE_NOT_ENABLED). native_btc (ETH USDC -> native BTC): $500: 1Click trails 15.67 bps behind relay (rank 2/3, destination units); $50,000: 1Click delivers 4.01 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 14.51 bps more than lifi (rank 1/2, destination units); unsupported: across (Across is EVM-only; no Bitcoin route); relay no_liquidity at $250,000. evm_l2 (Base USDC -> Arbitrum USDC): $500: 1Click delivers 0.03 bps more than across (rank 1/4, destination units); $50,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units); $250,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units).

## 8. Concentration and agents on intents.near (NearBlocks receipts)

- Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = **1,795** (bootstrap 90% CI 1,471-1,914) (N_eff = 5.57); over all predecessors 3,784; ex-AI-agent 2,107 (N_eff 4.75). These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.
- (b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = **n/a** (no bootstrap CI) (N_eff n/a) across 0 fill participations in 0 fills (0 atomic token_diff fills, 0 solver-to-settlement-hub legs), 0 distinct solvers; 0 execute_intents receipts decoded, 0 unresolved; the solver sample spans n/a. This is the population the solver_cartelization trigger reads; trigger status: not measured.
- AI-agent share of external receipts 24.1% is a NAME-PATTERN classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. Bridge / token-contract share 44.8%; 7 unique external callers in 29 external receipts.
- Sample: 200 unique receipts over 8 NearBlocks pages, blocks 225,964,358-225,964,410, a 36 s window; lifetime receipts on intents.near n/a. A window this short is a point sample, not a market-share estimate; both HHIs move by hundreds of points between runs.
- Method mix: TRANSFER 105, execute_intents 40, ft_on_transfer 13, ft_resolve_withdraw 12, ft_transfer_call 10, storage_deposit 6, do_storage_deposit 6, near_withdraw 6, ft_transfer 2.

### 8.1 Deposit / caller concentration (external predecessors)
| Caller | Class | Receipts | Share | Example tx |
| :--- | :--- | ---: | ---: | :--- |
| escrow.ai.near | AI agent | 7 | 24.1% | [8ZF9i8xGbjAn...](https://nearblocks.io/txns/8ZF9i8xGbjAnHp6EpLxpxcaBXpNzrN4f79fkRyav38Mw) |
| wrap.near | named account | 6 | 20.7% | [GN7U7wBSkVJC...](https://nearblocks.io/txns/GN7U7wBSkVJCizhfEby6xMPbrUUg49B2GjvtWhWp3KUQ) |
| xrp.omft.near | bridge / token contract | 6 | 20.7% | [5nn4nekTCJ1R...](https://nearblocks.io/txns/5nn4nekTCJ1RZtLRpKwYwiV6NBC1MNs3dfnFSeFngpzr) |
| 17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1 | bridge / token contract | 4 | 13.8% | [FkuZWKqxuiQ5...](https://nearblocks.io/txns/FkuZWKqxuiQ5oLFJWUQaTGqtJgYZgAikTbk82dREYuv9) |
| c50eaaa2572ee0c94ec5eff37e5c3d3ef1e831b4dd19f8344f510ff53ce2a860 | implicit account | 3 | 10.3% | [FkuZWKqxuiQ5...](https://nearblocks.io/txns/FkuZWKqxuiQ5oLFJWUQaTGqtJgYZgAikTbk82dREYuv9) |
| sol.omft.near | bridge / token contract | 2 | 6.9% | [2XKbptNuGrjS...](https://nearblocks.io/txns/2XKbptNuGrjS8b3p1Laq91FgRzaoPZHCAM6aaHfJSvrb) |
| sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near | bridge / token contract | 1 | 3.4% | [5LSASJn76zfg...](https://nearblocks.io/txns/5LSASJn76zfggQDewYgZ7s2ojq8aPCgmusPH3Jhrpbxh) |

### 8.2 Solver concentration (execute_intents signers)
No solver fill could be attributed in this sample; hhi_solver is null and the cartelization trigger is not measured.

## 9. Supply physics

### 9.1 Issuance: measured vs nominal
- Measured: 25,722.96 NEAR minted at epoch start 225,949,937 (previous jump 26,095.22 NEAR at 225,906,737); epoch wall time 6.876 h = 1,274.9 epochs/yr; implied annual issuance **32,794,304 NEAR** = 2.4985% of supply.
- Nominal: max_inflation_rate 2.50% x total supply 1,312,550,602 NEAR = 32,813,765 NEAR/yr; measured minus nominal -19,461 NEAR/yr (-0.06%). Daily: measured 89,786 NEAR vs nominal 89,839 NEAR; treasury share 0.0% (validators receive the rest).
- Within-epoch supply drift (net gas burn) -210.27 NEAR/epoch; measured block time 0.573 s. Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.

### 9.2 Daily sinks (NEAR/day, live)
| Sink | NEAR/day | Source | Basis |
| :--- | ---: | :--- | :--- |
| Buyback (holders revenue / price) | 18,364.9 NEAR | measured | $134.6M/day x 18.21 bps gross x alpha 22.9% / $3.05 |
| L1 gas burn | 733.9 NEAR | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| NEP state-lock growth | 395.2 NEAR | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| Total sinks | 19,494.1 NEAR |  | coverage 21.7% of measured issuance; net float 70,292 NEAR/day |


### 9.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)
| Regime (terminal rate) | V* at live take | vs today | V* at competitive ceiling |
| :--- | ---: | ---: | ---: |
| status quo (cap flat) | $649.7M | 4.8x | $3.94B |
| SVRN glidepath | $412.8M | 3.1x | $2.50B |

Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.

### 9.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)
| Regime | Volume path | Issuance/day m1 | Issuance/day m36 | Gross issuance 36m | Sinks 36m | Net float 36m | Flow crossover | Cumulative crossover |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| status quo (cap flat) | run-rate volume | 89,786 NEAR | 96,566 NEAR | 102,053,723 NEAR | 21,360,616 NEAR | 80,693,107 NEAR | none within horizon | none within horizon |
| status quo (cap flat) | +110% YoY volume | 89,786 NEAR | 96,566 NEAR | 102,053,723 NEAR | 73,809,847 NEAR | 28,243,876 NEAR | month 28 | none within horizon |
| SVRN glidepath | run-rate volume | 89,786 NEAR | 60,770 NEAR | 77,397,564 NEAR | 21,360,616 NEAR | 56,036,948 NEAR | none within horizon | none within horizon |
| SVRN glidepath | +110% YoY volume | 89,786 NEAR | 60,770 NEAR | 77,397,564 NEAR | 73,809,847 NEAR | 3,587,717 NEAR | month 22 | none within horizon |


### 9.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)
| Account | Contract | storage_usage bytes | Locked | Growth B/day | Growth NEAR/day | Window |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| intents.near | yes | 14,139,777,110 | 141,397.8 NEAR | 38,256,488 | 382.56 NEAR | 30.4 d |
| aurora | yes | 14,395,985,750 | 143,959.9 NEAR | 1,262,193 | 12.62 NEAR | 30.4 d |
| wrap.near | yes | 169,551,677 | 1,695.5 NEAR | n/a | n/a | n/a |
| v1.signer | yes | 1,132,749 | 11.3 NEAR | n/a | n/a | n/a |
| escrow.ai.near | no | 428 | 0.0 NEAR | n/a | n/a | n/a |
| treasury.near | yes | 357,895 | 3.6 NEAR | n/a | n/a | n/a |
| meme-cooking.near | yes | 5,960,939 | 59.6 NEAR | n/a | n/a | n/a |
| v2.ref-finance.near | yes | 111,471,438 | 1,114.7 NEAR | n/a | n/a | n/a |

- Total state-locked across 8 tracked contracts: **288,242 NEAR** at 0.01 NEAR/KB (storage_amount_per_byte 10,000,000,000,000,000,000 yocto). Measured lock growth 395.2 NEAR/day over intents.near, aurora (archival available).

### 9.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)
| Regime | Inflation | Nominal APR | Real APR | Buyback accrual | Real APR + accrual | Non-staker real |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| status quo (cap flat) | 2.50% | 5.51% | 3.01% | 0.511% | 3.52% | -1.99% |
| SVRN glidepath | 1.60% | 3.53% | 1.93% | 0.511% | 2.44% | -1.09% |

Live: 347 validators, 595,222,643 NEAR staked = 45.35% of supply.

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
Sign-request rate not measured this run (cumulative_receipts: NearBlocks count endpoint failed; sign rate / trend: no sample window returned).

## 10. Sum-of-the-parts valuation and peer comparables

### 10.1 Engines (percentiles over paths, USD; discounted to today)
| Engine | P10 | P25 | P50 | P75 | P90 | Assumption-heavy |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| clearinghouse | $156.0M | $337.1M | $764.3M | $1.73B | $3.60B | no |
| confidential | $104.2M | $220.3M | $516.1M | $1.26B | $2.79B | yes |
| monetary | $2.6M | $7.1M | $24.2M | $88.6M | $284.8M | yes |

| Total | P10 | P25 | P50 | P75 | P90 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| FDV (all engines) | $537.8M | $924.4M | $1.80B | $3.50B | $6.31B |
| FDV ex-monetary | $511.3M | $890.7M | $1.72B | $3.34B | $5.99B |
| Implied price / NEAR | $0.39 | $0.68 | $1.31 | $2.56 | $4.61 |

Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse $938.2M (52%) + confidential $786.5M (44%) + monetary $75.0M (4%) = $1.80B.

- PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor.
- Same construction on confidential volume at the assumed confidential take; terminal multiple x confidential_multiple_haircut because nearstats flags confidential TVL as unverified. Starting confidential share 8.7% is an on-chain estimate from Confidential Intents Treasury boundary flows (intents_forensics.volume.confidential_share_estimate), not nearstats' rejected split.
- PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.

### 10.2 Calibration (what the engines were fed)
| Parameter | Value | Source / basis |
| :--- | :--- | :--- |
| Public take t=0 (gross) | 18.04 bps | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d |
| Blended gross take / net take | 18.21 bps / 4.16 bps | DefiLlama near-intents fees / volume; net = gross x alpha |
| Capture ratio alpha | 22.86% | measured:defillama near-intents dailyHoldersRevenue / fees |
| Confidential take t=0 | 20 bps | assumption: registry confidential_take_bps (1Click confidential quotes need partner authentication) |
| Public take floor | 1.10 bps | derived; cross-VM headroom +1.10 bps, competitor ceiling 3.00 bps |
| Compression lambda (public / confidential) | 0.030 / 0.010 per month | geometric reversion to the floor |
| Volume growth (public / confidential, monthly) | 6.39% / 12.30% | confidential share 8.7% -> 40% target (start share ESTIMATED ON-CHAIN from Confidential Intents Treasury boundary flows) |
| Sigma: price (annual) / volume (monthly) | 1.028 / 0.240 | measured: monthly log-return sigma of 30-day volume aggregates; confidential sigma x 1.00 |
| Terminal multiple (FDV / annual holder revenue) | 60.0x (raw 2,480.3x) | source derived: peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; clipped to registry guardrails |
| Discount rate | 25% | assumption |
| Supply at horizon (glidepath) | 1,368,587,550 NEAR | fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory) |
| Current FDV | $4.00B | spot price x on-chain total_supply at the snapshot block; CoinGecko FDV via nearstats $3.97B (-0.91% gap, struck at a different instant; cross-check only) |
| GBM convention | mean-matching (Ito) | mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM uses the same convention (zero drift => E[P_t] = P_0) |
| Terminal public volume, month H | mean $1.14B/day; median $405.8M/day | start $122.9M/day; MC sample mean $1.09B, median $396.8M; the labeled YoY growth is the growth of the MEAN path |


### 10.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)
| Protocol | Fees 30d | Revenue 30d | FDV | FDV/fees | FDV/revenue | Revenue methodology (live text) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| SOL (solana) | $13.5M | $1.0M | $45.65B | 278.2x | 3,725.7x | Burned fees: 50% of base fees, and 50% of priority fees until SIMD-0096 (slot 320,112,000, 2025-02-12 06:59 UT |
| ETH (ethereum) | $20.2M | $6.9M | $207.73B | 846.1x | 2,480.3x | Amount of ETH burned — base fees plus blob fees (both are permanently burned, accruing to no proposer) |
| HYPE (hyperliquid) | $102.4M | $77.9M | $60.94B | 48.9x | 64.3x | Parent aggregates child protocols. Hyperliquid Perps: 99% of fees go to Assistance Fund for buying HYPE tokens |
| NEAR (near) | $94,358 | $74,417 | $3.99B | 3,472.6x | 4,403.1x | Gas fees permanently burned, reducing NEAR supply. Before 4 November 2026 (protocol upgrade v87) the burn is e |
| NEAR (near-intents) | $7.2M | $1.7M | $3.99B | 45.3x | 190.9x | NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.ne |
| NEAR (near_combined) | $7.3M | $1.8M | $3.99B | 44.7x | 183.0x | near: Gas fees permanently burned, reducing NEAR supply. Before 4 November 2026 (protocol upgrade v87) the bur |

- Median ex-NEAR FDV / annualized revenue 2,480.3x (n = 3); FDV / annualized fees 278.2x (n = 3). annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)
- `revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live methodology text is carried in the table so the multiple is read with its definition.

### 10.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take (SVRN glidepath; * = net-deflationary)
| Net take \ Volume/day | $100.0M | $250.0M | $500.0M | $1.00B | $1.50B |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2 bps | $262.2M | $613.8M | $1.20B | $2.37B* | $3.54B* |
| 6 bps | $731.0M | $1.79B | $3.54B* | $7.06B* | $10.58B* |
| 10 bps | $1.20B | $2.96B* | $5.89B* | $11.75B* | $17.61B* |
| 14 bps | $1.67B | $4.13B* | $8.23B* | $16.43B* | $24.64B* |
| 18 bps | $2.14B* | $5.30B* | $10.58B* | $21.12B* | $31.67B* |

Current FDV $4.00B; confidential share used in the split 8.7%. Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).

### 10.5 Out-of-sample backtest of the volume engine
At each of 20 monthly origins from 2025-04-02 to 2026-10-24 the volume GBM was re-calibrated on data up to the origin only (trailing 30-day volume, sigma from the trailing 365 days, drift = public_volume_growth_yoy 110%) and its P10-P90 band for 30-day volume was compared with what happened (defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json), 2024-12-10 to 2026-11-23). The test of 80% coverage fails at 3m, 6m (exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10). At 1 month the median realized volume is 1.33x the forecast median: the model under-predicts. Split at the middle origin (2026-01-27), coverage before: 1m 50% (n = 10), 3m 30% (n = 10), 6m 30% (n = 10); from it: 1m 100% (n = 10), 3m 100% (n = 7), 6m 100% (n = 4). 19 of the 19 misses come from origins before the split; 18 of 19 are realized volume above P90. With the drift replaced by the trailing mean log return (no registry input) coverage is 1m 85%, 3m 65%, 6m 43%. Not backtested: fee take rate (public and confidential) and its compression toward the floor; holder capture ratio alpha; confidential share of volume and its drift to the target share; terminal FDV/revenue multiple and discount rate; NEAR price and supply paths. 3- and 6-month forecasts from monthly origins overlap, so their errors are correlated and the binomial interval overstates the precision.

| Horizon | n | P10-P90 coverage [90% Wilson] | Binomial p vs 80% | Below P10 / above P90 | Median realized / P50 | PIT histogram (5 bins) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 1 month | 20 | 75% [57%-87%] | 0.58 | 1 / 4 | 1.33x | 1 1 5 5 8 |
| 3 months | 17 | 59% [39%-76%] | 0.06 | 0 / 7 | 2.29x | 0 1 2 5 9 |
| 6 months | 14 | 50% [30%-70%] | 0.01 | 0 / 7 | 4.10x | 0 1 1 3 9 |


## 11. Bear case and early-warning triggers

Value basis: deterministic at median inputs; not a Monte Carlo percentile. Base deterministic FDV (median inputs) $3.09B, implied price $2.26; the Monte Carlo P50 of section 10 is a different statistic and is not what the drawdowns below are measured against. drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed

| Scenario | Deterministic FDV (median inputs) | FDV drawdown | Implied price | Price drawdown | Flow crossover |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fee_race_to_zero | $476.4M | -84.6% | $0.35 | -84.6% | none within horizon |
| governance_stalemate | $3.09B | +0.0% | $2.22 | -1.8% | month 30 |
| post_incentive_decay | $1.23B | -60.4% | $0.90 | -60.4% | none within horizon |
| solver_cartelization | $1.66B | -46.4% | $1.21 | -46.4% | month 31 |
| combined worst | $268.5M | -91.3% | $0.19 | -91.5% | none within horizon |


### 11.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)
| Scenario | Metric | Now | Trigger | Status | Monitor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| fee_race_to_zero | net_take_bps_30d | 4.16 bps | < 3.00 bps | not breached | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue (sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days). |
| governance_stalemate | max_inflation_rate | 2.50% | > 1.60% | **BREACHED** | https://free.rpc.fastnear.com (EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)). Note: breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted |
| post_incentive_decay | volume_30d_vs_record_30d | -14.4% | <= -40.0% | not breached | https://nearstats.org/api/near/summary (intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1). |
| solver_cartelization | hhi_solver | n/a | > 3,500 | not measured | https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50 (HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)); secondary headroom_cross_vm_bps +1.10 bps < 0 bps (not breached). Note: no execute_intents fill with an attributable solver was parsed this run; solver HHI unmeasured or too thin and cross-VM headroom +1.10 bps, not negative; trigger not measured (trigger_breached null, not counted as breached or clear); deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = 1,795 |


### 11.2 Scenario narratives
**Aggregator bypass: public take races to 1 pip.** Third-party frontends route around near.com and the public gross take collapses from 18.0 bps to 0.01 bps (the bare intents.near contract fee); confidential execution reprices from 20 bps to 5 bps. Capture ratio alpha is held at 23%, so the hit is price, not allocation. Deterministic (median-input) FDV -84.6% to $476.4M; implied price $0.35. Evidence against it: live cross-VM headroom is +1.1 bps, so a bypassing frontend must first give up that execution edge. Trigger: DefiLlama 30d net take (gross x alpha) below 3.0 bps (now 4.2 bps).

**Governance stalemate: 2.5% issuance forever.** Validators never enact the SVRN cut: max_inflation_rate stays at 2.50% for the full horizon instead of gliding to 1.60%. Protocol cash flows do not change, so FDV moves +0.0%; the damage is dilution: 24,656,159 more NEAR outstanding at the horizon and a per-token value of $2.22 (-1.8% vs base). Net-float crossover: month 30 (base: month 24). This scenario is live today: the on-chain cap reads 2.50% and no cut has been enacted.

**Post-incentive volume decay (NEAR@3.33 unwind).** Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume $122.9M -> $49.2M (-60%), confidential $11.7M -> $3.5M (-70%) and confidential TVL x0.3 (nearstats flags that TVL unverified). Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV -60.4% to $1.23B; implied price $0.90. Current 30d volume $4.41B is 86% of the 30d record $5.15B; the trigger fires at -40%.

**Solver cartelization: HHI_solver > 3,500, 1Click loses the spread.** Two market makers take most fills (HHI_solver > 3,500) and spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM (headroom -2 bps). Keeping flow costs the same 2 bps of take (18.0 bps -> 16.0 bps) while compression runs at 0.15/month. Deterministic (median-input) FDV -46.4% to $1.66B; implied price $1.21. Live: no solver fill could be attributed from the sampled execute_intents payloads this run; deposit-source HHI over external predecessors 1,795 (not a solver measure); cross-VM headroom +1.1 bps; trigger at HHI_solver > 3,500 or headroom < 0.

### 11.3 Falsification summary
fee_race_to_zero: public gross take at 0.01 bps and confidential at 5 bps puts the deterministic FDV at $476.4M (-84.6%); watch DefiLlama near-intents 30d net take weekly, trigger < 3.0 bps, now 4.2 bps (not breached). governance_stalemate: no SVRN cut (cap 2.50% for 36 months) leaves the deterministic FDV at $3.09B (+0.0%) but dilutes per-token value to $2.22 (-1.8%) with crossover month 30; watch max_inflation_rate in EXPERIMENTAL_protocol_config, trigger > 1.60%, now 2.50% (BREACHED). post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at $1.23B (-60.4%); watch nearstats 30d volume against its 30d record weekly, trigger <= -40%, now -14.4% (not breached). solver_cartelization: HHI_solver > 3,500 with cross-VM headroom at -2 bps puts the deterministic FDV at $1.66B (-46.4%); watch the execute_intents solver HHI (now n/a) and the live quote-race headroom (now +1.1 bps) weekly (not measured). All four at once: deterministic FDV $268.5M (-91.3% vs base $3.09B); 1 of 3 measured triggers currently breached (1 not graded this run, inconclusive or not measured: solver_cartelization), and the thesis is falsified if any trigger holds for 30 consecutive days.

## 12. Further evidence: take-rate history, size limits, fee share, wider peers

### 12.1 Fee-pool share against competing cross-chain routers

**NEAR Intents takes 26.9% of the six-protocol cross-chain fee pool over the 30 days to 2026-11-21, rank 2 of 6 behind Relay at 41.0%; its rolling 30-day share moved from 35.0% to 26.9% over 182 days (low 2.5% on 2026-09-13, high 45.3% on 2026-07-04) and the linear trend (-5.38 pp per 30 days, 90% interval -8.61 to -2.15) is falling, with the interval excluding zero.**

Cuts against the bull case: NEAR Intents is losing share of the fees these routers collect, so fee growth has to come from the pool growing, not from share capture. It is overturned by a positive share trend whose 90% interval excludes zero. Relay collects 1.5x NEAR Intents' fees under its own adapter's definition. NEAR Intents' own 30-day fees went from $2.90M to $7.30M over the window; the pool went from $8.30M to $27.11M. With Relay excluded the share is 45.6% against 48.8% at the start of the window (-1.35 pp per 30 days, 90% interval -2.32 to -0.39).

| Rank | Protocol | 30d fees | Share | 90d fees | Days of data | Fee definition (adapter text) |
| ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| 1 | Relay | $11.10M | 41.0% | $253.16M | 214 | Platform fees, integrator app fees and swap costs paid by users on Relay bridges and swaps, excluding execution costs (network gas). |
| 2 | **NEAR Intents** | $7.30M | 26.9% | $20.63M | 562 | Gross fees charged on NEAR Intents swaps - the protocol fee plus the affiliate (distribution) fee each frontend collects, summed across all integra... |
| 3 | THORChain DEX | $4.63M | 17.1% | $9.55M | 2052 | Slip-based liquidity (swap) fees paid by users on each chain's THORChain pools, gross outbound fees and slashing fees paid into the Reserve, and af... |
| 4 | Chainflip | $3.43M | 12.6% | $6.90M | 1055 | Chainflip AMM: Includes Swap, Broker, Ingress, Egress and Network Fees for Buy/Burn Mechanism |
| 5 | deBridge | $515.8K | 1.9% | $1.57M | 1332 | All fees paid by users for swap and bridge tokens via deBridge. |
| 6 | Across | $137.3K | 0.5% | $329.3K | 1299 | Total fees paid by users for bridge txs, counted on the destination chain at the time of the deposit. |


| NEAR Intents rolling 30d share | Now | 30 days ago | 90 days ago | Window start |
| :--- | ---: | ---: | ---: | ---: |
| All included protocols | 26.9% (2026-11-21) | 14.1% (2026-10-22) | 12.1% (2026-08-23) | 35.0% (2026-05-23) |
| Relay excluded | 45.6% (2026-11-21) | 53.2% (2026-10-22) | 55.9% (2026-08-23) | 48.8% (2026-05-23) |


Trend of the rolling share: -5.38 pp per 30 days, 90% interval -8.61 to -2.15 (183 points, Newey-West 60 lags, R^2 0.48). Relay excluded: -1.35 pp per 30 days, 90% interval -2.32 to -0.39. Daily share, no overlap: -3.67 pp per 30 days, 90% interval -6.31 to -1.04. Excluding THORChain DEX (zero-fee run in the window): share 32.5% now against 41.6% at window start, trend -5.45 pp per 30 days, 90% interval -8.98 to -1.92.

Window: 2026-04-24 to 2026-11-21 (212 days common to all 6 protocols, set by Relay's first day). Trailing days left out as not final: 2026-11-22, 2026-11-23, 2026-11-24. Source: DefiLlama `summary/fees/<slug>?dataType=dailyFees`; records `defillama/fee_pool:<slug>:dailyFees` in the manifest.

Limits:

- Fee share is not volume share: a router charging more per dollar routed has a larger fee share at the same volume. DefiLlama's bridge-volume API is paid, so no volume-side comparison is made here.
- Adapter fee definitions differ, so the pool sums unlike quantities; each adapter's own text is quoted next to its protocol (`protocols[].methodology_fees`). The ex-Relay share is published because Relay's adapter counts integrator app fees and swap costs.
- The common window is 212 days (2026-04-24 to 2026-11-21), set by Relay's first day; the trend describes these months only.
- Routers outside DefiLlama's fee coverage (LI.FI and other aggregators) are absent, so the pool is these six protocols, not the cross-chain market.
- Rolling 30-day points overlap by 29 days; the interval uses a Newey-West error with 60 lags, and the daily non-overlapping share trend is reported as a cross-check.
- THORChain is measured by DefiLlama's `thorchain-dex` adapter (swap, outbound and affiliate fees); the `thorchain` slug is the chain's native transaction fee and is not a routing fee.
- The share path is not a line: it ranged from 2.5% (2026-09-13) to 45.3% (2026-07-04) and the linear trend explains 48% of its variance. Read the slope as the average drift over the window, not as a forecast.
- Relay's 30-day fees peaked at $205.95M on 2026-09-22, 14.7x its window median of $14.04M. NEAR Intents' share around that date moves with that surge in the denominator, not with a change in its own fees. Whether the surge is user-paid routing fees or an adapter artefact cannot be settled from this endpoint.
- THORChain DEX reports zero fees on 38 days of the window (longest run 37 days, 2026-05-16 to 2026-06-21). The zeros are kept as reported; if they are an adapter gap, the other protocols' shares are overstated for rolling windows that include those days. See the robustness share excluding it.

### 12.2 Size limits: the largest clip each router quotes

**1Click stops quoting at a smaller size than a competitor on 2 of 3 corridors: ETH USDC -> SOL USDC, $500K against LI.FI $5M; Base USDC -> Arbitrum USDC, $500K against LI.FI $5M.**

Dry quotes at $1K, $10K, $50K, $250K, $500K, $1M, $2.5M, $5M on each benchmarked corridor, run 2026-11-24T06:05:15.423Z: 59 quoted, 21 refused, 0 errors, 0 not attempted, 8 on routes the venue does not serve (88 cells, 25.426 s against a 75.0 s budget).

| Corridor | Venue | Largest size quoted | Cost at $250K | Cost at largest size | First size refused |
| :--- | :--- | ---: | ---: | ---: | ---: |
| ETH USDC -> SOL USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| ETH USDC -> SOL USDC | Relay | $1M | 3.00 bps | 3.00 bps | $2.5M |
| ETH USDC -> SOL USDC | LI.FI | $5M | 25.00 bps | 25.00 bps | none on the ladder |
| ETH USDC -> SOL USDC | Across | does not route | n/a | n/a | n/a |
| ETH USDC -> native BTC | 1Click | $1M | 19.11 bps | 21.24 bps | $2.5M |
| ETH USDC -> native BTC | Relay | $50K | n/a | 17.79 bps | $250K |
| ETH USDC -> native BTC | LI.FI | $1M | 31.01 bps | 37.26 bps via NEAR Intents | $2.5M |
| Base USDC -> Arbitrum USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| Base USDC -> Arbitrum USDC | Relay | $2.5M | 1.00 bps | 1.00 bps | $5M |
| Base USDC -> Arbitrum USDC | LI.FI | $5M | 25.00 bps | 25.00 bps | none on the ladder |
| Base USDC -> Arbitrum USDC | Across | $500K | 1.00 bps | 1.00 bps | $1M |


Cost: (amount in - amount out) / amount in x 1e4: on raw units where both legs are the same stablecoin, else on USD legs valued at one common price per cell (1Click token-list oracle, else the median of the venues' implied prices), as in execution_bench.

On this run 1Click quoted at least $1M on 1 of 3 corridors and stopped below a competitor on 2. That cuts against the case that the solver network already carries institutional clips on those routes: fee growth there has to come from retail-size flow until solver inventory deepens. On ETH USDC -> native BTC the largest competitor quote (LI.FI $1M) is 1Click execution resold; the largest quote on an independent route was $50K (Relay). Repeated runs in which 1Click quotes the same rungs its competitors do would overturn this reading.

Limits:
- A dry 'no liquidity' reflects the solvers' quoting policy at that moment. It is not proven hard depth, and a dry quote is not a fill.
- One run is one observation. Solver inventory and venue limits move within minutes; re-run before relying on a rung.
- Every figure is the largest size quoted on an eight-rung ladder ($1K to $5M), not depth. Sizes between two rungs were not observed.
- Cells marked not attempted did not complete inside the time budget. They carry no information about liquidity.

Raw responses: ledger records `ladder:<venue>:<corridor_id>:<size_usd>`; data in `snapshot.liquidity_ladder`.

### 12.3 Wider peer set: FDV to revenue across the top revenue chains

**The 60x terminal multiple cap sits at the 20th percentile of 15 peers (3 of 15 trade at or below it) on FDV to annualised 30-day revenue; the wide median is 394x (bootstrap 90% interval 187x to 982x), and NEAR on L1 gas revenue alone trades at 4,403x, the 87th percentile.**

The cap is at or below the upper quartile of the set (1,731x), so the model's terminal value does not rest on a multiple richer than what the market pays for chain revenue today. On L1 gas revenue alone NEAR (4,403x) is priced above the wide median (394x), so NEAR is not cheap on chain revenue; the long-term case has to be carried by Intents revenue, not by the L1 multiple. This reading is overturned if a re-run puts the cap above the 75th percentile of the set (peer multiples compressing toward 60x) or if the set shrinks below 8 peers.

| Chain | Token | Revenue, 30d | Revenue, annualised | FDV | FDV / revenue | Note |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| Dexalot | ALOT | $177,760 | $2.2M | $4.0M | 1.9x | DefiLlama types this adapter 'protocol', not 'chain': its revenue is not plain chain gas revenue |
| Quai | QUAI | $175,241 | $2.1M | $8.3M | 3.9x | revenue is merged-mining block rewards earned on other chains and spent on QUAI buyback and burn (the adapter's own Fees text), not gas paid on Quai |
| **Model floor** |  |  |  |  | **8x** | terminal_multiple_floor (assumption) |
| Polygon | POL | $1.3M | $15.4M | $829.0M | 53.9x |  |
| **Model cap** |  |  |  |  | **60x** | terminal_multiple_cap (assumption); the multiple the model uses |
| Tron | TRX | $23.6M | $287.0M | $29.34B | 102x |  |
| **NEAR (L1 + Intents, the model's basis)** | NEAR | $1.8M | $21.8M | $3.99B | **183x** | comps.near_combined; not like for like (no peer row includes app revenue) |
| Arbitrum | ARB | $513,878 | $6.3M | $1.17B | 187x | L2 governance token: sequencer revenue accrues to the DAO treasury, not to ARB by protocol rule |
| OP Mainnet | OP | $69,645 | $847,348 | $307.5M | 363x | L2 governance token: sequencer revenue accrues to the Optimism Collective, not to OP by protocol rule |
| Aptos | APT | $105,100 | $1.3M | $468.2M | 366x |  |
| Monad | MON | $280,590 | $3.4M | $1.35B | 394x |  |
| ICP | ICP | $148,943 | $1.8M | $1.18B | 650x |  |
| Avalanche | AVAX | $382,472 | $4.7M | $3.21B | 690x |  |
| Filecoin | FIL | $92,709 | $1.1M | $1.11B | 982x |  |
| Ethereum | ETH | $6.9M | $83.7M | $207.73B | 2,480x |  |
| Solana | SOL | $1.0M | $12.3M | $45.65B | 3,726x |  |
| **NEAR (L1 gas revenue only)** | NEAR | $74,417 | $905,407 | $3.99B | **4,403x** | subject, not counted in the set |
| Hyperliquid L1 | HYPE | $1.1M | $12.9M | $60.94B | 4,730x | chain row covers HyperEVM gas only; HYPE's FDV is priced mostly on the HyperCore exchange, whose revenue DefiLlama books under separate Hyperliquid protocols (the model's three-peer set uses that parent) |
| BSC | BNB | $1.1M | $13.6M | $72.69B | 5,363x | exchange-linked token: BNB's FDV also prices Binance exchange utility, not only BNB Chain's fee burn |

Distribution of FDV / revenue across 15 peers: median 394x (bootstrap 90% interval 187x to 982x; 10,000 resamples, seed 20261114), P25 144x, P75 1,731x, IQR 1,587x, range 1.9x to 5,363x. The 60x cap: 3 of 15 peers at or below it (20th percentile). The 8x floor: 2 of 15 (13th percentile). NEAR on L1 gas revenue only: 4,403x, the 87th percentile; on the model's combined L1 + Intents basis 183x, which would be the 27th percentile (not like for like).

Without the 6 flagged rows (9 peers): median 650x, P25 366x, P75 982x; 1 at or below the cap. For contrast, the three-peer median the model uses (Solana, Ethereum, Hyperliquid) is 2,480x (comps.median_fdv_to_revenue_ex_near), which the model clips to the 60x cap.

Inclusion rules (fixed before any multiple was computed):
- Universe: every DefiLlama fees-overview row with category 'Chain' and 30-day revenue (dataType=dailyRevenue) above zero.
- Ranking: by 30-day revenue, highest first. No chain is added or removed by hand after seeing its multiple.
- Peers: the first 15 chains in that ranking that have their own token with a CoinGecko fully diluted valuation.
- Excluded, each listed with its reason: chains with no native token; chains whose token has no FDV on CoinGecko; chains not in the chain-to-token mapping table (configuration in wide_peers.py); a second row for a token already counted.
- Flagged, not dropped: L2 tokens, exchange-linked tokens, rows whose adapter books something other than chain gas revenue and rows whose DefiLlama adapter is not typed 'chain'. They stay in the distribution; a sensitivity without them is reported next to it.
- NEAR is the subject. It is positioned against the set on the same basis (its own chain row and CoinGecko FDV) and is not counted in it.
- Multiple: FDV / (30-day revenue x 365 / 30). Percentile of a value: share of peers with a multiple at or below it.

Excluded inside the cut (3); 52 further chains rank below the last peer and were not evaluated:
- Base (rank 3 by revenue, $2.9M in 30 days): no native token: Coinbase-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.
- Robinhood Chain (rank 8 by revenue, $908,736 in 30 days): no native token: Robinhood-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.
- Elysium (rank 15 by revenue, $117,667 in 30 days): not in the chain-to-token mapping table (wide_peers.COINGECKO_ID_BY_SLUG); not evaluated.

Caveats:
- FDV to revenue on 30 days annualised is noisy: one busy or quiet month moves a chain's multiple by a large factor.
- Revenue definitions differ by chain adapter (burned base fees, sequencer profit, treasury share, buyback and burn); the adapter's own text is carried per row.
- Token FDV for an L2 or an exchange-linked token does not accrue chain revenue the way an L1 gas token does; those rows are flagged and a sensitivity without them is shown.
- Selection: ranking by revenue picks the chains with the most revenue, which pulls their multiples down relative to the long tail of low-revenue chains.
- NEAR's multiple here uses L1 gas revenue only. The model values NEAR on L1 plus Intents revenue (comps.near_combined), which no peer row here has an equivalent of.
- One snapshot. Nothing here is a time series, and the cap's position will move with token prices and monthly fee volume.

Sources: `defillama/overview:fees:dailyRevenue` sha256 `1bf84d7619f79af4`, `coingecko/coins_markets_wide` sha256 `46314d89dd77afda`; fetched 2026-11-24T06:05:11.697Z. Field: `snapshot.wide_peers`.

### 12.4 Take-rate history

Gross take compressed over the trailing year: the rolling 30-day rate is 18.2 bps on 2026-11-22 against 20.6 bps a year earlier, while average daily volume went from $121M to $135M; the trailing-365d log-linear trend is -28% per year (90% CI -42% to -11%), which excludes zero, and the trailing-180d trend, +61% per year (90% CI +38% to +89%), does not show the decline continuing.

| Window | Days (UTC) | Gross take (bps) | Net take (bps) | Holder take (bps) | Avg daily volume |
| :--- | :--- | ---: | ---: | ---: | ---: |
| last 30d | 2026-10-24 to 2026-11-22 | 18.21 | 4.16 | 4.16 | $135M |
| 30-60d ago | 2026-09-24 to 2026-10-23 | 16.25 | 5.21 | 5.21 | $138M |
| 60-90d ago | 2026-08-25 to 2026-09-23 | 14.78 | 3.44 | 3.44 | $148M |
| 150-180d ago | 2026-05-27 to 2026-06-25 | 12.27 | 2.83 | 2.83 | $82M |
| 330-360d ago | 2025-11-28 to 2025-12-27 | 20.49 | 0.88 | 0.00 | $67M |


- **Trend, trailing 365 days** (2025-11-23 to 2026-11-22, 365 rolling points): -28.2% per year, 90% CI -42.3% to -10.7% (excludes zero; Newey-West, 60-day lag).
- **Trend, trailing 180 days** (2026-05-27 to 2026-11-22, 180 rolling points): +61.4% per year, 90% CI +37.5% to +89.4% (excludes zero; Newey-West, 60-day lag).
- **Trend, full history** (2025-06-08 to 2026-11-22, 533 rolling points): +83.7% per year, 90% CI -1.2% to +241.7% (includes zero; Newey-West, 60-day lag). Dominated by the 2025 fee ramp from zero; not a competition signal.
- **Robustness of the trailing-365d trend** (reported, not graded): 30-day lag -41.1% to -12.5%; 120-day lag -41.3% to -12.2%; 13 non-overlapping 30-day windows -22.1% per year, Student-t 90% CI -36.8% to -4.0%.
- **Elasticity to volume, trailing 365 days** (365 days, 0 dropped for zero fees or volume): a 1% rise in daily volume goes with a -0.05% change in daily gross take, 90% CI -0.13 to +0.03 (includes zero; R2 0.01).
- **Elasticity to volume, full history** (553 days, 9 dropped for zero fees or volume): a 1% rise in daily volume goes with a +0.70% change in daily gross take, 90% CI +0.20 to +1.19 (excludes zero; R2 0.36).
- **Regime break** (first aligned day with dailyHoldersRevenue > 0): 2026-02-23. Pooled gross take 17.49 bps over the 289 days before (18.09 bps over the 92 of those inside the trailing year) and 15.85 bps over the 273 days since; net take 1.37 bps before (trailing year) and 3.38 bps since.
- **Range, trailing 365 rolling points**: gross take high 24.49 bps (2025-12-16), low 11.82 bps (2026-06-22).
- **Floor read** (trailing 365 rolling points): gross take was below the 0.5 bps model floor on 0 of them (minimum 11.82 bps, 2026-06-22); net take was below the 3 bps fee-race trigger on 270 (minimum 0.00 bps, 2025-12-31), and on 149 of the 244 windows that start after the regime break.

**Read.** This cuts against the bull case: gross take fell at 28% per year over the trailing year with an interval that excludes zero (non-overlapping check: -22% per year, 90% CI -37% to -4%, also excludes zero), so the claim that pricing power has held while volume grew is not supported by the fee history; the level is still 36x the 0.5 bps model floor. The trailing-180d trend is +61% per year (90% CI +38% to +89%): the decline is not visible in the last six months. A trailing-365d interval that includes zero again would overturn this read; a 180d interval wholly below zero would show compression still in progress. NEAR's captured (net) take went from 2.1 bps to 4.2 bps over the same span and sat under the 3 bps fee-race trigger on 270 of 365 trailing rolling points.

Data: 562 aligned settled days 2025-05-10 to 2026-11-22 (raw); unsettled trailing day(s) excluded: 2026-11-23. Source: defillama/fees:near-intents:dailyFees sha256 fc1b609784f6...; defillama/fees:near-intents:dailyRevenue sha256 b448d3d954c8...; defillama/fees:near-intents:dailyHoldersRevenue sha256 c1038a726baf...; defillama/dexs:near-intents sha256 3afe3d627d15....

Limits:
- Early history mixes fee regimes: the DefiLlama fee chart ramps from zero in mid-2025 and net revenue is zero until the first sweep, so the full-history trend measures fees being switched on. Read the trailing-365d figures.
- Fees, revenue and holders revenue follow DefiLlama's near-intents adapter definitions: gross fees include the affiliate fee each frontend keeps; revenue is NEAR swept into the revenue wallets and is booked on the sweep day, so net take is lumpy and can exceed fees on single days. An adapter revision restates the whole series.
- Rolling 30-day points overlap (29 of 30 days shared), so about 12 independent observations sit in a year. A Newey-West interval on such points is too narrow at this sample size: in the seeded null simulation in quant/tests/test_take_rate_series.py a trendless series is flagged well above the nominal 10% of the time. The non-overlapping 30-day check (Student-t) stays near its nominal size and is the stricter read: treat a trend as established only when both intervals exclude zero. An interval that includes zero means no decline was detected, not that none exists.
- The elasticity regresses fees/volume on volume: noise in daily volume enters both sides and pushes the estimate negative.

### 12.5 Volume engine: GBM against a block bootstrap, out of sample

The block bootstrap does not repair the volume engine: P10-P90 coverage (1m 20/20 (100%, p 0.02), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33)) is rejected against 80% for over-coverage at 1m and 3m; the pass at 6m rests on 14 overlapping forecasts, which is weak evidence; its band is 2.0x to 3.2x the GBM's log width, so it covers by being wide, not by being sharp; the GBM is rejected at 2 of 3 horizons (1m 15/20 (75%, p 0.58), 3m 10/17 (59%, p 0.06), 6m 7/14 (50%, p 0.01)), so the two engines bracket realized dispersion and neither is calibrated.

| Engine | Horizon | n | Inside | Coverage | Binomial p vs 80% | Below P10 / above P90 | Realized / median | Band width, ln(P90/P10) | Verdict |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| GBM, registry drift (valuation engine) | 1m | 20 | 15/20 | 75% | 0.58 | 1 / 4 | 1.33x | 1.32 | 80% not rejected |
| GBM, registry drift (valuation engine) | 3m | 17 | 10/17 | 59% | 0.06 | 0 / 7 | 2.29x | 2.28 | 80% rejected |
| GBM, registry drift (valuation engine) | 6m | 14 | 7/14 | 50% | 0.01 | 0 / 7 | 4.10x | 3.15 | 80% rejected |
| Block bootstrap, resampled drift | 1m | 20 | 20/20 | 100% | 0.02 | 0 / 0 | 0.87x | 2.63 | 80% rejected |
| Block bootstrap, resampled drift | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.43x | 6.16 | 80% rejected |
| Block bootstrap, resampled drift | 6m | 14 | 13/14 | 93% | 0.33 | 1 / 0 | 0.11x | 9.98 | 80% not rejected |
| Block bootstrap, registry drift (shape only) | 1m | 20 | 14/20 | 70% | 0.26 | 0 / 6 | 1.98x | 2.52 | 80% not rejected |
| Block bootstrap, registry drift (shape only) | 3m | 17 | 8/17 | 47% | 0.003 | 0 / 9 | 37.48x | 6.11 | 80% rejected |
| Block bootstrap, registry drift (shape only) | 6m | 14 | 1/14 | 7% | <0.001 | 0 / 13 | 5781.23x | 9.94 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 1m | 20 | 20/20 | 100% | 0.02 | 0 / 0 | 0.86x | 3.05 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.38x | 7.82 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 6m | 14 | 14/14 | 100% | 0.09 | 0 / 0 | 0.10x | 12.60 | 80% rejected |


Target coverage 80%; verdict rule: exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10. Bootstrap: 10,000 paths per origin, seed 20261114, mean block length 8 to 58 days across origins (median 12). At 1 month the bootstrap band is 2.00x the GBM band in log width. At 3 months the bootstrap band is 2.70x the GBM band in log width. At 6 months the bootstrap band is 3.16x the GBM band in log width.

Power at one month (n = 20): the test accepts 14 to 19 forecasts inside the band. A model whose true coverage is 60% would be rejected 75% of the time and one at 70% only 39% of the time, so a pass does not separate a calibrated engine from a mildly miscalibrated one.

Valuation effect, volume. The valuation uses the GBM; this is unchanged. From the latest origin (2026-11-23, trailing 30-day volume $4.15B), 30-day volume 12 months ahead as a multiple of current, P10 / P50 / P90: GBM 0.51x / 1.49x / 4.32x; bootstrap with the same expected path 0.13x / 0.77x / 4.44x; bootstrap with its own resampled drift 0.54x / 3.22x / 18.63x.

Valuation effect, FDV. Feeding bootstrap volume paths (same expected path, same price, take-rate and issuance paths, 10,000 paths) through the Monte Carlo gives FDV P10 / P50 / P90 of $79M / $508M / $4.55B against the base $538M / $1.80B / $6.31B (0.15x / 0.28x / 0.72x of base). The base run reproduces `sotp.fdv_percentiles` exactly. The bootstrap run holds the mean volume path fixed, so its lower median is the convexity cost of a wider distribution. These are variant figures; no headline number uses them.

The valuation uses the GBM. At the same expected path the bootstrap puts 30-day volume 12 months out at 0.13x / 0.77x / 4.44x of current (P10 / P50 / P90) against the GBM's 0.51x / 1.49x / 4.32x, a band 1.7x as wide in log terms; through the same Monte Carlo FDV P10 / P50 / P90 becomes 0.15x / 0.28x / 0.72x of the base. The backtest rejects the bootstrap for over-coverage, so read this as a stress bound on volume dispersion (with the mean path held fixed, a wider distribution lowers the median), not as a better central estimate.

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
| NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB) | **VERIFIED_ON_CHAIN** | intents.near storage_usage 14,139,777,110 bytes = 141,398 NEAR locked; 288,242 NEAR across 8 tracked contracts | near_rpc/view_account:intents.near sha256 7f2d6501f60f... @ block 225,964,398; storage_amount_per_byte from EXPERIMENTAL_protocol_config | high | growth 38,256,488 B/day = 382.6 NEAR/day over 30.4 d (archival); a 0.01 NEAR/KB lock is released if state is deleted, so it is a sink while state grows |
| Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap | **VERIFIED_ON_CHAIN** | 25,722.96 NEAR minted at epoch start 225,949,937 x 1,274.9 epochs/yr = 32,794,304 NEAR/yr (2.4985%), -0.06% vs nominal 32,813,765 | near_rpc/block:225949937 sha256 035505273805... and its predecessor by prev_hash; previous epoch start 225906737 | high | second independent jump 26,095.22 NEAR; within-epoch drift -210.27 NEAR/epoch is the net gas burn |
| Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC | **VERIFIED_LIVE_API** | median headroom +1.10 bps over 3 comparable cells (dest_units); competitor ceiling 3.00 bps | oneclick/relay/lifi/across quote records 2026-11-24T06:05:11.696Z | medium | $500: +1.46 bps vs relay (rank 1/3); $50,000: +1.10 bps vs relay (rank 1/3); $250,000: +0.98 bps vs relay (rank 1/3); no 1Click capacity failures |
| Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC | **VERIFIED_LIVE_API** | 1Click delivers +4.01 bps more BTC per USDC (median over 3 cells, dest_units; no USD oracle in the ranking) | oneclick/lifi/relay quote records 2026-11-24T06:05:11.696Z | medium | clip-dependent: $500: -15.67 bps vs relay (rank 2/3); $50,000: +4.01 bps vs relay (rank 1/3); $250,000: +14.51 bps vs lifi (rank 1/2); LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used |
| EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative) | **VERIFIED_LIVE_API** | median headroom -1.02 bps over 3 cells (dest_units; 1Click trails) | oneclick/across/relay/lifi quote records 2026-11-24T06:05:11.696Z | medium | $500: +0.03 bps vs across (rank 1/4); $50,000: -1.02 bps vs across (rank 3/4); $250,000: -1.02 bps vs across (rank 3/4); the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins |
| Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material | **DERIVED** | deposit/caller HHI_external 1,795 [90% CI 1,471-1,914] (N_eff 5.57), ex-AI-agent 2,107; AI-agent share 24.1% (>= 10% materiality line), bridge share 44.8% | nearblocks/txns:intents.near:p1 sha256 0f9d1fe7967d... ... p8 | low | 200 unique receipts over 36 s; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources (bridge callbacks, direct callers), not solvers |
| Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers | **NOT_SUPPORTED** | not measured: 0 solver fill participations (< 10) in 0 decoded execute_intents receipts | nearblocks/txns:intents.near:p1 sha256 0f9d1fe7967d... ... p8 + 8 method-filtered execute_intents page(s); args.signed[].payload.message (NEP-413 signer_id) | low | 0 execute_intents receipts decoded; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty |
| Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume | **NOT_SUPPORTED** | 8.7% (band 8.0%-8.8%) estimated on-chain: Confidential Intents Treasury 24h inflow $17.5M / outflow $17.7M against 24h volume $201.1M; < 10% materiality line | near_rpc/confidential:balances:head sha256 402db227e79d... treasury balances in intents.near (NEAR mainnet RPC) | low | nearstats' split was rejected by the plausibility guard; the share is estimated from the public treasury boundary instead. Biases: same-hour shield/unshield netting and in-shard turnover push it down, solver inventory pushes it up; 24h window |
| Confidential TVL backs the dark-pool engine (Engine 2) | **VERIFIED_ON_CHAIN** | $125.9M TVL read on-chain from the Confidential Intents treasury in intents.near (NEAR-reported via nearstats: $126.6M) | near_rpc/confidential:balances:head sha256 402db227e79d... intents.near mt_batch_balance_of (treasury) | high | Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut (0.7); the confidential take (20 bps) is an assumption |
| Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink | **DERIVED** | alpha 22.9%; gross take 18.21 bps, net take 4.16 bps; buyback sink 18,365 NEAR/day = 21.7% coverage incl. burn and lock | defillama/fees:near-intents:dailyHoldersRevenue sha256 c1038a726baf... / defillama/fees:near-intents sha256 fc1b609784f6... | medium | DefiLlama revenue methodology: NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.near.org and the on-chain buyback). Split by destination wallet into front-end affiliate revenue and Other. Transfers between those wallets are excluded. |
| Chain Signatures (v1.signer) is a growing second usage engine beyond Intents | **NOT_SUPPORTED** | not measured: NearBlocks v1.signer endpoints unavailable this run | nearblocks (none) | none | cumulative_receipts: NearBlocks count endpoint failed; sign rate / trend: no sample window returned |
| The volume engine (GBM with measured sigma) is calibrated out of sample: P10-P90 covers ~80% of realized 30-day volume | **NOT_SUPPORTED** | 1m 15/20 = 75% inside P10-P90 (binomial p 0.58); 3m 10/17 = 59% inside P10-P90 (binomial p 0.06); 6m 7/14 = 50% inside P10-P90 (binomial p 0.01); 1m median realized / forecast median 1.33x (under-prediction); 1m coverage 50% for origins before 2026-01-27, 100% from it; 20 monthly origins 2025-04-02 to 2026-10-24 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 3afe3d627d15... | low | Tests the volume distribution only; the take rate, holder capture, confidential share, multiple and discount rate are not backtested. 3m and 6m forecasts from monthly origins overlap, so their effective sample is smaller than n. |
| A block-bootstrap volume engine (fat tails, autocorrelation) is calibrated out of sample where GBM is not | **NOT_SUPPORTED** | block bootstrap 1m 20/20 (100%, p 0.02), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33); GBM 1m 15/20 (75%, p 0.58), 3m 10/17 (59%, p 0.06), 6m 7/14 (50%, p 0.01); bootstrap at the GBM's expected path (shape only) 1m 14/20 (70%, p 0.26), 3m 8/17 (47%, p <0.01), 6m 1/14 (7%, p <0.01); bootstrap band 2.0x the GBM's log width at 1m; 20 monthly origins 2025-04-02 to 2026-10-24 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 3afe3d627d15...; valuo.models.volume_bootstrap (seed 20261114, 10000 paths per origin) | low | Inside P10-P90 against an 80% target, exact two-sided binomial p. Low power: at n = 20 the test accepts 14 to 19 hits and rejects a 70%-coverage engine only 39% of the time; 3m and 6m forecasts overlap. Block length (Politis-White) and path count were fixed before coverage was computed; nothing is tuned. The valuation still uses the GBM; this row grades a parallel variant and tests the volume distribution only. |
| NEAR Intents' realized gross take rate is not trending to zero as volume grows | **NOT_SUPPORTED** | rolling 30d gross take 18.21 bps on 2026-11-22 vs 20.59 bps on 2025-11-23; trend -28.2%/yr, 90% CI -42.3% to -10.7% (excludes zero; Newey-West 60d lag, 365 overlapping points); floor 0.5 bps, 0 of 365 trailing points below it; non-overlapping 30d windows (n=13) -22.1%/yr, Student-t 90% CI -36.8% to -4.0%; trailing 180d trend +61.4%/yr, CI +37.5% to +89.4% | defillama/fees:near-intents:dailyFees sha256 fc1b609784f6...; defillama/fees:near-intents:dailyRevenue sha256 b448d3d954c8...; defillama/fees:near-intents:dailyHoldersRevenue sha256 c1038a726baf...; defillama/dexs:near-intents sha256 3afe3d627d15... | low | Graded on the trailing-365d trend only: a decline is counted when the Newey-West 90% interval and the non-overlapping-window Student-t interval both sit below zero; DERIVED needs no such decline and a latest rolling take above the model floor. Gross take includes affiliate fees kept by frontends; NEAR's captured share is the net / holder take. Rolling points overlap, so an interval that includes zero is not proof of a floor. The full-history trend is not used (fee ramp from zero in 2025). |
| 1Click quotes institutional size: at least $1M on every benchmarked corridor | **NOT_SUPPORTED** | ETH USDC -> SOL USDC: 1Click $500K, best competitor LI.FI $5M; ETH USDC -> native BTC: 1Click $1M, best competitor LI.FI $1M (routed through NEAR Intents); Base USDC -> Arbitrum USDC: 1Click $500K, best competitor LI.FI $5M (1 of 3 corridors with an attempted 1Click rung at or above $1M) | 1Click, Relay, LI.FI, Across dry quotes; ledger records ladder:<venue>:<corridor_id>:<size_usd> (81 responses), run 2026-11-24T06:05:15.423Z | low | Largest size quoted on an eight-rung ladder of dry quotes, one run. A dry 'no liquidity' is solver quoting policy at that moment, not proven depth, and a dry quote is not a fill. |
| NEAR Intents is gaining share of cross-chain routing fees | **NOT_SUPPORTED** | 26.9% of the six-protocol fee pool (30 days to 2026-11-21), rank 2 of 6 behind Relay at 41.0%; share at window start 35.0% (212-day common window); trend -5.38 pp per 30 days, 90% interval -8.61 to -2.15; ex-Relay 45.6%, trend -1.35 pp per 30 days, 90% interval -2.32 to -0.39 (share is falling) | defillama summary/fees dailyFees: near-intents, relay, across, debridge, chainflip, thorchain-dex | low | Fee share, not volume share; adapter fee definitions differ; the pool is the protocols DefiLlama covers. A share trend is DERIVED from live fee series, never VERIFIED. |
| The model's terminal multiple cap sits inside the observed peer range of FDV/revenue | **DERIVED** | cap 60x vs 15 chain tokens: 3 of 15 trade at or below it (20th percentile); P25 144x, median 394x [bootstrap 90% 187x to 982x], P75 1,731x, range 1.9x to 5,363x; NEAR L1-only 4,403x (87th percentile); without flagged rows: median 650x, n 9 | defillama/overview:fees:dailyRevenue sha256 1bf84d7619f7... + coingecko/coins_markets_wide sha256 46314d89dd77... | medium | Rule: DERIVED when the cap is at or below the 75th percentile of the wide set and n_peers >= 8. Here the cap is inside the observed range and at or below its upper quartile. FDV/revenue on 30 days annualised, one snapshot; revenue definitions differ by chain adapter; peers ranked by revenue and fixed before any multiple was computed (inclusion_rules, excluded). |


## 14. Assumptions register

### 14.1 Labeled assumptions (slider inputs; never presented as measured)
| Key | Default | Unit | Range | Justification |
| :--- | :--- | :--- | :--- | :--- |
| svrn_target_inflation | 0.016 | ratio_annual | [0.005, 0.03] | SVRN governance proposal to cut the protocol max_inflation_rate from 2.5% to 1.6%; not enacted on-chain (live EXPERIMENTAL_protocol_config.max_inflation_rate is still [1, 40]). |
| svrn_glidepath_months | 24 | months | [6, 48] | QUANT_PIPELINE_SPEC and TERMINAL_UI_SPEC model the 2.5% -> 1.6% cut as a linear 24-month (730-day) glidepath; the proposal itself does not fix the phasing. |
| public_volume_growth_yoy | 1.10251 | ratio_yoy | [0.506615, 1.93408] | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-24 to 2026-11-23 (365 days, DefiLlama dexs/near-intents): +110.3%/yr, 90% CI +50.7% to +193.4% (Newey-West, 30-day lags). Range = that CI. Median trend growth used as EXPECTED growth (conservative). Replaces the registry default +30%. Cross-checks (not used): yoy_trailing_30d +15%; mean_monthly_log_return_12m +11%. |
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
| total_supply_near | 1,312,550,602 | NEAR | measured | RPC block header total_supply at height 225964398 |
| current_max_inflation_rate | 0.025 | ratio_annual | measured | RPC EXPERIMENTAL_protocol_config.max_inflation_rate |
| treasury_share | 0 | ratio | measured | RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this) |
| staked_supply_ratio | 0.453485 | ratio | measured | RPC validators current stake / total_supply (347 validators) |
| annual_issuance_near | 32,794,304 | NEAR_per_year | measured | minted_per_epoch 25722.95905685833 NEAR x epochs_per_year 1274.9040154276968 from total_supply jumps at epoch starts 225906737 -> 225949937 |
| issuance_realization_factor | 0.999407 | ratio | measured | measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path |
| near_price_usd | 3.05 | USD | measured | nearstats price.currentUsd via intents_forensics.price.current_usd |
| daily_volume_usd | 134,575,196 | USD_per_day | measured | intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window (aligned daily charts, 30 complete UTC day |
| gross_take_bps | 18.2063 | bps | measured | intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window (aligned daily charts, 30 complete UTC |
| capture_ratio | 0.228614 | ratio | measured | intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window (aligned daily charts, 30 complete  |
| gas_burn_near_per_day | 733.9331 | NEAR_per_day | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| state_lock_growth_near_per_day | 395.1868 | NEAR_per_day | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| public_volume_growth_yoy | 1.1025 | ratio_yoy | measured | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-24 to 2026-11-23 (365 days, DefiLlama dexs/near-intents): +110.3%/yr, 90% CI +50.7% to +193.4% (New |
| competitive_fee_ceiling_bps | 3.004 | bps | derived | median over cross-VM cells of the best competitor's friction (per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding); the lowest-fric |
| tau_floor_bps | 1.1041 | bps | derived | max(0.5 bps, min(live public take, live cross-VM headroom)) from the execution benchmark (headroom_by_archetype_bps.cross_vm = 1.10 bps). |
| tau_pub_start_bps | 18.0355 | bps | derived | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d; blended live gross take 18.21 bps (DefiLlama daily fees / daily volume summed over the a |
| alpha_capture | 0.228614 | ratio | measured | measured:defillama near-intents dailyHoldersRevenue / fees |
| terminal_multiple | 60 | x_fdv_to_revenue | derived | peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; raw 2480.3x. |
| confidential_share_start | 0.0869363 | ratio | derived | on-chain estimate: Confidential Intents Treasury 24h inflow / (24h volume + inflow) = 8.7% (band 8.0%-8.8%); nearstats split implausible. Estimated from the Con |
| sigma_price_annual | 1.0282 | ratio_annual | measured | nearstats:price-history: 1y daily closes, log-return sigma x sqrt(365). |
| sigma_volume_monthly | 0.239748 | ratio_monthly | measured | measured: monthly log-return sigma of 30-day volume aggregates |


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

241 raw exchanges (189 ok, 52 failed), 12,927,149 bytes hashed; raw bodies persisted under `artifacts/raw` and listed with SHA-256 in `manifest.json`.

| Source | Records |
| :--- | ---: |
| across | 15 |
| coingecko | 2 |
| defillama | 22 |
| lifi | 33 |
| near_rpc | 37 |
| near_rpc_archival | 18 |
| nearblocks | 43 |
| nearstats | 2 |
| oneclick | 36 |
| relay | 33 |


Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):
| Source | Name | HTTP | Error |
| :--- | :--- | :--- | :--- |
| nearblocks | txns_count:intents.near | 410 | HTTP 410 |
| across | quote:eth_usdc_sol_usdc:500 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:50000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:250000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| relay | quote:eth_usdc_btc:250000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Solver has insufficient liquidity for this swap |
| across | ladder:across:eth_usdc_sol_usdc:1000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| relay | ladder:relay:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,35 |
| across | ladder:across:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 730757.383937 US |
| relay | ladder:relay:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,35 |
| relay | ladder:relay:eth_usdc_btc:250000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Solver has insufficient liquidity for this swap |
| across | ladder:across:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 730757.383937 US |
| relay | ladder:relay:eth_usdc_btc:500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $375, |
| across | ladder:across:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 730757.383937 US |
| relay | ladder:relay:eth_usdc_btc:1000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $375, |
| relay | ladder:relay:eth_usdc_btc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $375, |
| relay | ladder:relay:eth_usdc_btc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $375, |
| relay | ladder:relay:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Quote amount exceeds the maximum for this pair |
| oneclick | ladder:1click:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| lifi | ladder:lifi:eth_usdc_btc:2500000 | 404 | HTTP 404: No available quotes for the requested transfer |
| lifi | ladder:lifi:eth_usdc_btc:5000000 | 404 | HTTP 404: No available quotes for the requested transfer |
| nearblocks | txns:v1.signer:count | 410 | HTTP 410 |
| nearblocks | txns:v1.signer:before_date:2026-11-24 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:225833988 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-10-27 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:225572625 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-10-31 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:225311262 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-04 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:225049899 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-08 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-12 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-16 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-20 | 422 | HTTP 422 |


### 16.1 Methodology warnings recorded during the run (19)
- wide_peers: chain 'elysium' ranks 15 by 30-day revenue but has no entry in the mapping table; listed as excluded
- fee_pool: across: 3 malformed, negative or duplicate chart rows skipped
- execution_bench: eth_usdc_sol_usdc $500: venue USD oracles disagree with the cell's common price by more than the +1.46 bps headroom (1click +0.0 bps, relay +2.1 bps, lifi +14.0 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the +1.10 bps headroom (1click +0.0 bps, relay +2.1 bps, lifi +14.0 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +2.1 bps, lifi +14.0 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $500: venue USD oracles disagree with the cell's common price by more than the -15.67 bps headroom (1click +0.0 bps, relay -8.8 bps, lifi +39.8 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $50,000: venue USD oracles disagree with the cell's common price by more than the +4.01 bps headroom (1click +0.0 bps, relay -8.8 bps, lifi +39.8 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $250,000: venue USD oracles disagree with the cell's common price by more than the +14.51 bps headroom (1click +0.0 bps, lifi +39.8 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $500: venue USD oracles disagree with the cell's common price by more than the +0.03 bps headroom (1click +0.0 bps, relay +2.5 bps, lifi +21.8 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +2.5 bps, lifi +21.8 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +2.5 bps, lifi +21.8 bps); headroom is measured on destination units, not USD legs
- intents_forensics: nearblocks txns/count unavailable (HTTP 410); lifetime_receipts null
- intents_forensics: nearblocks execute_intents page 1 carried no usable id/timestamp pairs; solver sample falls back to contiguous cursor pages
- intents_forensics: confidential split: nearstats reports confidential 30d $0.00 (0.0000%), rejected (tvl_without_volume: confidential TVL $125.86M but all-time confidential volume $0.17 of $40.94B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'). Share ESTIMATED ON-CHAIN from the Confidential Intents Treasury: 8.7% (band 8.0%-8.8%; 24h inflow $17.49M, outflow $17.65M, volume $201.13M), replacing the registry assumption 40%
- intents_forensics: take-rate window leaves out 2026-11-23: DefiLlama reports revenue above fees for that day, so its fee figure is not final; the window ends the day before
- chain_signatures: NearBlocks txns/count unavailable (HTTP 410); cumulative receipts null
- chain_signatures: 12 of 12 sample windows failed; rates use the 0 that returned
- sotp: confidential share 8.7% is an ON-CHAIN ESTIMATE from Confidential Intents Treasury boundary flows (band 8.0%-8.8%), not nearstats' split (rejected as implausible); 24h window, biases listed in intents_forensics.volume.confidential_share_estimate
- sotp: peer median FDV/revenue 2480.3x clipped to 60.0x (guardrails [8, 60])
