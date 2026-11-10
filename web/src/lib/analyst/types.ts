/**
 * Wire types for POST/GET /api/analyst (the NEAR AI grounded IC analyst). Shared by the route
 * and AnalystPanel. Kept apart from lib/types.ts, which mirrors the Python snapshot schema.
 */

/** A manifest record a context item traces to (subset of RawRecord). */
export interface AnalystRecordRef {
  source: string;
  name: string;
  sha256: string;
  ok: boolean;
}

/** One numbered context item sent to the model. */
export interface AnalystContextItem {
  /** 1-based number the model cites as [n] */
  n: number;
  kind: "snapshot" | "memo";
  /** JSON path inside latest_snapshot.json ("near_rpc.epoch_issuance"), or the memo section heading */
  ref: string;
  /** short human label (path tail, claim text, section title) */
  label: string;
  /** raw payload records behind the item; empty for model outputs and memo prose */
  records: AnalystRecordRef[];
  /** "raw" = traced to manifest records; "model" = computed by the quant engine from snapshot inputs; "memo" = IC_MEMO.md prose */
  basis: "raw" | "model" | "memo";
}

export interface AnalystAttestationSummary {
  /** public report URL (no key); the nonce in it is the one we checked */
  report_url: string;
  verify_url: string;
  fetched_at_utc: string;
  model: string;
  nonce_bound: boolean;
  gateway_signing_address: string | null;
  gateway_signing_algo: string | null;
  model_signers: { signing_address: string; signing_algo: string }[];
  /** why the report is unusable, when it is */
  error: string | null;
}

export interface AnalystSignatureCheck {
  status: "verified" | "unverified" | "unavailable";
  /** plain-language reason, always set */
  detail: string;
  signature_kind: string | null;
  signing_algo: string | null;
  signing_address: string | null;
  /** signer found in the preflight attestation report (gateway or a model attestation) */
  signer_in_report: "gateway" | "model" | null;
  request_sha256: string;
  response_sha256: string;
  chat_id: string | null;
}

export interface AnalystFigureCheck {
  /** numbers found in the answer (citation markers and years excluded) */
  total: number;
  /** of those, numbers that appear verbatim, or as a rounding of a context number, in the context */
  grounded: number;
  ungrounded: string[];
}

/** SSE events streamed by POST /api/analyst (event name = `type`). */
export type AnalystEvent =
  | {
      type: "meta";
      model: string;
      snapshot_sha256: string | null;
      snapshot_generated_at_utc: string;
      block_height: number;
      memo_sha256: string | null;
      items: AnalystContextItem[];
      attestation: AnalystAttestationSummary | null;
    }
  | { type: "delta"; text: string }
  | { type: "reasoning" }
  | {
      type: "done";
      finish_reason: string | null;
      chat_id: string | null;
      cited: number[];
      invalid_citations: number[];
      figure_check: AnalystFigureCheck;
      signature: AnalystSignatureCheck;
      elapsed_ms: number;
    }
  | { type: "error"; reason: AnalystErrorReason; error: string };

export type AnalystErrorReason =
  | "not-configured"
  | "bad-request"
  | "rate-limited"
  | "no-snapshot"
  | "key-rejected"
  | "no-credits"
  | "model-unavailable"
  | "upstream-rate-limited"
  | "upstream-error"
  | "timeout";

/** GET /api/analyst: configuration and grounding status; never includes the key. */
export interface AnalystStatus {
  configured: boolean;
  model: string;
  model_source: "env" | "default";
  /** the not-configured message when configured=false */
  message: string | null;
  snapshot_sha256: string | null;
  snapshot_generated_at_utc: string | null;
  block_height: number | null;
  n_facts: number;
  n_memo_sections: number;
  suggestions: string[];
  max_question_chars: number;
}
