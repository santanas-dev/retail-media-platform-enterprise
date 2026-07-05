# Phase 4 — Advertiser Domain

**Date:** 2026-07-05
**Phase:** 4 (Advertiser Domain)
**Commit:** `37fc549` (implementation), `133812e` (behavioral fixes), `e21ecb4` (test tightening)
**Previous:** Phase 3.5c (Scoped Permission Guard)

## Purpose

Phase 4 delivers the advertiser domain — the foundational multi-tenant data model
for brands, contracts, and contacts owned by advertiser organizations.  Every
endpoint is protected by JWT + scoped permission + PostgreSQL RLS (two-layer
defense per ADR-009).

## Sub-phases

### Phase 4.0a — Architecture Lock ✅

| Deliverable | Status |
|-------------|--------|
| ADR-010 — advertiser domain foundation | ✅ complete |
| ERD v2.5 — advertiser tables added | ✅ complete |
| API groups v1 §4 — planned endpoints | ✅ complete |

**Decisions locked:**
- `advertiser_organizations` is the tenant root
- Brands and contracts FK to organization
- Contacts FK to organization, partial unique index for primary contact (active only)
- All tables have RLS from creation (`ENABLE ROW LEVEL SECURITY + FORCE ROW LEVEL SECURITY`)
- Fail-closed SELECT policies (pattern from ADR-009 / migration 004)
- No hard deletes for orgs with campaigns/contracts

### Phase 4.0b — Read-Only Foundation ✅

| Deliverable | Status |
|-------------|--------|
| Migration `005_advertiser_domain.py` | ✅ 3 tables + RLS |
| ORM models | ✅ `AdvertiserBrand`, `AdvertiserContract`, `AdvertiserContact` |
| Seed data | ✅ 4 permissions, role assignments, dev orgs/brands/contracts/contacts |
| Repository methods | ✅ `list_advertiser_brands/contracts/contacts()` |
| API endpoints (4) | ✅ all live at `/api/v1/identity/` |
| Unit tests (33) | ✅ models, RLS, seed, repository, router compliance |
| Behavioral tests (31) | ✅ 401/403/200 scoped/200 global, PII gate |
| CI checks (43/43) | ✅ |

#### Database Tables

| Table | FK to | RLS | Notes |
|-------|-------|-----|-------|
| `advertiser_brands` | `advertiser_organizations.id` | ✅ | Brand under one organization |
| `advertiser_contracts` | `advertiser_organizations.id` | ✅ | Contract under one organization |
| `advertiser_contacts` | `advertiser_organizations.id` | ✅ | Partial unique index: `(organization_id, is_primary) WHERE status = 'active'` |

#### API Endpoints

All under `/api/v1/identity/` (control-api router):

| Endpoint | Permission | Scope | PII |
|----------|------------|-------|-----|
| `GET /advertiser-organizations` | `organization.read` | Advertiser-scoped: own org via RLS | — |
| `GET /advertiser-brands` | `advertisers.read` | Advertiser-scoped via RLS | — |
| `GET /advertiser-contracts` | `advertisers.read` | Advertiser-scoped via RLS | — |
| `GET /advertiser-contacts` | `advertisers.contacts.read` | Advertiser-scoped via RLS | ✅ email/phone |

#### Permissions

| Code | Grant | Purpose |
|------|-------|---------|
| `advertisers.read` | system_admin, security_admin, **operator** (read-only) | Read brands, contracts |
| `advertisers.manage` | system_admin, security_admin | Create/modify advertiser data |
| `advertisers.contacts.read` | system_admin, security_admin | Read contact PII (email, phone) |
| `advertisers.contacts.manage` | system_admin, security_admin | Create/modify contacts |

> **operator** role has `advertisers.read` but NOT `advertisers.contacts.read` —
> can list brands and contracts, cannot see contact details (verified by
> behavioral test `test_advertisers_read_alone_is_not_enough_for_contacts`).

#### Behavioral Coverage (31 tests)

| Category | Count | Tests |
|----------|-------|-------|
| 401 — no token | 4 | brands, contracts, contacts, organizations |
| 403 — missing permission | 2 | `advertisers.read` for brands + contracts (analyst user) |
| 403 — missing `contacts.read` | 1 | operator has `advertisers.read` but not `contacts.read` |
| 403 — wrong scope | 1 | advertiser scoped to org-A, requests without advertiser scope |
| 200 — global (admin) | 3 | system_admin sees all brands/contracts/contacts |
| 200 — scoped (advertiser) | 4 | advertiser sees only own brands/contracts/contacts + orgs |
| RLS — skipped (no `SET LOCAL`) | 1 | `test_rls_requires_set_local_for_advertiser_tables` |

#### Key Files

| File | Purpose |
|------|---------|
| `packages/domain/models.py` | ORM models `AdvertiserBrand`, `AdvertiserContract`, `AdvertiserContact` |
| `apps/control-api/alembic/versions/005_advertiser_domain.py` | Migration with ENABLE+FORCE RLS |
| `apps/control-api/seed.py` | Dev seed data (orgs, brands, contracts, contacts) |
| `packages/domain/repository.py` | `list_advertiser_brands/contracts/contacts()` |
| `packages/api/identity.py` | 4 GET endpoints + `require_scoped_permission` |
| `packages/domain/schemas.py` | `AdvertiserBrandOut`, `AdvertiserContractOut`, `AdvertiserContactOut` |
| `packages/api/dependencies.py` | `require_scoped_permission`, `ScopeContext`, `set_rls_context` |
| `tests/test_phase4_advertiser_domain.py` | Unit tests (33) |
| `tests/behavioral/test_advertiser_domain.py` | Behavioral tests (31) |
| `tests/behavioral/conftest.py` | Test users: admin, advertiser, operator, analyst |

## Deferred (beyond Phase 4.0b)

| Area | Phase |
|------|-------|
| `POST/PATCH/DELETE` advertiser mutations | 4.0c+ |
| Campaigns and placements domain | 4.1+ |
| Transactional outbox producers (ADR-011) | 4.1+ |
| Outbox relay worker (NATS publishing) | 4.1+ |
| Frontend — advertiser-web (React) | 4.2+ |
| Advanced PII workflows / GDPR export | 4.3+ |
| Edge runtime — device gateway (ADR-013) | 5+ |
| Async I/O integrations (LDAPS, S3/MinIO) (ADR-012) | 5+ |

## References

- [ADR-010 — Advertiser Domain Foundation](adr/ADR-010-advertiser-domain-foundation.md)
- [ADR-009 — Fail-Closed Scopes and PostgreSQL RLS](adr/ADR-009-fail-closed-scopes-and-postgresql-rls.md)
- [ADR-011 — Transactional Outbox](adr/ADR-011-transactional-outbox-and-event-delivery.md)
- [ADR-012 — Async I/O Boundary](adr/ADR-012-async-io-and-blocking-work.md)
- [ADR-013 — Edge Runtime Safety](adr/ADR-013-edge-runtime-safety.md)
- [ADR-014 — Layering and Import Boundaries](adr/ADR-014-layering-and-import-boundaries.md)
- [API Groups v1 §4](api/api-groups-v1.md)
