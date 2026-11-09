"""Shared pytest fixtures.

- ``probes_dir``: recorded live payloads under tests/fixtures (read-only, untrusted JSON data).
- ``ledger``: a ProvenanceLedger persisting raw bytes into a temporary directory.
- ``load_fixture``: parse a fixture file by name.
- ``@pytest.mark.live`` tests are skipped unless VALUO_LIVE_TESTS=1.
"""
from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from valuo.config import live_tests_enabled
from valuo.provenance import ProvenanceLedger

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if live_tests_enabled():
        return
    skip_live = pytest.mark.skip(reason="live network test; set VALUO_LIVE_TESTS=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)


@pytest.fixture(scope="session")
def probes_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def ledger(tmp_path: Path) -> ProvenanceLedger:
    return ProvenanceLedger(raw_dir=tmp_path / "raw")


@pytest.fixture(scope="session")
def load_fixture(probes_dir: Path) -> Callable[[str], Any]:
    def _load(name: str) -> Any:
        return json.loads((probes_dir / name).read_bytes())

    return _load
