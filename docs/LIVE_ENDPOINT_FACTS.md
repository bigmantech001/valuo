# Live Endpoint Facts — probed 2026-10-30 23:51–23:56 UTC (NEAR block 222,342,342)

Every endpoint below was hit with `curl`, zero API keys. Raw responses are in the session
scratchpad at `/private/tmp/claude-501/-Users-mrnetwork-Valuo/e87b4bcb-b665-4dcf-a0bc-ce3336336123/scratchpad/probes/`
(read them with `python3 -I` if you need exact shapes). Numbers here are **point-in-time** and
must never be hardcoded — collectors re-fetch them. The field paths and quirks are what matter.

Several spec numbers in `CLAUDE.md` / `README.md` are stale or wrong. Where they conflict with this
file, **this file wins**:

| Claim in spec | Live truth | Consequence |
| --- | --- | --- |
| `protocol_reward_rate` = 10% treasury | `[0, 1]` = **0%** (treasury.near gets nothing) | Validator share of issuance is 100%. Read it live. |
| 392 validators | **379** `current_validators`, 593.17M NEAR staked (45.27%) | Read live. |
| `intents.near` 12.96 GB / 129,607 NEAR | **13,135,343,202 bytes → 131,353 NEAR** | Read live; it grows ~28–30 MB/day. |
| 1Click beats Relay/LI.FI everywhere | On ETH→SOL $50K: 1Click 49,989.89 vs Relay 49,984.98 (+1.0 bps for 1Click), LI.FI 49,875 (25 bps fee). On Base→Arb: Across 49,994.99 and Relay 49,994.98 **beat** 1Click 49,989.90 by ~1 bps. $250K ETH→SOL: 1Click returns **"No liquidity available"**. | Report exactly what comes back. The thesis is corridor-specific. |
| Issuance = 1 block/sec nominal | nearcore mints by **elapsed time**: measured 26,160–26,483 NEAR per epoch, epochs last ~7.12 h (~1,230/yr) → ~32.4M NEAR/yr ≈ 2.47% | Measure per-epoch minting from `total_supply` jumps at epoch boundaries. |

---

## 1. NEAR Mainnet JSON-RPC

**Primary** `POST https://free.rpc.fastnear.com` · **Fallback** `POST https://rpc.mainnet.near.org` (both verified 200) ·
**Archival (historical state)** `POST https://archival-rpc.mainnet.fastnear.com` (verified; `archival-rpc.mainnet.near.org` also works).
Body: `{"jsonrpc":"2.0","id":"1","method":<m>,"params":<p>}`. Errors come back as `{"result": ..., "error": {...}}` or `result.error` string for query misses.

### `block` `{"finality":"final"}` or `{"block_id": <height:int>}`
`result.header`: `height` (int), `hash` (str), `prev_hash`, `epoch_id`, `next_epoch_id`, `timestamp` (int, **nanoseconds**),
`timestamp_nanosec` (str), `total_supply` (str yoctoNEAR, e.g. `"1310395407206600716000010989007608"` → divide by 1e24), `gas_price` (str, `"100000000"`),
`chunks_included`. `result.chunks[]` each has `balance_burnt` (str yocto) — per-chunk burned fees for that block.

### `EXPERIMENTAL_protocol_config` `{"finality":"final"}`
`result`: `max_inflation_rate: [1, 40]` (→ 1/40 = 0.025), `protocol_reward_rate: [0, 1]` (→ 0.0 treasury share),
`num_blocks_per_year: 31536000`, `epoch_length: 43200` (blocks), `protocol_version: 86`, `protocol_treasury_account: "treasury.near"`,
`runtime_config.storage_amount_per_byte: "10000000000000000000"` (1e19 yocto = 1e-5 NEAR/byte = 1 NEAR per 100 KB), `chain_id: "mainnet"`,
`min_gas_price`, `gas_price_adjustment_rate`, `block_producer_kickout_threshold`, etc.

### `validators` `[null]`
`result.current_validators[]`: `account_id`, `stake` (str yocto), `is_slashed`, `num_expected_blocks`, `num_produced_blocks`,
`num_expected_chunks`, `num_produced_chunks`, `num_expected_endorsements`, `num_produced_endorsements`, `public_key`, `shards`.
Also `result.epoch_height` (4919), `result.epoch_start_height` (222321137), `current_proposals[]`, `next_validators[]`, `prev_epoch_kickout[]`.
Response is ~400 KB.

### `query` view_account `{"request_type":"view_account","finality":"final","account_id":<id>}` (or `"block_id": <height>` instead of finality)
`result`: `amount` (str yocto), `locked` (str yocto, staked), `storage_usage` (int **bytes**), `code_hash` (`"11111111111111111111111111111111"` = no contract), `block_height`, `block_hash`.
Live values (bytes → NEAR locked = bytes × 1e19 / 1e24 = bytes / 1e5):

| account | storage_usage | locked NEAR | amount NEAR | note |
| --- | ---: | ---: | ---: | --- |
| `intents.near` | 13,135,343,202 | 131,353 | 132,030 | Defuse clearinghouse. Contract. |
| `aurora` | 14,362,483,624 | 143,625 | 144,263 | Aurora EVM. |
| `wrap.near` | 167,737,369 | 1,677 | 34,859,117 | wNEAR vault — balance is user deposits, not a sink. |
| `v1.signer` | 1,201,317 | 12 | 3,160 | MPC coordinator. |
| `escrow.ai.near` | 428 | 0.004 | 1,186 | **Plain account (no contract)**; it is a *caller* of intents.near, not a state sink. |
| `treasury.near` | 357,895 | 3.6 | 1,518 | Protocol treasury (receives 0% currently). |

**Historical state (archival RPC)** — `view_account` with `block_id`: free RPC returns `GARBAGE_COLLECTED_BLOCK` for anything older than ~5 epochs; archival returns full state.
`intents.near` storage_usage: block 215,000,000 → 11,707,918,274; block 221,000,000 → 12,888,180,967; block 222,342,342 → 13,135,343,202.
Use two or three archival points (e.g. now, now − ~7d, now − ~30d in blocks ≈ 151,000 blocks/day at 0.571 s) to **measure** storage growth bytes/day per sink.
Block height ↔ time: use `block` `{"block_id": h}` → `header.timestamp` (ns) rather than assuming block time.

### Measuring realized issuance (verified method)
Epoch boundaries: `validators.epoch_start_height` = first block of current epoch E. Fetch `block` at `epoch_start_height` and `epoch_start_height − 1`:
`total_supply` jumps by the **epoch reward minted** (e.g. 222,321,136 → 222,321,137: +26,483.40 NEAR). The previous epoch's start is ≈ `epoch_start_height − 43200`
(verify by `header.epoch_id` change; heights can be skipped, so if `block` errors, step ±1..±5). Measured: +26,160.56 at 222,277,937; +25,829.83 at 222,234,737.
Epoch wall time = Δ`timestamp` between consecutive epoch-start blocks ≈ 7.12 h. Within-epoch supply drift (start→next start, excluding the jump) is the **net gas burn** (≈ −297 NEAR/epoch).
Nominal formula for cross-check: annual issuance = `max_inflation_rate × total_supply` (nearcore scales reward by epoch *duration* in ns / ns-per-year, so 2.5%/yr holds regardless of block time).

---

## 2. NEAR Intents 1Click API

### `GET https://1click.chaindefuser.com/v0/tokens` → JSON array (210 tokens, 38 blockchains)
Each: `assetId`, `decimals`, `blockchain` (`eth`,`sol`,`btc`,`base`,`arb`,`near`,`zec`,`hypercore`,`tron`,`sui`,…), `symbol`, `price` (float USD), `priceUpdatedAt`, `contractAddress`, `coingeckoId`.
Verified asset IDs:
- ETH USDC `nep141:eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near` (6 dp)
- SOL USDC `nep141:sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near` (6 dp)
- Base USDC `nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near` (6 dp)
- Arbitrum USDC `nep141:arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near` (6 dp)
- Native BTC `nep141:btc.omft.near` (8 dp, price 77,238) · Native ZEC `nep141:zec.omft.near` (8 dp) · Native SOL `nep141:sol.omft.near` (9 dp) · Native ETH `nep141:eth.omft.near` (18 dp) · wNEAR `nep141:wrap.near` (24 dp, 4.31)
- NEAR-native USDC `nep141:17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1`

### `POST https://1click.chaindefuser.com/v0/quote` (dry)
```json
{"dry": true, "swapType": "EXACT_INPUT", "slippageTolerance": 100,
 "originAsset": "<assetId>", "depositType": "ORIGIN_CHAIN", "destinationAsset": "<assetId>",
 "amount": "<raw int string>", "refundTo": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "refundType": "ORIGIN_CHAIN",
 "recipient": "<dest-chain address>", "recipientType": "DESTINATION_CHAIN", "deadline": "<ISO-8601 UTC, now+2h, e.g. 2026-10-31T01:52:16.000Z>"}
```
Success → `{"quote": {...}, "quoteRequest": {...}, "signature", "timestamp", "correlationId"}` with `quote`:
`amountIn`, `amountInFormatted`, `amountInUsd` (str), `minAmountIn`, `amountOut` (str raw), `amountOutFormatted` (str), `amountOutUsd` (str), `minAmountOut`,
`timeEstimate` (int **seconds**), `refundFee`, `withdrawFee` (str raw units of dest asset). `quoteRequest.appFees: [{"recipient": ..., "fee": 1}]` (fee in bps),
`quoteRequest.confidentiality: "public"`.
Failure → HTTP 4xx with `{"message": "No liquidity available" | "recipient is not valid" | ..., "correlationId", "timestamp", "path"}`. **Record `message` verbatim as the venue status.**
Recipients that validated: Solana `7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV`, BTC bech32 `bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq`, EVM `0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045`.
ZEC transparent `t1…` address was **rejected** ("recipient is not valid") — treat the ZEC corridor as optional/best-effort.
Observed quotes ($ in USDC):

| corridor | clip | amountOut | amountOutUsd | timeEstimate |
| --- | ---: | ---: | ---: | ---: |
| ETH USDC → SOL USDC | $500 | 499.901775 | 499.80 | 42 s |
| ETH USDC → SOL USDC | $50,000 | 49,989.890495 | 49,980.29 | 42 s |
| ETH USDC → SOL USDC | $250,000 | — | `No liquidity available` | — |
| ETH USDC → native BTC | $50,000 | 0.64637909 BTC | 49,922.44 | 490 s |
| Base USDC → Arb USDC | $50,000 | 49,989.895220 | 49,980.20 | 34 s |

Friction (bps) must be computed on **USD-normalized** legs for cross-asset corridors: `(amountInUsd − amountOutUsd)/amountInUsd × 1e4`
(for same-asset stablecoin corridors raw units are fine and avoid oracle noise; store both).

---

## 3. Competitor routers

### Relay `POST https://api.relay.link/quote`
```json
{"user": "0xd8dA…6045", "originChainId": 1, "destinationChainId": 792703809, "originCurrency": "0xa0b8…eb48",
 "destinationCurrency": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v", "recipient": "7EcD…LtV", "tradeType": "EXACT_INPUT", "amount": "50000000000"}
```
Chain IDs: Ethereum `1`, Base `8453`, Arbitrum `42161`, Solana `792703809`, **Bitcoin `8253038`** (`GET https://api.relay.link/chains` → `{id: 8253038, name: "bitcoin", vmType: "bvm", currency: {address: "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqmql8k8", symbol: "BTC", decimals: 8}}`).
Base USDC `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`, Arb USDC `0xaf88d065e77c8cC2239327C5EDb3A432268e5831`, native BTC = the `currency.address` above (`execution_bench.RELAY_NATIVE_BTC`, `corridors.ts RELAY_NATIVE_BTC_CURRENCY`).
Success → `details.currencyOut.{amount, amountFormatted, amountUsd, minimumAmount}`, `details.currencyIn.amountUsd`, `details.timeEstimate` (int seconds),
`details.totalImpact.{usd, percent}`, `details.swapImpact`, `fees.{gas, relayer, relayerGas, relayerService, app}` each with `amountUsd`, `steps[]`.
Observed: ETH→SOL $50K → 49,984.979876 (24 s, impact −0.03%); Base→Arb $50K → 49,994.977312 (1 s, −0.01%);
ETH USDC→native BTC $50K (2026-11-01 06:48 UTC, recipient `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4`) → **0.64084014 BTC, 24 s** vs 1Click 0.64037955 BTC (490 s) and LI.FI 0.63970344 BTC (`tool: "near"`, 1390 s):
on physical output units Relay delivered 7.2 bps *more* BTC than 1Click, while the venues' own USD marks disagreed by ~25 bps — compare output units, never USD legs, on cross-asset corridors.
Failure → HTTP 400 `{"message": ..., "errorCode": ..., "requestId"}`; record `errorCode`.
**Correction to the first probe (2026-10-31):** the `{"message": "Invalid input or output currency", "errorCode": "INVALID_INPUT_CURRENCY"}` returned for native BTC was caused by the placeholder *currency id* we sent, not by the route.
Relay quotes native BTC when `destinationChainId: 8253038` and `destinationCurrency: "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqmql8k8"`. A message-only variant exists: a wrong currency id on chain 8253038 returns
`{"message":"Invalid output currency","requestId":...}` with **no `errorCode`** (classified `error`, not `unsupported_route`, because only `errorCode` is mapped).
The BIP173 *example* address `bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq` (which §2 shows validating on 1Click) is on **Relay's blocklist**:
`{"message":"This address is blocked and cannot be used for transactions","errorCode":"BLOCKED_WALLET_ADDRESS","requestId":...}` → classified `error` (a recipient problem, not a route fact).
Use the BIP173 P2WPKH test vector `bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4` (`config.BTC_ADDRESS` = `corridors.ts DEFAULT_ADDRESSES.btc`, override `VALUO_BTC_ADDRESS`); it validates on 1Click, Relay and LI.FI.
Status mapping (`execution_bench.RELAY_*`, mirrored in `liveBenchmark.ts`): `INVALID_INPUT_CURRENCY`, `INVALID_OUTPUT_CURRENCY`, `UNSUPPORTED_CHAIN`, `UNSUPPORTED_CURRENCY`, `UNSUPPORTED_ROUTE`, `NO_SWAP_ROUTES_FOUND`, `NO_INTERNAL_SWAP_ROUTES_FOUND`, `ROUTE_TEMPORARILY_RESTRICTED` → `unsupported_route`;
`INSUFFICIENT_LIQUIDITY`, `SWAP_IMPACT_TOO_HIGH`, `NO_QUOTES` → `no_liquidity`; anything else (incl. `BLOCKED_WALLET_ADDRESS`, message-only bodies) → `error`.

### LI.FI `GET https://li.quest/v1/quote?fromChain=ETH&toChain=SOL&fromToken=USDC&toToken=USDC&fromAmount=50000000000&fromAddress=0xd8dA…6045&toAddress=7EcD…LtV`
Chain keys: `ETH`, `SOL`, `BTC`, `BAS` (Base), `ARB`. Token symbols accepted (`USDC`, `BTC`).
Success → top-level `tool` (str, e.g. `"polymerStandard"`, **`"near"`** — LI.FI's best native-BTC route *is* NEAR Intents), `toolDetails.name`,
`estimate.{toAmount, toAmountMin, fromAmount, executionDuration (seconds), fromAmountUSD, toAmountUSD, feeCosts[], gasCosts[]}`, `action.{fromToken, toToken}` with `decimals`.
`feeCosts[]` has `name` ("LIFI Fixed Fee"), `amount`, `amountUSD`, `percentage`, `included`. `gasCosts[].amountUSD`.
Observed: ETH→SOL $50K → 49,875.000000 (25 bps LI.FI fee, 1080 s, polymerStandard); ETH→BTC $50K → 0.64540895 BTC via `tool: "near"` (1390 s);
Base→Arb $50K → 49,875.000000 (1080 s, polymerStandard). Failure → 4xx JSON with `message`.

### Across `GET https://app.across.to/api/suggested-fees?inputToken=<addr>&outputToken=<addr>&originChainId=8453&destinationChainId=42161&amount=50000000000`
Success → `outputAmount` (str raw), `totalRelayFee.{pct, total}`, `relayerCapitalFee`, `relayerGasFee`, `lpFee`, `estimatedFillTimeSec` (int), `isAmountTooLow`, `limits.{minDeposit, maxDeposit, maxDepositInstant}`, `quoteBlock`, `timestamp`, `exclusiveRelayer`.
Observed Base→Arb: $50K → 49,994.992014 (1 s); $500 → 499.942025 (2 s). `pct` fields are 1e18-scaled (`100159720000000` = 1.0016 bps). Across returns **no USD legs**; USD friction must come from a common oracle (the 1Click token list), raw USDC→USDC friction is exact.
Chain list `GET https://app.across.to/api/chains` (22 chains on 2026-11-01: Ethereum, MegaETH, Optimism, Polygon, Arbitrum, Avalanche, zkSync, Base, Linea, World Chain, Ink, Soneium, Unichain, BNB Smart Chain, Solana, HyperEVM, Plasma, Monad, Tempo, TRON, Robinhood, ARC): each `{chainId, name, spokePool, inputTokens[], outputTokens[], ...}`.
**Solana is listed as `chainId: 34268394551451`** (`execution_bench.ACROSS_CHAIN_SOLANA`, `corridors.ts ACROSS_CHAIN_IDS.solana`) with `inputTokens: []` and `outputTokens: []`, so
ETH USDC→SOL USDC `suggested-fees?...&destinationChainId=34268394551451&outputToken=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v` → HTTP 400 `{"type":"AcrossApiError","code":"ROUTE_NOT_ENABLED","status":400,"message":"Route is not enabled.","id":...}`.
**`INVALID_PARAM` variant:** an `outputToken` that is not an enabled token on the destination chain — e.g. an EVM-hex address on chain 34268394551451, or any token on a `destinationChainId` Across does not list (`8253038`, Relay's Bitcoin id) — returns
HTTP 400 `{"type":"AcrossApiError","code":"INVALID_PARAM","status":400,"message":"Unsupported token address on given destination chain","param":"outputTokenAddress","id":...}`.
**No Bitcoin chain is listed**, so an ETH USDC→native BTC request cannot be formed; the quant collector declares Across unsupported for that corridor without HTTP, and the web live race records the `/api/chains` body as the evidence.
Status mapping: `AMOUNT_TOO_HIGH` → `no_liquidity`; web live race (`liveBenchmark.ts`): any other 4xx carrying a `code` (`ROUTE_NOT_ENABLED`, `INVALID_PARAM`, `UNSUPPORTED_CHAIN`, `UNSUPPORTED_TOKEN`) → `unsupported_route` with `supported=false` and `error_code` recorded;
quant collector (`execution_bench.ACROSS_ROUTE_ERROR_CODES`) maps only `ROUTE_NOT_ENABLED` / `UNSUPPORTED_CHAIN` / `UNSUPPORTED_TOKEN` to `unsupported_route` and other codes (incl. `INVALID_PARAM`) to `error`. 2xx with `isAmountTooLow: true` → `error` (`AMOUNT_TOO_LOW`).

---

## 4. NearStats

### `GET https://nearstats.org/api/near/summary` (~86 KB)
Top keys: `generatedAt`, `freshness`, `warnings[]`, `sources{}`, `sourceFetchedAt{}`, `sourceHealth{}`, `nearPositioning{}`, `protocol{}`, `intents{}`, `conversion{}`, `price{}`.
- `intents.totals.{allTimeUsd, volume24hUsd, volume7dUsd, volume30dUsd}` (36.68B / 141.7M / 800.5M / 3.893B).
- `intents.totalsBreakdown.{basis: "public+confidential", asOfDate, public{allTimeUsd, volume24hUsd, volume7dUsd, volume30dUsd}, confidential{…}, records{maxDayUsd, maxDayDate, max7dUsd, max30dUsd}, weekOverWeek{days[{date, volumeUsd}], thisWeekUsd, priorWeekUsd, changePct}, checks[{id,status,detail}]}`
  — 30d public 2.357B vs confidential 1.536B (confidential ≈ 39% of 30d volume, derived as NEAR total − public).
- `intents.protocolMetrics.{totalGeneratedFeesUsd (58.34M cumulative), confidentialTvlUsd (144,420,000), confidentialTvlObservation{sourceStatus:"unverified", warnings[]}, uniqueUsers7d (103,102)}` — **confidential TVL is flagged unverified by nearstats itself; carry that flag through.**
- `intents.{observedWindow, recentVolumeUsd, recentSwapCount, successCount, processingCount, sampledUniqueUsers, privacyRoutes{…}, largestSwap24h{…}, topSwaps[{txHash, originSymbol, destinationSymbol, originChain, destinationChain, volumeUsd, referral, affiliates[], signer, status, createdAt}]}` (affiliates include `buybacks.multisignature.near`).
- `price.{currentUsd, change24hPct, sparkline7d[], facts{athUsd, athDate, marketCapUsd, fdvUsd, circulatingSupply, totalSupply, volume24hUsd, priceChangePct{24h,7d,14d,30d,60d,200d,1y}, source:"coingecko"}, performance{24h,7d,1m,3m,ytd,1y,all}, vsBtc{}, vsEth{}, historyDays}`.
- `protocol.{nearPriceUsd, marketCapUsd, circulatingSupply, totalTransactions, tps, avgBlockTimeSeconds (0.5556), nodesOnline, latestBlockHeight, protocolVersion, validatorCount (100 — their own metric; do not use, use RPC)}`.

### `GET https://nearstats.org/api/near/price-history?window=1y`
`{ok, token, window, granularity ("1d"), points[{t (ms), o, h, l, c}], pointCount (365), rangeStart, rangeEnd, highUsd, lowUsd, currentPriceUsd, generatedAt, warning}`.
Default (no window) = 7d @ 30m (337 points). `window=90d` and `window=max` → **HTTP 500 HTML**. Use `1y` for annualized volatility (daily closes → log returns → σ·√365).

---

## 5. NearBlocks

### `GET https://api.nearblocks.io/v1/account/intents.near/txns?per_page=25&page=N` (pages 1–4 verified; cursor pagination also works: `&cursor=<cursor>`)
`{cursor, txns[]}`; each: `id`, `receipt_id`, `predecessor_account_id`, `receiver_account_id`, `receipt_kind` ("ACTION"), `receipt_block`, `receipt_outcome{status, gas_burnt, tokens_burnt}`,
`transaction_hash`, `included_in_block_hash`, `block_timestamp` (str ns), `block{block_height}`, `receipt_conversion_tokens_burnt`,
`actions[{action ("FUNCTION_CALL"|"TRANSFER"|...), method (e.g. "execute_intents","ft_on_transfer","ft_withdraw","ft_resolve_withdraw","ft_transfer","add_public_key", null), deposit, fee, args}]`, `actions_agg{deposit}`, `outcomes{status}`, `outcomes_agg{transaction_fee}`.
Observed predecessor mix (25 rows): `intents.near` 9 (self-receipts), `system` 8 (gas refunds), `escrow.ai.near` 4, `sol-…omft.near` 1 (bridge), `eth-0xdac1…omft.near` 1 (bridge), hex-named account 1 (implicit user), named user 1.
**Classify**: exclude `system`; treat `intents.near`→`intents.near` as internal; `*.omft.near` / `*.omni.hot.tg` = bridge/omni relayers; `escrow.ai.near`, `*.ai.near`, `*.agent.near` = AI/agentic; 64-hex = implicit (user/solver) account; others = named accounts.
Report HHI over **external callers** (excluding `system` and self), and separately the method mix. Pull ≥4 pages (100 receipts) with ~400 ms spacing; NearBlocks rate-limits unauthenticated bursts (optional `NEARBLOCKS_API_KEY` header `Authorization: Bearer`).
Also: `GET /v1/account/intents.near` → `account[0].{created.block_timestamp, amount, block_height}`; `GET /v1/account/intents.near/txns/count` → `txns[0].count` (156,722,083 lifetime receipts);
`GET /v1/stats` → `stats[0].{total_supply, circulating_supply (1.2498B), avg_block_time, gas_price, nodes_online, near_price, market_cap, total_txns, tps}`.
Explorer links: `https://nearblocks.io/txns/<transaction_hash>`, `https://nearblocks.io/address/<account>`, `https://nearblocks.io/blocks/<height>`.

---

## 6. DefiLlama (all verified)

`GET https://api.llama.fi/summary/fees/<slug>` with optional `?dataType=dailyRevenue` | `dailyHoldersRevenue`. Fields: `total24h`, `total7d`, `total30d`, `total1y`, `totalAllTime`, `change_1d`,
`totalDataChart: [[unix_s, usd], …]` (daily), `totalDataChartBreakdown`, `methodology{Fees, Revenue, HoldersRevenue,…}`, `linkedProtocols`, `parentProtocol`, `category`, `chains`, `childProtocols` (hyperliquid).

| slug | dataType | 24h | 30d | 1y | note |
| --- | --- | ---: | ---: | ---: | --- |
| `near-intents` | fees | 199,133 | 6,159,085 | 53,943,410 | "protocol fee + affiliate fee each frontend collects" |
| `near-intents` | dailyRevenue | 99,630 | 2,175,899 | 9,168,005 | "NEAR's net captured revenue … swept into revenue wallets (reconciles with revenue.near.org)" → **this is the buyback-directed flow** |
| `near-intents` | dailyHoldersRevenue | 99,630 | 2,175,899 | 7,397,810 | |
| `near` (chain) | fees | 3,444 | 202,360 | 1,216,606 | gas fees |
| `near` (chain) | dailyRevenue | 2,411 | 141,650 | 852,219 | "70% of every gas fee is permanently burned" |
| `solana` | fees | 564,523 | 23,319,305 | 235,860,363 | |
| `solana` | dailyRevenue | 38,828 | 2,780,947 | 26,330,243 | |
| `ethereum` | fees | 10,955,201 | 18,516,986 | 180,665,094 | |
| `ethereum` | dailyRevenue | 4,118,991 | 7,266,274 | 51,701,977 | |
| `hyperliquid` | fees | 6,356,888 | 83,812,036 | 903,160,487 | parent; `childProtocols[]` |
| `hyperliquid` | dailyRevenue | 4,869,602 | 65,950,297 | 687,027,875 | "99% of fees go to Assistance Fund for buying HYPE" |

`GET https://api.llama.fi/summary/dexs/near-intents` → volume: `total24h` 141,723,823, `total7d` 800,526,050, `total30d` 3,893,483,161, `total1y` 32.79B, `totalAllTime` 35.75B, `totalDataChart` 689 daily points (matches nearstats day-for-day; nearstats check `defillama-daily` passes at 0.00%).
Derived live: gross take = 6.159M / 3.893B = **15.8 bps**; net captured = 2.176M / 3.893B = **5.6 bps**; capture ratio α = 2.176 / 6.159 = **35.3%**.

Prices: `GET https://coins.llama.fi/prices/current/coingecko:near,coingecko:solana,coingecko:ethereum,coingecko:hyperliquid` → `coins{"coingecko:near": {price, symbol, timestamp, confidence}}`.
FDV/market cap (zero-key, rate-limited ~10–30 req/min): `GET https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=near,solana,ethereum,hyperliquid` → array with `id, current_price, market_cap, fully_diluted_valuation, total_supply, circulating_supply, max_supply`.
Observed FDV: NEAR 5.636B, SOL 61.30B, ETH 273.99B, HYPE 85.61B (mcap 21.54B). Fallback for FDV if CoinGecko 429s: nearstats `price.facts.fdvUsd` for NEAR; for peers use `coins.llama.fi` price × a supply figure fetched from `https://api.llama.fi/protocol/<slug>` is unreliable — instead retry CoinGecko with backoff and, failing that, mark peer FDV `null` and exclude from multiples (never invent).
