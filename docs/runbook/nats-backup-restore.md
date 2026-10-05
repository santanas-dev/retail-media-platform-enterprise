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
| Consumer delivery state | NATS volume `nats_jetstream` | ⚠️ Survives container recreate; lost with the volume or when the durable is recreated (then redelivery from the start of the stream) |

**JetStream store directory (RM-STAB-021).** In pilot and phase1 compose NATS
runs with `-js -sd /data`, and `/data` is the named volume `nats_jetstream`:
streams, their messages and the durable's position survive a container
recreate. Before RM-STAB-021 the command had no `-sd`, nats-server stored in
`/tmp/nats/jetstream` inside the container, and the mounted volume stayed
empty — every recreate of the NATS container was Scenario B below. The first
start after the upgrade begins with an empty volume (nothing is migrated from
the old container's `/tmp`). Events the relay already published (outbox
`published`) but the consumer has not acked are lost with the old container
and are not re-sent by the relay — before applying the upgrade:
1. Stop `control-api` — besides the worker, the only service writing outbox
   events (campaign, emergency, creative, PoP routes):
   `docker compose stop control-api`.
2. Keep `orchestrator-worker` running: its relay publishes the remaining
   `pending` outbox rows and its consumer reads them.
3. Wait until the durable `rmp-campaign-consumer` reports `num_pending=0` and
   `num_ack_pending=0` (NATS monitoring `:8222/jsz?consumers=true` from inside
   the compose network).
4. Apply the upgrade (NATS is recreated with `-sd /data`). Events the worker
   itself publishes to `RMP_EVENTS` (`delivery.*`) have no reader and are not
   drained; that buffer starts empty.

The durable's position survives only while provisioning finds it unchanged:
`_ensure_consumer` deletes and recreates the durable when `add_consumer`
fails (config change or any other error), and a recreated durable starts
from the beginning of the stream (redelivery; handlers must stay idempotent).

**Backing up the volume is optional.** It is not part of the unified backup
(`backup_manifest.py`: `excluded_replayable`); the system is designed to
recover from **empty NATS storage** via provisioning + outbox replay.

## 3. Dedup Safety

Every outbox event published to NATS carries `Nats-Msg-Id = event_id`
(UUID, ADR-011 §3). JetStream deduplication prevents the same event from
being delivered twice within the dedup window. This means:

- **Re-running the outbox relay is safe** — already-published events are
  skipped (status = `published`, not `pending`)
- **Republishing from a PostgreSQL restore** — dedup protects only within the
  stream's duplicate window (server default 2 minutes; provisioning does not
  set it). With the JetStream store on a persistent volume (RM-STAB-021) a
  restore to an earlier point must start NATS empty — see Scenario D
  step 2; otherwise safety rests on handler idempotency alone
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
1. Start NATS with JetStream on the volume: `nats-server -js -sd /data`
   (compose: `docker compose up -d nats`)
2. Volume intact → streams, messages and the durable are already there.
   Volume empty → the worker provisions at startup (`NATS_AUTO_PROVISION=true`);
   without provisioned streams it does not start (RM-STAB-021)
3. Stream + consumer exist
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
2. Start NATS with JetStream **on an empty store**. Since RM-STAB-021 the store
   (`-sd /data`, volume `nats_jetstream`) survives `compose down`/`up` without
   `-v` and container recreates. When PostgreSQL is restored to an earlier
   point on the same host, remove the volume before starting NATS
   (`docker compose stop nats orchestrator-worker && docker compose rm -f nats
   && docker volume rm <project>_nats_jetstream`): otherwise the stream still
   holds messages published after the backup point, and the durable delivers
   them on top of the older database state
3. Run provisioning (the worker does it at startup)
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
startup (configured via `NATS_AUTO_PROVISION=true` in compose). The worker runs
it whenever `NATS_URL` is set and exits before starting the relay if it fails
(RM-STAB-021; `docs/runbook/delivery-runtime.md` → Provisioning). It:

1. Creates stream "RMP" with subjects `campaign.>` if not exists
2. Creates durable consumer "rmp-campaign-consumer" if not exists
3. Updates them if config changed

The worker additionally provisions `RMP_EVENTS` (`delivery.>`, `pop.>`,
`emergency.>`, `creative_asset.>`; 1 GiB / 7 days) via
`provision_outbox_event_stream()` — RM-STAB-020; see
`docs/runbook/delivery-runtime.md` → Provisioning.

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
