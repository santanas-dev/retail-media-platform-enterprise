# Stabilization Tracker — Retail Media Platform Enterprise

**Last updated:** 2026-07-06
**Current phase:** 4.3a (PoP and Reporting Architecture Lock — locked)

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
| S-007 | PoP / reporting | P3 | 🔒 locked (4.3a) / ✅ 4.3b+4.3c done | — | ADR-017 accepted. **4.3b:** Migration 009, models, 6 repo helpers, 23u+10b tests. **4.3c:** `POST /api/v1/pop/batch` on control-api, device JWT auth, schema_version/device/dedup/duration/playback/cross-entity validation, manifest resolution → quarantine (72h, campaign_verified=false) or acceptance, outbox (pop.event.accepted / quarantined / pop.batch.ingested), PopEventIn/PopBatchResponse Pydantic schemas. 28 unit + 10 behavioral tests. Phase split: 4.3b (schema) → 4.3c (ingestion) → 4.3d (reporting) → 4.3e (views) | Implement 4.3d reporting endpoints |
| S-008 | DB write RLS `WITH CHECK` | P2 | deferred | — | ADR-009 two-layer defense; SELECT RLS enforced on 7 campaign tables | Add INSERT/UPDATE/DELETE RLS policies when write paths stabilize |
| S-009 | Frontend campaign management UI | P3 | open | — | React 19 + Vite scaffolded; admin-web + advertiser-web exist | Wire campaign CRUD to advertiser-web |

## Status Legend

- **done** — implemented, tested, committed, pushed
- **locked** — architecture locked (ADR accepted), implementation deferred
- **open** — not started, ready for implementation
- **deferred** — intentionally postponed (documented reason)
