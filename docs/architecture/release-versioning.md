# Release Versioning Policy — Retail Media Platform Enterprise

| **Created:** 2026-07-10
| **Version:** 1.0
| **Status:** active

## Purpose

Lightweight internal release versioning for project-control milestones.
Every release is a named Git tag that captures a known-good state of the
codebase with full traceability: what's included, what's not, and how to
roll back.

No semantic versioning (semver) for internal milestones — the platform is
pre-production.  Use descriptive tag names that communicate what business
capabilities the release delivers.

## Release Naming Convention

Use lowercase hyphen-separated names:

```
v{major}.{minor}-{description}
```

**Proposed milestones:**

| Tag | Description |
|-----|-------------|
| `v0.1-admin-campaign-mvp` | Admin portal + campaign CRUD, creative attach, approval, basic PoP reporting |
| `v0.2-media-upload-runtime-baseline` | Real media upload (S-017), manifest/PoP contracts (S-018), three-role DB (S-019), green CI baseline (S-021), HMAC signing configuration (S-021a) |
| `v0.3-advertiser-portal-foundation` | Advertiser portal: login, campaign list/detail, creative library+upload, PoP reporting |
| `v0.4-advertiser-self-service-pilot` | Advertiser self-service pilot: create/edit drafts, attach creative, submit approval, profile/password, responsive layout, live LAN preview |

Major (0.x) stays at 0 until first production deployment.  Minor
increments on each milestone release.

## Release Definition Template

Every release record must include:

```markdown
## v0.N-description — Title

### Metadata
- **Tag:** v0.N-description
- **Date:** YYYY-MM-DD
- **Commit SHA:** <full 40-char hash>
- **GitHub Actions run:** #<number> (conclusion: success)
- **Created by:** <name or "Hermes via P.S.">

### Business Capabilities
- bullet list of what business users can now do

### Technical Capabilities
- bullet list of infrastructure, APIs, subsystems delivered

### Known Limitations / Not Included
- explicit exclusion list — what this release does NOT do

### Rollback Note
- how to revert to the previous known-good state
- any migration/downgrade considerations

### References
- roadmap Excel snapshot reference (if available)
- related ADRs, design gates, phase reports
```

## Tag Commands

To create a release (requires explicit approval):

```bash
git tag -a <tagname> <commit-sha> -m "<title>"
git push origin <tagname>
```

Example:

```bash
git tag -a v0.1-admin-campaign-mvp d291cfed2eb1e6299080862f15e7f422247793d3 -m "v0.1 admin campaign MVP"
git push origin v0.1-admin-campaign-mvp
```

**Tags MUST NOT be created without explicit approval.**  This policy
document is the pre-approval preparation only.

## Release Artifacts

Each release produces:

1. **Git tag** — immutable reference to the commit
2. **This file** — release definition appended below
3. **Stabilization tracker update** — S-015 status change from open/prepared
   to done after tag creation

No GitHub Releases UI artifacts (release notes, binary attachments) are
required for internal milestones.

## Appendix: Proposed Release Definitions

*(Definitions below are proposed and subject to approval.)*

---

### v0.1-admin-campaign-mvp — Admin Campaign MVP

**Proposed.**  Tag not yet created.

#### Metadata
- **Tag:** v0.1-admin-campaign-mvp
- **Date:** 2026-07-10 (proposed)
- **Commit SHA:** d291cfed2eb1e6299080862f15e7f422247793d3
- **GitHub Actions run:** #72 (conclusion: success, all 32 jobs)
- **Created by:** P.S. (via Hermes)

#### Business Capabilities

- Staff login via LDAPS (Active Directory)
- Local advertiser login (email + bcrypt) — auth shell only, no advertiser portal
- Create, edit, archive campaigns
- Define flights (date ranges, budget)
- Define placements (display surfaces, creative slots)
- Attach creative assets (metadata-only — title, duration, mime type)
- Request approval, approve, reject campaigns
- View basic Proof-of-Play reporting per campaign

#### Technical Capabilities

- **Auth:** LDAPS bind/search interface defined (ADR-006), stub implementation (AD/production not yet wired). Local credentials (bcrypt) for advertiser/break-glass — product-ready path. JWT access/refresh tokens, HttpOnly cookies
- **RBAC/RLS:** two-layer defence — application-level permission checks + PostgreSQL RLS (28 policies on 7 tables)
- **Campaign domain:** ORM models (7 tables), CRUD endpoints, flight/placement/creative attachment APIs
- **Approval workflow:** request-approval/approve/reject with audit trail
- **Creative asset intake:** metadata-only (title, duration, mime_type) — no file storage yet
- **PoP reporting:** GET /api/v1/identity/campaigns/{id}/pop/{summary,by-day,by-surface}
- **Outbox relay:** transactional outbox → NATS JetStream → consumer → manifest generation
- **Device gateway:** GET /api/v1/device/manifest/latest (device JWT, ETag/304, security-hardened)
- **Admin web (React):** auth shell, login/logout, session, protected routes, campaign list/detail, create wizard, creative attach, approval UI
- **Testing:** 150+ unit, 150+ behavioral, 2 integration (NATS E2E + pilot E2E, opt-in)
- **CI:** GitHub Actions — 32 jobs per run, PostgreSQL behavioral gate with RLS runtime role

#### Known Limitations / Not Included

- Real file upload, storage, or presigned URLs — creative assets are metadata-only
- Real KSO player or sidecar
- Physical KSO hardware integration
- Advertiser portal — only admin web shipped
- ClickHouse, materialized views, or export/reporting pipeline
- Billing
- Android TV, price checker, ESL, LED
- Production-grade observability (Prometheus metrics, alert rules)
- Production manifest signing (HMAC placeholder only)

#### Rollback Note

No schema-breaking migrations in this release.  To revert:

```bash
git checkout <previous-known-good-sha>
```

If the tag was pushed, delete it:

```bash
git tag -d v0.1-admin-campaign-mvp
git push origin :refs/tags/v0.1-admin-campaign-mvp
```

The outbox/migration state is forward-compatible — reverting code does
not require database downgrade for this release.

#### References

- ADR-001 through ADR-017 (all architecture decision records)
- `docs/architecture/stabilization-tracker.md` (S-001 through S-015)
- Phase close-out reports: `phase-4-campaign-domain.md`, `phase-4-delivery-domain.md`

---

### v0.2-media-upload-runtime-baseline — Media Upload + Runtime Baseline

**Proposed.**  Tag not yet created.

#### Metadata
- **Tag:** v0.2-media-upload-runtime-baseline
- **Date:** 2026-07-11 (proposed)
- **Commit SHA:** a0cc5a2 (pending final verification)
- **GitHub Actions run:** #85 (conclusion: success, all jobs)
- **Created by:** P.S. (via Hermes)

#### Business Capabilities

- Upload creative media files (images, video) via presigned URLs
- Creative assets validated server-side (SHA-256, file size, mime type) — no client trust
- View upload progress and creative readiness in admin web Creatives tab
- Dual local auth operational: advertiser + break-glass admin credentials with bcrypt
- `/me` endpoint returns real DB-backed user profile
- Manifest integrity: backend HMAC-SHA256 signing (requires MANIFEST_SIGNING_KEY in production)

#### Technical Capabilities

- **S-016 — Dual auth:** local_credentials table + bcrypt hashing for advertiser/break-glass, AD stub (honest 503), DB-backed /me
- **S-017 — Media upload:** MinIO presigned PUT URLs, server-side SHA-256 + size + mime validation, complete-upload flow, admin-web upload UI, upload session tenant protection
- **S-018 — Contract alignment:** manifest_v1.schema.json + proof_event_v1.schema.json, contract validation tests, simulator PoP contract compliance
- **S-019 — Three-role DB:** retail_media_owner (DDL/migrations), retail_media_app (NOBYPASSRLS runtime), init-db.sql + grant-app-role.py, CI behavioural gate with RLS runtime role
- **S-021 — Green baseline:** CI dependency fix (minio), manifest schema fix (generated_at), seed test scope fixes, monotonic manifest_version per device, HMAC signing (sign_manifest_payload / verify_manifest_signature)
- **S-021a — Signing config:** production MANIFEST_SIGNING_KEY mandatory (≥32 chars, reject weak), dev graceful degradation, compose orchestrator-worker wired
- **Testing:** 869 unit + 245 behavioural + 2 integration (opt-in) = 1,116 total
- **CI:** GitHub Actions — all jobs green, PostgreSQL behavioural gate with NOBYPASSRLS runtime role

#### Known Limitations / Not Included

- Real KSO player or sidecar — device gateway HTTP only, no hardware
- Advertiser portal — admin web only
- ClickHouse production reporting, materialized views, export, billing
- Android TV, price checker, ESL, LED
- Malware scanning, manual moderation, transcoding, CDN, orphan cleanup, multipart upload
- Production deployment/observability beyond current health/readiness endpoints
- Manifest signature verification at device-gateway (signing exists, verification deferred)
- NATS stream/consumer provisioning not yet automated for production

#### Rollback Note

Schema additions since v0.1 are forward-compatible (local_credentials, delivery tables, creative asset storage fields). Reverting code does not require database downgrade.

To revert:

```bash
git checkout v0.1-admin-campaign-mvp
```

If tag was pushed, delete:

```bash
git tag -d v0.2-media-upload-runtime-baseline
git push origin :refs/tags/v0.2-media-upload-runtime-baseline
```

#### References

- ADR-001 through ADR-017
- S-016 through S-021a in `docs/architecture/stabilization-tracker.md`
- `docs/runbook/media-upload.md`, `docs/runbook/delivery-runtime.md`, `docs/runbook/clean-install-login.md`

---

### v0.3-advertiser-portal-foundation — Advertiser Portal Foundation

**Proposed.**  Tag not yet created.

#### Metadata
- **Tag:** v0.3-advertiser-portal-foundation
- **Date:** 2026-07-11 (proposed)
- **Commit SHA:** b2fba92e8271751408a6a878cd186b6adb6b02a5
- **GitHub Actions run:** #29159995308 (conclusion: success, all jobs)
- **Created by:** P.S. (via Hermes)

#### Business Capabilities

- Advertiser login via local credentials (email + bcrypt)
- Separate advertiser web application (не путать с admin‑web)
- View list of own campaigns with clickable rows
- Read‑only campaign detail: overview, flights, placements, creatives, approval status
- Creative library: view all uploaded creatives, create new creative metadata
- Upload creative media files (images, video) via presigned PUT URLs with progress bar
- PoP reporting per campaign: summary cards (impressions, duration), by‑day table, by‑surface table
- Honest disclaimer: «Не является отчётом по продажам или атрибуции»

#### Technical Capabilities

- **Seed RBAC:** `advertiser` role (6 permissions: campaigns read/manage, creatives read, advertisers/contacts read, organization read) with scoped `user_roles` → `SEED_ADV_ORG_ID`
- **Advertiser‑web:** separate Vite React TS SPA (5 test files, 32 vitest tests), port 3001
- **Auth:** `local_advertiser` provider only, JWT access/refresh tokens via HttpOnly cookies, `ProtectedRoute` with `campaigns.read` guard
- **API client:** typed `ApiError` with `instanceof` checks, not string‑matching
- **Campaign list:** GET `/identity/campaigns` with table, error/empty/loading states, 401 logout, 403 friendly
- **Campaign detail:** GET 7 identity endpoints, client‑side filter by `campaign_id`, 5 tabs
- **Creative library:** GET `/identity/campaigns/{id}/creatives` per campaign, POST `/creative-assets`, upload‑intent → XHR PUT presigned (no Authorization header) → complete‑upload → refresh
- **PoP reporting:** GET `/identity/campaigns/{id}/pop/{summary,by‑day,by‑surface}`, lazy‑loaded
- **CI coverage:** advertiser‑web in frontend matrix (tsc → build → vitest), admins‑web 64 tests unchanged
- **Backend unchanged:** no schema/RLS/endpoint changes, all identity endpoints reused as‑is
- **Testing:** 877 backend unit + 245 behavioural + 64 admin‑web + 32 advertiser‑web = 1,218 total

#### Known Limitations / Not Included

- Campaign create/edit from advertiser portal — not implemented
- Attach existing creative to campaign from advertiser portal — not implemented
- Submit/request approval from advertiser portal — not implemented
- Advertiser organization/profile page — not implemented
- Password change / `must_change_password` flow — not implemented
- Production UX polish / accessibility review — not done
- Sales lift / attribution reporting
- Billing, invoices, export
- ClickHouse reporting / materialized views
- KSO player / real device playback
- Android TV, LED, ESL
- v2.6 domains (self‑service cabinet, competitive separation, store‑level targeting, etc.)

#### Rollback Note

No schema changes, no backend changes. Rollback is pure frontend:

```bash
git checkout v0.2-media-upload-runtime-baseline
```

If tag was pushed, delete:

```bash
git tag -d v0.3-advertiser-portal-foundation
git push origin :refs/tags/v0.3-advertiser-portal-foundation
```

#### References

- ADR-001 through ADR-018
- S-023a through S-023d in `docs/architecture/stabilization-tracker.md`
- CI run #29159995308 (all gates green)
- `apps/advertiser-web/src/` — 5 test files, 32 vitest tests

---

### v0.4-advertiser-self-service-pilot — Advertiser Self-Service Pilot

**Proposed.**  Tag not yet created.

#### Metadata
- **Tag:** v0.4-advertiser-self-service-pilot
- **Date:** 2026-07-11 (proposed)
- **Commit SHA:** 38b5255b1600ec3f5e960bcbadfa73f1b7922e22
- **GitHub Actions run:** #29166816518 (conclusion: success, 33/33 jobs)
- **Created by:** P.S. (via Hermes)

#### Business Capabilities

- Advertiser login via local credentials (email + bcrypt)
- Campaign list and detail view (overview, flights, placements, creatives, approval status)
- Create and edit campaign drafts from advertiser portal
- Creative library — view, create metadata, upload media files via presigned URLs
- Attach existing creative assets to draft campaigns
- Submit campaign for approval
- PoP reporting per campaign (summary, by-day, by-surface)
- Profile page — organisation, brands, contracts, contacts
- Password change / must_change_password flow
- Responsive advertiser-web layout — hamburger sidebar on narrow screens, no page overflow
- Live LAN preview operational (http://192.168.110.77:3001)

#### Technical Capabilities

- **S-023e:** ProfilePage — 5 organisation/brand/contract/contact APIs, password change via /api/v1/auth/change-password. 13 vitest tests.
- **S-023f:** CampaignCreatePage — /campaigns/new, org/brand/contract selects, POST /campaigns. EditCampaignForm — PATCH /campaigns/{id}. 8 vitest tests.
- **S-023g:** AttachCreativeModal — ready/metadata_only filtering, POST /campaigns/{id}/creatives/attach. ReadinessPanel — flights/placements/creatives checks, submit approval. 13 vitest tests.
- **S-023h:** Russian localization — statusLabel, contactTypeLabel, authProviderLabel, timezoneLabel, surfaceLabel, mediaTypeLabel helpers. All UI text in Russian.
- **S-023i:** Layout.module.css — CSS module replacing inline styles. Hamburger + overlay for <768px. Table overflow-x:auto. timezoneLabel/mediaTypeLabel in CampaignDetailPage.
- **S-026a:** Auth fix — get_user_permissions includes scoped role permissions (commit 7ad4899).
- **S-026b:** LAN preview — docker-compose.preview.yml override, runbook at docs/runbook/local-preview.md.
- **Testing:** 881 Python unit + 245 behavioural + 64 admin-web + 66 advertiser-web = 1,256 total
- **CI:** GitHub Actions — 33 jobs per run, all green on code baseline 38b5255

#### Known Limitations / Not Included

- No advertiser approve/reject — admin-only
- No sales lift / attribution / billing
- No production UX/accessibility audit
- No real KSO player or sidecar
- No real AD/LDAPS (stub 503)
- No ClickHouse / materialized reporting
- No mobile application
- No production monitoring/alerting (Prometheus/Grafana deferred)

#### Rollback Note

No schema changes, no backend changes. Pure frontend:

```bash
git checkout v0.3-advertiser-portal-foundation
```

If tag was pushed, delete:

```bash
git tag -d v0.4-advertiser-self-service-pilot
git push origin :refs/tags/v0.4-advertiser-self-service-pilot
```

#### References

- ADR-001 through ADR-018
- S-023a through S-023i in `docs/architecture/stabilization-tracker.md`
- S-026a, S-026b in `docs/architecture/stabilization-tracker.md`
- CI run #29166816518 (all 33 jobs green)

---

### v0.5-business-portal-complete — Business Portal Complete

**Published.**  Tag created 2026-07-13.

#### Metadata
- **Tag:** v0.5-business-portal-complete
- **Date:** 2026-07-13 (proposed)
- **Commit SHA:** `5c41a6aca7de7af9f3f806469c6ab436403c537a` (last code baseline before docs-only S-042a/S-043)
- **GitHub Actions run:** #29244491388 (conclusion: success, 34/34 jobs)
- **Created by:** P.S. (via Hermes)

#### Business Capabilities

**Admin portal:**
- Memory-only token auth — session restore via refresh cookie, no localStorage
- User management — create local advertiser accounts, activate/deactivate, reset password
- AD settings page — honest stub (503), disabled/configured status reporting
- Advertiser organizations page — org list with search, detail panel (5 tabs: overview, brands, contracts, contacts, users)
- Campaign CRUD — list, detail, create, edit, archive
- Campaign approval inbox — readiness checklist, approve/reject with reason, creative moderation gate
- Creative upload/library — presigned MinIO URLs, SHA-256/server-side validation
- Creative moderation queue — pending_review/approved/rejected filter, approve/reject with reason
- Inventory management UI — stores/surfaces tabs with search, active/inactive toggle
- PoP reporting — summary, by-day, by-surface tables + CSV export

**Advertiser portal:**
- Memory-only token auth — session restore via refresh cookie, no localStorage
- Profile page — organisation, brands, contracts, contacts display
- Password change / must_change_password flow
- Campaign list/detail — overview, flights, placements, creatives, approval status
- Campaign create/edit drafts — org/brand/contract selects, inline editing
- Creative library/upload — metadata create, presigned upload with progress bar
- Attach existing creatives to draft campaigns
- Submit campaign for approval — readiness panel with flights/placements/creatives checks
- Approval/rejection visibility — Russian status labels, rejection reason display
- PoP reporting — summary cards, by-day table, by-surface table + CSV export

**Backend:**
- Dual auth — local_advertiser (bcrypt) + local_break_glass, AD stub (honest 503)
- RBAC/RLS — 23 permission gates, 28 PostgreSQL RLS policies, NOBYPASSRLS runtime role
- Campaign approval workflow — request-approval/approve/reject, status transitions, outbox events
- Creative upload + manual moderation — presigned URLs, server-side validation, moderation queue
- Inventory endpoints — stores/surfaces read/manage
- Advertiser org/brand/contract/contact — 6 endpoints with RBAC/RLS
- PoP reporting/export — JSON endpoints + CSV UTF-8 BOM export
- Audit hardening (S-035a–i) — CORS PATCH, refresh family revoke on replay, async MinIO wrapper, RLS + behavioural proof
- Production config gate (S-030) — CI job, 24 tests, fail on missing/weak secrets in production
- Backup/restore (S-031) — PostgreSQL backup/restore scripts, integration test (5/5), runbook, live drill (4.7MB)

#### Technical Capabilities

- **S-029:** Production gaps triage — 8 categories, 35+ gaps classified P0–P3
- **S-030:** Production CI gate + secrets validation — 24 config tests, CI job
- **S-031:** Backup/restore/DR — PostgreSQL backup/restore scripts + live drill
- **S-031a:** Flaky outbox test stabilization — due-event isolation pattern
- **S-032:** Roadmap resequence — Business Portal before Player per original ТЗ
- **S-033/S-033s:** Admin user management — create/deactivate/reset, RLS/org validation
- **S-034:** AD settings UI — honest connection status, no secrets
- **S-035a–i:** External audit hardening — 9 findings closed (CORS, refresh family, async MinIO, RLS, audit events)
- **S-036:** Creative moderation queue — approve/reject, `creatives.moderate` permission
- **S-037:** Advertising inventory UI — stores/surfaces endpoints + admin-web page
- **S-038:** Campaign approval inbox — readiness gate at approve-time, creative moderation block
- **S-039:** Admin advertisers page — org list + 5-tab detail panel, `advertisers.read`/`contacts.read`
- **S-040:** PoP CSV export — UTF-8 BOM, Russian headers, admin + advertiser download buttons
- **S-041:** Branch/release truth check — main stable at `f4ca15e`, develop clean
- **S-042:** v0.5 readiness review — CONDITIONAL GO with updated tracker
- **S-042a:** Stabilization tracker refresh for v0.5 RC
- **Testing:** 1006 Python unit + 255 behavioural + 71 admin-web + 68 advertiser-web = 1,400+ total
- **CI:** GitHub Actions — 34 jobs per run, all green on code baseline `5c41a6a`

#### Known Limitations / Not Included

- Password reset invite/email flow — deferred
- XLSX export — deferred (CSV done in S-040)
- Malware scan — deferred to v0.7
- Transcoding/renditions — deferred to v0.9
- ClickHouse/reporting warehouse — deferred to v0.8
- Billing/acts/ERP — deferred to v2.6
- Production observability (Prometheus/Grafana) — ✅ done in v0.6
- Real LDAPS/AD integration — ✅ done in v0.6
- MinIO/NATS backup — ✅ done in v0.6
- KSO player/sidecar — deferred to v0.9, out of scope for v0.5
- Real hardware provisioning — out of scope
- Device signature verification — HMAC-SHA256 implemented, device-gateway verification deferred
- Tenant model ADR-018 — proposed, decision pending
- Audit events for campaign approval/creative moderation — P2 follow-up (outbox events exist)
- Full behavioural RLS test for creative_upload_sessions — deferred

#### Rollback Note

Schema additions since v0.4 are forward-compatible. No destructive migrations.
To revert:

```bash
git checkout v0.4-advertiser-self-service-pilot
```

If tag was pushed, delete:

```bash
git tag -d v0.5-business-portal-complete
git push origin :refs/tags/v0.5-business-portal-complete
```

#### References

- ADR-001 through ADR-018
- S-029 through S-042a in `docs/architecture/stabilization-tracker.md`
- CI run #29244491388 (all 34 jobs green)
- S-042 readiness review report

---

### v0.6-production-readiness-foundation — Production Readiness Foundation

**Published.**  Tag created 2026-07-14.

#### Metadata
- **Tag:** v0.6-production-readiness-foundation
- **Date:** 2026-07-14
- **Code baseline:** `fd43791` (S-054 creative_upload_sessions RLS proof, CI #29282222261 green 34/34)
- **Release commit:** `b00772d` (main after S-056 release prep)
- **Predecessor:** v0.5-business-portal-complete (`5c41a6a`)
- **CI:** #29360043628 — 34/34 green

#### Completed Capabilities (S-047…S-054a)

- **Monitoring/observability (S-047):** ✅ Prometheus metrics on control-api + device-gateway (18 metrics), Grafana dashboard (12 panels), 8 alert rules in alerts.yml. AlertManager not provisioned (known limitation, deferred to future ops hardening).
- **Real LDAPS wiring (S-048):** ✅ RealLDAPAuthProvider with ldap3 bind+search, disabled/misconfigured/configured/unavailable modes, safe filter escaping, timeouts, no password logs. `local_advertiser` and `local_break_glass` preserved. Stub returns honest 503 when AD_ENABLED=false.
- **MinIO backup (S-049):** ✅ Python SDK full-bucket backup with SHA-256 manifest, restore with check/dry-run/confirm modes, destructive confirmation gate (REQUIRE_RESTORE_CONFIRMATION=yes), 4 integration tests. Runbook: `docs/runbook/minio-backup-restore.md`.
- **NATS backup policy (S-050):** ✅ Outbox-first recovery policy documented. Recovery diagnostics script. 4 integration tests. Runbook: `docs/runbook/nats-backup-restore.md`.
- **Portal error boundaries (S-051):** ✅ React ErrorBoundary in admin-web + advertiser-web, Russian fallback, JWT sanitisation in dev, 19 vitest tests.
- **Audit events for approval/moderation (S-052):** ✅ campaign.approved/rejected + creative.approved/rejected in same DB transaction, no secrets/storage fields, 10 audit tests.
- **identity.py router decomposition (S-053):** ✅ 2097-line identity.py split into 8 domain routers (users, ad_settings, advertisers, campaigns, creatives, reporting, inventory + common). Identity.py = 40-line aggregator. API paths, permissions, schemas, and business logic unchanged. CI green.
- **creative_upload_sessions behavioural RLS (S-054):** ✅ Full NOBYPASSRLS proof — 5 scenarios (org A sees session, org B cannot, admin bypass, empty scope fail-closed, cross-org count consistency). No policy changes needed.
- **XLSX export decision (S-054a):** ✅ CSV-only for v0.6 (done in S-040, UTF-8 BOM for Excel). XLSX deferred to v0.7/v0.8.

#### Known Limitations

- AlertManager routing not provisioned — rules exist, routing deferred to ops hardening
- AD group→role mapping deferred
- AD auto-provisioning deferred
- Customer AD infrastructure validation required (depends on customer environment)
- Offsite encrypted backup / backup lifecycle monitoring deferred
- Password reset invite/email flow deferred
- Audit retention / log review deferred
- KSO player / sidecar / hardware → v0.9
- Emergency Management backend → v0.7
- Feature flags / staged rollout → v0.7
- Inventory Planning / Forecasting → v0.8
- ClickHouse / reporting warehouse → v0.8
- Billing / acts / ERP → v2.6
- Tenant model ADR-018 → v2.6
- Device signature verification → v2.6

---

### v0.6.1-critical-hotfix — Critical Hotfix (Audit v4)

**Published.**  Tag created 2026-07-14.

#### Metadata
- **Tag:** v0.6.1-critical-hotfix
- **Date:** 2026-07-14
- **Code baseline:** `00060cc` (S-059 critical hotfix, CI #29404001541 green 34/34)
- **Predecessor:** v0.6-production-readiness-foundation (`fd43791`)

#### Closed Findings

- **CRITICAL-1:** LDAPS certificate validation — explicit `ssl.CERT_REQUIRED`, `AD_CA_CERT_FILE` config, `ca_certs_file` passed to `ldap3.Tls`, `ldap3>=2.9.1` in `requirements.txt` + CI
- **CRITICAL-2:** Moderation/approval queue RLS context — `set_rls_context` added to 4 admin endpoints (moderation queue, approve/reject creative, approval queue)

#### Known Limitations (same as v0.6)

- All v0.6 Known Limitations still apply

#### Remediation Plan

- `docs/product/audit-v4-remediation-plan.md` — remaining P1/P2/P3 findings, proposed S-062…S-074 sequence
- **S-062 ✅ done (2026-07-15):** no-op async tests fixed (22 awakened), audit events (7 new tests), dependency truth (minio, PyJWT, CI)
- **S-063…S-073 ✅ done (2026-07-15/16):** All P1/P2 findings closed. P3 UI foundation delivered.
- **S-074 ✅ done (2026-07-16):** Readiness review — GO recommendation for v0.6.2.
- Next milestone: v0.6.2-audit-remediation tag

---

### v0.6.2-audit-remediation — Audit v4 Remediation

**Proposed.**  Tag not yet created.

#### Metadata
- **Tag:** v0.6.2-audit-remediation
- **Date:** 2026-07-16 (proposed)
- **Code baseline:** `90e91cb` (S-073 merge — last code commit on develop)
- **Predecessor:** v0.6.1-critical-hotfix (`00060cc`)
- **CI baseline:** [#29483217520](https://github.com/santanas-dev/retail-media-platform-enterprise/actions/runs/29483217520) — 34/34 green

#### Closed Findings

- **CRITICAL (2/2):** LDAPS cert validation + RLS moderation context — closed in v0.6.1
- **P1 (9/9):** No-op async auth (22 awakened), login/break-glass audit (7 tests), dependency truth, PoP timezone, approval concurrency (FOR UPDATE + behavioural proof), metrics auth, device rate limiting, pagination
- **P2 (9/10):** Redis manifest cache, DB pool tuning, delivery_manifests/pop_events_raw retention, manifest signature, permission-filtered menu, audit log UI, device health workspace, emergency workspace (backend + UI + outbox), inventory domain gap analysis (implementation S-075+)
- **P3 (1/7 foundation):** Design tokens (60+ CSS properties), shared components (Button, StatusBadge, PageHeader), 5 pages migrated, admin login default → AD. Full WCAG audit + remaining pages deferred.
- **Architecture:** device-gateway 403 leak fixed, _scope_ids try/finally guarantee, MinIO provisioning documented

#### Known Limitations (unchanged from v0.6 + new deferred)

- Inventory domain implementation → S-075+
- Full WCAG audit, remaining UI pages migration → v0.7
- i18n strategy → v0.7
- 152-ФЗ compliance docs → v0.7
- pop-ingestor service extraction → v0.8
- All v0.6 Known Limitations still apply (KSO, ClickHouse, billing, etc.)

#### Release Docs

- `docs/product/audit-v4-remediation-readiness-review.md` — full status matrix, GO recommendation

---

## Future Branch: v2.6 Next Branch

v2.6 — дальнейшее развитие портала после закрытия первого ТЗ (v2.5).
**Не входит в v0.2.** Следующий release tag НЕ создаётся сейчас.

Будущие релизы после текущего первого ТЗ могут включать v2.6 milestones.

### Направления v2.6

- Attribution & Sales Lift
- Self-service advertiser cabinet
- Competitive Separation
- Store-level audience targeting
- Finance contract/invoicing integration
- Programmatic extension point (deferred)
- Dynamic creative MVP (deferred)
- Mobile field ops MVP (deferred)
- A/B lift metrics
- Third-party DOOH measurement/accreditation stub (deferred)

### P0 Foundation Decision

Перед реализацией v2.6 обязателен explicit P0 decision по tenant model.
ADR-018 (`docs/architecture/adr/ADR-018-tenant-model-for-next-branch.md`)
создан со статусом Proposed.

### Документация

- TZ: `docs/product/requirements/TZ_Retail_Media_Platform_v2_6_Next_Branch_2026-07-11.docx`
- README: `docs/product/requirements/README.md`
- Roadmap: `docs/product/roadmap-s020-2026-07-10.xlsx` (строки v2.6)

### Не входит в v2.6

- KSO player / sidecar — следующий release
- Android TV, LED/ESL, price checker — deferred
- ClickHouse / materialized reporting — deferred
- Advertiser portal — shipped (v0.3‑advertiser‑portal‑foundation)
