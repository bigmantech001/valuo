"""Provenance layer: every byte that enters the model is fetched here, hashed and recorded.

Contract (docs/MODEL_DESIGN.md section 2):
- ``fetch_json`` / ``fetch_json_sync`` return ``(parsed_json_or_None, RawRecord)``. Non-2xx bodies are
  still hashed, persisted and recorded (``ok=False``, ``error`` = message from the body) and the parsed
  body is returned so callers can read ``message`` / ``errorCode`` (1Click "No liquidity available",
  Relay ``INVALID_INPUT_CURRENCY``, Across ``ROUTE_NOT_ENABLED``).
- Retries with exponential backoff on 429 / 5xx / timeouts / transport errors; never on other 4xx.
- ``near_rpc_call`` tries the primary RPC, then the fallback on transport/5xx failure; a
  ``GARBAGE_COLLECTED_BLOCK`` / ``UNKNOWN_BLOCK`` answer to a ``block_id`` query is retried on the
  archival node and the record's ``source`` becomes ``"near_rpc_archival"``.
- The SHA-256 in each record is over the exact response bytes; ``raw_path`` points at the persisted copy.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from valuo import config
from valuo.schemas import RawRecord

__all__ = [
    "RawRecord", "ProvenanceLedger", "FetchError",
    "fetch_json", "fetch_json_sync", "near_rpc_call", "near_rpc_call_sync",
    "sha256_bytes", "sha256_json", "sha256_file", "canonical_json", "write_raw", "utc_now_iso",
    "is_gc_block_error", "rpc_error_message",
]

EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()
RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})
_MAX_RETRY_AFTER_S = 10.0
_GC_BLOCK_CAUSES = frozenset({"GARBAGE_COLLECTED_BLOCK", "UNKNOWN_BLOCK"})
_GC_BLOCK_TEXT = ("garbage collected", "unknown block", "db not found error: block")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


class FetchError(RuntimeError):
    """Raised only by convenience wrappers that demand success; fetch_json itself never raises."""


# ----------------------------------------------------------------------------- hashing / time
def utc_now_iso() -> str:
    """Current UTC time as ISO-8601 with millisecond precision and a Z suffix."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def sha256_bytes(data: bytes) -> str:
    """Hex SHA-256 of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj: Any) -> bytes:
    """Deterministic JSON encoding (sorted keys, compact separators, UTF-8) used for request-body hashes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_json(obj: Any) -> str:
    """Hex SHA-256 of the canonical JSON encoding of ``obj``."""
    return sha256_bytes(canonical_json(obj))


def sha256_file(path: Path | str, chunk_size: int = 1 << 20) -> str:
    """Hex SHA-256 of a file's bytes (streamed)."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_filename(source: str, name: str) -> str:
    return _SAFE_NAME.sub("_", f"{source}__{name}").strip("_")


def _relative_to_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(config.REPO_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def write_raw(payload: bytes, *, source: str, name: str, raw_dir: Path | None = None, is_json: bool = True) -> str:
    """Persist raw response bytes as ``<raw_dir>/<source>__<name>.json`` and return the path.

    The path is relative to the repo root when the directory is inside it (the manifest convention),
    absolute otherwise. Non-JSON bodies get a ``.txt`` suffix so nobody parses an HTML 500 as data.
    """
    directory = Path(raw_dir) if raw_dir is not None else config.RAW_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_filename(source, name)}{'.json' if is_json else '.txt'}"
    path.write_bytes(payload)
    return _relative_to_repo(path)


# ----------------------------------------------------------------------------- ledger
class ProvenanceLedger:
    """Ordered list of RawRecord plus the warnings collectors raise when a value had to be null."""

    def __init__(self, raw_dir: Path | None = None, *, persist_raw: bool = True) -> None:
        self.records: list[RawRecord] = []
        self.warnings: list[str] = []
        self.raw_dir: Path | None = Path(raw_dir) if raw_dir is not None else config.RAW_DIR
        self.persist_raw: bool = persist_raw and self.raw_dir is not None

    def add(self, record: RawRecord) -> RawRecord:
        self.records.append(record)
        return record

    def warn(self, message: str) -> None:
        """Record a methodology warning (missing live value, fallback used, clipped multiple...)."""
        if message not in self.warnings:
            self.warnings.append(message)

    def by_source(self, source: str) -> list[RawRecord]:
        return [r for r in self.records if r.source == source]

    def get(self, source: str, name: str) -> RawRecord | None:
        """Most recent record for (source, name), or None."""
        for r in reversed(self.records):
            if r.source == source and r.name == name:
                return r
        return None

    def failures(self) -> list[RawRecord]:
        return [r for r in self.records if not r.ok]

    def write_raw(self, payload: bytes, *, source: str, name: str, is_json: bool = True) -> str | None:
        """Persist bytes under this ledger's raw_dir; returns None when persistence is disabled."""
        if not self.persist_raw or self.raw_dir is None or not payload:
            return None
        return write_raw(payload, source=source, name=name, raw_dir=self.raw_dir, is_json=is_json)

    def sources(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for r in self.records:
            counts[r.source] = counts.get(r.source, 0) + 1
        return dict(sorted(counts.items()))

    def summary(self) -> dict[str, Any]:
        """Compact counts for Snapshot.provenance_summary / Manifest."""
        failed = self.failures()
        return {
            "records": len(self.records),
            "ok": len(self.records) - len(failed),
            "failures": len(failed),
            "bytes": sum(r.bytes for r in self.records),
            "sources": self.sources(),
            "failed": [f"{r.source}/{r.name}: {r.error or 'HTTP ' + str(r.http_status)}" for r in failed][:50],
            "warnings": list(self.warnings),
        }

    def records_as_dicts(self) -> list[dict[str, Any]]:
        return [r.model_dump(mode="json") for r in self.records]


# ----------------------------------------------------------------------------- shared request logic
def _default_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    merged = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}
    if headers:
        merged.update(headers)
    return merged


def _extract_error_message(parsed: Any, status: int | None) -> str:
    """Best-effort human message from an error body (1Click/Relay/Across/NearBlocks/RPC shapes)."""
    prefix = f"HTTP {status}" if status is not None else "HTTP ?"
    if isinstance(parsed, dict):
        raw_code = parsed.get("errorCode") or parsed.get("code")
        code = raw_code if isinstance(raw_code, str) else None
        for key in ("message", "msg", "detail", "error", "data"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                text = f"{code}: {value}" if code and code != value else value
                return f"{prefix}: {text}"[:300]
            if isinstance(value, dict):
                inner = value.get("message") or value.get("data") or value.get("error")
                if isinstance(inner, str) and inner.strip():
                    return f"{prefix}: {inner}"[:300]
        if code:
            return f"{prefix}: {code}"
    elif isinstance(parsed, str) and parsed.strip():
        return f"{prefix}: {parsed.strip()}"[:300]
    return prefix


def _parse_body(content: bytes) -> tuple[Any | None, bool]:
    if not content:
        return None, False
    try:
        return json.loads(content), True
    except (ValueError, UnicodeDecodeError):
        return None, False


def _retry_after_seconds(response: httpx.Response, cap_s: float = _MAX_RETRY_AFTER_S) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        return min(float(value), cap_s)
    except ValueError:
        return None


def _backoff_delay(
    attempt: int, backoff: float, response: httpx.Response | None, retry_after_cap_s: float = _MAX_RETRY_AFTER_S,
    transport_backoff: float | None = None,
) -> float:
    """Exponential delay before attempt ``attempt+1``; honours Retry-After on 429 when present (capped).

    After a transport error (``response`` is None) a flat ``transport_backoff`` is used when given, so a
    refused connection waits e.g. 2 s instead of climbing the HTTP 429 ladder.
    """
    if response is None and transport_backoff is not None:
        return float(transport_backoff)
    if response is not None:
        ra = _retry_after_seconds(response, retry_after_cap_s)
        if ra is not None:
            return ra
    return backoff * (2**attempt)


def _transport_budget(retries: int, transport_retries: int | None) -> int:
    """Retries allowed after a transport error (connect refused / timeout); defaults to the HTTP budget.

    Rate-limit ladders (NearBlocks 429) are long on purpose; a refused connection should not pay them,
    so collectors pass a smaller ``transport_retries``.
    """
    return retries if transport_retries is None else max(0, min(int(transport_retries), retries))


def _finish_record(
    *,
    ledger: ProvenanceLedger | None,
    source: str,
    name: str,
    url: str,
    method: str,
    body_sha: str | None,
    response: httpx.Response | None,
    exc: Exception | None,
    started: float,
    attempts: int,
    record_to_ledger: bool,
) -> tuple[Any | None, RawRecord, bytes]:
    """Build the RawRecord for a finished exchange; returns (parsed, record, exact_response_bytes)."""
    latency_ms = (time.perf_counter() - started) * 1000.0
    if response is None:
        record = RawRecord(
            source=source, name=name, url=url, method=method, request_body_sha256=body_sha,
            http_status=None, ok=False, error=f"{type(exc).__name__}: {exc}"[:300] if exc else "no response",
            fetched_at_utc=utc_now_iso(), latency_ms=round(latency_ms, 1), bytes=0, sha256=EMPTY_SHA256,
            raw_path=None, attempts=attempts,
        )
        if ledger is not None and record_to_ledger:
            ledger.add(record)
        return None, record, b""

    content = response.content
    parsed, is_json = _parse_body(content)
    ok = 200 <= response.status_code < 300
    error = None if ok else (_extract_error_message(parsed, response.status_code) if is_json else f"HTTP {response.status_code}: non-JSON body")
    raw_path = ledger.write_raw(content, source=source, name=name, is_json=is_json) if ledger is not None else None
    record = RawRecord(
        source=source, name=name, url=str(response.request.url), method=method, request_body_sha256=body_sha,
        http_status=response.status_code, ok=ok, error=error, fetched_at_utc=utc_now_iso(),
        latency_ms=round(latency_ms, 1), bytes=len(content), sha256=sha256_bytes(content), raw_path=raw_path,
        attempts=attempts,
    )
    if ok and not is_json and content:
        record.error = f"HTTP {response.status_code}: non-JSON body"
        record.ok = False
    if ledger is not None and record_to_ledger:
        ledger.add(record)
    return parsed, record, content


# ----------------------------------------------------------------------------- async fetch
async def _fetch_json_async(
    client: httpx.AsyncClient,
    ledger: ProvenanceLedger | None,
    *,
    source: str,
    name: str,
    method: str,
    url: str,
    json_body: Any | None,
    params: Mapping[str, Any] | None,
    headers: Mapping[str, str] | None,
    timeout: float,
    retries: int,
    backoff: float,
    record_to_ledger: bool,
    transport_retries: int | None = None,
    retry_after_cap_s: float = _MAX_RETRY_AFTER_S,
    retry_once_on: frozenset[int] = frozenset(),
    transport_backoff: float | None = None,
) -> tuple[Any | None, RawRecord, bytes]:
    body_sha = sha256_json(json_body) if json_body is not None else None
    started = time.perf_counter()
    response: httpx.Response | None = None
    last_exc: Exception | None = None
    attempts = 0
    transport_budget = _transport_budget(retries, transport_retries)
    once_used = False
    for attempt in range(max(1, retries + 1)):
        attempts = attempt + 1
        try:
            response = await client.request(
                method.upper(), url, params=params, json=json_body, headers=_default_headers(headers), timeout=timeout,
            )
            last_exc = None
            if response.status_code in retry_once_on and not once_used and attempt < retries:
                once_used = True  # e.g. a Cloudflare 403 challenge on CoinGecko: one more try, not a ladder
            elif response.status_code not in RETRYABLE_STATUS or attempt >= retries:
                break
        except httpx.HTTPError as exc:  # timeouts, connect errors, protocol errors
            response, last_exc = None, exc
            if attempt >= transport_budget:
                break
        await asyncio.sleep(_backoff_delay(attempt, backoff, response, retry_after_cap_s, transport_backoff))
    return _finish_record(
        ledger=ledger, source=source, name=name, url=url, method=method, body_sha=body_sha, response=response,
        exc=last_exc, started=started, attempts=attempts, record_to_ledger=record_to_ledger,
    )


async def fetch_json(
    client: httpx.AsyncClient | None,
    ledger: ProvenanceLedger,
    *,
    source: str,
    name: str,
    method: str,
    url: str,
    json: Any | None = None,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = config.HTTP_TIMEOUT_S,
    retries: int = 3,
    backoff: float = 0.6,
    transport_retries: int | None = None,
    retry_after_cap_s: float = _MAX_RETRY_AFTER_S,
    retry_once_on: frozenset[int] = frozenset(),
    transport_backoff: float | None = None,
) -> tuple[Any | None, RawRecord]:
    """Fetch ``url`` once (with retries), hash the raw bytes, persist them, and record provenance.

    Returns ``(parsed_json, record)``. ``parsed_json`` is None only when no body was received or the
    body was not JSON; for non-2xx JSON bodies it is the parsed error payload and ``record.ok`` is
    False. ``retries`` is the number of additional attempts after the first (3 -> at most 4 requests),
    taken only on 408/425/429/5xx or transport errors, with delay ``backoff * 2**attempt`` seconds
    (Retry-After, capped at ``retry_after_cap_s`` (default 10 s), wins when present).
    ``transport_retries`` caps the retries spent on transport errors (connection refused, timeout)
    separately from the HTTP ladder and ``transport_backoff`` is the flat delay used after one (default:
    the exponential ladder); ``retry_once_on`` names status codes retried exactly once.
    """
    kwargs = dict(
        source=source, name=name, method=method, url=url, json_body=json, params=params, headers=headers,
        timeout=timeout, retries=retries, backoff=backoff, record_to_ledger=True, transport_retries=transport_retries,
        retry_after_cap_s=retry_after_cap_s, retry_once_on=retry_once_on, transport_backoff=transport_backoff,
    )
    if client is None:
        async with httpx.AsyncClient(follow_redirects=True) as own_client:
            parsed, record, _ = await _fetch_json_async(own_client, ledger, **kwargs)
            return parsed, record
    parsed, record, _ = await _fetch_json_async(client, ledger, **kwargs)
    return parsed, record


# ----------------------------------------------------------------------------- sync fetch
def _fetch_json_sync_impl(
    client: httpx.Client,
    ledger: ProvenanceLedger | None,
    *,
    source: str,
    name: str,
    method: str,
    url: str,
    json_body: Any | None,
    params: Mapping[str, Any] | None,
    headers: Mapping[str, str] | None,
    timeout: float,
    retries: int,
    backoff: float,
    record_to_ledger: bool,
    transport_retries: int | None = None,
) -> tuple[Any | None, RawRecord, bytes]:
    body_sha = sha256_json(json_body) if json_body is not None else None
    started = time.perf_counter()
    response: httpx.Response | None = None
    last_exc: Exception | None = None
    attempts = 0
    transport_budget = _transport_budget(retries, transport_retries)
    for attempt in range(max(1, retries + 1)):
        attempts = attempt + 1
        try:
            response = client.request(
                method.upper(), url, params=params, json=json_body, headers=_default_headers(headers), timeout=timeout,
            )
            last_exc = None
            if response.status_code not in RETRYABLE_STATUS or attempt >= retries:
                break
        except httpx.HTTPError as exc:
            response, last_exc = None, exc
            if attempt >= transport_budget:
                break
        time.sleep(_backoff_delay(attempt, backoff, response))
    return _finish_record(
        ledger=ledger, source=source, name=name, url=url, method=method, body_sha=body_sha, response=response,
        exc=last_exc, started=started, attempts=attempts, record_to_ledger=record_to_ledger,
    )


def fetch_json_sync(
    ledger: ProvenanceLedger,
    *,
    source: str,
    name: str,
    method: str,
    url: str,
    json: Any | None = None,
    params: Mapping[str, Any] | None = None,
    headers: Mapping[str, str] | None = None,
    timeout: float = config.HTTP_TIMEOUT_S,
    retries: int = 3,
    backoff: float = 0.6,
    client: httpx.Client | None = None,
    transport_retries: int | None = None,
) -> tuple[Any | None, RawRecord]:
    """Synchronous twin of ``fetch_json`` for collectors that are not async (same semantics)."""
    kwargs = dict(
        source=source, name=name, method=method, url=url, json_body=json, params=params, headers=headers,
        timeout=timeout, retries=retries, backoff=backoff, record_to_ledger=True, transport_retries=transport_retries,
    )
    if client is None:
        with httpx.Client(follow_redirects=True) as own_client:
            parsed, record, _ = _fetch_json_sync_impl(own_client, ledger, **kwargs)
            return parsed, record
    parsed, record, _ = _fetch_json_sync_impl(client, ledger, **kwargs)
    return parsed, record


# ----------------------------------------------------------------------------- NEAR JSON-RPC
def rpc_error_message(parsed: Any) -> str | None:
    """Return the JSON-RPC error text if ``parsed`` is an error envelope (or a query miss), else None.

    nearcore returns ``{"error": {"name", "cause": {"name"}, "code", "message", "data"}}`` for
    handler errors, and older paths return ``{"result": {"error": "<text>", ...}}`` for query misses.
    """
    if not isinstance(parsed, dict):
        return "empty or non-object RPC response"
    err = parsed.get("error")
    if isinstance(err, dict):
        cause = err.get("cause") if isinstance(err.get("cause"), dict) else {}
        cause_name = cause.get("name") if isinstance(cause, dict) else None
        text = err.get("data") if isinstance(err.get("data"), str) else err.get("message")
        return f"{cause_name or err.get('name') or 'RPC_ERROR'}: {text}"[:300]
    if isinstance(err, str):
        return err[:300]
    result = parsed.get("result")
    if isinstance(result, dict) and isinstance(result.get("error"), str):
        return result["error"][:300]
    if "result" not in parsed:
        return "RPC response without result"
    return None


def is_gc_block_error(parsed: Any) -> bool:
    """True when the RPC refused a historical block (GARBAGE_COLLECTED_BLOCK / UNKNOWN_BLOCK)."""
    if not isinstance(parsed, dict):
        return False
    err = parsed.get("error")
    if isinstance(err, dict):
        cause = err.get("cause")
        if isinstance(cause, dict) and cause.get("name") in _GC_BLOCK_CAUSES:
            return True
        if err.get("name") in _GC_BLOCK_CAUSES:
            return True
    message = rpc_error_message(parsed) or ""
    lowered = message.lower()
    return any(token in lowered for token in _GC_BLOCK_TEXT)


def _has_block_id(params: Any) -> bool:
    return isinstance(params, Mapping) and params.get("block_id") is not None


def _rpc_body(method: str, params: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": "valuo", "method": method, "params": params}


def _rpc_endpoints(params: Any) -> list[tuple[str, str]]:
    """Ordered (url, source) candidates: primary, fallback, then archival for block_id queries."""
    endpoints = [(config.NEAR_RPC_URL, "near_rpc")]
    if config.NEAR_RPC_FALLBACK_URL and config.NEAR_RPC_FALLBACK_URL != config.NEAR_RPC_URL:
        endpoints.append((config.NEAR_RPC_FALLBACK_URL, "near_rpc"))
    if _has_block_id(params) and config.NEAR_ARCHIVAL_RPC_URL:
        endpoints.append((config.NEAR_ARCHIVAL_RPC_URL, "near_rpc_archival"))
    return endpoints


def _rpc_decide(parsed: Any, record: RawRecord, params: Any, is_archival: bool) -> tuple[bool, str | None]:
    """Return (done, note). done=False means try the next endpoint."""
    if record.http_status is None or not (200 <= (record.http_status or 0) < 300) or parsed is None:
        return False, f"{record.url}: {record.error}"
    if is_gc_block_error(parsed):
        if _has_block_id(params) and not is_archival:
            return False, f"{record.url}: {rpc_error_message(parsed)}; retrying on archival"
        return True, None
    return True, None


def _rpc_finalize(
    ledger: ProvenanceLedger, parsed: Any, record: RawRecord, source: str, notes: list[str], content: bytes
) -> tuple[Any | None, RawRecord]:
    """Stamp source/note, translate JSON-RPC errors into record.error, persist exact bytes, add to ledger."""
    record.source = source
    if notes:
        record.note = " | ".join(notes)[:500]
    err = rpc_error_message(parsed) if parsed is not None else record.error
    if err:
        record.ok = False
        record.error = err
        result = None
    else:
        result = parsed["result"]
    if content:
        record.raw_path = ledger.write_raw(content, source=source, name=record.name, is_json=parsed is not None)
    ledger.add(record)
    return result, record


async def near_rpc_call(
    client: httpx.AsyncClient | None,
    ledger: ProvenanceLedger,
    method: str,
    params: Any,
    name: str,
    *,
    timeout: float = config.HTTP_TIMEOUT_S,
    retries: int = 2,
    backoff: float = 0.6,
) -> tuple[Any | None, RawRecord]:
    """NEAR JSON-RPC call with primary -> fallback -> archival routing.

    Returns ``(result, record)`` where ``result`` is the ``result`` member on success and None on a
    JSON-RPC error (``record.ok`` False, ``record.error`` = ``<cause>: <data|message>``). Only the final
    exchange is added to the ledger; intermediate endpoint failures are summarised in ``record.note``.
    ``record.source`` is ``"near_rpc_archival"`` when the archival node answered; ``record.url`` is
    the endpoint that answered.
    """
    body = _rpc_body(method, params)
    notes: list[str] = []
    endpoints = _rpc_endpoints(params)
    own_client = client is None
    client = client or httpx.AsyncClient(follow_redirects=True)
    try:
        parsed: Any = None
        record: RawRecord | None = None
        content = b""
        source = "near_rpc"
        for url, source in endpoints:
            is_archival = source == "near_rpc_archival"
            parsed, record, content = await _fetch_json_async(
                client, None, source=source, name=name, method="POST", url=url, json_body=body, params=None,
                headers={"Content-Type": "application/json"}, timeout=timeout, retries=retries, backoff=backoff,
                record_to_ledger=False,
            )
            done, note = _rpc_decide(parsed, record, params, is_archival)
            if note:
                notes.append(note)
            if done:
                break
        assert record is not None
        return _rpc_finalize(ledger, parsed, record, source, notes, content)
    finally:
        if own_client:
            await client.aclose()


def near_rpc_call_sync(
    ledger: ProvenanceLedger,
    method: str,
    params: Any,
    name: str,
    *,
    timeout: float = config.HTTP_TIMEOUT_S,
    retries: int = 2,
    backoff: float = 0.6,
    client: httpx.Client | None = None,
) -> tuple[Any | None, RawRecord]:
    """Synchronous twin of ``near_rpc_call`` (same routing and return contract)."""
    body = _rpc_body(method, params)
    notes: list[str] = []
    endpoints = _rpc_endpoints(params)
    own_client = client is None
    client = client or httpx.Client(follow_redirects=True)
    try:
        parsed: Any = None
        record: RawRecord | None = None
        content = b""
        source = "near_rpc"
        for url, source in endpoints:
            is_archival = source == "near_rpc_archival"
            parsed, record, content = _fetch_json_sync_impl(
                client, None, source=source, name=name, method="POST", url=url, json_body=body, params=None,
                headers={"Content-Type": "application/json"}, timeout=timeout, retries=retries, backoff=backoff,
                record_to_ledger=False,
            )
            done, note = _rpc_decide(parsed, record, params, is_archival)
            if note:
                notes.append(note)
            if done:
                break
        assert record is not None
        return _rpc_finalize(ledger, parsed, record, source, notes, content)
    finally:
        if own_client:
            client.close()
