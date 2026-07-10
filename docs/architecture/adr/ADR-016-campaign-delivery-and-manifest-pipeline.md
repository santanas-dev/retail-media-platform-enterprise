# ADR-016: Campaign Delivery and Manifest Pipeline

**Status:** Accepted
**Date:** 2026-07-05
**Phase:** 4.2a (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ADR-015 §8 defines the delivery/outbox integration surface: which campaign
mutations produce events that should wake the manifest generator.  ADR-013
defines edge runtime safety: how a device receives, validates, and applies
manifests; kill-switch behavior; offline tolerance; PoP integrity.  ADR-011
mandates the transactional outbox pattern — no direct NATS publish from
OLTP mutations.

What remains undefined: **how an approved/scheduled campaign becomes a
manifest delivered to devices.**  The pipeline from campaign status change
to a verified manifest on a physical device is a multi-step async workflow
with multiple failure modes and safety invariants.

This ADR locks every decision before a single delivery component is built.

## Decision

### 1. Delivery Trigger

Campaign mutations that change delivery-relevant state produce an outbox
event in the same transaction (per ADR-011, ADR-015 §8).  Manifest
generation runs **asynchronously downstream** — never inside the mutation
transaction.

| Trigger | Outbox event | Consumer |
|----------|-------------|----------|
| Campaign approved | `campaign.approved` | Delivery planner |
| Campaign status → scheduled | `campaign.scheduled` | Delivery planner |
| Campaign status → active | `campaign.activated` | Manifest generator |
| Campaign updated (draft→approved/re-scheduled) | `campaign.updated` | Delivery planner |
| Campaign archived | `campaign.archived` | Manifest revoker |
| Campaign paused | `campaign.paused` | Manifest revoker |
| Campaign completed | `campaign.completed` | Manifest revoker |
| Placement added/changed | `campaign.placement.changed` | Delivery planner |
| Creative added/changed | `campaign.creative.changed` | Delivery planner |
| Flight added/changed | `campaign.flight.changed` | Delivery planner |

**Rule:** `campaign.approved` is the primary wake-up for delivery
planning.  `campaign.updated` when status is already ≥ approved also
triggers re-planning.  No manifest generation inside mutation POST
handlers — the mutation finishes in ~10ms, the manifest work happens
later with its own retry/failure handling.

### 2. Delivery Eligibility

A campaign is **eligible for manifest generation** when ALL of:

| Condition | Check |
|-----------|-------|
| Status ≥ `approved` | Approval record exists (ADR-015 §7) |
| Flight window valid | `start_at ≤ NOW()` (for `scheduled`/`active`) AND `end_at > NOW()` (not expired) |
| Contract valid | Contract `valid_from ≤ NOW()` AND (`valid_until IS NULL` OR `valid_until > NOW()`) |
| ≥1 placement target resolved | At least one placement resolves to ≥1 `display_surface_id` |
| ≥1 valid creative asset | At least one linked creative asset with `status = ready` AND `moderation_status = approved` |

**Runtime kill-switch** is checked at render time on the device (ADR-013
§2), NOT at manifest generation time.  Manifests are generated assuming
the campaign *may* play; the kill-switch is a runtime gate.  This avoids
regenerating manifests on every kill-switch toggle.

**Eligibility changes:** when a campaign becomes ineligible (archived,
paused, flight expired), a revocation event is produced.  The delivery
worker marks the device's manifest as needing a refresh, and on next
heartbeat/manifest pull the device receives an updated manifest without
the campaign.

### 3. Target Resolution

Per ADR-015 §5, placements target a location in the hierarchy — never
`physical_device_id` directly.

**Resolution chain:**

```
campaign_placements
  ├── display_surface_id (exact) ──────────┐
  ├── store_id            (broad) ──→ resolve → display_surface_ids
  ├── cluster_id          (broad) ──→ resolve → display_surface_ids
  └── branch_id           (broad) ──→ resolve → display_surface_ids
                                                    │
                                         ┌──────────┘
                                         ▼
                                   display_surfaces
                                         │
                                    logical_carrier_id
                                         │
                                    physical_device_id
```

**Resolution rules:**

- `display_surface_id` — direct, no resolution needed.
- `store_id` — all active display surfaces in that store.
- `cluster_id` — all active display surfaces in stores in that cluster.
- `branch_id` — all active display surfaces in stores whose clusters
  belong to that branch.
- Only surfaces with `status = active` and their linked device operational
  are included.
- Resolution is performed **at generation time** — the manifest contains
  only resolved surface IDs, no hierarchy references.

**Grouping:** resolved surfaces are grouped by `physical_device_id` to
produce **one manifest per physical device**.  A dual-screen KSO device
with two surfaces gets ONE manifest containing two `display_surfaces[]`
entries.  A store with 10 single-surface devices gets 10 separate
manifests.

### 4. Manifest Schema and Content

Each manifest is a signed JSON document following a schema compatible
with ADR-013's manifest apply protocol (§3: signature, monotonic version,
device_id match, media download).

> **S-018 (2026-07-10):** The pilot Manifest v1 uses a **flat `playlist[]`**
> at the manifest level, not nested under `display_surfaces[]`.  This is
> sufficient for single-surface KSO devices.  Per-surface `display_surfaces[].playlist[]`
> is deferred to **Manifest v2** for multi-surface KSO (dual-screen) support.
> The canonical schema lives at `packages/contracts/manifest_v1.schema.json`.
> Every generated manifest is validated against this schema (see S-018
> contract tests).

**Manifest structure (pilot v1 — flat playlist):**

```json
{
  "manifest_id": "<hash(campaign_version + device_id + generated_at)>",
  "manifest_version": "<monotonic counter per device>",
  "device_id": "<target device>",
  "generated_at": "<ISO8601>",
  "valid_from": "<campaign flight start>",
  "valid_to": "<campaign flight end or next planned update>",
  "offline_ttl_hours": 168,
  "schema_version": "1.0",
  "signature": {
    "algorithm": "HMAC-SHA256",
    "value": "<base64>"
  },
  "display_surfaces": [
    {
      "surface_id": "<uuid>",
      "playlist": [
        {
          "slot_id": "<uuid>",
          "campaign_id": "<uuid>",
          "creative_asset_id": "<uuid>",
          "media_type": "video/mp4",
          "presigned_url": "<time-limited URL>",
          "sha256_checksum": "<hex>",
          "duration_ms": 15000,
          "share_of_voice_pct": 40,
          "dayparting": { ... }
        }
      ]
    }
  ],
  "fallback_rules": {
    "on_manifest_expired": "show_fallback",
    "on_network_lost": "continue_last_valid",
    "filler_media_ids": [],
    "emit_pop": false
  }
}
```

**Security invariants for manifests:**

- `presigned_url` — time-limited, generated at manifest creation, valid
  for `offline_ttl_hours` + 2h buffer.  No permanent credentials.
- `storage_key` never appears in the manifest — only presigned URLs.
- No `advertiser_organization_id`, no contact PII, no internal IDs
  unrelated to render.
- `signature` covers the entire manifest including `manifest_id` and
  `manifest_version` — prevents tampering and replay.

### 5. Manifest Versioning

| Field | Semantics | Source |
|-------|-----------|--------|
| `manifest_id` | Content-addressed: `SHA-256(input_concat)` where `input_concat` is the byte-concatenation of the fields below, sorted where applicable | Deterministic, no wall-clock dependency |
| `manifest_version` | Monotonic counter per `device_id` | Incremented on each generated manifest |

**`manifest_id` input (canonical order):**

```
campaign.id ‖ campaign.status ‖ campaign.updated_at
‖ sorted(linked creative_asset.id) ‖ sorted(creative_asset.sha256_checksum)
‖ sorted(linked campaign_flight.id) ‖
  sorted(flight.start_at ‖ flight.end_at ‖ flight.dayparting_json ‖ flight.days_of_week)
‖ sorted(linked campaign_placement.id) ‖
  sorted(resolved display_surface.id for this device)
‖ device_id
```

All fields are concatenated as UTF-8 bytes with `‖` (U+2016) as the field separator. Lists are sorted lexicographically by their natural key before concatenation.

**Rationale for excluding `generated_at` from `manifest_id`:** including wall-clock time in the content hash makes the manifest ID non-deterministic — generating the same manifest twice produces different IDs, breaking idempotency. `manifest_version` (monotonic counter) already provides temporal ordering. `campaign.updated_at` in the hash captures the campaign's logical version; the manifest ID is stable for the same campaign/device content regardless of when generation runs.

**Version bump triggers:** any change to campaign content, flight window,
placement set, creative assets, or share-of-voice for that device.

**Rollback semantics:**

- Device always retains the **last-known-good manifest** (fully verified
  and applied per ADR-013 §3).
- If a new manifest is corrupt, invalid, or fails media download, the
  device continues with the last-known-good version.
- `emergency_flag = true` in a manifest permits version downgrade
  (ADR-013 §3 monotonic guard override).
- After rollback, the device reports the failure via
  `manifest.apply.failed` event.

**Idempotency:** generating the same manifest for the same
campaign/device content twice produces the same `manifest_id`.
The delivery worker can re-generate without creating duplicate manifests.
The device rejects manifests with `manifest_version <= current_version`
(unless emergency).

### 6. Outbox and Event Flow

All delivery events follow the ADR-011 transactional outbox pattern:

```
Campaign mutation (FastAPI handler)
  ├── UPDATE campaign status / INSERT outbox event ─── in same DB transaction
  └── return HTTP response

Outbox Relay Worker (background)
  ├── poll outbox_events WHERE status IN ('pending','failed')
  ├── publish to NATS JetStream (campaign.approved, campaign.updated, ...)
  └── mark published

Delivery Planner Worker (NATS consumer)
  ├── consumes all campaign delivery triggers from §1:
  │     campaign.approved, campaign.updated, campaign.scheduled,
  │     campaign.activated, campaign.paused, campaign.completed,
  │     campaign.archived, campaign.placement.changed,
  │     campaign.creative.changed, campaign.flight.changed
  ├── check eligibility (§2)
  ├── if eligible: resolve targets (§3), produce delivery.manifest.requested
  └── if ineligible: log, no manifest

Manifest Generator Worker (NATS consumer)
  ├── on delivery.manifest.requested
  ├── group targets by physical_device_id
  ├── for each device:
  │   ├── collect playlist items (creatives × surfaces × flights)
  │   ├── resolve dayparting to device timezone
  │   ├── resolve share_of_voice to slot weights
  │   ├── generate presigned URLs
  │   ├── compute manifest_id, increment manifest_version
  │   ├── sign manifest
  │   ├── store manifest in manifest_store (MinIO/S3 + metadata in PG)
  │   └── produce delivery.manifest.generated
  └── on failure: produce delivery.manifest.failed with reason

Device Gateway (responds to device polls)
  ├── device GET /device/v1/manifest
  ├── check if new manifest_version > device.current_version
  ├── return manifest (ETag + 304 if unchanged)
  └── device applies manifest per ADR-013 §3
```

**Event catalog:**

| Event | Producer | Key payload |
|-------|----------|-------------|
| `campaign.approved` | Control API (outbox) | `campaign_id`, `advertiser_organization_id` |
| `campaign.updated` | Control API (outbox) | `campaign_id`, `updated_fields` |
| `campaign.archived` | Control API (outbox) | `campaign_id` |
| `campaign.scheduled` | Control API (outbox) | `campaign_id`, `start_at` |
| `campaign.paused` | Control API (outbox) | `campaign_id` |
| `campaign.completed` | Control API (outbox) | `campaign_id` |
| `campaign.placement.changed` | Control API (outbox) | `campaign_id` |
| `campaign.creative.changed` | Control API (outbox) | `campaign_id` |
| `campaign.flight.changed` | Control API (outbox) | `campaign_id` |
| `delivery.manifest.requested` | Delivery Planner | `campaign_id`, `target_device_ids[]` |
| `delivery.manifest.generated` | Manifest Generator | `manifest_id`, `device_id`, `manifest_version`, `campaign_ids[]` |
| `delivery.manifest.failed` | Manifest Generator | `campaign_id`, `device_id`, `reason` |

**No direct NATS publish from control-api or domain packages.** Only the
outbox relay worker publishes to NATS.  The manifest generator and
delivery planner consume from NATS via JetStream durable consumers.

### 7. Idempotency and Deduplication

| Level | Mechanism |
|-------|-----------|
| Outbox relay | `outbox_events.event_id` — at-least-once, consumer dedupes by event_id |
| Delivery planner | `campaign_id + campaign.updated_at` — skip if no change since last plan |
| Manifest generator | `manifest_id = SHA-256(input_concat)` per §5 — same input → same `manifest_id`, no duplicate generation |
| Device | Monotonic `manifest_version` — rejects duplicate/downgrade |

**Re-delivery is safe.**  The delivery planner can run multiple times
for the same campaign version without generating duplicate manifests.
The manifest generator checks whether a manifest with the same
`manifest_id` already exists before storing a new one.

### 8. Observability

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| `delivery.manifest.generated.count` | Manifest Generator | — |
| `delivery.manifest.failed.count` | Manifest Generator | > 0 in 5 min |
| `delivery.manifest.generation.duration_ms` | Manifest Generator | p99 > 30s |
| `delivery.target_resolution.surface_count` | Delivery Planner | 0 = no eligible targets |
| `delivery.target_resolution.device_count` | Delivery Planner | — |
| `delivery.queue_age_seconds` | Outbox relay | > 60s |
| `delivery.device_lag_seconds` | Device Gateway | > 300s (device hasn't pulled) |
| `delivery.manifest.rollback.count` | Device Gateway | > 0 in 1 h |

All events carry `correlation_id` (campaign_id or manifest_id) for
end-to-end tracing across the async pipeline.

### 9. Security

| Rule | Enforcement |
|------|-------------|
| Manifest has no secrets | Schema validation on manifest generation; `presigned_url` only, no `storage_key`/bucket |
| Asset URLs are signed/short-lived | `presigned_url` with `offline_ttl_hours + 2h` expiry |
| No storage credentials in manifest | No `storage_bucket`, `access_key`, or `secret_key` fields |
| No contact PII | No `advertiser_organization_id`, `email`, `phone`, `contact_name` |
| Manifest signature verified by device | HMAC-SHA256 or Ed25519; device rejects unsigned manifests |
| Device authenticates before manifest pull | JWT `Authorization: Bearer` per ADR-003 |

### 10. Phase Split

| Phase | Deliverable | Description |
|-------|------------|-------------|
| **4.2a** | Architecture lock | This ADR (docs only) |
| **4.2b** | Delivery DB/model foundation | `manifest_store` table, `delivery_plans` tracking, outbox event types, migration |
| **4.2c** | Manifest generator worker skeleton | NATS consumer, target resolution, manifest JSON generation, presigned URL generation, signing, MinIO upload |
| **4.2d** | Device Gateway delivery endpoint | `GET /device/v1/manifest` with ETag/304, version check, manifest delivery |
| **4.2e** | Runtime simulator behavioral tests | Mock device that applies manifests, verifies ADR-013 safety invariants, kill-switch, rollback, PoP |

**PoP ingestion, reporting, and analytics remain in Phase 4.3+.**

### 11. Behavioral Proof Requirements

Before ACCEPTING any Phase 4.2b+ deliverable:

| Test | What it proves |
|------|---------------|
| Unapproved campaign generates no manifest | `status = draft` / `pending_approval` → delivery planner skips eligibility |
| Archived campaign removes delivery | `campaign.archived` → manifest without this campaign generated on next pull |
| Broad placement resolves to correct surfaces | `store_id` placement → manifest has all surfaces in that store |
| One physical device = one manifest | Multi-surface device → single manifest with multiple `display_surfaces[]` |
| Invalid campaign fails closed | No targets resolvable → `delivery.manifest.failed`, no partial manifest |
| Generated manifest validates against schema | Valid JSON, all required fields, no secrets, valid signature |
| Rollback creates no partial state | Failed manifest generation → device keeps last-known-good |
| Idempotent re-generation | Same input → same `manifest_id`, no duplicate store records |
| Kill-switch checked at runtime, not in manifest | Manifest generated for campaign → campaign kill-switched → device skips it at render, manifest unchanged |
| Presigned URLs are time-limited | URL expiry = `offline_ttl_hours + 2h`, no permanent credentials |

**Per ADR-008 testing gates:** behavioral/simulation tests for all auth,
RBAC, RLS, and runtime safety paths.  Runtime simulator required for
device-facing behavior (ADR-013 §10).

## Consequences

- **Positive:** Fully async delivery pipeline decoupled from campaign
  mutations.  Campaign approve → manifest generated → device pull is a
  resilient async chain with retry and observability at every step.
  Manifest versioning prevents replay and corruption.  Runtime safety
  (ADR-013) is baked into every device-facing decision.

- **Negative:** Three new workers (delivery planner, manifest generator,
  device gateway manifest endpoint) increase operational surface.
  Target resolution is CPU-bound for broad placements (branch-level at
  a large retailer = thousands of surfaces).  Presigned URL generation
  adds latency per manifest.

- **Risk:** Broad placement resolution at scale (branch → hundreds of
  stores → thousands of surfaces → manifest per device) could generate
  many manifests for a single campaign.  Mitigation: batch manifest
  generation, materialized surface-set cache per campaign, incremental
  regeneration only on placement/creative changes.

## References

- ADR-003 — Device identity (JWT, onboarding, no tokens in URLs)
- ADR-011 — Transactional outbox (mandatory for all delivery events)
- ADR-012 — Async I/O (manifest generation, presigned URL resolution)
- ADR-013 — Edge runtime safety (manifest apply protocol, kill-switch,
  offline behavior, PoP integrity)
- ADR-014 — Layering and import boundaries
- ADR-015 — Campaign domain foundation (§5 placement/surface model,
  §7 approval workflow, §8 delivery/outbox integration, §9 PoP)
- `docs/architecture/contracts/universal-manifest-v1.md` — Manifest schema
- `docs/architecture/contracts/proof-event-v1.md` — PoP schema
- `docs/architecture/events/event-contracts-v1.md` — Event envelope
- `docs/architecture/erd/erd-v2-5.md` — Current ERD
- `docs/architecture/api/api-groups-v1.md` — Current API catalog
