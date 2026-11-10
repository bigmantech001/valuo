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
