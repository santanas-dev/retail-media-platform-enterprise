# Observability Runbook — Retail Media Platform

| **Created:** 2026-07-13 |
| **Version:** 1.0 |
| **Service:** S-047 — Prometheus / Grafana baseline |

## Quick Start

```bash
# Start base services + observability
docker compose -f infra/compose/docker-compose.phase1.yml \
               -f infra/compose/docker-compose.observability.yml \
               up -d
```

## Access

| Service | URL | Notes |
|---------|-----|-------|
| Prometheus | http://localhost:9090 | Scrapes /metrics every 15s |
| Grafana | http://localhost:3002 | admin / admin (dev only) |
| control-api /metrics | http://localhost:8000/metrics | No auth required |
| device-gateway /metrics | http://localhost:8001/metrics | No auth required |

## Dashboards

### RMP Overview

- **Service Readiness:** up/down status, uptime, DB health, NATS health
- **HTTP Traffic:** request rate, 5xx error rate per service
- **Outbox & NATS:** outbox published/failed/dead-letter, NATS consumer processed/failed
- **Manifest & PoP:** manifest generation success/failure, PoP events accepted/quarantined

Dashboards provisioned from `infra/observability/grafana/dashboards/rmp-overview.json`.

## Alerts

Alert rules defined in `infra/observability/alerts.yml`:

| Alert | Severity | Condition |
|-------|----------|-----------|
| ServiceDown | critical | `up == 0` for 1m |
| High5xxRate | warning | `rate(rmp_http_5xx_total[5m]) > 0.1` |
| DBUnhealthy | critical | `rmp_db_ready == 0` for 2m |
| NATSUnhealthy | critical | `rmp_nats_ready == 0` for 2m |
| OutboxDeadLettersDetected | warning | `increase(rmp_outbox_dead_letter_total[15m]) > 0` |
| ManifestGenerationFailures | warning | `increase(rmp_manifest_generation_failed_total[15m]) > 2` |
| PopQuarantineSpike | warning | `increase(rmp_pop_events_quarantined_total[15m]) > 50` |
| NATSConsumerFailures | warning | `increase(rmp_nats_consumer_failed_total[15m]) > 5` |

AlertManager is not provisioned in this baseline — rules file exists for
future wiring.  Alerts can be viewed in Prometheus UI at
http://localhost:9090/alerts.

## Metrics Reference

### Common (all services)

| Metric | Type | Description |
|--------|------|-------------|
| `rmp_service_info` | gauge | Service name label: `service=<name>` |
| `rmp_service_uptime_seconds` | gauge | Seconds since process start |
| `rmp_http_requests_total` | counter | Total HTTP requests served |
| `rmp_http_5xx_total` | counter | HTTP 5xx responses |

### Domain (orchestrator-worker via control-api if HealthState wired)

| Metric | Type | Description |
|--------|------|-------------|
| `rmp_outbox_published_total` | counter | Events published to NATS |
| `rmp_outbox_failed_total` | counter | Publish failures |
| `rmp_outbox_dead_letter_total` | counter | Dead-letter events |
| `rmp_nats_consumer_processed_total` | counter | Consumer acked events |
| `rmp_nats_consumer_failed_total` | counter | Consumer nakd + terminated |
| `rmp_nats_consumer_errors_total` | counter | Consumer error count |
| `rmp_manifest_generated_total` | counter | Manifests generated |
| `rmp_manifest_generation_failed_total` | counter | Generation failures |
| `rmp_manifest_skipped_total` | counter | Manifests skipped (no-op) |
| `rmp_pop_batches_total` | counter | PoP batches ingested |
| `rmp_pop_events_accepted_total` | counter | PoP events accepted (billing-grade) |
| `rmp_pop_events_quarantined_total` | counter | PoP events quarantined |
| `rmp_creative_upload_completed_total` | counter | Upload completions |
| `rmp_auth_login_failed_total` | counter | Failed logins |
| `rmp_db_ready` | gauge | 1=ok, 0=fail |
| `rmp_nats_ready` | gauge | 1=ok, 0=fail |

## Known Limitations

- **orchestrator-worker** uses `http.server` (no FastAPI).  Domain counters
  (outbox, consumer, manifest) are only surfaced when `sync_from_health_state()`
  is called from the metrics endpoint.  Currently these metrics are visible
  only on **control-api** `/metrics` (which imports `health_state`).
  orchestrator-worker `/metrics` shows zero values for domain counters until
  it exposes its own endpoint.

- **pop-ingestor** uses `http.server` (no FastAPI).  No `/metrics` endpoint
  yet — PoP counters will show zero until wired.

- **adapter-workers/mock** uses `http.server`.  Same limitation.

- AlertManager not provisioned — alerts are viewable in Prometheus UI only.

- Grafana admin password is `admin` in dev — **change before production**.

- No auth on `/metrics` endpoint — acceptable for baseline; add auth for
  production if metrics contain sensitive label values.

## Verify

```bash
# Check metrics endpoint
curl -s http://localhost:8000/metrics | head -20

# Expected output: Prometheus text format with HELP/TYPE lines
# # HELP rmp_service_info Service metadata
# # TYPE rmp_service_info gauge
# rmp_service_info{service="control-api"} 1
# ...

# Check Grafana is up
curl -s -o /dev/null -w '%{http_code}' http://localhost:3002
# Expected: 200

# Check Prometheus targets
curl -s http://localhost:9090/api/v1/targets | python3 -m json.tool | grep -A5 '"job"'
# Expected: control-api and device-gateway are "UP"
```
