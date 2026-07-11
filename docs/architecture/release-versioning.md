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
| `v0.3-player-pilot-mvp` | Real KSO player/sidecar integration, device manifest delivery, PoP ingestion |

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
