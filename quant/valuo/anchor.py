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
    uv run python -m valuo.anchor falsification --account A [--dry-run]   # write falsified bear triggers (needs A's key)
    uv run python -m valuo.anchor falsification-list --account A [--verify]  # read them back (no key)

Falsification records. The thesis is falsified if a bear trigger holds for 30 consecutive days (streak rules:
``valuo.history._trigger_runs``). ``falsification`` reads ``artifacts/history/summary.json`` and, for every trigger
with ``falsified: true`` that has no record yet, writes one compact JSON value under::

    <account>/valuo/falsification/<trigger_key>

in a single ``social.near`` ``set``, through the same signing and sending path as the snapshot anchor. The first
record for a trigger stands: a later episode does not overwrite it (SocialDB keeps one value per key).
``falsification-list --verify`` recomputes each record's streak from the local ``snapshots.jsonl`` up to the
snapshot it names.
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
FALSIFICATION_NAMESPACE = "valuo/falsification"
FALSIFICATION_SCHEMA = "valuo-falsification/1"
FALSIFICATION_RULE = "thesis falsified if a trigger holds for 30 consecutive days"
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


def summary_path() -> Path:
    return repo_root() / "artifacts" / "history" / "summary.json"


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
    return read_namespace(account, NAMESPACE, url)


def read_namespace(account: str, namespace: str, url: str | None = None) -> dict[str, dict[str, Any]]:
    """Every JSON value under <account>/<namespace>/*, with the block each value was written at (view call, no key)."""
    args = {"keys": [f"{account}/{namespace}/*"], "options": {"with_block_height": True}}
    res = _rpc("query", {
        "request_type": "call_function", "finality": "final", "account_id": SOCIAL_CONTRACT,
        "method_name": "get", "args_base64": base64.b64encode(json.dumps(args).encode()).decode(),
    }, url)
    tree = json.loads(bytes(res["result"]).decode() or "{}")
    node = tree.get(account, {})
    for part in namespace.split("/"):
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


def _social_view(method: str, args: dict[str, Any], url: str | None = None) -> Any:
    res = _rpc("query", {"request_type": "call_function", "finality": "final", "account_id": SOCIAL_CONTRACT, "method_name": method,
                         "args_base64": base64.b64encode(json.dumps(args).encode()).decode()}, url)
    return json.loads(bytes(res["result"]).decode() or "null")


def anchor_deposit(account: str, url: str | None = None) -> int:
    """Deposit for this write: ANCHOR_DEPOSIT_YOCTO, plus SocialDB's minimum storage balance on the account's first write
    (social.near panics with "attached deposit is less than the minimum storage balance" otherwise)."""
    if _social_view("storage_balance_of", {"account_id": account}, url) is not None:
        return ANCHOR_DEPOSIT_YOCTO
    bounds = _social_view("storage_balance_bounds", {}, url) or {}
    return int(bounds.get("min") or 0) + ANCHOR_DEPOSIT_YOCTO


def send_set(account: str, args_obj: dict[str, Any], *, url: str | None = None, keydir: Path | None = None) -> dict[str, Any]:
    """Sign and send one social.near `set` with ``args_obj`` as its JSON args; returns the tx hash and final status."""
    seed, pub = load_key(account, keydir)
    args = json.dumps(args_obj, separators=(",", ":")).encode()
    deposit = anchor_deposit(account, url)
    ak = _rpc("query", {"request_type": "view_access_key", "finality": "final", "account_id": account,
                        "public_key": "ed25519:" + b58encode(pub)}, url)
    tx = borsh_function_call_tx(account, pub, int(ak["nonce"]) + 1, SOCIAL_CONTRACT, b58decode(ak["block_hash"]),
                                "set", args, ANCHOR_GAS, deposit)
    digest = hashlib.sha256(tx).digest()
    sig = ed25519_sign(seed, digest)
    if not ed25519_verify(pub, digest, sig):
        raise RuntimeError("local signature check failed; not sending")
    signed = base64.b64encode(tx + b"\x00" + sig).decode()
    res = _rpc("send_tx", {"signed_tx_base64": signed, "wait_until": "FINAL"}, url)
    outcome = res.get("status") or (res.get("transaction_outcome") or {}).get("outcome", {}).get("status")
    failure = outcome.get("Failure") if isinstance(outcome, dict) else None
    return {"tx_hash": b58encode(digest), "ok": failure is None, "status": outcome, "failure": failure, "deposit_yocto": str(deposit),
            "explorer": f"https://nearblocks.io/txns/{b58encode(digest)}"}


def publish(account: str, manifest_file: Path | None = None, *, url: str | None = None, keydir: Path | None = None) -> dict[str, Any]:
    """Sign and send the social.near `set` for the current manifest; returns the tx hash and final status."""
    return send_set(account, set_args(account, manifest_file), url=url, keydir=keydir)


# ---------------------------------------------------------------------------------------------- falsification records
def _load_triggers(summary_file: Path | None = None) -> dict[str, dict[str, Any]]:
    summary = json.loads((summary_file or summary_path()).read_text())
    trig = ((summary.get("snapshots") or {}).get("bear_triggers")) or {}
    return {k: v for k, v in sorted(trig.items()) if isinstance(v, dict)}


def falsification_record(key: str, trig: dict[str, Any]) -> dict[str, Any]:
    """The value written on-chain for one falsified trigger. Every field is copied from summary.json."""
    return {
        "schema": FALSIFICATION_SCHEMA,
        "trigger": key,
        "metric": trig.get("metric"),
        "threshold": trig.get("threshold"),
        "comparator": trig.get("comparator"),
        "breached_since_utc": trig.get("breached_since_utc"),
        "streak_days": trig.get("breached_streak_days"),
        "observed_days": trig.get("observed_days"),
        "last_t_utc": trig.get("last_t_utc"),
        "last_value": trig.get("last_value"),
        "snapshot_sha256": trig.get("last_snapshot_sha256"),
        "streak_max_gap_h": trig.get("streak_max_gap_h"),
        "rule": FALSIFICATION_RULE,
    }


def falsification_set_args(account: str, records: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """JSON args for one social.near `set` writing every record under <account>/valuo/falsification/<trigger_key>."""
    leaves = {k: json.dumps(v, separators=(",", ":"), sort_keys=True) for k, v in sorted(records.items())}
    return {"data": {account: {"valuo": {"falsification": leaves}}}}


def _num_text(v: Any, spec: str = ".4g") -> str:
    return format(v, spec) if isinstance(v, (int, float)) and not isinstance(v, bool) else "n/a"


def trigger_status_line(key: str, trig: dict[str, Any]) -> str:
    """One line per trigger: '<key>: breached 0.7 d of 30 ...' / 'clear' / 'not measured'."""
    days = float(trig.get("falsification_days") or 30)
    state = trig.get("state_now") or ("breached" if trig.get("breached_now") is True else
                                      "clear" if trig.get("breached_now") is False else "unmeasured")
    if trig.get("falsified"):
        return f"{key}: FALSIFIED, breached {trig.get('breached_streak_days'):.1f} d (>= {days:.0f}) since {trig.get('breached_since_utc')}"
    if state == "breached":
        streak = trig.get("breached_streak_days") or 0.0
        tail = f"since {trig.get('breached_since_utc')}, {trig.get('observed_days')} daily records"
        if trig.get("gap_reset_at_utc"):
            tail += f"; streak restarted after a data gap at {trig['gap_reset_at_utc']}"
        return f"{key}: breached {streak:.1f} d of {days:.0f} ({tail})"
    if state == "clear":
        return (f"{key}: clear ({trig.get('metric')} {_num_text(trig.get('last_value'))}, "
                f"trigger {trig.get('comparator')} {_num_text(trig.get('threshold'))})")
    return f"{key}: not measured on the latest daily run (streak reset)"


def falsification(account: str, summary_file: Path | None = None, *, dry_run: bool = False,
                  url: str | None = None, keydir: Path | None = None) -> dict[str, Any]:
    """Write every falsified trigger that has no on-chain record yet. Sends nothing if none qualifies.

    The on-chain read happens only when at least one trigger is falsified, so the common case needs no network."""
    triggers = _load_triggers(summary_file)
    lines = [trigger_status_line(k, t) for k, t in triggers.items()]
    falsified = {k: t for k, t in triggers.items() if t.get("falsified") is True}
    out: dict[str, Any] = {"account": account, "status": lines, "falsified": sorted(falsified), "already_recorded": [],
                           "to_publish": [], "args": None, "sent": None, "ok": True, "dry_run": dry_run}
    if not falsified:
        return out
    existing = read_namespace(account, FALSIFICATION_NAMESPACE, url)
    out["already_recorded"] = sorted(k for k in falsified if k in existing)
    new = {k: falsification_record(k, t) for k, t in falsified.items() if k not in existing}
    out["to_publish"] = sorted(new)
    if not new:
        return out
    out["args"] = falsification_set_args(account, new)
    if dry_run:
        return out
    out["sent"] = send_set(account, out["args"], url=url, keydir=keydir)
    out["ok"] = bool(out["sent"]["ok"])
    return out


def read_falsifications(account: str, url: str | None = None) -> dict[str, dict[str, Any]]:
    """Every falsification record under <account>/valuo/falsification/*, with its write block (no key)."""
    return read_namespace(account, FALSIFICATION_NAMESPACE, url)


def verify_falsification(value: dict[str, Any] | None, snapshot_records: list[dict[str, Any]]) -> list[str]:
    """Recompute the streak from local snapshot records up to the snapshot the on-chain record names ([] = consistent)."""
    from valuo import history

    if not isinstance(value, dict):
        return ["value is not a JSON object"]
    sha, key = value.get("snapshot_sha256"), value.get("trigger")
    hit = next((r for r in snapshot_records if r.get("snapshot_sha256") == sha), None)
    if hit is None:
        return [f"snapshot {str(sha)[:16]}... not in local snapshots.jsonl"]
    cut = history._parse_t(hit.get("t_utc"))
    upto = [r for r in snapshot_records if (history._parse_t(r.get("t_utc")) or cut) <= cut]
    runs = history._trigger_runs(history.latest_per_utc_day(upto)).get(str(key))
    if runs is None:
        return [f"trigger {key} absent from local history"]
    problems = []
    if not runs.get("falsified"):
        problems.append(f"local recomputation: streak {runs.get('breached_streak_days')} d at that snapshot, not falsified")
    if runs.get("breached_since_utc") != value.get("breached_since_utc"):
        problems.append(f"breached_since_utc: local {runs.get('breached_since_utc')!r} != on-chain {value.get('breached_since_utc')!r}")
    return problems


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
    f = sub.add_parser("falsification", help="write falsified bear triggers to <account>/valuo/falsification/<key>")
    f.add_argument("--account")
    f.add_argument("--summary", type=Path, help="history summary.json (default: artifacts/history/summary.json)")
    f.add_argument("--dry-run", action="store_true", help="print the status and set args; send nothing, no key needed")
    fl = sub.add_parser("falsification-list", help="read back <account>/valuo/falsification/* (no key)")
    fl.add_argument("--account")
    fl.add_argument("--verify", action="store_true", help="recompute each streak from local snapshots.jsonl")
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
    if a.cmd == "falsification":
        out = falsification(acct, a.summary, dry_run=a.dry_run)
        for line in out["status"]:
            print(line)
        for k in out["already_recorded"]:
            print(f"{k}: already recorded at {acct}/{FALSIFICATION_NAMESPACE}/{k}; not rewritten")
        if not out["falsified"]:
            print(f"no trigger has held for 30 consecutive days; nothing sent ({acct}/{FALSIFICATION_NAMESPACE}/* unchanged)")
        elif out["args"] is not None and a.dry_run:
            print("dry run, would send social.near set:")
            print(json.dumps(out["args"], separators=(",", ":")))
        elif out["sent"] is not None:
            print(json.dumps(out["sent"], indent=2, default=str))
        return 0 if out["ok"] else 1
    if a.cmd == "falsification-list":
        hits = read_falsifications(acct)
        if not hits:
            print(f"no records under {acct}/{FALSIFICATION_NAMESPACE}/*")
            return 0
        snaps = None
        if a.verify:
            from valuo import history
            snaps = history.read_jsonl(history.history_dir() / "snapshots.jsonl")
        bad = 0
        for key, hit in hits.items():
            v = hit["value"] or {}
            line = (f"{key}  write_block={hit['write_block_height']}  since={v.get('breached_since_utc')}  "
                    f"streak={v.get('streak_days')} d  snapshot={str(v.get('snapshot_sha256'))[:16]}...")
            if snaps is not None:
                problems = verify_falsification(hit["value"], snaps)
                bad += bool(problems)
                line += "  verified" if not problems else "  MISMATCH: " + "; ".join(problems)
            print(line)
        return 1 if bad else 0
    res = verify(acct, a.manifest)
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
