"""On-chain anchoring of snapshot hashes on NEAR mainnet (SocialDB, ``social.near``).

Each canonical snapshot's hashes are written under the anchoring account's own SocialDB namespace::

    <account>/valuo/snapshot/<YYYYMMDDTHHMMSSZ>  =  '{"manifest_sha256": ..., "snapshot_sha256": ..., ...}'

SocialDB stores the block height at which every value was written. Reading it back is a plain RPC view
call (no key, no account), so anyone can check that a snapshot with exactly these hashes existed at that
block and has not been edited since: a later edit would change the hashes, and a re-write would change
the write block.

Writing needs a funded NEAR account and runs only on the VPS (``ops/vps/valuo-run.sh``, near-cli-rs).
This module builds the write arguments and verifies; it never holds a key.

CLI::

    uv run python -m valuo.anchor args                   # print the social.near `set` JSON args for the current manifest
    uv run python -m valuo.anchor verify --account A     # check the local manifest against what A anchored on-chain
    uv run python -m valuo.anchor list --account A       # list every anchored snapshot with its write block
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from valuo import config
from valuo.provenance import sha256_file

SOCIAL_CONTRACT = "social.near"
NAMESPACE = "valuo/snapshot"
ANCHOR_SCHEMA = "valuo-anchor/1"
ANCHOR_ACCOUNT_ENV = "VALUO_ANCHOR_ACCOUNT"


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def manifest_path() -> Path:
    return repo_root() / "artifacts" / "manifest.json"


def anchor_key(generated_at_utc: str) -> str:
    """'2026-11-08T21:24:23.730Z' -> '20261108T212423Z' (SocialDB keys must avoid '.', ':' and '/')."""
    dt = datetime.fromisoformat(generated_at_utc.replace("Z", "+00:00"))
    return dt.strftime("%Y%m%dT%H%M%SZ")


def anchor_record(manifest: dict[str, Any], manifest_sha256: str) -> dict[str, Any]:
    """The value written on-chain for one snapshot. Every field is copied from the manifest or hashed from it."""
    return {
        "schema": ANCHOR_SCHEMA,
        "generated_at_utc": manifest.get("generated_at_utc"),
        "manifest_sha256": manifest_sha256,
        "snapshot_sha256": manifest.get("snapshot_sha256"),
        "memo_sha256": manifest.get("memo_sha256"),
        "data_block_height": manifest.get("block_height"),
        "data_block_hash": manifest.get("block_hash"),
        "n_records": len(manifest.get("records") or []),
        "seed": manifest.get("seed"),
    }


def set_args(account: str, manifest_file: Path | None = None) -> dict[str, Any]:
    """JSON args for ``social.near`` ``set``: one compact JSON string under <account>/valuo/snapshot/<key>."""
    path = manifest_file or manifest_path()
    manifest = json.loads(path.read_text())
    rec = anchor_record(manifest, sha256_file(path))
    key = anchor_key(rec["generated_at_utc"])
    return {"data": {account: {"valuo": {"snapshot": {key: json.dumps(rec, separators=(",", ":"), sort_keys=True)}}}}}


def _rpc(method: str, params: dict[str, Any], url: str | None = None) -> dict[str, Any]:
    urls = [u for u in (url, config.NEAR_RPC_URL, config.NEAR_RPC_FALLBACK_URL) if u]
    last: Exception | None = None
    for u in urls:
        try:
            r = httpx.post(u, json={"jsonrpc": "2.0", "id": "valuo-anchor", "method": method, "params": params}, timeout=20)
            body = r.json()
            if "result" in body:
                return body["result"]
            last = RuntimeError(f"{u}: {body.get('error')}")
        except (httpx.HTTPError, ValueError) as e:  # try the next endpoint
            last = e
    raise RuntimeError(f"NEAR RPC {method} failed on every endpoint: {last}")


def read_anchors(account: str, url: str | None = None) -> dict[str, dict[str, Any]]:
    """Every anchored snapshot under <account>/valuo/snapshot/*, with the block each value was written at."""
    args = {"keys": [f"{account}/{NAMESPACE}/*"], "options": {"with_block_height": True}}
    res = _rpc("query", {
        "request_type": "call_function", "finality": "final", "account_id": SOCIAL_CONTRACT,
        "method_name": "get", "args_base64": base64.b64encode(json.dumps(args).encode()).decode(),
    }, url)
    tree = json.loads(bytes(res["result"]).decode() or "{}")
    node = tree.get(account, {})
    for part in NAMESPACE.split("/"):
        node = node.get(part, {}) if isinstance(node, dict) else {}
    out: dict[str, dict[str, Any]] = {}
    for key, leaf in node.items():
        if key.startswith(":") or not isinstance(leaf, dict):
            continue
        raw = leaf.get("")
        try:
            value = json.loads(raw) if isinstance(raw, str) else None
        except ValueError:
            value = None
        out[key] = {"value": value, "raw": raw, "write_block_height": leaf.get(":block")}
    return dict(sorted(out.items()))


def block_time_utc(height: int, url: str | None = None) -> str | None:
    """Timestamp of a block (needs an archival node for old blocks; None when unavailable)."""
    for u in (url, config.NEAR_RPC_URL, config.NEAR_ARCHIVAL_RPC_URL):
        if not u:
            continue
        try:
            b = _rpc("block", {"block_id": int(height)}, u)
            ns = int(b["header"]["timestamp_nanosec"])
            return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:  # noqa: BLE001 - fall through to the next node
            continue
    return None


def compare(local: dict[str, Any], onchain: dict[str, Any] | None) -> list[str]:
    """Field-by-field mismatches between the local record and the anchored one ([] = match)."""
    if onchain is None:
        return ["not anchored"]
    return [f"{k}: local {local.get(k)!r} != on-chain {onchain.get(k)!r}" for k in local if local.get(k) != onchain.get(k)]


def verify(account: str, manifest_file: Path | None = None) -> dict[str, Any]:
    path = manifest_file or manifest_path()
    manifest = json.loads(path.read_text())
    local = anchor_record(manifest, sha256_file(path))
    key = anchor_key(local["generated_at_utc"])
    anchors = read_anchors(account)
    hit = anchors.get(key)
    problems = compare(local, hit["value"] if hit else None)
    out: dict[str, Any] = {"account": account, "key": f"{account}/{NAMESPACE}/{key}", "ok": not problems, "problems": problems, "local": local}
    if hit:
        wb = hit["write_block_height"]
        out["write_block_height"] = wb
        out["write_block_time_utc"] = block_time_utc(wb) if wb else None
        db = local.get("data_block_height")
        if isinstance(wb, int) and isinstance(db, int) and wb < db:
            out["ok"] = False
            out["problems"].append(f"write block {wb} precedes the data block {db}")
    return out


def _account(arg: str | None) -> str:
    acct = arg or os.environ.get(ANCHOR_ACCOUNT_ENV)
    if not acct:
        sys.exit(f"pass --account or set {ANCHOR_ACCOUNT_ENV}")
    return acct


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="valuo.anchor", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("args", "verify", "list"):
        s = sub.add_parser(name)
        s.add_argument("--account")
        if name != "list":
            s.add_argument("--manifest", type=Path)
    a = p.parse_args(argv)
    acct = _account(a.account)
    if a.cmd == "args":
        print(json.dumps(set_args(acct, a.manifest), separators=(",", ":")))
        return 0
    if a.cmd == "list":
        for key, hit in read_anchors(acct).items():
            v = hit["value"] or {}
            print(f"{key}  write_block={hit['write_block_height']}  data_block={v.get('data_block_height')}  manifest={str(v.get('manifest_sha256'))[:16]}...")
        return 0
    res = verify(acct, a.manifest)
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
