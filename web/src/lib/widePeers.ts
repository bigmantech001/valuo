/**
 * TypeScript mirror of the `wide_peers` snapshot section written by
 * `quant/valuo/collectors/wide_peers.py`: FDV to annualised 30-day revenue for the top revenue
 * chains that have their own token, the distribution of that multiple, and where NEAR and the
 * model's terminal multiple cap and floor sit in it.
 *
 * Multiples are plain ratios (538 = 538x); percentiles are shares in [0, 1] ("share of peers at or
 * below the value"); USD figures are whole dollars. Revenue is the DefiLlama fees overview
 * (`defillama / overview:fees:dailyRevenue`), FDV is one batched CoinGecko call
 * (`coingecko / coins_markets_wide`). This view is additive: it does not feed the valuation, and
 * `comps` / `relative_value` keep the three-peer set the model uses.
 */

export interface WidePeer {
  /** chain name as DefiLlama reports it */
  chain: string;
  slug: string;
  coingecko_id: string;
  symbol: string | null;
  /** 1 = highest 30-day revenue among DefiLlama chain rows */
  rank_by_revenue: number;
  revenue_30d_usd: number;
  /** revenue_30d_usd x 365 / 30 */
  annualized_revenue_usd: number;
  revenue_1y_usd?: number | null;
  fdv_usd: number;
  market_cap_usd?: number | null;
  fdv_to_revenue: number;
  /** why this row is not a like-for-like L1 gas token (L2, exchange-linked, non-gas revenue); empty when it is */
  flags: string[];
  /** the adapter's own definition of revenue, verbatim */
  revenue_methodology?: string | null;
}

export interface WidePeerDistribution {
  n: number;
  median: number | null;
  p25: number | null;
  p75: number | null;
  iqr: number | null;
  min: number | null;
  max: number | null;
  /** [5th, 95th] percentile of the bootstrapped median */
  median_ci90: [number, number] | null;
  bootstrap?: { seed: number; n_resamples: number; method: string };
}

/** NEAR on the same basis as the peers: its own chain row (L1 gas revenue only) over its CoinGecko FDV. */
export interface WidePeerNear {
  chain: string;
  slug: string;
  coingecko_id: string;
  rank_by_revenue: number | null;
  n_chains_ranked: number;
  revenue_30d_usd: number | null;
  annualized_revenue_usd: number | null;
  fdv_usd: number | null;
  fdv_to_revenue: number | null;
  percentile: number | null;
  n_peers_at_or_below: number | null;
  revenue_methodology?: string | null;
  basis: string;
}

export interface WidePeerModelMember {
  label: string;
  coingecko_id: string;
  revenue_30d_usd: number | null;
  annualized_revenue_usd: number | null;
  fdv_usd: number | null;
  fdv_to_revenue: number | null;
}

/** The Solana / Ethereum / Hyperliquid median the valuation uses, rebuilt from this view's payloads for contrast. */
export interface WidePeerModelThree {
  label: string;
  members: WidePeerModelMember[];
  n: number;
  median_fdv_to_revenue: number | null;
  basis: string;
}

/** The same distribution without the flagged rows. */
export interface WidePeerExFlagged {
  label: string;
  n_peers: number;
  n_flagged_removed: number;
  median: number | null;
  p25: number | null;
  p75: number | null;
  min: number | null;
  max: number | null;
  median_ci90: [number, number] | null;
  cap_percentile: number | null;
  n_peers_at_or_below_cap: number | null;
  near_percentile: number | null;
}

export interface WidePeerExcluded {
  chain: string;
  slug: string;
  rank_by_revenue: number;
  revenue_30d_usd: number;
  coingecko_id: string | null;
  /** no_native_token | unmapped | token_already_counted | no_coingecko_fdv */
  reason_code: string;
  reason: string;
}

export interface WidePeerSource {
  source: string;
  name: string;
  url?: string | null;
  sha256?: string | null;
  raw_path?: string | null;
  fetched_at_utc?: string | null;
  attempts?: number | null;
  [key: string]: unknown;
}

export interface WidePeers {
  status: string;
  basis: string;
  annualization: string;
  n_peers: number;
  n_peers_target: number;
  /** DefiLlama chain rows with 30-day revenue above zero */
  n_chains_ranked: number;
  n_chains_below_cut: number;
  peers: WidePeer[];
  distribution: WidePeerDistribution;
  near: WidePeerNear;
  /** from the run's assumptions registry */
  terminal_multiple_cap: number | null;
  cap_percentile: number | null;
  n_peers_at_or_below_cap: number | null;
  terminal_multiple_floor: number | null;
  floor_percentile: number | null;
  n_peers_at_or_below_floor: number | null;
  percentile_definition: string;
  model_three_peer: WidePeerModelThree;
  ex_flagged: WidePeerExFlagged;
  /** the finding in one sentence, written by the pipeline */
  headline: string;
  /** what it says about the NEAR case and what would overturn it */
  reading: string;
  inclusion_rules: string[];
  excluded: WidePeerExcluded[];
  caveats: string[];
  cap_source?: string | null;
  fetched_at_utc?: string | null;
  sources?: { revenue?: WidePeerSource; fdv?: WidePeerSource };
  elapsed_s?: number | null;
}
