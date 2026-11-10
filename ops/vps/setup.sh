#!/usr/bin/env bash
# One-time setup of the Valuo scheduled jobs on a Debian/Ubuntu VPS. Run as the user that will own the jobs
# (not root). Idempotent: re-running updates the checkout, the Python env and the crontab.
#
#   VALUO_REMOTE=git@github.com:bigmantech001/valuo.git bash ops/vps/setup.sh
#
# Optional on-chain anchoring: VALUO_ANCHOR_ACCOUNT=<account>.near bash ops/vps/setup.sh installs near-cli-rs and
# puts the account into the crontab block; its key must be in ~/.near-credentials/mainnet/<account>.json.
#
# Needs: an SSH deploy key with WRITE access to the repository, already loaded for this user (see docs/VPS.md).
set -Eeuo pipefail

REMOTE="${VALUO_REMOTE:-git@github.com:bigmantech001/valuo.git}"
REPO="${VALUO_REPO:-$HOME/valuo}"
BRANCH="${VALUO_BRANCH:-main}"

step() { printf '\n== %s\n' "$*"; }

step "system packages (git, make, curl, rsync, cron, flock)"
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq
  sudo apt-get install -y -qq git make curl rsync cron util-linux ca-certificates >/dev/null
  sudo systemctl enable --now cron >/dev/null 2>&1 || true
else
  echo "not a Debian/Ubuntu host: install git, make, curl, rsync, cron and flock yourself, then re-run" >&2
fi

step "uv (Python toolchain; installs Python 3.12 on demand)"
if ! command -v uv >/dev/null && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version

step "repository checkout at $REPO"
if [ -d "$REPO/.git" ]; then
  git -C "$REPO" fetch --quiet origin "$BRANCH"
  git -C "$REPO" checkout --quiet "$BRANCH"
  git -C "$REPO" merge --ff-only --quiet "origin/$BRANCH"
else
  git clone --quiet --branch "$BRANCH" "$REMOTE" "$REPO"
fi
chmod +x "$REPO/ops/vps/valuo-run.sh"

step "Python environment"
make -C "$REPO" sync

step "push access check (dry run, nothing is changed on the remote)"
git -C "$REPO" push --dry-run origin "HEAD:$BRANCH"

ANCHOR="${VALUO_ANCHOR_ACCOUNT:-}"
if [ -n "$ANCHOR" ]; then
  step "on-chain anchoring as $ANCHOR (near-cli-rs)"
  if ! command -v near >/dev/null && [ ! -x "$HOME/.cargo/bin/near" ]; then
    curl --proto '=https' --tlsv1.2 -LsSf https://github.com/near/near-cli-rs/releases/latest/download/near-cli-rs-installer.sh | sh
  fi
  export PATH="$HOME/.cargo/bin:$PATH"
  near --version
  if [ ! -f "$HOME/.near-credentials/mainnet/$ANCHOR.json" ]; then
    echo "missing $HOME/.near-credentials/mainnet/$ANCHOR.json: anchoring will be skipped until the key is there (docs/VPS.md)" >&2
  fi
fi

step "clock"
echo "server time: $(date) | UTC: $(date -u)"
echo "the crontab sets CRON_TZ=UTC; if your cron ignores CRON_TZ, run: sudo timedatectl set-timezone UTC"

step "crontab"
tmp="$(mktemp)"
{ crontab -l 2>/dev/null | sed '/# >>> valuo >>>/,/# <<< valuo <<</d' || true
  echo "# >>> valuo >>>"
  if [ -n "$ANCHOR" ]; then echo "VALUO_ANCHOR_ACCOUNT=$ANCHOR"; fi
  sed "s|__REPO__|$REPO|g" "$REPO/ops/vps/valuo.crontab"
  echo "# <<< valuo <<<"; } >"$tmp"
crontab "$tmp"
rm -f "$tmp"
crontab -l | sed -n '/# >>> valuo >>>/,/# <<< valuo <<</p'

step "done"
cat <<EOF
Jobs installed. Try them by hand first (each commits and pushes on success):
  $REPO/ops/vps/valuo-run.sh bench      # about 1 minute
  $REPO/ops/vps/valuo-run.sh snapshot   # 3 to 5 minutes
Logs: ~/valuo-logs/<date>-<job>.log
Dry run without pushing: VALUO_PUSH=0 $REPO/ops/vps/valuo-run.sh bench
EOF
