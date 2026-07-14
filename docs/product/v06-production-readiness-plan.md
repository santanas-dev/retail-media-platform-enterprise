# v0.6 Production Readiness Plan — Retail Media Platform Enterprise

| **Created:** 2026-07-13 |
| **Status:** ready for release prep (implemented on develop) |
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

### 6. Audit Events for Approval / Moderation (S-052) — ✅ DONE
- Campaign approve/reject: audit events `campaign.approved`, `campaign.rejected`
- Creative moderation approve/reject: audit events `creative.approved`, `creative.rejected`
- Same DB transaction as state change (before outbox enqueue)
- Details: old/new status, rejection_reason (truncated 200 chars), no secrets/storage fields
- Tests: 7 new — audit writes, no secrets, 403 skips audit
- Behavioural: audit event exists after approval/moderation action

### 7. identity.py Router Decomposition (S-053) ✅ DONE
- Split `packages/api/identity.py` (2097 lines) into 8 domain routers under `packages/api/identity_routes/`
- Categories: common (99), users (408), ad_settings (106), advertisers (147), campaigns (725), creatives (314), reporting (155), inventory (122)
- Identity.py now 40-line thin aggregator with backward-compatible `router` export
- All 66 identity API tests pass, import boundaries clean
- Preserved: API paths, auth/RBAC/RLS dependencies, schemas, business logic

### 8. XLSX Export Decision (S-054a) ✅ DONE
- **Decision:** v0.6 supports CSV export only (S-040, UTF-8 BOM for Excel). XLSX deferred to v0.7/v0.8.
- **Rationale:** CSV already works with Excel. XLSX adds runtime dependency (openpyxl/xlsxwriter) and attack surface. v0.6 scope = production readiness, not reporting feature expansion.
- **Revisit when:** Reporting warehouse / report snapshots are planned (v0.8).

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
| S-047 | Monitoring / Observability | P0 | Medium | ✅ done |
| S-048 | Real LDAPS | P0 | High | ✅ done |
| S-049 | MinIO Backup | P0 | Low | ✅ done |
| S-050 | NATS Backup Policy | P1 | Low | ✅ done |
| S-051 | Portal Error Boundaries | P2 | Low | ✅ done |
| S-052 | Audit Events (Approval/Moderation) | P2 | Low | ✅ done |
|| S-053 | identity Router Decomposition | P2 | Low | ✅ done |
|| S-054a | XLSX Export Decision | P2 | Low | ✅ done |
|| S-054 | creative_upload_sessions Behavioural RLS | P1 | Medium | ✅ done |
| S-055 | v0.6 Readiness Review | P0 | — | S-047…S-054 |

### S-047 — Prometheus/Grafana Baseline — ✅ DONE
- **Goal:** Metrics endpoint on control-api + device-gateway, Grafana dashboard
- **Files:** `packages/observability/`, `apps/control-api/main.py`, `apps/device-gateway/main.py`, `infra/compose/`
- **Acceptance:** `/metrics` returns Prometheus format; Grafana dashboard shows 4 panels
- **Tests:** Metric emission unit tests, endpoint smoke test, dashboard JSON validated
- **Risk:** Medium — requires prometheus-client dependency, compose wiring

### S-048 — Real LDAPS Client — ✅ DONE
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

### S-052 — Audit Events for Approval/Moderation — ✅ DONE
- **Goal:** Write audit_events_operational rows on campaign approve/reject + creative approve/reject
- **Files:** `packages/api/identity.py`, `tests/test_phase3_identity_api.py`
- **Acceptance:** 4 audit actions (campaign.approved/rejected, creative.approved/rejected) in same tx
- **Tests:** 7 new unit tests + all existing 59 pass (66 total)
- **Risk:** Low — existing create_audit_event infrastructure

### S-053 — identity Router Decomposition ✅ DONE
- **Goal:** Split 2097-line identity.py into bounded-context routers
- **Result:** 8 modules under `packages/api/identity_routes/`: common (99 ⤳), users (408 ⤳), ad_settings (106 ⤳), advertisers (147 ⤳), campaigns (725 ⤳), creatives (314 ⤳), reporting (155 ⤳), inventory (122 ⤳)
- **Identity.py:** 40-line aggregator with backward-compatible `router` export + `repository` re-export for test patches
- **Tests:** 66/66 identity API, 184/184 full backend regression, import boundaries clean. 3 test patches updated (`repository.XXX` target)
- **Risk:** Low — pure refactor, no API/business-logic change

### S-054 — creative_upload_sessions Behavioural RLS — ✅ DONE
- **Goal:** Behavioural proof that RLS policies on `creative_upload_sessions` work under NOBYPASSRLS
- **Result:** 5 behavioural RLS scenarios (own org visible, foreign org hidden, admin bypass, empty scope fail-closed, cross-org count consistency) — all pass in CI
- **Files:** `tests/behavioral/test_creative_upload_sessions_rls.py`, migration 013
- **Acceptance:** Advertiser A cannot see B's sessions; admin can see all
- **Tests:** 5 behavioural tests (NOBYPASSRLS role)

### S-055 — v0.6 Readiness Review — ✅ DONE
- **Goal:** Full regression guard review before v0.6 publish
- **Result:** CONDITIONAL GO — code/CI/security ready. 5 docs honesty issues found (fixed in S-055a)
- **Acceptance:** All S-047…S-054 gates green, CI green, audit reconciliation

## Milestone Map

```
v0.5 (PUBLISHED)     v0.6 (READY FOR RELEASE PREP)   v0.7              v0.8              v0.9
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
