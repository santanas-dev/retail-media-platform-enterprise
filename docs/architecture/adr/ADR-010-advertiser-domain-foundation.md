# ADR-010: Advertiser Domain Foundation

**Status:** Accepted
**Date:** 2026-07-04
**Phase:** 4.0a (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

Phase 3.5 locked in two-layer advertiser isolation: app-layer
`require_scoped_permission("organization.read", "advertiser")` +
PostgreSQL RLS on `advertiser_organizations` and
`advertiser_user_memberships`.  Advertiser users see only their own
organization — proven by behavioral tests.

What remains undefined: the internal advertiser domain model beyond
the bare `advertiser_organizations` table.  The architecture review
(`rmp_enterprise_architecture_review.md`) lists `advertiser, brand,
contract, order, contacts` as a domain.  TZ v2.5 §16.1 mentions
«advertiser cabinet» with campaigns, placements, reporting.  But no
ADR defines the advertiser entity graph, status lifecycle, contact/PII
rules, or the relationship between advertisers and future campaigns.

This ADR locks the advertiser domain foundation before Phase 4.0b
implementation begins.

## Decision

### 1. `advertiser_organizations` is the tenant root

`advertiser_organizations` is the authoritative tenant boundary for
advertiser users.  Every advertiser-scoped entity (brands, contracts,
campaigns, placements, media, reports) is ultimately owned by one
`advertiser_organization`.

An advertiser user authenticated with `auth_provider=local_advertiser`
sees data through the lens of their `advertiser_user_memberships`:
scope is resolved from memberships → `SET LOCAL` RLS variables →
PostgreSQL filters rows.

**Invariant:** no advertiser user can see another organization's data
at any layer (app, DB, or API).

### 2. Entity Graph

```
advertiser_organizations (tenant root)
├── advertiser_brands           ← 1:N, owned brands/product lines
├── advertiser_contracts        ← 1:N, legal/financial agreements
├── advertiser_contacts         ← 1:N embedded OR separate table (see §3)
├── campaigns                   ← future, 1:N
│   └── placements              ← future
└── advertiser_user_memberships ← N:M link to users
```

**`advertiser_brands`** — brands or product lines owned by the
advertiser.  One organization can have multiple brands (e.g. a
holding company with sub-brands).  Campaigns are optionally scoped to
a brand.

```sql
advertiser_brands
┌──────────────────────────┐
│ id (UUID)                │
│ advertiser_organization_id FK → advertiser_organizations.id
│ code (unique per org)    │  -- e.g. "BRAND-COLA", unique within org
│ name                     │  -- display name
│ description (optional)   │
│ status                   │  -- draft/active/suspended/archived
│ created_at               │
│ updated_at               │
└──────────────────────────┘
UNIQUE (advertiser_organization_id, code)
```

**`advertiser_contracts`** — legal/financial agreements between the
platform operator and the advertiser.  Includes budget, validity period,
and terms reference.  Campaigns are scoped to a contract (budget
enforcement point).

```sql
advertiser_contracts
┌──────────────────────────┐
│ id (UUID)                │
│ advertiser_organization_id FK → advertiser_organizations.id
│ code (unique per org)    │
│ name                     │
│ contract_number (opt)    │  -- external legal reference
│ budget_limit_amount      │  -- numeric, nullable (uncapped)
│ budget_limit_currency    │  -- default platform currency
│ valid_from               │
│ valid_until (nullable)   │  -- null = indefinite
│ status                   │  -- draft/active/suspended/expired/archived
│ terms_url (optional)     │  -- link to signed document
│ created_at               │
│ updated_at               │
└──────────────────────────┘
UNIQUE (advertiser_organization_id, code)
```

### 3. Contact Information — embedded vs. separate table

**Decision: separate `advertiser_contacts` table (1:N from organization).**

Rationale:
- Multiple contact roles per organization (primary, billing, technical,
  emergency).
- Contact history/audit requires tracking who was contact when.
- Avoids embedding PII in the organization row, which makes projection
  and GDPR/deletion harder.

```sql
advertiser_contacts
┌──────────────────────────┐
│ id (UUID)                │
│ advertiser_organization_id FK → advertiser_organizations.id
│ contact_type             │  -- primary/billing/technical/emergency
│ full_name                │
│ email                    │  -- not unique globally, scoped per org
│ phone (nullable)         │
│ is_primary (bool)        │  -- only one primary per org+type
│ status                   │  -- active/inactive
│ created_at               │
│ updated_at               │
└──────────────────────────┘
```

**PII rules:**
- `email` and `phone` are visible only to internal staff with
  `advertisers.read` permission.  Advertiser users see only their
  own contacts (RLS-filtered).
- Contact fields are NEVER included in audit event details.
- Contact deletion is a soft-delete (`status=inactive`).
- GDPR export/deletion: contacts are exported as part of the
  advertiser organization's data; deletion removes email/phone,
  retains anonymized record for audit integrity.

### 4. Status Lifecycle

All advertiser domain entities use the same status model:

```
draft → active → suspended → archived
  ↑        ↑                    │
  └────────┴────────────────────┘
       reactivate/unsuspend
```

| Status | Meaning | Allowed actions |
|--------|---------|----------------|
| `draft` | Created but not yet operational | Edit all fields, delete allowed |
| `active` | Operational, can have campaigns | Restricted edits (code locked, name/contacts editable) |
| `suspended` | Temporarily disabled (payment, violation) | No new campaigns. Existing campaigns paused. Read-only. |
| `archived` | Permanently decommissioned | Read-only. No reactivation without admin override. |

**Transition rules:**
- `draft → active`: requires at least one contact + one active contract
- `active → suspended`: admin action, audit-logged with reason
- `suspended → active`: admin action, audit-logged
- `active → archived`: only if zero active campaigns/contracts OR
  admin force-archive with audit log
- `archived → active`: requires security_admin permission, audit-logged

### 5. Relationship to Campaigns (Future)

When campaigns are implemented (Phase 4.1+):

- `campaigns.advertiser_organization_id` → FK to `advertiser_organizations`
- `campaigns.brand_id` → nullable FK to `advertiser_brands` (optional brand scope)
- `campaigns.contract_id` → FK to `advertiser_contracts` (budget tracking)

This means:
- Every campaign belongs to exactly one advertiser organization.
- Campaign can optionally be scoped to a specific brand.
- Campaign budget is tracked against a contract.
- Advertiser-scoped users see only their organization's campaigns
  (RLS via `advertiser_organization_id`).

### 6. RBAC / RLS

All advertiser endpoints follow the pattern proven in Phase 3.5c:

```python
@router.get("/advertisers/organizations")
async def list_orgs(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    ...
```

**Permissions:**

| Permission | Scope |
|-----------|-------|
| `advertisers.read` | Global: see all orgs. Advertiser scope: own org only. |
| `advertisers.manage` | Create/update orgs, brands, contracts. Internal only. |
| `advertisers.contacts.read` | See contact details (PII-gated). |
| `advertisers.contacts.manage` | Create/update contacts. |

**RLS policy:** every advertiser-scoped table (`advertiser_brands`,
`advertiser_contracts`, `advertiser_contacts`) gets
`FORCE ROW LEVEL SECURITY` + `CREATE POLICY … FOR SELECT` using the
same fail-closed `current_setting('app.rmp_scope_advertiser_ids', true)`
pattern from ADR-009.

**Negative behavioral test requirement:** every new endpoint MUST have
a behavioral test proving:
1. No token → 401
2. Wrong scope → 403
3. Advertiser user sees only own data
4. Admin sees all data

No endpoint is accepted without these four behavioral proofs.

### 7. Audit Requirements

The following events must be recorded in `audit_events_operational`
(Phase 4.0c or later, schema-only for now):

| Action | Target | Trigger |
|--------|--------|---------|
| `advertiser.org.created` | organization | New org created |
| `advertiser.org.updated` | organization | Name, status change |
| `advertiser.org.status_changed` | organization | Status transition with old→new |
| `advertiser.brand.created` | brand | New brand |
| `advertiser.contract.created` | contract | New contract |
| `advertiser.contact.created` | contact | New contact |
| `advertiser.contact.updated` | contact | Contact detail change |
| `advertiser.membership.added` | membership | User linked to org |
| `advertiser.membership.removed` | membership | User unlinked |

**Anti-patterns:** no raw PII in `details_json`.  Audit records
reference entity IDs, not email/phone values.

### 8. Deletion Policy

**No hard delete for advertiser organizations that have:**

- Active or past campaigns (even archived)
- Active or past contracts
- Associated users with login history

**Hard delete allowed only for:**
- `draft` status organizations with zero campaigns and zero contracts
- Individual contacts (soft-delete via `status=inactive`)
- Brands with zero campaigns (soft-delete via `status=archived`)

**Cascade rule:** archiving an organization cascades to all its
brands and contracts (status → `archived`).  Does NOT cascade to
campaigns — campaigns must be individually archived first.

### 9. Phase 4.0b Implementation Target

Phase 4.0b is the **minimal read-only advertiser domain**:

| Deliverable | Scope |
|------------|-------|
| Migration | `005_advertiser_domain.py`: `advertiser_brands`, `advertiser_contracts`, `advertiser_contacts` tables + RLS policies |
| Models | SQLAlchemy ORM models in `models.py` |
| Seed | Test advertiser + 2 brands + 1 contract + 2 contacts |
| Endpoints | `GET /api/v1/advertisers/organizations`, `GET /api/v1/advertisers/organizations/{id}`, `GET /api/v1/advertisers/brands`, `GET /api/v1/advertisers/contracts` |
| Auth | `require_scoped_permission("advertisers.read", "advertiser")` + `set_rls_context` on all endpoints |
| Behavioral tests | 4 proofs per endpoint (no-token, wrong-scope, scoped, admin) |
| Mutations | **Deferred** — no POST/PATCH/DELETE yet |

**Explicitly excluded from 4.0b:**
- Campaigns, placements, media, orders
- Advertiser cabinet frontend (`advertiser-web`)
- Mutation endpoints (POST, PATCH, DELETE)
- Advertiser registration/invitation flow
- Budget enforcement logic
- Contact email/phone verification

## Consequences

- **Positive:** Advertiser domain model is defined before implementation —
  brands, contracts, contacts have clear schemas, statuses, and PII rules.
  RLS enforcement extends naturally from the Phase 3.5c pilot.
  Campaign-to-contract relationship is decided now (budget tracking anchor)
  rather than retrofitted later.

- **Negative:** Three new tables increase migration surface.  Contact PII
  rules add complexity (projection, GDPR, audit exclusion).  Status
  lifecycle validation needs to be implemented before mutation endpoints.

- **Risk:** `advertiser_contacts` as a separate table means JOINs on
  every organization detail view.  Mitigation: contacts are loaded
  separately (not joined into org list) — trade one N+1 for clean
  separation.

## References

- ADR-006 §3 — Advertiser identity model (`local_advertiser`)
- ADR-009 §2 — Two-layer defense (app + RLS)
- ADR-009 §8 — Advertiser scope is orthogonal to hierarchy
- Phase 3.5c commit `c9b2a60` — `require_scoped_permission` + behavioral proof
- `rmp_enterprise_architecture_review.md` — «Advertisers: advertiser, brand, contract, order, contacts»
- `packages/domain/models.py` — `AdvertiserOrganization`, `AdvertiserUserMembership`
