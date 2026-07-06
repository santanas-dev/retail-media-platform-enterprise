# Stabilization Tracker — Retail Media Platform Enterprise

| **Last updated:** 2026-07-06
| **Current phase:** 4.3d (PoP reporting — closed, next: 4.3e materialized views)

| ID | Phase | Priority | Status | Owner | Evidence | Next Action |
|----|-------|----------|--------|-------|----------|-------------|
| S-001 | Import boundaries (ADR-014) | P1 | ✅ done | — | `check-import-boundaries.py` passes 44/44 | — |
| S-002 | Outbox foundation (ADR-011) | P1 | ✅ done | — | Migration 007, `OutboxEvent` model, `enqueue_outbox_event`, 10 unit + 9 behavioral tests | — |
| S-003 | Campaign read-only (Phase 4.1b) | P1 | ✅ done | — | 7 endpoints, 7 ORM models, migration 006, 41 unit + 30 behavioral tests | — |
| S-004 | Campaign mutations (Phase 4.1c) | P1 | ✅ done | — | 3 endpoints (create/update/archive), tenant isolation, cross-org validation, outbox integration, 12 unit + 10 behavioral tests | — |
| S-005 | Campaign approval workflow | P2 | ✅ done | — | 3 endpoints (request-approval/approve/reject), status transitions, approval records, outbox, requested_at semantics, contract validation, idempotency. Commits: `fc09f4b` + `c405bdc` + `0fea6ac`. 18 unit + 24 behavioral tests | — |
| S-006a | Delivery architecture lock | P2 | 🔒 locked | — | ADR-016 accepted: delivery trigger, eligibility, target resolution, manifest schema, versioning, outbox events, observability, security, phase split (4.2b→4.2e), behavioral proof requirements | — |
| S-006b | Delivery DB/model foundation | P2 | ✅ done | — | Migration 008, 5 ORM models (DeliveryPlan/Manifest/Surface/Asset/Attempt), 7 repository helpers, 16 unit + 10 behavioral tests. Commits: `46cfe71` + `137ae0b` | — |
| S-006c | Manifest generator worker skeleton | P2 | ✅ done | — | `packages/domain/delivery.py` (776 lines): eligibility, target resolution, `compute_manifest_id` + `compute_campaign_version_hash`, manifest JSON gen, delivery_plan/manifest persistence, `delivery.manifest.generated`/`failed` outbox, plan idempotency. 25 unit + 12 behavioral tests. Commits: `e467543` + `e05b960` + `0154681`. | — |
| S-006d | Device gateway manifest endpoint | P2 | ✅ done | — | `apps/device-gateway/main.py`: `GET /api/v1/device/manifest/latest` with device JWT auth, device status check, ETag/If-None-Match, response shape alignment with `generate_manifest_json()`/`manifest_v1.schema.json`, no direct SQL in router, store-orphan detection. 10 unit + 7 behavioral tests. Commits: `c34d5fa` + `c8a369e` + `08b099e`. | — |
| S-006e | Runtime simulator safety proofs | P2 | ✅ done | — | `packages/runtime/simulator.py` (505 lines): ADR-013 safety simulator — manifest apply (validate/secrets/device_id/version/signature → atomic swap + lkg), kill-switch (4 levels, fail-closed), render slot (6 safety gates), PoP integrity (only after render, dedup, required fields), offline TTL (monotonic, fallback after expiry). 41 unit tests. Commits: `52a50fc` + fix. | Phase 4.3+: PoP ingestion / event delivery |
| S-007c | PoP ingestion endpoint | P3 | ✅ done | — | `POST /api/v1/pop/batch` on control-api, device JWT, 11-step validation (schema/device/dedup/duration/playback/stale/clock_drift/manifest/cross-entity), quarantine 72h, accepted = billing-grade, outbox (pop.event.accepted/quarantined + pop.batch.ingested), dedup flush fix (59060ad), fixture hardening (d1d7bb5), cleanup time fence (d97be76). 29 unit + 27 behavioral tests. Commits: `d1c6e8c` + `d1d7bb5` + `59060ad` + `d97be76`. | Implement 4.3d reporting endpoints |
| S-007d | PoP reporting / read models | P3 | ✅ done | — | `GET /api/v1/identity/campaigns/{id}/pop/{summary,by-day,by-surface}` with JWT + `require_scoped_permission("campaigns.read","advertiser")` + `set_rls_context`. 3 repository helpers filtering `status='accepted' AND campaign_verified=true AND playback_result='success'`. Campaign ownership guard (`_require_campaign_visible`) — scoped advertiser foreign campaign → 404, admin bypass. CampaignPopSummaryOut/ByDay/BySurface schemas, no PII/secrets. 13 unit + 23 behavioral (8 reporting + 15 scope). P1 fix: `1f3e98d`. Commits: `518475c` + `1f3e98d`. | Implement 4.3e materialized views |
| S-007e | Behavioral PostgreSQL CI gate | P1 | ✅ done | — | `.github/workflows/phase1-ci.yml` — `behavioral-postgres-tests` job: PostgreSQL 16 service, two-role setup (owner for migrations, `retail_media_app` NOBYPASSRLS for runtime), migrations + seed + explicit `GRANT`, zero-tests-passed guard, blocks merge on failure. Local runner: `scripts/ci/behavioral-postgres-checks.sh` with superuser/BYPASSRLS warning + zero-test guard. RLS-proof runtime role verified in CI. | — |
| S-008 | DB write RLS `WITH CHECK` | P2 | deferred | — | ADR-009 two-layer defense; SELECT RLS enforced on 7 campaign tables | Add INSERT/UPDATE/DELETE RLS policies when write paths stabilize |
| S-009 | Frontend campaign management UI | P3 | open | — | React 19 + Vite scaffolded; admin-web + advertiser-web exist | Wire campaign CRUD to advertiser-web |

## Status Legend

- **done** — implemented, tested, committed, pushed
- **locked** — architecture locked (ADR accepted), implementation deferred
- **open** — not started, ready for implementation
- **deferred** — intentionally postponed (documented reason)
