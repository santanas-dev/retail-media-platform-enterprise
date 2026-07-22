# NAS Mirror Sync — Operator Runbook

**SOURCE-TRUTH-001:** GitHub `origin/develop` is the sole git-source-of-truth.
NAS/ASUSTOR at `\\192.168.110.118\project\retail-media-platform-enterprise`
is a mirror — it may be stale.

## Architecture: Hermes-Owned Mirror Sync

```
GitHub (origin/develop)
    ↑ HTTPS (git fetch)
 Hermes host (cobalt) — cron every 3 min
    ↓ CIFS mount at /mnt/asustor-project/
NAS/ASUSTOR mirror (passive CIFS write)
```

1. **Hermes host** fetches `origin/develop`, `origin/main`, and all tags from GitHub via HTTPS.
2. **Hermes host** resets the NAS clone to `origin/develop`, updates `main` branch pointer, and syncs tags — writes through the local CIFS mount.
3. Cycle: **every 3 minutes** (Hermes cron job `c0687f5ced4d`, script `nas-mirror-sync.sh`).
4. NAS itself has **no GitHub trust** — no SSH key, no deploy key, no HTTPS token stored on NAS.
5. **santa2 relay is DEPRECATED** — replaced by Hermes-owned sync as of NAS-SYNC-OWNER-001.

## Operator: NAS Mount Setup

**One-time operator task.** Hermes only documents the procedure; operator owns credentials and mount.
Once mounted, Hermes cron handles ongoing sync.

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
sudo mkdir -p /mnt/asustor-project
sudo mount -t cifs //192.168.110.118/project /mnt/asustor-project \
  -o credentials=/etc/nas-cred,uid=$(id -u),gid=$(id -g),iocharset=utf8,file_mode=0664,dir_mode=0775
```

### 4. Persist across reboots (/etc/fstab)

Add this line to `/etc/fstab` (replace `<uid>` and `<gid>` with output of `id -u` / `id -g`):

```
//192.168.110.118/project /mnt/asustor-project cifs credentials=/etc/nas-cred,uid=<uid>,gid=<gid>,iocharset=utf8,file_mode=0664,dir_mode=0775,_netdev,nofail 0 0
```

`_netdev` ensures mount waits for network; `nofail` prevents boot hang if NAS is unreachable.

### 5. Git-over-CIFS hygiene

CIFS may produce spurious mode-change noise (executable bits). Disable file-mode tracking
in the NAS clone:

```bash
cd /mnt/asustor-project/retail-media-platform-enterprise
git config core.fileMode false
```

This is a local repo config — it does not affect the GitHub origin.

### 6. Verify mount

```bash
ls /mnt/asustor-project/retail-media-platform-enterprise/.git
git -C /mnt/asustor-project/retail-media-platform-enterprise remote -v
```

Expected: `origin  https://github.com/santanas-dev/retail-media-platform-enterprise.git (fetch)`

## Hermes Cron: NAS Mirror Sync

**Owner:** Hermes agent. **Schedule:** every 3 minutes. **Job ID:** `c0687f5ced4d`.

Script: `~/.hermes/scripts/nas-mirror-sync.sh`
Log: `~/.hermes/cron/nas-mirror-sync.log`

What it does each tick:
1. `git fetch origin develop main --tags`
2. Capture working tree dirtiness for diagnostics (first 5 dirty files)
3. `git reset --hard origin/develop` (working tree on develop) — stderr captured to log on failure
4. `git branch -f main origin/main` (update main branch pointer)
5. Log result: synced/up-to-date/stale with develop+main SHAs

To verify the cron is running:

```bash
tail -20 ~/.hermes/cron/nas-mirror-sync.log

# Manual run:
bash ~/.hermes/scripts/nas-mirror-sync.sh
```

## Operator Verification Procedure

Run from Hermes host (cobalt, local mount at `/mnt/asustor-project/`):

```bash
# Compare NAS HEAD vs GitHub origin (all refs):
ORIGIN_DEV=$(git ls-remote origin refs/heads/develop | awk '{print $1}')
NAS_DEV=$(git -C /mnt/asustor-project/retail-media-platform-enterprise rev-parse develop)
ORIGIN_MAIN=$(git ls-remote origin refs/heads/main | awk '{print $1}')
NAS_MAIN=$(git -C /mnt/asustor-project/retail-media-platform-enterprise rev-parse main)
echo "develop: origin=$ORIGIN_DEV NAS=$NAS_DEV"
echo "main:    origin=$ORIGIN_MAIN NAS=$NAS_MAIN"
[ "$ORIGIN_DEV" = "$NAS_DEV" ] && [ "$ORIGIN_MAIN" = "$NAS_MAIN" ] \
  && echo "✅ SYNCED" || echo "❌ STALE"
```

### Result: verified

NAS matches GitHub origin. Update PROJECT_STATE:

```
| NAS mirror (ASUSTOR) | verified | <sha> | Hermes cron, verified <timestamp> |
```

### Result: stale

NAS is behind. Hermes cron should catch this automatically on next cycle.
For immediate fix:

```bash
cd /mnt/asustor-project/retail-media-platform-enterprise
git fetch origin
git reset --hard origin/develop
```

Then re-verify and update PROJECT_STATE.

### Result: dirty working tree (deleted/modified files)

NAS working tree has uncommitted changes (e.g. deleted files, modified binaries).
This blocks `git reset --hard` if CIFS locks interfere. The cron script now logs
the dirtiness state before attempting reset for diagnostics.

Recovery procedure:

```bash
cd /mnt/asustor-project/retail-media-platform-enterprise
# Verify origin is reachable
git fetch origin develop main --tags
# Force-reset to origin (discards ALL local changes — mirror is derived)
git reset --hard origin/develop
git branch -f main origin/main
# Verify clean
git status --short --branch
```

If `reset --hard` fails with permission errors:
1. Check CIFS mount is writable: `touch /mnt/asustor-project/.../.test_write && rm $_`
2. If mount is read-only, remount per step 3 above.
3. If individual files are locked (CIFS `oplocks`), wait 30s and retry.

Root cause: CIFS over a network can transiently deny write access to files
held by another client (Codex, Windows Explorer, Samba oplocks). The cron script
treats this as a hard failure and logs the exact stderr for diagnosis.

### Result: mount unavailable

If `/mnt/asustor-project/` is not mounted, Hermes cron log will show errors.
Operator must remount per step 3 above.

## Operator: Remove Deprecated santa2 Key

santa2 relay is DEPRECATED. Remove its SSH authorized key from the NAS:

```bash
# Run ON THE NAS (admin@192.168.110.118):
sed -i '/santa2-nas-sync/d' /home/admin/.ssh/authorized_keys
grep "santa2-nas-sync" /home/admin/.ssh/authorized_keys && echo "KEY STILL PRESENT" || echo "KEY REMOVED"
```

## Hermes Agent Rules

From `AGENTS.md`:

- **Hermes owns mirror sync freshness.** The cron job `c0687f5ced4d` syncs every 3 minutes.
- Agent must NOT claim "NAS synced" without actual verification: NAS develop == origin/develop, NAS main == origin/main, and release tags present.
- After Hermes push, NAS should catch up within 3 minutes via cron — verify before claiming.
- If NAS mount is unavailable, state: `pending | mount unavailable` — not `verified`.
- GitHub + CI green is sufficient for task DONE — mirror sync is tracked separately
  in PROJECT_STATE Repository Checkpoint.

## Warnings

- **git over CIFS is less reliable than local disk.** Possible issues: lock contention,
  permission drift, latency spikes. Monitor `nas-mirror-sync.log` for anomalies.
- **NAS does NOT pull GitHub directly.** The trust boundary is: GitHub → Hermes host (HTTPS) →
  NAS (passive CIFS write). No deploy key, SSH key, GitHub token, or `known_hosts` entry
  for GitHub lives on the NAS device.
- **Hermes does NOT execute mount or credential setup.** These are one-time operator tasks.
  Hermes owns ongoing sync via cron; operator owns the CIFS mount.

## Why Not NAS Self-Pull?

NAS self-pull cron (`git fetch origin` directly from NAS) was an early design
considered in CONSOLIDATE-CANON-001A. It was rejected because:

1. NAS has no GitHub trust (no SSH key, no deploy key) — and should not.
2. Storing GitHub credentials on a network-attached storage device is a security regression.
3. Hermes relay keeps the trust boundary clean: Hermes host is the only machine with
   GitHub access; NAS receives updates passively through the mount.

The NAS self-pull pattern is **not a future target** — it is explicitly deprecated.
Hermes-owned mirror sync is the canonical sync mechanism as of NAS-SYNC-OWNER-001.
