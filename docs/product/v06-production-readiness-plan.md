# v0.6 Production Readiness Plan — Retail Media Platform Enterprise

| **Created:** 2026-07-13 |
| **Status:** planned |
| **Predecessor:** v0.5 Business Portal Complete (published) |
| **Successor:** v0.7 Emergency + Feature Flags |

## Purpose

v0.6 closes the production readiness gaps identified as blocking after
v0.5 Business Portal Complete (S-045 audit reconciliation).  This
milestone does NOT include player, hardware, billing, or v2.6 tenant
model work.

## Scope

### 1. Monitoring / Observability (S-047)
- Prometheus metrics endpoint on control-api + device-gateway
- Core metrics: API latency, error rate, DB pool utilisation, NATS queue depth
- Grafana dashboard (4 panels minimum: API, DB, NATS, outbox relay)
- Health/readiness/liveness endpoint parity across all services
- AlertManager rules: API error rate > 5%, dead-letter count > 0

### 2. Real LDAPS Wiring (S-048)
- Replace AD stub with real LDAPS bind/search adapter
- Configure via `AD_LDAP_URL`, `AD_BIND_DN`, `AD_SEARCH_BASE` env vars
- Fail-safe: fallback to `local_break_glass` when LDAPS unavailable
- Connection test endpoint existing (S-034) — wire to real LDAPS
- No plaintext credentials in logs/config responses

### 3. MinIO Backup / Mirror (S-049) — ✅ DONE
- Python SDK full-bucket backup with manifest + SHA-256 (`scripts/backup/minio_backup.py`)
- Restore script with check/dry-run/confirm modes + post-restore verification (`scripts/restore/minio_restore.py`)
- Integration test: backup → restore → verify (4 test cases)
- Runbook: `docs/runbook/minio-backup-restore.md`
- `docs/runbook/backup-restore-dr.md` updated with MinIO section and full recovery order

### 4. NATS Backup / Restore Policy (S-050) — ✅ DONE
- Policy decision: PostgreSQL outbox is source of truth
- Recovery: provisioning + relay replay (dedup-safe via Nats-Msg-Id = event_id)
- Recovery diagnostics: `scripts/check/nats_recovery_check.py`
- Integration test: `tests/integration/test_nats_recovery.py` (4 scenarios)
- Runbook: `docs/runbook/nats-backup-restore.md`
- Compose: named `nats_jetstream` volume for faster recovery
- `docs/runbook/backup-restore-dr.md` updated with 4-step recovery order
- Decision: whether to automate NATS backup or rely on outbox replay

### 5. Portal Error Boundaries (S-051) — ✅ DONE
- `ErrorBoundary` class component in both admin-web and advertiser-web
- Top-level wrap around AuthProvider + RouterProvider
- Route `errorElement` for per-route isolation + auto-reset on navigation
- Russian fallback: "Что-то пошло не так" + "Обновить страницу"
- Dev mode: safe error message (JWT/credential patterns redacted)
- Tests: 7 per portal — fallback renders, no secrets, resetKey, custom fallback

### 6. Audit Events for Approval / Moderation (S-052)
- `create_audit_event` in campaign approve/reject endpoints
- `create_audit_event` in creative approve/reject endpoints
- Operational audit table (`audit_events_operational`) writers
- Behavioural: audit event exists after approval/moderation action

### 7. identity.py Router Decomposition (S-053)
- Plan: split `packages/api/identity.py` (2036 lines) into domain routers
- Categories: users, campaigns, creatives, inventory, advertisers, PoP
- Each router self-contained with own RBAC/RLS dependencies
- Backward-compatible URL paths preserved
- Implementation decision: do we split in v0.6 or plan for v0.7?

### 8. XLSX Export Decision (S-054a)
- Evaluate openpyxl dependency vs Python built-in XML approach
- If openpyxl: add to requirements, update CI, implement XLSX endpoint
- If deferred again: update roadmap + tracker with explicit rationale
- Decision document in `docs/architecture/adr/` or plan section

### 9. creative_upload_sessions Behavioural RLS Test (S-054)
- Full behavioural test under `retail_media_app` (NOBYPASSRLS) role
- Prove: advertiser A cannot access advertiser B's upload sessions
- Prove: admin bypass works correctly
- Currently: migration structure test only (S-035h)

## Explicitly Out of Scope

- KSO player / sidecar / hardware → v0.9
- Emergency Management backend → v0.7
- Feature flags / staged rollout → v0.7
- Inventory Planning / Forecasting → v0.8
- Report snapshots → v0.8
- ClickHouse / reporting warehouse → v0.8
- Billing / acts / ERP → v2.6
- Tenant model ADR-018 → v2.6
- Device signature verification → v2.6
- Transcoding / renditions → v0.9
- Malware scan → v0.7

## S-Ticket Sequence

| Ticket | Area | Priority | Risk | Depends On |
|--------|------|----------|------|------------|
| S-047 | Monitoring / Observability | P0 | Medium | — |
| S-048 | Real LDAPS | P0 | High | — |
| S-049 | MinIO Backup | P0 | Low | ✅ done |
| S-050 | NATS Backup Policy | P1 | Low | ✅ done |
| S-051 | Portal Error Boundaries | P2 | Low | ✅ done |
| S-052 | Audit Events (Approval/Moderation) | P2 | Low | — |
| S-053 | identity Router Decomposition Plan | P2 | Low | — |
| S-054a | XLSX Export Decision | P2 | Low | — |
| S-054 | creative_upload_sessions Behavioural RLS | P1 | Medium | — |
| S-055 | v0.6 Readiness Review | P0 | — | S-047…S-054 |

### S-047 — Prometheus/Grafana Baseline
- **Goal:** Metrics endpoint on control-api + device-gateway, Grafana dashboard
- **Files:** `packages/observability/`, `apps/control-api/main.py`, `apps/device-gateway/main.py`, `infra/compose/`
- **Acceptance:** `/metrics` returns Prometheus format; Grafana dashboard shows 4 panels
- **Tests:** Metric emission unit tests, endpoint smoke test, dashboard JSON validated
- **Risk:** Medium — requires prometheus-client dependency, compose wiring

### S-048 — Real LDAPS Client
- **Goal:** Replace AD stub with real LDAPS bind/search
- **Files:** `packages/auth/ad_provider.py`, `packages/security/config.py`, `.env.example`
- **Acceptance:** Login via real AD credentials, honest error on connection failure, no secrets in logs
- **Tests:** Integration test with test LDAP server, negative: wrong password, unreachable server
- **Risk:** High — requires AD controller or test LDAP; configuration surface is complex

### S-049 — MinIO Backup/Mirror — ✅ DONE
- **Goal:** Python SDK full-bucket backup, restore drill with verification
- **Files:** `scripts/backup/minio_backup.py`, `scripts/restore/minio_restore.py`, `docs/runbook/minio-backup-restore.md`, `tests/integration/test_minio_backup_restore.py`
- **Acceptance:** Backup creates manifest with SHA-256, restore verifies post-upload, drill passes
- **Tests:** 4 integration tests (full cycle, empty bucket, confirmation gate, dry-run) — gated by `RUN_MINIO_INTEGRATION_TESTS=1`
- **Risk:** Low — MinIO SDK stable, no external CLI dependencies

### S-050 — NATS Backup Policy — ✅ DONE
- **Goal:** Document recovery strategy: outbox source of truth, provisioning replay
- **Policy:** NATS JetStream volume optional; PostgreSQL outbox mandatory
- **Files:** `docs/runbook/nats-backup-restore.md`, `scripts/check/nats_recovery_check.py`, `tests/integration/test_nats_recovery.py`, `infra/compose/docker-compose.phase1.yml`
- **Acceptance:** Policy documented, recovery proofed via integration test, diagnostics script works
- **Tests:** 4 integration tests (provisioning, replay after reset, dedup safety, check script) — gated by `RUN_NATS_INTEGRATION_TESTS=1`
- **Risk:** Low — outbox relay already publishes with Nats-Msg-Id dedup

### S-051 — Portal Error Boundaries — ✅ DONE
- **Goal:** React ErrorBoundary in both portals with Russian fallback
- **Files:** `apps/admin-web/src/components/ErrorBoundary.tsx`, `apps/advertiser-web/src/components/ErrorBoundary.tsx`, updated `main.tsx` in both
- **Acceptance:** Error fallback shows instead of white screen; secrets redacted in dev
- **Tests:** 7 vitest per portal — fallback renders, refresh button, resetKey, no secrets, custom fallback
- **Risk:** Low — standard React pattern, class component avoids hook issues

### S-052 — Audit Events for Approval/Moderation
- **Goal:** Write audit events on campaign approve/reject + creative approve/reject
- **Files:** `packages/api/identity.py`, `packages/domain/repository.py`, `tests/behavioral/`
- **Acceptance:** Audit event exists after each action, actor + target IDs correct, no secrets
- **Tests:** Behavioural: event row in `audit_events_operational` after action
- **Risk:** Low — existing `create_audit_event` infrastructure

### S-053 — identity Router Decomposition Plan
- **Goal:** Produce decomposition plan (ADR or design doc), decision on v0.6 vs v0.7
- **Files:** `docs/architecture/adr/` (new ADR), `packages/api/identity.py` (read-only)
- **Acceptance:** ADR created, module boundary map, decision documented
- **Tests:** Not applicable — planning only
- **Risk:** Low — read-only analysis

### S-054 — creative_upload_sessions Behavioural RLS
- **Goal:** Behavioural proof that RLS policies on `creative_upload_sessions` work under NOBYPASSRLS
- **Files:** `tests/behavioral/test_creative_upload.py`, migration 013
- **Acceptance:** Advertiser A cannot see B's sessions; admin can see all
- **Tests:** 2 behavioural tests minimum
- **Risk:** Medium — CI runs behavioural as superuser by default; needs NOBYPASSRLS role

### S-055 — v0.6 Readiness Review
- **Goal:** Full regression guard review before v0.6 publish
- **Files:** `docs/architecture/stabilization-tracker.md`
- **Acceptance:** All S-047…S-054 gates green, CI green, audit reconciliation
- **Tests:** Full CI suite
- **Risk:** Low — review only

## Milestone Map

```
v0.5 (PUBLISHED)          v0.6 (PLANNED)         v0.7              v0.8              v0.9
Business Portal ──────► Production Readiness ──► Emergency/Flags ─► Inventory/Report ─► KSO/Player
                                                       │
                                                   v2.6 (separate, after ADR-018)
```

## References

- S-045 audit reconciliation report
- `docs/product/production-gaps-triage.md`
- `docs/architecture/release-versioning.md`
- `docs/architecture/stabilization-tracker.md`
- `docs/product/roadmap-s020-2026-07-10.xlsx`
