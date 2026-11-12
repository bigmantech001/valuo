# <img src="web/src/app/icon.svg" alt="" width="34" height="34" align="top"> Valuo

**The long-term investment case for $NEAR, stated as conditions anyone can check against live mainnet data.**

Valuo is an Investment Committee (IC) terminal and a Python quant engine. It reads NEAR mainnet and NEAR Intents live, races NEAR Intents' 1Click router against Relay, LI.FI and Across on the same trades, values the cash flows NEAR holders can point to with a seeded 10,000-path Monte Carlo, and then inverts the model: what would each input have to be for the model to equal the market price? Everything is judged by one comparison: **what NEAR's market value requires vs what the live data shows today**, condition by condition, graded *on track*, *behind* or *against*.

Built for the NEAR Hackathon 2026, `[ 02 / INV ] Investment Thesis` track · Not investment advice · App: **[usevaluo.vercel.app](https://usevaluo.vercel.app)** · Demo: `<VIDEO_URL>` · Code: private until submission, access on request

**Judges, start here:** open [`/terminal#thesis`](https://usevaluo.vercel.app/terminal#thesis) for the bull-case scorecard (no wallet, no login), then [`/terminal?verify=rehash`](https://usevaluo.vercel.app/terminal?verify=rehash) to re-hash every stored source payload in your browser. To rebuild every number yourself: `make sync && make reproduce` (no API keys). A claim-by-claim checklist is in **[JUDGES.md](JUDGES.md)**.

---

## Seven sections, no wallet needed

| Section | What it is | Try it without a wallet |
| --- | --- | --- |
| **01 Thesis & evidence** | The **bull-case scorecard**: 8 conditions the long-term case needs (Intents volume growth, holder revenue, the L1 multiple, 1Click's pricing edge, confidential flow, net deflation, the 2.5% → 1.6% issuance cut, solver competition). Each shows the value it requires, the live value, a 90-day trend from a real series and a status. Below it: the reverse valuation and the evidence scorecard. | [`/terminal#thesis`](https://usevaluo.vercel.app/terminal#thesis) |
| **02 Execution alpha** | **Live quote race.** The same dry quote request goes to 1Click, Relay, LI.FI and Across at once, ranked on destination units delivered for the identical input, on cross-VM (`ETH USDC → SOL USDC`), native BTC and EVM L2 routes, at $500, $50,000 and $250,000. Nothing is signed or sent. | [`/terminal#execution`](https://usevaluo.vercel.app/terminal#execution) → **Run live quote race** |
| **03 Supply physics** | Issuance measured per epoch from `total_supply` jumps, against buybacks, L1 gas burn and NEP storage-staking locks (1 NEAR per 100 KB). Breakeven daily volume per issuance regime, and a **Chain Signatures** audit of `v1.signer` usage. | [`/terminal#supply`](https://usevaluo.vercel.app/terminal#supply) → toggle the regime |
| **04 SOTP & Monte Carlo** | Three-engine sum-of-the-parts (SOTP) valuation, 10,000 seeded paths (seed `20261114`), sliders that re-price client-side with the same formulas, a sensitivity tornado and peer multiples. **Publish your forecast** to NEAR from here (needs a wallet). | [`/terminal#sotp`](https://usevaluo.vercel.app/terminal#sotp) → move the sliders |
| **05 Bear case** | Four stress scenarios priced through the same model, each with a live early-warning trigger and threshold. A trigger that was not measured says so; it is never read as "not breached". | [`/terminal#bear`](https://usevaluo.vercel.app/terminal#bear) |
| **06 History** | Daily snapshots and hourly quote races as time series, plus an **out-of-sample backtest** of the volume model, including where it fails. | [`/terminal#history`](https://usevaluo.vercel.app/terminal#history) |
| **07 Ask the analyst** | Questions answered only from the hashed snapshot by a model on NEAR AI Cloud's attested private inference. Every sentence cites its source; numbers are checked against the context; the response signature is verified against NEAR AI's attestation report. *If it is not in the snapshot, the analyst says so.* | [`/terminal#analyst`](https://usevaluo.vercel.app/terminal#analyst) |

### More to explore

| Feature | What it is | Where |
| --- | --- | --- |
| **Verify sources** | Re-hashes every stored raw payload with WebCrypto in your browser, and "Fetch live and compare" re-issues a recorded request to show what changed since the snapshot. | header → **Verify sources**, or [`/terminal?verify=rehash`](https://usevaluo.vercel.app/terminal?verify=rehash) |
| **IC memo** | A 15-section Markdown memo generated from the snapshot. It opens with the falsifiable long-term case. | [`/api/snapshot?format=memo`](https://usevaluo.vercel.app/api/snapshot?format=memo) |
| **Snapshot JSON** | The exact bytes of the dataset the terminal renders (SHA-256 equals `manifest.json`: `snapshot_sha256`). The manifest comes with the default [`/api/snapshot`](https://usevaluo.vercel.app/api/snapshot) response. | [`/api/snapshot?format=json`](https://usevaluo.vercel.app/api/snapshot?format=json) |
| **Forecast board** | Every forecast published to NEAR SocialDB under `*/valuo/forecast/*`, read key-free and scored against later snapshots. The board keeps the newest 5 records per account and drops any record whose horizon is not after its creation date or whose stated creation time disagrees with the block that stored it (a backdated forecast). | [`/terminal#sotp`](https://usevaluo.vercel.app/terminal#sotp), below **Publish your forecast** (click **Refresh** if it looks empty; the list is cached up to 30 s). Raw: [`/api/forecasts`](https://usevaluo.vercel.app/api/forecasts) |
| **Landing page** | The thesis in one page: what the price requires, the measured strengths and weaknesses, and the falsification triggers. | [`/`](https://usevaluo.vercel.app/) |

The terminal has a sticky left sidebar with count badges (bull-case conditions on track, bear triggers breached, history points) that collapses to its section numbers. On phones and tablets it becomes a left drawer opened by a burger button, every table scrolls inside its card, and inputs use 16 px text so iOS does not zoom. The header shows the snapshot's NEAR block, its time and how far it trails the live chain head.

## Why NEAR mainnet is essential

Without NEAR's public chain there is no evidence, only a narrative.

- **No mainnet, no supply physics.** Issuance, validators, storage locks and protocol limits are read from NEAR RPC at a recorded block (`quant/valuo/collectors/near_rpc.py`). Issuance is measured from `total_supply` jumps at epoch boundaries, not assumed from the 2.5% cap.
- **No `intents.near`, no forensics.** Solver concentration is decoded from `execute_intents` signer payloads, and the Confidential Intents treasury (an implicit account holding NEP-245 balances inside `intents.near`) is read directly for TVL and boundary flow (`quant/valuo/collectors/confidential_boundary.py`).
- **No 1Click, no pricing-power test.** The headroom figure only exists because NEAR Intents serves executable dry quotes that can be compared, unit for unit, with competitors (`quant/valuo/collectors/execution_bench.py`).
- **No SocialDB, no tamper evidence.** Each daily snapshot's hashes are written to `social.near`, and visitors' forecasts are written there too (`quant/valuo/anchor.py`, `web/src/lib/forecast.ts`). Anyone can read both back over public RPC.

## Architecture

Valuo has four layers:
- **The quant engine** (`quant/`, Python): collectors fetch and hash every response, models compute, and one command writes `artifacts/`.
- **The artifacts** (`artifacts/`): `latest_snapshot.json`, `manifest.json` (SHA-256 of every raw payload), `IC_MEMO.md`, raw payloads and the history store. The web app reads only these.
- **The web terminal** (`web/`, Next.js): renders the artifacts and runs the live checks (quote race, re-hash, refetch, analyst, forecasts).
- **The scheduler:** a VPS runs the daily snapshot and the hourly quote race, commits the results back to the repository and anchors each snapshot on NEAR.

Model design, field by field: **[docs/MODEL_DESIGN.md](docs/MODEL_DESIGN.md)**. Endpoint behaviour as probed: **[docs/LIVE_ENDPOINT_FACTS.md](docs/LIVE_ENDPOINT_FACTS.md)**. Scheduler: **[docs/VPS.md](docs/VPS.md)**.

### System overview

```mermaid
flowchart LR
  subgraph Visitors["Visitors"]
    direction TB
    JUDGE["Judges and readers<br/>no wallet"]
    FORE["Forecasters<br/>NEAR wallet"]
  end

  subgraph Sched["Scheduler VPS"]
    direction TB
    DAILY["Daily 06:05 UTC<br/>snapshot + anchor"]
    HOURLY["Hourly :23<br/>quote race"]
  end

  subgraph Quant["Python quant engine"]
    direction TB
    COLL["Collectors<br/>hash every response"]
    MODELS["Models<br/>SOTP, Monte Carlo, bull, bear,<br/>backtest, reverse valuation"]
  end

  subgraph Repo["Git repository"]
    ART["artifacts/<br/>snapshot, manifest, memo, raw, history"]
  end

  subgraph Web["Next.js web terminal"]
    direction TB
    PAGES["Pages<br/>/ and /terminal"]
    API["API routes<br/>snapshot, raw, refetch,<br/>live-benchmark, forecasts, analyst"]
  end

  subgraph External["Public sources and NEAR"]
    direction TB
    RPC["NEAR RPC<br/>mainnet + archival"]
    INTENTS["1Click, Relay,<br/>LI.FI, Across"]
    DATA["NearBlocks, nearstats,<br/>DefiLlama, CoinGecko"]
    SOCIAL["social.near<br/>SocialDB"]
    NEARAI["NEAR AI Cloud<br/>attested inference"]
  end

  DAILY -->|make reproduce| COLL
  HOURLY -->|make bench-history| COLL
  COLL -->|key-free reads| RPC
  COLL --> INTENTS
  COLL --> DATA
  COLL --> MODELS
  MODELS -->|write| ART
  DAILY -->|signed set, anchor key| SOCIAL
  ART --> API
  JUDGE --> PAGES
  PAGES --> API
  API -->|dry quotes| INTENTS
  API -->|view calls| SOCIAL
  API -->|server key| NEARAI
  FORE -->|wallet-signed set| SOCIAL
```

The engine is the only writer of `artifacts/`; the web app only reads them, so every number on screen traces to a hashed file. The live checks in the web app (quote race, refetch, forecast board, analyst) call public sources directly but never change the artifacts. The scheduler commits each run back to the repository, so the deployed site and the repository show the same snapshot.

### Who holds which key

```mermaid
flowchart LR
  ANCHORKEY["Anchor key<br/>VPS only"] -->|"signs social.near set"| ANCHORNS["valuo/snapshot/*<br/>under the anchor account"]
  WALLET["Visitor's wallet"] -->|"signs social.near set"| FORENS["valuo/forecast/*<br/>under the visitor's account"]
  AIKEY["NEAR_AI_API_KEY<br/>server env only"] -->|"Bearer, chat completions"| NEARAI["NEAR AI Cloud"]
  DEPLOY["Deploy key<br/>VPS only"] -->|"git push"| REPO["bigmantech001/valuo"]
```

| Key | Lives in | Can | Can never |
| --- | --- | --- | --- |
| Anchor account key | the VPS, `/home/valuo/.near-credentials/mainnet/` (mode 600) | write `valuo/snapshot/*` under its own SocialDB namespace, spend its own small balance | touch other accounts, user funds or any visitor's forecast |
| Visitor's wallet | the visitor's wallet app | write that visitor's own forecast | write under any other account (SocialDB only accepts writes to the signer's namespace) |
| `NEAR_AI_API_KEY` | server environment (`.env` locally, the host's env vars in production) | call NEAR AI chat completions | reach the browser; it is never logged or returned |
| GitHub deploy key | the VPS, `~/.ssh/valuo_deploy` | push to this one repository | access any other repository |

Collectors need no key at all. Optional keys (`ONECLICK_JWT`, `NEARBLOCKS_API_KEY`) only unlock confidential quotes or raise rate limits.

### The data pipeline

```mermaid
flowchart LR
  subgraph Collect["Collect, hash every response"]
    direction TB
    A1["near_rpc"]
    A2["execution_bench<br/>quote race"]
    A3["intents_forensics<br/>+ confidential treasury"]
    A4["comps<br/>peer fees, FDV"]
    A5["chain_signatures<br/>v1.signer"]
  end
  subgraph Model["Model"]
    direction TB
    B1["supply_physics"]
    B2["sotp_valuation<br/>10,000 paths"]
    B3["bear_case"]
  end
  subgraph Derive["Derived views"]
    direction TB
    C1["market_implied"]
    C2["sensitivity"]
    C3["relative_value"]
    C4["bull_case"]
    C5["backtest"]
  end
  subgraph Write["Write"]
    direction TB
    D1["latest_snapshot.json"]
    D2["manifest.json"]
    D3["IC_MEMO.md"]
    D4["history/"]
  end
  Collect --> Model --> Derive --> Write
```

Collectors run concurrently and every request goes through `valuo.provenance.fetch_json` or `near_rpc_call`, which store the exact response bytes under `artifacts/raw/` and record source, URL, SHA-256, size and fetch time in the manifest. A source that fails becomes a warning and a `null`; nothing is substituted. The derived views read only the snapshot, so they add no fetches.

### Daily run on the scheduler

```mermaid
sequenceDiagram
  autonumber
  participant Cron as cron 06:05 UTC
  participant Job as valuo-run.sh snapshot
  participant Q as quant engine
  participant Git as GitHub repo
  participant Soc as social.near
  Cron->>Job: start in a systemd scope, MemoryMax 768M
  Job->>Git: fetch, fast-forward main
  Job->>Q: make reproduce
  Q->>Q: collect, model, write artifacts
  Job->>Q: make test
  Job->>Q: append to history
  Job->>Git: commit artifacts and README findings
  alt VALUO_ANCHOR_ACCOUNT set
    Job->>Q: valuo.anchor publish
    Q->>Soc: set valuo/snapshot/key = hashes, signed with the anchor key
    Soc-->>Q: write block height
    Job->>Q: valuo.anchor verify
    Job->>Q: valuo.anchor falsification
  end
  Job->>Git: push, rebase and retry on conflict
  Note over Job: one lock serialises the daily and hourly jobs
```

An anchoring failure is logged and never fails the run; that snapshot is simply not anchored. The hourly job (`valuo-run.sh bench`) runs the quote race, re-hashes its stored payloads and commits `artifacts/history/`.

**Falsification is written on-chain, not announced.** The thesis is falsified if any bear trigger holds for 30 consecutive days. `valuo.history` counts each streak over the daily records: two records more than 36 h apart break it, and so does a day the trigger was not measured, so a missed run never counts as a breached day. After each anchor, `valuo.anchor falsification` reads `artifacts/history/summary.json` and, for any trigger whose streak has reached 30 days and has no record yet, writes `<account>/valuo/falsification/<trigger>` (trigger, threshold, streak start, last value, snapshot SHA-256) with the same key and transaction path as the snapshot anchor. As of 2026-11-12 no trigger qualifies: governance stalemate and solver cartelization each read 1.7 of 30 days, restarted on 2026-11-10 after a 40 h gap in the daily records. Current streaks are on the History tab and in `artifacts/history/summary.json` (`snapshots.bear_triggers`). `make falsification-check ANCHOR=<account>` prints the per-trigger status and the args it would send (no key); `make falsification-list ANCHOR=<account>` reads the records back and recomputes each streak from `snapshots.jsonl`.

### Publishing a forecast

```mermaid
sequenceDiagram
  autonumber
  participant U as Visitor
  participant App as /terminal#sotp
  participant API as /api/forecasts
  participant W as NEAR wallet
  participant Soc as social.near
  U->>App: set sliders, price target, horizon
  App->>API: storage_for the account
  API->>Soc: storage_balance_of, storage_balance_bounds
  API-->>App: deposit to attach
  App->>W: sign set with the forecast JSON
  alt visitor approves
    W->>Soc: FunctionCall set, 100 Tgas
    Soc-->>App: tx hash, stored key
  else visitor rejects
    W-->>App: nothing was written
  end
  App->>API: board, read key-free
  Note over API,Soc: the indexer finds accounts, RPC confirms each entry on-chain
```

On an account's first SocialDB write the deposit is SocialDB's minimum storage balance (0.02 NEAR) plus about 0.01 NEAR; later writes attach about 0.01 NEAR. Forecasts are scored against the price in later snapshots once their horizon passes.

### Asking the analyst

```mermaid
sequenceDiagram
  autonumber
  participant U as Reader
  participant R as /api/analyst
  participant AI as NEAR AI Cloud
  U->>R: question
  R->>R: retrieve facts from the snapshot and memo, BM25
  R->>AI: attestation report, nonce-bound
  R->>AI: chat completion, numbered context only
  AI-->>R: streamed answer with citations
  R->>AI: response signature
  R->>R: check sha256 of request and response, verify ed25519 signer
  R-->>U: answer, citations, figure check, verified badge
  Note over R: no key or no credits means an explicit message, never a fallback answer
```

The default model is `deepseek-ai/DeepSeek-V4.1-Flash-1017`, served by NEAR AI from attested TEE (trusted execution environment) hardware. "Verified by NEAR AI attestation" appears only when the signed hashes match the exact bytes sent and received and the signer is in the attestation report. The hardware quotes inside that report are not re-verified locally.

### Getting started

```mermaid
flowchart LR
  subgraph Read["Read and verify, no wallet"]
    direction LR
    S1["Open /terminal"] --> S2["Bull-case scorecard"] --> S3["Run the quote race"] --> S4["Verify sources"]
  end
  subgraph Rebuild["Rebuild, no keys"]
    direction LR
    R1["make sync"] --> R2["make reproduce"] --> R3["make test"] --> R4["make anchor-verify"]
  end
  subgraph Commit["Commit a view, wallet"]
    direction LR
    F1["Connect wallet"] --> F2["Publish forecast"] --> F3["See it on the board"]
  end
  Read --> Rebuild --> Commit
```

### One real run, end to end

On 2026-11-10 the scheduler's account anchored the 13:04 UTC snapshot (manifest of 134 hashed records, NEAR block 223,919,878) on NEAR mainnet in transaction [`7fZ41XeD…`](https://nearblocks.io/txns/7fZ41XeDrCAjzN2ig7YTP7e3hPZz218Bns2KiiUkLPyy), written at block 223,920,960. Checked from a separate machine with `make anchor-verify ANCHOR=0161aff7…81f0`: every hash matched. The anchor account is [`0161aff7…81f0`](https://nearblocks.io/address/0161aff765e5412f3d3cac430933fb44325b5b012cf525410a9c7d1fa2fa81f0).

**A visitor forecast, end to end.** On 2026-11-11 the account [`bigmantech001.near`](https://nearblocks.io/address/bigmantech001.near) published a forecast from its own wallet through **Publish your forecast**: transaction [`3ZqwUprY…`](https://nearblocks.io/txns/3ZqwUprYywZuJ6puotb7mK9zHBTKmKnM3aQaTWwmpU2y), SocialDB key `bigmantech001.near/valuo/forecast/20261111T045413Z`, written at block 224,018,870 (5.5 Tgas, 0.03 NEAR storage deposit). It shows on the board at [`/terminal#sotp`](https://usevaluo.vercel.app/terminal#sotp) (scroll below **Publish your forecast**) as "On-chain", and in [`/api/forecasts`](https://usevaluo.vercel.app/api/forecasts).

**The quote-race record.** Over the first 46 recorded races (2026-11-08 20:34 to 2026-11-12 06:23 UTC, 3.4 days), 1Click delivered the most output in 171 of 413 decided route-clip races: 41%, 90% Wilson interval 37% to 45%. The aggregate hides a split. It won all 138 on ETH USDC to SOL USDC (median margin +0.98 bps), 26 of 138 on ETH USDC to native BTC (Relay won 109 of the 112 losses, median shortfall 14.5 bps) and 7 of 137 on Base USDC to Arbitrum USDC (Across 112, Relay 18; median shortfall 1.02 bps). The job adds a race every hour, so these counts are a dated reading; the current ones are in the table named below. A race counts only when 1Click and at least one competitor quoted; |headroom| below 0.01 bps is a tie and is left out of the rate. Hourly races are autocorrelated, so the interval is narrower than the true uncertainty. The table is `bench.routes` in `artifacts/history/summary.json` and the first card of the History tab.

---

<!-- VALUO:FINDINGS:START -->
## Findings as of the committed snapshot (NEAR block 224,174,242, 2026-11-12T06:05:01.555Z UTC)

Generated by `python -m valuo.reproduce` from `artifacts/latest_snapshot.json` (SHA-256 `f201d830075e3451cb4aaadcd502ee1c393c84b7e01b5a33e0646b25e173c11e`, 2026-11-12T06:05:03.441Z UTC, valuo 0.1.0). Every figure is a live fetch, an arithmetic derivation or a labeled assumption; `n/a` means the source was unavailable in this run and nothing was substituted. `make reproduce` regenerates this block.

| Finding | Value | Basis |
| :--- | :--- | :--- |
| NEAR block / total supply | 224,174,242 / 1,311,473,244 NEAR | RPC `block` header at 2026-11-12T06:05:01.555Z |
| Market FDV vs model (expected path / MC P50) | $4.63B vs $2.11B / $689.1M (market = 2.2x the expected path) | model capitalises Intents holder revenue + gas burn + state lock, 36 m, 25% discount, 60x terminal cap |
| What the market FDV requires (one input at a time) | expected volume growth 127.4% (evidence 21.8%; outside); starting public take 56.99 bps (evidence 3.00 bps; outside); terminal multiple 135x (evidence 2,512x; inside) | brentq solve on the expected path, others at base; evidence = trailing-12m Intents volume growth, live competitive fee ceiling, peer median FDV/revenue (`market_implied`) |
| Relative value: FDV / annualised fees | NEAR 64x vs peer median 257x; rank 2 of 4 (lowest first, inside the peer range) | peer-multiple band $11.50B-$46.25B is a cross-check, not a fair value; n = 3 peers (`relative_value`) |
| Top FDV drivers (tornado) | public_volume_growth_yoy $710.2M-$6.45B; terminal_multiple $369.2M-$5.13B; fee_compression_lambda_monthly $847.9M-$3.53B (86% of swing-squared variance) | 17 inputs at registry / measured ranges; 2 reach the market FDV (`sensitivity`) |
| Protocol inflation cap / measured issuance | 2.50% cap; measured 32,701,161 NEAR/yr = 2.493% (89,531 NEAR/day) | `EXPERIMENTAL_protocol_config`; total_supply jumps at epoch starts |
| Validators / staked ratio | 340 / 44.38% (581,994,836 NEAR) | RPC `validators` |
| intents.near NEP state lock | 13,603,518,865 bytes = 136,035 NEAR locked; growth 304.9 NEAR/day over 29.9 d | `view_account` + storage_amount_per_byte (0.01 NEAR/KB); archival lookback for growth |
| NEAR Intents 30d volume (public / confidential) | $3.73B (n/a / n/a; confidential share 11.5%) | total: nearstats / DefiLlama; confidential share ESTIMATED ON-CHAIN (`onchain_estimate`): on-chain estimate: Confidential Intents Treasury 24h inflow / (24h volume + inflow) = 11.5% (band 11.5%-14.8%); nearstats split implausible |
| Gross take / net take / capture ratio | 15.50 bps / 4.83 bps / 31.2% | ONE canonical window: aligned daily charts, 30 complete UTC days 2026-10-13..2026-11-11 |
| Daily sinks vs issuance | buyback 17,025 NEAR + gas burn 966 NEAR + state lock 337 NEAR = 20.5% of 89,531 NEAR/day | supply_physics; buyback = V x tau x alpha / P |
| Breakeven daily volume V* (status quo / SVRN glidepath) | $644.5M / $409.1M per day (today $124.4M/day) | V* = (I - G - L) x P / (tau x alpha) at the regime's terminal rate |
| Live quote race, 1Click headroom vs best competitor (destination units) | ETH USDC -> SOL USDC: +2.25 bps median over 3 cells; ETH USDC -> native BTC: -0.09 bps median over 3 cells; Base USDC -> Arbitrum USDC: -1.02 bps median over 3 cells | 1Click vs Relay / LI.FI / Across at $500, $50,000, $250,000; competitor ceiling 3.00 bps on cross-VM; 2026-11-12T06:05:10.633Z |
| Deposit/caller HHI / solver HHI on intents.near | 2,450 (bootstrap 90% CI 1,500-3,550) / 4,324 (bootstrap 90% CI 3,757-4,816) (87 fill participations over 17,341 s); cartel trigger breached | NearBlocks receipts: 137 over 8 pages; AI-agent (name-pattern) share 45.0% |
| SOTP FDV P10 / P50 / P90 (36 m, discounted) | $134.7M / $689.1M / $4.17B vs current FDV $4.63B (-85.1% at P50) | 10,000 paths, seed 20261114; terminal multiple 60.0x (derived); deterministic (expected-path) FDV $2.11B |
| Bear case, combined worst (deterministic, median inputs) | $214.5M (-90%); triggers breached 2 of 4 measured | four falsification scenarios through deterministic_sotp; live early-warning metrics |
| Evidence scorecard | DERIVED 4, NOT_SUPPORTED 2, VERIFIED_LIVE_API 3, VERIFIED_ON_CHAIN 3 | 12 graded claims in `IC_MEMO.md` section 12 |

13 methodology warning(s) recorded in this run; see `IC_MEMO.md` section 15.1.
<!-- VALUO:FINDINGS:END -->

---

## Safety and trust model

- **Nothing moves money.** Every quote in the race is a dry quote (`"dry": true` on 1Click); nothing is signed or deposited. The only transactions Valuo sends are SocialDB writes from the anchor account, and the only ones visitors send are their own forecast writes, approved in their own wallet.
- **The server never holds a visitor key.** Forecasts are signed in the visitor's wallet through NEAR Wallet Selector, with no function-call access key created for the app (`web/src/lib/nearWallet.ts`).
- **The anchor key signs locally and checks itself.** `valuo.anchor publish` builds the transaction in Borsh, signs its SHA-256 with ed25519 through the system `openssl`, verifies the signature before sending, and reads the key from a mode-600 file that never leaves the VPS (`quant/valuo/anchor.py`).
- **Rate limits on every public route** (in memory, per instance): `/api/analyst` 10 questions per IP and 60 overall per minute; `/api/refetch` 20 per IP per 5 minutes; `/api/forecasts` 30 per IP per 5 minutes; `/api/live-benchmark` 60 per IP per 5 minutes; `/api/raw` 300 per IP per 5 minutes. `/api/refetch` only re-issues requests to an allow-list of the recorded hosts, and rebuilds NEAR RPC bodies only when they hash to the recorded request.
- **User-written data is untrusted.** Forecasts read from SocialDB are length-capped, numbers are coerced, malformed entries are dropped and counted, and nothing is rendered as HTML. Text inside analyst context items is passed to the model as data, not instructions.
- **The scheduler cannot hurt its host.** On a shared server the jobs run as an unprivileged `valuo` user inside a systemd scope (`MemoryMax=768M`, low CPU and IO weight); a runaway run is killed instead of competing with other services (`ops/vps/install-shared.sh`).
- **The in-browser reproduce button is off by default** (`VALUO_ALLOW_REPRODUCE`), so a public deployment cannot be made to spawn the pipeline.
- **Tests:** 365 passed, 5 skipped (the skipped ones are live-network tests, run with `VALUO_LIVE_TESTS=1`), `make test`, 2026-11-12.

## What is measured, derived, assumed or simulated

| Measured live (hashed) | Derived, assumed or simulated (labelled as such) |
| --- | --- |
| NEAR supply, protocol config, validators, storage locks, per-epoch issuance (NEAR RPC) | The 10,000-path Monte Carlo and the SOTP value: a model, seeded, not a forecast of price |
| Executable dry quotes from 1Click, Relay, LI.FI and Across | 38 labelled assumptions (discount rate, terminal multiple cap, confidential share target, bear stresses...), each with a range in `IC_MEMO.md` |
| Intents volume, fees, holder revenue (DefiLlama), price (CoinGecko via nearstats) | Confidential share of volume: estimated on-chain from the Confidential Intents Treasury's 24-hour inflow and outflow against 24-hour volume, with a band, while nearstats' split is broken (the 40% registry value is only the fallback if the treasury read fails) |
| Volume growth: trend of 365 days of DefiLlama daily volume, with a Newey-West 90% interval; it replaces the old fixed 30%/yr and its interval becomes the slider range | Growth as the model's *expected* path: the measured value is median trend growth, so using it as the expected growth is conservative |
| Solver and caller concentration from `intents.near` receipts (NearBlocks), with bootstrap 90% confidence intervals | Confidential take rate: an assumption unless a 1Click partner key (`ONECLICK_JWT`) lets the race price confidential quotes |
| Confidential Intents treasury TVL and 30-day net flow (`intents.near` balances) | Bull-case requirements: one input moved at a time until the model equals the market value; each says what that condition alone must deliver |
| Chain Signatures usage, sampled from NearBlocks pages | The backtest: the volume model re-run at past dates on data available then; it under-predicts at 3 and 6 months and says so |
| Snapshot hashes on NEAR (SocialDB) | Forecast scores: a forecast is scored against the latest snapshot price once its horizon has passed |

## Tech stack

Python 3.11+ with `uv`, `httpx`, `pydantic` v2, `numpy`, `scipy`, `duckdb`, `pytest` · Next.js 15.5 (App Router), React 19.1, TypeScript 5, Tailwind CSS 4, hand-rolled SVG charts · NEAR Wallet Selector 10.1 (MyNearWallet, Meteor, HERE, Intear) · NEAR AI Cloud (OpenAI-compatible API, default `deepseek-ai/DeepSeek-V4.1-Flash-1017`) · Data: FastNEAR RPC (mainnet and archival), 1Click, Relay, LI.FI, Across, NearBlocks, nearstats, DefiLlama, CoinGecko, `api.near.social` indexer · Scheduler: cron on Ubuntu 24.04, systemd scopes.

## Run it locally

**Prerequisites:** Python 3.11+ with [uv](https://docs.astral.sh/uv/), Node 20+, `make`, and `openssl` 3 (only for publishing anchors).

```bash
make sync          # cd quant && uv sync
make reproduce     # live mainnet + quote race + forensics -> 10,000-path Monte Carlo -> artifacts/ (about 8 minutes; the scheduled daily run allows a longer Chain Signatures sample and takes about 13)
make test          # unit tests + invariant checks against artifacts/
shasum -a 256 artifacts/latest_snapshot.json   # must equal manifest.json: snapshot_sha256
cd web && npm install && npm run dev            # http://localhost:3000, reads ../artifacts
```

| Command | What it does |
| --- | --- |
| `make reproduce-fast` | smoke run (no quote race, 2,000 paths) into `artifacts/dev/`; never touches the canonical files |
| `make bench-history` | one live quote race into `artifacts/history/bench.jsonl`, raw responses gzipped and hashed |
| `make history-verify` | re-hash every raw payload referenced by the history store |
| `make anchor-verify ANCHOR=<account>` | compare your `manifest.json` with the hashes anchored on NEAR (no key) |
| `make anchor-list ANCHOR=<account>` | list every anchored snapshot and its write block |
| `make falsification-check ANCHOR=<account>` | per-trigger 30-day streak status and the falsification write it would send (dry run, no key) |
| `make falsification-list ANCHOR=<account>` | read back `valuo/falsification/*` and recompute each streak from local history (no key) |

Everything works without a `.env`. Copy `.env.example` to `.env` at the repo root to change anything:

| Variable | What it does | Default / when unset |
| --- | --- | --- |
| `NEAR_RPC_URL`, `NEAR_RPC_FALLBACK_URL`, `NEAR_ARCHIVAL_RPC_URL` | NEAR RPC endpoints | FastNEAR free RPC, then `rpc.mainnet.near.org`; FastNEAR archival |
| `ONECLICK_JWT` | 1Click partner token; enables the confidential-quote check | unset: confidential take stays a labelled assumption |
| `NEARBLOCKS_API_KEY` | raises NearBlocks rate limits | unset: calls are spaced to the free tier |
| `VALUO_MC_SEED`, `VALUO_MC_PATHS`, `VALUO_HORIZON_MONTHS` | Monte Carlo settings | `20261114`, `10000`, `36` |
| `VALUO_ARTIFACTS_DIR` | where artifacts are written and read | `<repo>/artifacts` |
| `NEAR_AI_API_KEY` | server-side key for the analyst | unset: the analyst says NEAR AI is not configured and answers nothing |
| `NEAR_AI_MODEL` | analyst model id | `deepseek-ai/DeepSeek-V4.1-Flash-1017` |
| `VALUO_ALLOW_REPRODUCE` | enables the in-browser reproduce button | `0` (off) |
| `VALUO_ANCHOR_ACCOUNT` | scheduler only: NEAR account that anchors snapshots | unset: no anchoring |

**Test status (2026-11-12):**

```
365 passed, 5 skipped
```

## Deploying

1. **Web.** Import the repository into Vercel with **Root Directory** `web`. The `prebuild` step copies `../artifacts` into `web/.valuo-data`, so the deployed site serves the committed snapshot. Set `NEAR_AI_API_KEY` as an environment variable for the analyst; leave `VALUO_ALLOW_REPRODUCE` unset. With Vercel's Git integration on, each data commit the scheduler pushes redeploys the site.
2. **Scheduler.** On a Debian or Ubuntu server, follow [docs/VPS.md](docs/VPS.md): a job user with a GitHub deploy key, `make sync`, then `ops/vps/setup.sh` (dedicated server) or `ops/vps/install-shared.sh` (server shared with other services). It installs `5 6 * * *` (daily snapshot) and `23 * * * *` (hourly quote race), UTC.
3. **Anchoring (optional).** Fund a NEAR account (an implicit account works), put its key in `~/.near-credentials/mainnet/<account>.json` on the VPS, and re-run the installer with `VALUO_ANCHOR_ACCOUNT=<account>`. Each anchor attaches about 0.01 NEAR for SocialDB storage.
4. **First live runs.** The hourly race first ran and pushed on its own at 2026-11-10 12:23 UTC. The first anchor is transaction [`6ZPRJLh8…`](https://nearblocks.io/txns/6ZPRJLh8mCBTBZXquqA4WFP5mL384u3z3dbNqXt5vwhk) (block 223,914,397).

## Repository map

```
Valuo/
├── README.md, JUDGES.md          this file; the judges' claim-by-claim checklist
├── Makefile                      reproduce, test, history, anchor targets
├── .env.example                  every optional setting, all key-free by default
├── artifacts/                    written by quant, read by web
│   ├── latest_snapshot.json      the canonical dataset
│   ├── manifest.json             SHA-256 of every raw payload and of the snapshot
│   ├── IC_MEMO.md                the generated Investment Committee memo
│   ├── raw/                      exact response bytes behind every number
│   └── history/                  daily snapshots and hourly quote races
├── quant/
│   ├── valuo/collectors/         near_rpc, execution_bench, intents_forensics,
│   │                             confidential_boundary, comps, chain_signatures
│   ├── valuo/models/             supply_physics, sotp_valuation, bear_case, bull_case,
│   │                             market_implied, sensitivity, relative_value, backtest
│   ├── valuo/provenance.py       fetch, hash and record every response
│   ├── valuo/assumptions.py      the labelled assumption registry with ranges
│   ├── valuo/anchor.py           SocialDB anchoring: build, sign, send, verify
│   ├── valuo/history.py          the time-series store
│   ├── valuo/memo_generator.py   IC_MEMO.md and the README findings block
│   ├── valuo/reproduce.py        the one-command pipeline
│   └── tests/                    unit tests and invariants
├── web/src/
│   ├── app/                      / (landing), /terminal, api/ (snapshot, raw, refetch,
│   │                             live-benchmark, forecasts, analyst, reproduce)
│   ├── components/               landing, tab1..tab6 sections, analyst, provenance, ui
│   └── lib/                      snapshot loading, verification, forecasts, wallet, analyst
├── ops/vps/                      valuo-run.sh, valuo.crontab, setup.sh, install-shared.sh
└── docs/                         MODEL_DESIGN.md, LIVE_ENDPOINT_FACTS.md, VPS.md
```

`QUANT_PIPELINE_SPEC.md` and `TERMINAL_UI_SPEC.md` are the original pre-build briefs, kept for the record; where they differ from the artifacts, the artifacts are right.

## Pre-existing work and credits

- **No prior Valuo code.** Everything in `quant/` and `web/` was written for this hackathon.
- **Libraries:** Next.js and React, NEAR Wallet Selector (wallet signing), the Python scientific stack (numpy, scipy), pydantic, httpx, DuckDB.
- **Reference material:** NEAR's public agent skills (`github.com/near/agent-skills`) were read during the build; they are not part of this repository.
- **Data and APIs:** NEAR mainnet RPC (FastNEAR), NEAR Intents 1Click, Relay, LI.FI, Across, NearBlocks, nearstats.org, DefiLlama, CoinGecko, the NEAR Social indexer, NEAR AI Cloud. Third-party figures are shown as reported by those sources and hashed as received.
- **Contracts:** Valuo deploys none. It writes to the existing `social.near` (SocialDB) contract and reads `intents.near` and `v1.signer`.

## License

[MIT](LICENSE).

---

*Valuo is research software. Nothing here is investment advice; model outputs are not price targets, and every assumption is labelled with its range.*
