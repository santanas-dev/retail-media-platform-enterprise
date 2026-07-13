# NATS JetStream Backup / Restore Policy — Retail Media Platform Enterprise

| **Created:** 2026-07-13 |
| **S-050** — NATS backup policy and recovery proof |
| **Status:** documented |

## 1. Role of NATS in the Platform

NATS JetStream is the **delivery event transport** between the outbox relay
and campaign event consumer:

```
PostgreSQL outbox (source of truth)
    → OutboxRelay
    → NatsJetStreamPublisher (Nats-Msg-Id = event_id)
    → NATS JetStream stream "RMP", subject "campaign.>"
    → NatsJetStreamCampaignConsumer (durable "rmp-campaign-consumer")
    → manifest generation → delivery_manifests
```

NATS **does not** hold business state. Every event exists in the PostgreSQL
outbox table first. NATS is a transient delivery mechanism with JetStream
providing at-least-once delivery semantics.

## 2. Source of Truth Decision

**Policy: PostgreSQL outbox is the single source of truth.**

| State | Stored in | Recoverable from |
|-------|-----------|-----------------|
| Event payload | PostgreSQL `outbox_events` | ✅ PostgreSQL backup |
| Event status (pending/published/failed/dead_letter) | PostgreSQL `outbox_events` | ✅ PostgreSQL backup |
| Delivery manifests | PostgreSQL `delivery_manifests` | ✅ PostgreSQL backup |
| JetStream message storage | NATS `/data` volume | ⚠️ Recreatable via outbox replay |
| Consumer delivery state | NATS in-memory/volume | ⚠️ Ephemeral — consumer restarts from first pending |

**NATS JetStream persistent volume is optional.** The named volume
`nats_jetstream` in docker-compose provides faster recovery (no need to
replay all pending events), but the system is designed to recover from
**empty NATS storage** via provisioning + outbox replay.

## 3. Dedup Safety

Every outbox event published to NATS carries `Nats-Msg-Id = event_id`
(UUID, ADR-011 §3). JetStream deduplication prevents the same event from
being delivered twice within the dedup window. This means:

- **Re-running the outbox relay is safe** — already-published events are
  skipped (status = `published`, not `pending`)
- **Republishing from a PostgreSQL restore is safe** — JetStream will not
  redeliver events already processed
- **Consumer restart is safe** — unacked messages are redelivered with the
  same Msg-Id, and the handler is idempotent

## 4. What to Back Up

| Component | Required? | Method |
|-----------|-----------|--------|
| PostgreSQL (outbox + manifests) | **Mandatory** | `pg_dump` (S-031) |
| NATS JetStream volume | Optional | Named volume in compose (`nats_jetstream:/data`) |
| NATS stream config | Recreatable | `provision_campaign_delivery()` at startup |

**Recommendation for production:** back up the JetStream volume for faster
recovery (no outbox replay needed). But the mandatory minimum is PostgreSQL.

## 5. Failure Scenarios and Recovery

### Scenario A: NATS container lost, DB intact

**Impact:** Relay cannot publish. Consumer stops. No data loss.

**Recovery:**
1. Start NATS with JetStream: `nats-server -js`
2. Run provisioning: `provision_campaign_delivery()`
3. Stream + consumer are recreated
4. Outbox relay resumes — publishes pending events
5. Consumer processes and generates manifests

**RTO:** < 2 minutes (container start + provisioning)

### Scenario B: NATS stream corrupted / JetStream volume lost

**Impact:** In-flight messages lost. Published events may be missing from stream.

**Recovery:**
1. Stop consumer
2. Delete corrupted stream volume
3. Start NATS — empty JetStream
4. Run provisioning — creates fresh stream + consumer
5. Run recovery diagnostics: `scripts/check/nats_recovery_check.py`
6. Start relay — republishes all pending events
7. Start consumer — processes and generates manifests

**RTO:** < 5 minutes (excluding outbox replay time, which depends on pending count)

### Scenario C: Consumer durable lost

**Impact:** Consumer starts from scratch — may re-process messages still in stream.

**Recovery:**
1. Run provisioning — recreates consumer
2. Consumer resumes from first unprocessed message
3. Dedup via Nats-Msg-Id protects against duplicate side effects

**RTO:** < 1 minute

### Scenario D: Full disaster — DB restored, NATS empty

**Impact:** Complete loss of all runtime state.

**Recovery order:**
1. Restore PostgreSQL from backup
2. Start NATS with JetStream
3. Run provisioning
4. Start control-api + orchestrator-worker (they handle relay + consumer startup)
5. Verify: `scripts/check/nats_recovery_check.py`
6. Monitor relay published counters (Prometheus: `outbox_published_total`)

**RTO:** < 30 minutes (depends on DB restore time)

## 6. Recovery Diagnostics

Run the recovery check script:

```bash
DATABASE_URL=postgresql://***:***@host:5432/retail_media_platform \
NATS_URL=nats://localhost:4222 \
python scripts/check/nats_recovery_check.py
```

Options:
- `--detailed` — show recent pending/dead_letter events
- `--json` — machine-readable output

**What it checks:**
- NATS reachable
- Stream + consumer exist
- Outbox event counts by status (pending/published/failed/dead_letter)
- Recovery recommendation

## 7. Provisioning Proof

`provision_campaign_delivery()` is idempotent and safe to run at every
startup (configured via `NATS_AUTO_PROVISION=true` in compose). It:

1. Creates stream "RMP" with subjects `campaign.>` if not exists
2. Creates durable consumer "rmp-campaign-consumer" if not exists
3. Updates them if config changed

Integration test `test_nats_recovery.py` proves:
- Fresh NATS provisioning creates stream + consumer
- Outbox relay publishes to fresh stream after NATS reset
- Consumer processes events and generates manifests
- Dedup-safe replay (running relay twice produces 0 duplicates)

## 8. RPO / RTO

| Метрика | Pilot Target |
|---------|-------------|
| **RPO** | 0 (no event loss — outbox in PostgreSQL) |
| **RTO** | < 5 minutes (NATS restart + provisioning + relay resume) |

RTO assumes NATS container restart. If outbox replay is needed (scenario B),
RTO scales with pending event count — typically < 5 minutes for pilot volumes.

## 9. Known Limitations

| Элемент | Статус |
|---------|--------|
| JetStream volume backup automation | Deferred — manual `rsync` or compose volume snapshot |
| Multi-node NATS cluster | Deferred — single node only |
| Consumer scaling (multiple instances) | Deferred — single consumer |
| RTO for large outbox replay | Deferred — acceptable for pilot volumes |
| NATS monitoring / alerting | Deferred — integration with Prometheus AlertManager |

## 10. References

- Скрипт: `scripts/check/nats_recovery_check.py`
- Интеграционный тест: `tests/integration/test_nats_recovery.py`
- E2E тест: `tests/integration/test_nats_e2e.py`
- PostgreSQL backup: `docs/runbook/backup-restore-dr.md`
- Стабилизационный трекер: `docs/architecture/stabilization-tracker.md`
