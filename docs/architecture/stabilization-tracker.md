# Stabilization Tracker — Retail Media Platform Enterprise

| **Last updated:** 2026-07-09
| **Current phase:** Backend pilot delivery chain proven (B1/B2/B3). 4.3d component-complete; 4.3e deferred.

## Pilot Backend Readiness (2026-07-09)

**Backend pilot delivery chain proven through device manifest fetch** (9 July 2026 evidence).

Separately covered:
- **Campaign setup/approval APIs** — behavioral tests (42 campaign mutations + 24 approval)
- **Delivery pipeline** — B2 NATS E2E + B3 pilot E2E (opt-in, real NATS + real PostgreSQL)
- **Device manifest fetch** — device-gateway HTTP with device JWT, ETag/304, security audit

**Proven chain:** outbox enqueue → NATS relay → JetStream consumer → manifest generation → device-gateway `/api/v1/device/manifest/latest` HTTP response (200 + correct shape, 304/401 security, no storage secrets).

**Not yet proven (out of scope for backend pilot):**
- Real KSO player/sidecar
- Frontend (advertiser/admin portal)
- Real creative upload/storage/presigned URLs
- Production manifest signing (HMAC placeholder)
- ClickHouse / materialized reporting
- Production deployment/observability hardening

**Evidence:**
| Deliverable | Commits | Tests |
|-------------|---------|-------|
| B1 — flight/placement/creative APIs | `0e3e10f`, `ba5a731`, `6df6f13`, `1f60924` | Campaign mutations behavioral: 42 pass |
| B1 — approval workflow | `fc09f4b`, `c405bdc`, `0fea6ac` | Approval behavioral: 24 pass |
| B2 — NATS delivery pipeline | `adde7d3`, `4462aac`, `ec12dfb` | NATS E2E: 1 pass (opt-in) |
| B3 — pilot E2E smoke | `5f6763c` | Pilot E2E: 1 pass (opt-in) |

---

| ID | Phase | Priority | Status | Owner | Evidence | Next Action |
|----|-------|----------|--------|-------|----------|-------------|
| S-001 | Import boundaries (ADR-014) | P1 | ✅ done | — | `check-import-boundaries.py` passes 44/44 | — |
| S-002 | Outbox foundation (ADR-011) | P1 | ✅ done | — | Migration 007, `OutboxEvent` model, `enqueue_outbox_event`, 10 unit + 9 behavioral tests | — |
| S-003 | Campaign read-only (Phase 4.1b) | P1 | ✅ done | — | 7 endpoints, 7 ORM models, migration 006, 41 unit + 30 behavioral tests | — |
| S-004 | Campaign mutations (Phase 4.1c) | P1 | ✅ done | — | 3 endpoints (create/update/archive), tenant isolation, cross-org validation, outbox integration, 12 unit + 10 behavioral tests | — |
| S-004b | Campaign flight/placement/creative APIs (Pilot B1) | P1 | ✅ done | — | POST/PATCH /campaigns/{id}/flights, POST/PATCH /campaigns/{id}/placements, POST /campaigns/{id}/creatives. Flight window validation + finite valid_until, creative scope fix, outbox per ADR-015. 42 behavioral tests. Commits: 0e3e10f + ba5a731 + 6df6f13 + 1f60924. | — |
| S-005 | Campaign approval workflow | P2 | ✅ done | — | 3 endpoints (request-approval/approve/reject), status transitions, approval records, outbox, requested_at semantics, contract validation, idempotency. Commits: fc09f4b + c405bdc + 0fea6ac. 18 unit + 24 behavioral tests | — |
| S-006a | Delivery architecture lock | P2 | 🔒 locked | — | ADR-016 accepted: delivery trigger, eligibility, target resolution, manifest schema, versioning, outbox events, observability, security, phase split (4.2b→4.2e), behavioral proof requirements | — |
| S-006b | Delivery DB/model foundation | P2 | ✅ done | — | Migration 008, 5 ORM models (DeliveryPlan/Manifest/Surface/Asset/Attempt), 7 repository helpers, 16 unit + 10 behavioral tests. Commits: 46cfe71 + 137ae0b | — |
| S-006c | Manifest generator worker skeleton | P2 | ✅ done | — | packages/domain/delivery.py (776 lines): eligibility, target resolution, compute_manifest_id + compute_campaign_version_hash, manifest JSON gen, delivery_plan/manifest persistence, delivery.manifest.generated/failed outbox, plan idempotency. 25 unit + 12 behavioral tests. Commits: e467543 + e05b960 + 0154681. | — |
| S-006d | Device gateway manifest endpoint | P2 | ✅ done | — | apps/device-gateway/main.py: GET /api/v1/device/manifest/latest with device JWT auth, device status check, ETag/If-None-Match, response shape alignment with generate_manifest_json()/manifest_v1.schema.json, no direct SQL in router, store-orphan detection. 10 unit + 7 behavioral tests. Commits: c34d5fa + c8a369e + 08b099e. | — |
| S-006e | Runtime simulator safety proofs | P2 | ✅ done | — | packages/runtime/simulator.py (505 lines): ADR-013 safety simulator — manifest apply (validate/secrets/device_id/version/signature → atomic swap + lkg), kill-switch (4 levels, fail-closed), render slot (6 safety gates), PoP integrity (only after render, dedup, required fields), offline TTL (monotonic, fallback after expiry). 41 unit tests. Commits: 52a50fc + fix. | — |
| S-006f | NATS delivery pipeline (Pilot B2) | P1 | ✅ done | — | docker-compose.phase1.yml orchestrator-worker env wiring. jetstream_provisioning.py: idempotent stream+consumer, delete_consumer param fix. E2E integration test (test_nats_e2e.py): outbox→relay→NATS→consumer→manifest→DB row. Opt-in (RUN_NATS_INTEGRATION_TESTS=1). Commits: adde7d3 + 4462aac + ec12dfb. 82 consumer+delivery unit + 6 provisioning unit + 1 NATS E2E pass. | — |
| S-006g | Pilot E2E smoke (Pilot B3) | P1 | ✅ done | — | tests/integration/test_pilot_e2e.py: campaign state→outbox→relay→NATS→consumer→manifest→device-gateway HTTP fetch. Asserts 200+ETag+304, 401 no-token+wrong-provider, 17 manifest fields, no storage_bucket/storage_key/presigned_url. Opt-in (RUN_NATS_INTEGRATION_TESTS=1). Commit: 5f6763c. 1 pilot E2E pass. | — |
| S-007c | PoP ingestion endpoint | P3 | ✅ done | — | POST /api/v1/pop/batch on control-api, device JWT, 11-step validation (schema/device/dedup/duration/playback/stale/clock_drift/manifest/cross-entity), quarantine 72h, accepted = billing-grade, outbox (pop.event.accepted/quarantined + pop.batch.ingested), dedup flush fix (59060ad), fixture hardening (d1d7bb5), cleanup time fence (d97be76). 29 unit + 27 behavioral tests. Commits: d1c6e8c + d1d7bb5 + 59060ad + d97be76. | Implement 4.3d reporting endpoints |
| S-007d | PoP reporting / read models | P3 | ✅ done | — | GET /api/v1/identity/campaigns/{id}/pop/{summary,by-day,by-surface} with JWT + require_scoped_permission("campaigns.read","advertiser") + set_rls_context. 3 repository helpers filtering status='accepted' AND campaign_verified=true AND playback_result='success'. Campaign ownership guard (_require_campaign_visible) — scoped advertiser foreign campaign → 404, admin bypass. CampaignPopSummaryOut/ByDay/BySurface schemas, no PII/secrets. 13 unit + 23 behavioral (8 reporting + 15 scope). P1 fix: 1f3e98d. Commits: 518475c + 1f3e98d. | Implement 4.3e materialized views |
| S-007e | Behavioral PostgreSQL CI gate | P1 | ✅ done | — | .github/workflows/phase1-ci.yml — behavioral-postgres-tests job: PostgreSQL 16 service, two-role setup (owner for migrations, retail_media_app NOBYPASSRLS for runtime), migrations + seed + explicit GRANT, zero-tests-passed guard, blocks merge on failure. Local runner: scripts/ci/behavioral-postgres-checks.sh with superuser/BYPASSRLS warning + zero-test guard. RLS-proof runtime role verified in CI. | — |
| S-010 | Auth login rate limiting (ADR-006 §8) | P1 | ✅ done | — | count_recent_failed_attempts in repository, guard in AuthService.login() before user lookup, 429 on exceeding 5 attempts/15min window, rate-limited attempts recorded in login_attempts for audit, no user enumeration in 429 response. Config: login_rate_limit_max_attempts=5, login_rate_limit_window_minutes=15. 5 unit + 4 behavioral tests. | — |
| S-011 | CORS baseline | P1 | ✅ done | — | SecurityConfig: cors_allowed_origins, cors_allow_credentials, cors_allowed_methods, cors_allowed_headers. Dev defaults: localhost:5173. Production: requires explicit CORS_ALLOWED_ORIGINS, rejects ["*"] + allow_credentials=True. CORSMiddleware on control-api only. 10 tests (4 header + 6 config validation). | — |
| S-012 | Outbox relay + orchestration runtime wiring | P1 | ✅ done | — | OutboxRelay poller with fetch_pending_events (time-fence next_attempt_at <= NOW()), exponential backoff, dead-letter. Real JetStream publisher: NatsJetStreamPublisher with Nats-Msg-Id dedup, fail-fast on missing NATS, Stub fallback only via OUTBOX_RELAY_ALLOW_STUB=true. Campaign event handler: 7 ADR-016 delivery triggers → generate_manifests_for_campaign, safe no-op on unknown/missing campaign_id. Real JetStream consumer: NatsJetStreamCampaignConsumer — pull-based, durable, campaign.> wildcard, ack after commit, nak with delay on failure, term on malformed (poison pill). Worker integration: relay + consumer run as independent asyncio.create_task(), health endpoint always available. E2E NATS test (test_nats_e2e.py, opt-in, RUN_NATS_INTEGRATION_TESTS=1): proves outbox→relay→NATS→consumer→manifest generated→DB row. Pilot E2E smoke (test_pilot_e2e.py, opt-in): extends B2 path through device-gateway HTTP fetch with device JWT, ETag/304, 401, manifest shape + secrets audit. 88 unit + 20 behavioral + 2 integration (opt-in) tests. | Production: NATS stream/consumer provisioning, deployment config, observability (metrics, alerts) |
| S-013 | Production readiness — provisioning + observability | P1 | ✅ done | — | NATS provisioning: packages/services/jetstream_provisioning.py — idempotent stream/consumer create/update, check_stream_exists(), safe to re-run. Startup checks: _run_provisioning() — NATS_AUTO_PROVISION=true auto-provisions, otherwise fail-fast with clear message if stream missing. Health/readiness: GET /health/ready returns DB+NATS+publisher+consumer status + relay/consumer/manifest counters. GET /health/live returns liveness probe. Thread-safe HealthState singleton with locking. Observability: relay published/failed counters, consumer acked/nakd/terminated/errors counters, manifest success/failed/skipped counters, periodic summary logger (60s). Runbook: docs/runbook/delivery-runtime.md — quick-start, env vars, provisioning, health checks, diagnostic checklist. 35 unit tests. | Prometheus metrics, alert rules |
| S-014 | Pilot reliability hardening | P1 | ✅ done | — | Real DB readiness: check_db_health() connectivity check at startup replaces unconditional set_db_ok(True). Fail-fast with safe message (no DATABASE_URL in errors). Dead-letter counter: mark_event_failed returns bool; relay bumps bump_relay_dead_letter() on True. Behavioral tests for transient/max-attempt/not-found. Graceful shutdown: SIGTERM/SIGINT handlers → stop relay loop (OutboxRelay.stop()), stop consumer loop, drain/disconnect NATS publisher + consumer, log shutdown steps. Health state → shutting_down status → /health/ready returns 503. Shutdown idempotent (safe to call twice). Consumer DB check: _start_consumer() also verifies DB via check_db_health(). 86 unit tests (relay 35 + readiness 51). Behavioral: 0 run (requires PostgreSQL). | Prometheus metrics/alerts (deferred) |
| S-008 | DB write RLS WITH CHECK | P0 | ✅ done | — | Migration 010: INSERT/UPDATE/DELETE RLS policies on all 7 campaign-domain tables. WITH CHECK using app.rmp_scope_advertiser_ids + admin bypass. Direct + via-campaign patterns. CI fix: behavioral tests now run with DATABASE_URL=retail_media_app (NOBYPASSRLS). S-008 gate verifies rolsuper=false, rolbypassrls=false before tests. Tests: 4 behavioral RLS write enforcement tests (TestRLSWriteEnforcement) + all existing mutation tests pass under NOBYPASSRLS. Policy matrix: 7 tables × 4 policies = 28 total. | — |
| S-009 | Frontend campaign management UI | P3 | 🚧 S-009b done | — | S-009b: admin-web auth shell + API client (React 19, react-router-dom, vitest). Login/logout/session, protected routes, /me loading, sidebar nav, placeholder pages for campaigns/advertisers. 11 API client tests. Build passes (48 modules, 592ms). Next: S-009c campaign list/detail. | Wire campaign list/detail (S-009c) |

## Status Legend

- **done** — implemented, tested, committed, pushed
- **locked** — architecture locked (ADR accepted), implementation deferred
- **open** — not started, ready for implementation
- **deferred** — intentionally postponed (documented reason)

## Remaining Gaps (non-blocking for backend pilot)

| Gap | Status |
|-----|--------|
| Real KSO player/sidecar | Out of scope |
| Frontend advertiser/admin portal | Scaffolded, not wired (S-009) |
| Real creative upload/storage/presigned URLs | Deferred |
| Production manifest signing (real HMAC) | Placeholder only |
| ClickHouse / materialized reporting (4.3e) | Deferred |
| Production deployment/observability hardening | Prometheus metrics/alerts deferred |
