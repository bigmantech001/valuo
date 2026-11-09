import type { Corridor, CorridorArchetype, CorridorLeg, VenueName } from "./types";

/**
 * The three benchmark corridors. Ids, labels, archetypes, venue order and every venue parameter
 * mirror `quant/valuo/collectors/execution_bench.py` (CORRIDORS, RELAY_*, ACROSS_CHAIN_SOLANA) so
 * the live browser race and the reproducible snapshot measure the same thing.
 *
 * Every identifier below was verified live (docs/LIVE_ENDPOINT_FACTS.md sections 2-3, plus the
 * Across `/api/chains` and Relay `/chains` lists probed 2026-10-31):
 *  - 1Click asset ids are the Defuse/Omni `nep141:...` ids from `GET /v0/tokens`.
 *  - Relay chain ids: Ethereum 1, Base 8453, Arbitrum 42161, Solana 792703809, Bitcoin 8253038;
 *    Relay's native-BTC currency id is `bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqmql8k8` (any other
 *    placeholder returns INVALID_INPUT_CURRENCY).
 *  - LI.FI chain keys: ETH, SOL, BTC, BAS (Base), ARB; token symbols accepted.
 *  - Across chain ids: 1, 8453, 42161; Solana is listed as 34268394551451 with zero enabled
 *    tokens/routes, so `suggested-fees` answers ROUTE_NOT_ENABLED. Across lists no Bitcoin chain.
 *
 * Addresses are only recipients/refund targets for `dry` quotes; nothing is ever sent. The
 * defaults equal `quant/valuo/config.py` (EVM_ADDRESS, SOL_ADDRESS, BTC_ADDRESS) and can be
 * overridden with VALUO_EVM_ADDRESS / VALUO_SOL_ADDRESS / VALUO_BTC_ADDRESS at the repo root.
 */

export const DEFAULT_CLIPS_USD: readonly number[] = [500, 50_000, 250_000];

export const DEFAULT_ADDRESSES = {
  evm: "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
  sol: "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV",
  // BIP173 P2WPKH test vector; the BIP173 *example* address bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq is on
  // Relay's blocklist (BLOCKED_WALLET_ADDRESS). Must equal quant/valuo/config.py BTC_ADDRESS.
  btc: "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4",
} as const;

export type AddressKind = keyof typeof DEFAULT_ADDRESSES;
export type Addresses = Record<AddressKind, string>;

export type ChainVm = "evm" | "svm" | "btc" | "near" | "zec";

/**
 * One side of a corridor as the web defines it. `toCorridorLeg()` turns it into the Python
 * `CorridorLeg` shape (which carries the resolved recipient address and the per-venue ids).
 */
export type ChainLeg = {
  /** 1Click `blockchain` key (eth, sol, btc, base, arb) */
  chain: string;
  chain_label: string;
  vm: ChainVm;
  symbol: string;
  decimals: number;
  /** token contract / mint; null for a native asset such as BTC */
  token_address: string | null;
  is_usd_stable: boolean;
  /** which benchmark address receives funds on this chain */
  address_kind: AddressKind;
};

export interface OneClickParams {
  originAsset: string;
  destinationAsset: string;
}
export interface RelayParams {
  originChainId: number;
  destinationChainId: number;
  originCurrency: string;
  destinationCurrency: string;
}
export interface LifiParams {
  fromChain: string;
  toChain: string;
  fromToken: string;
  toToken: string;
}
export interface AcrossParams {
  originChainId: number;
  destinationChainId: number;
  inputToken: string;
  outputToken: string;
}

export interface CorridorVenues {
  oneclick: OneClickParams;
  relay?: RelayParams;
  lifi?: LifiParams;
  /** absent when Across has no chain for the destination; the benchmark then verifies that live via /api/chains */
  across?: AcrossParams;
}

export interface CorridorDef {
  corridor_id: string;
  label: string;
  archetype: CorridorArchetype;
  origin: ChainLeg;
  destination: ChainLeg;
  /** both legs are the same USD stablecoin: friction can be measured in raw units (no oracle noise) */
  same_asset: boolean;
  /** venues called, in the Python collector's order */
  venues_attempted: VenueName[];
  /** venue -> structural reason it is not quoted (mirrors execution_bench venues_declared_unsupported) */
  venues_declared_unsupported: Partial<Record<VenueName, string>>;
  venues: CorridorVenues;
  /** structural context per venue, surfaced next to `unsupported_route` results */
  venue_notes: Partial<Record<VenueName, string>>;
}

const ETH_USDC = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48";
const BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const ARB_USDC = "0xaf88d065e77c8cC2239327C5EDb3A432268e5831";
const SOL_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v";

export const RELAY_CHAIN_IDS = {
  ethereum: 1,
  base: 8453,
  arbitrum: 42161,
  solana: 792703809,
  bitcoin: 8253038,
} as const;
/** Relay's native-BTC currency id as published by GET https://api.relay.link/chains (chain 8253038, vm "bvm"). */
export const RELAY_NATIVE_BTC_CURRENCY = "bc1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqmql8k8";

export const ACROSS_CHAIN_IDS = {
  ethereum: 1,
  base: 8453,
  arbitrum: 42161,
  solana: 34268394551451,
} as const;

/**
 * Across ids per 1Click chain key, as the Python `_leg()` objects carry them (a leg knows its Across
 * ids whether or not the corridor is Across-quotable; Bitcoin has none). Used by `toCorridorLeg()`.
 */
const ACROSS_LEG_IDS: Record<string, { chainId: number; token: string }> = {
  eth: { chainId: ACROSS_CHAIN_IDS.ethereum, token: ETH_USDC },
  base: { chainId: ACROSS_CHAIN_IDS.base, token: BASE_USDC },
  arb: { chainId: ACROSS_CHAIN_IDS.arbitrum, token: ARB_USDC },
  sol: { chainId: ACROSS_CHAIN_IDS.solana, token: SOL_USDC },
};

const ACROSS_NO_BTC = "Across is EVM-only; no Bitcoin route";

export const CORRIDORS: readonly CorridorDef[] = [
  {
    corridor_id: "eth_usdc_sol_usdc",
    label: "ETH USDC -> SOL USDC",
    archetype: "cross_vm",
    origin: {
      chain: "eth",
      chain_label: "Ethereum",
      vm: "evm",
      symbol: "USDC",
      decimals: 6,
      token_address: ETH_USDC,
      is_usd_stable: true,
      address_kind: "evm",
    },
    destination: {
      chain: "sol",
      chain_label: "Solana",
      vm: "svm",
      symbol: "USDC",
      decimals: 6,
      token_address: SOL_USDC,
      is_usd_stable: true,
      address_kind: "sol",
    },
    same_asset: true,
    venues_attempted: ["1click", "relay", "lifi", "across"],
    venues_declared_unsupported: {},
    venues: {
      oneclick: {
        originAsset: "nep141:eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near",
        destinationAsset: "nep141:sol-5ce3bf3a31af18be40ba30f721101b4341690186.omft.near",
      },
      relay: {
        originChainId: RELAY_CHAIN_IDS.ethereum,
        destinationChainId: RELAY_CHAIN_IDS.solana,
        originCurrency: ETH_USDC,
        destinationCurrency: SOL_USDC,
      },
      lifi: { fromChain: "ETH", toChain: "SOL", fromToken: "USDC", toToken: "USDC" },
      across: {
        originChainId: ACROSS_CHAIN_IDS.ethereum,
        destinationChainId: ACROSS_CHAIN_IDS.solana,
        inputToken: ETH_USDC,
        outputToken: SOL_USDC,
      },
    },
    venue_notes: {
      across:
        "Across lists Solana (chainId 34268394551451) with zero enabled input/output tokens; the EVM-only intent bridge cannot settle this corridor.",
    },
  },
  {
    corridor_id: "eth_usdc_btc",
    label: "ETH USDC -> native BTC",
    archetype: "native_btc",
    origin: {
      chain: "eth",
      chain_label: "Ethereum",
      vm: "evm",
      symbol: "USDC",
      decimals: 6,
      token_address: ETH_USDC,
      is_usd_stable: true,
      address_kind: "evm",
    },
    destination: {
      chain: "btc",
      chain_label: "Bitcoin",
      vm: "btc",
      symbol: "BTC",
      decimals: 8,
      token_address: null,
      is_usd_stable: false,
      address_kind: "btc",
    },
    same_asset: false,
    venues_attempted: ["1click", "lifi", "relay"],
    venues_declared_unsupported: { across: ACROSS_NO_BTC },
    venues: {
      oneclick: {
        originAsset: "nep141:eth-0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48.omft.near",
        destinationAsset: "nep141:btc.omft.near",
      },
      relay: {
        originChainId: RELAY_CHAIN_IDS.ethereum,
        destinationChainId: RELAY_CHAIN_IDS.bitcoin,
        originCurrency: ETH_USDC,
        destinationCurrency: RELAY_NATIVE_BTC_CURRENCY,
      },
      lifi: { fromChain: "ETH", toChain: "BTC", fromToken: "USDC", toToken: "BTC" },
      // no `across`: declared unsupported above; the live race still reads /api/chains to record the absence.
    },
    venue_notes: {
      across: "Across has no Bitcoin chain in /api/chains; a suggested-fees request cannot be formed.",
      relay:
        "Relay quotes native BTC (chain 8253038, currency bc1qqqq...mql8k8) but rejects some public recipient addresses with BLOCKED_WALLET_ADDRESS; set VALUO_BTC_ADDRESS to change the recipient.",
      lifi: "LI.FI's best native-BTC route has been observed to be NEAR Intents itself (tool = \"near\").",
    },
  },
  {
    corridor_id: "base_usdc_arb_usdc",
    label: "Base USDC -> Arbitrum USDC",
    archetype: "evm_l2",
    origin: {
      chain: "base",
      chain_label: "Base",
      vm: "evm",
      symbol: "USDC",
      decimals: 6,
      token_address: BASE_USDC,
      is_usd_stable: true,
      address_kind: "evm",
    },
    destination: {
      chain: "arb",
      chain_label: "Arbitrum",
      vm: "evm",
      symbol: "USDC",
      decimals: 6,
      token_address: ARB_USDC,
      is_usd_stable: true,
      address_kind: "evm",
    },
    same_asset: true,
    venues_attempted: ["1click", "across", "relay", "lifi"],
    venues_declared_unsupported: {},
    venues: {
      oneclick: {
        originAsset: "nep141:base-0x833589fcd6edb6e08f4c7c32d4f71b54bda02913.omft.near",
        destinationAsset: "nep141:arb-0xaf88d065e77c8cc2239327c5edb3a432268e5831.omft.near",
      },
      relay: {
        originChainId: RELAY_CHAIN_IDS.base,
        destinationChainId: RELAY_CHAIN_IDS.arbitrum,
        originCurrency: BASE_USDC,
        destinationCurrency: ARB_USDC,
      },
      lifi: { fromChain: "BAS", toChain: "ARB", fromToken: "USDC", toToken: "USDC" },
      across: {
        originChainId: ACROSS_CHAIN_IDS.base,
        destinationChainId: ACROSS_CHAIN_IDS.arbitrum,
        inputToken: BASE_USDC,
        outputToken: ARB_USDC,
      },
    },
    venue_notes: {},
  },
];

export const CORRIDOR_IDS: readonly string[] = CORRIDORS.map((c) => c.corridor_id);

export function getCorridor(corridorId: string): CorridorDef | null {
  return CORRIDORS.find((c) => c.corridor_id === corridorId) ?? null;
}

export const ARCHETYPE_LABELS: Record<CorridorArchetype, string> = {
  cross_vm: "Cross-VM",
  native_btc: "Native BTC",
  evm_l2: "EVM L2",
  native_zec: "Native ZEC",
};

export const VENUE_LABELS: Record<VenueName, string> = {
  "1click": "NEAR Intents (1Click)",
  relay: "Relay",
  lifi: "LI.FI",
  across: "Across",
};

/**
 * One leg in the Python `execution_bench._leg()` shape: the resolved dry-quote address plus the
 * per-venue identifiers, so a live-race `Corridor` is field-for-field the snapshot's.
 */
export function toCorridorLeg(def: CorridorDef, side: "origin" | "destination", addresses: Addresses = DEFAULT_ADDRESSES): CorridorLeg {
  const leg = def[side];
  const { oneclick, relay, lifi, across } = def.venues;
  const isOrigin = side === "origin";
  const acrossIds = across
    ? { chainId: isOrigin ? across.originChainId : across.destinationChainId, token: isOrigin ? across.inputToken : across.outputToken }
    : ACROSS_LEG_IDS[leg.chain] ?? null;
  return {
    chain: leg.chain,
    symbol: leg.symbol,
    decimals: leg.decimals,
    oneclick_asset_id: isOrigin ? oneclick.originAsset : oneclick.destinationAsset,
    address: addresses[leg.address_kind],
    relay_chain_id: relay ? (isOrigin ? relay.originChainId : relay.destinationChainId) : null,
    relay_currency: relay ? (isOrigin ? relay.originCurrency : relay.destinationCurrency) : null,
    lifi_chain: lifi ? (isOrigin ? lifi.fromChain : lifi.toChain) : leg.chain.toUpperCase(),
    lifi_token: lifi ? (isOrigin ? lifi.fromToken : lifi.toToken) : leg.symbol,
    across_chain_id: acrossIds?.chainId ?? null,
    across_token: acrossIds?.token ?? null,
  };
}

/** The plain `Corridor` shape (what the snapshot stores) for a definition. */
export function toCorridor(def: CorridorDef, addresses: Addresses = DEFAULT_ADDRESSES): Corridor {
  return {
    corridor_id: def.corridor_id,
    label: def.label,
    archetype: def.archetype,
    origin: toCorridorLeg(def, "origin", addresses),
    destination: toCorridorLeg(def, "destination", addresses),
    venues_attempted: [...def.venues_attempted],
    venues_declared_unsupported: { ...def.venues_declared_unsupported },
  };
}

/** USD clip -> raw integer string in the origin token's decimals (USDC: 6). */
export function clipToRawAmount(clipUsd: number, decimals: number): string {
  if (!Number.isFinite(clipUsd) || clipUsd <= 0) throw new Error(`invalid clip ${clipUsd}`);
  // Exact for clips below 9e15 / 10^decimals; the UI caps clips far below that.
  return BigInt(Math.round(clipUsd * 10 ** decimals)).toString();
}
