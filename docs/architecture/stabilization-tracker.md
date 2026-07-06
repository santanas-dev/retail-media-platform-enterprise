# Stabilization Tracker — Retail Media Platform Enterprise

**Last updated:** 2026-07-06
**Current phase:** 4.2c (Manifest Generator Worker Skeleton — closed)

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
| S-006d | Device gateway manifest endpoint | P2 | ✅ done | — | `apps/device-gateway/main.py`: `GET /api/v1/device/manifest/latest` with device JWT auth, device status check. `get_latest_manifest_for_device` in repository. 9 unit + 6 behavioral tests. Commit: TBD. | Phase 4.2e: runtime simulator behavioral tests |
| S-007 | PoP / reporting | P3 | open | — | ADR-015; `proof_event_v1.schema.json` defined | Implement PoP ingestion + campaign analytics |
| S-008 | DB write RLS `WITH CHECK` | P2 | deferred | — | ADR-009 two-layer defense; SELECT RLS enforced on 7 campaign tables | Add INSERT/UPDATE/DELETE RLS policies when write paths stabilize |
| S-009 | Frontend campaign management UI | P3 | open | — | React 19 + Vite scaffolded; admin-web + advertiser-web exist | Wire campaign CRUD to advertiser-web |

## Status Legend

- **done** — implemented, tested, committed, pushed
- **locked** — architecture locked (ADR accepted), implementation deferred
- **open** — not started, ready for implementation
- **deferred** — intentionally postponed (documented reason)
