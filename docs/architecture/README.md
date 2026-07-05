# Architecture Documentation Index

## Source of Truth Order

When decisions conflict, resolve in this order:

1. **`docs/00-source-of-truth/`** — ТЗ v2.5 extraction + rewrite starting decisions
2. **`docs/architecture/adr/ADR-001..ADR-015`** — architecture decision records (current)
3. **`docs/architecture/erd/erd-v2-5.md`** + **`docs/architecture/api/api-groups-v1.md`** — current ERD and API contracts
4. **`docs/architecture/contracts/`** — manifest/proof event schemas
5. **`docs/architecture/*.md` (superseded)** — historical design gates, retained for context only

## Active Documents

| Document | Purpose |
|----------|---------|
| `adr/ADR-001` | Deployment and service boundaries |
| `adr/ADR-002` | Event bus (NATS JetStream) |
| `adr/ADR-003` | Device identity (JWT, certificates) |
| `adr/ADR-004` | Frontend stack (React + TypeScript) |
| `adr/ADR-005` | Monitoring and observability |
| `adr/ADR-006` | User identity and RBAC |
| `adr/ADR-007` | Data and analytics boundary (ClickHouse deferred) |
| `adr/ADR-008` | Testing strategy and phase gates |
| `adr/ADR-009` | Fail-closed scopes and PostgreSQL RLS |
| `adr/ADR-010` | Advertiser domain foundation (Phase 4.0a) |
| `adr/ADR-011` | Transactional outbox and event delivery |
| `adr/ADR-012` | Async I/O and blocking work |
| `adr/ADR-013` | Edge runtime safety |
| `adr/ADR-014` | Layering and import boundaries |
| `adr/ADR-015` | Campaign domain foundation (Phase 4.1a) |
| `erd/erd-v2-5.md` | Current entity-relationship diagram |
| `api/api-groups-v1.md` | Current API endpoint catalog |
| `contracts/` | Manifest v1, proof event v1 schemas |
| `events/` | Event contract definitions |
| `phase-1-skeleton.md` | Phase 1 deliverable summary |
| `phase-2-foundation.md` | Phase 2 deliverable summary |
| `phase-4-advertiser-domain.md` | Phase 4 (advertiser domain) close-out summary |
| `phase-4-campaign-domain.md` | Phase 4 (campaign domain) close-out summary |
| `legacy-reference.md` | Old platform reference pointer |

## Superseded Documents (Historical Only)

These documents predate current ADRs and contain decisions that have been
changed or refined.  They are retained for historical context — do not
implement from them when they conflict with ADRs.

| File | Superseded by | Reason |
|------|---------------|--------|
| `architecture-decisions-v2-5-a2.md` | ADR-007 | ClickHouse mandated "до PoP production" — ADR-007 defers to Phase 4+ |
| `v2-5-architecture-correction-plan-46-1.md` | ADR-009 | "RBAC/RLS сохранить как есть, RLS=rowsecurity=false" — ADR-009 mandates PostgreSQL RLS |
| `device-model-api-b2.md` | ADR-009 | "RLS/scope: 47/47 unchanged" — ADR-009 introduces fail-closed two-layer defense |
| `backend1-debt-closure-design-gate.md` | ADR-009 | Application-level scope checks only, no DB-level RLS — ADR-009 adds RLS |
| `erd-v2-5-a2.md` | `erd/erd-v2-5.md` | Superseded by current ERD with Phase 2–4 updates |
| `domain-boundaries-v2-5-a2.md` | ADR-001, ADR-006, ADR-010 | Superseded by current domain model |
| `api-contracts-v2-5-a2.md` | `api/api-groups-v1.md` | Superseded by current API docs with Phase 3–4 endpoints |
| `event-contracts-v2-5-a2.md` | `events/event-contracts-v1.md` | Superseded by current event contracts |
| `kso-post-migration-safety-gate-a3-2.md` | ADR-009 | Pre-dates RLS architecture; RLS=rowsecurity=false accepted as baseline |
| KSO migration docs (a3*) | ADR-009 | Operational migration docs from old platform; do not reflect current RBAC/RLS |
| `h0-production-readiness-design-gate.md` | ADR-007, ADR-009 | ClickHouse deferred, RLS not yet designed |
| Channel registry docs (b1) | ADR-003, current ERD | Operational cleanup docs from Phase B |
