"""Runtime configuration for the Valuo quant engine.

Every endpoint is public and key-free; a repo-root ``.env`` (see ``.env.example``) may override
any value, and optional keys only raise rate limits. Nothing here is a model input: numbers that
feed the models come from live fetches (``provenance.py``) or the labeled registry in
``assumptions.py``.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# quant/valuo/config.py -> parents[0]=valuo, [1]=quant, [2]=repo root
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
QUANT_ROOT: Path = Path(__file__).resolve().parents[1]

# Repo-root .env is optional; existing process env always wins (override=False).
load_dotenv(REPO_ROOT / ".env", override=False)


def _env(key: str, default: str) -> str:
    value = os.environ.get(key)
    return value.strip() if value and value.strip() else default


def _env_opt(key: str) -> str | None:
    value = os.environ.get(key)
    return value.strip() if value and value.strip() else None


def _env_int(key: str, default: int) -> int:
    return int(_env(key, str(default)))


def _env_float(key: str, default: float) -> float:
    return float(_env(key, str(default)))


# ----------------------------------------------------------------------------- NEAR JSON-RPC
NEAR_RPC_URL: str = _env("NEAR_RPC_URL", "https://free.rpc.fastnear.com")
NEAR_RPC_FALLBACK_URL: str = _env("NEAR_RPC_FALLBACK_URL", "https://rpc.mainnet.near.org")
# Historical state (view_account at a block_id older than ~5 epochs) is garbage-collected on
# non-archival nodes; provenance.near_rpc_call retries such queries here.
NEAR_ARCHIVAL_RPC_URL: str = _env("NEAR_ARCHIVAL_RPC_URL", "https://archival-rpc.mainnet.fastnear.com")

# ----------------------------------------------------------------------------- Routers
ONECLICK_API_BASE: str = _env("ONECLICK_API_BASE", "https://1click.chaindefuser.com").rstrip("/")
ONECLICK_JWT: str | None = _env_opt("ONECLICK_JWT")
RELAY_API_BASE: str = _env("RELAY_API_BASE", "https://api.relay.link").rstrip("/")
LIFI_API_BASE: str = _env("LIFI_API_BASE", "https://li.quest/v1").rstrip("/")
ACROSS_API_BASE: str = _env("ACROSS_API_BASE", "https://app.across.to/api").rstrip("/")

# ----------------------------------------------------------------------------- Analytics
NEARSTATS_API_BASE: str = _env("NEARSTATS_API_BASE", "https://nearstats.org/api/near").rstrip("/")
NEARBLOCKS_API_BASE: str = _env("NEARBLOCKS_API_BASE", "https://api.nearblocks.io/v1").rstrip("/")
NEARBLOCKS_API_KEY: str | None = _env_opt("NEARBLOCKS_API_KEY")
DEFILLAMA_API_BASE: str = _env("DEFILLAMA_API_BASE", "https://api.llama.fi").rstrip("/")
COINS_LLAMA_BASE: str = _env("COINS_LLAMA_BASE", "https://coins.llama.fi").rstrip("/")
COINGECKO_API_BASE: str = _env("COINGECKO_API_BASE", "https://api.coingecko.com/api/v3").rstrip("/")

# ----------------------------------------------------------------------------- Reproducibility
SEED: int = _env_int("VALUO_MC_SEED", 20261114)
MC_PATHS: int = _env_int("VALUO_MC_PATHS", 10_000)
HORIZON_MONTHS: int = _env_int("VALUO_HORIZON_MONTHS", 36)
HTTP_TIMEOUT_S: float = _env_float("VALUO_HTTP_TIMEOUT_S", 20.0)
# Polite spacing between paginated NearBlocks calls (unauthenticated bursts are rate-limited). 12 pages at 0.4 s
# tripped the unauthenticated 429 limit in testing; 8 pages at 0.8 s did not. reproduce.py's --nearblocks-delay
# defaults to None, so this .env knob is what the collector reads unless the flag is given explicitly.
NEARBLOCKS_PAGE_DELAY_S: float = _env_float("VALUO_NEARBLOCKS_PAGE_DELAY_S", 0.8)
USER_AGENT: str = "valuo-quant/0.1.0 (reproducible research; httpx)"

# ----------------------------------------------------------------------------- Artifacts
ARTIFACTS_DIR: Path = Path(_env("VALUO_ARTIFACTS_DIR", str(REPO_ROOT / "artifacts"))).expanduser().resolve()
RAW_DIR: Path = ARTIFACTS_DIR / "raw"
DUCKDB_PATH: Path = ARTIFACTS_DIR / "valuo.duckdb"
SNAPSHOT_PATH: Path = ARTIFACTS_DIR / "latest_snapshot.json"
MANIFEST_PATH: Path = ARTIFACTS_DIR / "manifest.json"
MEMO_PATH: Path = ARTIFACTS_DIR / "IC_MEMO.md"

# ----------------------------------------------------------------------------- Benchmark recipients
# Dry quotes still require syntactically valid destination/refund addresses (FACTS section 2).
# These are well-known public addresses; nothing is ever sent (every quote uses "dry": true).
# BTC: the BIP173 P2WPKH test-vector address. The BIP173 *example* address bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq
# is on Relay's blocklist (BLOCKED_WALLET_ADDRESS); this one quotes on 1Click, Relay and LI.FI (verified 2026-10-31).
# web/src/lib/corridors.ts honours the same VALUO_BTC_ADDRESS from the repo-root .env.
EVM_ADDRESS: str = _env("VALUO_EVM_ADDRESS", "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
SOL_ADDRESS: str = _env("VALUO_SOL_ADDRESS", "7EcDhSYGxXyscszYEp35KHN8vvw3svAuLKTzXwCFLtV")
BTC_ADDRESS: str = _env("VALUO_BTC_ADDRESS", "bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4")


def live_tests_enabled() -> bool:
    """True when VALUO_LIVE_TESTS=1; gates every @pytest.mark.live test."""
    return os.environ.get("VALUO_LIVE_TESTS", "").strip() == "1"


def nearblocks_headers() -> dict[str, str]:
    """Headers for api.nearblocks.io; adds the optional bearer key when configured."""
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if NEARBLOCKS_API_KEY:
        headers["Authorization"] = f"Bearer {NEARBLOCKS_API_KEY}"
    return headers


def oneclick_headers() -> dict[str, str]:
    """Headers for 1click.chaindefuser.com; adds the optional JWT when configured."""
    headers = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": USER_AGENT}
    if ONECLICK_JWT:
        headers["Authorization"] = f"Bearer {ONECLICK_JWT}"
    return headers


def ensure_artifact_dirs() -> None:
    """Create ARTIFACTS_DIR and RAW_DIR if missing."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def repo_relative(path: Path) -> str | None:
    """``path`` relative to REPO_ROOT as posix (e.g. "artifacts"); None when it lies outside the repository.

    The snapshot must not embed the author's absolute local path, so callers store this instead.
    """
    try:
        return Path(path).resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return None


def artifact_paths(out_dir: Path | None = None) -> dict[str, Path]:
    """Artifact file paths under ``out_dir`` (default ARTIFACTS_DIR): snapshot, manifest, memo, duckdb, raw."""
    base = Path(out_dir).expanduser().resolve() if out_dir is not None else ARTIFACTS_DIR
    return {
        "dir": base, "raw": base / "raw", "duckdb": base / "valuo.duckdb",
        "snapshot": base / "latest_snapshot.json", "manifest": base / "manifest.json", "memo": base / "IC_MEMO.md",
    }


def as_dict() -> dict[str, object]:
    """Non-secret configuration for the console summary / manifest (paths relative to the repo root, never absolute)."""
    return {
        "near_rpc_url": NEAR_RPC_URL,
        "near_rpc_fallback_url": NEAR_RPC_FALLBACK_URL,
        "near_archival_rpc_url": NEAR_ARCHIVAL_RPC_URL,
        "oneclick_api_base": ONECLICK_API_BASE,
        "relay_api_base": RELAY_API_BASE,
        "lifi_api_base": LIFI_API_BASE,
        "across_api_base": ACROSS_API_BASE,
        "nearstats_api_base": NEARSTATS_API_BASE,
        "nearblocks_api_base": NEARBLOCKS_API_BASE,
        "nearblocks_api_key_set": NEARBLOCKS_API_KEY is not None,
        "defillama_api_base": DEFILLAMA_API_BASE,
        "coins_llama_base": COINS_LLAMA_BASE,
        "coingecko_api_base": COINGECKO_API_BASE,
        "seed": SEED,
        "mc_paths": MC_PATHS,
        "horizon_months": HORIZON_MONTHS,
        "http_timeout_s": HTTP_TIMEOUT_S,
        "nearblocks_page_delay_s": NEARBLOCKS_PAGE_DELAY_S,
        "artifacts_dir": repo_relative(ARTIFACTS_DIR) or "<outside repository>",
    }


__all__ = [
    "REPO_ROOT", "QUANT_ROOT",
    "NEAR_RPC_URL", "NEAR_RPC_FALLBACK_URL", "NEAR_ARCHIVAL_RPC_URL",
    "ONECLICK_API_BASE", "ONECLICK_JWT", "RELAY_API_BASE", "LIFI_API_BASE", "ACROSS_API_BASE",
    "NEARSTATS_API_BASE", "NEARBLOCKS_API_BASE", "NEARBLOCKS_API_KEY", "DEFILLAMA_API_BASE",
    "COINS_LLAMA_BASE", "COINGECKO_API_BASE",
    "SEED", "MC_PATHS", "HORIZON_MONTHS", "HTTP_TIMEOUT_S", "NEARBLOCKS_PAGE_DELAY_S", "USER_AGENT",
    "ARTIFACTS_DIR", "RAW_DIR", "DUCKDB_PATH", "SNAPSHOT_PATH", "MANIFEST_PATH", "MEMO_PATH",
    "EVM_ADDRESS", "SOL_ADDRESS", "BTC_ADDRESS",
    "live_tests_enabled", "nearblocks_headers", "oneclick_headers", "ensure_artifact_dirs", "as_dict",
    "repo_relative", "artifact_paths",
]
