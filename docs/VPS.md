# Scheduled runs on a VPS

Valuo's time series (the terminal's History tab) grows from two jobs that run on a small Linux server and commit their output back to the repository:

| Job | Schedule (UTC) | What it does | Commits |
| :--- | :--- | :--- | :--- |
| `valuo-run.sh snapshot` | daily 06:05 | `make reproduce` (live mainnet, quote race, 10,000-path Monte Carlo), `make test`, append to `artifacts/history/` | `artifacts/`, README findings block |
| `valuo-run.sh bench` | hourly at :17 | live 1Click / Relay / LI.FI / Across quote race, re-hash its raw payloads | `artifacts/history/` |

The schedule lives in `ops/vps/valuo.crontab`; the History tab reads it from there. Both jobs take one lock, so they never write `artifacts/` at the same time. No API keys are needed.

## Requirements

- Debian or Ubuntu, 1 vCPU and 1 GB RAM are enough (a daily run takes 3 to 5 minutes; a race about 1 minute).
- Outbound HTTPS to NEAR RPC, 1Click, Relay, LI.FI, Across, NearBlocks, nearstats.org, DefiLlama, CoinGecko and GitHub.
- A non-root user to own the jobs.

## Setup

1. **Deploy key with write access.** On the VPS, as the job user:
   ```bash
   ssh-keygen -t ed25519 -N "" -f ~/.ssh/valuo_deploy -C "valuo-vps"
   cat ~/.ssh/valuo_deploy.pub
   printf 'Host github.com\n  IdentityFile ~/.ssh/valuo_deploy\n  IdentitiesOnly yes\n' >> ~/.ssh/config
   ssh -o StrictHostKeyChecking=accept-new -T git@github.com   # "Hi bigmantech001/valuo! ..." means the key works
   ```
   In GitHub: repository → Settings → Deploy keys → Add deploy key, paste the public key, tick **Allow write access**.

2. **Install.** Clone once over SSH and run the setup script (it installs git, make, cron and uv, syncs the Python environment, checks push access with a dry run and installs the crontab):
   ```bash
   git clone git@github.com:bigmantech001/valuo.git ~/valuo
   bash ~/valuo/ops/vps/setup.sh
   ```

3. **First runs by hand**, to see them succeed before cron takes over:
   ```bash
   ~/valuo/ops/vps/valuo-run.sh bench
   ~/valuo/ops/vps/valuo-run.sh snapshot
   tail -n 40 ~/valuo-logs/$(date -u +%F)-snapshot.log
   ```

## Optional: anchor each snapshot on NEAR mainnet

After each daily snapshot, the job can write the manifest's hashes to NEAR's SocialDB (`social.near`) under the anchoring account:

```
<account>/valuo/snapshot/<YYYYMMDDTHHMMSSZ> = {"manifest_sha256", "snapshot_sha256", "memo_sha256", "data_block_height", ...}
```

SocialDB records the block each value was written at, so anyone can check, with no key and no account, that a snapshot with exactly these hashes existed at that block: `make anchor-verify ANCHOR=<account>` (or `cd quant && uv run python -m valuo.anchor verify --account <account>`). Editing a committed manifest afterwards breaks the match.

1. Create a NEAR mainnet account for this alone and fund it with about 1 NEAR. Each write attaches 0.01 NEAR, credited to the account's SocialDB storage balance; a record takes about 500 bytes (0.005 NEAR) and the rest carries over to later writes. With gas that is roughly 2 NEAR a year at one write a day; top it up as needed.
2. Put its full-access key on the VPS as the job user (the legacy keychain format near-cli-rs reads):
   ```bash
   mkdir -p ~/.near-credentials/mainnet && chmod 700 ~/.near-credentials
   cat > ~/.near-credentials/mainnet/<account>.json <<'EOF'
   {"account_id":"<account>","public_key":"ed25519:...","private_key":"ed25519:..."}
   EOF
   chmod 600 ~/.near-credentials/mainnet/<account>.json
   ```
3. Re-run setup with the account: `VALUO_ANCHOR_ACCOUNT=<account> bash ~/valuo/ops/vps/setup.sh`. It installs near-cli-rs and adds `VALUO_ANCHOR_ACCOUNT` to the crontab block.

An anchoring failure (for example an empty balance) is logged and does not fail the run; that snapshot is simply not anchored.

## Operating it

- Logs: `~/valuo-logs/<date>-<job>.log`, kept 30 days.
- Dry run without pushing: `VALUO_PUSH=0 ~/valuo/ops/vps/valuo-run.sh bench`.
- Optional higher NearBlocks limits: put `NEARBLOCKS_API_KEY=...` at the top of the crontab (`crontab -e`). Not required.
- Pause: `crontab -e` and comment out the lines between `# >>> valuo >>>` and `# <<< valuo <<<`. Remove: delete that block.
- Code updates: push to `main` as usual; each job fast-forwards the checkout before it runs. If you push while a job is running, the job rebases its data commit onto your commit and keeps its own output for the data files.
- If a run's log ends in `FAILED`, the next scheduled run starts clean; a data commit that could not be pushed stays local and goes out with the next successful push.
