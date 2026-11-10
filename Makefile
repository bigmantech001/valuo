.PHONY: reproduce reproduce-fast test test-live invariants dev build bench clean clean-dev sync history bench-history history-summary history-verify anchor-verify anchor-list

# Full live reproduction (the only configuration that writes the CANONICAL artifacts/): fetch NEAR mainnet state +
# router quotes, run the 10,000-path Monte Carlo (seed 20261114), write artifacts/{latest_snapshot.json,manifest.json,
# IC_MEMO.md,valuo.duckdb,raw/} and rewrite the findings block in README.md. No API keys.
reproduce:
	cd quant && uv run python -m valuo.reproduce

# Faster smoke: no live quote race (execution_bench = null), 2,000 paths. Any non-default run writes to
# artifacts/dev/ (never over the canonical files); pass --out DIR to choose another directory.
reproduce-fast:
	cd quant && uv run python -m valuo.reproduce --skip-bench --paths 2000
	@echo "smoke artifacts written to artifacts/dev/ (canonical artifacts/ untouched)"

# Offline unit tests + the five invariant checks against artifacts/ (invariants skip if artifacts are absent).
test:
	cd quant && uv run pytest -q

# Only the mandated invariant suite (needs artifacts/ from `make reproduce`).
invariants:
	cd quant && uv run pytest -q tests/test_invariants.py

# Opt-in tests that hit live endpoints.
test-live:
	cd quant && VALUO_LIVE_TESTS=1 uv run pytest -q -m live

# `next dev` writes to web/.next-dev; `make build` / `npm start` use web/.next (next.config.ts distDir), so a running
# dev server cannot corrupt a production build's route manifests. Do not run two servers on one port.
dev:
	cd web && npm run dev

build:
	cd web && npm run build

# Live 1Click vs Relay vs LI.FI vs Across quote matrix only (prints a table; writes nothing).
bench:
	cd quant && uv run python -m valuo.collectors.execution_bench --no-persist

sync:
	cd quant && uv sync

clean:
	rm -rf artifacts/latest_snapshot.json artifacts/manifest.json artifacts/IC_MEMO.md artifacts/raw artifacts/valuo.duckdb artifacts/valuo.duckdb.wal

clean-dev:
	rm -rf artifacts/dev

# --- History store (artifacts/history/: snapshots.jsonl, bench.jsonl, summary.json, raw/<utc>/*.json.gz) ---
# Append the current canonical artifacts/latest_snapshot.json (de-duplicated by snapshot sha256) and rebuild summary.json.
history:
	cd quant && uv run python -m valuo.history snapshot

# One live quote race (all corridors x clips, concurrency 4): gzip raw responses + sha256 -> bench.jsonl -> summary.json.
bench-history:
	cd quant && uv run python -m valuo.history bench

history-summary:
	cd quant && uv run python -m valuo.history summary

# Re-hash every raw payload referenced by bench.jsonl (gunzip, sha256, compare).
history-verify:
	cd quant && uv run python -m valuo.history verify

# Check the local manifest against the hashes anchored on NEAR mainnet (SocialDB). Key-free:
#   make anchor-verify ANCHOR=<account>.near
anchor-verify:
	cd quant && uv run python -m valuo.anchor verify --account "$(ANCHOR)"

anchor-list:
	cd quant && uv run python -m valuo.anchor list --account "$(ANCHOR)"
