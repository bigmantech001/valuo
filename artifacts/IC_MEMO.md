# Valuo IC Memo: NEAR at block 224,026,014

*NEAR Intents clearinghouse + NEAR L1. Generated 2026-11-11T06:05:03.180Z UTC from live mainnet RPC and key-free public APIs; every figure below is in `artifacts/latest_snapshot.json` with a SHA-256-hashed raw payload in `artifacts/manifest.json`. Judged on evidence: measured values are labeled measured, derived values derived, and assumptions are listed with their ranges in section 13.*

| Provenance | Value |
| :--- | :--- |
| NEAR block | 224,026,014 (`Dmbpkt6uoRRGeYWMniCkHSHA4mVy8qcSi9cVarVatm5P`), 2026-11-11T06:05:00.892Z |
| RPC endpoint | https://free.rpc.fastnear.com |
| Snapshot generated | 2026-11-11T06:05:03.180Z UTC, runtime 400.1 s, valuo 0.1.0, schema 1.0.0 |
| Snapshot SHA-256 | `bfea7b9118863c7c0adcc7399b3dad4bbdf70c006dd3e11d0d118735d3eaa96c` |
| Monte Carlo | seed 20261114, 10,000 paths, 36 months |
| Raw records | 133 HTTP/RPC exchanges hashed, 3 non-2xx/failed (every one listed in manifest.json) |


## 1. The long-term case, made falsifiable

The long-term case for NEAR at $4.80B: 3 of 8 measured conditions are on track. It holds if the market keeps an L1 multiple (396x revenue needed against a 2,411x peer median) while Intents grows into it; it fails if volume growth stays near 21% a year against the 167% the price implies.

| Condition | Required | Live | Trend | Status |
| :--- | ---: | ---: | :--- | :--- |
| Intents volume compounds fast enough to grow into the price | 167% a year | 21% a year | +87% (30-day volume vs 90 days earlier) | **Behind** |
| Holder revenue (buybacks) scales to support the price at the model's multiple | $178.2M a year | $22.1M a year | +272% (30-day holder revenue vs 90 days earlier) | **Behind** |
| The market keeps valuing NEAR like an L1, not like a fee-only app | 396x | 2,411x | n/a | **On track** |
| 1Click keeps a pricing edge where it competes (cross-VM routes) | > 0 | +0.98 bps | n/a | **On track** |
| Confidential (private) flow keeps growing | > 0 | $18.1M | +382% (confidential TVL vs 90 days earlier) | **On track** |
| Fees retire more NEAR than issuance creates | $425.9M a day | $125.3M a day | n/a | **Behind** |
| Governance cuts issuance from 2.5% to 1.6% | 1.6% | 2.5% | n/a | **Behind** |
| Solver competition stays broad enough to keep spreads tight | <= 3,500 | 4,876 | n/a | **Against** |


How to read it: each requirement is what the market price needs if that condition alone carries the case (from the reverse valuation in section 3), or the threshold the bear case watches (section 11). An investor holding NEAR long-term is betting that the conditions marked Behind close; the ones marked Against are where the case is currently losing. Re-run `make reproduce` to re-grade every row against live data.

## 2. Executive summary

**Model value vs market value.** Market FDV is $4.80B (spot price x on-chain total supply at block 224,026,014). The model's expected-path FDV is $775.4M and its 10,000-path Monte Carlo gives P10 / P50 / P90 = $54.0M / $248.1M / $1.57B. The market sits above the expected path (6.2x it) and at 19.3x the Monte Carlo P50. The model capitalises NEAR Intents holder revenue, L1 gas burn and state-lock flow over 36 months at a 25% discount rate and a 60x terminal multiple; the question below is which input would have to change for it to reach the market price, and whether the evidence allows that.

**What the market is pricing** (one input at a time, all others at base, solved on the expected path with brentq; full table in section 3).

| Input | Base | Required for market FDV | Evidence | Inside evidence |
| :--- | ---: | ---: | ---: | :--- |
| Expected annual public-volume growth (3-year path) | 30.0% | 167.2% | 20.8% | no |
| Starting gross public take rate | 10.88 bps | 183.52 bps | 3.00 bps | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 396x | 2,411x | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $1.48B) | 10.0% | n/a |
| Confidential share of volume at month 36 | 40.0% | 91.6% | 40.0% (ASSUMED, not measured) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $26.5M/yr | $178.2M/yr | $22.1M/yr | no |


**Conclusion.** The market price is consistent with NEAR's holder revenue capitalised at an L1 peer multiple (396x needed; live peer FDV/revenue HYPE 82x, SOL 2,411x, ETH 3,319x, median 2,411x over n = 3 peers). No discount rate closes the gap: even at 0% the model reaches $1.48B against the market's $4.80B, because the terminal multiple is capped at 60x. The gap is a multiple question, not a discount-rate question. The market values NEAR the way it values other L1 tokens, on a revenue multiple that carries a monetary premium, not as a claim on Intents cash flow at the model's 60x terminal cap. On cash flow alone (multiple held at the model's 60x), the market price requires 167%/yr expected public-volume growth for 3 years (trailing 12 months: +20.8%), or a 184 bps starting public take (today 10.88 bps, live competitive ceiling 3.00 bps), or $178.2M of annualised holder revenue in year 3 (8.1x today's $22.1M); none of these is inside its measured evidence. Whether NEAR keeps an L1 multiple is the investment question; this model does not assume it, so its value is what the measured cash flows support, not a fair value of the token.

**What you have to believe** (section 4). The three inputs that move FDV most are Expected annual public-volume growth (-20.0% to 150.0%: $241.4M-$4.04B); Terminal FDV / holder-revenue multiple (8.00x to 150x: $153.3M-$1.85B); Public take compression speed (per month) (0.0%/month to 15.0%/month: $283.7M-$1.25B). Together they carry 91% of the swing-squared variance proxy. 0 of 17 single-input ranges reach the market FDV.

**Relative value** (section 5). NEAR trades at 70x annualised fees against a peer median of 253x (rank 2 of 4, lowest multiple first; inside the peer range); at peer FDV/fees multiples NEAR's fees map to $10.76B-$43.75B (cross-check, not a fair value; n = 3 peers); holder revenue covers 19% of the $119.9M/yr security budget.

**Evidence quality flags.**

- Confidential share: NOT MEASURED this run. nearstats reported 0.0000% of 30d volume as confidential, which its own payload contradicts (tvl_without_volume: confidential TVL $141.26M but all-time confidential volume $0.32 of $38.26B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok); the model uses the registry assumption confidential_share = 40% (range 15%-60%), so Engine 2 ($414.9M of the $775.4M expected-path FDV) values an assumed volume. On-chain cross-check: the Confidential Intents treasury (`51e8f94d...de7cbe` in `intents.near`) holds $141.3M at block 224,026,027 (204 tokens, 30 unpriced); net 30-day boundary flow $18.1M at today's prices; over 24h at least $21.6M entered and $17.6M left (hourly snapshots, lower bounds), an inflow of 12.4% of 24h volume. Confidential swaps settle on a private chain whose RPC needs authentication, so swap volume itself cannot be read; boundary inflow is a proxy, not the share (it nets same-hour flows and includes solver inventory).
- Deposit/caller HHI 2,219 (bootstrap 90% CI 1,403-3,265) over 28 external receipts spanning 50 s; a point sample, not a market-share estimate.
- Solver HHI 4,876 (bootstrap 90% CI 3,878-5,322) over 77 fill participations spanning 29,003 s. Cartel trigger: BREACHED (sample: 77 solver fill participations over 29,003 s).
- Bear case: 2 of 4 graded early-warning triggers breached. Combined-worst deterministic FDV $104.1M (-87%).

## 3. What the market is pricing (reverse valuation)

Basis: deterministic_sotp expected path (mean-matching GBM); one input moved at a time, all others at the snapshot base. Solver: scipy.optimize.brentq on [lo, hi] search bounds, xtol = rtol = 1e-12. Market FDV $4.80B; expected-path model FDV $775.4M (gap 6.2x); Monte Carlo P50 $248.1M (gap 19.3x). Every required value is the expected-path requirement; the P50 sits lower by lognormal convexity, so the P50 requirement is larger still. 'Inside evidence' compares the required value with the evidence in the direction that makes the thesis harder (higher growth, take, multiple, share or revenue; lower discount rate).

| Input | Base | Required for market FDV | Evidence | Evidence basis | Inside evidence |
| :--- | ---: | ---: | ---: | :--- | :--- |
| Expected annual public-volume growth (3-year path) | 30.0% | 167.2% | 20.8% | trailing-12-month NEAR Intents 30-day volume growth | no |
| Starting gross public take rate | 10.88 bps | 183.52 bps | 3.00 bps | live competitive fee ceiling (median best-competitor friction, cross-VM cells) | no |
| Terminal FDV / annual holder-revenue multiple | 60x | 396x | 2,411x | peer median FDV / annualised revenue ex-NEAR (unclipped) | yes |
| Annual discount rate | 25.0% | not reachable at any discount rate >= 0% (FDV at 0% is $1.48B) | 10.0% | low end of the registry discount-rate range (10%-40%) | n/a |
| Confidential share of volume at month 36 | 40.0% | 91.6% | 40.0% (ASSUMED, not measured) | ASSUMED confidential share (registry confidential_share; the nearstats split was not measured this run) | no |
| Year-3 annualised holder revenue at the base multiple (volumes scaled jointly) | $26.5M/yr | $178.2M/yr | $22.1M/yr | current annualised holder revenue (30-day window x 365.25/30) | no |

- Justifying $4.80B needs 167% expected annual public-volume growth for 3 years (base 30%); trailing-12-month Intents volume growth was 21%.
- Justifying $4.80B needs a starting gross public take of 183.5 bps (decaying to the 0.98 bps floor at 3%/month) versus 10.88 bps today; the live competitive fee ceiling is 3.00 bps.
- Justifying $4.80B needs a 396x terminal FDV/holder-revenue multiple; the live peer median is 2,411x (HYPE 82x, SOL 2,411x, ETH 3,319x) and the model caps it at 60x.
- Even a 0% discount rate gives $1.48B, short of $4.80B: the gap is not a discount-rate question.
- Justifying $4.80B needs the confidential share to reach 92% by month 36; the share is NOT MEASURED this run (the model assumes 40%, registry confidential_share).
- Justifying $4.80B at the 60x base multiple needs $178M of annualised holder revenue in year 3 (6.7x the base path's $26M), versus $22M today (101%/yr compounded).

Headline: Market FDV $4.80B is 6.2x the model's expected-path FDV $775M; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 396x (evidence 2,411x).

Each solve moves one input. Inputs interact (the terminal multiple scales every engine's terminal value; growth and take compound), so the joint requirement is smaller than any single one; section 4 shows which inputs carry the variance.

## 4. What you have to believe (one-at-a-time sensitivity)

Basis: deterministic_sotp expected path; one input at its low / high, all others at the snapshot base. Base expected-path FDV $775.4M against a $4.80B market FDV. Variance share: swing^2 / sum(swing^2): first-order share for independent inputs, an approximation. Ranges: assumptions use their registry [low, high]; measured inputs use a measured dispersion where the snapshot has one, otherwise the labeled band `sensitivity_unmeasured_band` (each row states its basis in the snapshot).

| # | Input | Source | Range | Base | FDV at low | FDV at high | Swing | Variance share |
| ---: | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Expected annual public-volume growth | assumption | -20.0% - 150.0% | 30.0% | $241.4M | $4.04B | $3.80B | 72.1% |
| 2 | Terminal FDV / holder-revenue multiple | derived | 8.00x - 150x | 60x | $153.3M | $1.85B | $1.70B | 14.4% |
| 3 | Public take compression speed (per month) | assumption | 0.0%/month - 15.0%/month | 3.0%/month | $1.25B | $283.7M | $967.3M | 4.7% |
| 4 | Confidential share at month 36 | assumption | 5.0% - 60.0% | 40.0% | $417.8M | $1.18B | $757.5M | 2.9% |
| 5 | Annual discount rate | assumption | 10.0% - 40.0% | 25.0% | $1.12B | $560.1M | $563.0M | 1.6% |
| 6 | Starting 30-day Intents volume (public + confidential) | measured | 0.71x - 1.42x | 1.00x | $568.5M | $1.07B | $500.5M | 1.2% |
| 7 | Holder capture (revenue / gross fees) | measured | 12.9% - 33.3% | 33.3% | $346.3M | $775.4M | $429.1M | 0.9% |
| 8 | NEAR price drift (gas-burn and state-lock USD value) | assumption | -50.0% - 100.0% | 0.0% | $716.0M | $1.13B | $415.3M | 0.9% |
| 9 | Confidential multiple haircut | assumption | 30.0% - 100.0% | 70.0% | $557.0M | $939.3M | $382.3M | 0.7% |
| 10 | Confidential compression divisor | assumption | 1.00x - 10x | 3.00x | $601.0M | $865.8M | $264.8M | 0.3% |
| 11 | Blended gross take (public take re-reconciled) | measured | 12.47 bps - 16.85 bps | 14.53 bps | $695.7M | $865.9M | $170.2M | 0.1% |
| 12 | Public take hard floor | assumption | 0.00 bps - 5.00 bps | 0.50 bps | $775.4M | $942.2M | $166.7M | 0.1% |
| 13 | Confidential gross take (public take re-reconciled to live fees) | assumption | 10.00 bps - 30.00 bps | 20.00 bps | $726.9M | $824.0M | $97.1M | 0.0% |
| 14 | NEAR spot price (USD value of gas burn and state lock) | measured | $2.72 - $4.92 | $3.66 | $756.7M | $800.7M | $44.0M | 0.0% |
| 15 | L1 gas burn (NEAR/day) | measured | 638 NEAR/day - 1,063 NEAR/day | 851 NEAR/day | $757.5M | $793.4M | $35.9M | 0.0% |
| 16 | Cross-VM headroom (sets the public take floor) | measured | 0.74 bps - 1.23 bps | 0.98 bps | $765.3M | $785.6M | $20.4M | 0.0% |
| 17 | State-lock growth (NEAR/day) | measured | 249 NEAR/day - 415 NEAR/day | 332 NEAR/day | $775.1M | $775.8M | $708,302 | 0.0% |

Top three inputs carry 91% of the variance proxy. 0 of 17 single-input ranges reach the market FDV at either end.

Headline: public_volume_growth_yoy, terminal_multiple, fee_compression_lambda_monthly carry 91% of the swing-squared variance proxy; public_volume_growth_yoy alone moves FDV from $241M to $4.04B across its range, and 0 of 17 single-input ranges reach the $4.80B market FDV.

Excluded (move issuance and implied price, not FDV): svrn_target_inflation (issuance path only: moves supply at horizon and implied price, not FDV); svrn_glidepath_months (issuance path only: moves supply at horizon and implied price, not FDV).

## 5. Relative value: peer cash-flow multiples and the security budget

Basis: live comps (DefiLlama fees/revenue, CoinGecko FDV) recomputed; rank 1 = lowest multiple; percentile = share of peers strictly below NEAR.

### 5.1 NEAR cash-flow coverage against the peer set
| Metric | NEAR | Peer median | Peer P25 - P75 | NEAR rank | Position |
| :--- | ---: | ---: | ---: | ---: | :--- |
| FDV / annualised fees (30-day run-rate) | 70x | 253x | 158x - 643x | 2 of 4 | inside the peer range |
| FDV / annualised revenue (30-day run-rate) | 206x | 2,411x | 1,246x - 2,865x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day fees | 87x | 229x | 153x - 832x | 2 of 4 | inside the peer range |
| FDV / trailing-365-day revenue | 470x | 2,091x | 1,096x - 3,678x | 2 of 4 | inside the peer range |

| Protocol | FDV | Fees (ann.) | Revenue (ann.) | FDV/fees | FDV/revenue | FDV/fees 1y | FDV/revenue 1y | Revenue/fees |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SOL (solana) | $53.05B | $209.5M | $22.0M | 253x | 2,411x | 229x | 2,091x | 11% |
| ETH (ethereum) | $252.65B | $244.8M | $76.1M | 1,032x | 3,319x | 1,436x | 5,264x | 31% |
| HYPE (hyperliquid) | $68.68B | $1.09B | $839.5M | 63x | 82x | 77x | 101x | 77% |
| NEAR (near_combined) | $4.78B | $68.1M | $23.3M | 70x | 206x | 87x | 470x | 34% |
| NEAR (near) | $4.78B | $1.7M | $1.2M | 2,875x | 4,108x | 4,107x | 5,863x | 70% |
| NEAR (near-intents) | $4.78B | $66.4M | $22.1M | 72x | 217x | 89x | 511x | 33% |

The model's terminal multiple is 60x; 0 of 3 peers trade at or below it on FDV/revenue.

### 5.2 Peer-multiple FDV band (relative-value cross-check, not a fair value)
| Cash flow | NEAR (ann.) | at peer P25 | at peer median | at peer P75 | Peers | Basis |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| fees | $68.1M | $10.76B | $17.23B | $43.75B | 3 | comps.near_combined.annualized_fees_usd x peer FDV / annualised fees (30-day run-rate) |
| revenue | $23.3M | $28.97B | $56.05B | $66.61B | 3 | comps.near_combined.annualized_revenue_usd x peer FDV / annualised revenue (30-day run-rate) |

relative-value cross-check, not a fair value: NEAR cash flow x the live peer multiple distribution; market FDV $4.80B.

### 5.3 Staking and security budget
- Security budget: 32,755,060 NEAR/yr of issuance (2.50%) x $3.66 = $119.9M/yr (2.51% of FDV).
- Against it: $68.1M/yr of fees (57% of the budget) and $23.3M/yr of holder revenue (19%); net dilution $96.6M/yr.
- Staked 44.4% of supply; nominal staking APR 5.63%. Basis: security budget = supply_physics.current_daily_issuance_near x 365.25 x NEAR price; fees / revenue = comps.near_combined 30-day run-rate.

### 5.4 Findings
- NEAR trades at 70x annualised fees versus a peer median of 253x (rank 2 of 4, lowest first; inside the peer range); on revenue it is 206x versus 2,411x (inside the peer range).
- 0 of 3 peers trade at or below the model's 60x terminal FDV/revenue multiple; NEAR itself trades at 206x.
- At the peer FDV/fees distribution, NEAR's $68M of annualised fees maps to $10.76B-$43.75B (median $17.23B, n = 3) against a $4.80B market FDV; a relative-value cross-check, not a fair value.
- NEAR issues $120M a year to validators and delegators (2.5% of FDV) against $68M of annualised fees and $23M of holder revenue (gas burn + Intents buyback): revenue covers 19% of the security budget.
- At 2.5% inflation stakers earn 5.63% nominal and 3.59% real including buybacks; non-stakers lose 2.04% a year to dilution net of buybacks.

Caveat: Peer 'revenue' follows each chain's own DefiLlama methodology (peers[].revenue_methodology), so revenue multiples compare different cash-flow definitions; with n = 3 peers the median is a reference point, not a distribution.

## 6. Model valuation detail

**Base case.** 10,000-path SOTP (seed 20261114): P10 / P50 / P90 FDV = $54.0M / **$248.1M** / $1.57B; implied price $0.04 / **$0.18** / $1.15 per NEAR against spot $3.66. The P50 sits 94.8% below the current FDV of $4.80B. The deterministic SOTP at the labeled inputs (the expected-volume path) is $775.4M: engines $287.3M clearinghouse + $414.9M confidential + $73.3M monetary; the Monte Carlo mean is $747.4M. Ex-monetary P50: $229.9M.

**Why the P50 is below the deterministic value.** The volume and price processes are mean-matching GBMs (Ito drift), so the labeled +30% YoY volume growth is the growth of the MEAN path and the deterministic FDV prices that path. At the measured monthly volume sigma of 0.349 the MEDIAN simulated path ends month 36 at 11.1% of the expected path ($18.4M/day vs $165.1M/day), which is what pulls the P50 FDV below the mean. The dispersion is measured from 11 monthly volume log-returns (sigma excluding the three oldest, incentive-era windows: 0.322); a thin sample, reported as such.

**Reading.** At live take rates the run-rate cash flows do not reproduce the current valuation; section 3 solves which single input would: Market FDV $4.80B is 6.2x the model's expected-path FDV $775M; holding the rest at base, the gap closes inside measured evidence only through: terminal multiple 396x (evidence 2,411x). The P90 ($1.57B) comes from volume paths, not from take-rate expansion (the public take only compresses in this model).

**What the current FDV requires (held-constant 5x5 grid, SVRN glidepath).** 6 bps net take needs >= $1.00B/day; 10 bps net take needs >= $500.0M/day; 14 bps net take needs >= $500.0M/day; 18 bps net take needs >= $250.0M/day. Live run-rate: $125.3M/day at 4.83 bps net (14.53 bps gross x capture 33.3%).

**Net-float crossover.** Today sinks cover 19.8% of measured issuance (17,715 NEAR/day vs 89,678 NEAR/day). status quo (cap flat): deterministic flow crossover none within horizon at run-rate volume, none within horizon with the +30% YoY growth assumption; Monte Carlo P(crossover within 36m) = 46.4%, P(deflationary at horizon) = 26.0%; breakeven volume V* = $670.5M/day (5.4x today). SVRN glidepath: deterministic flow crossover none within horizon at run-rate volume, none within horizon with the +30% YoY growth assumption; Monte Carlo P(crossover within 36m) = 54.7%, P(deflationary at horizon) = 32.5%; breakeven volume V* = $425.9M/day (3.4x today). The MC crossover probabilities are a dispersion artefact of the volume and price GBMs (a path crosses when holder revenue / price outruns issuance); the deterministic path (the expected-volume path) is the one to quote.

**Falsification.** Four stress scenarios (section 11) put the combined-worst deterministic FDV (median inputs, not a Monte Carlo percentile) at $104.1M (-87% vs the deterministic base $775.4M); 2 of 4 measured early-warning triggers are breached in this snapshot (breached: governance_stalemate (max_inflation_rate now 2.50% vs > 1.60%); solver_cartelization (hhi_solver now 4,876 vs > 3,500)). The on-chain inflation cap reads 2.50%; the SVRN cut is a proposal, not protocol state.

## 7. Microstructure evidence: live quote race (1Click vs Relay vs LI.FI vs Across)

Executable quotes fetched 2026-11-11T06:05:10.558Z UTC (30 ok of 36; 1Click token universe 229 assets on 39 chains). Headroom and 1Click rank are computed on DESTINATION UNITS delivered for the identical raw input (headroom = (out_1click - out_best_competitor) / out_best_competitor x 1e4, basis `dest_units`); no price oracle enters the ranking, so a venue's own USD mark of BTC cannot make it look better or worse than the BTC it actually pays out. USD friction = (in - out) / in x 1e4 with every venue in a cell valued at ONE common price (`price_basis`: oneclick_token_list_oracle); raw-unit friction is exact for USDC -> USDC. Positive headroom means 1Click paid out more after all fees.

| Corridor | Clip | Venue | Status | Out | Friction | ETA | Route |
| :--- | ---: | :--- | :--- | ---: | ---: | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | 1click | ok | 499.894565 | 2.11 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $500 | relay | ok | 499.829993 | 3.40 bps (raw) | 1 s | relay |
| ETH USDC -> SOL USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $500 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $50,000 | 1click | ok | 49,989.890515 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $50,000 | relay | ok | 49,984.979993 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $50,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> SOL USDC | $250,000 | 1click | ok | 249,949.492595 | 2.02 bps (raw) | 42 s | 1click-solver-network |
| ETH USDC -> SOL USDC | $250,000 | relay | ok | 249,924.979993 | 3.00 bps (raw) | 24 s | relay |
| ETH USDC -> SOL USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| ETH USDC -> SOL USDC | $250,000 | across | unsupported_route: ROUTE_NOT_ENABLED: Route is not enabled. | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $500 | 1click | ok | 0.006740 | 48.20 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $500 | relay | ok | 0.006764 | 11.96 bps (usd) | 359 s | relay |
| ETH USDC -> native BTC | $500 | lifi | ok | 0.006751 | 32.28 bps (usd) | 1,559 s | relaydepository |
| ETH USDC -> native BTC | $500 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $50,000 | 1click | ok | 0.675811 | 21.32 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $50,000 | relay | ok | 0.676776 | 7.08 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $50,000 | lifi | ok | 0.675084 | 32.06 bps (usd) | 1,224 s | relaydepository |
| ETH USDC -> native BTC | $50,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| ETH USDC -> native BTC | $250,000 | 1click | ok | 3.375350 | 32.26 bps (usd) | 490 s | 1click-solver-network |
| ETH USDC -> native BTC | $250,000 | relay | ok | 3.377530 | 25.83 bps (usd) | 24 s | relay |
| ETH USDC -> native BTC | $250,000 | lifi | ok | 3.374069 | 36.05 bps (usd) | 1,224 s | relaydepository |
| ETH USDC -> native BTC | $250,000 | across | unsupported_route: Across is EVM-only; no Bitcoin route | n/a | n/a | n/a |  |
| Base USDC -> Arbitrum USDC | $500 | 1click | ok | 499.921819 | 1.56 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $500 | relay | ok | 499.927500 | 1.45 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $500 | lifi | ok | 498.750000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $500 | across | ok | 499.942630 | 1.15 bps (raw) | 2 s | across |
| Base USDC -> Arbitrum USDC | $50,000 | 1click | ok | 49,989.895220 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $50,000 | relay | ok | 49,994.977506 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $50,000 | lifi | ok | 49,875.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $50,000 | across | ok | 49,994.992630 | 1.00 bps (raw) | 120 s | across |
| Base USDC -> Arbitrum USDC | $250,000 | 1click | ok | 249,949.497300 | 2.02 bps (raw) | 34 s | 1click-solver-network |
| Base USDC -> Arbitrum USDC | $250,000 | relay | ok | 249,974.977506 | 1.00 bps (raw) | 1 s | relay |
| Base USDC -> Arbitrum USDC | $250,000 | lifi | ok | 249,375.000000 | 25.00 bps (raw) | 1,080 s | polymerStandard |
| Base USDC -> Arbitrum USDC | $250,000 | across | ok | 249,974.992630 | 1.00 bps (raw) | 900 s | across |


| Corridor | Clip | Headroom | Basis | 1Click rank | Reading |
| :--- | ---: | ---: | :--- | ---: | :--- |
| ETH USDC -> SOL USDC | $500 | +1.29 bps | dest_units | 1/3 | 1Click delivers 1.29 bps more than relay |
| ETH USDC -> SOL USDC | $50,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> SOL USDC | $250,000 | +0.98 bps | dest_units | 1/3 | 1Click delivers 0.98 bps more than relay |
| ETH USDC -> native BTC | $500 | -36.28 bps | dest_units | 3/3 | 1Click trails relay by 36.28 bps |
| ETH USDC -> native BTC | $50,000 | -14.25 bps | dest_units | 2/3 | 1Click trails relay by 14.25 bps |
| ETH USDC -> native BTC | $250,000 | -6.45 bps | dest_units | 2/3 | 1Click trails relay by 6.45 bps |
| Base USDC -> Arbitrum USDC | $500 | -0.42 bps | dest_units | 3/4 | 1Click trails across by 0.42 bps |
| Base USDC -> Arbitrum USDC | $50,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |
| Base USDC -> Arbitrum USDC | $250,000 | -1.02 bps | dest_units | 3/4 | 1Click trails across by 1.02 bps |


- cross_vm: median headroom +0.98 bps over 3 comparable cells
- native_btc: median headroom -14.25 bps over 3 comparable cells
- evm_l2: median headroom -1.02 bps over 3 comparable cells
- competitive fee ceiling (median over cross-VM cells of the BEST competitor's friction, n = 3; per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding): 3.00 bps. The lowest-friction venue polled is the binding ceiling; a higher venue fee is not.

- Where 1Click loses (destination units): eth_usdc_btc at $500 trails relay by 36.28 bps; eth_usdc_btc at $50,000 trails relay by 14.25 bps; eth_usdc_btc at $250,000 trails relay by 6.45 bps; base_usdc_arb_usdc at $500 trails across by 0.42 bps; base_usdc_arb_usdc at $50,000 trails across by 1.02 bps; base_usdc_arb_usdc at $250,000 trails across by 1.02 bps.
- Oracle caveat: on eth_usdc_sol_usdc at $500, eth_usdc_sol_usdc at $50,000, eth_usdc_sol_usdc at $250,000, eth_usdc_btc at $50,000, eth_usdc_btc at $250,000, base_usdc_arb_usdc at $500, base_usdc_arb_usdc at $50,000, base_usdc_arb_usdc at $250,000 the venues' own USD marks of the destination asset differ from the common price by more than the headroom itself; a USD-leg comparison there would have been decided by oracles, which is why the ranking uses units.
- Structurally unsupported routes: across on eth_usdc_btc (declared), across on eth_usdc_sol_usdc (ROUTE_NOT_ENABLED).
- Collector summary: cross_vm (ETH USDC -> SOL USDC): $500: 1Click delivers 1.29 bps more than relay (rank 1/3, destination units); $50,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); $250,000: 1Click delivers 0.98 bps more than relay (rank 1/3, destination units); unsupported: across (ROUTE_NOT_ENABLED). native_btc (ETH USDC -> native BTC): $500: 1Click trails 36.28 bps behind relay (rank 3/3, destination units); $50,000: 1Click trails 14.25 bps behind relay (rank 2/3, destination units); $250,000: 1Click trails 6.45 bps behind relay (rank 2/3, destination units); unsupported: across (Across is EVM-only; no Bitcoin route). evm_l2 (Base USDC -> Arbitrum USDC): $500: 1Click trails 0.42 bps behind across (rank 3/4, destination units); $50,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units); $250,000: 1Click trails 1.02 bps behind across (rank 3/4, destination units).

## 8. Concentration and agents on intents.near (NearBlocks receipts)

- Two populations are measured and they answer different questions. (a) DEPOSIT / CALLER concentration: HHI over external predecessors of intents.near receipts (system refunds and intents.near self-receipts excluded) = **2,219** (bootstrap 90% CI 1,403-3,265) (N_eff = 4.51); over all predecessors 3,664; ex-AI-agent 1,172 (N_eff 8.53). These predecessors are bridge token-contract deposit callbacks and direct callers; execute_intents fills are relayer self-receipts (predecessor intents.near) and never enter this HHI, so it cannot detect solver concentration.
- (b) SOLVER concentration: HHI over solver fill participations decoded from execute_intents NEP-413 signer payloads = **4,876** (bootstrap 90% CI 3,878-5,322) (N_eff 2.05) across 77 fill participations in 74 fills (5 atomic token_diff fills, 69 solver-to-settlement-hub legs), 5 distinct solvers; 457 execute_intents receipts decoded, 0 unresolved; the solver sample spans 29,003 s. This is the population the solver_cartelization trigger reads; trigger status: breached.
- AI-agent share of external receipts 42.9% is a NAME-PATTERN classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic, not a verified agent. Bridge / token-contract share 42.9%; 12 unique external callers in 28 external receipts.
- Sample: 185 unique receipts over 8 NearBlocks pages, blocks 224,025,945-224,026,030, a 50 s window; lifetime receipts on intents.near 156,827,534. A window this short is a point sample, not a market-share estimate; both HHIs move by hundreds of points between runs.
- Method mix: TRANSFER 86, execute_intents 57, ft_on_transfer 12, ft_resolve_withdraw 10, ft_transfer 5, ft_transfer_call 5, do_storage_deposit 3, near_withdraw 3, storage_deposit 2, mt_resolve_withdraw 1.

### 8.1 Deposit / caller concentration (external predecessors)
| Caller | Class | Receipts | Share | Example tx |
| :--- | :--- | ---: | ---: | :--- |
| escrow.ai.near | AI agent | 12 | 42.9% | [9WaVzviHUdzL...](https://nearblocks.io/txns/9WaVzviHUdzLpQUrGRzZYWKPhNsKxZSs6Jeo5sWWi9eP) |
| sol.omft.near | bridge / token contract | 3 | 10.7% | [CpHZ92QRCMqe...](https://nearblocks.io/txns/CpHZ92QRCMqeXUvVubM71UPSV5EJsDUNbgdNe3MizNVB) |
| wrap.near | named account | 3 | 10.7% | [7oxvtKMpZXvk...](https://nearblocks.io/txns/7oxvtKMpZXvky3EAMEJNQSqEVdWFdrgpfcWvdxPMpj4R) |
| eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near | bridge / token contract | 2 | 7.1% | [BVPqoutKUawx...](https://nearblocks.io/txns/BVPqoutKUawxe7SpChD3DhBJr9MLPwGpykDyxnfnroFu) |
| 17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1 | bridge / token contract | 1 | 3.6% | [6GMACASA2pN5...](https://nearblocks.io/txns/6GMACASA2pN57Y4PrtPPq5CKN7GMFMxcEX2ypEVvsTxo) |
| 7f4aacbef51f39f90338b106acc1522d6304dd0a9515fe14185f3518be3bb75a | implicit account | 1 | 3.6% | [6GMACASA2pN5...](https://nearblocks.io/txns/6GMACASA2pN57Y4PrtPPq5CKN7GMFMxcEX2ypEVvsTxo) |
| base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near | bridge / token contract | 1 | 3.6% | [BLC9E9DAtkLr...](https://nearblocks.io/txns/BLC9E9DAtkLrr7a6pLsCe9Z1YAPJjPTJGHghrisAsjqA) |
| bnb-0x55d398326f99059ff775485246999027b3197955.omdep.near | bridge / token contract | 1 | 3.6% | [3h9cx4RC5z4U...](https://nearblocks.io/txns/3h9cx4RC5z4UH4Q2QkRJzNwZv9nWJd8aw2Hd8j1VERL2) |
| eth.omft.near | bridge / token contract | 1 | 3.6% | [AZ6xiTWGCj9V...](https://nearblocks.io/txns/AZ6xiTWGCj9VoMs1dxfm2TecWiUQYxXFurbUqFCaEY8E) |
| sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near | bridge / token contract | 1 | 3.6% | [9YMx9icAv3cV...](https://nearblocks.io/txns/9YMx9icAv3cVcSbnhvsPzoHffF9QQUFXcz8Hp9bvgwho) |
| sol-c800a4bd850783ccb82c2b2c7e84175443606352.omft.near | bridge / token contract | 1 | 3.6% | [5M2MJkyV6rCs...](https://nearblocks.io/txns/5M2MJkyV6rCsMcuwYP6ai2yFYHjisFDzwwmpGADHTF6e) |
| zec.omft.near | bridge / token contract | 1 | 3.6% | [3dZy1v6njqek...](https://nearblocks.io/txns/3dZy1v6njqek7jhoWrWEKKxNQXCrES2DB5ogE5h29fck) |

### 8.2 Solver concentration (execute_intents signers)
| Solver account | Fill participations | Share | Example tx |
| :--- | ---: | ---: | :--- |
| solver-priv-liq.near | 47 | 61.0% | [GMa66poznF2i...](https://nearblocks.io/txns/GMa66poznF2i7ESWGB7Khik6ymJzbUgHhAyqFTfbiRNa) |
| solver-multichain-asset.near | 26 | 33.8% | [GMa66poznF2i...](https://nearblocks.io/txns/GMa66poznF2i7ESWGB7Khik6ymJzbUgHhAyqFTfbiRNa) |
| brlabs-solver.near | 2 | 2.6% | [DsRrr51gY3Ai...](https://nearblocks.io/txns/DsRrr51gY3AiEhZ67vJyYGmYQQKQsqAnN9WaTZNgT3Sq) |
| bestswap.near | 1 | 1.3% | [iBdb1a65qoKQ...](https://nearblocks.io/txns/iBdb1a65qoKQdHT6S7VZHAbYFCkrgc4UcjQKuHLN7BK) |
| solver-earn.near | 1 | 1.3% | [YxB7YE3LK7Yo...](https://nearblocks.io/txns/YxB7YE3LK7YoN5NYZvJC2zfnGRE1v8X3j9iLy4iAfcg) |

Attribution: fill participation = (a) the solver side of an atomic execute_intents fill (>= 2 token_diff signers; solver = pure token_diff signer when the counterparty bundles a withdrawal, else a signer whose name matches (*solver*, *-liq*, market maker) or that the structure rule identified elsewhere in the sample, else the named account facing an implicit 1Click deposit address), or (b) a transfer intent from a solver to the settlement hub (see settlement_hub.rule); HHI over participations per solver account; transfers that are not solver-to-hub legs are inventory or user moves, not fills. hhi_solver_ci90 is a bias-corrected bootstrap (bootstrap_method): a block bootstrap by NearBlocks page when the sample is stratified in time (bootstrap_resampling = block_by_page), else over sampled units

## 9. Supply physics

### 9.1 Issuance: measured vs nominal
- Measured: 25,705.59 NEAR minted at epoch start 224,005,937 (previous jump 25,760.09 NEAR at 223,962,737); epoch wall time 6.879 h = 1,274.2 epochs/yr; implied annual issuance **32,755,060 NEAR** = 2.4977% of supply.
- Nominal: max_inflation_rate 2.50% x total supply 1,311,395,122 NEAR = 32,784,878 NEAR/yr; measured minus nominal -29,818 NEAR/yr (-0.09%). Daily: measured 89,678 NEAR vs nominal 89,760 NEAR; treasury share 0.0% (validators receive the rest).
- Within-epoch supply drift (net gas burn) -243.81 NEAR/epoch; measured block time 0.573 s. Epochs/yr uses 365.25 x 24 h; nearcore's reward scaling uses a 365-day year, a 0.07% definitional difference.

### 9.2 Daily sinks (NEAR/day, live)
| Sink | NEAR/day | Source | Basis |
| :--- | ---: | :--- | :--- |
| Buyback (holders revenue / price) | 16,532.2 NEAR | measured | $125.3M/day x 14.53 bps gross x alpha 33.3% / $3.66 |
| L1 gas burn | 850.6 NEAR | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| NEP state-lock growth | 332.3 NEAR | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| Total sinks | 17,715.1 NEAR |  | coverage 19.8% of measured issuance; net float 71,963 NEAR/day |


### 9.3 Breakeven daily volume V* (dS <= 0 at today's price, gross take and capture ratio)
| Regime (terminal rate) | V* at live take | vs today | V* at competitive ceiling |
| :--- | ---: | ---: | ---: |
| status quo (cap flat) | $670.5M | 5.4x | $3.24B |
| SVRN glidepath | $425.9M | 3.4x | $2.06B |

Formula: V* = max(0, I - G - L) x P / ((tau_gross / 1e4) x alpha), with I at the regime's terminal rate x issuance realization factor.

### 9.4 36-month trajectories (constant 30.4375-day months; sinks held at measured run-rate except volume growth where stated)
| Regime | Volume path | Issuance/day m1 | Issuance/day m36 | Gross issuance 36m | Sinks 36m | Net float 36m | Flow crossover | Cumulative crossover |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | :--- | :--- |
| status quo (cap flat) | run-rate volume | 89,678 NEAR | 96,448 NEAR | 101,930,410 NEAR | 19,411,341 NEAR | 82,519,069 NEAR | none within horizon | none within horizon |
| status quo (cap flat) | +30% YoY volume | 89,678 NEAR | 96,448 NEAR | 101,930,410 NEAR | 28,545,429 NEAR | 73,384,981 NEAR | none within horizon | none within horizon |
| SVRN glidepath | run-rate volume | 89,678 NEAR | 60,697 NEAR | 77,304,258 NEAR | 19,411,341 NEAR | 57,892,917 NEAR | none within horizon | none within horizon |
| SVRN glidepath | +30% YoY volume | 89,678 NEAR | 60,697 NEAR | 77,304,258 NEAR | 28,545,429 NEAR | 48,758,829 NEAR | none within horizon | none within horizon |


### 9.5 NEP storage-staking sinks (view_account at the snapshot block; growth from archival state)
| Account | Contract | storage_usage bytes | Locked | Growth B/day | Growth NEAR/day | Window |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: |
| intents.near | yes | 13,566,758,299 | 135,667.6 NEAR | 29,638,482 | 296.38 NEAR | 30.9 d |
| aurora | yes | 14,380,937,721 | 143,809.4 NEAR | 3,592,688 | 35.93 NEAR | 30.9 d |
| wrap.near | yes | 168,832,121 | 1,688.3 NEAR | n/a | n/a | n/a |
| v1.signer | yes | 1,164,178 | 11.6 NEAR | n/a | n/a | n/a |
| escrow.ai.near | no | 428 | 0.0 NEAR | n/a | n/a | n/a |
| treasury.near | yes | 357,895 | 3.6 NEAR | n/a | n/a | n/a |
| meme-cooking.near | yes | 5,972,881 | 59.7 NEAR | n/a | n/a | n/a |
| v2.ref-finance.near | yes | 111,271,948 | 1,112.7 NEAR | n/a | n/a | n/a |

- Total state-locked across 8 tracked contracts: **282,353 NEAR** at 0.01 NEAR/KB (storage_amount_per_byte 10,000,000,000,000,000,000 yocto). Measured lock growth 332.3 NEAR/day over intents.near, aurora (archival available).

### 9.6 Staking yield by regime (nominal = i x (1 - treasury) / staked ratio; real = nominal - i; accrual = buyback x 365.25 / supply)
| Regime | Inflation | Nominal APR | Real APR | Buyback accrual | Real APR + accrual | Non-staker real |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| status quo (cap flat) | 2.50% | 5.63% | 3.13% | 0.460% | 3.59% | -2.04% |
| SVRN glidepath | 1.60% | 3.60% | 2.00% | 0.460% | 2.46% | -1.14% |

Live: 351 validators, 582,122,256 NEAR staked = 44.39% of supply.

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
Sign-request rate not measured this run (30d rate: one of the two strata (last 7 days, days 7-30) returned no window; trend: fewer than 5 00:00 UTC windows returned). NearBlocks counts 26,396,207 cumulative receipts at v1.signer.

## 10. Sum-of-the-parts valuation and peer comparables

### 10.1 Engines (percentiles over paths, USD; discounted to today)
| Engine | P10 | P25 | P50 | P75 | P90 | Assumption-heavy |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| clearinghouse | $9.6M | $21.8M | $59.2M | $178.3M | $490.7M | no |
| confidential | $14.2M | $30.9M | $86.1M | $275.4M | $810.0M | yes |
| monetary | $804,419 | $1.8M | $5.5M | $21.1M | $79.2M | yes |

| Total | P10 | P25 | P50 | P75 | P90 |
| :--- | ---: | ---: | ---: | ---: | ---: |
| FDV (all engines) | $54.0M | $105.3M | $248.1M | $621.7M | $1.57B |
| FDV ex-monetary | $49.8M | $97.6M | $229.9M | $569.9M | $1.43B |
| Implied price / NEAR | $0.04 | $0.08 | $0.18 | $0.45 | $1.15 |

Note: path percentiles are not additive. Each engine's P50 is taken over its own paths, so the three engine P50s do not sum to the total P50. The additive decomposition of the one path whose total is the sample median is: clearinghouse $11.1M (4%) + confidential $234.6M (95%) + monetary $2.3M (1%) = $248.1M.

- PV of H months of public holder revenue (V_pub x tau_pub x alpha) at the discount rate, plus year-3 annualized revenue x peer-median FDV/revenue multiple, discounted; tau_pub reverts to the benchmark floor.
- Same construction on confidential volume at the assumed confidential take; terminal multiple x confidential_multiple_haircut because nearstats flags confidential TVL as unverified. NOT MEASURED this run: the nearstats public/confidential split failed the plausibility guard; the starting confidential share is the registry assumption confidential_share (40%), so this engine values an assumed volume, not a measured one.
- PV of L1 gas burn (grown with public volume) at the peer multiple plus the discounted market value of newly state-locked NEAR (sum state_lock_t x P_t): a demand-flow proxy, not a cash flow.

### 10.2 Calibration (what the engines were fed)
| Parameter | Value | Source / basis |
| :--- | :--- | :--- |
| Public take t=0 (gross) | 10.88 bps | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d |
| Blended gross take / net take | 14.53 bps / 4.83 bps | DefiLlama near-intents fees / volume; net = gross x alpha |
| Capture ratio alpha | 33.26% | measured:defillama near-intents dailyHoldersRevenue / fees |
| Confidential take t=0 | 20 bps | assumption: registry confidential_take_bps (1Click confidential quotes need partner authentication) |
| Public take floor | 0.98 bps | derived; cross-VM headroom +0.98 bps, competitor ceiling 3.00 bps |
| Compression lambda (public / confidential) | 0.030 / 0.010 per month | geometric reversion to the floor |
| Volume growth (public / confidential, monthly) | 2.21% / 2.21% | confidential share 40.0% -> 40% target (start share ASSUMED: registry confidential_share; nearstats split failed the plausibility guard) |
| Sigma: price (annual) / volume (monthly) | 1.026 / 0.349 | measured: monthly log-return sigma of 30-day volume aggregates; confidential sigma x 1.00 |
| Terminal multiple (FDV / annual holder revenue) | 60.0x (raw 2,410.6x) | source derived: peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; clipped to registry guardrails |
| Discount rate | 25% | assumption |
| Supply at horizon (glidepath) | 1,369,288,038 NEAR | fdv / (S_0 + gross issuance - buybacks - gas burn - state lock at H, svrn_glidepath trajectory) |
| Current FDV | $4.80B | spot price x on-chain total_supply at the snapshot block; CoinGecko FDV via nearstats $4.79B (-0.26% gap, struck at a different instant; cross-check only) |
| GBM convention | mean-matching (Ito) | mean-matching (Ito): log V_t = log V_0 + t (ln(1+g) - sigma^2/2) + sigma W_t, so E[V_t] = V_0 (1+g)^t; public_volume_growth_yoy is the EXPECTED (mean) growth and equals the deterministic path; the MEDIAN simulated path is lower by exp(-sigma^2 t/2) (see volume_terminal_median_usd_day vs volume_terminal_mean_usd_day); the price GBM uses the same convention (zero drift => E[P_t] = P_0) |
| Terminal public volume, month H | mean $165.1M/day; median $18.4M/day | start $75.2M/day; MC sample mean $145.5M, median $17.8M; the labeled YoY growth is the growth of the MEAN path |


### 10.3 Peer comparables (DefiLlama trailing 30d run-rates, CoinGecko valuations)
| Protocol | Fees 30d | Revenue 30d | FDV | FDV/fees | FDV/revenue | Revenue methodology (live text) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| SOL (solana) | $17.2M | $1.8M | $53.05B | 253.2x | 2,410.6x | Transaction base fees paid by users |
| ETH (ethereum) | $20.1M | $6.3M | $252.65B | 1,032.1x | 3,319.1x | Amount of ETH burned — base fees plus blob fees (both are permanently burned, accruing to no proposer) |
| HYPE (hyperliquid) | $89.6M | $69.0M | $68.68B | 63.0x | 81.8x | Parent aggregates child protocols. Hyperliquid Perps: 99% of fees go to Assistance Fund for buying HYPE tokens |
| NEAR (near) | $136,746 | $95,723 | $4.78B | 2,875.3x | 4,107.6x | 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract developers |
| NEAR (near-intents) | $5.5M | $1.8M | $4.78B | 72.0x | 216.6x | NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.ne |
| NEAR (near_combined) | $5.6M | $1.9M | $4.78B | 70.3x | 205.8x | near: 70% of every gas fee is permanently burned, reducing NEAR supply. The other 30% is paid to contract deve |

- Median ex-NEAR FDV / annualized revenue 2,410.6x (n = 3); FDV / annualized fees 253.2x (n = 3). annualized_* = DefiLlama total30d x 365/30; *_1y = DefiLlama total1y (trailing 365d sum)
- `revenue` means different things per protocol (ETH/SOL burn, HYPE buybacks, NEAR Intents sweeps to revenue wallets); the live methodology text is carried in the table so the multiple is read with its definition.

### 10.4 Sensitivity: deterministic FDV at held-constant daily volume x blended NET take (SVRN glidepath; * = net-deflationary)
| Net take \ Volume/day | $100.0M | $250.0M | $500.0M | $1.00B | $1.50B |
| :--- | ---: | ---: | ---: | ---: | ---: |
| 2 bps | $251.7M | $571.6M | $1.10B | $2.17B | $3.24B* |
| 6 bps | $678.3M | $1.64B | $3.24B* | $6.44B* | $9.64B* |
| 10 bps | $1.10B | $2.70B* | $5.37B* | $10.70B* | $16.04B* |
| 14 bps | $1.53B | $3.77B* | $7.50B* | $14.97B* | $22.44B* |
| 18 bps | $1.96B | $4.84B* | $9.64B* | $19.24B* | $28.83B* |

Current FDV $4.80B; confidential share used in the split 40.0%. Cells hold volume and take constant for the horizon with alpha folded into the net take; they are deterministic run-rate marks, not forecasts and not Monte Carlo percentiles (the snapshot field is named fdv_p50 for compatibility).

### 10.5 Out-of-sample backtest of the volume engine
At each of 20 monthly origins from 2025-03-20 to 2026-10-11 the volume GBM was re-calibrated on data up to the origin only (trailing 30-day volume, sigma from the trailing 365 days, drift = public_volume_growth_yoy 30%) and its P10-P90 band for 30-day volume was compared with what happened (defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json), 2024-12-10 to 2026-11-10). The test of 80% coverage fails at 1m, 3m, 6m (exact two-sided binomial test of P10-P90 coverage vs 80%, p >= 0.10). At 1 month the median realized volume is 1.43x the forecast median: the model under-predicts. Split at the middle origin (2026-01-14), coverage before: 1m 40% (n = 10), 3m 20% (n = 10), 6m 30% (n = 10); from it: 1m 90% (n = 10), 3m 86% (n = 7), 6m 100% (n = 4). 21 of the 23 misses come from origins before the split; 23 of 23 are realized volume above P90. With the drift replaced by the trailing mean log return (no registry input) coverage is 1m 65%, 3m 59%, 6m 29%. Not backtested: fee take rate (public and confidential) and its compression toward the floor; holder capture ratio alpha; confidential share of volume and its drift to the target share; terminal FDV/revenue multiple and discount rate; NEAR price and supply paths. 3- and 6-month forecasts from monthly origins overlap, so their errors are correlated and the binomial interval overstates the precision.

| Horizon | n | P10-P90 coverage [90% Wilson] | Binomial p vs 80% | Below P10 / above P90 | Median realized / P50 | PIT histogram (5 bins) |
| :--- | ---: | ---: | ---: | ---: | ---: | :--- |
| 1 month | 20 | 65% [47%-80%] | 0.10 | 0 / 7 | 1.43x | 1 3 3 3 10 |
| 3 months | 17 | 47% [29%-66%] | 0.00 | 0 / 9 | 2.12x | 0 2 0 6 9 |
| 6 months | 14 | 50% [30%-70%] | 0.01 | 0 / 7 | 4.79x | 0 1 2 1 10 |


## 11. Bear case and early-warning triggers

Value basis: deterministic at median inputs; not a Monte Carlo percentile. Base deterministic FDV (median inputs) $775.4M, implied price $0.57; the Monte Carlo P50 of section 10 is a different statistic and is not what the drawdowns below are measured against. drawdown_pct = fdv_scenario / fdv_base - 1 (signed fraction) on the deterministic (median-input) FDV; price_drawdown_pct likewise on implied price; mc_drawdown_pct on the Monte Carlo median when computed

| Scenario | Deterministic FDV (median inputs) | FDV drawdown | Implied price | Price drawdown | Flow crossover |
| :--- | ---: | ---: | ---: | ---: | :--- |
| fee_race_to_zero | $175.9M | -77.3% | $0.13 | -77.3% | none within horizon |
| governance_stalemate | $775.4M | +0.0% | $0.56 | -1.8% | none within horizon |
| post_incentive_decay | $312.7M | -59.7% | $0.23 | -59.7% | none within horizon |
| solver_cartelization | $551.7M | -28.9% | $0.40 | -28.9% | none within horizon |
| combined worst | $104.1M | -86.6% | $0.07 | -86.8% | none within horizon |


### 11.1 Early-warning triggers (check weekly; 'not measured' = the live metric was null or too thin this run; 'inconclusive' = measured but not gradable; neither is a clear)
| Scenario | Metric | Now | Trigger | Status | Monitor |
| :--- | :--- | :--- | :--- | :--- | :--- |
| fee_race_to_zero | net_take_bps_30d | 4.83 bps | < 3.00 bps | not breached | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue (sum(dailyRevenue chart) / sum(summary/dexs/near-intents chart) x 1e4 over the same 30 complete UTC days). |
| governance_stalemate | max_inflation_rate | 2.50% | > 1.60% | **BREACHED** | https://free.rpc.fastnear.com (EXPERIMENTAL_protocol_config.max_inflation_rate (num/den)). Note: breached while the on-chain cap exceeds the SVRN target: the cut has not been enacted |
| post_incentive_decay | volume_30d_vs_record_30d | -22.3% | <= -40.0% | not breached | https://nearstats.org/api/near/summary (intents.totals.volume30dUsd / intents.totalsBreakdown.records.max30dUsd - 1). |
| solver_cartelization | hhi_solver | 4,876 | > 3,500 | **BREACHED** | https://api.nearblocks.io/v1/account/intents.near/txns?method=execute_intents&per_page=50 (HHI over solver fill participations decoded from execute_intents args.signed[].payload.message (NEP-413 signer_id, token_diff legs); secondary: headroom_by_archetype_bps.cross_vm (destination units)); secondary headroom_cross_vm_bps +0.98 bps < 0 bps (not breached). Note: sample: 77 solver fill participations over 29,003 s; HHI_solver 4,876, bootstrap 90% CI [3,878, 5,322] (CI lower bound 3,878 > 3,500: breached); deposit-source HHI over external predecessors (bridge callbacks, direct callers; not solvers) = 2,219 |


### 11.2 Scenario narratives
**Aggregator bypass: public take races to 1 pip.** Third-party frontends route around near.com and the public gross take collapses from 10.9 bps to 0.01 bps (the bare intents.near contract fee); confidential execution reprices from 20 bps to 5 bps. Capture ratio alpha is held at 33%, so the hit is price, not allocation. Deterministic (median-input) FDV -77.3% to $175.9M; implied price $0.13. Evidence against it: live cross-VM headroom is +1.0 bps, so a bypassing frontend must first give up that execution edge. Trigger: DefiLlama 30d net take (gross x alpha) below 3.0 bps (now 4.8 bps).

**Governance stalemate: 2.5% issuance forever.** Validators never enact the SVRN cut: max_inflation_rate stays at 2.50% for the full horizon instead of gliding to 1.60%. Protocol cash flows do not change, so FDV moves +0.0%; the damage is dilution: 24,626,153 more NEAR outstanding at the horizon and a per-token value of $0.56 (-1.8% vs base). Net-float crossover: none within horizon (base: none within horizon). This scenario is live today: the on-chain cap reads 2.50% and no cut has been enacted.

**Post-incentive volume decay (NEAR@3.33 unwind).** Mercenary liquidity from the NEAR@3.33 incentive program unwinds: public daily volume $75.2M -> $30.1M (-60%), confidential $50.1M -> $15.0M (-70%) and confidential TVL x0.3 (nearstats flags that TVL unverified). Take rates are unchanged, so revenue falls with volume and the deterministic (median-input) FDV -59.7% to $312.7M; implied price $0.23. Current 30d volume $3.76B is 78% of the 30d record $4.84B; the trigger fires at -40%.

**Solver cartelization: HHI_solver > 3,500, 1Click loses the spread.** Two market makers take most fills (HHI_solver > 3,500) and spreads widen until Relay/LI.FI deliver 2 bps better net execution on cross-VM (headroom -2 bps). Keeping flow costs the same 2 bps of take (10.9 bps -> 8.9 bps) while compression runs at 0.15/month. Deterministic (median-input) FDV -28.9% to $551.7M; implied price $0.40. Live: HHI over solver fill participations 4,876 (2.1 effective solvers across 77 fill participations), bootstrap 90% CI [3,878, 5,322]; deposit-source HHI over external predecessors 2,219 (not a solver measure); cross-VM headroom +1.0 bps; trigger at HHI_solver > 3,500 or headroom < 0.

### 11.3 Falsification summary
fee_race_to_zero: public gross take at 0.01 bps and confidential at 5 bps puts the deterministic FDV at $175.9M (-77.3%); watch DefiLlama near-intents 30d net take weekly, trigger < 3.0 bps, now 4.8 bps (not breached). governance_stalemate: no SVRN cut (cap 2.50% for 36 months) leaves the deterministic FDV at $775.4M (+0.0%) but dilutes per-token value to $0.56 (-1.8%) with crossover none within horizon; watch max_inflation_rate in EXPERIMENTAL_protocol_config, trigger > 1.60%, now 2.50% (BREACHED). post_incentive_decay: public volume -60% and confidential -70% puts the deterministic FDV at $312.7M (-59.7%); watch nearstats 30d volume against its 30d record weekly, trigger <= -40%, now -22.3% (not breached). solver_cartelization: HHI_solver > 3,500 with cross-VM headroom at -2 bps puts the deterministic FDV at $551.7M (-28.9%); watch the execute_intents solver HHI (now 4,876) and the live quote-race headroom (now +1.0 bps) weekly (BREACHED). All four at once: deterministic FDV $104.1M (-86.6% vs base $775.4M); 2 of 4 measured triggers currently breached, and the thesis is falsified if any trigger holds for 30 consecutive days.

## 12. Evidence scorecard

| Claim | Status | Value | Source | Confidence | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| NEP storage staking is a measured on-chain supply sink (1 NEAR per 100 KB) | **VERIFIED_ON_CHAIN** | intents.near storage_usage 13,566,758,299 bytes = 135,668 NEAR locked; 282,353 NEAR across 8 tracked contracts | near_rpc/view_account:intents.near sha256 cfa9d6277912... @ block 224,026,014; storage_amount_per_byte from EXPERIMENTAL_protocol_config | high | growth 29,638,482 B/day = 296.4 NEAR/day over 30.9 d (archival); a 0.01 NEAR/KB lock is released if state is deleted, so it is a sink while state grows |
| Realized issuance is measured from epoch-boundary supply jumps, not assumed from the 2.5% cap | **VERIFIED_ON_CHAIN** | 25,705.59 NEAR minted at epoch start 224,005,937 x 1,274.2 epochs/yr = 32,755,060 NEAR/yr (2.4977%), -0.09% vs nominal 32,784,878 | near_rpc/block:224005937 sha256 e384eae4dc1f... and its predecessor by prev_hash; previous epoch start 223962737 | high | second independent jump 25,760.09 NEAR; within-epoch drift -243.81 NEAR/epoch is the net gas burn |
| Cross-VM execution headroom: 1Click out-delivers Relay/LI.FI net of fees on ETH USDC -> SOL USDC | **VERIFIED_LIVE_API** | median headroom +0.98 bps over 3 comparable cells (dest_units); competitor ceiling 3.00 bps | oneclick/relay/lifi/across quote records 2026-11-11T06:05:10.558Z | medium | $500: +1.29 bps vs relay (rank 1/3); $50,000: +0.98 bps vs relay (rank 1/3); $250,000: +0.98 bps vs relay (rank 1/3); no 1Click capacity failures |
| Native BTC corridor: 1Click delivers more BTC per USDC than LI.FI/Relay on ETH USDC -> native BTC | **NOT_SUPPORTED** | 1Click delivers LESS BTC per USDC than the best competitor (relay): median headroom -14.25 bps over 3 cells (dest_units); the claim is not supported by this run | oneclick/lifi/relay quote records 2026-11-11T06:05:10.558Z | medium | clip-dependent: $500: -36.28 bps vs relay (rank 3/3); $50,000: -14.25 bps vs relay (rank 2/3); $250,000: -6.45 bps vs relay (rank 2/3); LI.FI's best BTC route is often NEAR Intents itself (tool `near`); venue USD marks of BTC differ by tens of bps and are not used |
| EVM-L2 stablecoin routing is commoditized: Across/Relay match or beat 1Click on Base USDC -> Arbitrum USDC (honest negative) | **VERIFIED_LIVE_API** | median headroom -1.02 bps over 3 cells (dest_units; 1Click trails) | oneclick/across/relay/lifi quote records 2026-11-11T06:05:10.558Z | medium | $500: -0.42 bps vs across (rank 3/4); $50,000: -1.02 bps vs across (rank 3/4); $250,000: -1.02 bps vs across (rank 3/4); the moat, where it exists, is corridor-specific (cross-VM, native assets), not EVM-L2 stablecoins |
| Deposit/caller concentration on intents.near is measurable and AI-agent-labeled flow is material | **DERIVED** | deposit/caller HHI_external 2,219 [90% CI 1,403-3,265] (N_eff 4.51), ex-AI-agent 1,172; AI-agent share 42.9% (>= 10% materiality line), bridge share 42.9% | nearblocks/txns:intents.near:p1 sha256 910ee34f755c... ... p8 | low | 185 unique receipts over 50 s; a point sample of the live receipt stream, not a market-share estimate. AI-agent is a name-pattern classification (*.ai.near, *.agent.near); escrow.ai.near has no deployed contract, so the label is a heuristic. This HHI is over deposit sources (bridge callbacks, direct callers), not solvers |
| Solver concentration on intents.near is measured from execute_intents fills, not inferred from deposit callers | **VERIFIED_LIVE_API** | HHI_solver 4,876 [90% CI 3,878-5,322] (N_eff 2.05) over 77 fill participations in 74 fills (5 atomic token_diff fills, 69 hub-settled legs), 5 distinct solvers; CI entirely above the 3,500 cartel threshold | nearblocks/txns:intents.near:p1 sha256 910ee34f755c... ... p8 + 8 method-filtered execute_intents page(s); args.signed[].payload.message (NEP-413 signer_id) | medium | 457 execute_intents receipts decoded; settlement hub 51e8f94d77b5... (152 counterparties) routes most swaps via transfer legs; see intents_forensics.solver_concentration.method. The CI is within-sample (one window of minutes), so it understates long-run uncertainty |
| Confidential (dark-pool) execution is a material share of 30d NEAR Intents volume | **ASSUMPTION** | NOT MEASURED this run: nearstats reported 0.00% (implausible); the model uses the registry assumption confidential_share = 40% | nearstats/summary sha256 b60bb94e67bb... intents.totalsBreakdown (basis public+confidential) | none | split rejected by the plausibility guard (share_below_floor: reported 0.0000% < 1%; tvl_without_volume: confidential TVL $141.26M but all-time confidential volume $0.32 of $38.26B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'); raw fields in intents_forensics.volume.split_reported. Engine 2 rests on an assumption this run |
| Confidential TVL backs the dark-pool engine (Engine 2) | **VERIFIED_ON_CHAIN** | $141.3M TVL read on-chain from the Confidential Intents treasury in intents.near (NEAR-reported via nearstats: $142.6M) | near_rpc/confidential:balances:head sha256 1ec57d1e2dd7... intents.near mt_batch_balance_of (treasury) | high | Engine 2 is flagged assumption_heavy and its terminal multiple carries the confidential_multiple_haircut (0.7); the confidential take (20 bps) is an assumption |
| Buyback capture alpha = holders revenue / gross fees is measured, so V x tau x alpha / P is a live sink | **DERIVED** | alpha 33.3%; gross take 14.53 bps, net take 4.83 bps; buyback sink 16,532 NEAR/day = 19.8% coverage incl. burn and lock | defillama/fees:near-intents:dailyHoldersRevenue sha256 ce48261c4cc3... / defillama/fees:near-intents sha256 f731c22bd380... | medium | DefiLlama revenue methodology: NEAR's net captured revenue, measured as NEAR/wNEAR swept into its revenue wallets (reconciles with revenue.near.org and the on-chain buyback). Split by destination wallet into front-end affiliate revenue and Other. Transfers between those wallets are excluded. |
| Chain Signatures (v1.signer) is a growing second usage engine beyond Intents | **VERIFIED_LIVE_API** | usage only: 26,396,207 cumulative v1.signer receipts; growth not measured this run | nearblocks/txns:v1.signer:count | low | the sampled rate/trend failed this run; the level is counted, the growth claim is not supported |
| The volume engine (GBM with measured sigma) is calibrated out of sample: P10-P90 covers ~80% of realized 30-day volume | **NOT_SUPPORTED** | 1m 13/20 = 65% inside P10-P90 (binomial p 0.10); 3m 8/17 = 47% inside P10-P90 (binomial p 0.00); 6m 7/14 = 50% inside P10-P90 (binomial p 0.01); 1m median realized / forecast median 1.43x (under-prediction); 1m coverage 40% for origins before 2026-01-14, 90% from it; 20 monthly origins 2025-03-20 to 2026-10-11 | defillama:dexs/near-intents totalDataChart (raw/defillama__dexs_near-intents.json) sha256 1e165a2b58fa... | low | Tests the volume distribution only; the take rate, holder capture, confidential share, multiple and discount rate are not backtested. 3m and 6m forecasts from monthly origins overlap, so their effective sample is smaller than n. |


## 13. Assumptions register

### 13.1 Labeled assumptions (slider inputs; never presented as measured)
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


### 13.2 Measured and derived model inputs (point values with their source)
| Key | Value | Unit | Source | Basis |
| :--- | :--- | :--- | :--- | :--- |
| total_supply_near | 1,311,395,122 | NEAR | measured | RPC block header total_supply at height 224026014 |
| current_max_inflation_rate | 0.025 | ratio_annual | measured | RPC EXPERIMENTAL_protocol_config.max_inflation_rate |
| treasury_share | 0 | ratio | measured | RPC EXPERIMENTAL_protocol_config.protocol_reward_rate (validators receive 1 - this) |
| staked_supply_ratio | 0.443895 | ratio | measured | RPC validators current stake / total_supply (351 validators) |
| annual_issuance_near | 32,755,060 | NEAR_per_year | measured | minted_per_epoch 25705.589906658413 NEAR x epochs_per_year 1274.2387951313358 from total_supply jumps at epoch starts 223962737 -> 224005937 |
| issuance_realization_factor | 0.99909 | ratio | measured | measured annual issuance / (max_inflation_rate x total_supply); scales every regime's rate path |
| near_price_usd | 3.66 | USD | measured | nearstats price.currentUsd via intents_forensics.price.current_usd |
| daily_volume_usd | 125,257,736 | USD_per_day | measured | intents_forensics.fees.volume_30d_usd: DefiLlama near-intents daily volume summed over the canonical take-rate window (aligned daily charts, 30 complete UTC day |
| gross_take_bps | 14.5257 | bps | measured | intents_forensics.fees.gross_take_bps: sum(DefiLlama near-intents daily fees) / sum(dexs daily volume) x 1e4, same window (aligned daily charts, 30 complete UTC |
| capture_ratio | 0.33256 | ratio | measured | intents_forensics.fees.holders_capture_ratio: sum(DefiLlama near-intents dailyHoldersRevenue) / sum(daily fees), same window (aligned daily charts, 30 complete  |
| gas_burn_near_per_day | 850.5572 | NEAR_per_day | measured | -net_burn_per_epoch_near x epochs_per_year / 365.25 (total_supply drift within an epoch) |
| state_lock_growth_near_per_day | 332.3117 | NEAR_per_day | measured | archival view_account storage_usage growth across intents.near, aurora x storage_amount_per_byte |
| competitive_fee_ceiling_bps | 3.004 | bps | derived | median over cross-VM cells of the best competitor's friction (per-venue medians: Relay 3.0 bps (n=3) binding, LI.FI 25.0 bps (n=3) not binding); the lowest-fric |
| tau_floor_bps | 0.9824 | bps | derived | max(0.5 bps, min(live public take, live cross-VM headroom)) from the execution benchmark (headroom_by_archetype_bps.cross_vm = 0.98 bps). |
| tau_pub_start_bps | 10.8762 | bps | derived | reconciled: (gross_fees_30d - V_conf_30d x tau_conf / 1e4) / V_pub_30d; blended live gross take 14.53 bps (DefiLlama daily fees / daily volume summed over the a |
| alpha_capture | 0.33256 | ratio | measured | measured:defillama near-intents dailyHoldersRevenue / fees |
| terminal_multiple | 60 | x_fdv_to_revenue | derived | peer median FDV / annualized revenue ex-NEAR (n = 3), clipped to [8, 60]; raw 2410.6x. |
| sigma_price_annual | 1.026 | ratio_annual | measured | nearstats:price-history: 1y daily closes, log-return sigma x sqrt(365). |
| sigma_volume_monthly | 0.349226 | ratio_monthly | measured | measured: monthly log-return sigma of 30-day volume aggregates |


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

133 raw exchanges (130 ok, 3 failed), 5,201,770 bytes hashed; raw bodies persisted under `artifacts/raw` and listed with SHA-256 in `manifest.json`.

| Source | Records |
| :--- | ---: |
| across | 6 |
| coingecko | 1 |
| defillama | 15 |
| lifi | 9 |
| near_rpc | 38 |
| near_rpc_archival | 17 |
| nearblocks | 25 |
| nearstats | 2 |
| oneclick | 11 |
| relay | 9 |


Failed or non-2xx exchanges (expected ones include venue `no liquidity` / `route not enabled` answers, which are evidence, not errors):
| Source | Name | HTTP | Error |
| :--- | :--- | :--- | :--- |
| across | quote:eth_usdc_sol_usdc:50000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:500 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |
| across | quote:eth_usdc_sol_usdc:250000 | 400 | HTTP 400: ROUTE_NOT_ENABLED: Route is not enabled. |


### 15.1 Methodology warnings recorded during the run (15)
- execution_bench: eth_usdc_sol_usdc $500: venue USD oracles disagree with the cell's common price by more than the +1.29 bps headroom (1click +0.0 bps, relay +1.5 bps, lifi +4.6 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +1.5 bps, lifi +4.6 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_sol_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the +0.98 bps headroom (1click +0.0 bps, relay +1.5 bps, lifi +4.6 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $50,000: venue USD oracles disagree with the cell's common price by more than the -14.25 bps headroom (1click +0.0 bps, relay -19.1 bps, lifi +8.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: eth_usdc_btc $250,000: venue USD oracles disagree with the cell's common price by more than the -6.45 bps headroom (1click +0.0 bps, relay -19.1 bps, lifi +8.4 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $500: venue USD oracles disagree with the cell's common price by more than the -0.42 bps headroom (1click +0.0 bps, relay +0.3 bps, lifi +11.7 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $50,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click -0.0 bps, relay +0.3 bps, lifi +11.7 bps); headroom is measured on destination units, not USD legs
- execution_bench: base_usdc_arb_usdc $250,000: venue USD oracles disagree with the cell's common price by more than the -1.02 bps headroom (1click +0.0 bps, relay +0.3 bps, lifi +11.7 bps); headroom is measured on destination units, not USD legs
- intents_forensics: CONFIDENTIAL SPLIT IMPLAUSIBLE - NOT MEASURED: nearstats reports confidential 30d $0.20 (0.0000% of 30d volume) while tvl_without_volume: confidential TVL $141.26M but all-time confidential volume $0.32 of $38.26B; stream_ok: nearstats sourceHealth.confidentialStream.status = ok; split_withheld: check confidential-vs-shield (skip) says 'split withheld — NEAR total ≈ public'. The public tile appears to include confidential flow (source change). public/confidential fields set to null (raw kept in volume.split_reported); confidential_share_30d = 40% from the registry assumption confidential_share (source=assumption)
- intents_forensics: confidential share cross-check: on-chain treasury inflow over 24h was $21.63M, 12.4% of 24h volume + inflow, below the assumption's 15%-60% range (assumed 40%). A proxy, not a measurement of the share: hourly snapshots undercount gross flow and solver inventory inflates it
- intents_forensics: nearblocks: 15 duplicate receipt(s) seen on overlapping pages were counted once (id-based cursor vs time-ordered rows); unique receipts sampled = 185
- chain_signatures: 240 s sampling budget spent (NearBlocks rate limits) at window 7/12; remaining windows skipped
- chain_signatures: 6 of 12 sample windows failed; rates use the 6 that returned
- sotp: confidential share is the registry ASSUMPTION confidential_share = 40%, not a measurement (nearstats reported 0.0000%, rejected as implausible by confidential_split_guard); Engine 2 rests on that assumption and is reported as NOT MEASURED
- sotp: peer median FDV/revenue 2410.6x clipped to 60.0x (guardrails [8, 60])
