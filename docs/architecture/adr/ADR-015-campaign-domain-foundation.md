# ADR-015: Campaign Domain Foundation

**Status:** Accepted
**Date:** 2026-07-05
**Phase:** 4.1a (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ADR-010 locked the advertiser domain: `advertiser_organizations` is the
tenant root; brands, contracts, and contacts are defined with status
lifecycles, RLS policies, and PII rules.  Phase 4.0b delivered read-only
endpoints with behavioral proof.

What remains undefined: the campaign domain — the core revenue-generating
entity graph.  Campaigns, creatives, placements, scheduling, approval,
delivery, and proof-of-play form a closed loop that touches every ADR:
outbox (ADR-011), edge safety (ADR-013), layering (ADR-014), analytics
(ADR-007), and device identity (ADR-003).

Without an architecture lock, the implementation risks:
- Campaigns created without advertiser tenant root → broken scoping.
- Dual-write to NATS in mutations → ghost events.
- Placements targeting physical devices (brittle) instead of surfaces
  (stable abstraction).
- Schedule validation in frontend only → backend accepts invalid
  schedules.
- No approval gate → unreviewed campaigns go live.
- PoP attributed to un-rendered content → billing fraud.

This ADR locks every decision before a single campaign table is created.

## Decision

### 1. Campaign Ownership

Every campaign belongs to one `advertiser_organization`.  No campaign
exists without an advertiser tenant root.

```sql
campaigns.advertiser_organization_id → FK → advertiser_organizations.id
campaigns.advertiser_brand_id        → nullable FK → advertiser_brands.id
campaigns.advertiser_contract_id     → FK → advertiser_contracts.id
```

**Invariants:**
- `advertiser_organization_id` is NOT NULL — tenant ownership at all times.
- `advertiser_contract_id` is NOT NULL — every campaign has budget
  accountability.
- `advertiser_brand_id` is optional — campaigns may target the
  organization directly or a specific brand.

**Tenant isolation:** advertiser-scoped users see only campaigns where
`advertiser_organization_id` matches their scope (RLS).

### 2. Core Entity Graph

```
advertiser_organizations (tenant root)
└── campaigns
    ├── campaign_flights          ← 1:N time periods
    ├── campaign_placements       ← 1:N targeting surfaces/stores
    ├── campaign_creatives        ← 1:N creative → asset links
    ├── campaign_approvals        ← 1:N approval records
    ├── campaign_status_history   ← 1:N audit trail
    └── outbox_events             ← transactional side effects
```

#### `campaigns`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `advertiser_organization_id` | UUID FK NOT NULL | Tenant root |
| `advertiser_brand_id` | UUID FK nullable | Optional brand scope |
| `advertiser_contract_id` | UUID FK NOT NULL | Budget tracking |
| `code` | VARCHAR(64) NOT NULL | Human-readable, unique per org |
| `name` | VARCHAR(255) NOT NULL | Display name |
| `description` | TEXT nullable | |
| `status` | campaign_status ENUM | Lifecycle state |
| `priority` | INT DEFAULT 0 | Higher = more weight in conflicts |
| `budget_limit_amount` | NUMERIC nullable | Null = uncapped |
| `budget_limit_currency` | VARCHAR(3) DEFAULT 'RUB' | |
| `start_at` | TIMESTAMPTZ nullable | Earliest allowed delivery (null = manual activation only) |
| `end_at` | TIMESTAMPTZ nullable | Latest allowed delivery |
| `timezone` | VARCHAR(64) DEFAULT 'Europe/Moscow' | IANA timezone for dayparting |
| `created_by` | UUID FK → users.id | |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

UNIQUE `(advertiser_organization_id, code)`.

#### `campaign_flights`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `campaign_id` | UUID FK NOT NULL | |
| `name` | VARCHAR(255) nullable | e.g. "Week 1", "Holiday push" |
| `start_at` | TIMESTAMPTZ NOT NULL | Flight start |
| `end_at` | TIMESTAMPTZ NOT NULL | Flight end |
| `dayparting_json` | JSONB nullable | Day/time windows (see §4) |
| `days_of_week` | SMALLINT[] nullable | Bitmask or array [0..6] |
| `priority` | INT DEFAULT 0 | Overrides campaign priority within this flight |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

#### `campaign_placements`

Placements target `display_surfaces`, not physical devices.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `campaign_id` | UUID FK NOT NULL | |
| `display_surface_id` | UUID FK NOT NULL | Target surface (ADR-010 surface model) |
| `store_id` | UUID FK nullable | Optional store-level targeting |
| `cluster_id` | UUID FK nullable | Optional cluster-level targeting |
| `branch_id` | UUID FK nullable | Optional branch-level targeting |
| `share_of_voice_pct` | INT DEFAULT 100 | 0-100, weight in loop |
| `max_impressions` | BIGINT nullable | Null = unlimited |
| `impressions_delivered` | BIGINT DEFAULT 0 | Running counter |
| `status` | placement_status ENUM | active/paused/completed |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

**Constraint:** at least one of `display_surface_id`, `store_id`,
`cluster_id`, or `branch_id` must be non-null (targeting intent
required).

**Rationale for surface targeting:** physical devices can have multiple
surfaces (dual-screen KSO, LED panel array, ESL shelf array).
Targeting `display_surfaces` decouples campaign logic from hardware
topology.  The manifest generator resolves surfaces → devices at
delivery time.

#### `campaign_creatives`

Links a campaign to creative assets.

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `campaign_id` | UUID FK NOT NULL | |
| `creative_asset_id` | UUID FK NOT NULL → creative_assets | |
| `sort_order` | INT DEFAULT 0 | Playlist ordering within campaign |
| `duration_override_ms` | INT nullable | Override asset default duration |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

UNIQUE `(campaign_id, creative_asset_id)`.

#### `creative_assets`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `advertiser_organization_id` | UUID FK NOT NULL | Tenant ownership |
| `code` | VARCHAR(64) NOT NULL | Unique per org |
| `name` | VARCHAR(255) NOT NULL | |
| `media_type` | VARCHAR(32) NOT NULL | image/png, image/jpeg, video/mp4, video/webm, html/widget |
| `storage_bucket` | VARCHAR(128) NOT NULL | MinIO/S3 bucket |
| `storage_key` | VARCHAR(512) NOT NULL | Object key (not presigned URL) |
| `sha256_checksum` | VARCHAR(64) NOT NULL | Content integrity |
| `file_size_bytes` | BIGINT NOT NULL | |
| `duration_ms` | INT nullable | Null for static images |
| `resolution_w` | INT nullable | |
| `resolution_h` | INT nullable | |
| `status` | asset_status ENUM | uploading/ready/failed/archived |
| `moderation_status` | moderation_status ENUM | pending/approved/rejected |
| `moderation_notes` | TEXT nullable | |
| `created_by` | UUID FK → users.id | |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |
| `updated_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

UNIQUE `(advertiser_organization_id, code)`.

**Rule:** no raw binary in PostgreSQL.  Only metadata + storage
reference.  Binary stored in MinIO/S3 via presigned upload.
`storage_key` is NOT a presigned URL — it is an opaque key that the
media service resolves to a presigned URL on read.

**Future hook:** `moderation_status` is a placeholder for content
validation/scan integration (ADR-004 compliance, not in Phase 4.1).

#### `campaign_approvals`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `campaign_id` | UUID FK NOT NULL | |
| `requested_by` | UUID FK → users.id | Who submitted |
| `requested_at` | TIMESTAMPTZ NOT NULL | |
| `reviewed_by` | UUID FK → users.id nullable | Who approved/rejected |
| `reviewed_at` | TIMESTAMPTZ nullable | |
| `decision` | approval_decision ENUM | approved/rejected |
| `rejection_reason` | TEXT nullable | Required if rejected |
| `created_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |

**Invariant:** campaign cannot transition `pending_approval → approved`
without a `campaign_approvals` record with `decision = approved`.

#### `campaign_status_history`

| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `campaign_id` | UUID FK NOT NULL | |
| `old_status` | campaign_status nullable | Null = creation |
| `new_status` | campaign_status NOT NULL | |
| `changed_by` | UUID FK → users.id NOT NULL | |
| `changed_at` | TIMESTAMPTZ NOT NULL DEFAULT NOW() | |
| `reason` | TEXT nullable | Free-text audit context |

**Rule:** every status transition writes a history row in the same
transaction as the status update.

### 3. Status Lifecycle

```
                  ┌──────────────────────────────────┐
                  │                                  │
                  ▼                                  │
draft ──→ pending_approval ──→ approved ──→ scheduled ──→ active ──→ completed
  │                │               │            │         │
  │                │               │            │         ├──→ paused ──→ active
  │                │               │            │         │
  └──→ archived    └──→ rejected   └──→ rejected│         └──→ archived
                  (draft again)                 │
                                        └──→ archived
```

| From | To | Who | Constraint |
|------|----|-----|------------|
| — | `draft` | advertiser | Creation |
| `draft` | `pending_approval` | advertiser | Has ≥1 creative + ≥1 placement |
| `draft` | `archived` | advertiser | Direct archive |
| `pending_approval` | `approved` | internal (operator/admin) | Approval record created |
| `pending_approval` | `rejected` | internal | Reason required |
| `pending_approval` | `draft` | advertiser | Withdraw submission |
| `approved` | `scheduled` | internal or system | `start_at`/`end_at` validated |
| `approved` | `rejected` | internal | Revoke approval (reason required) |
| `approved` | `draft` | advertiser | Unlock for edits |
| `scheduled` | `active` | system (auto) | `start_at ≤ NOW()` and not paused |
| `scheduled` | `paused` | internal/advertiser | Manual pause |
| `active` | `paused` | internal/advertiser | Manual pause |
| `active` | `completed` | system (auto) | `end_at < NOW()` |
| `paused` | `active` | internal/advertiser | Resume (resumes at previous priority) |
| `paused` | `completed` | system | `end_at` passed while paused |
| `paused` | `draft` | advertiser | Unlock for edits |
| `active` | `archived` | internal | Admin force-archive |
| `paused` | `archived` | internal | Admin force-archive |
| `completed` | `archived` | internal | Cleanup |
| `rejected` | `draft` | advertiser | Revise and resubmit |

**Audit:** every transition writes `campaign_status_history` + an
outbox event `campaign.status_changed` with `{old_status, new_status,
campaign_id, changed_by}`.

### 4. Scheduling

#### Time Bounds

`campaigns.start_at` / `end_at` define the overall delivery window.
`campaign_flights` subdivide the window into periods with optional
dayparting.

```json
// campaign_flights.dayparting_json
{
  "windows": [
    {"days": [1,2,3,4,5], "start_time": "08:00", "end_time": "12:00"},
    {"days": [1,2,3,4,5], "start_time": "17:00", "end_time": "21:00"},
    {"days": [6,0],       "start_time": "10:00", "end_time": "20:00"}
  ]
}
```

- `days` — ISO weekday numbers: 1=Monday, 7=Sunday. 0 also = Sunday.
- `start_time` / `end_time` — HH:MM in the campaign's IANA timezone.
- Windows must not overlap within a flight.
- Empty `dayparting_json` = "any time" within the flight's `start_at..end_at`.

#### Timezone

Campaign timezone defaults to `Europe/Moscow`.  Dayparting windows
are interpreted in this timezone.  The manifest generator converts
to device-local timezone at generation time.

**Validation (fail-closed):**
- `start_at < end_at` enforced at DB constraint level.
- Flight `start_at`/`end_at` must be within campaign `start_at`/`end_at`.
- Overlapping windows within a flight → rejected at API layer.
- Past dates accepted for `draft` campaigns; rejected for `pending_approval`
  and beyond.

#### Targeting

Placements target one of:
- `display_surface_id` — exact surface
- `store_id` — all surfaces in a store
- `cluster_id` — all surfaces in a cluster
- `branch_id` — all surfaces in a branch

At least one must be set.  Targeting is resolved at manifest generation
time to a concrete set of `display_surface_ids`.  The manifest contains
only resolved surface IDs — no hierarchy references.

### 5. Placement and Surface Model

Placements target `display_surfaces`, not `physical_devices`.

**Why:** ADR-003 and ERD v2.5 define `physical_devices → logical_carriers
→ display_surfaces`.  One physical device (e.g. dual-screen KSO) has
multiple display surfaces.  A campaign targets "the left screen" — a
surface, not a device.

**Manifest resolution:** the manifest generator:
1. Reads `campaign_placements` for all active campaigns.
2. Resolves `store_id`/`cluster_id`/`branch_id` to concrete
   `display_surface_ids`.
3. Resolves `display_surface_ids` → `logical_carrier_id` →
   `physical_device_id`.
4. Groups by `physical_device_id` to produce per-device manifests.

**Invariant:** the placement table never references `physical_device_id`
directly.  Targeting is always at surface level or higher.

### 6. Creative Model

#### Asset Lifecycle

```
uploading → ready → archived
              │
              └──→ failed (checksum/format validation errors)
```

- `uploading` — ingest in progress (presigned upload).
- `ready` — validated, available for campaigns.
- `failed` — checksum mismatch, format not supported, or moderation
  rejection.
- `archived` — soft-deleted, not available for new campaigns.

#### Storage

Assets live in MinIO/S3.  PostgreSQL holds metadata only.
`storage_bucket` + `storage_key` = object path.  The media service
generates time-limited presigned URLs on read.

**No presigned URLs in the database.**  The `storage_key` is an opaque
reference; presigned URLs are generated at access time and are never
stored persistently.

#### Integrity

- `sha256_checksum` computed at upload completion; compared after
  download by player (ADR-013 §1).
- `file_size_bytes` validated against actual object size at upload.
- `duration_ms` validated from media headers for video; null for images.
- `media_type` constrained to platform-supported formats at API layer.

#### Future: Moderation Hook

`moderation_status` defaults to `approved` (no automated scan initially).
When content validation is integrated, the upload pipeline will:
1. Upload → `moderation_status = pending`.
2. Async scan (virus, NSFW, brand compliance).
3. Callback → `moderation_status = approved|rejected`.
4. Only `approved` assets can be linked to campaigns.

### 7. Approval Workflow

| Step | Actor | Action |
|------|-------|--------|
| 1 | Advertiser | Drafts campaign, adds creatives + placements |
| 2 | Advertiser | Submits → `status = pending_approval` |
| 3 | Internal (operator/admin) | Reviews campaign details, creatives, targeting |
| 4 | Internal | Approves → `campaign_approvals` row + `status = approved` |
| 5 | Internal | Rejects → `campaign_approvals` row + reason + `status = rejected` |

**RBAC:**
- `advertiser` scope users → draft, submit, withdraw, edit `draft`/`rejected`.
- `operator` role → view campaigns, approve/reject with
  `campaigns.approve` permission.
- `admin` → all operator rights + force-archive, force-status-change.

**Invariant:** a campaign with `status` beyond `approved` (i.e.,
`scheduled`, `active`, `paused`, `completed`) must have at least one
`campaign_approvals` row with `decision = approved`.

**Audit:** approval/rejection writes:
1. `campaign_approvals` row (who, when, decision).
2. `campaign_status_history` row (old → new status).
3. Outbox event `campaign.approval.decided` (for downstream:
   manifest generator wakes up on approval).

### 8. Delivery and Outbox Integration

Per ADR-011: every campaign mutation that changes delivery-relevant
state produces an outbox event in the same transaction.

| Mutation | Outbox event | Consumer |
|----------|-------------|----------|
| Campaign created | `campaign.created` | Analytics, audit |
| Campaign status → `scheduled` | `campaign.scheduled` | Manifest generator |
| Campaign status → `active` | `campaign.activated` | Manifest generator, PoP readiness |
| Campaign status → `paused` | `campaign.paused` | Manifest generator (removes from active manifests) |
| Campaign status → `completed` | `campaign.completed` | Manifest generator, analytics |
| Placement added/removed | `campaign.placement.changed` | Manifest generator |
| Creative added/removed | `campaign.creative.changed` | Manifest generator |
| Approval decided | `campaign.approval.decided` | Manifest generator, audit |
| Schedule/flight changed | `campaign.schedule.changed` | Manifest generator |

**Rule:** no `nats.publish()` inside mutation transactions.  All events
go through `outbox_events` → relay worker → NATS JetStream.

**Direct NATS publish is allowed only for:** device heartbeat
(`device.heartbeat`), PoP batch ingest (`pop.ingest.batch`), and
fire-and-forget telemetry — per ADR-011 §7.

### 9. Proof-of-Play and Reporting

Per ADR-013 §6: PoP events are emitted only after actual render.

| PoP field | Source | Notes |
|-----------|--------|-------|
| `campaign_id` | Manifest → PoP event | From active manifest |
| `creative_version_id` / `media_asset_id` | Manifest → PoP event | Which creative was rendered |
| `manifest_id` | Manifest header | Which manifest was active |
| `surface_id` | Device → PoP event | Which surface rendered |
| `duration_ms` | Actual render time | From renderer, not scheduled |
| `playback_result` | Render outcome | `success`, `skipped`, `failed` |

**Billing/reporting:**
- Only `playback_result = success` counts toward billing.
- `failed` / `skipped` / `interrupted` are diagnostics only.
- No billing for fallback content (unless `emit_pop = true`).
- No PoP emitted for content not rendered.

**Reporting flow:**
1. Device emits PoP → local buffer → Device Gateway → NATS JetStream.
2. PoP Ingestor → PostgreSQL (recent 30d) + ClickHouse (deferred).
3. Campaign performance dashboards query PostgreSQL materialized views.
4. Advertiser cabinet shows campaign-level PoP stats (scoped by
   `advertiser_organization_id`).

### 10. RLS and Security

Every campaign-scoped table has `ENABLE ROW LEVEL SECURITY + FORCE ROW
LEVEL SECURITY` with fail-closed SELECT policies (ADR-009 pattern).

| Table | RLS policy | Filter |
|-------|-----------|--------|
| `campaigns` | Advertiser sees own | `advertiser_organization_id = ANY(current_setting(...)::uuid[])` |
| `campaign_placements` | Via campaign | Subquery: `campaign_id IN (SELECT id FROM campaigns WHERE ...)` |
| `campaign_creatives` | Via campaign | Same pattern |
| `campaign_flights` | Via campaign | Same pattern |
| `creative_assets` | Advertiser sees own | `advertiser_organization_id = ANY(...)` |

**Internal users:** scoped users (operator, analyst) obey
branch/cluster/store scope via `require_scoped_permission`.

**Advertiser users:** see only their organization's campaigns.
Contact PII never exposed through campaign endpoints.

**Permission mapping:**

| Permission | Scope | Grants |
|------------|-------|--------|
| `campaigns.read` | Global or advertiser | List/view campaigns |
| `campaigns.create` | Advertiser scoped | Draft campaigns |
| `campaigns.manage` | Internal | Edit any campaign, force status changes |
| `campaigns.approve` | Internal | Approve/reject |
| `campaigns.archive` | Internal | Archive campaigns |
| `creatives.read` | Global or advertiser | View creative metadata |
| `creatives.upload` | Advertiser scoped | Upload new creatives |
| `creatives.manage` | Internal | Moderate, force-delete |

### 11. API Phase Split

| Phase | Deliverable | Endpoints |
|-------|------------|-----------|
| **4.1b** | DB schema + read-only | `GET /api/v1/campaigns`, `GET /api/v1/campaigns/{code}`, `GET /api/v1/campaigns/{code}/placements`, `GET /api/v1/campaigns/{code}/creatives`, `GET /api/v1/campaigns/{code}/flights`, `GET /api/v1/creatives` |
| **4.1c** | Mutations draft/update/archive | `POST /api/v1/campaigns`, `PATCH /api/v1/campaigns/{code}`, `POST /api/v1/campaigns/{code}/submit`, `PATCH /api/v1/campaigns/{code}/status`, `POST/DELETE` placements, creatives, flights |
| **4.1d** | Approval workflow | `POST /api/v1/campaigns/{code}/approve`, `POST /api/v1/campaigns/{code}/reject`, approval history |
| **4.1e** | Delivery/outbox | Outbox relay worker, manifest generator integration, `campaign.*` outbox events |
| **4.1f** | Reporting/PoP | Campaign performance dashboards, PoP-to-campaign aggregation, advertiser reporting |

**All endpoints** require JWT + `require_scoped_permission` + RLS
(two-layer defense per ADR-009).

### 12. Behavioral Proof Requirements

Before ACCEPTING any Phase 4.1b+ deliverable:

| Test | What it proves |
|------|---------------|
| Tenant isolation | Advertiser A sees only own campaigns; advertiser B sees only own |
| Cannot deliver unapproved | `active`/`scheduled` transition blocked without approval record |
| Invalid schedule rejected | `end_at < start_at`, overlapping flight windows → 422 |
| Outbox in same transaction | Campaign status change → `outbox_events` row committed |
| Rollback = no outbox | `BEGIN; UPDATE campaign; INSERT outbox; ROLLBACK` → relay sees nothing |
| PoP only for rendered | `playback_result=success` → billing counter increments; `skipped`/`failed` → does not |
| Admin sees all | system_admin → all campaigns regardless of advertiser |
| Scoped sees own | Advertiser user → filtered by `advertiser_organization_id` via RLS |
| PII not leaked | Contact email/phone not in campaign response payloads |

**Per ADR-008 testing gates:** unit tests for models, seed, and router
compliance; behavioral tests for all auth/RBAC/RLS paths.  No endpoint
accepted without negative behavioral proof (401, 403, scoped-200,
global-200).

### 13. Related Updates

This ADR requires:
- **ERD v2.5** — add campaign domain tables with ADR-015 annotations.
- **api-groups-v1.md §7** — add Phase 4.1b read-only campaign +
  creatives endpoints; mark Phase 4.1c–f as deferred.
- **architecture/README** — add ADR-015 to active documents.

## Consequences

- **Positive:** Campaign domain is fully specified before implementation.
  Tenant isolation, status lifecycle, scheduling, placement targeting,
  approval, delivery, and PoP attribution are locked.  Behavioral
  test requirements prevent regressions at every phase gate.

- **Negative:** Seven new tables increase migration surface.  Status
  lifecycle validation is complex (20+ transitions).  Outbox integration
  adds latency (~1ms per event INSERT).  Manifest generator must resolve
  hierarchy → surfaces → devices at generation time.

- **Risk:** `placement_targets` deferring to `display_surface_id` means
  the manifest generator must resolve hierarchy (branch → cluster →
  store → surface) at generation time.  This is a CPU-bound operation
  that must be tested at scale (hundreds of campaigns × thousands of
  surfaces).  Mitigation: materialize resolved surface sets per
  campaign in a cache table; regenerate only on placement change.

## References

- ADR-002 — Event bus (NATS JetStream)
- ADR-003 — Device identity and surface model
- ADR-007 — Analytics boundary (operational reports on PostgreSQL)
- ADR-009 — Fail-closed scopes and PostgreSQL RLS
- ADR-010 — Advertiser domain foundation (tenant root, brands, contracts)
- ADR-011 — Transactional outbox (mandatory for campaign events)
- ADR-013 — Edge runtime safety (PoP integrity, kill-switch, manifest atomicity)
- ADR-014 — Layering and import boundaries
- `docs/architecture/contracts/universal-manifest-v1.md` — Manifest schema
- `docs/architecture/contracts/proof-event-v1.md` — PoP schema
- `docs/architecture/events/event-contracts-v1.md` — Event envelope
- `docs/architecture/erd/erd-v2-5.md` — Current ERD
- `docs/architecture/api/api-groups-v1.md` — Current API catalog
