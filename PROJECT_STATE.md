# Retail Media Platform — Project State

**Last updated:** 2026-07-16
**Repository (local):** `/home/cobalt/retail-media-platform-enterprise`
**Canon (ASUSTOR):** `\\192.168.110.118\project\retail-media-platform-enterprise`
**Remote:** `github.com:santanas-dev/retail-media-platform-enterprise`

## Current HEAD

| Branch  | SHA      | Note |
|---------|----------|------|
| develop | 8930e3e  | C1 docs commit |
| main    | 4db6dc0  | v0.7 published |

## Active Workstreams

### C1 — Creative Moderation + Campaign Approval RLS 🟡
- Fix applied on develop (SHA 4adde45 → 8930e3e)
- 4 endpoints under NOBYPASSRLS, 8 behavioural tests (all pass locally)
- **NOT CLOSED — blocked on:**
  a) ADR-008 gate (behavioural CI) must be **green** — currently red due to H0 flaky test
  b) Merge to main pending
- Bug fixed: `AdvertiserOrganization.name` → `legal_name` (4 places)
- Seed gap closed: `creatives.moderate` in role_permissions for system_admin/security_admin

### C2 — ❗ Only open Critical
- Blocked behind H0 + C1 closure

### H0 — Flaky test_backoff_respected_on_second_run 🔴
- `tests/behavioral/test_outbox_relay.py::TestOutboxRelayBehavioral::test_backoff_respected_on_second_run`
- **Failing on CI, colours ADR-008 gate red on develop**
- Must be fixed or quarantined — **only after timing-only proof that this is pure flake**
- Sequence: H0 → C2 → C1 merge to main

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
