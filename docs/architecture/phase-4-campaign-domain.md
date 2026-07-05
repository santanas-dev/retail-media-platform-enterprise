# Phase 4 — Campaign Domain

**Date:** 2026-07-05
**Phase:** 4.1d (Campaign Approval Workflow)
**Commits:** `aab040e` (read-only), `8280d54` (hardening), `1c5e013` (alignment), `4b19637` (mutations), `7dd05a3` (tenant isolation), `861d082` (existence oracle), `...` (approval workflow)
**Previous:** Phase 4.0b (Advertiser Read-Only Foundation)

## Purpose

Phase 4.1 delivers the campaign domain — the core revenue-generating entity graph:
campaigns, flights, creatives, placements, approvals, and status history.  All
endpoints are protected by JWT + scoped permission + PostgreSQL RLS (two-layer
defense per ADR-009).

## Sub-phases

### Phase 4.1a — Architecture Lock ✅

| Deliverable | Status |
|-------------|--------|
| ADR-015 — campaign domain foundation | ✅ complete |
| ERD v2.5 — campaign tables added | ✅ complete |
| API groups v1 §7 — endpoints planned | ✅ complete |

**Decisions locked:**
- `advertiser_organizations` is the tenant root for all campaigns
- `advertiser_contract_id` NOT NULL — every campaign has budget accountability
- `advertiser_brand_id` nullable — campaigns may target org directly
- 9 campaign statuses with 20+ transitions (draft → … → archived)
- Placements target surfaces or above (store/cluster/branch) — never `physical_device_id`
- `display_surface_id` nullable with CHECK at-least-one-target
- Approval mandatory before `scheduled`/`active`
- Flight windows must fit within contract validity
- All mutations produce outbox events (ADR-011) — no direct NATS publish
- Fail-closed RLS on all 7 tables (ADR-009 pattern)

### Phase 4.1b — Read-Only DB/API Foundation ✅

| Deliverable | Status |
|-------------|--------|
| Migration `006_campaign_domain.py` | ✅ 7 tables + RLS + CHECK constraints |
| ORM models (7) | ✅ `Campaign`, `CampaignFlight`, `CampaignPlacement`, `CreativeAsset`, `CampaignCreative`, `CampaignApproval`, `CampaignStatusHistory` |
| Seed data | ✅ 4 permissions (`campaigns.read/manage/approve` + `creatives.read`), role assignments, 1 dev campaign with flight/creative/placement/history |
| Repository methods (7) | ✅ `list_campaigns/flights/creatives/assets/placements/approvals/history()` |
| API endpoints (7) | ✅ all live at `/api/v1/identity/` (provisional flat list-all paths) |
| Unit tests (41) | ✅ models, migration RLS, seed, schemas (no storage secrets), router compliance (no `db.execute`), BigInteger types, CHECK constraints |
| Behavioral tests (30) | ✅ auth (401), scoped access (own campaigns only), no-permission (403), admin sees all, PII not leaked, storage secrets hidden, approvals permission behavior |
| CI checks (44/44) | ✅ import boundaries + all gates |

#### Database Tables

| Table | FK to | RLS | Notes |
|-------|-------|-----|-------|
| `campaigns` | `advertiser_organizations` (NOT NULL), `advertiser_brands` (nullable), `advertiser_contracts` (NOT NULL) | ✅ direct | Tenant root via org, budget via contract |
| `campaign_flights` | `campaigns` | ✅ via campaign | Time periods with `start_at < end_at` CHECK |
| `campaign_placements` | `campaigns` (NOT NULL), `display_surfaces` (nullable), `stores` (nullable), `clusters` (nullable), `branches` (nullable) | ✅ via campaign | At-least-one-target CHECK, BIGINT counters |
| `creative_assets` | `advertiser_organizations` (NOT NULL) | ✅ direct | Metadata only — no binary, no presigned URLs |
| `campaign_creatives` | `campaigns`, `creative_assets` | ✅ via campaign | UNIQUE (campaign_id, creative_asset_id) |
| `campaign_approvals` | `campaigns`, `users` (requested_by, reviewed_by) | ✅ via campaign | Approval audit trail |
| `campaign_status_history` | `campaigns`, `users` (changed_by) | ✅ via campaign | Every transition writes a row |

#### API Endpoints

| Method | Endpoint | Permission | Notes |
|--------|----------|------------|-------|
| GET | `/api/v1/identity/campaigns` | `campaigns.read` | Scoped + RLS |
| GET | `/api/v1/identity/campaign-flights` | `campaigns.read` | Via-campaign RLS |
| GET | `/api/v1/identity/campaign-creatives` | `campaigns.read` | Via-campaign RLS |
| GET | `/api/v1/identity/creative-assets` | `creatives.read` | No storage_bucket/key exposed |
| GET | `/api/v1/identity/campaign-placements` | `campaigns.read` | Via-campaign RLS |
| GET | `/api/v1/identity/campaign-approvals` | `campaigns.read` | Via-campaign RLS |
| GET | `/api/v1/identity/campaign-status-history` | `campaigns.read` | Via-campaign RLS |

All endpoints are provisional flat list-all paths under `/api/v1/identity/`.
Nested REST paths (`/api/v1/campaigns/{code}/flights`, etc.) are planned for
Phase 4.1c+ (mutations/detail).

#### Permissions

| Permission | Scope | Grant |
|------------|-------|-------|
| `campaigns.read` | Global or advertiser | List/view campaigns and sub-entities |
| `campaigns.manage` | Internal | Edit campaigns, force status changes |
| `campaigns.approve` | Internal | Approve/reject (system_admin, security_admin) |
| `creatives.read` | Global or advertiser | View creative asset metadata |

**Role assignments (seed):**
- `system_admin` / `security_admin`: read + manage + approve + creatives.read
- `operator`: campaigns.read only
- `analyst`: campaigns.read + creatives.read
- `advertiser`: scoped campaigns.read + creatives.read (behavioral conftest)

#### Behavioral Proof

| Test | Proves |
|------|--------|
| No token → 401 | 7/7 endpoint groups |
| Admin sees all | campaigns, flights, creatives, placements, approvals, history |
| Advertiser sees only own org | campaigns, flights, creatives, placements, history |
| No campaigns.read → 403 | disabled user (no roles) on all 7 endpoints |
| PII not leaked | `email`/`phone`/`contact_name` absent from campaign responses |
| Storage secrets hidden | `storage_bucket`/`storage_key`/`presigned_url` absent from creative asset responses |
| Global read sees all | operator (global campaigns.read) sees all campaigns |

### Phase 4.1c — Mutation Foundation (Phase 4.2) ✅

| Deliverable | Status |
|-------------|--------|
| Repository methods (3) | ✅ `create_campaign`, `update_campaign`, `archive_campaign` |
| API endpoints (3) | ✅ POST `/campaigns`, PATCH `/campaigns/{id}`, POST `/campaigns/{id}/archive` |
| Domain exceptions | ✅ `ScopeError`, `CrossOrgReferenceError`, `EntityNotFoundError` |
| Outbox integration | ✅ `campaign.created/updated/archived` in same DB transaction |
| Tenant isolation | ✅ scoped advertiser → 403 on cross-org create/update/archive |
| Brand/contract org validation | ✅ cross-org → 422, no existence oracle |
| Unit tests | ✅ 12 (schemas, permissions, draft-only, no `db.execute`, exceptions, scope helpers) |
| Behavioral tests | ✅ 10 (401, 403, create/update/archive, outbox, status history, cross-org isolation, no-outbox-on-rejection) |
| CI checks | ✅ 44/44 (import boundaries + all gates) |

#### Implemented Mutations

| Method | Endpoint | Permission | Scope check | Status |
|--------|----------|------------|-------------|--------|
| POST | `/api/v1/identity/campaigns` | `campaigns.manage` | Org must be in advertiser scope | ✅ |
| PATCH | `/api/v1/identity/campaigns/{campaign_id}` | `campaigns.manage` | Campaign org must be in scope | ✅ |
| POST | `/api/v1/identity/campaigns/{campaign_id}/archive` | `campaigns.manage` | Campaign org must be in scope | ✅ |

All endpoints are provisional identity-prefixed flat paths.  Admin bypass
preserved (`scope_advertiser_ids=None` → no restriction).

#### Behavioral Proof

| Test | Proves |
|------|--------|
| Scoped advertiser cannot create for other org | 403 (scope) |
| Scoped advertiser cannot use cross-org brand | 422 (generic) |
| Scoped advertiser cannot use cross-org contract | 422 (generic) |
| Scoped advertiser CAN create for own org | 201 + draft |
| Admin can create for any org | 201 (scope bypass) |
| Admin cannot use cross-org contract | 422 (brand/contract checks universal) |
| Scoped advertiser cannot update/archive other org campaign | 403 (scope) |
| Admin can update any org campaign | 200 |
| Nonexistent brand/contract same as cross-org | both 422 "Invalid advertiser … reference" |
| Rejection writes no campaign + no outbox | `SELECT` proves empty |
| Successful create writes outbox `campaign.created` | `outbox_events` row exists |
| Successful update writes outbox `campaign.updated` | `outbox_events` row exists |
| Successful archive writes outbox `campaign.archived` | `outbox_events` row exists |
| Non-draft update → 409 | seed campaign set to 'active', PATCH rejected |
| Status history written on create + archive | `campaign_status_history` rows verified |

### Phase 4.1d — Approval Workflow ✅

| Deliverable | Status |
|-------------|--------|
| Repository methods (3) | ✅ `request_campaign_approval`, `approve_campaign`, `reject_campaign` |
| API endpoints (3) | ✅ POST `request-approval`, POST `approve`, POST `reject` |
| Status transitions | ✅ draft→pending_approval, pending_approval→approved, pending_approval→rejected |
| Validation | ✅ ≥1 flight + placement + creative before request |
| Approval records | ✅ `campaign_approvals` row on approve/reject with decision + reviewer |
| Status history | ✅ row on every transition |
| Outbox | ✅ `campaign.approval_requested/approved/rejected` in same transaction |
| Permission separation | ✅ `campaigns.manage` for request, `campaigns.approve` for approve/reject |
| Advertiser cannot self-approve | ✅ scoped advertiser gets 403 on approve/reject |
| Unit tests | ✅ 15 (schemas, permissions, transitions, compliance) |
| Behavioral tests | ✅ 16 (401, 403, request/approve/reject, non-draft, validation, no-outbox, self-approve) |

### Deferred (Phase 4.2–4.4)

- **Mutations:** create/update/submit/status-change for campaigns, placements, creatives, flights
- **Approval workflow:** approve/reject actions, approval history by campaign
- **Outbox producers:** `campaign.*` events via transactional outbox (ADR-011)
- **Manifest generation:** resolve hierarchy → surfaces → devices
- **PoP/reporting:** campaign performance dashboards, advertiser reporting
- **Frontend:** advertiser-web campaign management UI
- **Scheduling validation:** contract window enforcement, flight overlap checks, past-date rejection

## References

- ADR-015 — Campaign domain foundation
- ADR-009 — Fail-closed scopes and PostgreSQL RLS
- ADR-010 — Advertiser domain foundation
- ADR-011 — Transactional outbox
- ADR-014 — Layering and import boundaries
- `docs/architecture/erd/erd-v2-5.md` — Campaign section
- `docs/architecture/api/api-groups-v1.md` — §7 Campaigns & Placements
