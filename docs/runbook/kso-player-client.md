# KSO Player Client — Runbook

Hardware-independent enterprise KSO contract client. NOT a production KSO runtime.
Real KSO player requires KSO-ENV-001 (real Sherman-J/KSO environment audit) before
any scheduler, kiosk, or media playback work.

## Setup

```bash
# 1. Start dev stack
cd infra/compose
docker compose -f docker-compose.phase1.yml up -d postgres redis minio control-api device-gateway

# 2. Ensure device exists and is active
# Seed creates KSO-001 (00000000-0000-0000-0000-000000000020).
# If not active: UPDATE physical_devices SET status='active' WHERE id='...'

# 3. Install dependencies
pip install requests pyjwt
```

## Run

```bash
cd retail-media-platform-enterprise

PLAYER_GATEWAY_URL=http://localhost:8001 \
  PYTHONPATH=apps/kso-player-client \
  python apps/kso-player-client/main.py --once
```

## Expected output (no manifest available)

```
[AUTH] using configured JWT
[MANIFEST] FAILED: manifest missing signature (signing_key configured)
```

When manifest exists:
```
[MANIFEST] m-001 (verified=True, emergency=False)
[HEARTBEAT] accepted=True server_time=...
[POP] accepted=1 rejected=0 quarantined=0
[DONE] client loop complete
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Config error |
| 3 | Auth failure |
| 4 | Manifest failure |
| 5 | Heartbeat failure |
| 6 | PoP failure |

## Env vars

| Variable | Default | Description |
|----------|---------|-------------|
| PLAYER_GATEWAY_URL | http://localhost:8001 | Device-gateway URL (manifest + heartbeat) |
| PLAYER_CONTROL_URL | http://localhost:8000 | Control-api URL (PoP batch) |
| PLAYER_SIGNING_KEY | "" | MANIFEST_SIGNING_KEY for verification |
| PLAYER_DEVICE_JWT | "" | Pre-configured JWT (skip auth) |
| PLAYER_DEVICE_CODE | "" | Device code for onboarding |
| PLAYER_DEVICE_SECRET | "" | Device secret for onboarding |
| PLAYER_RETAILER_ID | "" | Retailer UUID |
| PLAYER_MAX_RETRIES | 3 | Max HTTP retries |

## Non-goals

- Real kiosk deployment / Chromium / X11
- Media playback UI
- Offline cache / filesystem persistence
- Command channel
- Staged rollout
- Media download
- Channel Orchestrator

---

## EPIC-L-000 — Licensing Seat-Hook Requirement

**Added:** 2026-07-30.

Future real KSO/device enrollment MUST include a license seat reservation hook.
The hardware-independent contract client must not be extended to real enrollment
without this boundary. Retrofit is expensive — plan the hook at enrollment design time.

See: `docs/architecture/epic-l-licensing.md`, `docs/product/user-journeys.md` §EPIC-L.
- Old repo KSO code import (except retry_backoff.py)
