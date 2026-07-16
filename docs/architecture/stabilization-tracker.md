# Stabilization Tracker — Retail Media Platform Enterprise

| **Last updated:** 2026-07-16
| **Current phase:** v0.6.2 published (tag 90e91cb). v0.7 inventory foundation: S-076 design ✅, S-077 schema ✅, S-078 availability ✅. S-079 booking запланирован. Roadmap format normalized (S-078b).|

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
- Real creative upload/storage/presigned URLs — S-017 done. Backend + admin-web upload UI shipped. Deferred: malware scan, transcoding, CDN, multipart upload
- Production manifest signing: HMAC-SHA256 implemented (S-021), production config hardened (S-021a). Verification at device-gateway deferred.
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
| S-009 | Frontend campaign management UI | P3 | 🚧 S-009b done | — | S-009b: admin-web auth shell + API client (React 19, react-router-dom, vitest). Login/logout/session, protected routes, /me loading, sidebar nav, placeholder pages for campaigns/advertisers. Auth contract fix: login/refresh/logout use /api/v1/auth + credentials:include (HttpOnly cookie), no refresh_token in JSON body, LoginResponse/MeResponse match backend schemas. 17 tests (13 API contract + 4 auth-shell). Build passes (48 modules, 605ms). Next: S-009c campaign list/detail. | Wire campaign list/detail (S-009c) |
| S-009rr | Runtime truth gate — CI green baseline | P0 | ✅ done (local) | — | **Root cause**: device-gateway used `Depends(get_session)` with no engine wiring; `get_session(engine)` needs an explicit engine arg (not a FastAPI dep). Fix: added lifespan engine creation + `get_db()` dependency (matching control-api pattern). Also: device-gateway/requirements.txt (sqlalchemy, asyncpg, PyJWT), orchestrator-worker/requirements.txt (sqlalchemy, asyncpg), pop-ingestor/requirements.txt (empty, Dockerfile expects file). Compose: added ENVIRONMENT=dev, JWT_SECRET, CORS_ALLOWED_ORIGINS, DATABASE_URL to device-gateway; added ENVIRONMENT to all services; added postgres health dependency to device-gateway. CI: added ENVIRONMENT=dev + JWT_SECRET to python-tests and import-boundaries jobs. Local baseline restored — **GitHub Actions verification pending after push**. | Push + verify GitHub Actions |
| S-015 | GitHub Release Versioning / Product Milestones | P1 | ✅ done | P.S. (Hermes) | Policy: `docs/architecture/release-versioning.md`. Tag v0.1-admin-campaign-mvp created at d291cfed. | — |
| S-016 | Dual Auth Readiness — local credentials + AD stub | P1 | ✅ done | P.S. (Hermes) | `/me` DB-backed (username, display_name, must_change_password). Seed: local_credentials for break_glass_admin + advertiser_test with production gate (ENVIRONMENT=dev / SEED_DEV_CREDENTIALS=true). Admin-web: provider selector (ad/local_advertiser/local_break_glass), AD stub → 503 message. E2E tests: dual auth cycle, refresh/logout, break-glass audit. AD stays stub — honest 503. Runbook: `docs/runbook/clean-install-login.md`. | Behavioural proof with real PostgreSQL |
| S-017 | Creative Media Upload (MinIO presigned URL) | P1 | ✅ done | P.S. (Hermes) | ...
| S-018 | Manifest / PoP Contract Alignment | P1 | ✅ done | P.S. (Hermes) | Schemas: `manifest_v1.schema.json` (flat playlist per ADR-016 v1 pilot), `proof_event_v1.schema.json` (flat, matches PopEventIn). Simulator: `_build_pop_event` emits `playback_result` + `campaign_id`. Nested per-surface playlist deferred to Manifest v2. Contract tests: 15 manifest + 16 PoP (schema validation, DTO round-trip, full-chain proof). ADR-016/017 updated. | Nested playlist for multi-surface KSO → v2 |
| S-019 | Runtime / Deployment Security Alignment | P0 | ✅ done | P.S. (Hermes) | Three-role DB architecture: `retail_media_owner` (DDL/migrations/seed), `retail_media_app` (NOBYPASSRLS runtime). `init-db.sql` + `grant-app-role.py`. Worker admin context via `set_worker_admin_context()` → `app.rmp_is_admin=true`. Compose: all runtime services use `retail_media_app`. device-gateway CORS removed. admin-web CORS +:3000. Role safety test suite (7 opt-in tests). Docs: delivery-runtime + clean-install-login updated. | Worker per-scope resolution (ADR-009 §9 Phase 3.6) |
| S-021 | Green Baseline After Audit | P0 | ✅ done | P.S. (Hermes) | Root causes: CI missing minio dep (S-017), manifest schema missing generated_at, seed tests scanning whole file, manifest_version hardcoded to 1, empty signature placeholder. Fixes: minio in CI + MANIFEST_SIGNING_KEY, generated_at in schema, seed test scoped to SEED_SQL, monotonic get_next_manifest_version_for_device per device, HMAC-SHA256 sign_manifest_payload/verify_manifest_signature, behavioural test approval bypass for S-017 metadata-only guard. 862→869 unit, 243→245 behavioural. CI Run #84 green. | — |
| S-021a | Manifest Signing Config Hardening | P0 | ✅ done | P.S. (Hermes) | SecurityConfig: _validate_manifest_signing_production() — fail-fast ValueError on missing/short/weak key in production. Dev: empty allowed, warn on <16. Compose: MANIFEST_SIGNING_KEY in orchestrator-worker. 7 new config+integration tests. CI Run #85 green. | — |
| S-023a | Advertiser Portal Foundation — Seed RBAC + Scaffold | P0 | ✅ done | P.S. (Hermes) | Seed: advertiser role (id=0000...0114) with 6 permissions (campaigns read/manage, creatives.read, advertisers/contacts read, organization.read), scoped user_roles for advertiser_test → ADV-001. Advertiser-web: separate Vite React TS SPA (port 3001), auth shell (local_advertiser only), ProtectedRoute with provider + campaigns.read guard, read-only campaign list with typed ApiError error handling. Tests: 40 seed source-inspection + 12 vitest frontend (auth/protectedRoute/campaignList). CI Run #87 green after seed insert count fix (83→91). | S-023b: campaign detail page |
| S-023b | Advertiser Portal — Read-only Campaign Detail | P0 | ✅ done | P.S. (Hermes) | CampaignDetailPage: route /campaigns/:id, clickable list rows, 5 sections (Обзор, Флайты, Размещения, Креативы, Согласование). Data from 7 identity endpoints (list + client-side filter by campaign_id). Types fixed: CampaignApprovalOut (requested_by/at, reviewed_by/at, decision), CampaignStatusHistoryOut (old_status, changed_at, reason). No admin buttons, no storage secrets. Tests: 5 vitest (render, 7 API calls, 403/401, storage safety). Build passes. Advertiser-web CI covered (S-023a.1). | S-023c: creative library/upload |
| S-023c | Advertiser Portal — Creative Library + Upload | P0 | ✅ done | P.S. (Hermes) | CreativeLibraryPage: table (name, type, size, status, moderation), create metadata-only (POST /creative-assets), upload flow (upload-intent → XHR PUT presigned no-Auth → complete-upload → refresh), progress bar. Route /creatives. Layout: Креативы nav. Types: CreativeAssetCreateRequest, UploadIntent*, CompleteUpload*. No storage_bucket/key/presigned_url in UI. Tests: 9 vitest (list, empty, 403, 401, no storage, upload button, create POST, upload-intent call, error). 26 total advertiser-web tests. Build passes. | S-023d: PoP reporting |
| S-023e | Advertiser Portal — Profile + Password Change | P0 | ✅ done | P.S. (Hermes) | ProfilePage: organisation/brands/contracts/contacts display, password change form (current/new/confirm), must_change_password banner. Types: AdvertiserOrganizationOut/AdvertiserBrandOut/AdvertiserContractOut/AdvertiserContactOut. Auth helpers: contactTypeLabel, authProviderLabel. Tests: 13 vitest (5 profile render + 8 password change). | S-023f: campaign create/edit draft |
| S-023f | Advertiser Portal — Campaign Create/Edit Draft Flow | P0 | ✅ done | P.S. (Hermes) | CampaignCreatePage: /campaigns/new with org/brand/contract selects, auto-code from name, validation, POST /campaigns. CampaignDetailPage: draft edit mode (inline EditCampaignForm), PATCH /campaigns/{id}. CampaignListPage: + «Создать» button. No backend changes. Tests: 6 create + 2 edit vitest (53 total). CI #29162245072 green (all 33 jobs including behavioural). | S-023g: attach creative + submit approval |
| S-023g | Advertiser Portal — Attach Creative + Submit Approval | P0 | ✅ done | P.S. (Hermes) | CampaignDetailPage: «+ Прикрепить креатив» button (draft only), AttachCreativeModal with ready/metadata_only filtering, POST /campaigns/{id}/creatives/attach. ReadinessPanel: flights/placements/creatives checks + «Отправить на согласование» button (disabled until ready), POST /campaigns/{id}/request-approval. Non-draft: read-only message. No approve/reject buttons. Tests: 13 new vitest (66 total). CI #29162925840 green (all 33 jobs including behavioural). | S-023h: localization polish |
| S-023h | Advertiser Portal — Localization Polish | P1 | ✅ done | P.S. (Hermes) | Russian labels for status (Черновик/Активна/etc), contact_type (Основной/Бухгалтерия), auth_provider (Локальная учётная запись), surface UUIDs → «Поверхность XXXXXXXX», timezoneLabel (Москва GMT+3). Helpers: statusLabel, contactTypeLabel, authProviderLabel, timezoneLabel, surfaceLabel, mediaTypeLabel. Tests: 66 vitest. CI #29166284943 green. | S-023i: responsive layout polish |
| S-023i | Advertiser Portal — Responsive Layout Polish | P1 | ✅ done | P.S. (Hermes) | Layout.module.css replaces inline styles. Hamburger + overlay sidebar for <768px. Tables: overflow-x:auto on narrow (no page-level overflow). Text fixes: timezoneLabel, mediaTypeLabel in CampaignDetailPage. Tests: 66 vitest. CI #29166816518 green (33/33). | S-026: live LAN preview |
| S-024 | v2.6 Next Branch Requirements Captured | P1 | ✅ done | P.S. (Hermes) | TZ v2.6 DOCX placed in `docs/product/requirements/`. ADR-018 (tenant model) proposed — P0 decision needed before v2.6 implementation. Roadmap updated with v2.6 rows. Release-versioning has Future branch section. No code changes. | Tenant model ADR accepted → implementation |
| S-029 | Production Gaps Triage | P0 | ✅ docs/triage done | P.S. (Hermes) | `docs/product/production-gaps-triage.md` — 8 categories, 35+ gaps triaged with P0/P1/P2/P3 severity. Recommended milestones v0.5–v0.9. Roadmap updated with production gap rows. No code changes. Branch: develop. | Start v0.5 P0 gates |
| S-030 | Production CI Gate + Secrets Validation | P0 | ✅ done | P.S. (Hermes) | `packages/security/config.py`: SEED_DEV_CREDENTIALS, CORS localhost, DATABASE_URL validation in production. `tests/test_production_config_gate.py`: 24 tests (positive + negative). CI: `production-config-gate` job in phase1-ci.yml. Branch: feature/S-030. | — |
| S-031 | Backup / Restore / DR Runbook + Tested Restore Drill | P0 | ✅ done | P.S. (Hermes) | `scripts/backup/postgres_backup.py`, `scripts/restore/postgres_restore.py`. `tests/integration/test_backup_restore.py` (5/5). `docs/runbook/backup-restore-dr.md`. Live drill: 4.7MB, 39 таблиц. Branch: feature/S-031. | — |
| S-031a | Stabilize flaky outbox relay behavioural test | P0 | ✅ done | P.S. (Hermes) | Root cause: due events from other suites consumed `fail_next(1)`. Fix: delete ALL due events + per-event assertions. CI #29188698606 green (33/33). Branch: fix/S-031a. | — |
| S-033 | Admin User Management + Local Account Administration | P0 | ✅ done | P.S. (Hermes) | Backend: 5 новых endpoint'ов (GET /users/{id}, POST /users/local-advertiser, activate/deactivate, reset-password). Permissions: users.read/users.manage. Frontend: UsersPage с create/deactivate/reset. Build OK, 64 tests. Branch: feature/S-033. | — |
| S-033s | Security hardening (RLS, org validation, self-lockout) | P0 | ✅ done | P.S. (Hermes) | P1/P2 fixes from S-033r. Branch: fix/S-033s. | — |
| S-034 | AD/LDAPS Settings UI + Honest Connection Status | P0 | ✅ done | P.S. (Hermes) | GET/POST /auth/ad-settings endpoints with users.manage. ADSettingsPage in admin-web. Honest stub/disabled/configured status. No secrets exposed. 9 backend tests + 64 frontend. Branch: feature/S-034. | — |
| S-035 | External audit hardening (S-035a–i + S-035R re-review + S-035T test gaps) | P0 | ✅ done | P.S. (Hermes) | 9 audit findings closed, 5 test gaps filled, CI green. Branches: fix/S-035-*. | — |
| S-036 | Creative Moderation Queue | P0 | ✅ done | P.S. (Hermes) | Backend: 3 endpoints (GET moderation-queue, POST approve/reject) with `creatives.moderate` permission, creative_auto_approve_uploads now False. Frontend: CreativeModerationPage in admin-web (/creatives/moderation), advertiser-web moderation status + rejection reason. Tests: 12 backend + 0 frontend regression. Branch: feature/S-036-creative-moderation-queue. | — |
| S-037 | Advertising Inventory UI | P0 | ✅ done | P.S. (Hermes) | Backend: 3 endpoints (GET /inventory/stores, GET /inventory/surfaces, PATCH /inventory/surfaces/{id}) with `inventory.read`/`inventory.manage`. Enriched schemas with cluster/branch/store names + surface count. Frontend: InventoryPage with stores/surfaces tabs, search, active/inactive toggle. Tests: 6 backend + 68 advertiser-web regression. Branch: feature/S-037-advertising-inventory-ui. | — |
| S-038 | Campaign Approval Inbox | P0 | ✅ done | P.S. (Hermes) | Backend: GET /campaigns/approval-queue with readiness summary + creative moderation gate in approve_campaign. Frontend: ApprovalInboxPage with readiness checklist, approve/reject, rejection reason. Tests: 4 backend + 64 admin-web regression. Branch: feature/S-038-campaign-approval-inbox. | — |
| S-039 | Admin Advertisers Management Page | P0 | ✅ done | P.S. (Hermes) | Backend: 6 endpoints (org detail, filtered brands/contracts/contacts by org, user memberships) with advertisers.read/contacts.read + RLS. Frontend: AdvertisersPage replaces stub — org list with search + detail panel with 5 tabs (overview, brands, contracts, contacts, users). No secrets/PII exposed. Read-only. Tests: 17 backend + 7 admin-web vitest. Branch: feature/S-039-admin-advertisers-page. | — |
| S-040 | PoP Reporting Export CSV | P0 | ✅ done | P.S. (Hermes) | Backend: GET /campaigns/{id}/pop/export — CSV with BOM, same auth/RBAC/RLS as JSON endpoints. Russian headers. Frontend: admin-web + advertiser-web «Скачать CSV» buttons. XLSX deferred (no openpyxl in project requirements). Tests: 11 backend + existing vitest regression green. Branch: feature/S-040-pop-report-export. | — |
| S-032 | Roadmap Re-sequence: Business Portal before Player | P0 | ✅ docs done | P.S. (Hermes) | Roadmap resequenced per original ТЗ. No code changed. Branch: develop. | — |
| S-042a | Stabilization tracker refresh for v0.5 RC | P0 | ✅ done | P.S. (Hermes) | `docs/architecture/stabilization-tracker.md` updated: header, remaining gaps. Branch: docs/S-042a. | — |
| S-043 | v0.5 Release Prep | P0 | ✅ done | P.S. (Hermes) | `release-versioning.md`: v0.5 section. `production-gaps-triage.md`: baseline→v0.5. `roadmap-s020.xlsx`: v0.5 rows→✅. Branch: docs/S-043. | — |
| S-044 | Publish v0.5 | P0 | ✅ done | P.S. (Hermes) | main ff→5114f83. Tag v0.5-business-portal-complete→5c41a6a. CI #29248156271 green (34/34). | — |
| S-045 | Audit Reconciliation | P0 | ✅ done | P.S. (Hermes) | 9/9 S-035 findings CLOSED. Architecture gaps deferred honestly. GO verdict. | — |
| S-046 | v0.6 Production Readiness Plan | P0 | ✅ done | P.S. (Hermes) | `docs/product/v06-production-readiness-plan.md`: S-047…S-055 sequence complete. Monitoring, LDAPS, backups, error boundaries, audit events, router split, RLS test, XLSX decision — all done. Out of scope: KSO, Emergency, Flags, Inventory, ClickHouse, v2.6. | S-055 done, ready for S-056 release prep |
| S-047 | Observability baseline (Prometheus/Grafana) | P0 | ✅ done | P.S. (Hermes) | `packages/observability/metrics.py`: 18 metrics (common + domain), /metrics endpoint on control-api + device-gateway. `infra/compose/docker-compose.observability.yml`: Prometheus + Grafana. `infra/observability/`: prometheus.yml, alerts.yml, grafana dashboard rmp-overview.json. `docs/runbook/observability.md`. Tests: 9/9. AlertManager not provisioned (known limitation). | — |
| S-048 | Real LDAPS authentication | P0 | ✅ done | P.S. (Hermes) | `packages/auth/ad_provider.py`: RealLDAPAuthProvider with ldap3 bind+search, safe filter escaping, timeouts, no password logs. AD settings/test endpoints updated with real provider. `docs/runbook/ldaps-auth.md`. Stub preserved when AD_ENABLED=false. | — |
| S-049 | MinIO backup/restore drill | P0 | ✅ done | P.S. (Hermes) | `scripts/backup/minio_backup.py`: full-bucket backup with SHA-256 manifest. `scripts/restore/minio_restore.py`: check/dry-run/confirm. 4 integration tests. Runbook: `docs/runbook/minio-backup-restore.md`. | — |
| S-050 | NATS backup policy | P1 | ✅ done | P.S. (Hermes) | Outbox-first recovery policy. `scripts/check/nats_recovery_check.py`. 4 integration tests. Runbook: `docs/runbook/nats-backup-restore.md`. | — |
| S-051 | Portal error boundaries | P2 | ✅ done | P.S. (Hermes) | ErrorBoundary in admin-web + advertiser-web. Russian fallback, JWT sanitisation. 19 vitest tests. | — |
| S-052 | Audit events for approval/moderation | P2 | ✅ done | P.S. (Hermes) | campaign.approved/rejected + creative.approved/rejected in same tx. No secrets/storage fields. 10 audit tests. | — |
| S-053 | identity router decomposition | P2 | ✅ done | P.S. (Hermes) | identity.py split into 8 domain routers (users, ad_settings, advertisers, campaigns, creatives, reporting, inventory + common). 40-line aggregator. API paths, permissions, schemas unchanged. CI green. | — |
| S-054 | creative_upload_sessions behavioural RLS | P1 | ✅ done | P.S. (Hermes) | 5 NOBYPASSRLS scenarios. Policy unchanged, proven fail-closed. CI behavioural gate green. | — |
| S-054a | XLSX export decision | P2 | ✅ done | P.S. (Hermes) | CSV-only for v0.6 (S-040). XLSX deferred to v0.7/v0.8. | — |
| S-055 | v0.6 readiness review | P0 | ✅ done | P.S. (Hermes) | CONDITIONAL GO: code/CI/security ready. 5 docs honesty P0 findings. | S-055a fix docs |
| S-055a | v0.6 docs honesty fix | P0 | ✅ done | P.S. (Hermes) | 5 P0 + 1 P2 docs fixed. v06 plan, release-versioning, tracker, roadmap updated. Branch: docs/S-055a. | S-056 release prep |
| S-056 | v0.6 release prep | P0 | ✅ done | P.S. (Hermes) | `release-versioning.md`: v0.6 finalised. `stabilization-tracker.md`: S-056 row. `production-gaps-triage.md`: baseline→v0.6. `roadmap-s020.xlsx`: v0.6→ready for publish. Tag target: `fd43791`. Branch: docs/S-056. | Publish (S-057) |
| S-057 | Publish v0.6 | P0 | ✅ done | P.S. (Hermes) | main ff→b00772d. Tag v0.6-production-readiness-foundation→fd43791. CI #29360043628 green 34/34. | — |
| S-059 | v0.6 critical hotfix (external audit v4) | P0 | ✅ done | P.S. (Hermes) | CRITICAL-1: LDAPS cert validation — ssl.CERT_REQUIRED, AD_CA_CERT_FILE, ldap3 in requirements+CI. CRITICAL-2: RLS context on moderation/approval queues — set_rls_context on 4 endpoints. Tests: 7 AD cert + 9 hotfix-verification. CI #29403409655 green 34/34. | — |
| S-060 | Publish v0.6.1 critical hotfix | P0 | ✅ done | P.S. (Hermes) | main ff→00060cc. Tag v0.6.1-critical-hotfix→00060cc. CI #29404001541 green 34/34. | — |
| S-061 | Audit v4 remediation plan | P0 | ✅ done | P.S. (Hermes) | `docs/product/audit-v4-remediation-plan.md`: P1/P2/P3 classified, S-062…S-074 proposed. Tracker, gaps triage, release-versioning, roadmap updated. | Start S-062 |
| S-062 | Auth / test / dependency truth (P1) | P1 | ✅ done | P.S. (Hermes) | No-op async auth tests → IsolatedAsyncioTestCase (22 tests awakened). Guard test against async-in-plain-TestCase. Audit events: auth.login.success, auth.login.failure, auth.logout (7 new tests). Dependency truth: minio added to requirements, PyJWT bounds aligned (≥2.12.0), CI install unified. | — |
| S-063 | PoP timezone correctness (P1) | P1 | ✅ done | P.S. (Hermes) | `list_campaign_pop_by_day` now groups by local store day (Store.timezone → Branch.timezone → Europe/Moscow) via PostgreSQL `timezone()` + `COALESCE`. 8 unit tests + 1 behavioural (Vladivostok UTC+10 proof). API shape unchanged. | — |
| S-064 | Approval concurrency + audit consistency (P1) | P1 | ✅ done | P.S. (Hermes) | `approve_campaign` + `reject_campaign` now use `SELECT ... FOR UPDATE` — row-level lock serializes concurrent transitions. Production fix only. | — |
| S-064a | Approval concurrency behavioural proof | P1 | ✅ done | P.S. (Hermes) | 3 behavioural tests (approve/approve, approve/reject, reject/reject) with real PostgreSQL — two AsyncConnections, `asyncio.gather`, manual BEGIN/COMMIT. Proves FOR UPDATE prevents duplicate approvals/history. | — |
| S-065 | Metrics/rate-limit/device-gateway hardening | P1 | ✅ done | P.S. (Hermes) | METRICS_AUTH_TOKEN protects both /metrics endpoints (fail-fast in production). In-memory token bucket rate limit on device manifest + PoP batch. Device-gateway 403 errors no longer leak internal status. | — |
| S-066 | Pagination foundations | P1 | ✅ done | P.S. (Hermes) | Generic PaginatedResponse[T] schema + 5 paginated repo methods. 6 endpoints: /inventory/stores, /inventory/surfaces, /campaigns, /campaigns/approval-queue, /creative-assets/moderation-queue. MAX_LIMIT=200, DEFAULT_LIMIT=50. Admin-web: 4 pages with pagination controls + total/range display. | — |
| S-066a | Pagination CI truth / test mock fix | P1 | ✅ done | P.S. (Hermes) | Fixed 6 identity API test mocks (old function names → _paginated variants, list return → tuple). Fixed 3 behavioural campaign tests (PaginatedResponse shape). Root cause: mock paths not updated during S-066 function renames. CI now fully green — all 34 jobs including Behavioural PostgreSQL. | — |
| S-067 | Manifest performance + Redis cache | P1 | ✅ done | P.S. (Hermes) | Fast ETag: lightweight metadata query (1 SELECT) before full assembly — 304 returned without 6+ queries + HMAC. Redis cache: optional fail-open cache for manifest payloads (REDIS_URL, MANIFEST_CACHE_ENABLED, TTL). Content-hash guarded against stale cache. 0 dependencies on Redis at import time. | — |
| S-068 | DB pool + retention + lookup index | P2 | ✅ done | P.S. (Hermes) | Configurable DB pool (DB_POOL_SIZE/MAX_OVERFLOW/TIMEOUT/RECYCLE). Delivery manifests retention script (dry-run safe, never deletes latest). PoP events retention strategy documented. Composite index ix_delivery_manifests_device_status_generated for manifest lookup. | — |
| S-069 | Admin: audit log UI + permission-filtered menu | P2 | ✅ done | P.S. (Hermes) | Layout.tsx filters nav items by user permissions from /me. Audit log page at /audit — paginated table, Russian labels, secret redaction. Backend audit-events endpoint was already ready — no backend changes needed. | — |
| S-070 | Fleet / device health workspace | P2 | ✅ done | P.S. (Hermes) | GET /devices, /devices/summary, /devices/{id} endpoints with devices.read permission. Admin-web DeviceHealthPage — summary cards + paginated table. Honest «нет данных» for missing telemetry (player/chromium version, free space — not yet collected by runtime). | — |
## Status Legend

- **done** — implemented, tested, committed, pushed
- **locked** — architecture locked (ADR accepted), implementation deferred
- **open** — not started, ready for implementation
- **open/prepared** — definition written, tag commands prepared, awaiting approval
- **deferred** — intentionally postponed (documented reason)

## Remaining Gaps (v0.6 Production Readiness — ready for release prep)

| Gap | Status |
|-----|--------|
| Monitoring/observability (Prometheus/Grafana) | ✅ S-047 done |
| Real AD/LDAPS | ✅ S-048 done |
| MinIO backup (S3 mirror) | ✅ S-049 done |
| NATS backup policy | ✅ S-050 done |
| Portal error boundaries | ✅ S-051 done |
| Audit events for approval/moderation | ✅ S-052 done |
|| identity.py router decomposition | ✅ S-053 done |
|| XLSX export | ✅ S-054a done — CSV-only for v0.6, XLSX deferred |
|| Full behavioural RLS test for creative_upload_sessions | ✅ S-054 done |
| Production UX/accessibility audit | Deferred — v0.7 |
| Emergency Management backend | Deferred — v0.7 |
| Feature flags / staged rollout | Deferred — v0.7 |
| Inventory Planning / Forecasting | Deferred — v0.8 |
| Report snapshots | Deferred — v0.8 |
| ClickHouse / materialized reporting | Deferred — v0.8 |
| Real KSO player/sidecar | Deferred — v0.9 |
| Malware scan / transcoding / renditions | Deferred — v0.9 |
| Production manifest signing verification at device-gateway | Deferred — v2.6 |
| Billing / acts / ERP | Deferred — v2.6 |
| Sales lift / attribution | Deferred — v2.6 |
| Mobile application | Deferred — v2.6 |
| Tenant model ADR before v2.6 | 🟡 Decision needed — ADR-018 |
| Password reset invite/email flow | Deferred |
| Advertiser approve/reject campaigns | Deferred — admin-only |

## Audit v4 Remediation Backlog (S-061 plan)

| Ticket | Area | Priority | Status |
|--------|------|----------|--------|
| S-062 | Auth/test/dependency truth (no-op async, audit login/logout, requirements) | P1 | ✅ done |
| S-063 | PoP by-day timezone correctness | P1 | ✅ done |
| S-064 | Approval concurrency + audit consistency | P1 | ✅ done |
| S-064a | Approval concurrency behavioural proof | P1 | ✅ done |
| S-065 | Metrics/rate-limit/device-gateway hardening | P1 | ✅ done |
| S-066 | Pagination foundations (stores, surfaces, campaigns, queues) | P1 | ✅ done |
| S-066a | Pagination CI truth / test mock fix | P1 | ✅ done |
| S-067 | Manifest performance + Redis cache | P2 | ✅ done |
| S-068 | DB pool + retention strategy (delivery_manifests, pop_events_raw) | P2 | ✅ done |
| S-069 | Admin UI: audit log + permission-filtered menu | P2 | ✅ done |
| S-070 | Fleet/device health workspace | P2 | ✅ done |
| S-071 | Emergency workspace / kill-switch UI | P2 | ✅ done |
| S-072 | Inventory domain gap analysis and plan | P2 | ✅ done |
| S-073 | UI design-system / a11y foundation | P3 | ✅ done (foundation) |
| S-074 | v0.6.2 audit-remediation readiness review | — | ✅ done |
| S-075 | Publish v0.6.2-audit-remediation | — | ✅ done (tag at 90e91cb, CI #29484402650 green) |
| S-076 | Inventory domain foundation — architecture model design | P0 | ✅ done |
| S-077 | Inventory schema + repository skeleton | P0 | ✅ done |
| S-078 | Inventory availability calculator MVP | P0 | ✅ done |
| S-078b | Roadmap format + Russian business narrative repair | — | ✅ done |
| S-079 | Inventory reservation lifecycle + campaign integration | P0 | ✅ done |
| Tenant model ADR before v2.6 | 🟡 Decision needed — ADR-018 |
| Password reset invite/email flow | Deferred |
| Advertiser approve/reject campaigns | Deferred — admin-only |
