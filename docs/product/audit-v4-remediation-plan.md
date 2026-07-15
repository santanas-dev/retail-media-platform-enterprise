# External Audit v4 — Remediation Plan

| **Created:** 2026-07-14 |
| **Status:** active |
| **Branch:** develop |
| **Predecessor:** S-059/S-060 — Critical findings closed in v0.6.1 |

## 1. Context

External audit v4 was performed against the v0.6 Production Readiness
Foundation codebase.  Two Critical findings were identified and closed
in the v0.6.1 hotfix (S-059/S-060).  This document outlines the
remaining High / Medium / Low findings and proposes a phased
remediation sequence.

## 2. Closed — v0.6.1 Critical Hotfix

| ID | Finding | Severity | S-ticket | Status |
|----|---------|----------|----------|--------|
| CRITICAL-1 | LDAPS certificate validation not enforced | Critical | S-059 | ✅ Closed |
| CRITICAL-2 | Moderation/approval queue missing RLS context | Critical | S-059 | ✅ Closed |

**Tag:** v0.6.1-critical-hotfix → `00060cc`
**CI:** #29404001541 — 34/34 green

## 3. Remaining Findings by Priority

### P1 — Next Remediation Block (blocks production confidence)

| # | Finding | Impact | Proposed Ticket |
|---|---------|--------|-----------------|
| P1-1 | ✅ No-op async auth tests — fixed: 22 tests awakened with IsolatedAsyncioTestCase + guard | False confidence in auth stack | S-062 |
| P1-2 | ✅ Audit events for login/logout/break-glass — 7 new tests, no secrets in details | Compliance gap, no incident response data | S-062 |
| P1-3 | ✅ ldap3/minio in requirements; CI aligned; PyJWT bounds unified ≥2.12.0 | Dependency drift, unreliable CI | S-062 |
| P1-4 | ✅ PoP by-day timezone correctness — groups by local store day (Store.tz → Branch.tz → Moscow) | Billing/reporting accuracy | S-063 |
| P1-5 | ✅ approve_campaign race condition — SELECT FOR UPDATE makes concurrent approve/reject atomic; 7 behavioural concurrency tests | Data integrity, double-approval | S-064 |
| P1-6 | /metrics exposure hardening — metrics endpoint lacks auth/rate-limit | Information disclosure | S-065 |
| P1-7 | No rate limiting on /device/manifest/latest and /pop/batch | DoS surface on device-facing endpoints | S-065 |
| P1-8 | No pagination on large lists: stores, surfaces, campaigns, moderation queue, approval queue | UI degradation at scale, N+1 risk | S-066 |

### P2 — Production Hardening

| # | Finding | Impact | Proposed Ticket |
|---|---------|--------|-----------------|
| P2-1 | No Redis cache for manifest — every device request hits PostgreSQL | Latency at scale (40K devices) | S-067 |
| P2-2 | DB pool configuration not production-tuned | Connection exhaustion under load | S-068 |
| P2-3 | delivery_manifests table — no retention/purge strategy | Unbounded growth | S-068 |
| P2-4 | pop_events_raw — no partitioning/retention before ClickHouse | Unbounded growth, analytical query degradation | S-068 |
| P2-5 | Manifest signature not persisted / threat model not documented | Integrity verification gap | S-067 |
| P2-6 | Admin menu not filtered by user permissions | UX confusion, security-relevant | S-069 |
| P2-7 | No audit log UI — audit_events_operational write-only | Operators can't review audit trail | S-069 |
| P2-8 | No device/fleet health UI | Operational blindness | S-070 |
| P2-9 | No emergency workspace / kill-switch UI | ADR-013 architecture proven but no operator UI | S-071 |
| P2-10 | Inventory domain not implemented per ТЗ §6.3 (airtime, forecasting, conflicts, sold-out) | Core domain gap | S-072 |
| P2-11 | 152-ФЗ operational docs/procedures not prepared | Compliance risk | S-073 |

### P3 — UI / Product Maturity

| # | Finding | Impact | Proposed Ticket |
|---|---------|--------|-----------------|
| P3-1 | No design system tokens/components | Inconsistent UI, slow iteration | S-073 |
| P3-2 | Inline-style sprawl in page components | Maintenance burden | S-073 |
| P3-3 | Contrast / accessibility issues | WCAG non-compliance | S-073 |
| P3-4 | Missing h1 / page landmarks | Screen-reader navigation | S-073 |
| P3-5 | Missing hover/focus states | Keyboard accessibility | S-073 |
| P3-6 | Admin login defaults to AD provider (unavailable → confusing UX) | First-login friction | S-073 |
| P3-7 | No i18n strategy (Russian hardcoded) | Future localisation blocked | S-073 |

### Architecture / Tech Debt (low severity, high leverage)

| # | Finding | Impact | Proposed Ticket |
|---|---------|--------|-----------------|
| A-1 | pop-ingestor shares control-api; architectural drift from separate service | Deployment coupling | S-074 review |
| A-2 | ADR-003 device identity issuance not implemented as designed | Spec/code gap | S-074 review |
| A-3 | device-gateway 403 leaks internal error details | Information disclosure | S-065 |
| A-4 | JsonFormatter.SANITIZED_FIELDS defined but unused | Dead code | S-065 |
| A-5 | MinIO service account provisioning not automated | Manual ops step | S-068 |
| A-6 | authz _scope_ids latent issue (scope=None fallback) | Edge-case authz bypass | S-062 |
| A-7 | Old ТЗ extraction integrity — some sections from DOCX not verified | Traceability gap | S-074 review |

## 4. Proposed S-Ticket Sequence

```
S-062 ─► ✅ Auth/test/dependency truth (DONE)
          ├─ ✅ No-op async test fix — 4 classes → IsolatedAsyncioTestCase, 1 AST guard
          ├─ ✅ Login/logout/break-glass audit events — 7 new tests
          ├─ ✅ Requirements/CI dependency truth — minio added, PyJWT aligned, CI unified
          └─ → _scope_ids latent issue deferred to S-074 readiness review

S-063 ─► ✅ PoP timezone correctness (DONE)
          └─ ✅ By-day grouping uses store local day: Store.tz → Branch.tz → Moscow

S-064 ─► Approval concurrency + audit consistency
          ├─ approve_campaign race condition
          └─ Audit event idempotency

S-065 ─► Metrics/rate-limit/device-gateway hardening
          ├─ /metrics auth/rate-limit
          ├─ Rate limiting for /device/manifest/latest + /pop/batch
          ├─ device-gateway 403 leakage fix
          └─ JsonFormatter.SANITIZED_FIELDS cleanup

S-066 ─► Pagination foundations
          └─ Paginated stores, surfaces, campaigns, moderation queue, approval queue

S-067 ─► Manifest performance + Redis cache
          ├─ Redis cache for manifest GET
          └─ Manifest signature persistence / threat model

S-068 ─► DB pool + retention strategy
          ├─ DB pool production tuning
          ├─ delivery_manifests retention
          ├─ pop_events_raw partitioning/retention
          └─ MinIO service account provisioning

S-069 ─► Admin UI: audit log + permission-filtered menu
          ├─ Audit log read-only UI
          └─ Menu filtering by user permissions

S-070 ─► Fleet/device health workspace (plan or MVP)
          └─ Device status dashboard, last-seen, health indicators

S-071 ─► Emergency workspace (plan or MVP)
          └─ Kill-switch UI, pause/immediate/emergency controls

S-072 ─► Inventory domain gap analysis and plan
          └─ ТЗ §6.3: airtime, forecasting, conflicts, sold-out, rules

S-073 ─► UI design-system / a11y foundation
          ├─ Design tokens + component library start
          ├─ Accessibility audit fixes (contrast, landmarks, focus)
          └─ i18n strategy document

S-074 ─► v0.6.2 / v0.7 readiness review
          ├─ pop-ingestor architecture review
          ├─ ADR-003 device identity gap
          ├─ ТЗ extraction integrity
          └─ Go/no-go for v0.7
```

## 5. What Is NOT Blocked by This Audit

- KSO player / sidecar / hardware — separate v0.9 milestone
- Android TV / LED / ESL — deferred
- ClickHouse / reporting warehouse — v0.8
- Billing / ERP — v2.6
- Tenant model ADR-018 — v2.6
- v2.6 business expansion — separate branch

## 6. Production Blocker Assessment

| Blocker | Status |
|---------|--------|
| CRITICAL-1 (LDAPS cert) | ✅ Closed v0.6.1 |
| CRITICAL-2 (RLS context) | ✅ Closed v0.6.1 |
| P1-1…P1-8 (next block) | 🟡 Not blocking pilot with <100 devices; blocking production at scale |
| P2-1…P2-11 (hardening) | 🟡 Not blocking internal pilot; blocking customer-facing production |
| P3-1…P3-7 (UI/polish) | 🟢 Not blocking; quality-of-life |

**Recommendation:** S-062 through S-066 should be completed before
any production deployment with real customer data.  S-067 through
S-073 can be interleaved or deferred to v0.7 depending on pilot
feedback.

## 7. References

- `docs/architecture/stabilization-tracker.md` — S-059, S-061, remediation backlog
- `docs/product/production-gaps-triage.md` — audit v4 section
- `docs/architecture/release-versioning.md` — v0.6.1 published, v0.6.2/v0.7 planned
- `docs/product/roadmap-s020-2026-07-10.xlsx` — audit remediation rows
- v0.6.1-critical-hotfix tag (`00060cc`)
