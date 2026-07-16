# Retail Media Platform — Project State

**Last updated:** 2026-07-16
**Repository:** `/home/cobalt/retail-media-platform-enterprise`
**Remote:** `github.com:santanas-dev/retail-media-platform-enterprise`

## Current Branch & HEAD

```
develop @ 4adde45
```

## Published Tags

- `v0.7` — published on `main @ 4db6dc0`

## Active Workstreams

### C1 — Creative Moderation + Campaign Approval RLS ✅
- 4 endpoints connected to RLS context under NOBYPASSRLS
- 8 behavioural tests — all pass
- Bug fixed: `AdvertiserOrganization.name` → `legal_name` (4 places in repository)
- Seed gap closed: `creatives.moderate` added to `system_admin`/`security_admin` role_permissions

### A3 / S-088 — Inventory Rules Management UI ✅
- Backend: 5 endpoints (CRUD + activate/deactivate), 13 tests
- Frontend: RulesTab in InventoryPage, 124/124 vitest

## Blockers Before Player (A4–A6)

| ID | Task | Status |
|----|------|--------|
| A1 S-086 | Inventory availability forecast | ✅ |
| A2 S-087 | Sold-out alternatives | ✅ |
| A3 S-088 | Rules management UI | ✅ |
| A4 S-089 | Inventory simulation | ⏳ |
| A5 S-090 | Campaign dashboard | ⏳ |
| A6 S-091 | Emergency controls | ⏳ |

## Environment

- **PostgreSQL:** Docker `rmp-phase1-postgres-1` (port 5432)
- **App user:** `retail_media_app` (NOBYPASSRLS)
- **Owner user:** `retail_media_owner` (fixture setup)
- **Behavioural tests:** `RUN_BEHAVIORAL_TESTS=1` + env vars for DB URLs

## Key Constraints

- `main` = stable releases; `develop` = active integration
- Feature branches: `feature/S-XXX-desc` from develop → PR → merge
- No direct commits to main
- Protected boundaries: `.env`, Docker/deploy scripts, destructive migrations
- RLS on all tenant-scoped tables; NOBYPASSRLS enforced on app role
