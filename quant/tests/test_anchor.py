"""valuo.anchor: the on-chain record is built from the manifest, and verify() reads SocialDB's write block."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from valuo import anchor
from valuo.provenance import sha256_file

MANIFEST = {
    "generated_at_utc": "2026-11-08T21:24:23.730Z", "block_height": 223672128, "block_hash": "6Wam",
    "snapshot_sha256": "a" * 64, "memo_sha256": "b" * 64, "seed": 20261114, "records": [{}, {}],
}


@pytest.fixture()
def manifest_file(tmp_path: Path) -> Path:
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(MANIFEST))
    return p


def test_key_is_socialdb_safe():
    assert anchor.anchor_key("2026-11-08T21:24:23.730Z") == "20261108T212423Z"


def test_set_args_shape(manifest_file: Path):
    args = anchor.set_args("valuo.near", manifest_file)
    raw = args["data"]["valuo.near"]["valuo"]["snapshot"]["20261108T212423Z"]
    rec = json.loads(raw)
    assert rec["manifest_sha256"] == sha256_file(manifest_file)
    assert rec["snapshot_sha256"] == "a" * 64 and rec["data_block_height"] == 223672128 and rec["n_records"] == 2


def _socialdb(account: str, key: str, value: str, block: int) -> dict:
    tree = {account: {":block": block, "valuo": {":block": block, "snapshot": {":block": block, key: {":block": block, "": value}}}}}
    return {"result": list(json.dumps(tree).encode()), "block_height": block + 10}


def test_verify_match_and_tamper(manifest_file: Path, monkeypatch: pytest.MonkeyPatch):
    raw = anchor.set_args("valuo.near", manifest_file)["data"]["valuo.near"]["valuo"]["snapshot"]["20261108T212423Z"]
    monkeypatch.setattr(anchor, "_rpc", lambda method, params, url=None: _socialdb("valuo.near", "20261108T212423Z", raw, 223672500))
    monkeypatch.setattr(anchor, "block_time_utc", lambda h, url=None: "2026-11-08T21:30:00Z")
    ok = anchor.verify("valuo.near", manifest_file)
    assert ok["ok"] and ok["write_block_height"] == 223672500 and ok["problems"] == []

    # any edit to the local manifest after anchoring changes its hash and fails verification
    manifest_file.write_text(json.dumps({**MANIFEST, "seed": 1}))
    bad = anchor.verify("valuo.near", manifest_file)
    assert not bad["ok"] and any("manifest_sha256" in p for p in bad["problems"])


def test_verify_rejects_write_before_data(manifest_file: Path, monkeypatch: pytest.MonkeyPatch):
    raw = anchor.set_args("valuo.near", manifest_file)["data"]["valuo.near"]["valuo"]["snapshot"]["20261108T212423Z"]
    monkeypatch.setattr(anchor, "_rpc", lambda method, params, url=None: _socialdb("valuo.near", "20261108T212423Z", raw, 223600000))
    monkeypatch.setattr(anchor, "block_time_utc", lambda h, url=None: None)
    res = anchor.verify("valuo.near", manifest_file)
    assert not res["ok"] and any("precedes" in p for p in res["problems"])


def test_not_anchored(manifest_file: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(anchor, "_rpc", lambda method, params, url=None: {"result": list(b"{}"), "block_height": 1})
    res = anchor.verify("valuo.near", manifest_file)
    assert res["problems"] == ["not anchored"] and not res["ok"]


# ------------------------------------------------------------------------------------------------- signing / publish
RFC8032_SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
RFC8032_PUB = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")


def test_ed25519_matches_rfc8032_vector():
    # RFC 8032 section 7.1, TEST 2 (one-byte message 0x72). openssl cannot sign an empty message (TEST 1); the
    # anchor always signs a 32-byte SHA-256, so that case never arises.
    seed = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    pub = bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    want = bytes.fromhex("92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00")
    sig = anchor.ed25519_sign(seed, b"\x72")
    assert sig == want
    assert anchor.ed25519_verify(pub, b"\x72", sig)
    assert not anchor.ed25519_verify(pub, b"\x73", sig)


def test_base58_roundtrip():
    for b in (b"", b"\0\0abc", RFC8032_PUB, bytes(32)):
        assert anchor.b58decode(anchor.b58encode(b)) == b


def test_borsh_layout():
    tx = anchor.borsh_function_call_tx("ab", RFC8032_PUB, 7, "social.near", bytes(range(32)), "set", b"{}", 5, 3)
    i = 0
    assert tx[i:i + 4] == (2).to_bytes(4, "little") and tx[4:6] == b"ab"; i = 6
    assert tx[i] == 0 and tx[i + 1:i + 33] == RFC8032_PUB; i += 33
    assert int.from_bytes(tx[i:i + 8], "little") == 7; i += 8
    assert int.from_bytes(tx[i:i + 4], "little") == 11 and tx[i + 4:i + 15] == b"social.near"; i += 15
    assert tx[i:i + 32] == bytes(range(32)); i += 32
    assert int.from_bytes(tx[i:i + 4], "little") == 1 and tx[i + 4] == 2; i += 5   # one action, FunctionCall
    assert tx[i:i + 7] == (3).to_bytes(4, "little") + b"set"; i += 7
    assert tx[i:i + 6] == (2).to_bytes(4, "little") + b"{}"; i += 6
    assert int.from_bytes(tx[i:i + 8], "little") == 5 and int.from_bytes(tx[i + 8:i + 24], "little") == 3
    assert len(tx) == i + 24


def _keyfile(tmp_path: Path, account: str) -> Path:
    d = tmp_path / "keys"
    d.mkdir()
    (d / f"{account}.json").write_text(json.dumps({
        "account_id": account, "public_key": "ed25519:" + anchor.b58encode(RFC8032_PUB),
        "private_key": "ed25519:" + anchor.b58encode(RFC8032_SEED + RFC8032_PUB),
    }))
    return d


def test_publish_signs_what_it_sends(manifest_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import base64 as b64
    import hashlib

    keys = _keyfile(tmp_path, "valuo.near")
    sent: dict = {}

    def fake_rpc(method, params, url=None):
        if method == "query" and params["request_type"] == "call_function":
            reply = {"storage_balance_of": b"null", "storage_balance_bounds": b'{"min":"20000000000000000000000","max":null}'}[params["method_name"]]
            return {"result": list(reply)}
        if method == "query":
            assert params["request_type"] == "view_access_key"
            return {"nonce": 41, "block_hash": anchor.b58encode(bytes(32))}
        sent.update(params)
        return {"status": {"SuccessValue": ""}}

    monkeypatch.setattr(anchor, "_rpc", fake_rpc)
    out = anchor.publish("valuo.near", manifest_file, keydir=keys)
    raw = b64.b64decode(sent["signed_tx_base64"])
    tx, sig = raw[:-65], raw[-64:]
    assert raw[-65] == 0 and anchor.ed25519_verify(RFC8032_PUB, hashlib.sha256(tx).digest(), sig)
    assert out["ok"] and out["tx_hash"] == anchor.b58encode(hashlib.sha256(tx).digest())
    assert int.from_bytes(tx[4 + 10 + 33:4 + 10 + 41], "little") == 42          # nonce = access-key nonce + 1
    assert b'"valuo.near":{"valuo":{"snapshot":{"20261108T212423Z"' in tx
    # first write: SocialDB minimum (0.02 NEAR) + the per-write 0.01 NEAR, as the last 16 bytes (u128 deposit)
    assert int.from_bytes(tx[-16:], "little") == 2 * 10**22 + anchor.ANCHOR_DEPOSIT_YOCTO == int(out["deposit_yocto"])


def test_load_key_rejects_mismatched_pair(tmp_path: Path):
    d = tmp_path / "k"
    d.mkdir()
    (d / "x.json").write_text(json.dumps({"public_key": "ed25519:" + anchor.b58encode(bytes(32)),
                                          "private_key": "ed25519:" + anchor.b58encode(RFC8032_SEED + RFC8032_PUB)}))
    with pytest.raises(ValueError):
        anchor.load_key("x", d)


# ------------------------------------------------------------------------------------------------- falsification records
def _trigger(falsified: bool, *, state: str = "breached", streak: float | None = 31.0, since: str | None = "2026-10-01T06:00:00Z") -> dict:
    return {"metric": "max_inflation_rate", "threshold": 0.016, "comparator": ">", "state_now": state,
            "breached_now": state == "breached" if state != "unmeasured" else None, "breached_since_utc": since,
            "breached_streak_days": streak, "observed_days": 32, "last_t_utc": "2026-11-01T06:00:00Z", "last_value": 0.025,
            "last_snapshot_sha256": "c" * 64, "gap_reset_at_utc": None, "falsified": falsified,
            "streak_max_gap_h": 36.0, "falsification_days": 30.0}


def _summary_file(tmp_path: Path, triggers: dict) -> Path:
    p = tmp_path / "summary.json"
    p.write_text(json.dumps({"snapshots": {"bear_triggers": triggers}}))
    return p


def _no_network(*a, **k):
    raise AssertionError("no RPC call expected")


def test_falsification_nothing_falsified_sends_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(anchor, "_rpc", _no_network)
    path = _summary_file(tmp_path, {
        "governance_stalemate": _trigger(False, streak=1.0),
        "fee_race_to_zero": _trigger(False, state="clear", streak=None, since=None),
        "solver_cartelization": _trigger(False, state="unmeasured", streak=None, since=None),
    })
    out = anchor.falsification("valuo.near", path)
    assert out["falsified"] == [] and out["sent"] is None and out["args"] is None and out["ok"]
    assert out["status"][1].startswith("governance_stalemate: breached 1.0 d of 30")
    assert out["status"][0].startswith("fee_race_to_zero: clear") and "not measured" in out["status"][2]


def test_falsification_dry_run_builds_args_without_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_rpc(method, params, url=None):
        calls.append((method, params.get("method_name")))
        assert method == "query" and params["method_name"] == "get"
        return {"result": list(b"{}")}

    monkeypatch.setattr(anchor, "_rpc", fake_rpc)
    monkeypatch.setattr(anchor, "load_key", _no_network)
    path = _summary_file(tmp_path, {"governance_stalemate": _trigger(True), "fee_race_to_zero": _trigger(False, state="clear")})
    out = anchor.falsification("valuo.near", path, dry_run=True)
    assert out["to_publish"] == ["governance_stalemate"] and out["sent"] is None and calls == [("query", "get")]
    leaf = out["args"]["data"]["valuo.near"]["valuo"]["falsification"]
    assert list(leaf) == ["governance_stalemate"]
    rec = json.loads(leaf["governance_stalemate"])
    assert rec["trigger"] == "governance_stalemate" and rec["snapshot_sha256"] == "c" * 64 and rec["streak_days"] == 31.0
    assert rec["breached_since_utc"] == "2026-10-01T06:00:00Z" and rec["rule"] == anchor.FALSIFICATION_RULE
    assert rec["comparator"] == ">" and rec["threshold"] == 0.016 and rec["last_value"] == 0.025
    assert "FALSIFIED" in out["status"][1]


def test_falsification_skips_already_recorded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    existing = json.dumps({"trigger": "governance_stalemate"})
    monkeypatch.setattr(anchor, "_rpc", lambda method, params, url=None: {"result": list(json.dumps(
        {"valuo.near": {"valuo": {"falsification": {"governance_stalemate": {":block": 5, "": existing}}}}}).encode())})
    monkeypatch.setattr(anchor, "send_set", _no_network)
    out = anchor.falsification("valuo.near", _summary_file(tmp_path, {"governance_stalemate": _trigger(True)}))
    assert out["already_recorded"] == ["governance_stalemate"] and out["to_publish"] == [] and out["sent"] is None


def test_falsification_publish_uses_anchor_signing_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    import base64 as b64
    import hashlib

    keys = _keyfile(tmp_path, "valuo.near")
    sent: dict = {}

    def fake_rpc(method, params, url=None):
        if method == "query" and params["request_type"] == "call_function":
            reply = {"get": b"{}", "storage_balance_of": b'{"total":"1","available":"0"}'}[params["method_name"]]
            return {"result": list(reply)}
        if method == "query":
            return {"nonce": 9, "block_hash": anchor.b58encode(bytes(32))}
        assert method == "send_tx"
        sent.update(params)
        return {"status": {"SuccessValue": ""}}

    monkeypatch.setattr(anchor, "_rpc", fake_rpc)
    out = anchor.falsification("valuo.near", _summary_file(tmp_path, {"solver_cartelization": _trigger(True)}), keydir=keys)
    raw = b64.b64decode(sent["signed_tx_base64"])
    tx, sig = raw[:-65], raw[-64:]
    assert anchor.ed25519_verify(RFC8032_PUB, hashlib.sha256(tx).digest(), sig)
    assert b'"valuo.near":{"valuo":{"falsification":{"solver_cartelization"' in tx
    assert int.from_bytes(tx[-16:], "little") == anchor.ANCHOR_DEPOSIT_YOCTO   # storage already registered
    assert out["ok"] and out["sent"]["tx_hash"] == anchor.b58encode(hashlib.sha256(tx).digest())


def test_read_and_verify_falsification(monkeypatch: pytest.MonkeyPatch):
    from datetime import datetime, timedelta, timezone

    t0 = datetime(2026, 10, 1, 6, tzinfo=timezone.utc)
    snaps = [{"t_utc": (t0 + timedelta(days=d)).strftime("%Y-%m-%dT%H:%M:%SZ"), "snapshot_sha256": f"{d:064d}",
              "bear_triggers": [{"key": "g", "metric": "m", "threshold": 1, "comparator": ">", "current_value": 2, "breached": True}]}
             for d in range(32)]
    good = {"trigger": "g", "snapshot_sha256": f"{30:064d}", "breached_since_utc": snaps[0]["t_utc"]}
    tree = {"valuo.near": {"valuo": {"falsification": {"g": {":block": 77, "": json.dumps(good)}}}}}
    monkeypatch.setattr(anchor, "_rpc", lambda method, params, url=None: {"result": list(json.dumps(tree).encode())})
    hits = anchor.read_falsifications("valuo.near")
    assert hits["g"]["write_block_height"] == 77 and hits["g"]["value"] == good
    assert anchor.verify_falsification(hits["g"]["value"], snaps) == []
    early = {**good, "snapshot_sha256": f"{20:064d}"}            # only 20 days by then
    assert any("not falsified" in p for p in anchor.verify_falsification(early, snaps))
    assert any("not in local" in p for p in anchor.verify_falsification({**good, "snapshot_sha256": "x"}, snaps))
