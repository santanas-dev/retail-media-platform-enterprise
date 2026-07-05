# ADR-011: Transactional Outbox and Event Delivery

**Status:** Accepted
**Date:** 2026-07-04
**Phase:** 4.0a+ (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ADR-002 established NATS JetStream as the event bus.  Event contracts
define subjects, payloads, and delivery guarantees.  Proof events require
at-least-once delivery with idempotent deduplication.

What remains undefined: **how events leave the PostgreSQL transaction.**
Every domain event (campaign published, manifest generated, audit event
recorded) is produced inside a service that writes to PostgreSQL.  Without
a transactional outbox, the platform faces a dual-write problem:

```
BEGIN;
  INSERT INTO campaigns ...;
  ── nats.publish("campaign.created", ...) ── ← separate system
COMMIT;   ← PostgreSQL commits
          ← NATS publish already fired; if COMMIT fails, ghost event
```

The risk: a committed PostgreSQL write without a published event (lost
notification), or a published event without a committed PostgreSQL write
(ghost event).  Both are data-integrity bugs that compound across every
event-producing endpoint.

This ADR closes the gap: every domain event MUST go through a
PostgreSQL-backed transactional outbox before reaching NATS.

## Decision

### 1. Transactional Outbox is Mandatory

Every service that produces domain events as a side effect of an OLTP
write MUST use the outbox pattern:

```
BEGIN;
  INSERT INTO campaigns ...;              ← business write
  INSERT INTO outbox_events ...;          ← event in same transaction
COMMIT;                                   ← both or neither

── transaction committed ──

Relay Worker polls outbox_events (status='pending')
  → publishes to NATS JetStream
  → on broker ack → UPDATE outbox_events SET status='published'
```

**No service may call `nats.publish()` directly inside a
request/business transaction.**  Direct publish is allowed only for
fire-and-forget telemetry (heartbeats, metrics) that does not carry
business state.

### 2. `outbox_events` Table

```sql
outbox_events
┌─────────────────────────────┐
│ id (UUID, PK)               │
│ event_type (VARCHAR 128)    │  -- e.g. "campaign.created"
│ event_version (VARCHAR 16)  │  -- schema version "1.0"
│ aggregate_type (VARCHAR 64) │  -- "campaign", "placement", "manifest"
│ aggregate_id (UUID)         │  -- FK to owning entity
│ partition_key (VARCHAR 128) │  -- for ordering: device_id, advertiser_id
│ payload_json (JSONB)        │  -- full event payload
│ headers_json (JSONB)        │  -- correlation_id, source_service, etc.
| status (VARCHAR 32)         │  -- pending|publishing|published|failed|dead_letter
|                             │     publishing: relay claim lock (prevents
|                             │     double-processing in concurrent relay)
│ attempts (INT, DEFAULT 0)   │
│ next_attempt_at (TIMESTAMPTZ │
│   NOT NULL DEFAULT NOW())    │  -- immediate eligibility; producers
│ published_at (TIMESTAMPTZ,   │     may defer by setting a future time
│   nullable)                 │
│ last_error (TEXT, nullable) │
│ created_at (TIMESTAMPTZ)    │
└─────────────────────────────┘

CREATE INDEX idx_outbox_status_next ON outbox_events
  (status, next_attempt_at) WHERE status IN ('pending', 'failed');
```

**Constraints:**
- `payload_json` MUST NOT contain secrets, passwords, tokens, PII
  (email, phone), or raw credentials.
- `headers_json` carries `correlation_id`, `source_service`,
  `event_id` (same as `id`), `trace_parent` (W3C).
- `last_error` is truncated to 2048 chars — never includes raw
  payloads or stack traces in production.

### 3. Relay Worker

A single background worker (`outbox-relay`) polls `outbox_events`:

```
LOOP:
  SELECT * FROM outbox_events
    WHERE status IN ('pending', 'failed')
      AND next_attempt_at <= NOW()
    ORDER BY next_attempt_at
    LIMIT 100;

  FOR EACH event:
    subject = derive_subject(event_type)  -- "campaign.created" → "campaign.created"
    pub_ack = nats.jetstream_publish(subject, envelope(event))
    IF pub_ack:
      UPDATE outbox_events SET status='published', published_at=NOW()
    ELSE:
      UPDATE outbox_events SET status='failed',
        attempts=attempts+1,
        next_attempt_at=NOW() + backoff(attempts),
        last_error=error_message
      IF attempts >= max_attempts:
        UPDATE outbox_events SET status='dead_letter'
```

**Concurrency:** single worker (no leader election needed for initial
release).  Horizontal scaling via partition_key sharding deferred.

**Backoff:** exponential with jitter — `[1s, 2s, 4s, 8s, 16s, 32s,
64s]` → dead-letter after 7 failures (~2 min).  Configurable per
environment.

**Batch size:** 100 events per poll cycle, `LIMIT` prevents unbounded
memory.  Poll interval: 500ms default, configurable.

**Idempotent publish:** uses NATS JetStream dedup by `event_id`
(`Nats-Msg-Id` header).  If relay crashes between NATS ack and
PostgreSQL UPDATE, re-publish is harmless — JetStream deduplicates.

### 4. Delivery Semantics

| Guarantee | Mechanism |
|-----------|-----------|
| **At-least-once** | Outbox poll → JetStream publish with ack → UPDATE status.  Crash before UPDATE means re-delivery. |
| **Idempotent** | Consumers deduplicate by `event_id` from envelope metadata.  NATS JetStream dedup by `Nats-Msg-Id`. |
| **Ordered per partition** | `partition_key` groups events.  Relay publishes in `next_attempt_at` order within a poll batch.  No strict ordering within a batch — consumers sort by `created_at` if needed. |
| **No global ordering** | Events across different aggregates/partitions arrive in arbitrary order.  No total-order promise. |

### 5. Event Envelope

All outbox events are wrapped before NATS publish:

```json
{
  "metadata": {
    "event_id": "<outbox_events.id>",
    "event_type": "campaign.created",
    "version": "1.0",
    "timestamp": "2026-07-04T...",
    "correlation_id": "...",
    "source_service": "control-api",
    "partition_key": "ADV-001"
  },
  "payload": { ... }
}
```

This matches the existing envelope from `event-contracts-v1.md`.
`event_id` is the outbox row UUID — serves as both dedup key and
trace identifier.

### 6. Observability

Metrics exposed by the relay worker:

| Metric | Type | Description |
|--------|------|-------------|
| `outbox_events_pending` | Gauge | Current pending count |
| `outbox_events_published_total` | Counter | Successfully published |
| `outbox_events_failed_total` | Counter | Transient failures |
| `outbox_events_dead_letter_total` | Counter | Dead-lettered after max attempts |
| `outbox_age_oldest_seconds` | Gauge | Age of oldest pending event |
| `outbox_publish_latency_seconds` | Histogram | Time from created_at to published_at |

Alert thresholds:
- `outbox_age_oldest_seconds > 300` (5 min) → warning
- `outbox_age_oldest_seconds > 900` (15 min) → critical
- `outbox_events_pending > 10000` → warning
- `outbox_events_dead_letter_total > 0` → immediate investigation

`correlation_id` propagates from the originating API request through
the outbox → NATS → consumer chain.  All relay logs include
`correlation_id` for tracing.

### 7. What Goes in the Outbox vs. Direct Publish

| Event | Outbox | Direct | Reason |
|-------|:------:|:------:|--------|
| `campaign.created` | ✓ | | Business state — must be transactional |
| `campaign.published` | ✓ | | Side effect of approval workflow |
| `manifest.generate.request` | ✓ | | Triggered from Control API write |
| `audit.event` | ✓ | | Audit integrity depends on transaction |
| `advertiser.org.created` | ✓ | | Domain event from org registration |
| `device.heartbeat` | | ✓ | Telemetry, fire-and-forget, no business state |
| `device.error` | | ✓ | Diagnostic, no transactional dependency |
| `emergency.execute` | ✓ | | Business state — must be durable |

**Rule of thumb:** if the event carries business state that consumers
depend on for correctness, it goes through the outbox.  If it's
telemetry/observability that can be lost without data corruption,
direct publish is acceptable.

### 8. Testing Requirements (Before Accepting Any Producer)

Every service that writes to `outbox_events` MUST pass behavioral tests:

| Test | What it proves |
|------|---------------|
| **Rollback does not produce event** | `BEGIN; INSERT campaign; INSERT outbox; ROLLBACK;` — relay sees zero events |
| **Commit produces exactly one event** | `BEGIN; INSERT campaign; INSERT outbox; COMMIT;` — relay publishes exactly one with correct payload |
| **Relay retry after transient NATS failure** | NATS down → event stays `pending` → NATS recovers → event published |
| **Idempotent re-delivery** | Relay crashes after NATS ack but before UPDATE → re-publishes → consumer deduplicates by `event_id` |
| **Dead-letter after max attempts** | NATS permanently down → event retries 7× → status `dead_letter` |

**No event-producing endpoint is accepted without these behavioral
proofs.**  This extends ADR-008's testing gates to the outbox relay.

### 9. Non-Goals / Deferred

- **Debezium/CDC:** change-data-capture from PostgreSQL WAL is a
  potential future optimization but not Phase 4.  Polling is simpler,
  portable, and sufficient for the projected event volume.
- **Multi-worker sharding:** single relay worker is adequate for
  initial load.  Shard by `partition_key` when throughput demands it.
- **Schema registry:** event versioning via `event_version` field in
  the outbox row is sufficient.  No Avro/Protobuf registry yet.
- **Dead-letter UI:** manual replay of dead-letter events via admin
  API is deferred.  For now, dead-letter = alert → manual SQL replay.
- **Outbox for analytics events:** PoP batch ingest (`pop.ingest.batch`)
  arrives via Device Gateway → NATS directly (device-facing, no OLTP
  transaction).  These events are NOT produced from OLTP writes and
  do not require the outbox.

## Consequences

- **Positive:** Eliminates the dual-write problem for every
  event-producing endpoint.  At-least-once delivery with idempotent
  consumers is proven.  Observability gives operators visibility into
  event pipeline health.  Test requirements catch outbox bugs before
  they reach production.

- **Negative:** Adds ~1ms latency per event (INSERT into outbox_events).
  Relay polling adds up to 500ms delivery delay (acceptable for async
  events).  Single relay worker is a SPOF — if it crashes, events
  accumulate until restart (no data loss, just delay).

- **Risk:** `outbox_events` table grows unboundedly without cleanup.
  Mitigation: retention policy — DELETE rows with `status='published'`
  AND `published_at < NOW() - INTERVAL '7 days'`.  Dead-letter rows
  are retained until manually replayed or discarded.

## References

- ADR-002 — Event bus (NATS JetStream)
- ADR-007 — Data and analytics boundary (ClickHouse deferred)
- ADR-008 — Testing strategy (behavioral test gates)
- `docs/architecture/events/event-contracts-v1.md` — Event envelope
- Chris Richardson, "Microservices Patterns" — Transactional Outbox pattern
- PostgreSQL docs: `LISTEN`/`NOTIFY` (alternative to polling, deferred)
