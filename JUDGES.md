# Valuo: a guide for judges and AI auditors

This file maps every claim Valuo makes to the one command or click that checks it. It contains no numbers on purpose: the figures live in `artifacts/latest_snapshot.json`, regenerate on every run, and would make this file stale. Each check below prints the current value from the snapshot or re-derives it from live sources.

Track: `[ 02 / INV ] Investment Thesis`, judged on evidence, not conviction.

---

## 1. Reproduce everything (about 2 minutes, no API keys)

```bash
make sync          # Python env via uv (quant/.venv)
make reproduce     # live NEAR RPC, quote race, NearBlocks / nearstats / DefiLlama -> models -> artifacts/
make test          # offline unit tests + invariant checks against the new artifacts
shasum -a 256 artifacts/latest_snapshot.json    # must equal manifest.json: snapshot_sha256
```

`make reproduce` rewrites `artifacts/latest_snapshot.json`, `manifest.json`, `IC_MEMO.md`, `raw/` and the findings block in `README.md`. Your numbers will differ from the committed ones by however much the chain and the markets moved; the method, seed (`20261114`) and path count (10,000) are fixed.

Faster smoke run that never touches the committed files: `make reproduce-fast` (writes `artifacts/dev/`).

## 2. Check provenance without trusting us

| What | How |
| :--- | :--- |
| Every raw payload is hashed | `artifacts/manifest.json` lists source, URL, method, SHA-256, size and fetch time for each response; the bodies are in `artifacts/raw/`. |
| Hashes match the stored bytes | From the repo root: `python3 -c "import json,hashlib;m=json.load(open('artifacts/manifest.json'));r=[x for x in m['records'] if x.get('raw_path')];bad=[x['name'] for x in r if hashlib.sha256(open(x['raw_path'],'rb').read()).hexdigest()!=x['sha256']];print(len(r)-len(bad),'of',len(r),'match',bad)"` |
| Same check, in your browser | Open `/terminal?verify=rehash`. The drawer re-hashes every stored payload with `crypto.subtle` and reports "N of N payloads match". |
| The source still says what we recorded | In the same drawer, "Fetch live and compare" re-issues a recorded GET or NEAR RPC request and lists the fields that changed since the snapshot. |
| Quote race history | `make history-verify` re-hashes every payload saved by the hourly quote races in `artifacts/history/raw/`. |

## 3. Claim-by-claim verification

Every graded claim is in `evidence_scorecard` with its grade, value, source record and confidence: `python3 -c "import json;[print(c['status'],'|',c['claim']) for c in json.load(open('artifacts/latest_snapshot.json'))['evidence_scorecard']]"`. Grades: VERIFIED_ON_CHAIN > VERIFIED_LIVE_API > DERIVED > ASSUMPTION; NOT_SUPPORTED claims stay on the list.

| Claim | Snapshot field | Independent check |
| :--- | :--- | :--- |
| Realized issuance is measured from total-supply jumps at epoch boundaries, not assumed from the 2.5% cap | `near_rpc.epoch_issuance` | `curl -s -X POST https://free.rpc.fastnear.com -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"block","params":{"block_id":<epoch_start_height>}}'` and its predecessor; the difference in `header.total_supply` is the mint. |
| NEP storage staking locks NEAR on `intents.near` (1 NEAR per 100 KB) | `near_rpc.tracked_sinks[]`, `near_rpc.storage_near_per_kb` | `view_account` on `intents.near` (`storage_usage` × `storage_amount_per_byte` from `EXPERIMENTAL_protocol_config`). |
| 1Click out-delivers the best competitor on cross-VM routes, and trails on native BTC and EVM L2 | `execution_bench.results[]`, `headroom_by_archetype_bps` | Terminal, tab 02, "Run live quote race": the same dry quotes, fired from your browser session, compared on destination units. Or `make bench`. |
| Take rate, capture ratio and volume on one aligned 30-day window | `intents_forensics.fees`, `intents_forensics.volume` | `curl -s https://api.llama.fi/summary/fees/near-intents?dataType=dailyFees` (and `dailyRevenue`, `dailyHoldersRevenue`); the window dates are in `fees.take_rate_window`. |
| Confidential share of volume | `intents_forensics.volume.confidential_share_status` | If the status is `implausible_fallback`, the nearstats split was rejected (cumulative confidential volume reported as zero while confidential TVL is non-zero) and the model uses the labelled 40% registry assumption; the claim is graded ASSUMPTION, not VERIFIED. Check `curl -s https://nearstats.org/api/near/summary` → `intents.totalsBreakdown`. |
| Solver concentration (the cartelization trigger) | `intents_forensics.solver_concentration` (`hhi_solver`, `hhi_solver_ci90`, `sample_span_s`) | The trigger is graded only when the sample spans at least `solver_sample_min_span_s` (in `assumptions[]`); otherwise it reads "inconclusive". Raw pages: `nearblocks` records in the manifest. |
| What NEAR's market value requires | `market_implied.solves[]` | Each solve reports `check_rel_error`: plugging the required value back into the model reproduces the market FDV. `cd quant && uv run python -m valuo.models.market_implied ../artifacts/latest_snapshot.json` recomputes it. |
| Which assumptions move the valuation | `sensitivity.rows[]` | `uv run python -m valuo.models.sensitivity ../artifacts/latest_snapshot.json`; ranges come from the registry (`assumptions[]`, each with low, high and justification) or from measured dispersion. |
| NEAR against peer L1s on fees and revenue | `relative_value.coverage`, `relative_value.peers[]` | `uv run python -m valuo.models.relative_value ../artifacts/latest_snapshot.json`; peer FDVs from CoinGecko, fees from DefiLlama, both in the manifest. Only 3 peers: medians are fragile, and the output says so. |
| Monte Carlo is reproducible | `sotp.fdv_percentiles`, `run_config` | `make test` includes a seeded re-run check; the same seed and inputs give identical percentiles. |
| Bear case: four falsification scenarios with live triggers | `bear_case.scenarios[]` (`trigger_status`, `current_value`, `trigger_threshold`, `monitor_source`) | Each trigger names its live source URL and threshold; the IC memo section "Bear case" states the 30-consecutive-day falsification rule. |

## 4. Where the thesis is weak (read before scoring)

We list these ourselves; none of them is hidden in the UI or the memo.

- The model values only NEAR Intents cash flow plus two assumption-heavy engines; the market prices NEAR as a layer 1. `market_implied` quantifies the gap instead of explaining it away.
- The terminal multiple is capped at 60× (`assumptions[]`, `terminal_multiple_cap`); the raw peer median is far higher and shown next to it.
- The confidential share is an assumption whenever nearstats' split fails its plausibility check (status in the snapshot). Engine 2 depends on it.
- Native BTC: 1Click does not out-deliver Relay on the corridors we sample; the claim is graded NOT_SUPPORTED.
- Peer set for relative value is three chains.
- NearBlocks' free tier limits the solver sample; its span and confidence interval are reported, and the trigger reads "inconclusive" below the minimum span.
- Daily and hourly history begins when the GitHub Actions start running; early series have few points, and the History tab says so.

## 5. Where things are

| Path | What |
| :--- | :--- |
| `artifacts/latest_snapshot.json` | Every number the UI and memo show. |
| `artifacts/manifest.json`, `artifacts/raw/` | SHA-256 of every raw response, and the responses. |
| `artifacts/IC_MEMO.md` | The investment-committee memo, rendered from the snapshot. |
| `artifacts/history/` | Daily snapshot and hourly quote-race time series (`summary.json`, JSONL, raw payloads). |
| `quant/valuo/collectors/` | Live fetchers: NEAR RPC, quote race, Intents forensics, peer comps. |
| `quant/valuo/models/` | Supply physics, SOTP + Monte Carlo, bear case, market-implied, sensitivity, relative value. |
| `quant/valuo/assumptions.py` | Every assumption with its value, range and justification. |
| `quant/tests/` | Unit tests and invariant checks (`make test`). |
| `web/` | Next.js terminal; it only reads `artifacts/`. |
| `docs/MODEL_DESIGN.md` | Field contract and modelling decisions. |
| `.github/workflows/` | Daily canonical run and hourly quote race. |
