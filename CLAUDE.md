# CLAUDE.md — Valuo Build Instructions for Claude Code

## 1. Mission & Track Context
You are building **Valuo** for **`[ 02 / INV ] Investment Thesis`** (`$10,000` 1st Place + `$55,000` Overall Grand Prize contender) in the **`$250,000` NEAR Hackathon** (`nearhackathon.com`, submission window: **Nov 1 – Nov 14, 2026**).

**Official Track Mandate:**
> *"Make the long-term case. Build a long-term investment thesis for NEAR and back it with data: onchain analytics, live dashboards and models anyone can re-run. **Judged on evidence, not conviction.**"*

**One-Sentence Product Definition:**
> **Valuo is a reproducible Institutional Investment Committee (IC) Terminal and Python Quant Engine for `$NEAR`:** it empirically measures NEAR Intents' live basis-point pricing power against competing cross-chain routers (`1Click` vs. Relay, LI.FI, and Across), audits on-chain solver/agent concentration and NEP storage-staking supply sinks directly from NEAR Mainnet RPC, and feeds those verified empirical parameters—zero guessed inputs—into a **10,000-path Monte Carlo Issuance Crossover & Sum-of-the-Parts (SOTP) Valuation Model** with a Steel-Manned Bear Case.

---

## 2. CRITICAL: How This Repo Will Be Judged (`Claude Code` + `Codex` + VC Jury)
Hackathon repos are audited directly by **Claude Code and Codex acting as AI Judges**, alongside **Haseeb Qureshi (Dragonfly)**, **Avichal Garg (Electric Capital)**, **Eddy Lazzarin (a16z crypto CTO)**, **Kain Warwick (Synthetix/Infinex)**, **Mert Mumtaz (Helius)**, **Stepan Gershuni (cyber•Fund)**, and **Illia Polosukhin (NEAR)**.

### Non-Negotiable Rules:
1. **DO NOT CLONE EXISTING DASHBOARDS:** `revenue.near.org`, `nearstats.org`, and `svrn.net` already display headline NEAR Intents volume and cumulative fees. Valuo treats those as baseline inputs and answers the **unsolved institutional IC questions**:
   - *Microstructure Proof:* Why won't competing bridges compress NEAR Intents' take-rate to `0 bps`? (Proven via live executable quote benchmarks across `$500` / `$50K` / `$250K` clips + Confidential Shard dark-pool margin analysis).
   - *Concentration & Stickiness Audit:* Who actually settles on `intents.near` (solver/actor Herfindahl-Hirschman Index `HHI` + autonomous AI agent share such as `escrow.ai.near`)?
   - *Complete Supply Physics:* Combining open-market `$NEAR` buybacks + **NEP State-Staking Permanent Lock (`1 NEAR per 100 KB`)** against epoch issuance (`2.5%` current vs. the proposed **`2.5% -> 1.6%` SVRN governance glidepath**).
   - *Falsifiable Bear Case:* Quantifying exact conditions under which the bull thesis fails.
2. **ZERO MOCKED OR HARDCODED DATA:** Never invent synthetic chart arrays or fake quote spreads. Every metric in the UI and thesis must come from live RPC/API responses cached into timestamped, SHA-256 hashed DuckDB/JSON artifacts (`artifacts/latest_snapshot.json` & `artifacts/manifest.json`) with a live refresh button and CLI command.
3. **ONE-COMMAND REPRODUCIBILITY (`make reproduce`):** Any judge or AI auditor must be able to run `make reproduce` (or `cd quant && uv run python -m valuo.reproduce`) with **zero paid API keys required** to re-fetch live NEAR Mainnet state, execute live cross-router quote benchmarks, run the 10,000-path Monte Carlo simulation with a fixed seed (`seed=20261114`), run `pytest` statistical invariant checks, and regenerate `artifacts/latest_snapshot.json` + `artifacts/IC_MEMO.md`.
4. **CRISP `NetLayerLabs` QUANT PROSE:** Write like an Electric Capital / Dragonfly research memo—direct, mathematical, skeptical, and zero AI buzzwords ("revolutionize", "delve", "seamless", "unlocking").

---

## 3. First Step Before Coding: Pull Official NEAR Skills
Run these commands first in the repository root:
```bash
mkdir -p .claude/skills vendor docs artifacts
git clone --depth 1 https://github.com/near/agent-skills.git vendor/near-agent-skills
cp -r vendor/near-agent-skills/* .claude/skills/ 2>/dev/null || true
```

---

## 4. Verified Live Zero-Key Data Endpoints (Tested Oct 2026)

Every endpoint below works **without paid API keys** out of the box (optional keys in `.env` only increase rate limits):

| Data Layer | Live Endpoint | Verified Output |
| :--- | :--- | :--- |
| **NEAR Mainnet RPC (FastNEAR)** | `POST https://free.rpc.fastnear.com` | `block` (`total_supply` ~`1.3098B NEAR`, `gas_price`), `EXPERIMENTAL_protocol_config` (`max_inflation_rate: [1, 40]` = `2.5%`, `storage_amount_per_byte: 10^19`), `validators` (`392` validators, `~593.5M NEAR` staked), `query/view_account` (`intents.near` `12.96 GB` = `129,607 NEAR` state-locked!) |
| **NEAR Intents 1Click Tokens** | `GET https://1click.chaindefuser.com/v0/tokens` | Live Defuse/Omni asset IDs (`nep141:...`), decimals, USD prices across BTC, SOL, ETH, Base, Arbitrum, NEAR, ZEC |
| **NEAR Intents 1Click Quotes** | `POST https://1click.chaindefuser.com/v0/quote` (`"dry": true`) | Live executable solver quotes (`amountOut`, `amountOutUsd`, `timeEstimate`, `withdrawFee`) with no deposit address spam |
| **Relay Competitor Quotes** | `POST https://api.relay.link/quote` | Live cross-chain solver quotes (`details.currencyOut.amountFormatted`, `details.timeEstimate`) across Ethereum (`1`), Base (`8453`), Arbitrum (`42161`), Solana (`792703809`) |
| **LI.FI Competitor Quotes** | `GET https://li.quest/v1/quote` | Live aggregator quotes (`estimate.toAmount`, `estimate.executionDuration`, `tool`) across EVM + Solana + Bitcoin bridges |
| **Across Competitor Quotes** | `GET https://app.across.to/api/suggested-fees` | Live EVM-only intent fees (`totalRelayFee.total`, `estimatedFillTimeSec`) showing Across's EVM speed vs. inability to route native BTC/SOL/NEAR/ZEC |
| **NearStats Ecosystem API** | `GET https://nearstats.org/api/near/summary` & `/price-history` | Live 24h/7d/30d/all-time NEAR Intents swap volume (`$35.8B+`), chain/route breakdowns, historical `$NEAR` price series |
| **NearBlocks On-Chain Txns** | `GET https://api.nearblocks.io/v1/account/intents.near/txns?per_page=25&page=1` | Live `intents.near` callers (`escrow.ai.near`, solver relayers, user wallets) + `/v1/stats` network telemetry |
| **DefiLlama Fees & Comps** | `GET https://api.llama.fi/summary/fees/{slug}` & `/summary/dexs/near-intents` | Historical daily fees/revenue for `near-intents`, `near`, `solana`, `ethereum`, `hyperliquid` for live REV valuation multiples |

---

## 5. Target Monorepo Architecture

```text
Valuo/
├── CLAUDE.md
├── README.md
├── QUANT_PIPELINE_SPEC.md
├── TERMINAL_UI_SPEC.md
├── Makefile                         # `make reproduce`, `make test`, `make dev`
├── .env.example
├── artifacts/                       # Generated by `quant` and read/served by `web`
│   ├── latest_snapshot.json         # Complete reproducible dataset + Monte Carlo outputs
│   ├── manifest.json                # Block heights, UTC timestamps, SHA-256 raw payload hashes
│   └── IC_MEMO.md                   # Auto-generated quantitative Investment Committee memo
├── quant/                           # Reproducible Python 3.11+ Quant Engine (`pyproject.toml`)
│   ├── pyproject.toml
│   ├── valuo/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── collectors/
│   │   │   ├── near_rpc.py          # Protocol config, supply, stake, NEP storage-lock audit
│   │   │   ├── execution_bench.py   # Live 1Click vs Relay vs LI.FI vs Across quote matrix
│   │   │   ├── intents_forensics.py # NearStats + DefiLlama + NearBlocks actor/HHI & AI share
│   │   │   └── comps.py             # Live SOL, ETH, HYPE fee/FDV multiples
│   │   ├── models/
│   │   │   ├── supply_physics.py    # 2.5% vs 1.6% SVRN glidepath + buybacks + state-lock sink
│   │   │   ├── sotp_valuation.py    # 3-Engine SOTP DCF + Comps + 10,000-path Monte Carlo
│   │   │   └── bear_case.py         # Falsifiability thresholds & stress-test matrix
│   │   ├── memo_generator.py        # Renders `artifacts/IC_MEMO.md` from verified numbers
│   │   └── reproduce.py             # Single CLI entrypoint (`python -m valuo.reproduce`)
│   └── tests/
│       └── test_invariants.py       # Accounting identities, HHI bounds, Monte Carlo reproducibility
└── web/                             # Next.js 15 (App Router) Institutional Quant Terminal
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx             # 5-tab Institutional IC Terminal
    │   │   └── api/
    │   │       ├── snapshot/route.ts       # Serves verified snapshot + provenance manifest
    │   │       └── live-benchmark/route.ts # Executes real-time 1Click vs Competitor quote race
    │   ├── components/              # SpreadMatrix, SupplyCrossoverChart, MonteCarloLab, BearStressTable, ProvenanceDrawer
    │   └── lib/
    │       └── quantClient.ts       # Deterministic client-side sensitivity & slider recalculation
    └── package.json
```

---

## 6. Execution Order for Claude Code

1. **Phase 1 — Reproducible Python Quant Engine (`quant/`):**
   - Implement all 4 collectors in `quant/valuo/collectors/` with resilient timeouts, exact JSON schema validation (`pydantic`), and raw payload SHA-256 hashing.
   - Implement `supply_physics.py`, `sotp_valuation.py` (`10,000` seeded Monte Carlo paths), and `bear_case.py`.
   - Run `python -m valuo.reproduce` and verify it generates real, populated `artifacts/latest_snapshot.json`, `artifacts/manifest.json`, and `artifacts/IC_MEMO.md` from live mainnet/API calls.
   - Run `pytest` in `quant/` to verify every accounting identity and statistical bound passes.
2. **Phase 2 — Live Next.js API Routes (`web/src/app/api/`):**
   - Wire `/api/snapshot` to serve `artifacts/latest_snapshot.json` + `artifacts/manifest.json` (with live RPC header freshness check).
   - Wire `/api/live-benchmark` so any judge can click **"Run Live Quote Race"** in the browser and watch `1Click` vs. `Relay` vs. `LI.FI` vs. `Across` return real-time quotes in `<3 seconds`.
3. **Phase 3 — Institutional IC Research Terminal (`web/`):**
   - Build all 5 tabs defined in `TERMINAL_UI_SPEC.md` with institutional quant aesthetics (high-density tabular figures `tabular-nums`, confidence fan charts, sensitivity heatmaps, clickable block/tx provenance badges, and 1-click IC Memo export).
4. **Phase 4 — Final Audit & Documentation Polish:**
   - Run `make reproduce && make test` and `npm run build` in `web/`.
   - Ensure `README.md` top section contains exact live findings and the 60-second reproduction instructions for `Claude Code` / `Codex` and human judges.
