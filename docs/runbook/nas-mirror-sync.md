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

## santa2 Relay Cron

On santa2 (Linux machine with NAS mounted at `/mnt/nas/`):

```bash
# Crontab on santa2 (every 3 minutes):
*/3 * * * * cd /mnt/nas/retail-media-platform-enterprise && git fetch origin && git reset --hard origin/develop && /path/to/docs/runbook/mirror-check.sh --discover-origin --nas-path /mnt/nas/retail-media-platform-enterprise
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

## Why Not NAS Self-Pull?

NAS self-pull cron (`git fetch origin` directly from NAS) was an early design
considered in CONSOLIDATE-CANON-001A. It was rejected because:

1. NAS has no GitHub trust (no SSH key, no deploy key) — and should not.
2. Storing GitHub credentials on a network-attached storage device is a security regression.
3. santa2 relay keeps the trust boundary clean: santa2 is the only machine with
   GitHub access; NAS receives updates passively through the mount.

The NAS self-pull pattern is **not a future target** — it is explicitly deprecated.
santa2 relay is the canonical sync mechanism.
