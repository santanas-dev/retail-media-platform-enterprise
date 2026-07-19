# NAS Mirror Sync — Operator Runbook

**SOURCE-TRUTH-001:** GitHub `origin/develop` is the sole git-source-of-truth.
NAS/ASUSTOR at `\\192.168.110.118\project\retail-media-platform-enterprise`
is a mirror — it may be stale.

## Current State

Mirror sync is **operator-driven** until NAS self-pull infrastructure is configured.

- **After Hermes push:** PROJECT_STATE records "mirror-check pending."
- **Operator/santa2:** runs verification, updates PROJECT_STATE with result.
- **Future target:** NAS self-pull cron (`git fetch origin && git reset --hard origin/develop`)
  after NAS→GitHub trust is configured (SSH deploy key or HTTPS token).

## Operator Verification Procedure

Run from **santa2** (or any machine with both GitHub and NAS access):

```bash
# 1. Discover current origin SHA
./docs/runbook/mirror-check.sh --discover-origin --nas-path /mnt/nas/retail-media-platform-enterprise

# 2. Or with known SHA:
EXPECTED_ORIGIN_DEVELOP_SHA=<sha> ./docs/runbook/mirror-check.sh --nas-path /mnt/nas/retail-media-platform-enterprise
```

### Result: verified (exit 0)
NAS matches GitHub origin. Update PROJECT_STATE:

```
| NAS mirror (ASUSTOR) | verified | <sha> (via operator/santa2) | <date> |
```

### Result: stale (exit 1)
NAS is behind. Pull on NAS:

```bash
cd /mnt/nas/retail-media-platform-enterprise
git fetch origin
git reset --hard origin/develop
git log --oneline -3   # verify
```

Then re-run mirror-check and update PROJECT_STATE.

### Result: cannot-verify-from-here (exit 2)
Network, GitHub, or NAS unreachable. Honest status — do not falsify.

## NAS Self-Pull Cron (Future)

After operator configures NAS→GitHub trust (deploy key or HTTPS token):

```bash
# Crontab on NAS (every 5 minutes):
*/5 * * * * cd /volume1/project/retail-media-platform-enterprise && git fetch origin && git reset --hard origin/develop
```

**Hermes agents MUST NOT configure the deploy key/token.** This is a one-time operator task.

## Hermes Agent Rules

From `AGENTS.md`:

- Agent must NOT claim "NAS synced" without mirror-check proof.
- SSH-unavailable → "cannot verify from here" (not "stale," not "synced").
- Mirror-check pending is a valid post-push state.
- GitHub + CI green is sufficient for task DONE — mirror sync is tracked separately.
