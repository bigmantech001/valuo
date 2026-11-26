# Valuo IC Memo: NEAR at block 226,265,522

*NEAR Intents clearinghouse + NEAR L1. Generated 2026-11-26T06:05:03.509Z UTC from live mainnet RPC and key-free public APIs; every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section 14.*

| Provenance | Value |
| :--- | :--- |
| NEAR block | 226,265,522 (`7ogAwpFVJ5pgx1jX3v93UFhTzkVY1r9yyExVBWEjabuG`), 2026-11-26T06:05:01.603Z |
| RPC endpoint | https://free.rpc.fastnear.com |
| Snapshot generated | 2026-11-26T06:05:03.509Z UTC, runtime 468.9 s, valuo 0.1.0, schema 1.0.0 |
| Snapshot SHA-256 | `88df224b80a656861428c55f4d66c8207b9c1aac6222e8479906c866518baa19` |
| Monte Carlo | seed 20261114, 10,000 paths, 36 months |
| Raw records | 241 HTTP/RPC exchanges hashed, 50 non-2xx/failed (every one listed in manifest.json) |


## 1. The long-term case, made falsifiable

The long-term case for NEAR at $4.02B: 3 of 7 measured conditions are on track. It holds if the market keeps an L1 multiple (74x revenue needed against a 2,425x peer median) while Intents grows into it; it fails if volume growth stays near 115% a year against the 135% the price implies.

| Condition | Required | Live | Trend | Status |
| :--- | ---: | ---: | :--- | :--- |
| Intents volume compounds fast enough to grow into the price | 135% a year | 115% a year | +64% (30-day volume vs 90 days earlier) | **Behind** |
| Holder revenue (buybacks) scales to support the price at the model's multiple | $141.3M a year | $20.8M a year | +155% (30-day holder revenue vs 90 days earlier) | **Behind** |
| The market keeps valuing NEAR like an L1, not like a fee-only app | 74x | 2,425x | n/a | **On track** |
| 1Click keeps a pricing edge where it competes (cross-VM routes) | > 0 | +1.05 bps | n/a | **On track** |
| Confidential (private) flow keeps growing | > 0 | $22.2M | +198% (confidential TVL vs 90 days earlier) | **On track** |
| Fees retire more NEAR than issuance creates | $431.7M a day | $149.5M a day | n/a | **Behind** |
| Governance cuts issuance from 2.5% to 1.6% | 1.6% | 2.5% | n/a | **Behind** |
| Solver competition stays broad enough to keep spreads tight | <= 3,500 | n/a | n/a | **Not measured** |


How to read it: each requirement is what the market price needs if that condition alone carries the case (from the reverse valuation in section 3), or the threshold the bear case watches (section 11). An investor holding NEAR long-term is betting that the conditions marked Behind close; the ones marked Against are where the case is currently losing. Re-run `make reproduce` to re-grade every row against live data.

## 2. Executive summary

**Model value vs market value.** Market FDV is $4.02B (spot price x on-chain total supply at block 226,265,522). The model's expected-path FDV is $3.29B and its 10,000-path Monte Carlo gives P10 / P50 / P90 = $666.5M / $2.06B / $6.65B. The market sits above the expected path (1.2x it) and at 1.9x the Monte Carlo P50. The model capitalises NEAR Intents holder revenue, L1 gas burn and state-lock flow over 36 months at a 25% discount rate and a 60x terminal multiple; the question below is which input would have to change for it to reach the market price, and whether the evidence allows that.

**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in section 3).

| Input | Base | Required for market FDV | Evidence | Inside evidence |
| :--- | ---: | ---: | ---: | :--- |
| Expected annual public-volume growth (3-year path) | 117.2% | 134.6% | 114.7% | no |
| Starting gross public take rate | 18.17 bps | 26.21 bps | 3.00 bps | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 74x | 2,425x | yes |
| Annual discount rate | 25.0% | 16.9% | 10.0% | yes |
| Confidential share of volume at month 36 | 40.0% | 52.3% | 13.3% | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $114.6M/yr | $141.3M/yr | $20.8M/yr | no |


**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple (74x needed; live peer FDV/revenue HYPE 60x, ETH 2,425x, SOL 3,722x, median 2,425x over n = 3 peers). A 16.9% discount rate would also close it (registry range starts at 10%). The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on Intents cash flow at the model's 60x terminal cap. On cash flow alone (multiple held at the model's 60x), the market price requires 135%/yr expected public-volume growth for 3 years (trailing 12 months: +114.7%), or a 26 bps starting public take (today 18.17 bps, live competitive ceiling 3.00 bps), or $141.3M of annualised holder revenue in year 3 (6.8x today's $20.8M); none of these is inside its measured evidence. Whether NEAR keeps an L1 multiple is the investment question; this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token.

**What you have to believe** (section 4). The three inputs that move FDV most are Terminal FDV / holder-revenue multiple (8.00x to 150x: $558.1M-$8.03B); Expected annual public-volume growth (55.8% to 202.8%: $1.41B-$7.80B); Public take compression speed (per month) (0.0%/month to 15.0%/month: $906.3M-$6.14B). Together they carry 82% of the swing-squared variance proxy. 8 of 17 single-input ranges reach the market FDV.

**Relative value** (section 5). NEAR trades at 42x annualised fees against a peer median of 279x (rank 1 of 4, lowest multiple first; below every peer); at peer FDV/fees multiples NEAR's fees map to $15.42B-$53.15B (cross-check, not a fair value; n = 3 peers); holder revenue covers 22% of the $100.3M/yr security budget.

**Evidence quality flags.**

- Confidential share: ESTIMATED ON-CHAIN at 13.3% (band 11.8%-15.9%). nearstats reported 0.0000%, which its own payload contradicts, so the share is read from the Confidential Intents Treasury instead: 24h inflow $21.7M, outflow $25.9M, against 24h volume $162.9M. Same-hour netting and in-shard turnover bias it down, solver inventory up; one 24h window. Engine 2 ($1.33B of the $3.29B expected-path FDV) is valued on this estimate, not on the 40% registry assumption. On-chain cross-check: the Confidential Intents treasury (`51e8f94d...de7cbe` in `intents.near`) holds $126.6M at block 226,265,535 (210 tokens, 28 unpriced); net 30-day boundary flow $22.2M at today's prices; over 24h at least $21.7M entered and $25.9M left (hourly snapshots, lower bounds), an inflow of 11.8% of 24h volume. Confidential swaps settle on a private chain whose RPC needs authentication, so swap volume itself cannot be read; boundary inflow is a proxy, not the share (it nets same-hour flows and includes solver inventory).
- Deposit/caller HHI 1,956 (bootstrap 90% CI 1,276-2,600) over 30 external receipts spanning 54 s; a point sample, not a market-share estimate.
- Solver HHI not measured. Cartel trigger: not measured.
- Bear case: 1 of 3 graded early-warning triggers breached; not graded this run: solver_cartelization. Combined-worst deterministic FDV $290.5M (-91%).

## 3. What the market is pricing (reverse valuation)

Basis: deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base. Solver: scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12. Market FDV $4.02B; expected-path model FDV $3.29B (gap 1.2x); Monte Carlo P50 $2.06B (gap 1.9x). Every required value is the expected-path requirement; the P50 sits lower by lognormal convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).

| Input | Base | Required for market FDV | Evidence | Evidence basis | Inside evidence |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Expected annual public-volume growth (3-year path) | 117.2% | 134.6% | 114.7% | trailing-12-month NEAR Intents 30-day volume growth | no |
| Starting gross public take rate | 18.17 bps | 26.21 bps | 3.00 bps | live competitive fee ceiling (median best-competitor friction, cross-VM cells) | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 74x | 2,425x | peer median FDV / annualised revenue ex-NEAR (unclipped) | yes |
| Annual discount rate | 25.0% | 16.9% | 10.0% | low end of the registry discount-rate range (10%-40%) | yes |
| Confidential share of volume at month 36 | 40.0% | 52.3% | 13.3% | on-chain estimate of the confidential share (Confidential Intents Treasury 24h boundary flow / 24h volume) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $114.6M/yr | $141.3M/yr | $20.8M/yr | current annualised holder revenue (30-day window x 365.25/30) | no |

- Justifying $4.02B needs 135% expected annual public-volume growth for 3 years (base 117%); trailing-12-month Intents volume growth was 115%.
- Justifying $4.02B needs a starting gross public take of 26.2 bps (decaying to the 1.05 bps floor at 3%/month) versus 18.17 bps today; the live competitive fee ceiling is 3.00 bps.
- Justifying $4.02B needs a 74x terminal FDV/holder-revenue multiple; the live peer median is 2,425x (HYPE 60x, ETH 2,425x, SOL 3,722x) and the model caps it at 60x.
- Justifying $4.02B needs a 16.9% discount rate versus 25% base; the registry range is 10%-40%.
- Justifying $4.02B needs the confidential share to reach 52% by month 36; the on-chain estimate today is 13% (band 12%-16%).
- Justifying $4.02B at the 60x base multiple needs $141M of annualised holder revenue in year 3 (1.2x the base path's $115M), versus $21M today (89%/yr compounded).

Headline: Market FDV $4.02B is 1.2x the model's expected-path FDV $3.29B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 74x (evidence 2,425x); discount rate 17% (evidence 10%).

Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the joint requirement is smaller than any single one; section 4 shows which inputs carry the variance.

## 4. What you have to believe (one-at-a-time sensitivity)

Basis: deterministic_sotp expected path; one input at its low / high, all others at the snapshot base. Base expected-path FDV $3.29B against a $4.02B market FDV. Variance share: swing^2 / sum(swing^2): first-order share for independent inputs, an approximation. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).

| # | Input | Source | Range | Base | FDV at low | FDV at high | Swing | Variance share |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Terminal FDV / holder-revenue multiple | derived | 8.00x - 150x | 60x | $558.1M | $8.03B | $7.47B | 37.1% |
| 2 | Expected annual public-volume growth | measured | 55.8% - 202.8% | 117.2% | $1.41B | $7.80B | $6.39B | 27.1% |
| 3 | Public take compression speed (per month) | assumption | 0.0%/month - 15.0%/month | 3.0%/month | $6.14B | $906.3M | $5.23B | 18.2% |
| 4 | Holder capture (revenue / gross fees) | measured | 14.7% - 32.7% | 21.7% | $2.29B | $4.87B | $2.57B | 4.4% |
| 5 | Confidential share at month 36 | assumption | 5.0% - 60.0% | 40.0% | $2.12B | $4.67B | $2.55B | 4.3% |
| 6 | Annual discount rate | assumption | 10.0% - 40.0% | 25.0% | $4.81B | $2.36B | $2.45B | 4.0% |
| 7 | Starting 30-day Intents volume (public + confidential) | measured | 0.80x - 1.25x | 1.00x | $2.67B | $4.07B | $1.40B | 1.3% |
| 8 | Confidential multiple haircut | assumption | 30.0% - 100.0% | 70.0% | $2.57B | $3.84B | $1.27B | 1.1% |
| 9 | NEAR price drift (gas-burn and state-lock USD value) | assumption | -50.0% - 100.0% | 0.0% | $3.14B | $4.28B | $1.14B | 0.9% |
| 10 | Confidential gross take (public take re-reconciled to live fees) | assumption | 10.00 bps - 30.00 bps | 20.00 bps | $2.78B | $3.81B | $1.02B | 0.7% |
| 11 | Confidential compression divisor | assumption | 1.00x - 10x | 3.00x | $2.71B | $3.60B | $886.3M | 0.5% |
| 12 | Public take hard floor | assumption | 0.00 bps - 5.00 bps | 0.50 bps | $3.29B | $3.94B | $645.3M | 0.3% |
| 13 | Blended gross take (public take re-reconciled) | measured | 12.44 bps - 17.90 bps | 18.41 bps | $2.68B | $3.24B | $565.4M | 0.2% |
| 14 | NEAR spot price (USD value of gas burn and state lock) | measured | $2.27 - $4.12 | $3.06 | $3.25B | $3.36B | $115.9M | 0.0% |
| 15 | L1 gas burn (NEAR/day) | measured | 540 NEAR/day - 901 NEAR/day | 720 NEAR/day | $3.25B | $3.34B | $94.2M | 0.0% |
| 16 | Cross-VM headroom (sets the public take floor) | measured | 0.79 bps - 1.31 bps | 1.05 bps | $3.25B | $3.34B | $85.6M | 0.0% |
| 17 | State-lock growth (NEAR/day) | measured | 307 NEAR/day - 512 NEAR/day | 409 NEAR/day | $3.29B | $3.30B | $1.8M | 0.0% |

Top three inputs carry 82% of the variance proxy. 8 of 17 single-input ranges reach the market FDV at either end.

Headline: terminal_multiple, public_volume_growth_yoy, fee_compression_lambda_monthly carry 82% of the swing-squared variance proxy; terminal_multiple alone moves FDV from $558M to $8.03B across its range, and 8 of 17 single-input ranges reach the $4.02B market FDV.

Excluded (move issuance and implied price, not FDV): svrn_target_inflation (issuance path only: moves supply at horizon and implied price, not FDV); svrn_glidepath_months (issuance path only: moves supply at horizon and implied price, not FDV).

## 5. Relative value: peer cash-flow multiples and the security budget

Basis: live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR.

### 5.1 NEAR cash-flow coverage against the peer set
| Metric | NEAR | Peer median | Peer P25 - P75 | NEAR rank | Position |
| :--- | ---: | ---: | ---: | ---: | :--- |
| FDV / annualised fees (30-day run-rate) | 42x | 279x | 162x - 560x | 1 of 4 | below every peer |
| FDV / annualised revenue (30-day run-rate) | 185x | 2,425x | 1,243x - 3,074x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day fees | 73x | 197x | 131x - 704x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day revenue | 376x | 1,842x | 964x - 3,120x | 2 of 4 | inside the peer range |

| Protocol | FDV | Fees (ann.) | Revenue (ann.) | FDV/fees | FDV/revenue | FDV/fees 1y | FDV/revenue 1y | Revenue/fees |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SOL (solana) | $45.10B | $161.4M | $12.1M | 279x | 3,722x | 197x | 1,842x | 8% |
| ETH (ethereum) | $206.14B | $245.2M | $85.0M | 841x | 2,425x | 1,210x | 4,398x | 35% |
| HYPE (hyperliquid) | $58.32B | $1.28B | $974.6M | 45x | 60x | 65x | 86x | 76% |
| NEAR (near_combined) | $4.01B | $94.9M | $21.6M | 42x | 185x | 73x | 376x | 23% |
| NEAR (near) | $4.01B | $1.1M | $915,968 | 3,526x | 4,373x | 3,644x | 5,135x | 81% |
| NEAR (near-intents) | $4.01B | $93.8M | $20.7M | 43x | 194x | 74x | 406x | 22% |

The model's terminal multiple is 60x; 1 of 3 peers trade at or below it on FDV/revenue.

### 5.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)
| Cash flow | NEAR (ann.) | at peer P25 | at peer median | at peer P75 | Peers | Basis |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| fees | $94.9M | $15.42B | $26.52B | $53.15B | 3 | comps.near_combined.annualized_fees_usd x peer FDV / annualised fees (30-day run-rate) |
| revenue | $21.6M | $26.85B | $52.40B | $66.41B | 3 | comps.near_combined.annualized_revenue_usd x peer FDV / annualised revenue (30-day run-rate) |

relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution; market FDV $4.02B.

### 5.3 Staking and security budget
- Security budget: 32,772,196 NEAR/yr of issuance (2.50%) x $3.06 = $100.3M/yr (2.50% of FDV).
- Against it: $94.9M/yr of fees (95% of the budget) and $21.6M/yr of holder revenue (22%); net dilution $78.7M/yr.
- Staked 45.4% of supply; nominal staking APR 5.51%. Basis: security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate.

### 5.4 Findings
- NEAR trades at 42x annualised fees versus a peer median of 279x (rank 1 of 4, lowest first; below every peer); on revenue it is 185x versus 2,425x (inside the peer range).
- 1 of 3 peers trade at or below the model's 60x terminal FDV/revenue multiple; NEAR itself trades at 185x.
- At the peer FDV/fees distribution, NEAR's $95M of annualised fees maps to $15.42B-$53.15B (median $26.52B, n = 3) against a $4.02B market FDV; a relative-value cross-check, not a fair value.
- NEAR issues $100M a year to validators and delegators (2.5% of FDV) against $95M of annualised fees and $22M of holder revenue (gas burn + Intents buyback): revenue covers 22% of the security budget.
- At 2.5% inflation stakers earn 5.51% nominal and 3.52% real including buybacks; non-stakers lose 1.98% a year to dilution net of buybacks.

Caveat: Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples compare different cash-flow definitions; with n = 3 peers the median is a reference point, not a distribution.

## 6. Model valuation detail

**Base case.** 10,000-path SOTP (seed 20261114): P10 / P50 / P90 FDV = $666.5M / **$2.06B** / $6.65B; implied price $0.49 / **$1.51** / $4.86 per NEAR against spot $3.06. The P50 sits 48.6% below the current FDV of $4.02B. The deterministic SOTP at the labeled inputs (the expected-volume path) is $3.29B: engines $1.78B clearinghouse + $1.33B confidential + $192.0M monetary; the Monte Carlo mean is $3.22B. Ex-monetary P50: $1.97B.

**Volume growth is measured, not assumed.** Trend growth of NEAR Intents daily volume over 2025-11-26 to 2026-11-25 (365 days, DefiLlama): +117.2%/yr, 90% CI +56% to +203% (OLS of log volume on time, Newey-West errors). The model uses it as public_volume_growth_yoy, with the CI as its range; it is the median trend, so reading it as expected growth is conservative. Cross-checks, not used: yoy trailing 30d +16%, mean monthly log return 12m +18%.



**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled +117% YoY volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of 0.224 the MEDIAN simulated path ends month 36 at 40.5% of the expected path ($513.0M/day vs $1.27B/day), which is what pulls the P50 FDV below the mean. The dispersion is measured from 11 monthly volume log-returns (sigma excluding the three oldest, incentive-era windows: 0.220); a thin sample, reported as such.

**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation; section 3 solves which single input would: Market FDV $4.02B is 1.2x the model's expected-path FDV $3.29B; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 74x (evidence 2,425x); discount rate 17% (evidence 10%). The P90 ($6.65B) comes from volume paths, not from take-rate expansion (the public take only compresses in this model).

**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** 6 bps net take needs >= $1.00B/day; 10 bps net take needs >= $500.0M/day; 14 bps net take needs >= $250.0M/day; 18 bps net take needs >= $250.0M/day. Live run-rate: $142.6M/day at 3.99 bps net (18.41 bps gross x capture 21.7%).

**Net-float crossover.** Today sinks cover 22.0% of measured issuance (19,721 NEAR/day vs 89,725 NEAR/day). status quo (cap flat): deterministic flow crossover none within horizon at run-rate volume, month 26 with the +117% YoY growth assumption; Monte Carlo P(crossover within 36m) = 85.1%, P(deflationary at horizon) = 76.5%; breakeven volume V* = $679.3M/day (4.8x today). SVRN glidepath: deterministic flow crossover none within horizon at run-rate volume, month 21 with the +117% YoY growth assumption; Monte Carlo P(crossover within 36m) = 90.4%, P(deflationary at horizon) = 83.2%; breakeven volume V* = $431.7M/day (3.0x today). The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price outruns issuance); the deterministic path (the expected-volume path) is the one to quote.

**Falsification.** Four stress scenarios (section 11) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo percentile) at $290.5M (-91% vs the deterministic base $3.29B); 1 of 3 measured early-warning triggers are breached in this snapshot (breached: governance_stalemate (max_inflation_rate now 2.50% vs > 1.60%); not measured this run: solver_cartelization). The on-chain inflation cap reads 2.50%; the SVRN cut is a proposal, not protocol state.

## 7. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)

Executable quotes fetched 2026-11-26T06:05:11.092Z UTC (30 ok of 36; 1Click token universe 234 assets on 39 chains). Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input (headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price (`price_basis`: oneclick_token_list_oracle); raw-unit friction is exact for USDC -> USDC. Positive headroom means 1Click paid out more after all fees.

| Corridor | Clip | Venue | Status | Out | Friction | ETA | Route |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | 1click | ok | 499.897638 | 2.05 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $500 | relay | ok | 499.829707 | 3.41 bps (raw) | 1 s | relay |
| ETH USDC -> SOL USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $500 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $50,000 | 1click | ok | 49,990.217967 | 1.96 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $50,000 | relay | ok | 49,984.979707 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $50,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $250,000 | 1click | ok | 249,949.492562 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $250,000 | relay | ok | 249,924.979707 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $250,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | 1click | ok | 0.008222 | 27.83 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $500 | relay | ok | 0.008230 | 17.87 bps (usd) | 157 s | relay |
| ETH USDC -> native BTC | $500 | lifi | ok | 0.008209 | 43.93 bps (usd) | 1,357 s | relaydepository |
| ETH USDC -> native BTC | $500 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | 1click | ok | 0.823847 | 7.61 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $50,000 | relay | ok | 0.823509 | 11.72 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $50,000 | lifi | ok | 0.822568 | 23.12 bps (usd) | 1,390 s | near (= NEAR Intents resold via LI.FI) |
| ETH USDC -> native BTC | $50,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | 1click | ok | 4.118659 | 9.01 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $250,000 | relay | ok | 4.115923 | 15.65 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $250,000 | lifi | ok | 4.112140 | 24.82 bps (usd) | 1,390 s | near (= NEAR Intents resold via LI.FI) |
| ETH USDC -> native BTC | $250,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | 1click | ok | 499.931875 | 1.36 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $500 | relay | ok | 499.927915 | 1.44 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $500 | across | ok | 499.943919 | 1.12 bps (raw) | 1 s | across |
| Base USDC -> Arbitrum USDC | $50,000 | 1click | ok | 49,989.895220 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $50,000 | relay | ok | 49,994.977970 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $50,000 | across | ok | 49,994.993919 | 1.00 bps (raw) | 33 s | across |
| Base USDC -> Arbitrum USDC | $250,000 | 1click | ok | 249,949.497300 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $250,000 | relay | ok | 249,974.977962 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $250,000 | across | ok | 249,974.993919 | 1.00 bps (raw) | 900 s | across |


| Corridor | Clip | Headroom | Basis | 1Click rank | Reading |
| :--- | ---: | ---: | :--- | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | +1.36 bps | dest_units | 1/3 | 1Click delivers 1.36 bps more than relay |
| ETH USDC -> SOL USDC | $50,000 | +1.05 bps | dest_units | 1/3 | 1Click delivers 1.05 bps more than relay |
| ETH USDC -> SOL USDC | $250,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> native BTC | $500 | -9.98 bps | dest_units | 2/3 | 1Click trails relay by 9.98 bps |
| ETH USDC -> native BTC | $50,000 | +4.12 bps | dest_units | 1/3 | 1Click delivers 4.12 bps more than relay |
| ETH USDC -> native BTC | $250,000 | +6.65 bps | dest_units | 1/3 | 1Click delivers 6.65 bps more than relay |
| Base USDC -> Arbitrum USDC | $500 | -0.24 bps | dest_units | 2/4 | 1Click trails across by 0.24 bps |
| Base USDC -> Arbitrum USDC | $50,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |
| Base USDC -> Arbitrum USDC | $250,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |


- cross_vm: median headroom +1.05 bps over 3 comparable cells
- native_btc: median headroom +4.12 bps over 3 comparable cells
- evm_l2: median headroom -1.02 bps over 3 comparable cells
- competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = 3; per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding): 3.00 bps. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not.

- Where 1Click loses (destination units): eth_usdc_btc at $500 trails relay by 9.98 bps; base_usdc_arb_usdc at $500 trails across by 0.24 bps; base_usdc_arb_usdc at $50,000 trails across by 1.02 bps; base_usdc_arb_usdc at $250,000 trails across by 1.02 bps.
- Oracle caveat: on eth_usdc_sol_usdc at $500, eth_usdc_sol_usdc at $50,000, eth_usdc_sol_usdc at $250,000, eth_usdc_btc at $500, eth_usdc_btc at $50,000, eth_usdc_btc at $250,000, base_usdc_arb_usdc at $500, base_usdc_arb_usdc at $50,000, base_usdc_arb_usdc at $250,000 the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg comparison there would have been decided by oracles, which is why the ranking uses units.
- Structurally unsupported routes: across on eth_usdc_btc (declared), across on eth_usdc_sol_usdc (ROUTE_NOT_ENABLED).
- LI.FI's quote on eth_usdc_btc $250,000, eth_usdc_btc $50,000 routes through NEAR Intents itself (tool `near`), so it is 1Click execution plus LI.FI's fee, not an independent price.
- Collector summary: cross_vm (ETH USDC -> SOL USDC): $500: 1Click delivers 1.36 bps more than relay (rank 1/3, destination units); $50,000: 1Click delivers 1.05 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); unsupported: across (ROUTE_NOT_ENABLED). native_btc (ETH USDC -> native BTC): $500: 1Click trails 9.98 bps behind relay (rank 2/3, destination units); $50,000: 1Click delivers 4.12 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 6.65 bps more than relay (rank 1/3, destination units); unsupported: across (Across is EVM-only; no Bitcoin route). evm_l2 (Base USDC -> Arbitrum USDC): $500: 1Click trails 0.24 bps behind across (rank 2/4, destination units); $50,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units); $250,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units).

## 8. Concentration and agents on intents.near (NearBlocks receipts)

- Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = **1,956** (bootstrap 90% CI 1,276-2,600) (N_eff = 5.11); over all predecessors 3,706; ex-AI-agent 1,524 (N_eff 6.56). These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.
- (b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = **n/a** (no bootstrap CI) (N_eff n/a) across 0 fill participations in 0 fills (0 atomic token_diff fills, 0 solver-to-settlement-hub legs), 0 distinct solvers; 0 execute_intents receipts decoded, 0 unresolved; the solver sample spans n/a. This is the population the solver_cartelization trigger reads; trigger status: not measured.
- AI-agent share of external receipts 36.7% is a NAME-PATTERN classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. Bridge / token-contract share 60.0%; 12 unique external callers in 30 external receipts.
- Sample: 200 unique receipts over 8 NearBlocks pages, blocks 226,265,440-226,265,536, a 54 s window; lifetime receipts on intents.near n/a. A window this short is a point sample, not a market-share estimate; both HHIs move by hundreds of points between runs.
- Method mix: TRANSFER 100, execute_intents 46, ft_on_transfer 13, ft_resolve_withdraw 13, ft_transfer 7, storage_deposit 5, do_storage_deposit 5, near_withdraw 5, ft_transfer_call 5, ft_withdraw 1.

### 8.1 Deposit / caller concentration (external predecessors)
| Caller | Class | Receipts | Share | Example tx |
| :--- | :--- | ---: | ---: | :--- |
| escrow.ai.near | AI agent | 11 | 36.7% | [2cDStoFGmqcR...](https://nearblocks.io/txns/2cDStoFGmqcR7vkQDdY62MSsRgXJRrCg9MRout76z9JS) |
| wrap.near | bridge / token contract | 6 | 20.0% | [3vRjnj5GdtmH...](https://nearblocks.io/txns/3vRjnj5GdtmHV1vUiZ8SF6XB8wWUsoXQx9d8PH3q27s4) |
| eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near | bridge / token contract | 2 | 6.7% | [AcDddMZQsvZ3...](https://nearblocks.io/txns/AcDddMZQsvZ3K1qH1Q8M88wk7ZuGCpfFq3gnVfWzE4Np) |
| ltc.omft.near | bridge / token contract | 2 | 6.7% | [7PcF6Xe6UTRf...](https://nearblocks.io/txns/7PcF6Xe6UTRfjpxYbA12WRkbBeh3YPzeo6qPjyjgcfwe) |
| sol.omft.near | bridge / token contract | 2 | 6.7% | [9itP9pJMEstJ...](https://nearblocks.io/txns/9itP9pJMEstJndhVKC1ZGzzcDN4zywv8JdinDykvVtVY) |
| bnb-0x55d398326f99059ff775485246999027b3197955.omdep.near | bridge / token contract | 1 | 3.3% | [8MFnSWEg62J7...](https://nearblocks.io/txns/8MFnSWEg62J7FgHvuf9W43hdEsaDd8gW9tCvztC9v5RE) |
| eth-0xdac17f958d2ee523a2206206994597c13d831ec7.omft.near | bridge / token contract | 1 | 3.3% | [Aib7tQHGVGcC...](https://nearblocks.io/txns/Aib7tQHGVGcCcdwRUYAyyNJL8rrm8dnYyF8CE5VPEDDb) |
| eth.omft.near | bridge / token contract | 1 | 3.3% | [8RBYdkkWoMBu...](https://nearblocks.io/txns/8RBYdkkWoMBuaCd9YMvSaWDo2R3n14tQAFxmS1SRC4hh) |
| plasma-0xb8ce59fc3717ada4c02eadf9682a9e934f625ebb.omft.near | bridge / token contract | 1 | 3.3% | [12UTxTncgKVG...](https://nearblocks.io/txns/12UTxTncgKVGkKLzbGMQPTV2Sv7j5xrgVEk9pVJqx56g) |
| slowtag1642.near | named account | 1 | 3.3% | [J4AgQpTDLJWe...](https://nearblocks.io/txns/J4AgQpTDLJWeWceXuUe1MSrWTAPvEoACGEGU1ip4SMM6) |
| sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near | bridge / token contract | 1 | 3.3% | [DqjEm7dMMyZT...](https://nearblocks.io/txns/DqjEm7dMMyZT1KBHLEm6ofh9gzbthbTSEHmkosNcxFDK) |
| tron.omft.near | bridge / token contract | 1 | 3.3% | [3dBBhandBNjY...](https://nearblocks.io/txns/3dBBhandBNjY6MR8p4ZaKjqntuTDhBVJ5vpEUR5ig8Xk) |

### 8.2 Solver concentration (execute_intents signers)
No solver fill could be attributed in this sample; hhi_solver is null and the cartelization trigger is not measured.

## 9. Supply physics

### 9.1 Issuance: measured vs nominal
- Measured: 25,710.84 NEAR minted at epoch start 226,252,337 (previous jump 25,553.51 NEAR at 226,209,137); epoch wall time 6.877 h = 1,274.6 epochs/yr; implied annual issuance **32,772,196 NEAR** = 2.4965% of supply.
- Nominal: max_inflation_rate 2.50% x total supply 1,312,729,117 NEAR = 32,818,228 NEAR/yr; measured minus nominal -46,032 NEAR/yr (-0.14%). Daily: measured 89,725 NEAR vs nominal 89,851 NEAR; treasury share 0.0% (validators receive the rest).
- Within-epoch supply drift (net gas burn) -206.44 NEAR/epoch; measured block time 0.573 s. Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.

### 9.2 Daily sinks (NEAR/day, live)
| Sink | NEAR/day | Source | Basis |
| :--- | ---: | :--- | :--- |
| Buyback (holders revenue / price) | 18,591.5 NEAR | measured | $142.6M/day x 18.41 bps gross x alpha 21.7% / $3.06 |
| L1 gas burn | 720.4 NEAR | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| NEP state-lock growth | 409.3 NEAR | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| Total sinks | 19,721.2 NEAR |  | coverage 22.0% of measured issuance; net float 70,004 NEAR/day |


### 9.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)
| Regime (terminal rate) | V* at live take | vs today | V* at competitive ceiling |
| :--- | ---: | ---: | ---: |
| status quo (cap flat) | $679.3M | 4.8x | $4.16B |
| SVRN glidepath | $431.7M | 3.0x | $2.65B |

Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.

### 9.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)
| Regime | Volume path | Issuance/day m1 | Issuance/day m36 | Gross issuance 36m | Sinks 36m | Net float 36m | Flow crossover | Cumulative crossover |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| status quo (cap flat) | run-rate volume | 89,725 NEAR | 96,495 NEAR | 101,981,883 NEAR | 21,609,523 NEAR | 80,372,360 NEAR | none within horizon | none within horizon |
| status quo (cap flat) | +117% YoY volume | 89,725 NEAR | 96,495 NEAR | 101,981,883 NEAR | 79,608,254 NEAR | 22,373,628 NEAR | month 26 | none within horizon |
| SVRN glidepath | run-rate volume | 89,725 NEAR | 60,727 NEAR | 77,343,628 NEAR | 21,609,523 NEAR | 55,734,105 NEAR | none within horizon | none within horizon |
| SVRN glidepath | +117% YoY volume | 89,725 NEAR | 60,727 NEAR | 77,343,628 NEAR | 79,608,254 NEAR | -2,264,626 NEAR | month 21 | month 36 |


### 9.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)
| Account | Contract | storage_usage bytes | Locked | Growth B/day | Growth NEAR/day | Window |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| intents.near | yes | 14,228,050,111 | 142,280.5 NEAR | 39,604,891 | 396.05 NEAR | 30.4 d |
| aurora | yes | 14,398,346,032 | 143,983.5 NEAR | 1,321,724 | 13.22 NEAR | 30.4 d |
| wrap.near | yes | 169,615,432 | 1,696.2 NEAR | n/a | n/a | n/a |
| v1.signer | yes | 1,132,595 | 11.3 NEAR | n/a | n/a | n/a |
| escrow.ai.near | no | 428 | 0.0 NEAR | n/a | n/a | n/a |
| treasury.near | yes | 357,895 | 3.6 NEAR | n/a | n/a | n/a |
| meme-cooking.near | yes | 5,960,939 | 59.6 NEAR | n/a | n/a | n/a |
| v2.ref-finance.near | yes | 111,480,968 | 1,114.8 NEAR | n/a | n/a | n/a |

- Total state-locked across 8 tracked contracts: **289,149 NEAR** at 0.01 NEAR/KB (storage_amount_per_byte 10,000,000,000,000,000,000 yocto). Measured lock growth 409.3 NEAR/day over intents.near, aurora (archival available).

### 9.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)
| Regime | Inflation | Nominal APR | Real APR | Buyback accrual | Real APR + accrual | Non-staker real |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| status quo (cap flat) | 2.50% | 5.51% | 3.01% | 0.517% | 3.52% | -1.98% |
| SVRN glidepath | 1.60% | 3.52% | 1.92% | 0.517% | 2.44% | -1.08% |

Live: 350 validators, 596,137,103 NEAR staked = 45.41% of supply.

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
| clearinghouse | $195.9M | $406.2M | $875.7M | $1.88B | $3.74B | no |
| confidential | $142.8M | $287.2M | $636.3M | $1.46B | $3.05B | yes |
| monetary | $3.1M | $8.4M | $28.5M | $101.4M | $319.9M | yes |

| Total | P10 | P25 | P50 | P75 | P90 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| FDV (all engines) | $666.5M | $1.11B | $2.06B | $3.84B | $6.65B |
| FDV ex-monetary | $634.9M | $1.07B | $1.97B | $3.66B | $6.27B |
| Implied price / NEAR | $0.49 | $0.81 | $1.51 | $2.81 | $4.86 |

Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse $1.57B (76%) + confidential $390.7M (19%) + monetary $104.0M (5%) = $2.06B.

- PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor.
- Same construction on confidential volume at the assumed confidential take; terminal multiple x confidential_multiple_haircut because nearstats flags confidential TVL as unverified. Starting confidential share 13.3% is an on-chain estimate from Confidential Intents Treasury boundary flows (intents_forensics.volume.confidential_share_estimate), not nearstats' rejected split.
- PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.

### 10.2 Calibration (what the engines were fed)
| Parameter | Value | Source / basis |
| :--- | :--- | :--- |
| Public take t=0 (gross) | 18.17 bps | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d |
| Blended gross take / net take | 18.41 bps / 3.99 bps | DefiLlama near-intents fees / volume; net = gross x alpha |
| Capture ratio alpha | 21.67% | measured:defillama near-intents dailyHoldersRevenue / fees |
| Confidential take t=0 | 20 bps | assumption: registry confidential_take_bps (1Click confidential quotes need partner authentication) |
| Public take floor | 1.05 bps | derived; cross-VM headroom +1.05 bps, competitor ceiling 3.00 bps |
| Compression lambda (public / confidential) | 0.030 / 0.010 per month | geometric reversion to the floor |
| Volume growth (public / confidential, monthly) | 6.68% / 11.12% | confidential share 13.3% -> 40% target (start share ESTIMATED ON-CHAIN from Confidential Intents Treasury boundary flows) |
| Sigma: price (annual) / volume (monthly) | 1.030 / 0.224 | measured: monthly log-return sigma of 30-day volume aggregates; confidential sigma x 1.00 |
| Terminal multiple (FDV / annual holder revenue) | 60.0x (raw 2,425.5x) | source derived: peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; clipped to registry guardrails |
| Discount rate | 25% | assumption |
| Supply at horizon (glidepath) | 1,368,463,222 NEAR | fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory) |
| Current FDV | $4.02B | spot price x on-chain total_supply at the snapshot block; CoinGecko FDV via nearstats $4.04B (0.52% gap, struck at a different instant; cross-check only) |
| GBM convention | mean-matching (Ito) | mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM uses the same convention (zero drift => E[P_t] = P_0) |
| Terminal public volume, month H | mean $1.27B/day; median $513.0M/day | start $123.6M/day; MC sample mean $1.22B, median $502.3M; the labeled YoY growth is the growth of the MEAN path |


### 10.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)
| Protocol | Fees 30d | Revenue 30d | FDV | FDV/fees | FDV/revenue | Revenue methodology (live text) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| SOL (solana) | $13.3M | $995,895 | $45.10B | 279.4x | 3,721.8x | Burned fees: 50% of base fees, and 50% of priority fees until SIMD-0096 (slot 320,112,000, 2025-02-12 06:59 UT |
| ETH (ethereum) | $20.2M | $7.0M | $206.14B | 840.6x | 2,425.5x | Amount of ETH burned — base fees plus blob fees (both are permanently burned, accruing to no proposer) |
| HYPE (hyperliquid) | $105.5M | $80.1M | $58.32B | 45.4x | 59.8x | Parent aggregates child protocols. Hyperliquid Perps: 99% of fees go to Assistance Fund for buying HYPE tokens |
| NEAR (near) | $93,378 | $75,285 | $4.01B | 3,526.1x | 4,373.5x | Gas fees permanently burned, reducing NEAR supply. Before 4 November 2026 (protocol upgrade v87) the burn is e |
| NEAR (near-intents) | $7.7M | $1.7M | $4.01B | 42.7x | 193.6x | NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.ne |
| NEAR (near_combined) | $7.8M | $1.8M | $4.01B | 42.2x | 185.4x | near: Gas fees permanently burned, reducing NEAR supply. Before 4 November 2026 (protocol upgrade v87) the bur |

- Median ex-NEAR FDV / annualized revenue 2,425.5x (n = 3); FDV / annualized fees 279.4x (n = 3). annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)
- `revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live methodology text is carried in the table so the multiple is read with its definition.

### 10.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take (SVRN glidepath; * = net-deflationary)
| Net take \ Volume/day | $100.0M | $250.0M | $500.0M | $1.00B | $1.50B |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2 bps | $258.7M | $605.6M | $1.18B | $2.34B* | $3.50B* |
| 6 bps | $721.3M | $1.76B | $3.50B* | $6.97B* | $10.43B* |
| 10 bps | $1.18B | $2.92B* | $5.81B* | $11.59B* | $17.37B* |
| 14 bps | $1.65B | $4.07B* | $8.12B* | $16.22B* | $24.31B* |
| 18 bps | $2.11B* | $5.23B* | $10.43B* | $20.84B* | $31.25B* |

Current FDV $4.02B; confidential share used in the split 13.3%. Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).

### 10.5 Out-of-sample backtest of the volume engine
At each of 20 monthly origins from 2025-04-04 to 2026-10-26 the volume GBM was re-calibrated on data up to the origin only (trailing 30-day volume, sigma from the trailing 365 days, drift = public_volume_growth_yoy 117%) and its P10-P90 band for 30-day volume was compared with what happened (defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json), 2024-12-10 to 2026-11-25). The test of 80% coverage fails at 3m, 6m (exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10). At 1 month the median realized volume is 1.31x the forecast median: the model under-predicts. Split at the middle origin (2026-01-29), coverage before: 1m 50% (n = 10), 3m 30% (n = 10), 6m 30% (n = 10); from it: 1m 100% (n = 10), 3m 100% (n = 7), 6m 100% (n = 4). 19 of the 19 misses come from origins before the split; 18 of 19 are realized volume above P90. With the drift replaced by the trailing mean log return (no registry input) coverage is 1m 85%, 3m 71%, 6m 50%. Not backtested: fee take rate (public and confidential) and its compression toward the floor; holder capture ratio alpha; confidential share of volume and its drift to the target share; terminal FDV/revenue multiple and discount rate; NEAR price and supply paths. 3- and 6-month forecasts from monthly origins overlap, so their errors are correlated and the binomial interval overstates the precision.

| Horizon | n | P10-P90 coverage [90% Wilson] | Binomial p vs 80% | Below P10 / above P90 | Median realized / P50 | PIT histogram (5 bins) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 1 month | 20 | 75% [57%-87%] | 0.58 | 1 / 4 | 1.31x | 1 2 5 5 7 |
| 3 months | 17 | 59% [39%-76%] | 0.06 | 0 / 7 | 2.22x | 0 1 2 5 9 |
| 6 months | 14 | 50% [30%-70%] | 0.01 | 0 / 7 | 4.06x | 0 1 2 2 9 |


## 11. Bear case and early-warning triggers

Value basis: deterministic at median inputs; not a Monte Carlo percentile. Base deterministic FDV (median inputs) $3.29B, implied price $2.41; the Monte Carlo P50 of section 10 is a different statistic and is not what the drawdowns below are measured against. drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed

| Scenario | Deterministic FDV (median inputs) | FDV drawdown | Implied price | Price drawdown | Flow crossover |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fee_race_to_zero | $519.6M | -84.2% | $0.38 | -84.2% | none within horizon |
| governance_stalemate | $3.29B | +0.0% | $2.37 | -1.8% | month 29 |
| post_incentive_decay | $1.30B | -60.5% | $0.95 | -60.5% | month 36 |
| solver_cartelization | $1.79B | -45.6% | $1.31 | -45.6% | month 30 |
| combined worst | $290.5M | -91.2% | $0.21 | -91.3% | none within horizon |


### 11.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)
| Scenario | Metric | Now | Trigger | Status | Monitor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| fee_race_to_zero | net_take_bps_30d | 3.99 bps | < 3.00 bps | not breached | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue (sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days). |
| governance_stalemate | max_inflation_rate | 2.50% | > 1.60% | **BREACHED** | https://free.rpc.fastnear.com (EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)). Note: breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted |
| post_incentive_decay | volume_30d_vs_record_30d | -13.0% | <= -40.0% | not breached | https://nearstats.org/api/near/summary (intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1). |
| solver_cartelization | hhi_solver | n/a | > 3,500 | not measured | https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50 (HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)); secondary headroom_cross_vm_bps +1.05 bps < 0 bps (not breached). Note: no execute_intents fill with an attributable solver was parsed this run; solver HHI unmeasured or too thin and cross-VM headroom +1.05 bps, not negative; trigger not measured (trigger_breached null, not counted as breached or clear); deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = 1,956 |


### 11.2 Scenario narratives
**Aggregator bypass: public take races to 1 pip.** Third-party frontends route around near.com and the public gross take collapses from 18.2 bps to 0.01 bps (the bare intents.near contract fee); confidential execution reprices from 20 bps to 5 bps. Capture ratio alpha is held at 22%, so the hit is price, not allocation. Deterministic (median-input) FDV -84.2% to $519.6M; implied price $0.38. Evidence against it: live cross-VM headroom is +1.0 bps, so a bypassing frontend must first give up that execution edge. Trigger: DefiLlama 30d net take (gross x alpha) below 3.0 bps (now 4.0 bps).

**Governance stalemate: 2.5% issuance forever.** Validators never enact the SVRN cut: max_inflation_rate stays at 2.50% for the full horizon instead of gliding to 1.60%. Protocol cash flows do not change, so FDV moves +0.0%; the damage is dilution: 24,638,255 more NEAR outstanding at the horizon and a per-token value of $2.37 (-1.8% vs base). Net-float crossover: month 29 (base: month 23). This scenario is live today: the on-chain cap reads 2.50% and no cut has been enacted.

**Post-incentive volume decay (NEAR@3.33 unwind).** Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume $123.6M -> $49.4M (-60%), confidential $19.0M -> $5.7M (-70%) and confidential TVL x0.3 (nearstats flags that TVL unverified). Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV -60.5% to $1.30B; implied price $0.95. Current 30d volume $4.48B is 87% of the 30d record $5.15B; the trigger fires at -40%.

**Solver cartelization: HHI_solver > 3,500, 1Click loses the spread.** Two market makers take most fills (HHI_solver > 3,500) and spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM (headroom -2 bps). Keeping flow costs the same 2 bps of take (18.2 bps -> 16.2 bps) while compression runs at 0.15/month. Deterministic (median-input) FDV -45.6% to $1.79B; implied price $1.31. Live: no solver fill could be attributed from the sampled execute_intents payloads this run; deposit-source HHI over external predecessors 1,956 (not a solver measure); cross-VM headroom +1.0 bps; trigger at HHI_solver > 3,500 or headroom < 0.

### 11.3 Falsification summary
fee_race_to_zero: public gross take at 0.01 bps and confidential at 5 bps puts the deterministic FDV at $519.6M (-84.2%); watch DefiLlama near-intents 30d net take weekly, trigger < 3.0 bps, now 4.0 bps (not breached). governance_stalemate: no SVRN cut (cap 2.50% for 36 months) leaves the deterministic FDV at $3.29B (+0.0%) but dilutes per-token value to $2.37 (-1.8%) with crossover month 29; watch max_inflation_rate in EXPERIMENTAL_protocol_config, trigger > 1.60%, now 2.50% (BREACHED). post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at $1.30B (-60.5%); watch nearstats 30d volume against its 30d record weekly, trigger <= -40%, now -13.0% (not breached). solver_cartelization: HHI_solver > 3,500 with cross-VM headroom at -2 bps puts the deterministic FDV at $1.79B (-45.6%); watch the execute_intents solver HHI (now n/a) and the live quote-race headroom (now +1.0 bps) weekly (not measured). All four at once: deterministic FDV $290.5M (-91.2% vs base $3.29B); 1 of 3 measured triggers currently breached (1 not graded this run, inconclusive or not measured: solver_cartelization), and the thesis is falsified if any trigger holds for 30 consecutive days.

## 12. Further evidence: take-rate history, size limits, fee share, wider peers

### 12.1 Fee-pool share against competing cross-chain routers

**NEAR Intents takes 27.3% of the six-protocol cross-chain fee pool over the 30 days to 2026-11-21, rank 2 of 6 behind Relay at 40.8%; its rolling 30-day share moved from 35.0% to 27.3% over 182 days (low 2.5% on 2026-09-13, high 45.3% on 2026-07-04) and the linear trend (-5.37 pp per 30 days, 90% interval -8.61 to -2.14) is falling, with the interval excluding zero.**

Cuts against the bull case: NEAR Intents is losing share of the fees these routers collect, so fee growth has to come from the pool growing, not from share capture. It is overturned by a positive share trend whose 90% interval excludes zero. Relay collects 1.5x NEAR Intents' fees under its own adapter's definition. NEAR Intents' own 30-day fees went from $2.90M to $7.42M over the window; the pool went from $8.30M to $27.23M. With Relay excluded the share is 46.0% against 48.8% at the start of the window (-1.35 pp per 30 days, 90% interval -2.31 to -0.39).

| Rank | Protocol | 30d fees | Share | 90d fees | Days of data | Fee definition (adapter text) |
| ---: | :--- | ---: | ---: | ---: | ---: | :--- |
| 1 | Relay | $11.10M | 40.8% | $253.16M | 216 | Platform fees, integrator app fees and swap costs paid by users on Relay bridges and swaps, excluding execution costs (network gas). |
| 2 | **NEAR Intents** | $7.42M | 27.3% | $20.76M | 564 | Gross fees charged on NEAR Intents swaps - the protocol fee plus the affiliate (distribution) fee each frontend collects, summed across all integra... |
| 3 | THORChain DEX | $4.63M | 17.0% | $9.55M | 2054 | Slip-based liquidity (swap) fees paid by users on each chain's THORChain pools, gross outbound fees and slashing fees paid into the Reserve, and af... |
| 4 | Chainflip | $3.43M | 12.6% | $6.90M | 1057 | Chainflip AMM: Includes Swap, Broker, Ingress, Egress and Network Fees for Buy/Burn Mechanism |
| 5 | deBridge | $515.8K | 1.9% | $1.57M | 1334 | All fees paid by users for swap and bridge tokens via deBridge. |
| 6 | Across | $137.3K | 0.5% | $329.3K | 1301 | Total fees paid by users for bridge txs, counted on the destination chain at the time of the deposit. |


| NEAR Intents rolling 30d share | Now | 30 days ago | 90 days ago | Window start |
| :--- | ---: | ---: | ---: | ---: |
| All included protocols | 27.3% (2026-11-21) | 14.1% (2026-10-22) | 12.1% (2026-08-23) | 35.0% (2026-05-23) |
| Relay excluded | 46.0% (2026-11-21) | 53.2% (2026-10-22) | 55.9% (2026-08-23) | 48.8% (2026-05-23) |


Trend of the rolling share: -5.37 pp per 30 days, 90% interval -8.61 to -2.14 (183 points, Newey-West 60 lags, R^2 0.47). Relay excluded: -1.35 pp per 30 days, 90% interval -2.31 to -0.39. Daily share, no overlap: -3.64 pp per 30 days, 90% interval -6.30 to -0.98. Excluding THORChain DEX (zero-fee run in the window): share 32.8% now against 41.6% at window start, trend -5.45 pp per 30 days, 90% interval -8.98 to -1.91.

Window: 2026-04-24 to 2026-11-21 (212 days common to all 6 protocols, set by Relay's first day). Trailing days left out as not final: 2026-11-22, 2026-11-23, 2026-11-24, 2026-11-25, 2026-11-26. Source: DefiLlama `summary/fees/<slug>?dataType=dailyFees`; records `defillama/fee_pool:<slug>:dailyFees` in the manifest.

Limits:

- Fee share is not volume share: a router charging more per dollar routed has a larger fee share at the same volume. DefiLlama's bridge-volume API is paid, so no volume-side comparison is made here.
- Adapter fee definitions differ, so the pool sums unlike quantities; each adapter's own text is quoted next to its protocol (`protocols[].methodology_fees`). The ex-Relay share is published because Relay's adapter counts integrator app fees and swap costs.
- The common window is 212 days (2026-04-24 to 2026-11-21), set by Relay's first day; the trend describes these months only.
- Routers outside DefiLlama's fee coverage (LI.FI and other aggregators) are absent, so the pool is these six protocols, not the cross-chain market.
- Rolling 30-day points overlap by 29 days; the interval uses a Newey-West error with 60 lags, and the daily non-overlapping share trend is reported as a cross-check.
- THORChain is measured by DefiLlama's `thorchain-dex` adapter (swap, outbound and affiliate fees); the `thorchain` slug is the chain's native transaction fee and is not a routing fee.
- The share path is not a line: it ranged from 2.5% (2026-09-13) to 45.3% (2026-07-04) and the linear trend explains 47% of its variance. Read the slope as the average drift over the window, not as a forecast.
- Relay's 30-day fees peaked at $205.95M on 2026-09-22, 14.7x its window median of $14.04M. NEAR Intents' share around that date moves with that surge in the denominator, not with a change in its own fees. Whether the surge is user-paid routing fees or an adapter artefact cannot be settled from this endpoint.
- THORChain DEX reports zero fees on 38 days of the window (longest run 37 days, 2026-05-16 to 2026-06-21). The zeros are kept as reported; if they are an adapter gap, the other protocols' shares are overstated for rolling windows that include those days. See the robustness share excluding it.

### 12.2 Size limits: the largest clip each router quotes

**1Click stops quoting at a smaller size than a competitor on 2 of 3 corridors: ETH USDC -> SOL USDC, $500K against LI.FI $5M; Base USDC -> Arbitrum USDC, $500K against LI.FI $5M.**

Dry quotes at $1K, $10K, $50K, $250K, $500K, $1M, $2.5M, $5M on each benchmarked corridor, run 2026-11-26T06:05:14.307Z: 60 quoted, 20 refused, 0 errors, 0 not attempted, 8 on routes the venue does not serve (88 cells, 24.983 s against a 75.0 s budget).

| Corridor | Venue | Largest size quoted | Cost at $250K | Cost at largest size | First size refused |
| :--- | :--- | ---: | ---: | ---: | ---: |
| ETH USDC -> SOL USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| ETH USDC -> SOL USDC | Relay | $1M | 3.00 bps | 3.00 bps | $2.5M |
| ETH USDC -> SOL USDC | LI.FI | $5M | 25.00 bps | 25.00 bps | none on the ladder |
| ETH USDC -> SOL USDC | Across | does not route | n/a | n/a | n/a |
| ETH USDC -> native BTC | 1Click | $1M | 9.66 bps | 16.22 bps | $2.5M |
| ETH USDC -> native BTC | Relay | $250K | 15.65 bps | 15.65 bps | $500K |
| ETH USDC -> native BTC | LI.FI | $1M | 33.61 bps | 32.70 bps via NEAR Intents | $2.5M |
| Base USDC -> Arbitrum USDC | 1Click | $500K | 2.02 bps | 2.02 bps | $1M |
| Base USDC -> Arbitrum USDC | Relay | $2.5M | 1.00 bps | 1.00 bps | $5M |
| Base USDC -> Arbitrum USDC | LI.FI | $5M | 25.00 bps | 25.00 bps | none on the ladder |
| Base USDC -> Arbitrum USDC | Across | $500K | 1.00 bps | 1.00 bps | $1M |


Cost: (amount in - amount out) / amount in x 1e4: on raw units where both legs are the same stablecoin, else on USD legs valued at one common price per cell (1Click token-list oracle, else the median of the venues' implied prices), as in execution_bench.

On this run 1Click quoted at least $1M on 1 of 3 corridors and stopped below a competitor on 2. That cuts against the case that the solver network already carries institutional clips on those routes: fee growth there has to come from retail-size flow until solver inventory deepens. On ETH USDC -> native BTC the largest competitor quote (LI.FI $1M) is 1Click execution resold; the largest quote on an independent route was $250K (Relay). Repeated runs in which 1Click quotes the same rungs its competitors do would overturn this reading.

Limits:
- A dry 'no liquidity' reflects the solvers' quoting policy at that moment. It is not proven hard depth, and a dry quote is not a fill.
- One run is one observation. Solver inventory and venue limits move within minutes; re-run before relying on a rung.
- Every figure is the largest size quoted on an eight-rung ladder ($1K to $5M), not depth. Sizes between two rungs were not observed.
- Cells marked not attempted did not complete inside the time budget. They carry no information about liquidity.

Raw responses: ledger records `ladder:<venue>:<corridor_id>:<size_usd>`; data in `snapshot.liquidity_ladder`.

### 12.3 Wider peer set: FDV to revenue across the top revenue chains

**The 60x terminal multiple cap sits at the 20th percentile of 15 peers (3 of 15 trade at or below it) on FDV to annualised 30-day revenue; the wide median is 364x (bootstrap 90% interval 184x to 1,404x), and NEAR on L1 gas revenue alone trades at 4,373x, the 87th percentile.**

The cap is at or below the upper quartile of the set (1,915x), so the model's terminal value does not rest on a multiple richer than what the market pays for chain revenue today. On L1 gas revenue alone NEAR (4,373x) is priced above the wide median (364x), so NEAR is not cheap on chain revenue; the long-term case has to be carried by Intents revenue, not by the L1 multiple. This reading is overturned if a re-run puts the cap above the 75th percentile of the set (peer multiples compressing toward 60x) or if the set shrinks below 8 peers.

| Chain | Token | Revenue, 30d | Revenue, annualised | FDV | FDV / revenue | Note |
| :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| Dexalot | ALOT | $193,602 | $2.4M | $4.0M | 1.7x | DefiLlama types this adapter 'protocol', not 'chain': its revenue is not plain chain gas revenue |
| Quai | QUAI | $146,075 | $1.8M | $8.1M | 4.5x | revenue is merged-mining block rewards earned on other chains and spent on QUAI buyback and burn (the adapter's own Fees text), not gas paid on Quai |
| **Model floor** |  |  |  |  | **8x** | terminal_multiple_floor (assumption) |
| Polygon | POL | $1.2M | $14.2M | $810.0M | 57.1x |  |
| **Model cap** |  |  |  |  | **60x** | terminal_multiple_cap (assumption); the multiple the model uses |
| Tron | TRX | $23.7M | $288.5M | $28.85B | 100.0x |  |
| Arbitrum | ARB | $511,667 | $6.2M | $1.14B | 184x | L2 governance token: sequencer revenue accrues to the DAO treasury, not to ARB by protocol rule |
| **NEAR (L1 + Intents, the model's basis)** | NEAR | $1.8M | $21.6M | $4.01B | **185x** | comps.near_combined; not like for like (no peer row includes app revenue) |
| Monad | MON | $284,664 | $3.5M | $1.10B | 318x |  |
| OP Mainnet | OP | $68,261 | $830,509 | $294.7M | 355x | L2 governance token: sequencer revenue accrues to the Optimism Collective, not to OP by protocol rule |
| Aptos | APT | $103,563 | $1.3M | $458.7M | 364x |  |
| ICP | ICP | $144,876 | $1.8M | $1.12B | 634x |  |
| Avalanche | AVAX | $390,155 | $4.7M | $3.14B | 662x |  |
| Filecoin | FIL | $62,370 | $758,835 | $1.07B | 1,404x |  |
| Ethereum | ETH | $7.0M | $85.0M | $206.14B | 2,425x |  |
| Solana | SOL | $995,895 | $12.1M | $45.10B | 3,722x |  |
| **NEAR (L1 gas revenue only)** | NEAR | $75,285 | $915,968 | $4.01B | **4,373x** | subject, not counted in the set |
| Hyperliquid L1 | HYPE | $1.1M | $13.1M | $58.32B | 4,460x | chain row covers HyperEVM gas only; HYPE's FDV is priced mostly on the HyperCore exchange, whose revenue DefiLlama books under separate Hyperliquid protocols (the model's three-peer set uses that parent) |
| BSC | BNB | $1.1M | $13.0M | $73.19B | 5,615x | exchange-linked token: BNB's FDV also prices Binance exchange utility, not only BNB Chain's fee burn |

Distribution of FDV / revenue across 15 peers: median 364x (bootstrap 90% interval 184x to 1,404x; 10,000 resamples, seed 20261114), P25 142x, P75 1,915x, IQR 1,773x, range 1.7x to 5,615x. The 60x cap: 3 of 15 peers at or below it (20th percentile). The 8x floor: 2 of 15 (13th percentile). NEAR on L1 gas revenue only: 4,373x, the 87th percentile; on the model's combined L1 + Intents basis 185x, which would be the 33rd percentile (not like for like).

Without the 6 flagged rows (9 peers): median 634x, P25 318x, P75 1,404x; 1 at or below the cap. For contrast, the three-peer median the model uses (Solana, Ethereum, Hyperliquid) is 2,425x (comps.median_fdv_to_revenue_ex_near), which the model clips to the 60x cap.

Inclusion rules (fixed before any multiple was computed):
- Universe: every DefiLlama fees-overview row with category 'Chain' and 30-day revenue (dataType=dailyRevenue) above zero.
- Ranking: by 30-day revenue, highest first. No chain is added or removed by hand after seeing its multiple.
- Peers: the first 15 chains in that ranking that have their own token with a CoinGecko fully diluted valuation.
- Excluded, each listed with its reason: chains with no native token; chains whose token has no FDV on CoinGecko; chains not in the chain-to-token mapping table (configuration in wide_peers.py); a second row for a token already counted.
- Flagged, not dropped: L2 tokens, exchange-linked tokens, rows whose adapter books something other than chain gas revenue and rows whose DefiLlama adapter is not typed 'chain'. They stay in the distribution; a sensitivity without them is reported next to it.
- NEAR is the subject. It is positioned against the set on the same basis (its own chain row and CoinGecko FDV) and is not counted in it.
- Multiple: FDV / (30-day revenue x 365 / 30). Percentile of a value: share of peers with a multiple at or below it.

Excluded inside the cut (3); 51 further chains rank below the last peer and were not evaluated:
- Base (rank 3 by revenue, $3.0M in 30 days): no native token: Coinbase-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.
- Robinhood Chain (rank 8 by revenue, $892,470 in 30 days): no native token: Robinhood-operated L2, gas is paid in ETH, so there is no token FDV to divide by revenue.
- Elysium (rank 15 by revenue, $123,542 in 30 days): not in the chain-to-token mapping table (wide_peers.COINGECKO_ID_BY_SLUG); not evaluated.

Caveats:
- FDV to revenue on 30 days annualised is noisy: one busy or quiet month moves a chain's multiple by a large factor.
- Revenue definitions differ by chain adapter (burned base fees, sequencer profit, treasury share, buyback and burn); the adapter's own text is carried per row.
- Token FDV for an L2 or an exchange-linked token does not accrue chain revenue the way an L1 gas token does; those rows are flagged and a sensitivity without them is shown.
- Selection: ranking by revenue picks the chains with the most revenue, which pulls their multiples down relative to the long tail of low-revenue chains.
- NEAR's multiple here uses L1 gas revenue only. The model values NEAR on L1 plus Intents revenue (comps.near_combined), which no peer row here has an equivalent of.
- One snapshot. Nothing here is a time series, and the cap's position will move with token prices and monthly fee volume.

Sources: `defillama/overview:fees:dailyRevenue` sha256 `239eeca4209ed226`, `coingecko/coins_markets_wide` sha256 `53222dd8126eb0af`; fetched 2026-11-26T06:05:11.093Z. Field: `snapshot.wide_peers`.

### 12.4 Take-rate history

Gross take compressed over the trailing year: the rolling 30-day rate is 18.4 bps on 2026-11-24 against 20.7 bps a year earlier, while average daily volume went from $124M to $143M; the trailing-365d log-linear trend is -27% per year (90% CI -42% to -9%), which excludes zero, and the trailing-180d trend, +69% per year (90% CI +46% to +94%), does not show the decline continuing.

| Window | Days (UTC) | Gross take (bps) | Net take (bps) | Holder take (bps) | Avg daily volume |
| :--- | :--- | ---: | ---: | ---: | ---: |
| last 30d | 2026-10-26 to 2026-11-24 | 18.41 | 3.99 | 3.99 | $143M |
| 30-60d ago | 2026-09-26 to 2026-10-25 | 16.37 | 5.28 | 5.28 | $132M |
| 60-90d ago | 2026-08-27 to 2026-09-25 | 14.91 | 3.61 | 3.61 | $151M |
| 150-180d ago | 2026-05-29 to 2026-06-27 | 12.42 | 2.78 | 2.78 | $80M |
| 330-360d ago | 2025-11-30 to 2025-12-29 | 20.40 | 0.90 | 0.00 | $65M |


- **Trend, trailing 365 days** (2025-11-25 to 2026-11-24, 365 rolling points): -27.4% per year, 90% CI -41.8% to -9.4% (excludes zero; Newey-West, 60-day lag).
- **Trend, trailing 180 days** (2026-05-29 to 2026-11-24, 180 rolling points): +68.6% per year, 90% CI +46.3% to +94.2% (excludes zero; Newey-West, 60-day lag).
- **Trend, full history** (2025-06-08 to 2026-11-24, 535 rolling points): +83.3% per year, 90% CI -1.0% to +239.4% (includes zero; Newey-West, 60-day lag). Dominated by the 2025 fee ramp from zero; not a competition signal.
- **Robustness of the trailing-365d trend** (reported, not graded): 30-day lag -40.5% to -11.3%; 120-day lag -40.9% to -10.8%; 13 non-overlapping 30-day windows -21.3% per year, Student-t 90% CI -36.3% to -2.7%.
- **Elasticity to volume, trailing 365 days** (365 days, 0 dropped for zero fees or volume): a 1% rise in daily volume goes with a -0.04% change in daily gross take, 90% CI -0.13 to +0.04 (includes zero; R2 0.01).
- **Elasticity to volume, full history** (555 days, 9 dropped for zero fees or volume): a 1% rise in daily volume goes with a +0.70% change in daily gross take, 90% CI +0.20 to +1.19 (excludes zero; R2 0.36).
- **Regime break** (first aligned day with dailyHoldersRevenue > 0): 2026-02-23. Pooled gross take 17.49 bps over the 289 days before (17.67 bps over the 90 of those inside the trailing year) and 15.91 bps over the 275 days since; net take 1.41 bps before (trailing year) and 3.38 bps since.
- **Range, trailing 365 rolling points**: gross take high 24.49 bps (2025-12-16), low 11.82 bps (2026-06-22).
- **Floor read** (trailing 365 rolling points): gross take was below the 0.5 bps model floor on 0 of them (minimum 11.82 bps, 2026-06-22); net take was below the 3 bps fee-race trigger on 268 (minimum 0.00 bps, 2025-12-31), and on 149 of the 246 windows that start after the regime break.

**Read.** This cuts against the bull case: gross take fell at 27% per year over the trailing year with an interval that excludes zero (non-overlapping check: -21% per year, 90% CI -36% to -3%, also excludes zero), so the claim that pricing power has held while volume grew is not supported by the fee history; the level is still 37x the 0.5 bps model floor. The trailing-180d trend is +69% per year (90% CI +46% to +94%): the decline is not visible in the last six months. A trailing-365d interval that includes zero again would overturn this read; a 180d interval wholly below zero would show compression still in progress. NEAR's captured (net) take went from 2.1 bps to 4.0 bps over the same span and sat under the 3 bps fee-race trigger on 268 of 365 trailing rolling points.

Data: 564 aligned settled days 2025-05-10 to 2026-11-24 (raw); unsettled trailing day(s) excluded: 2026-11-25. Source: defillama/fees:near-intents:dailyFees sha256 e02bb715ff95...; defillama/fees:near-intents:dailyRevenue sha256 8c48531cadd0...; defillama/fees:near-intents:dailyHoldersRevenue sha256 ab2cddd9f13c...; defillama/dexs:near-intents sha256 e46dc7a5272e....

Limits:
- Early history mixes fee regimes: the DefiLlama fee chart ramps from zero in mid-2025 and net revenue is zero until the first sweep, so the full-history trend measures fees being switched on. Read the trailing-365d figures.
- Fees, revenue and holders revenue follow DefiLlama's near-intents adapter definitions: gross fees include the affiliate fee each frontend keeps; revenue is NEAR swept into the revenue wallets and is booked on the sweep day, so net take is lumpy and can exceed fees on single days. An adapter revision restates the whole series.
- Rolling 30-day points overlap (29 of 30 days shared), so about 12 independent observations sit in a year. A Newey-West interval on such points is too narrow at this sample size: in the seeded null simulation in quant/tests/test_take_rate_series.py a trendless series is flagged well above the nominal 10% of the time. The non-overlapping 30-day check (Student-t) stays near its nominal size and is the stricter read: treat a trend as established only when both intervals exclude zero. An interval that includes zero means no decline was detected, not that none exists.
- The elasticity regresses fees/volume on volume: noise in daily volume enters both sides and pushes the estimate negative.

### 12.5 Volume engine: GBM against a block bootstrap, out of sample

The block bootstrap does not repair the volume engine: P10-P90 coverage (1m 20/20 (100%, p 0.02), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33)) is rejected against 80% for over-coverage at 1m and 3m; the pass at 6m rests on 14 overlapping forecasts, which is weak evidence; its band is 2.1x to 3.1x the GBM's log width, so it covers by being wide, not by being sharp; the GBM is rejected at 2 of 3 horizons (1m 15/20 (75%, p 0.58), 3m 10/17 (59%, p 0.06), 6m 7/14 (50%, p 0.01)), so the two engines bracket realized dispersion and neither is calibrated.

| Engine | Horizon | n | Inside | Coverage | Binomial p vs 80% | Below P10 / above P90 | Realized / median | Band width, ln(P90/P10) | Verdict |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :--- |
| GBM, registry drift (valuation engine) | 1m | 20 | 15/20 | 75% | 0.58 | 1 / 4 | 1.31x | 1.26 | 80% not rejected |
| GBM, registry drift (valuation engine) | 3m | 17 | 10/17 | 59% | 0.06 | 0 / 7 | 2.22x | 2.22 | 80% rejected |
| GBM, registry drift (valuation engine) | 6m | 14 | 7/14 | 50% | 0.01 | 0 / 7 | 4.06x | 3.24 | 80% rejected |
| Block bootstrap, resampled drift | 1m | 20 | 20/20 | 100% | 0.02 | 0 / 0 | 0.92x | 2.59 | 80% rejected |
| Block bootstrap, resampled drift | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.32x | 6.18 | 80% rejected |
| Block bootstrap, resampled drift | 6m | 14 | 13/14 | 93% | 0.33 | 1 / 0 | 0.10x | 9.97 | 80% not rejected |
| Block bootstrap, registry drift (shape only) | 1m | 20 | 15/20 | 75% | 0.58 | 0 / 5 | 1.92x | 2.50 | 80% not rejected |
| Block bootstrap, registry drift (shape only) | 3m | 17 | 8/17 | 47% | 0.003 | 0 / 9 | 22.24x | 6.15 | 80% rejected |
| Block bootstrap, registry drift (shape only) | 6m | 14 | 1/14 | 7% | <0.001 | 0 / 13 | 4399.49x | 9.94 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 1m | 20 | 20/20 | 100% | 0.02 | 0 / 0 | 0.88x | 3.02 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 3m | 17 | 17/17 | 100% | 0.03 | 0 / 0 | 0.31x | 7.78 | 80% rejected |
| Sensitivity: bootstrap, n^(1/3) blocks | 6m | 14 | 14/14 | 100% | 0.09 | 0 / 0 | 0.10x | 12.63 | 80% rejected |


Target coverage 80%; verdict rule: exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10. Bootstrap: 10,000 paths per origin, seed 20261114, mean block length 7 to 58 days across origins (median 12). At 1 month the bootstrap band is 2.06x the GBM band in log width. At 3 months the bootstrap band is 2.79x the GBM band in log width. At 6 months the bootstrap band is 3.08x the GBM band in log width.

Power at one month (n = 20): the test accepts 14 to 19 forecasts inside the band. A model whose true coverage is 60% would be rejected 75% of the time and one at 70% only 39% of the time, so a pass does not separate a calibrated engine from a mildly miscalibrated one.

Valuation effect, volume. The valuation uses the GBM; this is unchanged. From the latest origin (2026-11-25, trailing 30-day volume $4.31B), 30-day volume 12 months ahead as a multiple of current, P10 / P50 / P90: GBM 0.59x / 1.61x / 4.35x; bootstrap with the same expected path 0.14x / 0.79x / 4.66x; bootstrap with its own resampled drift 0.45x / 2.53x / 14.91x.

Valuation effect, FDV. Feeding bootstrap volume paths (same expected path, same price, take-rate and issuance paths, 10,000 paths) through the Monte Carlo gives FDV P10 / P50 / P90 of $92M / $588M / $5.75B against the base $667M / $2.06B / $6.65B (0.14x / 0.28x / 0.86x of base). The base run reproduces `sotp.fdv_percentiles` exactly. The bootstrap run holds the mean volume path fixed, so its lower median is the convexity cost of a wider distribution. These are variant figures; no headline number uses them.

The valuation uses the GBM. At the same expected path the bootstrap puts 30-day volume 12 months out at 0.14x / 0.79x / 4.66x of current (P10 / P50 / P90) against the GBM's 0.59x / 1.61x / 4.35x, a band 1.8x as wide in log terms; through the same Monte Carlo FDV P10 / P50 / P90 becomes 0.14x / 0.28x / 0.86x of the base. The backtest rejects the bootstrap for over-coverage, so read this as a stress bound on volume dispersion (with the mean path held fixed, a wider distribution lowers the median), not as a better central estimate.

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
| NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB) | **VERIFIED_ON_CHAIN** | intents.near storage_usage 14,228,050,111 bytes = 142,281 NEAR locked; 289,149 NEAR across 8 tracked contracts | near_rpc/view_account:intents.near sha256 e77a3fde3902... @ block 226,265,522; storage_amount_per_byte from EXPERIMENTAL_protocol_config | high | growth 39,604,891 B/day = 396.0 NEAR/day over 30.4 d (archival); a 0.01 NEAR/KB lock is released if state is deleted, so it is a sink while state grows |
| Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap | **VERIFIED_ON_CHAIN** | 25,710.84 NEAR minted at epoch start 226,252,337 x 1,274.6 epochs/yr = 32,772,196 NEAR/yr (2.4965%), -0.14% vs nominal 32,818,228 | near_rpc/block:226252337 sha256 fe84ede1d1d7... and its predecessor by prev_hash; previous epoch start 226209137 | high | second independent jump 25,553.51 NEAR; within-epoch drift -206.44 NEAR/epoch is the net gas burn |
| Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC | **VERIFIED_LIVE_API** | median headroom +1.05 bps over 3 comparable cells (dest_units); competitor ceiling 3.00 bps | oneclick/relay/lifi/across quote records 2026-11-26T06:05:11.092Z | medium | $500: +1.36 bps vs relay (rank 1/3); $50,000: +1.05 bps vs relay (rank 1/3); $250,000: +0.98 bps vs relay (rank 1/3); no 1Click capacity failures |
| Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC | **VERIFIED_LIVE_API** | 1Click delivers +4.12 bps more BTC per USDC (median over 3 cells, dest_units; no USD oracle in the ranking) | oneclick/lifi/relay quote records 2026-11-26T06:05:11.092Z | medium | clip-dependent: $500: -9.98 bps vs relay (rank 2/3); $50,000: +4.12 bps vs relay (rank 1/3); $250,000: +6.65 bps vs relay (rank 1/3); LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used |
| EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative) | **VERIFIED_LIVE_API** | median headroom -1.02 bps over 3 cells (dest_units; 1Click trails) | oneclick/across/relay/lifi quote records 2026-11-26T06:05:11.092Z | medium | $500: -0.24 bps vs across (rank 2/4); $50,000: -1.02 bps vs across (rank 3/4); $250,000: -1.02 bps vs across (rank 3/4); the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins |
| Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material | **DERIVED** | deposit/caller HHI_external 1,956 [90% CI 1,276-2,600] (N_eff 5.11), ex-AI-agent 1,524; AI-agent share 36.7% (>= 10% materiality line), bridge share 60.0% | nearblocks/txns:intents.near:p1 sha256 873bd0913277... ... p8 | low | 200 unique receipts over 54 s; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources (bridge callbacks, direct callers), not solvers |
| Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers | **NOT_SUPPORTED** | not measured: 0 solver fill participations (< 10) in 0 decoded execute_intents receipts | nearblocks/txns:intents.near:p1 sha256 873bd0913277... ... p8 + 8 method-filtered execute_intents page(s); args.signed[].payload.message (NEP-413 signer_id) | low | 0 execute_intents receipts decoded; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty |
| Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume | **DERIVED** | 13.3% (band 11.8%-15.9%) estimated on-chain: Confidential Intents Treasury 24h inflow $21.7M / outflow $25.9M against 24h volume $162.9M; >= 10% materiality line | near_rpc/confidential:balances:head sha256 23cd5c0fef8d... treasury balances in intents.near (NEAR mainnet RPC) | low | nearstats' split was rejected by the plausibility guard; the share is estimated from the public treasury boundary instead. Biases: same-hour shield/unshield netting and in-shard turnover push it down, solver inventory pushes it up; 24h window |
| Confidential TVL backs the dark-pool engine (Engine 2) | **VERIFIED_ON_CHAIN** | $126.6M TVL read on-chain from the Confidential Intents treasury in intents.near (NEAR-reported via nearstats: $123.6M) | near_rpc/confidential:balances:head sha256 23cd5c0fef8d... intents.near mt_batch_balance_of (treasury) | high | Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut (0.7); the confidential take (20 bps) is an assumption |
| Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink | **DERIVED** | alpha 21.7%; gross take 18.41 bps, net take 3.99 bps; buyback sink 18,592 NEAR/day = 22.0% coverage incl. burn and lock | defillama/fees:near-intents:dailyHoldersRevenue sha256 ab2cddd9f13c... / defillama/fees:near-intents sha256 e02bb715ff95... | medium | DefiLlama revenue methodology: NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.near.org and the on-chain buyback). Split by destination wallet into front-end affiliate revenue and Other. Transfers between those wallets are excluded. |
| Chain Signatures (v1.signer) is a growing second usage engine beyond Intents | **NOT_SUPPORTED** | not measured: NearBlocks v1.signer endpoints unavailable this run | nearblocks (none) | none | cumulative_receipts: NearBlocks count endpoint failed; sign rate / trend: no sample window returned |
| The volume engine (GBM with measured sigma) is calibrated out of sample: P10-P90 covers ~80% of realized 30-day volume | **NOT_SUPPORTED** | 1m 15/20 = 75% inside P10-P90 (binomial p 0.58); 3m 10/17 = 59% inside P10-P90 (binomial p 0.06); 6m 7/14 = 50% inside P10-P90 (binomial p 0.01); 1m median realized / forecast median 1.31x (under-prediction); 1m coverage 50% for origins before 2026-01-29, 100% from it; 20 monthly origins 2025-04-04 to 2026-10-26 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 e46dc7a5272e... | low | Tests the volume distribution only; the take rate, holder capture, confidential share, multiple and discount rate are not backtested. 3m and 6m forecasts from monthly origins overlap, so their effective sample is smaller than n. |
| A block-bootstrap volume engine (fat tails, autocorrelation) is calibrated out of sample where GBM is not | **NOT_SUPPORTED** | block bootstrap 1m 20/20 (100%, p 0.02), 3m 17/17 (100%, p 0.03), 6m 13/14 (93%, p 0.33); GBM 1m 15/20 (75%, p 0.58), 3m 10/17 (59%, p 0.06), 6m 7/14 (50%, p 0.01); bootstrap at the GBM's expected path (shape only) 1m 15/20 (75%, p 0.58), 3m 8/17 (47%, p <0.01), 6m 1/14 (7%, p <0.01); bootstrap band 2.1x the GBM's log width at 1m; 20 monthly origins 2025-04-04 to 2026-10-26 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 e46dc7a5272e...; valuo.models.volume_bootstrap (seed 20261114, 10000 paths per origin) | low | Inside P10-P90 against an 80% target, exact two-sided binomial p. Low power: at n = 20 the test accepts 14 to 19 hits and rejects a 70%-coverage engine only 39% of the time; 3m and 6m forecasts overlap. Block length (Politis-White) and path count were fixed before coverage was computed; nothing is tuned. The valuation still uses the GBM; this row grades a parallel variant and tests the volume distribution only. |
| NEAR Intents' realized gross take rate is not trending to zero as volume grows | **NOT_SUPPORTED** | rolling 30d gross take 18.41 bps on 2026-11-24 vs 20.69 bps on 2025-11-25; trend -27.4%/yr, 90% CI -41.8% to -9.4% (excludes zero; Newey-West 60d lag, 365 overlapping points); floor 0.5 bps, 0 of 365 trailing points below it; non-overlapping 30d windows (n=13) -21.3%/yr, Student-t 90% CI -36.3% to -2.7%; trailing 180d trend +68.6%/yr, CI +46.3% to +94.2% | defillama/fees:near-intents:dailyFees sha256 e02bb715ff95...; defillama/fees:near-intents:dailyRevenue sha256 8c48531cadd0...; defillama/fees:near-intents:dailyHoldersRevenue sha256 ab2cddd9f13c...; defillama/dexs:near-intents sha256 e46dc7a5272e... | low | Graded on the trailing-365d trend only: a decline is counted when the Newey-West 90% interval and the non-overlapping-window Student-t interval both sit below zero; DERIVED needs no such decline and a latest rolling take above the model floor. Gross take includes affiliate fees kept by frontends; NEAR's captured share is the net / holder take. Rolling points overlap, so an interval that includes zero is not proof of a floor. The full-history trend is not used (fee ramp from zero in 2025). |
| 1Click quotes institutional size: at least $1M on every benchmarked corridor | **NOT_SUPPORTED** | ETH USDC -> SOL USDC: 1Click $500K, best competitor LI.FI $5M; ETH USDC -> native BTC: 1Click $1M, best competitor LI.FI $1M (routed through NEAR Intents); Base USDC -> Arbitrum USDC: 1Click $500K, best competitor LI.FI $5M (1 of 3 corridors with an attempted 1Click rung at or above $1M) | 1Click, Relay, LI.FI, Across dry quotes; ledger records ladder:<venue>:<corridor_id>:<size_usd> (81 responses), run 2026-11-26T06:05:14.307Z | low | Largest size quoted on an eight-rung ladder of dry quotes, one run. A dry 'no liquidity' is solver quoting policy at that moment, not proven depth, and a dry quote is not a fill. |
| NEAR Intents is gaining share of cross-chain routing fees | **NOT_SUPPORTED** | 27.3% of the six-protocol fee pool (30 days to 2026-11-21), rank 2 of 6 behind Relay at 40.8%; share at window start 35.0% (212-day common window); trend -5.37 pp per 30 days, 90% interval -8.61 to -2.14; ex-Relay 46.0%, trend -1.35 pp per 30 days, 90% interval -2.31 to -0.39 (share is falling) | defillama summary/fees dailyFees: near-intents, relay, across, debridge, chainflip, thorchain-dex | low | Fee share, not volume share; adapter fee definitions differ; the pool is the protocols DefiLlama covers. A share trend is DERIVED from live fee series, never VERIFIED. |
| The model's terminal multiple cap sits inside the observed peer range of FDV/revenue | **DERIVED** | cap 60x vs 15 chain tokens: 3 of 15 trade at or below it (20th percentile); P25 142x, median 364x [bootstrap 90% 184x to 1,404x], P75 1,915x, range 1.7x to 5,615x; NEAR L1-only 4,373x (87th percentile); without flagged rows: median 634x, n 9 | defillama/overview:fees:dailyRevenue sha256 239eeca4209e... + coingecko/coins_markets_wide sha256 53222dd8126e... | medium | Rule: DERIVED when the cap is at or below the 75th percentile of the wide set and n_peers >= 8. Here the cap is inside the observed range and at or below its upper quartile. FDV/revenue on 30 days annualised, one snapshot; revenue definitions differ by chain adapter; peers ranked by revenue and fixed before any multiple was computed (inclusion_rules, excluded). |


## 14. Assumptions register

### 14.1 Labeled assumptions (slider inputs; never presented as measured)
| Key | Default | Unit | Range | Justification |
| :--- | :--- | :--- | :--- | :--- |
| svrn_target_inflation | 0.016 | ratio_annual | [0.005, 0.03] | SVRN governance proposal to cut the protocol max_inflation_rate from 2.5% to 1.6%; not enacted on-chain (live EXPERIMENTAL_protocol_config.max_inflation_rate is still [1, 40]). |
| svrn_glidepath_months | 24 | months | [6, 48] | QUANT_PIPELINE_SPEC and TERMINAL_UI_SPEC model the 2.5% -> 1.6% cut as a linear 24-month (730-day) glidepath; the proposal itself does not fix the phasing. |
| public_volume_growth_yoy | 1.1721 | ratio_yoy | [0.558122, 2.02803] | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-26 to 2026-11-25 (365 days, DefiLlama dexs/near-intents): +117.2%/yr, 90% CI +55.8% to +202.8% (Newey-West, 30-day lags). Range = that CI. Median trend growth used as EXPECTED growth (conservative). Replaces the registry default +30%. Cross-checks (not used): yoy_trailing_30d +16%; mean_monthly_log_return_12m +18%. |
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
| total_supply_near | 1,312,729,117 | NEAR | measured | RPC block header total_supply at height 226265522 |
| current_max_inflation_rate | 0.025 | ratio_annual | measured | RPC EXPERIMENTAL_protocol_config.max_inflation_rate |
| treasury_share | 0 | ratio | measured | RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this) |
| staked_supply_ratio | 0.45412 | ratio | measured | RPC validators current stake / total_supply (350 validators) |
| annual_issuance_near | 32,772,196 | NEAR_per_year | measured | minted_per_epoch 25710.836911087157 NEAR x epochs_per_year 1274.6452400285953 from total_supply jumps at epoch starts 226209137 -> 226252337 |
| issuance_realization_factor | 0.998597 | ratio | measured | measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path |
| near_price_usd | 3.06 | USD | measured | nearstats price.currentUsd via intents_forensics.price.current_usd |
| daily_volume_usd | 142,555,457 | USD_per_day | measured | intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window (aligned daily charts, 30 complete UTC day |
| gross_take_bps | 18.4147 | bps | measured | intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window (aligned daily charts, 30 complete UTC |
| capture_ratio | 0.216714 | ratio | measured | intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window (aligned daily charts, 30 complete  |
| gas_burn_near_per_day | 720.4255 | NEAR_per_day | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| state_lock_growth_near_per_day | 409.2661 | NEAR_per_day | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| public_volume_growth_yoy | 1.1721 | ratio_yoy | measured | MEASURED: trend growth of NEAR Intents daily volume, 2025-11-26 to 2026-11-25 (365 days, DefiLlama dexs/near-intents): +117.2%/yr, 90% CI +55.8% to +202.8% (New |
| competitive_fee_ceiling_bps | 3.0041 | bps | derived | median over cross-VM cells of the best competitor's friction (per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding); the lowest-fric |
| tau_floor_bps | 1.048 | bps | derived | max(0.5 bps, min(live public take, live cross-VM headroom)) from the execution benchmark (headroom_by_archetype_bps.cross_vm = 1.05 bps). |
| tau_pub_start_bps | 18.1712 | bps | derived | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d; blended live gross take 18.41 bps (DefiLlama daily fees / daily volume summed over the a |
| alpha_capture | 0.216714 | ratio | measured | measured:defillama near-intents dailyHoldersRevenue / fees |
| terminal_multiple | 60 | x_fdv_to_revenue | derived | peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; raw 2425.5x. |
| confidential_share_start | 0.133182 | ratio | derived | on-chain estimate: Confidential Intents Treasury 24h inflow / (24h volume + inflow) = 13.3% (band 11.8%-15.9%); nearstats split implausible. Estimated from the  |
| sigma_price_annual | 1.0298 | ratio_annual | measured | nearstats:price-history: 1y daily closes, log-return sigma x sqrt(365). |
| sigma_volume_monthly | 0.224058 | ratio_monthly | measured | measured: monthly log-return sigma of 30-day volume aggregates |


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

241 raw exchanges (191 ok, 50 failed), 13,018,419 bytes hashed; raw bodies persisted under `artifacts/raw` and listed with SHA-256 in `manifest.json`.

| Source | Records |
| :--- | ---: |
| across | 15 |
| coingecko | 2 |
| defillama | 22 |
| lifi | 33 |
| near_rpc | 36 |
| near_rpc_archival | 19 |
| nearblocks | 43 |
| nearstats | 2 |
| oneclick | 36 |
| relay | 33 |


Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):
| Source | Name | HTTP | Error |
| :--- | :--- | :--- | :--- |
| nearblocks | txns_count:intents.near | 410 | HTTP 410 |
| across | quote:eth_usdc_sol_usdc:50000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:500 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:250000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | ladder:across:eth_usdc_sol_usdc:1000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| relay | ladder:relay:eth_usdc_btc:500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $477, |
| relay | ladder:relay:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,51 |
| relay | ladder:relay:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $1,51 |
| relay | ladder:relay:eth_usdc_btc:1000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $477, |
| across | ladder:across:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 700858.201852 US |
| relay | ladder:relay:eth_usdc_btc:2500000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $477, |
| relay | ladder:relay:eth_usdc_btc:5000000 | 400 | HTTP 400: INSUFFICIENT_LIQUIDITY: Amount is higher than the available liquidity. Max amount is $477, |
| across | ladder:across:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 700858.201852 US |
| across | ladder:across:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Amount is higher than available liquidity. Max amount is 700858.201852 US |
| relay | ladder:relay:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: AMOUNT_TOO_HIGH: Quote amount exceeds the maximum for this pair |
| oneclick | ladder:1click:eth_usdc_sol_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:1000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:2500000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_btc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:eth_usdc_sol_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| oneclick | ladder:1click:base_usdc_arb_usdc:5000000 | 400 | HTTP 400: No liquidity available |
| lifi | ladder:lifi:eth_usdc_btc:2500000 | 404 | HTTP 404: No available quotes for the requested transfer |
| lifi | ladder:lifi:eth_usdc_btc:5000000 | 404 | HTTP 404: No available quotes for the requested transfer |
| nearblocks | txns:v1.signer:count | 410 | HTTP 410 |
| nearblocks | txns:v1.signer:before_date:2026-11-26 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:226133726 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-10-29 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:225869564 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-02 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:225605402 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-06 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:225341241 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-10 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-14 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-18 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-22 | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_date:2026-11-26:retry | 422 | HTTP 422 |
| nearblocks | txns:v1.signer:before_block:226133726:retry | 422 | HTTP 422 |


### 16.1 Methodology warnings recorded during the run (19)
- wide_peers: chain 'elysium' ranks 15 by 30-day revenue but has no entry in the mapping table; listed as excluded
- fee_pool: across: 3 malformed, negative or duplicate chart rows skipped
- execution_bench: eth_usdc_sol_usdc $500: venue USD oracles disagree with the cell's common price by more than the +1.36 bps headroom (1click +0.0 bps, relay +4.2 bps, lifi +44.2 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the +1.05 bps headroom (1click +0.0 bps, relay +4.2 bps, lifi +44.2 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +4.2 bps, lifi +44.2 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $500: venue USD oracles disagree with the cell's common price by more than the -9.98 bps headroom (1click +0.0 bps, relay -19.6 bps, lifi +50.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $50,000: venue USD oracles disagree with the cell's common price by more than the +4.12 bps headroom (1click +0.0 bps, relay -19.6 bps, lifi +50.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $250,000: venue USD oracles disagree with the cell's common price by more than the +6.65 bps headroom (1click +0.0 bps, relay -19.6 bps, lifi +50.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $500: venue USD oracles disagree with the cell's common price by more than the -0.24 bps headroom (1click -0.0 bps, relay +4.2 bps, lifi +18.9 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +4.2 bps, lifi +18.9 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +4.2 bps, lifi +18.9 bps); headroom is measured on destination units, not USD legs
- intents_forensics: nearblocks txns/count unavailable (HTTP 410); lifetime_receipts null
- intents_forensics: nearblocks execute_intents page 1 carried no usable id/timestamp pairs; solver sample falls back to contiguous cursor pages
- intents_forensics: confidential split: nearstats reports confidential 30d $0.00 (0.0000%), rejected (tvl_without_volume: confidential TVL $126.63M but all-time confidential volume $0.00 of $41.25B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'). Share ESTIMATED ON-CHAIN from the Confidential Intents Treasury: 13.3% (band 11.8%-15.9%; 24h inflow $21.70M, outflow $25.93M, volume $162.90M), replacing the registry assumption 40%
- intents_forensics: take-rate window leaves out 2026-11-25: DefiLlama reports revenue above fees for that day, so its fee figure is not final; the window ends the day before
- chain_signatures: NearBlocks txns/count unavailable (HTTP 410); cumulative receipts null
- chain_signatures: 12 of 12 sample windows failed; rates use the 0 that returned
- sotp: confidential share 13.3% is an ON-CHAIN ESTIMATE from Confidential Intents Treasury boundary flows (band 11.8%-15.9%), not nearstats' split (rejected as implausible); 24h window, biases listed in intents_forensics.volume.confidential_share_estimate
- sotp: peer median FDV/revenue 2425.5x clipped to 60.0x (guardrails [8, 60])
