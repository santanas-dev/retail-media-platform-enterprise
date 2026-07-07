# Delivery Runtime Runbook

How to operate the outbox → NATS → consumer → manifest generation pipeline.

## Quick-start

```bash
# Start infrastructure
docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres nats

# Apply migrations + seed
cd apps/control-api && alembic upgrade head && python seed.py

# Provision JetStream (only needed once, or set NATS_AUTO_PROVISION=true)
python -c "
import asyncio
from packages.services.jetstream_provisioning import provision_campaign_delivery
asyncio.run(provision_campaign_delivery('nats://localhost:4222'))
"

# Start orchestrator-worker
NATS_URL=nats://localhost:4222 \
DATABASE_URL=postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform \
CAMPAIGN_CONSUMER_ENABLED=true \
NATS_AUTO_PROVISION=true \
python apps/orchestrator-worker/main.py
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NATS_URL` | — | NATS server URL (required for relay + consumer) |
| `DATABASE_URL` | — | PostgreSQL async URL (required) |
| `CAMPAIGN_CONSUMER_ENABLED` | `false` | Enable campaign event consumer |
| `CAMPAIGN_CONSUMER_ALLOW_STUB` | `false` | Use StubConsumer even when NATS_URL is set (dev only) |
| `CAMPAIGN_CONSUMER_DURABLE` | `rmp-campaign-consumer` | JetStream durable consumer name |
| `CAMPAIGN_CONSUMER_SUBJECT` | `campaign.>` | NATS subject to subscribe |
| `CAMPAIGN_CONSUMER_STREAM` | `RMP` | JetStream stream name |
| `CAMPAIGN_CONSUMER_BATCH_SIZE` | `10` | Messages per fetch batch |
| `CAMPAIGN_CONSUMER_FETCH_TIMEOUT` | `5.0` | Fetch timeout in seconds |
| `NATS_AUTO_PROVISION` | `false` | Auto-create stream + consumer on startup |
| `OUTBOX_RELAY_ALLOW_STUB` | `false` | Use StubPublisher when NATS_URL is set (dev only) |
| `RELAY_POLL_INTERVAL` | `0.5` | Outbox poll interval in seconds |
| `RELAY_BATCH_SIZE` | `100` | Max events per poll batch |
| `NATS_TIMEOUT` | `5.0` | NATS publish timeout |
| `ORCHESTRATOR_PORT` | `8003` | Health HTTP server port |

## Provisioning

JetStream stream + consumer must exist before the worker starts (unless `NATS_AUTO_PROVISION=true`).

### Manual provisioning

```python
import asyncio
from packages.services.jetstream_provisioning import provision_campaign_delivery

asyncio.run(provision_campaign_delivery(
    nats_url="nats://localhost:4222",
    stream="RMP",
    subjects=["campaign.>"],
    durable="rmp-campaign-consumer",
))
```

The script is idempotent — safe to run multiple times. It creates the stream/consumer if missing, updates them if they exist.

### Auto-provisioning

Set `NATS_AUTO_PROVISION=true`. The worker provisions at startup before starting relay/consumer.

If auto-provision is off and the stream does not exist, the worker fails fast with:
```
RuntimeError: JetStream stream 'RMP' not found at nats://localhost:4222.
Run provisioning first: set NATS_AUTO_PROVISION=true, or run
provision_campaign_delivery() from jetstream_provisioning.py.
```

## Health checks

```
# Liveness (always 200 if process is running)
curl http://localhost:8003/health/live
→ {"status": "ok", "service": "orchestrator-worker"}

# Readiness (full component status)
curl http://localhost:8003/health/ready
→ {
    "status": "ok" | "degraded",
    "checks": {
      "database": "ok" | "fail",
      "nats": "ok" | "fail",
      "publisher": "ready" | "not_ready",
      "consumer": "ready" | "not_ready"
    },
    "components": {
      "relay": {"running": true, "published": 42, "failed": 0, ...},
      "consumer": {"running": true, "acked": 10, "nakd": 0, ...,
                   "manifest": {"success": 8, "failed": 0, "skipped": 2}}
    }
  }
```

The worker also logs a health summary every 60 seconds:
```
Health summary: db=ok nats=ok publisher=ready consumer=ready
relay(pub=42 fail=0 dlq=0) consumer(ack=10 nak=0 term=0 err=0)
manifest(ok=8 fail=0 skip=2)
```

## Diagnostic checklist

### Relay not publishing events

1. Check `NATS_URL` is set and NATS is running: `curl http://localhost:8222/healthz`
2. Check `DATABASE_URL` is set and PostgreSQL is reachable
3. Look for "Outbox relay NOT started" or "Outbox relay started" in logs
4. If using Stub: `OUTBOX_RELAY_ALLOW_STUB=true` means no real publishing
5. Check `/health/ready` — relay.running should be `true`

### Consumer not receiving events

1. Check `CAMPAIGN_CONSUMER_ENABLED=true`
2. Verify JetStream stream exists: check NATS monitoring at `http://localhost:8222`
3. Check consumer is "started (JetStream pull)" vs "started (stub mode)" in logs
4. Check `/health/ready` — consumer.running should be `true`
5. If stuck as stub: check `CAMPAIGN_CONSUMER_ALLOW_STUB` setting

### Manifest generation not happening

1. Verify campaign is in `approved` status
2. Check campaign has placements, creatives, and flight dates
3. Look for "Manifest generation done" or "Manifest generation failed" in logs
4. Check `/health/ready` manifest counters: success > 0 means it's working
5. Check outbox_events table for pending delivery events:
   ```sql
   SELECT event_type, status, attempts, last_error
   FROM outbox_events
   WHERE event_type LIKE 'campaign.%' AND status = 'pending'
   ORDER BY created_at DESC LIMIT 10;
   ```

### NATS connection issues

```bash
# Check NATS is running with JetStream
curl http://localhost:8222/healthz
curl http://localhost:8222/jsz

# List streams
nats stream ls
# List consumers
nats consumer ls RMP
```

## DB readiness

The worker verifies actual PostgreSQL connectivity at startup with a `SELECT 1` query.
If the DB is unreachable, the worker fails-fast with:

```
RuntimeError: Database unreachable at postgresql+asyncpg://...: Connection refused.
Check DATABASE_URL and PostgreSQL availability.
```

DB status is reflected in `/health/ready` under `checks.database` (`"ok"` / `"fail"`).

## Dead-letter counter

The `dead_letter` counter in `/health/ready` increments each time an outbox event
exhausts all retry attempts and transitions to `dead_letter` status.  A nonzero
dead-letter count means events are permanently failing and require manual
investigation:

```sql
SELECT id, event_type, aggregate_id, attempts, last_error
FROM outbox_events
WHERE status = 'dead_letter'
ORDER BY created_at DESC LIMIT 10;
```

Dead-letter events will NOT be retried automatically.  They must be manually
replayed or discarded.

## Graceful shutdown

Send SIGTERM or SIGINT to the worker process for clean shutdown:

```bash
kill -TERM <pid>
# or Ctrl+C in the terminal
```

The shutdown sequence:
1. Sets health status to `shutting_down` → `/health/ready` returns 503
2. Stops the outbox relay polling loop
3. Stops the campaign event consumer fetch loop
4. Drains/disconnects NATS publisher and consumer
5. Logs "Shutdown complete"

In-flight publish/ack operations complete normally — no messages are lost.
Shutdown is idempotent — sending the signal again does not cause errors.

### Stuck shutdown

If the worker does not exit within ~10 seconds after SIGTERM, check:
1. NATS connection state — a hung NATS drain may block shutdown
2. DB connection pool — long-running queries may delay exit
3. Check logs for "Relay stopped", "Consumer stopped", "NATS publisher disconnected"

## Integration tests

```bash
# Start NATS + PostgreSQL
docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres nats

# Run opt-in integration tests
RUN_NATS_INTEGRATION_TESTS=1 \
NATS_URL=nats://localhost:4222 \
BEHAVIORAL_DB_URL=postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform \
python -m pytest tests/integration/test_nats_consumer.py -v
```
