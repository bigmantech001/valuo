# QUANT_PIPELINE_SPEC.md — Reproducible Python Quant & Data Engine (`quant/`)

> **Status: original pre-build brief (Oct 2026), kept for the record.** The implementation and its design decisions are in `docs/MODEL_DESIGN.md`; dated endpoint probes are in `docs/LIVE_ENDPOINT_FACTS.md`. Figures quoted below are pre-build examples, not results. Current values are in `artifacts/latest_snapshot.json`; where this brief and the artifacts disagree, the artifacts are right.

## 1. Design Philosophy for AI & VC Judges
Every claim in **Valuo** must be **re-runnable from scratch with zero paid API keys** via `python -m valuo.reproduce`.
- All raw HTTP/RPC responses are hashed with `hashlib.sha256` and recorded in `artifacts/manifest.json` alongside exact NEAR Mainnet `block_height`, `block_hash`, and UTC timestamp.
- Monte Carlo simulations use an explicit deterministic `numpy.random.default_rng(seed=20261114)` so re-running on a judge's machine reproduces identical `P10 / P50 / P90` percentiles given the same snapshot.

---

## 2. Collector 1: NEAR Mainnet RPC Supply, Stake & Storage-Lock Audit (`quant/valuo/collectors/near_rpc.py`)

Use `POST https://free.rpc.fastnear.com` (fallback `https://rpc.mainnet.near.org`) to pull **100% on-chain ground truth**:

```python
import httpx
from pydantic import BaseModel

FASTNEAR_RPC = "https://free.rpc.fastnear.com"

TRACKED_STATE_SINKS = [
    "intents.near",     # Defuse / NEAR Intents core clearinghouse (live lock: near_rpc.tracked_sinks)
    "aurora",           # Aurora EVM engine state (live lock: near_rpc.tracked_sinks)
    "wrap.near",        # Wrapped NEAR liquidity vault (~34.9M NEAR balance)
    "v1.signer",        # Chain Signatures MPC coordinator
    "escrow.ai.near",   # NEAR AI Cloud / Agent escrow settlement account
    "meme-cooking.near",
    "ref-finance-101.near",
]

class ContractSinkSnapshot(BaseModel):
    account_id: str
    storage_bytes: int
    storage_locked_near: float   # storage_bytes * storage_amount_per_byte / 1e24
    liquid_balance_near: float   # (amount / 1e24) - storage_locked_near
    total_balance_near: float

class NearOnchainTruth(BaseModel):
    block_height: int
    block_hash: str
    timestamp_ns: int
    total_supply_near: float
    max_inflation_rate: float            # e.g. 1/40 = 0.025 (2.5%)
    storage_near_per_kb: float           # 0.01 NEAR/KB = 1 NEAR per 100 KB
    active_validator_count: int
    total_staked_near: float
    staked_Supply_ratio: float           # ~0.4531 (45.31%)
    nominal_staking_apr_current: float   # (0.025 * 0.90) / staked_ratio (90% validator share, 10% treasury)
    nominal_staking_apr_svrn_1_6: float  # (0.016 * 0.90) / staked_ratio
    gross_daily_issuance_near: float     # total_supply * max_inflation_rate / 365.25
    gross_daily_issuance_svrn_near: float# total_supply * 0.016 / 365.25
    tracked_sinks: list[ContractSinkSnapshot]
```

### Exact RPC Methods to Call:
1. **`block` (`{"finality": "final"}`)** $\rightarrow$ Extract `header.height`, `header.hash`, `header.timestamp`, and `int(header.total_supply) / 1e24`.
2. **`EXPERIMENTAL_protocol_config` (`{"finality": "final"}`)** $\rightarrow$ Extract `max_inflation_rate` (`num / den`, currently `[1, 40] = 0.025`), `protocol_reward_rate` (`[1, 10]` treasury share), and `runtime_config.storage_amount_per_byte` (`10000000000000000000` yoctoNEAR = `10^-5 NEAR/byte` = `1 NEAR / 100 KB`).
3. **`validators` (`[None]`)** $\rightarrow$ Sum `int(v["stake"]) / 1e24` across `current_validators`.
4. **`query` (`{"request_type": "view_account", "finality": "final", "account_id": acct}`)** $\rightarrow$ Compute exact `storage_locked_near = (storage_usage * storage_amount_per_byte) / 1e24`.

---

## 3. Collector 2: Live Cross-Venue Execution Benchmark (`quant/valuo/collectors/execution_bench.py`)

This collector proves empirically **why NEAR Intents commands sustainable pricing power**. Query real executable quotes concurrently across **3 clip sizes (`$500`, `$50,000`, `$250,000`)** and **3 corridor archetypes**:
1. **Cross-VM Flagship (`Ethereum USDC -> Solana USDC`):** `1Click` vs `Relay` vs `LI.FI` *(Note: `Across` is structurally incapable of non-EVM Solana settlement—record `supported=False` as empirical moat proof!)*.
2. **Native Bitcoin Corridor (`Ethereum USDC -> Native BTC`):** `1Click` (`nep141:btc.omft.near`) vs `Relay` vs `LI.FI` *(native BTC settlement without wrapped-BTC trust assumptions; Across cannot route it)*.
3. **EVM L2 Commodity Corridor (`Base USDC -> Arbitrum USDC`):** `1Click` vs `Across` vs `Relay` vs `LI.FI` *(intellectual honesty: show where EVM-native bridges like Across compete tightly at `~1–2 bps`, testing whether NEAR Intents' margin comes from cross-VM routes rather than EVM-L2 stablecoin swaps. Live result: 1Click leads on cross-VM and trails on EVM L2 and on native BTC, so the native-BTC moat claim is graded NOT_SUPPORTED)*.

### Verified Live Payloads (Tested & Working):

#### A. NEAR Intents `1Click` (`POST https://1click.chaindefuser.com/v0/quote`)
First fetch `GET https://1click.chaindefuser.com/v0/tokens` to map exact live `assetId` and `price` USD values dynamically. Then POST with `"dry": true`:
```python
oneclick_payload = {
    "dry": True,
    "swapType": "EXACT_INPUT",
    "slippageTolerance": 100,
    "originAsset": "nep141:eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near",
    "depositType": "ORIGIN_CHAIN",
    "destinationAsset": "nep141:sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near",
    "amount": str(amount_raw),  # e.g. "1000000000" for 1,000 USDC (6 decimals)
    "refundTo": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "refundType": "ORIGIN_CHAIN",
    "recipient": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV", # Valid Base58 Solana pubkey (or bc1q... for BTC)
    "recipientType": "DESTINATION_CHAIN",
    "deadline": deadline_iso_utc, # current UTC + 2 hours in ISO-8601
}
# Response: quote["amountOutFormatted"], quote["amountOutUsd"], quote["timeEstimate"]
```

#### B. Relay (`POST https://api.relay.link/quote`)
```python
relay_payload = {
    "user": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
    "originChainId": 1,               # 1 = Ethereum, 8453 = Base
    "destinationChainId": 792703809,  # 792703809 = Solana, 42161 = Arbitrum
    "originCurrency": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
    "destinationCurrency": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "recipient": "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
    "tradeType": "EXACT_INPUT",
    "amount": str(amount_raw),
}
# Response: details["currencyOut"]["amountFormatted"], details["timeEstimate"]
```

#### C. LI.FI (`GET https://li.quest/v1/quote`)
```python
# Query params: fromChain=ETH&toChain=SOL&fromToken=USDC&toToken=USDC&fromAmount=1000000000
# &fromAddress=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045&toAddress=7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV
# Response: int(estimate["toAmount"]) / 1e6, estimate["executionDuration"], tool
```

#### D. Across (`GET https://app.across.to/api/suggested-fees`)
```python
# Query params (Base 8453 -> Arbitrum 42161 USDC):
# inputToken=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913&outputToken=0xaf88d065e77c8cC2239327C5EDb3A432268e5831
# &originChainId=8453&destinationChainId=42161&amount=1000000000
# Net output = amount_raw - int(data["totalRelayFee"]["total"])
```

### Derived Microstructure Metric: **Pricing-Power Headroom (`bps`)**
For each corridor $c$ and clip size $s$:
$$\text{EffectiveFriction}_{\text{venue}}(c, s) = \frac{V_{\text{in}} - V_{\text{out, venue}}}{V_{\text{in}}} \times 10{,}000 \text{ bps}$$
$$\text{PricingPowerHeadroom}(c, s) = \min_{v \neq \text{1Click}} \text{EffectiveFriction}_{v}(c, s) - \text{EffectiveFriction}_{\text{1Click}}(c, s)$$
When $\text{PricingPowerHeadroom} > 0$, NEAR Intents delivers superior net execution *even after fees*, proving room for sustainable protocol/frontend buyback capture without losing order flow.

---

## 4. Collector 3: On-Chain `intents.near` Forensics & Comps (`intents_forensics.py` & `comps.py`)

1. **`GET https://nearstats.org/api/near/summary`** & **`/api/near/price-history`**:
   - Extract 24h, 7d, 30d, and all-time NEAR Intents swap volume, route/chain distribution, and historical `$NEAR` price volatility $\sigma$ (annualized log-return volatility from `/price-history` used directly to parameterize the Monte Carlo simulation!).
2. **`GET https://api.nearblocks.io/v1/account/intents.near/txns?per_page=25&page=1`** (fetch pages `1..4` = `100` recent settlements with polite rate-limit delay):
   - Classify `predecessor_account_id` across recent settlements:
     - **Autonomous AI / Escrow Contracts** (e.g. `escrow.ai.near`, `*.agent.near`, sub-account vaults)
     - **Omni / Bridge Relayers & Solver Accounts** (`*.omft.near`, solver accounts)
     - **Direct User Accounts**
   - Compute empirical **Caller Concentration HHI**:
     $$\text{HHI} = \sum_{i=1}^{N} \left(100 \times s_i\right)^2 \in (0, 10{,}000]$$
     and **Effective Number of Participants** $N_{\text{eff}} = 10{,}000 / \text{HHI}$.
3. **`GET https://api.llama.fi/summary/fees/{slug}`** for `near-intents`, `near`, `solana`, `ethereum`, `hyperliquid` + **`GET https://api.llama.fi/summary/dexs/near-intents`**:
   - Compute real trailing 30d annualized **Gross Fees**, **Protocol Revenue / Holder Buybacks**, and **FDV / Annualized Fees Multiple** across peer networks (`SOL`, `ETH`, `HYPE` vs. `NEAR`).

---

## 5. Quantitative Models (`quant/valuo/models/`)

### Model A: Supply Physics & Net-Deflation Crossover (`supply_physics.py`)
Daily net circulating `$NEAR` float change $\Delta S_t$ (in `NEAR/day`) is modeled as:
$$\Delta S_t = \underbrace{\frac{S_t \cdot i_t}{365.25}}_{\text{Epoch Validator + Treasury Issuance}} - \underbrace{\frac{V_{\text{pub}, t} \cdot \tau_{\text{pub}} \cdot \alpha_{\text{buyback}} + V_{\text{conf}, t} \cdot \tau_{\text{conf}} \cdot \alpha_{\text{buyback}}}{P_{\text{NEAR}, t}}}_{\text{Open-Market Buyback Sink}} - \underbrace{B_{\text{gas}, t}}_{\text{L1 Gas Burn (70\% base fee)}} - \underbrace{L_{\text{storage}, t}}_{\text{NEP State-Lock Sink (1 NEAR / 100 KB)}}$$

Where:
- $i_t$: `0.025` (`2.5%` current protocol cap) vs. **SVRN Governance Glidepath** linearly stepping from `0.025` to `0.016` (`1.6%`) over 24 months (`730` days).
- $V_{\text{pub}, t}, V_{\text{conf}, t}$: Daily Public Intents volume vs. **Confidential Intents Private Shard** volume (confidential TVL: `intents_forensics.confidential_tvl_usd`).
- $\tau_{\text{pub}}$: Empirically bounded by **Collector 2's** measured `PricingPowerHeadroom` (e.g. `4–12 bps` blended net fee).
- $\tau_{\text{conf}}$: Institutional MEV-protected Confidential Shard fee (`15–25 bps`).
- $\alpha_{\text{buyback}}$: Protocol/frontend net revenue share directed to open-market `$NEAR` buybacks (`~28%–35%` empirically observed on `revenue.near.org`, adjustable in UI).
- $L_{\text{storage}, t}$: Daily new state-locked `$NEAR` from new `intents.near` accounts, `v1.signer` vaults, and AI agent sub-accounts (`~5 KB–50 KB` per active agent/vault).

Solve analytically and numerically for **Breakeven Daily Intents Volume $V^*$** where $\Delta S_t \le 0$ (Net Deflation) under both `2.5%` and `1.6%` issuance regimes!

### Model B: 3-Engine Sum-of-the-Parts (SOTP) & 10,000-Path Monte Carlo (`sotp_valuation.py`)
Run `N = 10,000` 36-month (`3-year`) daily/monthly stochastic paths (`seed=20261114`) calibrated to historical `$NEAR` price/volume volatility from `nearstats.org` & `DefiLlama`:
1. **Engine 1 — Cross-Chain Clearinghouse Value:** Discounted cash flow + peer REV multiple on Public Intents buyback cash flows, incorporating competitive fee-compression decay $\lambda_{\text{decay}}$.
2. **Engine 2 — Confidential Execution & Dark-Pool Franchise Value:** High-margin institutional volume routed via NEAR's PBFT/TEE Confidential Shard (modeled separately due to structural MEV-protection moat).
3. **Engine 3 — Sovereign Agentic Custody & State-Lock Monetary Premium:** Scarcity premium from staked `$NEAR` (`~45.3%`) + permanently state-locked `$NEAR` across `intents.near`, `v1.signer`, and autonomous AI agents (`escrow.ai.near` / NEAR AI Cloud).

Output `P10` (Bear), `P25`, `P50` (Base), `P75`, `P90` (Bull) implied `$NEAR` valuations, Net Issuance Crossover Month probability distribution, and a $5 \times 5$ **Sensitivity Heatmap** (`Daily Intents Volume` $\times$ `Blended Take-Rate bps`).

### Model C: Steel-Manned Bear Case & Falsifiability (`bear_case.py`)
Explicitly quantify **4 Falsification Scenarios** (with exact math showing implied downside valuation if triggered):
1. **Aggregator Bypass / Fee Race to Zero:** Unauthenticated `25 bps` / partner `10–20 bps` fees compress to `1 pip` (`0.01 bps` base `intents.near` contract fee) because 3rd-party frontends bypass `near.com`.
2. **Governance Stalemate (`2.5%` Forever):** Validators reject the `2.5% -> 1.6%` issuance reduction, leaving `~32.7M NEAR/year` gross issuance overhang.
3. **Post-Incentive Volume Decay:** `NEAR@3.33` mercenary liquidity unwinds Confidential TVL by `-70%` and 30d volume drops `-60%`.
4. **Solver Cartelization (`HHI > 3,500`):** Top 2 market makers capture `>80%` of solver fills, widening spreads until LI.FI/Relay win order flow back.

---

## 6. Mandatory `pytest` Invariant Suite (`quant/tests/test_invariants.py`)
1. `test_near_rpc_ground_truth`: Verifies `total_supply_near > 1_000_000_000`, `0 < max_inflation_rate <= 0.05`, `intents.near` `storage_locked_near > 50_000`, and `0.25 < staked_supply_ratio < 0.80`.
2. `test_execution_benchmark_live_quotes`: Verifies real non-zero quotes returned by `1Click` and at least 2 external competitors, and verifies friction math `(in - out)/in * 10000` is exact.
3. `test_hhi_bounds`: Verifies `0 < HHI <= 10_000` and `abs(sum(shares) - 1.0) < 1e-6`.
4. `test_monte_carlo_determinism`: Runs `run_monte_carlo(seed=20261114)` twice and asserts `np.allclose(res1.p50_path, res2.p50_path, atol=1e-9)`.
5. `test_manifest_sha256_integrity`: Verifies `artifacts/manifest.json` contains valid 64-char hex SHA-256 digests and block hash matching `artifacts/latest_snapshot.json`.
