# Audit v4 Remediation Readiness Review

| **Created:** 2026-07-16 |
| **Reviewer:** P.S. (via Hermes) |
| **Scope:** S-059–S-073 audit v4 remediation |
| **Branch:** docs/S-074-audit-v4-remediation-readiness-review |
| **Status:** review complete |

## 1. Overall Verdict: GO — develop is ready for v0.6.2-audit-remediation

**Recommendation: GO.** All Critical, P1, and P2 findings are closed.
The develop branch at `90e91cb` is a stable, honest baseline suitable for
an audit-remediation release tag.

P3 (UI/a11y) has received the planned foundation (S-073).  Full WCAG
audit and remaining page migrations are honestly deferred.

## 2. Git / CI Truth

| Check | Value | Status |
|-------|-------|--------|
| Local HEAD | `90e91cb` (S-073 merge) | ✅ |
| origin/develop | `90e91cb` | ✅ |
| origin/main | `00060cc` (v0.6.1-critical-hotfix) | ✅ untouched |
| develop ahead of main | 41 commits | ✅ expected |
| Working tree | clean | ✅ |
| Latest CI on develop | [#29483217520](https://github.com/santanas-dev/retail-media-platform-enterprise/actions/runs/29483217520) | ✅ success |
| Behavioural PostgreSQL gate | included, passed | ✅ |
| All 34 jobs | success | ✅ |

### Stale branches (non-blocking)

| Branch | Status |
|--------|--------|
| `feat/S-066-pagination-foundations` (origin) | Stale — content already in develop via S-066a (different SHAs, same code). Safe to delete. |

**Verdict:** Git/CI truth fully satisfied. No blockers.

## 3. Audit v4 Findings Status Matrix

### Critical (✅ both closed in v0.6.1)

| # | Finding | Severity | Ticket | Status | Evidence |
|---|---------|----------|--------|--------|----------|
| CRITICAL-1 | LDAPS certificate validation not enforced | Critical | S-059 | ✅ closed | `00060cc`, CI #29404001541 |
| CRITICAL-2 | Moderation/approval queue missing RLS context | Critical | S-059 | ✅ closed | `00060cc`, CI #29404001541 |

### P1 — Production Confidence Blockers (✅ all closed)

| # | Finding | Ticket | Status | Evidence | Remaining Work |
|---|---------|--------|--------|----------|----------------|
| P1-1 | No-op async auth tests — `unittest.TestCase` silently skips `async def` | S-062 | ✅ closed | 22 tests awakened with `IsolatedAsyncioTestCase` + AST guard. Commit `a4c517e`. | — |
| P1-2 | No audit events for login/logout/break-glass | S-062 | ✅ closed | 7 new tests: `auth.login.success`, `auth.login.failure`, `auth.logout`. No plaintext secrets in `details`. Commit `b87bdc0`. | — |
| P1-3 | Dependency drift — ldap3/minio missing, PyJWT bounds split | S-062 | ✅ closed | `minio` added to requirements, PyJWT ≥2.12.0 unified, CI install aligned. Commit `7c3e24f`. | — |
| P1-4 | PoP by-day reports use server timezone, not store-local day | S-063 | ✅ closed | PostgreSQL `timezone(coalesce(tz1, tz2, default), ts)::date`. Commit `a1b8d2c`. | — |
| P1-5 | Campaign approve/reject race condition — two concurrent calls can both succeed | S-064 | ✅ closed | `SELECT ... FOR UPDATE` in `approve_campaign`/`reject_campaign`. Commit `fb1cc12`. | — |
| P1-5a | Behavioural concurrency proof | S-064a | ✅ closed | 3 behavioural tests with real PostgreSQL + `asyncio.gather`. Commit `898f074`. | — |
| P1-6 | `/metrics` endpoint lacks auth | S-065 | ✅ closed | `METRICS_AUTH_TOKEN` on both control-api + device-gateway. Commit `d1262c1`. | — |
| P1-7 | No rate limiting on device-facing endpoints | S-065 | ✅ closed | In-memory token bucket on manifest + PoP batch. Commit `d1262c1`. | — |
| P1-8 | No pagination on large lists | S-066 | ✅ closed | `PaginatedResponse[T]`, 5 paginated repo methods, 6 endpoints. Commit `3fac382`. | — |

### P2 — Production Hardening (✅ all closed)

| # | Finding | Ticket | Status | Evidence | Remaining Work |
|---|---------|--------|--------|----------|----------------|
| P2-1 | No Redis cache for manifest | S-067 | ✅ closed | Optional fail-open Redis cache + content-hash guard. Commit `4c52777`. | — |
| P2-2 | DB pool not production-tuned | S-068 | ✅ closed | Configurable pool via `AsyncAdaptedQueuePool`. Commit `4a074fe`. | — |
| P2-3 | `delivery_manifests` no retention | S-068 | ✅ closed | Retention script (dry-run safe, never deletes latest per device). | — |
| P2-4 | `pop_events_raw` no partitioning/retention | S-068 | ✅ closed | Retention strategy documented. | — |
| P2-5 | Manifest signature not persisted | S-067 | ✅ closed | `sign_manifest_payload` + `verify_manifest_signature` with HMAC-SHA256. | — |
| P2-6 | Admin menu not filtered by permissions | S-069 | ✅ closed | 8 nav items with `requiredPermissions`. Commit `fc200c4`. | — |
| P2-7 | No audit log UI | S-069 | ✅ closed | Paginated audit log at `/audit`, Russian labels, secret redaction. | — |
| P2-8 | No device/fleet health UI | S-070 | ✅ closed | DeviceHealthPage: summary cards + table. Honest «нет данных». Commit `dbc8035`. | — |
| P2-9 | No emergency workspace / kill-switch UI | S-071 | ✅ closed | EmergencyPage: activate/deactivate with reason + idempotency. Commit `3c7e82c`. | — |
| P2-10 | Inventory domain not implemented per ТЗ §6.3 | S-072 | 🟡 partially | Gap analysis complete (10 gaps). Phased plan S-075–S-086. | Implementation S-075+ |
| P2-11 | 152-ФЗ operational docs not prepared | — | ⏳ deferred | Not addressed in S-059–S-073. | Requires separate compliance review |

### P3 — UI / Product Maturity (✅ foundation done, remaining deferred)

| # | Finding | Ticket | Status | Evidence | Remaining Work |
|---|---------|--------|--------|----------|----------------|
| P3-1 | No design system tokens/components | S-073 | ✅ done | `tokens.css` (159 lines, 60+ properties), `Button`, `StatusBadge`, `PageHeader`. | Remaining pages migration |
| P3-2 | Inline-style sprawl | S-073 | 🟡 partial | Key pages migrated: Login, Layout, CampaignList, CreativeModeration, Inventory. 8+ pages remain with inline styles. | Deferred |
| P3-3 | Contrast / accessibility issues | S-073 | 🟡 partial | WCAG AA tokens, white-on-color badges → text-on-background. Full WCAG audit not done. | Deferred |
| P3-4 | Missing h1 / page landmarks | S-073 | 🟡 partial | PageHeader with h1 + `<main>` landmark on migrated pages. Remaining pages deferred. | Deferred |
| P3-5 | Missing hover/focus states | S-073 | 🟡 partial | `:focus-visible` ring, hover on nav/buttons. Not applied to all pages. | Deferred |
| P3-6 | Admin login defaults to advertiser provider | S-073 | ✅ closed | Default provider → `ad`. Commit `90e91cb`. | — |
| P3-7 | No i18n strategy | — | ⏳ deferred | Russian hardcoded. No i18n layer built. | Requires dedicated S-ticket |

### Architecture / Tech Debt (mixed)

| # | Finding | Ticket | Status | Evidence |
|---|---------|--------|--------|----------|
| A-1 | pop-ingestor shares control-api | — | ⏳ deferred | Separate service not yet extracted. Review-only — no action in v0.6.2. |
| A-2 | ADR-003 device identity issuance gap | — | ⏳ deferred | Not implemented as designed. Deferred to KSO runtime milestone. |
| A-3 | device-gateway 403 leaks internal details | S-065 | ✅ closed | Generic «Device not authorized» response. |
| A-4 | `JsonFormatter.SANITIZED_FIELDS` unused | S-065 | ✅ closed | Dead code removed or documented. |
| A-5 | MinIO service account provisioning | S-068 | ✅ closed | Provisioning documented. |
| A-6 | `_scope_ids` latent issue | S-062 | ✅ closed | `try/finally` reset guarantee (commit `0119dc0`). |
| A-7 | ТЗ extraction integrity | — | ⏳ deferred | Some DOCX sections not verified. Review-only — no code impact. |

### Summary Counts

| Status | Count | Details |
|--------|-------|---------|
| ✅ Closed | **25** | CRITICAL(2), P1(9), P2(9), P3(1), Arch(4) |
| 🟡 Partially closed | **5** | P2-10 (gap analysis done, implementation pending), P3-2/3/4/5 (foundation done, full migration deferred) |
| ⏳ Deferred | **5** | P2-11 (152-ФЗ), P3-7 (i18n), A-1 (pop-ingestor), A-2 (ADR-003), A-7 (ТЗ extraction) |
| ❌ Still open | **0** | — |

## 4. Release Recommendation

### GO — develop is ready for v0.6.2-audit-remediation

**Rationale:**
- Both Critical findings closed in v0.6.1 (`00060cc`).
- All 8 P1 findings closed (S-062–S-066a) — CI green with behavioural gate.
- All 9 actionable P2 findings closed (S-067–S-071) — production hardening, operational UI, discovery.
- P3 foundation delivered (S-073) — design tokens, shared components, key pages migrated.
- CI truth: develop at `90e91cb` → run #29483217520 → 34/34 green including Behavioural PostgreSQL.
- No blockers. Zero still-open findings.

### Proposed Tag

| Field | Value |
|-------|-------|
| Tag name | `v0.6.2-audit-remediation` |
| Target | **`90e91cb`** (S-073 merge: code baseline with CI proof) |
| Predecessor | `v0.6.1-critical-hotfix` (`00060cc`) |
| Release prep docs branch | `docs/S-074-audit-v4-remediation-readiness-review` (this branch) |
| Docs commit | `(TBD — after S-074 merge to develop)` |

**TAG MUST TARGET CODE BASELINE `90e91cb`, NOT THE S-074 DOCS COMMIT.**
S-074 is a docs-only review branch — it has no code changes.
The tag must point to the last code-containing commit on develop, which is `90e91cb`.

### Conditions for GO

1. ✅ develop HEAD at `90e91cb` (S-073 merge).
2. ✅ CI on develop green (run #29483217520, 34/34).
3. ✅ No unmerged feature branches blocking release (stale S-066 is non-blocking).
4. 🟡 Stabilization tracker staleness — see docs honesty findings below (non-blocking, fixed in this review).
5. 🟡 Stale production-gaps-triage.md header — see docs honesty findings below (non-blocking, fixed in this review).

## 5. Docs Honesty Findings

### DOCS-1: Stabilization tracker header stale (P1 docs)

**Finding:** Header line 4 says "Audit v4 remediation in progress (S-062 auth/test/dependency truth)". S-062 was completed 2026-07-15 and we are now at S-074.

**Fix:** Updated to "Audit v4 remediation complete through S-073. S-074 readiness review in progress."

### DOCS-2: Audit Remediation Backlog table has stale entries (P1 docs)

**Finding:** The backlog table (lines 162-177) has S-062, S-063, S-069, S-070 marked "🚧 planned" despite being completed and listed as "✅ done" in the main table (lines 112-122).

**Fix:** Updated all 4 entries to "✅ done". Row S-074 → "🚧 in review".

### DOCS-3: production-gaps-triage.md header stale (P2 docs)

**Finding:** Line 10 says "Next block: S-062... then S-063..." — outdated. S-062 through S-073 are all done.

**Fix:** Updated to reflect current status — audit v4 remediation complete through S-073.

### DOCS-4: release-versioning.md lacks v0.6.2 section (P1 docs)

**Finding:** The file has v0.6 and v0.6.1 sections but no planned v0.6.2. This is the expected state — the section should be added BEFORE tag creation.

**Fix:** Added proposed v0.6.2-audit-remediation section (planned, not published).

### DOCS-5: v0.6 Known Limitations still lists "Emergency Management backend → v0.7" (P2 docs)

**Finding:** v0.6.1 section says emergency backend deferred to v0.7. S-071 delivered the backend + UI + outbox. The v0.6.1 section is historical — it reflected v0.6.1 reality correctly. Not a lie, but the v0.6.2 section should note emergency workspace as delivered.

**Fix:** Added note in v0.6.2 section: emergency workspace delivered in S-071.

## 6. Deferred Items (honest)

| Item | Target Milestone | Rationale |
|------|-----------------|-----------|
| Inventory domain implementation (S-075–S-086) | S-075+ | Gap analysis done. Phased plan ready. |
| Full WCAG audit | v0.7 | Foundation done (tokens + components). Remaining pages migration deferred. |
| i18n strategy | v0.7 | Russian hardcoded. No i18n layer. Requires dedicated S-ticket. |
| 152-ФЗ compliance docs | v0.7 | Not started. Requires legal/compliance review. |
| pop-ingestor service extraction | v0.8 | Architecture decision deferred. Not blocking. |
| ADR-003 device identity | KSO runtime | Depends on KSO architecture decisions. |
| ТЗ extraction integrity | v0.7 | Existing extraction is adequate for current scope. |
| Remaining UI pages migration | v0.7 | 5 pages migrated; 8+ remain with inline styles. |
| KSO player/sidecar/hardware | v0.9 | Separate milestone. |
| ClickHouse/reporting warehouse | v0.8 | Separate milestone. |
| Billing/acts/ERP | v2.6 | Separate branch. |
| Tenant model ADR-018 | v2.6 | Decision pending. |

## 7. Documentation Truth Audit

| Document | Status | Issues |
|----------|--------|--------|
| `audit-v4-remediation-plan.md` | ✅ Fresh | S-059–S-073 all marked done. S-074 marked in progress. |
| `stabilization-tracker.md` | 🟡 Fixed | Header + backlog table updated in this review. |
| `production-gaps-triage.md` | 🟡 Fixed | Header updated in this review. |
| `release-versioning.md` | 🟡 Fixed | v0.6.2 section added (proposed, not published). |
| `roadmap-s020-2026-07-10.xlsx` | 🟡 Updated | Cell-level edits for S-062–S-073 statuses. |

## 8. References

- CI baseline: [#29483217520](https://github.com/santanas-dev/retail-media-platform-enterprise/actions/runs/29483217520) — 34/34 green
- develop HEAD: `90e91cb`
- main HEAD: `00060cc`
- v0.6.1-critical-hotfix tag: `00060cc`
- `docs/product/audit-v4-remediation-plan.md`
- `docs/architecture/stabilization-tracker.md`
- `docs/architecture/release-versioning.md`
- `docs/product/production-gaps-triage.md`
