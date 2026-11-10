#!/usr/bin/env bash
# Install the Valuo jobs on a SHARED server without touching anything else on it. Run as root AFTER the job user
# exists, has its deploy key and has run ops/vps/setup.sh-equivalent steps (clone + `make sync`; see docs/VPS.md,
# "Shared server"). What this script changes, and nothing more:
#   - root's crontab: appends (or replaces) one block between `# >>> valuo >>>` and `# <<< valuo <<<`.
# Each job then runs as the unprivileged job user inside a transient systemd scope with a hard memory cap and low
# CPU / IO priority, so a misbehaving run is killed by the kernel instead of competing with the server's services.
# No packages are installed and no service is started, stopped or restarted.
#
#   VALUO_USER=valuo VALUO_MEM_MAX=768M bash ops/vps/install-shared.sh
set -Eeuo pipefail

U="${VALUO_USER:-valuo}"
HOME_U="$(getent passwd "$U" | cut -d: -f6)"
REPO="${VALUO_REPO:-$HOME_U/valuo}"
MEM="${VALUO_MEM_MAX:-768M}"
SWAP="${VALUO_SWAP_MAX:-128M}"
[ "$(id -u)" = 0 ] || { echo "run as root (it writes root's crontab to use systemd-run --uid)" >&2; exit 1; }
[ -n "$HOME_U" ] || { echo "user $U does not exist" >&2; exit 1; }
[ -x "$REPO/ops/vps/valuo-run.sh" ] || { echo "$REPO/ops/vps/valuo-run.sh missing or not executable" >&2; exit 1; }

wrap="/usr/bin/systemd-run --quiet --scope --uid=$U --gid=$U -p MemoryMax=$MEM -p MemorySwapMax=$SWAP -p CPUWeight=20 -p IOWeight=20 /usr/bin/env HOME=$HOME_U USER=$U LOGNAME=$U /usr/bin/nice -n 10 $REPO/ops/vps/valuo-run.sh"
extra_env=""
[ -n "${VALUO_ANCHOR_ACCOUNT:-}" ] && extra_env="VALUO_ANCHOR_ACCOUNT=$VALUO_ANCHOR_ACCOUNT "

tmp="$(mktemp)"
{ crontab -l 2>/dev/null | sed '/# >>> valuo >>>/,/# <<< valuo <<</d' || true
  echo "# >>> valuo >>>"
  # Only the job lines: the block sits at the end of root's crontab, and no CRON_TZ/SHELL line is added so the
  # server's other entries are unaffected (the server clock must be UTC; checked below).
  grep -E '^[0-9*]' "$REPO/ops/vps/valuo.crontab" | sed "s|__REPO__/ops/vps/valuo-run.sh|${extra_env//|/\\|}$wrap|"
  echo "# <<< valuo <<<"; } >"$tmp"
crontab "$tmp"
rm -f "$tmp"
crontab -l | sed -n '/# >>> valuo >>>/,/# <<< valuo <<</p'
[ "$(date +%Z)" = UTC ] || echo "WARNING: server timezone is $(date +%Z), not UTC; the schedule in valuo.crontab is UTC" >&2
