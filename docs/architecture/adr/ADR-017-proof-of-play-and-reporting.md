# ADR-017: Proof-of-Play and Reporting

**Status:** Accepted
**Date:** 2026-07-07
**Phase:** 4.3a (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ADR-013 defines edge runtime safety — PoP events are emitted by the
device runtime only after successful render, deduplicated by `event_id`,
and buffered locally until delivery.  ADR-016 defines the manifest
pipeline that schedules campaign content on devices.  Phase 4.2e proved
these invariants with a headless runtime simulator (41 behavioral tests).

What remains undefined: **the server-side ingestion, validation, storage,
and reporting pipeline for PoP events.**  PoP events are the canonical
evidence of ad delivery.  Every reporting dashboard, billing report, and
audit query depends on their integrity.  If an event is silently
dropped, duplicated, miscounted, or attributed to the wrong campaign,
the platform's billing and analytics are incorrect.

This ADR locks the architecture for the PoP pipeline before any
implementation begins.

## Decision

### 1. PoP Source — Runtime Only

PoP events are **emitted exclusively by the device runtime after a
successful render.**  The platform never synthesizes, estimates, or
invents PoP events.

| Source | Allowed | Rationale |
|--------|---------|-----------|
| Device runtime (successful render) | ✅ | ADR-013 §6: emit only after actual render |
| Device runtime (fallback) | Only if `fallback_rules.emit_pop = true` | Distinguish billable from filler |
| Device runtime (skipped/failed/interrupted) | ❌ | ADR-013 §6 anti-patterns |
| Manifest generator | ❌ | Generation ≠ delivery |
| Device gateway | ❌ | Gateway relays, does not play |
| Reporting/analytics pipeline | ❌ | Never synthesize events from DB state |

**Baseline:** the Phase 4.2e runtime simulator (41 tests) proves
that a compliant runtime emits PoP only when all safety gates pass,
deduplicates by `event_id`, and never emits PoP for fallback
(unless `emit_pop=true`).

### 2. PoP Ingestion Endpoint

**`POST /api/v1/pop/batch`** (Control API or dedicated PoP Ingestor service)

| Requirement | Implementation |
|-------------|---------------|
| Authentication | Device JWT (`auth_provider=device`). Reject user/admin tokens |
| Device binding | `event.device_id` (from payload) MUST match JWT `sub` |
| Batch format | JSON array of PoP events. Maximum 500 events per batch |
| Idempotency key | `event_id` (UUID). Dedup at ingestion layer |
| Duplicates | Return `409 Conflict` for individual duplicate `event_id`s; accepted events processed normally |
| At-least-once | Devices may retry; dedup handles this |
| Response | `accepted_count`, `rejected_count`, per-event rejection reasons |
| Clock drift | Accept timestamps up to ±5 minutes from server time; events outside that window are quarantined |

**Endpoint is read-write.**  Requires device authentication and
rate-limiting per ADR-005.

### 3. PoP Event Contract (Canonical)

Every accepted PoP event MUST contain these fields (per
`proof-event-v1.md` plus campaign-reporting additions):

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | UUID | Yes | Globally unique dedup key |
| `event_type` | string | Yes | Always `"proof"` |
| `manifest_id` | string | Yes | Manifest that scheduled this play |
| `campaign_id` | UUID | Yes | Owning campaign (resolved from manifest at ingest) |
| `creative_asset_id` | UUID | Yes | Media asset that was rendered |
| `surface_id` | string | Yes | Display surface |
| `device_id` | UUID | Yes | Physical device |
| `rendered_at` | ISO 8601 | Yes | When content was rendered (device clock) |
| `event_recorded_at` | ISO 8601 | Yes | When event was recorded by runtime |
| `duration_ms` | int | Yes | Playback duration in milliseconds |
| `playback_result` | enum | Yes | `success` only for billable events |

**Anti-requirements:**
- No `storage_bucket`, `storage_key`, `presigned_url` in events
- No contact PII (`email`, `phone`, `advertiser_contact`)
- No device secrets, tokens, or raw signatures in event payload
  (signature is validated at the gateway layer, not stored)

### 4. Validation Rules

Events are validated synchronously at ingestion before any DB write:

| Rule | Violation → Action |
|------|-------------------|
| `event_id` already exists in dedup index | Reject 409, do not double-count |
| `device_id` ≠ JWT `sub` | Reject 403 |
| `manifest_id` unknown (not in `delivery_manifests`) | **Quarantine** — accept, mark `pending_verification`. Do not count in reporting until manifest is confirmed. Quarantine TTL: 72 hours, then discard |
| `campaign_id`/`creative_asset_id`/`surface_id` missing or invalid | Reject 422 |
| `rendered_at` > server_time + 5 minutes | Quarantine (clock drift) |
| `rendered_at` < server_time - 30 days | Reject (stale event, outside reporting window) |
| `duration_ms` ∉ [1, 86_400_000] (1ms to 24h) | Reject 422 |
| `playback_result` ≠ `success` | Reject — only successes are billable |
| `event_type` ≠ `proof` | Reject 422 |

**Quarantine rationale:** a device may receive a manifest, render
content, and submit PoP before the manifest record reaches the backend
(manifest generation is asynchronous).  The ingest endpoint must accept
validly-formed events and hold them until the manifest is confirmed,
rather than rejecting and forcing device retry.

**Quarantine TTL:** 72 hours.  If the manifest still does not exist
after that window, the event is discarded (the manifest was likely
rolled back or the campaign was deleted).  Discarded events are logged
as `pop.event.quarantine_expired`.

### 5. Storage — PostgreSQL as Source of Truth

Per ADR-007, ClickHouse is deferred for later phases.  Phase 4.3 uses
PostgreSQL as the initial OLTP source of truth for PoP data.

**Tables (Phase 4.3b):**

```
pop_events_raw
├── id (UUID, PK)
├── event_id (UUID, UNIQUE INDEX)    ← dedup key
├── device_id (UUID, FK → physical_devices.id)
├── manifest_id (VARCHAR, FK → delivery_manifests.manifest_id)
├── campaign_id (UUID, FK → campaigns.id)
├── creative_asset_id (UUID, FK → creative_assets.id)
├── surface_id (VARCHAR)
├── rendered_at (TIMESTAMPTZ)
├── event_recorded_at (TIMESTAMPTZ)
├── duration_ms (INTEGER, CHECK >= 1)
├── status (VARCHAR 32)              ← 'accepted'|'quarantined'|'rejected'
├── quarantine_reason (VARCHAR 128)  ← nullable
├── received_at (TIMESTAMPTZ DEFAULT NOW())
└── batch_id (UUID)                  ← ingestion batch correlation

pop_dedup_index
├── event_id (UUID, UNIQUE, PK)      ← fast dedup lookup
└── created_at (TIMESTAMPTZ)
```

**No RLS on PoP tables** — events are device-owned and ingested by an
internal service.  Reporting APIs enforce their own RLS via JOINs to
campaign/placement visibility rules.

**No soft-delete / no UPDATE after acceptance.**  Accepted events are
immutable.  Quarantined events may transition to accepted or expired.

### 6. Reporting — Billing-Grade Integrity

| Principle | Rule |
|-----------|------|
| **Only successes count** | `playback_result = success` AND `status = accepted` |
| **No fallback in billing** | `emit_pop = false` by default; only explicit opt-in counts |
| **No scheduled-but-not-rendered** | Campaign schedules are not a billing signal |
| **No duplicates** | Dedup by `event_id` eliminates double-counting |
| **No quarantined events** | Only `accepted` events participate in counts |
| **No synthesized events** | Every counted event has a device-originated PoP |

**Initial reporting:** PostgreSQL materialized views refreshed on a
schedule (e.g., hourly for operational dashboards, daily for billing
exports).

**Deferred to Phase 4.3e:**
- Materialized views for campaign/placement/advertiser rollups
- CSV/Excel export endpoints
- Real-time dashboard streaming

### 7. Audit Trail

| Event | What is logged |
|-------|---------------|
| Batch accepted | batch_id, accepted_count, rejected_count, device_id, received_at |
| Individual event accepted | event_id, manifest_id, campaign_id, device_id |
| Event rejected | event_id, rejection reason, raw payload (sanitized — no secrets) |
| Event quarantined | event_id, quarantine reason, manifest_id, TTL |
| Quarantine expired | event_id, reason "manifest not confirmed within 72h" |
| Duplicate event | event_id, original received_at |

Audit events are written via the transactional outbox (ADR-011).
No direct NATS publish.

### 8. Outbox Integration

```
PoP Ingest (request)
  → validate events
  → BEGIN
      INSERT INTO pop_events_raw (...)
      INSERT INTO pop_dedup_index (...)
      INSERT INTO outbox_events (event_type='pop.event.accepted', ...)
    COMMIT
  → Relay Worker polls outbox → NATS JetStream
```

Event types emitted via outbox:

| Event Type | When |
|------------|------|
| `pop.event.accepted` | Event passed validation and was stored |
| `pop.event.quarantined` | Event valid but manifest unknown |
| `pop.event.rejected` | Event failed validation |
| `pop.batch.ingested` | Batch processing complete (summary) |

**No direct NATS publish from the ingestion handler.**  All events go
through the outbox (ADR-011).

### 9. Phase Split

| Phase | Deliverable | Scope |
|-------|------------|-------|
| **4.3a** | This ADR | Architecture lock |
| **4.3b** | PoP persistence schema | `pop_events_raw` table, `pop_dedup_index`, migration, seed |
| **4.3c** | Ingestion endpoint | `POST /api/v1/pop/batch`, validation, dedup, quarantine |
| **4.3d** | Reporting read-only | `GET /api/v1/reporting/campaign/{id}/impressions`, `GET /api/v1/reporting/dashboard` |
| **4.3e** | Materialized views + exports | Reporting optimizations, CSV exports |

### 10. Behavioral Proof Requirements

Before Phase 4.3c (ingestion endpoint) is accepted:

| # | Test | What it proves |
|---|------|---------------|
| 1 | Valid event accepted once | Insert succeeds, 201 response |
| 2 | Duplicate event ignored | Same `event_id` → 409, no second row |
| 3 | Event from wrong device rejected | `event.device_id ≠ JWT sub` → 403 |
| 4 | Fallback/skipped event rejected | `playback_result ≠ success` → 422 |
| 5 | Unknown manifest quarantined | `manifest_id ∉ delivery_manifests` → 202 quarantine |
| 6 | Future timestamp quarantined | `rendered_at > now + 5min` → 202 quarantine |
| 7 | Reporting count = accepted unique successes | `SELECT COUNT(*) WHERE status='accepted'` matches expected |
| 8 | Batch partial acceptance | Valid events accepted, invalid rejected, response reflects both |
| 9 | Device can resubmit after quarantine resolution | After manifest appears, previously quarantined event is accepted |

## Consequences

- **Positive:** Billing-grade integrity — every counted impression has
  a device-originated PoP event.  Dedup eliminates double-counting.
  Quarantine handles async manifest delivery without forcing device
  retry.  Audit trail is complete and queryable.

- **Negative:** Quarantine adds complexity — events sit in limbo for up
  to 72 hours.  PostgreSQL as PoP store will eventually hit scale limits;
  ClickHouse migration (ADR-007) is explicitly deferred.  Materialized
  views have refresh latency.

- **Risk:** A device submitting PoP for a manifest that was never
  persisted (e.g., manifest generation failed silently, outbox event
  lost) will have events quarantined → expired → discarded.  This is a
  data loss scenario.  Mitigation: manifest generation uses outbox
  (ADR-011) for at-least-once guarantees.  Monitor quarantine volumes;
  spikes indicate a backend delivery problem.

## References

- ADR-002 — Event bus (NATS JetStream)
- ADR-003 — Device identity (device JWT, no user tokens)
- ADR-005 — Monitoring and observability
- ADR-007 — Platform data boundary (ClickHouse deferred)
- ADR-011 — Transactional outbox
- ADR-013 — Edge runtime safety (PoP emission rules)
- ADR-016 — Campaign delivery and manifest pipeline
- `docs/architecture/contracts/proof-event-v1.md` — PoP schema
- `docs/architecture/events/event-contracts-v1.md` — Batch/event contracts
- `docs/architecture/phase-4-delivery-domain.md` — Delivery domain phases
- `tests/test_phase4_2e_runtime_simulator.py` — Runtime simulator (41 tests)
