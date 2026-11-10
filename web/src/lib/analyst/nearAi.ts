import "server-only";
import { createHash, createPublicKey, randomBytes, verify as cryptoVerify } from "node:crypto";
import { serverEnv } from "@/lib/env";
import type { AnalystAttestationSummary, AnalystErrorReason, AnalystSignatureCheck } from "./types";

/**
 * NEAR AI Cloud client for the IC analyst (OpenAI-compatible API at cloud-api.near.ai).
 *
 * - The key comes from NEAR_AI_API_KEY (process env, then repo-root .env via serverEnv). It is
 *   only ever placed in the Authorization header of requests to NEAR_AI_BASE; it is never logged,
 *   returned to the browser, or echoed in an error.
 * - Attestation preflight: GET /v1/attestation/report?model=..&provider=near&signing_algo=ed25519
 *   &nonce=<32 random bytes> (public, no key). We check that the report echoes our nonce and keep
 *   the gateway and model signing keys. We do NOT verify the Intel TDX / NVIDIA quotes themselves
 *   (that needs Intel DCAP collateral); the UI links to cloud.near.ai/verify for that.
 * - Response signature: GET /v1/signature/{chat_id}?model=..&signing_algo=ed25519 (key required).
 *   We recompute sha256 of the exact request bytes we sent and the exact response bytes we
 *   received, check the signed text equals "<req>:<resp>" (gateway) or "<model>:<req>:<resp>"
 *   (provider_tee), check the signer is a key from the preflight report, and verify the ed25519
 *   signature with node:crypto. Docs: https://docs.near.ai/cloud/verification
 */

export const NEAR_AI_BASE = "https://cloud-api.near.ai/v1";
export const NEAR_AI_VERIFY_URL = "https://cloud.near.ai/verify";
export const NEAR_AI_VERIFY_DOCS = "https://docs.near.ai/cloud/verification";
/**
 * Default model: NEAR AI's own deployment of DeepSeek V4.1 Flash (Oct 17 2026 snapshot). Its
 * /v1/models entry is owned_by "nearai" and described as "Served privately from NEAR AI's attested
 * TEE infrastructure", and /v1/attestation/report returns a model attestation for it. Override with
 * NEAR_AI_MODEL (any id from GET https://cloud-api.near.ai/v1/models).
 */
export const DEFAULT_NEAR_AI_MODEL = "deepseek-ai/DeepSeek-V4.1-Flash-1017";
export const NOT_CONFIGURED_MESSAGE = "NEAR AI is not configured on this deployment (set NEAR_AI_API_KEY)";

export interface NearAiConfig {
  key: string | null;
  model: string;
  modelSource: "env" | "default";
}

export function nearAiConfig(): NearAiConfig {
  const key = serverEnv("NEAR_AI_API_KEY") ?? null;
  const envModel = serverEnv("NEAR_AI_MODEL");
  return { key, model: envModel ?? DEFAULT_NEAR_AI_MODEL, modelSource: envModel ? "env" : "default" };
}

export function sha256Hex(bytes: Uint8Array | string): string {
  return createHash("sha256").update(bytes).digest("hex");
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number, outer?: AbortSignal): Promise<Response> {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(new Error("timeout")), timeoutMs);
  const onOuter = () => ctl.abort(outer?.reason);
  outer?.addEventListener("abort", onOuter, { once: true });
  try {
    return await fetch(url, { ...init, signal: ctl.signal, cache: "no-store" });
  } finally {
    clearTimeout(timer);
    outer?.removeEventListener("abort", onOuter);
  }
}

// --------------------------------------------------------------------------- model metadata

interface ModelMeta {
  id: string;
  supported_sampling_parameters?: string[];
  owned_by?: string;
  description?: string;
}
let modelsCache: { at: number; models: ModelMeta[] } | null = null;

/** Public /v1/models entry for `model` (cached 1 h); null when the list cannot be fetched. */
export async function modelMeta(model: string): Promise<ModelMeta | null> {
  if (!modelsCache || Date.now() - modelsCache.at > 3_600_000) {
    try {
      const r = await fetchWithTimeout(`${NEAR_AI_BASE}/models`, { headers: { Accept: "application/json" } }, 8_000);
      if (!r.ok) return null;
      const j = (await r.json()) as { data?: ModelMeta[] };
      modelsCache = { at: Date.now(), models: Array.isArray(j.data) ? j.data : [] };
    } catch {
      return null;
    }
  }
  return modelsCache.models.find((m) => m.id === model) ?? null;
}

// --------------------------------------------------------------------------- attestation preflight

export interface AttestationPreflight extends AnalystAttestationSummary {
  gatewayKey: string | null;
}

const ATTESTATION_TTL_MS = 10 * 60_000;
const attestationCache = new Map<string, { at: number; value: AttestationPreflight }>();

/**
 * Fetch (or reuse, for 10 minutes) the attestation report for `model` with a fresh nonce.
 * Never throws: failures are returned in `error`.
 */
export async function attestationPreflight(model: string): Promise<AttestationPreflight> {
  const hit = attestationCache.get(model);
  if (hit && Date.now() - hit.at < ATTESTATION_TTL_MS && !hit.value.error) return hit.value;
  const nonce = randomBytes(32).toString("hex");
  const qs = new URLSearchParams({ model, provider: "near", signing_algo: "ed25519", nonce, include_tls_fingerprint: "false" });
  const reportUrl = `${NEAR_AI_BASE}/attestation/report?${qs.toString()}`;
  const base: AttestationPreflight = {
    report_url: reportUrl,
    verify_url: NEAR_AI_VERIFY_URL,
    fetched_at_utc: new Date().toISOString(),
    model,
    nonce_bound: false,
    gateway_signing_address: null,
    gateway_signing_algo: null,
    model_signers: [],
    error: null,
    gatewayKey: null,
  };
  try {
    const r = await fetchWithTimeout(reportUrl, { headers: { Accept: "application/json", "x-no-aliasing": "true" } }, 15_000);
    const text = await r.text();
    if (!r.ok) {
      let msg = `HTTP ${r.status}`;
      try {
        const j = JSON.parse(text) as { error?: { message?: string } };
        if (j.error?.message) msg += `: ${j.error.message}`;
      } catch {
        /* non-JSON body */
      }
      return { ...base, error: `attestation report unavailable (${msg})` };
    }
    const j = JSON.parse(text) as {
      gateway_attestation?: { signing_address?: string; signing_algo?: string; request_nonce?: string };
      model_attestations?: { model_name?: string; signing_address?: string; signing_algo?: string; request_nonce?: string }[];
    };
    const g = j.gateway_attestation ?? {};
    const models = (j.model_attestations ?? []).filter((m) => typeof m.signing_address === "string" && typeof m.signing_algo === "string");
    const nonceBound = g.request_nonce === nonce && models.every((m) => m.request_nonce === nonce);
    const value: AttestationPreflight = {
      ...base,
      nonce_bound: nonceBound,
      gateway_signing_address: g.signing_address ?? null,
      gateway_signing_algo: g.signing_algo ?? null,
      gatewayKey: g.signing_address ?? null,
      model_signers: models.map((m) => ({ signing_address: m.signing_address as string, signing_algo: m.signing_algo as string })),
      error: nonceBound ? (models.length ? null : "report carries no model attestation for this model") : "report did not echo the request nonce",
    };
    attestationCache.set(model, { at: Date.now(), value });
    return value;
  } catch (e) {
    return { ...base, error: `attestation report unavailable (${e instanceof Error && e.message === "timeout" ? "timed out" : "network error"})` };
  }
}

/** Public part of the preflight (drops nothing secret today; keeps the wire type exact). */
export function publicAttestation(a: AttestationPreflight): AnalystAttestationSummary {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const { gatewayKey, ...rest } = a;
  return rest;
}

// --------------------------------------------------------------------------- completion errors

export interface UpstreamError {
  status: number;
  reason: AnalystErrorReason;
  error: string;
}

/** Map a non-2xx NEAR AI response to a status/reason/message for the browser. */
export function mapUpstreamError(status: number, bodyText: string, model: string): UpstreamError {
  let type: string | null = null;
  let message: string | null = null;
  try {
    const j = JSON.parse(bodyText) as { error?: { type?: string; message?: string } | string; message?: string };
    if (typeof j.error === "string") message = j.error;
    else if (j.error) {
      type = j.error.type ?? null;
      message = j.error.message ?? null;
    } else if (typeof j.message === "string") message = j.message;
  } catch {
    message = bodyText.slice(0, 300) || null;
  }
  const said = message ? ` NEAR AI said: "${message.slice(0, 300)}"` : "";
  if (type === "no_limit_configured" || status === 402)
    return { status: 402, reason: "no-credits", error: `NEAR AI key is valid but the account has no credits yet.${said}` };
  if (status === 401 || type === "invalid_api_key" || type === "missing_auth_header")
    return { status: 502, reason: "key-rejected", error: `NEAR AI rejected the key (HTTP ${status}).${said}` };
  if (status === 403) return { status: 502, reason: "key-rejected", error: `NEAR AI refused this key for the request (HTTP 403).${said}` };
  if (status === 404 || type === "model_not_found" || /model/i.test(message ?? "") && status === 400)
    return { status: 502, reason: "model-unavailable", error: `NEAR AI cannot serve model ${model} (HTTP ${status}). Set NEAR_AI_MODEL to an id from ${NEAR_AI_BASE}/models.${said}` };
  if (status === 429) return { status: 503, reason: "upstream-rate-limited", error: `NEAR AI is rate limiting this deployment (HTTP 429).${said}` };
  return { status: 502, reason: "upstream-error", error: `NEAR AI returned HTTP ${status}.${said}` };
}

// --------------------------------------------------------------------------- response signature

const ED25519_SPKI_PREFIX = Buffer.from("302a300506032b6570032100", "hex");

function decodeSig(sig: string): Buffer | null {
  const hex = sig.startsWith("0x") ? sig.slice(2) : sig;
  if (/^[0-9a-fA-F]{128}$/.test(hex)) return Buffer.from(hex, "hex");
  try {
    const b = Buffer.from(sig, "base64");
    return b.length === 64 ? b : null;
  } catch {
    return null;
  }
}

function ed25519Verify(publicKeyHex: string, text: string, sig: Buffer): boolean {
  const hex = publicKeyHex.startsWith("0x") ? publicKeyHex.slice(2) : publicKeyHex;
  if (!/^[0-9a-fA-F]{64}$/.test(hex)) return false;
  const key = createPublicKey({ key: Buffer.concat([ED25519_SPKI_PREFIX, Buffer.from(hex, "hex")]), format: "der", type: "spki" });
  return cryptoVerify(null, Buffer.from(text, "utf8"), key, sig);
}

/**
 * Fetch and check the signature NEAR AI recorded for `chatId`. Retries a 404 briefly (the
 * signature is written after the stream ends). Never throws.
 */
export async function checkResponseSignature(opts: {
  key: string;
  model: string;
  chatId: string | null;
  requestSha256: string;
  responseSha256: string;
  attestation: AttestationPreflight | null;
}): Promise<AnalystSignatureCheck> {
  const out: AnalystSignatureCheck = {
    status: "unavailable",
    detail: "",
    signature_kind: null,
    signing_algo: null,
    signing_address: null,
    signer_in_report: null,
    request_sha256: opts.requestSha256,
    response_sha256: opts.responseSha256,
    chat_id: opts.chatId,
  };
  if (!opts.chatId) return { ...out, detail: "NEAR AI returned no completion id, so no signature can be looked up." };
  const url = `${NEAR_AI_BASE}/signature/${encodeURIComponent(opts.chatId)}?${new URLSearchParams({ model: opts.model, signing_algo: "ed25519" }).toString()}`;
  type SigBody = { text?: string; signature?: string; signing_address?: string; signing_algo?: string; signature_kind?: string; error_code?: string; message?: string };
  let body = null as SigBody | null;
  for (let attempt = 0; attempt < 4; attempt++) {
    try {
      const r = await fetchWithTimeout(url, { headers: { Accept: "application/json", Authorization: `Bearer ${opts.key}` } }, 8_000);
      if (r.status === 404) {
        await new Promise((res) => setTimeout(res, 700 * (attempt + 1)));
        continue;
      }
      const text = await r.text();
      if (!r.ok) return { ...out, detail: `Signature lookup failed (HTTP ${r.status}).` };
      body = JSON.parse(text) as SigBody;
      break;
    } catch {
      return { ...out, detail: "Signature lookup failed (network error or timeout)." };
    }
  }
  if (!body) return { ...out, detail: "NEAR AI had no signature recorded for this completion (404 after retries)." };
  if (body.error_code || !body.text || !body.signature) return { ...out, detail: `NEAR AI reported the signature as unavailable${body.message ? `: ${body.message}` : ""}.` };

  const kind = body.signature_kind ?? null;
  const algo = body.signing_algo ?? null;
  const signer = body.signing_address ?? null;
  const res: AnalystSignatureCheck = { ...out, status: "unverified", signature_kind: kind, signing_algo: algo, signing_address: signer };
  if (algo !== "ed25519") return { ...res, detail: `Signature algorithm ${algo ?? "unknown"} is not checked here (only ed25519 is).` };
  const expected = kind === "provider_tee" ? `${opts.model}:${opts.requestSha256}:${opts.responseSha256}` : `${opts.requestSha256}:${opts.responseSha256}`;
  if (body.text !== expected) return { ...res, detail: "The signed text does not match the sha256 of the bytes this server sent and received." };
  const a = opts.attestation;
  let inReport: AnalystSignatureCheck["signer_in_report"] = null;
  if (a && !a.error && signer) {
    if (kind !== "provider_tee" && a.gateway_signing_algo === "ed25519" && a.gateway_signing_address === signer) inReport = "gateway";
    else if (kind === "provider_tee" && a.model_signers.filter((m) => m.signing_algo === "ed25519" && m.signing_address === signer).length === 1) inReport = "model";
  }
  const sig = decodeSig(body.signature);
  if (!sig || !signer) return { ...res, signer_in_report: inReport, detail: "Signature or signer is malformed." };
  let valid = false;
  try {
    valid = ed25519Verify(signer, body.text, sig);
  } catch {
    valid = false;
  }
  if (!valid) return { ...res, signer_in_report: inReport, detail: "The ed25519 signature does not verify." };
  if (!inReport)
    return {
      ...res,
      detail: a?.error ? `Signature verifies, but the attestation preflight failed (${a.error}), so the signer is not tied to attested hardware.` : "Signature verifies, but the signer is not a key from the preflight attestation report.",
    };
  return {
    ...res,
    status: "verified",
    signer_in_report: inReport,
    detail: `ed25519 signature over sha256(request):sha256(response) verifies, and the signer is the ${inReport === "gateway" ? "gateway" : "model"} key in NEAR AI's nonce-bound attestation report.`,
  };
}
