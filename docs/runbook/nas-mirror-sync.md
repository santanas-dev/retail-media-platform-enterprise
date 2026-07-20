# NAS Mirror Sync — Operator Runbook

**SOURCE-TRUTH-001:** GitHub `origin/develop` is the sole git-source-of-truth.
NAS/ASUSTOR at `\\192.168.110.118\project\retail-media-platform-enterprise`
is a mirror — it may be stale.

## Architecture: santa2 Relay

NAS **never** pulls GitHub directly. The relay pattern:

```
GitHub (origin/develop)
    ↑ HTTPS (git fetch)
 santa2 (operator machine)
    ↓ local filesystem (NAS mounted at /mnt/nas/…)
NAS/ASUSTOR mirror
    ↑ mirror-check.sh verifies
```

1. **santa2** fetches `origin/develop` from GitHub via **HTTPS** (no SSH, no deploy key on NAS).
2. **santa2** resets the NAS clone to `origin/develop` — writes through the local NAS mount.
3. **mirror-check.sh** runs post-sync to confirm NAS HEAD matches GitHub origin.
4. Cycle: **every 3 minutes** (santa2 cron or systemd timer).
5. NAS itself has **no GitHub trust** — no SSH key, no deploy key, no HTTPS token stored on NAS.

## Operator: NAS Mount Setup

**Hermes agents MUST NOT execute this setup.** This is a one-time operator/santa2 task.
Hermes only documents the procedure; the operator owns credentials, mount, and cron.

### 1. Install CIFS tooling

```bash
sudo apt-get update
sudo apt-get install -y cifs-utils
```

### 2. Create credentials file

```bash
sudo tee /etc/nas-cred > /dev/null <<'EOF'
username=<samba_user>
password=<samba_password>
EOF
sudo chmod 600 /etc/nas-cred
```

### 3. Mount NAS share

```bash
sudo mkdir -p /mnt/nas
sudo mount -t cifs //192.168.110.118/project /mnt/nas \
  -o credentials=/etc/nas-cred,uid=$(id -u),gid=$(id -g),iocharset=utf8,file_mode=0664,dir_mode=0775
```

### 4. Persist across reboots (/etc/fstab)

Add this line to `/etc/fstab` (replace `<santa2_uid>` and `<santa2_gid>` with output of `id -u` / `id -g`):

```
//192.168.110.118/project /mnt/nas cifs credentials=/etc/nas-cred,uid=<santa2_uid>,gid=<santa2_gid>,iocharset=utf8,file_mode=0664,dir_mode=0775,_netdev,nofail 0 0
```

`_netdev` ensures mount waits for network; `nofail` prevents boot hang if NAS is unreachable.

### 5. Git-over-CIFS hygiene

CIFS may produce spurious mode-change noise (executable bits). Disable file-mode tracking
in the NAS clone:

```bash
cd /mnt/nas/retail-media-platform-enterprise
git config core.fileMode false
```

This is a local repo config — it does not affect the GitHub origin.

### 6. Verify mount

```bash
ls /mnt/nas/retail-media-platform-enterprise/.git
git -C /mnt/nas/retail-media-platform-enterprise remote -v
```

Expected: `origin  https://github.com/santanas-dev/retail-media-platform-enterprise.git (fetch)`

## santa2 Relay Cron

On santa2 (Linux machine with NAS mounted at `/mnt/nas/`):

```bash
# Crontab on santa2 (every 3 minutes):
*/3 * * * * cd /mnt/nas/retail-media-platform-enterprise && git fetch origin develop && git reset --hard origin/develop && ./docs/runbook/mirror-check.sh --discover-origin --nas-path /mnt/nas/retail-media-platform-enterprise
```

**Hermes agents MUST NOT configure this cron, SSH keys, or GitHub tokens.**
This is a one-time operator/santa2 task.

## Operator Verification Procedure

Run from **santa2** (or any machine with both GitHub HTTPS and NAS access):

```bash
# Discover current origin SHA and compare against NAS mirror:
./docs/runbook/mirror-check.sh --discover-origin --nas-path /mnt/nas/retail-media-platform-enterprise

# Or with known SHA:
EXPECTED_ORIGIN_DEVELOP_SHA=<sha> ./docs/runbook/mirror-check.sh --nas-path /mnt/nas/retail-media-platform-enterprise
```

### Result: verified (exit 0)

NAS matches GitHub origin. Update PROJECT_STATE:

```
| NAS mirror (ASUSTOR) | verified | <sha> (via operator/santa2) | <date> |
```

### Result: stale (exit 1)

NAS is behind. santa2 relay should catch this automatically on next cycle.
For immediate fix on santa2:

```bash
cd /mnt/nas/retail-media-platform-enterprise
git fetch origin
git reset --hard origin/develop
git log --oneline -3   # verify
```

Then re-run mirror-check and update PROJECT_STATE.

### Result: cannot-verify-from-here (exit 0)

Network, GitHub, or NAS unreachable. Honest status — do not falsify.

## Hermes Agent Rules

From `AGENTS.md`:

- Agent must NOT claim "NAS synced" without mirror-check proof.
- Hermes is **not the owner** of mirror freshness — santa2 relay is.
- After Hermes push, the honest state is: **mirror-check pending — santa2 relay will sync**.
- If mirror-check cannot run from agent's environment → `cannot-verify-from-here` / `pending`.
  Never `verified` and never `stale` without actual proof.
- GitHub + CI green is sufficient for task DONE — mirror sync is tracked separately
  in PROJECT_STATE Repository Checkpoint.

## Warnings

- **git over CIFS is less reliable than local disk.** Possible issues: lock contention,
  permission drift, latency spikes. The operator must monitor cron logs and mirror-check
  output for anomalies.
- **NAS does NOT pull GitHub directly.** The trust boundary is: GitHub → santa2 (HTTPS) →
  NAS (passive CIFS write). No deploy key, SSH key, GitHub token, or `known_hosts` entry
  for GitHub lives on the NAS device.
- **Hermes does NOT execute mount, credentials, or cron setup.** These are one-time
  operator/santa2 tasks. Hermes documents the procedure; the operator owns the execution
  and ongoing monitoring.

## Why Not NAS Self-Pull?

NAS self-pull cron (`git fetch origin` directly from NAS) was an early design
considered in CONSOLIDATE-CANON-001A. It was rejected because:

1. NAS has no GitHub trust (no SSH key, no deploy key) — and should not.
2. Storing GitHub credentials on a network-attached storage device is a security regression.
3. santa2 relay keeps the trust boundary clean: santa2 is the only machine with
   GitHub access; NAS receives updates passively through the mount.

The NAS self-pull pattern is **not a future target** — it is explicitly deprecated.
santa2 relay is the canonical sync mechanism.
