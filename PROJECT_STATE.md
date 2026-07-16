# Retail Media Platform — Project State

**Last updated:** 2026-07-16
**Repository (local):** `/home/cobalt/retail-media-platform-enterprise`
**Canon (ASUSTOR):** `\\192.168.110.118\project\retail-media-platform-enterprise`
**Remote:** `github.com:santanas-dev/retail-media-platform-enterprise`

## Current HEAD

| Branch  | SHA      | Note |
|---------|----------|------|
| develop | 39dc8bc  | H0 fix |
| main    | 4db6dc0  | v0.7 published |

## Active Workstreams

### H0 — Flaky test_backoff_respected_on_second_run ✅ RESOLVED
- **Verdict: confirmed timing flake, not real backoff regression.**
- Root cause: `_make_engine_and_clean()` only deleted `test.relay.%` events. Foreign pending/failed outbox events from other test suites (pop, campaigns) survived cleanup and consumed the shared `fail_next(1)` token.
- Fix (SHA 39dc8bc): `_make_engine_and_clean()` now deletes ALL pending/failed events regardless of event_type. Added +1s margin + 0.1s sleep in per-test isolation.
- CI proof: Run #29515994509 — 34/34 green, behavioural success.
- 10/10 local, 9/9 outbox relay suite.

### C1 — Creative Moderation + Campaign Approval RLS 🟡
- Fix applied on develop (SHA 4adde45 → 39dc8bc)
- 4 endpoints under NOBYPASSRLS, 8 behavioural tests (all pass)
- **NOT CLOSED — merge to main after C2 completes**
- No remaining blockers: ADR-008 gate GREEN ✅ (H0 resolved)
- Bug fixed: `AdvertiserOrganization.name` → `legal_name` (4 places)
- Seed gap closed: `creatives.moderate` in role_permissions for system_admin/security_admin

### C2 — ❗ Next active Critical (after H0)
- Now unblocked: H0 resolved, C1 merge to main comes *after* C2
- Sequence: H0 (done) → C2 → C1 merge to main

## Completed (Player Blockers A1–A3)

| ID | Task | Status |
|----|------|--------|
| A1 S-086 | Inventory availability forecast | ✅ |
| A2 S-087 | Sold-out alternatives | ✅ |
| A3 S-088 | Rules management UI | ✅ |

## Pending

| ID | Task | Status |
|----|------|--------|
| A4 S-089 | Inventory simulation | ⏳ |
| A5 S-090 | Campaign dashboard | ⏳ |
| A6 S-091 | Emergency controls | ⏳ |

## Environment

- **PostgreSQL:** Docker `rmp-phase1-postgres-1` (port 5432)
- **App role:** `retail_media_app` (NOBYPASSRLS)
- **Owner role:** `retail_media_owner` (fixtures)
- **Behavioural:** `RUN_BEHAVIORAL_TESTS=1` + BEHAVIORAL_DB_URL + BEHAVIORAL_APP_DB_URL

## Constraints

- `main` = stable releases, `develop` = active integration
- Protected: `.env`, Docker/deploy scripts, destructive migrations
- RLS on all tenant-scoped tables, NOBYPASSRLS enforced
- Only Hermes pushes to GitHub; ASUSTOR = local canon
