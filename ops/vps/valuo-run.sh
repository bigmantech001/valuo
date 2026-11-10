#!/usr/bin/env bash
# Valuo scheduled job runner for a VPS (replaces CI). Called from cron (see valuo.crontab):
#
#   valuo-run.sh snapshot   daily: canonical `make reproduce` -> `make test` -> append to the history store
#   valuo-run.sh bench      hourly: live quote race -> append to bench history -> re-hash its raw payloads
#
# Then it commits artifacts/ (and the README findings block for `snapshot`) and pushes to the repository.
# Zero API keys. One lock serializes both jobs so they never write artifacts/ at the same time.
#
# Environment (all optional; defaults suit the layout made by setup.sh):
#   VALUO_REPO        repository checkout          (default: the checkout this script lives in)
#   VALUO_BRANCH      branch to commit to          (default: main)
#   VALUO_LOG_DIR     log directory                (default: $HOME/valuo-logs)
#   VALUO_PUSH        set to 0 to commit locally without pushing (dry runs)
#   NEARBLOCKS_API_KEY  passed through to the pipeline if set (raises NearBlocks rate limits; not required)
#   VALUO_ANCHOR_ACCOUNT  NEAR account that anchors each snapshot's hashes in SocialDB (snapshot mode only;
#                         its key must be in ~/.near-credentials/mainnet/<account>.json, see docs/VPS.md)
set -Eeuo pipefail

MODE="${1:-}"
case "$MODE" in
  snapshot | bench) ;;
  *)
    echo "usage: $0 snapshot|bench" >&2
    exit 2
    ;;
esac

REPO="${VALUO_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
BRANCH="${VALUO_BRANCH:-main}"
LOG_DIR="${VALUO_LOG_DIR:-$HOME/valuo-logs}"
LOCK="${TMPDIR:-/tmp}/valuo-artifacts.lock"
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

mkdir -p "$LOG_DIR"
find "$LOG_DIR" -name "*.log" -mtime +30 -delete 2>/dev/null || true
LOG="$LOG_DIR/$(date -u +%Y-%m-%d)-$MODE.log"
exec >>"$LOG" 2>&1
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) valuo $MODE start (repo $REPO, branch $BRANCH)"
trap 'echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) valuo $MODE FAILED at line $LINENO (exit $?)"' ERR

# One job at a time. A daily run takes a few minutes; a race that finds the lock held waits up to 20 minutes.
exec 9>"$LOCK"
if ! flock -w 1200 9; then
  echo "another valuo job still holds $LOCK after 20 minutes; skipping this $MODE run"
  exit 0
fi

cd "$REPO"
git fetch --quiet origin "$BRANCH"
git checkout --quiet "$BRANCH"
# Start from the remote tip so code changes pushed from elsewhere are picked up. The runner only ever adds
# data commits, so a fast-forward is the normal case; anything else is reported and the run stops.
if ! git merge --ff-only --quiet "origin/$BRANCH"; then
  echo "local $BRANCH has diverged from origin/$BRANCH; resolve by hand (git status) before the next run"
  exit 1
fi

make sync >/dev/null

if [ "$MODE" = snapshot ]; then
  make reproduce
  make test
  (cd quant && uv run python -m valuo.history snapshot)
  paths=(artifacts README.md)
  msg="data: canonical snapshot $(date -u +%Y-%m-%dT%H:%MZ)"
else
  make bench-history
  make history-verify
  paths=(artifacts/history)
  msg="data: quote race $(date -u +%Y-%m-%dT%H:%MZ)"
fi

git add -A -- "${paths[@]}"
if git diff --cached --quiet; then
  echo "no changes to commit"
  echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) valuo $MODE done (nothing new)"
  exit 0
fi
git -c user.name="${VALUO_GIT_NAME:-valuo-bot}" -c user.email="${VALUO_GIT_EMAIL:-valuo-bot@users.noreply.github.com}" commit --quiet -m "$msg"

# Anchor the committed manifest's hashes on NEAR mainnet (optional). valuo.anchor signs with the account key in
# ~/.near-credentials/mainnet/<account>.json via the system openssl. A failure is logged, never fatal: the data
# commit is still valid; it is just not anchored on-chain this run.
if [ "$MODE" = snapshot ] && [ -n "${VALUO_ANCHOR_ACCOUNT:-}" ]; then
  if (cd quant && uv run python -m valuo.anchor publish --account "$VALUO_ANCHOR_ACCOUNT"); then
    (cd quant && uv run python -m valuo.anchor verify --account "$VALUO_ANCHOR_ACCOUNT" >/dev/null) && echo "anchor: verified on-chain" ||
      echo "anchor: written, verify did not match yet (finality lag?); re-check with make anchor-verify"
  else
    echo "anchor: publish failed; snapshot not anchored this run"
  fi
fi

if [ "${VALUO_PUSH:-1}" = 0 ]; then
  echo "VALUO_PUSH=0: committed locally, not pushed"
  exit 0
fi

# Someone may push code while a run is in progress. Rebase this data commit onto the new tip; on a
# conflict inside the paths this job owns, keep this run's output (it is the newest measurement).
for attempt in 1 2 3 4 5; do
  if git push --quiet origin "HEAD:$BRANCH"; then
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) valuo $MODE done (pushed $(git rev-parse --short HEAD))"
    exit 0
  fi
  echo "push rejected; rebasing onto origin/$BRANCH (attempt $attempt)"
  git fetch --quiet origin "$BRANCH"
  if ! git rebase --quiet -X theirs "origin/$BRANCH"; then
    git rebase --abort || true
    echo "rebase failed; leaving the data commit local for the next run to retry"
    exit 1
  fi
  sleep $((attempt * 5))
done
echo "could not push after 5 attempts; the data commit stays local and the next run retries" >&2
exit 1
