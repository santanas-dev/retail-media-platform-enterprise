# Production Gaps Triage — Retail Media Platform Enterprise

| **Created:** 2026-07-11
| **Version:** 1.0
| **Status:** active
| **Branch:** develop

## A. Current Baseline

| Parameter | Value |
|-----------|-------|
| **Latest release** | v0.4-advertiser-self-service-pilot |
| **Code baseline** | 38b5255b1600ec3f5e960bcbadfa73f1b7922e22 |
| **Branch model** | main (stable) / develop (active integration) |
| **Live preview** | http://192.168.110.77:3001 (advertiser-web), :3000 (admin-web) |
| **Tests** | 881 Python unit + 245 behavioural + 64 admin-web + 66 advertiser-web = 1,256 total |
| **CI** | GitHub Actions — 33 jobs, all green on code baseline |

### What is pilot-ready (v0.4)

- Advertiser self-service: login → campaigns CRUD → creatives → attach → submit approval
- Admin campaign management: full CRUD, approval workflow, creative upload
- PoP reporting: summary, by-day, by-surface
- Delivery pipeline: outbox → NATS → manifest → device-gateway HTTP
- Dual auth: local_advertiser + local_break_glass (bcrypt), AD stub (503)
- RBAC/RLS: two-layer defence (app permissions + 28 PostgreSQL RLS policies)
- Responsive advertiser-web: desktop + tablet (hamburger sidebar)
- Live LAN preview with runbook

### What is NOT production-ready

See gap categories below. No gap is production-ready — each requires explicit work.

---

## B. Production Gap Categories

### 1. Auth / Identity

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| Real LDAPS/AD integration | P1 | Staff login without test credentials | Auth unavailable without LDAPS — blocks real admin | AD controller provisioning | v0.6 |
| Password reset / invite flow | P1 | Advertiser self-onboarding | Manual user creation blocks scale | Email/SMS integration | v0.6 |
| Account lockout / expiry | P2 | Security baseline | Brute-force on local accounts | Login rate limiting (S-010, done) | v0.6 |
| MFA (TOTP/WebAuthn) | P3 | Security hardening | Not required for pilot | Identity provider capability | v1.0+ |
| Session/device management | P2 | User control over active sessions | Session hijack without detection | Token blacklist/revocation | v0.8 |

### 2. UI / UX / Accessibility

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| Production UX audit | P1 | Confidence for customer demo | Pilot UI may have papercuts | Design system review | v0.5 |
| Mobile 390px validation | P2 | Field operator use case | Narrow screens untested | Responsive layout (S-023i basis) | v0.7 |
| Accessibility audit (WCAG AA) | P2 | Compliance, inclusivity | Keyboard/focus/contrast gaps | axe-core, manual review | v0.7 |
| Design system cleanup | P2 | Consistency across portals | Inline styles still in page components | CSS modules pattern (S-023i) | v0.7 |
| Date/time picker localization | P3 | Russian UX | Native browser widget shows English | Custom or library picker | v0.7 |

### 3. Creative Moderation / Media Pipeline

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| Manual moderation | P1 | Quality control before live | Unmoderated content on displays | Admin-web moderation UI | v0.7 |
| Malware scan | P1 | Security — uploaded files | Malicious files in storage | ClamAV or cloud scanning | v0.7 |
| Transcoding / renditions | P2 | Player compatibility | Wrong format → playback failure | FFmpeg or cloud transcoding | v0.9 |
| CDN / edge delivery | P2 | Performance at scale | Latency for remote stores | CDN integration (CloudFront/etc) | v1.0+ |
| Orphan cleanup | P2 | Storage cost | Unreferenced files accumulate | Periodic sweep job | v0.7 |
| Format/size/duration policy | P2 | Operational control | Uploads without limits | Configurable policy engine | v0.7 |

### 4. Reporting / Analytics

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| Export CSV/XLSX/PDF | P1 | Customer-facing reports | No offline report delivery | Report templating engine | v0.8 |
| ClickHouse / reporting warehouse | P1 | Performance at scale | PostgreSQL analytical queries degrade OLTP | ClickHouse deployment + schema | v0.8 |
| Sales lift / attribution | P2 | Business value proof | No revenue impact measurement | Receipt data + PoP pipeline | v2.6 |
| Billing-grade reconciliation | P1 | Revenue assurance | Discrepancies → disputes | Immutable PoP + audit trail | v0.8 |
| Freshness / SLA monitoring | P2 | Operational confidence | Stale reports go unnoticed | Monitoring + alerting | v0.8 |

### 5. Production Operations

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| Monitoring / alerting | P0 | Incident detection | Silent failures in production | Prometheus + Grafana + AlertManager | v0.5 |
| Backup / restore / DR | P0 | Data safety | Data loss on failure | pg_dump/pg_basebackup + MinIO mirroring | v0.5 |
| Secrets management | P0 | Security baseline | Hardcoded secrets in config | HashiCorp Vault or env-based hardening | v0.5 |
| Production CI gate | P0 | Quality gate | Broken code on production | Behavioural PostgreSQL gate (exists), add production config validation | v0.5 |
| Load / performance tests | P1 | Scalability confidence | 40K devices target unproven | Locust/k6 + production-like env | v0.8 |
| Audit retention / log review | P1 | Compliance, forensics | No historical audit trail | Audit table + retention policy | v0.5 |

### 6. Device / Manifest / Player

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| Real KSO player / sidecar | P1 | First channel live | No real device playback | KSO hardware access + Linux agent | v0.9 |
| Manifest signature verification (device) | P1 | Integrity on device | Tampered manifest accepted | HMAC-SHA256 signing (S-021 done), verify on device | v0.9 |
| Device provisioning lifecycle | P2 | Device fleet management | Manual device registration | Device registration API + UI | v0.9 |
| Token rotation / revocation | P2 | Security | Compromised device token | JWT revocation list or short-lived tokens | v0.9 |
| Offline / fail-closed validation | P1 | Safety | Display shows stale/unauthorised content | Kill-switch + offline TTL (simulator proven) | v0.9 |

### 7. Finance / Commercial

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| Billing | P2 | Revenue collection | Manual billing → errors | Contract + campaign data | v2.6 |
| Acts / closing documents | P2 | Legal compliance | No formal financial documents | Billing → acts pipeline | v2.6 |
| Invoicing / ERP integration (1C) | P3 | Automation | Manual data entry | External API contract | v2.6 |

### 8. Tenancy / v2.6 Readiness

| Gap | Severity | Value | Risk | Dependency | Milestone |
|-----|----------|-------|------|------------|-----------|
| ADR-018 tenant model decision | P0 | Architecture foundation | Wrong model → costly rewrite | Stakeholder decision | v0.5 (decision) |
| Competitor blocking | P2 | Advertiser requirement | Brand conflict on same screen | Tenant model + targeting | v2.6 |
| Audience targeting | P3 | Premium feature | Complex rules engine | Tenant model + inventory | v2.6 |
| Attribution roadmap | P2 | Business model validation | No ROI measurement | PoP pipeline + receipt data | v2.6 |

---

## C. Prioritization Matrix

| Rank | Gap | P-level | Rationale |
|------|-----|---------|-----------|
| 1 | Production CI gate | P0 | **Blocks all further work.** No production gate → no confidence in any release. |
| 2 | Secrets management | P0 | Security baseline. Hardcoded secrets unacceptable. |
| 3 | Backup / restore / DR | P0 | Data safety. No backups → existential risk. |
| 4 | Monitoring / alerting | P0 | Incident detection. Silent failures → undetected downtime. |
| 5 | Audit retention | P1 | Compliance + debugging. S-010 login attempts table exists — extend. |
| 6 | ADR-018 tenant model decision | P0 | Architecture fork. v2.6 blocks on this. Must decide before any v2.6 work. |
| 7 | Real LDAPS/AD integration | P1 | Staff cannot login without test credentials. |
| 8 | Password reset / invite flow | P1 | Advertiser self-onboarding blocked without it. |
| 9 | Manual moderation | P1 | Unmoderated content on displays. |
| 10 | Malware scan | P1 | Uploaded files unverified. |
| 11 | Manifest signature verification (device) | P1 | Manifest integrity at edge. |
| 12 | Offline fail-closed validation | P1 | Safety — stale content on display. |
| 13 | Real KSO player | P1 | First channel — no playback without it. |
| 14 | Reporting export | P1 | Customer-facing deliverable. |
| 15 | ClickHouse foundation | P1 | PostgreSQL analytical queries degrade OLTP. |
| 16 | Billing-grade reconciliation | P1 | Revenue disputes without it. |

---

## D. Recommended Next Milestones

### v0.5 — Production Readiness Foundation (P0 gates)

**Rationale:** Close the P0 gaps that block all further work. No features — pure operations.

| Item | Action |
|------|--------|
| Production CI gate | Add `ENVIRONMENT=production` validation to CI. Fail on missing secrets, weak keys, non-HTTPS origins. |
| Secrets management | Enforce `SECRET_*` env vars in production. Document rotation procedure. Add `.env.example` with production template. |
| Backup / restore | `pg_dump` cron + MinIO mirroring. Runbook with restore test procedure. |
| Monitoring baseline | Prometheus metrics on control-api + device-gateway. Grafana dashboard (4 panels: API latency, error rate, DB pool, NATS queue). |
| Audit retention | Extend `login_attempts` to general audit table. Retention policy (90 days dev, 365 production). Log review runbook. |
| ADR-018 decision | Stakeholder meeting. Document decision (single-retailer vs multi-retailer/syndication). Update ADR-018 status: Accepted or Rejected. |

**Deliverable:** Production CI green on develop. Runbook tested with restore drill.

### v0.6 — Identity Hardening

**Rationale:** Real staff access + advertiser self-onboarding.

| Item | Action |
|------|--------|
| LDAPS/AD | Wire real AD adapter. Replace stub 503. Test with staging AD. |
| Password reset | Email-based reset token flow. Rate-limited. Audit trail. |
| Advertiser invite | Admin sends invite → advertiser sets password → must_change_password. |
| Account lockout | Extend S-010 rate limiting: 5 attempts/15min → lock (30min) → unlock. |

### v0.7 — Creative Moderation + UI Polish

**Rationale:** Quality control before content goes live.

| Item | Action |
|------|--------|
| Manual moderation | Admin-web: moderation queue, approve/reject with reason. |
| Malware scan | ClamAV on upload complete. Quarantine on detection. |
| Orphan cleanup | Periodic sweep: unreferenced assets > 30 days → delete. |
| Media policy | Configurable limits: file size, resolution, duration, format whitelist. |
| Production UX audit | Keyboard navigation, focus indicators, contrast check. 390px mobile validation. |
| Date/time picker | Replace native browser widget with Russian-localized component. |

### v0.8 — Reporting Export + Analytics Foundation

**Rationale:** Customer-facing reports + performance at scale.

| Item | Action |
|------|--------|
| CSV/XLSX export | Campaign + PoP export endpoints. Streaming download. |
| ClickHouse | Deployment + schema mirror. PoP data replication. |
| Reporting SLA | Freshness monitoring. Alert on stale data. |
| Billing-grade reconciliation | Immutable PoP events. Hash-chain or append-only audit. |

### v0.9 — Device / Player Readiness

**Rationale:** First channel goes live. Device security + playback.

| Item | Action |
|------|--------|
| Real KSO player | Linux agent (Chromium/Electron). Manifest fetch + apply loop. Sidecar for health. |
| Manifest verification (device) | HMAC-SHA256 verify on player side before apply. Reject on mismatch. |
| Offline fail-closed | Kill-switch levels (4, from ADR-013 simulator). Offline TTL expiry → blank screen. |
| Device provisioning | Registration API + admin-web UI. Token generation. Status monitoring. |

---

## E. Recommendation

### Close first (v0.5, now)
1. **P0 operations gates** — CI, secrets, backups, monitoring, audit. These block everything.
2. **ADR-018 tenant decision** — P0 architecture fork. Must decide before v2.6.

### Close next (v0.6–v0.7, after v0.5)
3. **Identity hardening** — real LDAPS, password reset, advertiser invite.
4. **Creative moderation** — manual review, malware scan, media policy.

### Defer to v0.8–v0.9
5. **Reporting export + ClickHouse** — needed for scale but not for first live channel.
6. **Device/player readiness** — requires KSO hardware access.

### v2.6+ (after ADR-018 decided)
- Billing / acts / ERP
- Sales lift / attribution
- Competitor blocking
- Audience targeting
- Mobile field ops

### Not in current TZ (v2.6/v3.0)
- Programmatic extension (OpenRTB)
- Dynamic creative templating
- Third-party DOOH measurement
- Android TV / LED / ESL / Price Checker

---

## References

- ADR-001 through ADR-018
- `docs/architecture/stabilization-tracker.md`
- `docs/architecture/release-versioning.md`
- `docs/product/roadmap-s020-2026-07-10.xlsx`
- v0.4-advertiser-self-service-pilot tag (38b5255)
