"""On-chain anchoring of snapshot hashes on NEAR mainnet (SocialDB, ``social.near``).

Each canonical snapshot's hashes are written under the anchoring account's own SocialDB namespace::

    <account>/valuo/snapshot/<YYYYMMDDTHHMMSSZ>  =  '{"manifest_sha256": ..., "snapshot_sha256": ..., ...}'

SocialDB stores the block height at which every value was written. Reading it back is a plain RPC view
call (no key, no account), so anyone can check that a snapshot with exactly these hashes existed at that
block and has not been edited since: a later edit would change the hashes, and a re-write would change
the write block.

Writing needs a funded NEAR account and runs only on the VPS (``ops/vps/valuo-run.sh``). ``publish`` builds the
``social.near`` ``set`` transaction (Borsh), signs its SHA-256 with the account's ed25519 key through the system
``openssl`` (no extra Python dependency, no downloaded binary) and sends it over public RPC. The key is read from
``~/.near-credentials/mainnet/<account>.json`` (the near-cli legacy keychain format) and never leaves the process.

CLI::

    uv run python -m valuo.anchor args                   # print the social.near `set` JSON args for the current manifest
    uv run python -m valuo.anchor verify --account A     # check the local manifest against what A anchored on-chain
    uv run python -m valuo.anchor list --account A       # list every anchored snapshot with its write block
    uv run python -m valuo.anchor publish --account A    # sign and send the social.near write (needs A's key)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
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
ANCHOR_GAS = 100 * 10**12            # 100 Tgas; a SocialDB set of ~500 bytes uses well under this
ANCHOR_DEPOSIT_YOCTO = 10**22       # 0.01 NEAR, credited to the account's SocialDB storage balance
_B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
_ED25519_PKCS8_PREFIX = bytes.fromhex("302e020100300506032b657004220420")
_ED25519_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


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


# ---------------------------------------------------------------------------------------------- signing / sending
def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + _B58.index(ch)
    raw = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\0" * (len(s) - len(s.lstrip("1"))) + raw


def b58encode(b: bytes) -> str:
    n, out = int.from_bytes(b, "big"), ""
    while n:
        n, r = divmod(n, 58)
        out = _B58[r] + out
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + out


def _bstr(s: str) -> bytes:
    b = s.encode()
    return struct.pack("<I", len(b)) + b


def borsh_function_call_tx(signer: str, public_key: bytes, nonce: int, receiver: str, block_hash: bytes,
                           method: str, args: bytes, gas: int, deposit: int) -> bytes:
    """Borsh bytes of a NEAR Transaction (V0) with one FunctionCall action.

    Layout: signer_id, PublicKey{ED25519=0, 32 bytes}, nonce u64, receiver_id, block_hash [32], Vec<Action> with
    Action::FunctionCall (enum index 2) = {method_name, args Vec<u8>, gas u64, deposit u128}."""
    if len(public_key) != 32 or len(block_hash) != 32:
        raise ValueError("public key and block hash must be 32 bytes")
    action = b"\x02" + _bstr(method) + struct.pack("<I", len(args)) + args + struct.pack("<Q", gas) + deposit.to_bytes(16, "little")
    return (_bstr(signer) + b"\x00" + public_key + struct.pack("<Q", nonce) + _bstr(receiver) + block_hash
            + struct.pack("<I", 1) + action)


def ed25519_sign(seed: bytes, message: bytes) -> bytes:
    """Ed25519 signature via the system openssl (3.x). The key file lives in a 0700 temp dir only for the call."""
    with tempfile.TemporaryDirectory() as t:
        key, msg, sig = Path(t, "k.der"), Path(t, "m"), Path(t, "s")
        old = os.umask(0o077)
        try:
            key.write_bytes(_ED25519_PKCS8_PREFIX + seed)
            msg.write_bytes(message)
        finally:
            os.umask(old)
        subprocess.run(["openssl", "pkeyutl", "-sign", "-rawin", "-inkey", str(key), "-keyform", "DER", "-in", str(msg), "-out", str(sig)],
                       check=True, capture_output=True)
        out = sig.read_bytes()
    if len(out) != 64:
        raise RuntimeError("openssl returned a malformed ed25519 signature")
    return out


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    with tempfile.TemporaryDirectory() as t:
        pub, msg, sig = Path(t, "p.der"), Path(t, "m"), Path(t, "s")
        pub.write_bytes(_ED25519_SPKI_PREFIX + public_key)
        msg.write_bytes(message)
        sig.write_bytes(signature)
        r = subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-rawin", "-inkey", str(pub), "-keyform", "DER", "-in", str(msg), "-sigfile", str(sig)],
                           capture_output=True)
    return r.returncode == 0


def load_key(account: str, keydir: Path | None = None) -> tuple[bytes, bytes]:
    """(seed, public_key) from ~/.near-credentials/mainnet/<account>.json; checks the pair matches."""
    path = (keydir or Path.home() / ".near-credentials" / "mainnet") / f"{account}.json"
    data = json.loads(path.read_text())
    secret = b58decode(str(data["private_key"]).split(":", 1)[1])
    pub = b58decode(str(data["public_key"]).split(":", 1)[1])
    if len(secret) != 64 or secret[32:] != pub:
        raise ValueError(f"{path}: private key does not match its public key")
    return secret[:32], pub


def publish(account: str, manifest_file: Path | None = None, *, url: str | None = None, keydir: Path | None = None) -> dict[str, Any]:
    """Sign and send the social.near `set` for the current manifest; returns the tx hash and final status."""
    seed, pub = load_key(account, keydir)
    args = json.dumps(set_args(account, manifest_file), separators=(",", ":")).encode()
    ak = _rpc("query", {"request_type": "view_access_key", "finality": "final", "account_id": account,
                        "public_key": "ed25519:" + b58encode(pub)}, url)
    tx = borsh_function_call_tx(account, pub, int(ak["nonce"]) + 1, SOCIAL_CONTRACT, b58decode(ak["block_hash"]),
                                "set", args, ANCHOR_GAS, ANCHOR_DEPOSIT_YOCTO)
    digest = hashlib.sha256(tx).digest()
    sig = ed25519_sign(seed, digest)
    if not ed25519_verify(pub, digest, sig):
        raise RuntimeError("local signature check failed; not sending")
    signed = base64.b64encode(tx + b"\x00" + sig).decode()
    res = _rpc("send_tx", {"signed_tx_base64": signed, "wait_until": "FINAL"}, url)
    outcome = res.get("status") or (res.get("transaction_outcome") or {}).get("outcome", {}).get("status")
    failure = outcome.get("Failure") if isinstance(outcome, dict) else None
    return {"tx_hash": b58encode(digest), "ok": failure is None, "status": outcome, "failure": failure,
            "explorer": f"https://nearblocks.io/txns/{b58encode(digest)}"}


def _account(arg: str | None) -> str:
    acct = arg or os.environ.get(ANCHOR_ACCOUNT_ENV)
    if not acct:
        sys.exit(f"pass --account or set {ANCHOR_ACCOUNT_ENV}")
    return acct


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="valuo.anchor", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("args", "verify", "list", "publish"):
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
    if a.cmd == "publish":
        out = publish(acct, a.manifest)
        print(json.dumps(out, indent=2, default=str))
        return 0 if out["ok"] else 1
    res = verify(acct, a.manifest)
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
