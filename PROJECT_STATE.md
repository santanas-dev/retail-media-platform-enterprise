# Retail Media Platform — Project State

**Last updated:** 2026-07-16
**Repository (local):** `/home/cobalt/retail-media-platform-enterprise`
**Canon (ASUSTOR):** `\\192.168.110.118\project\retail-media-platform-enterprise`
**Remote:** `github.com:santanas-dev/retail-media-platform-enterprise`

## Repository Checkpoint

| Branch  | Payload SHA | State/Docs SHA | Note |
|---------|-------------|----------------|------|
| develop | 0e4c320     | c932fac        | A6/S-091 Emergency controls |
| main    | cab9014     | —              | C1 merged (v0.8) |

> **Rule:** Git refs (`git rev-parse HEAD`, `origin/develop`) are canonical for actual branch HEAD.
> PROJECT_STATE is canonical for task status and records the last verified payload/state
> checkpoints; it must not pretend to self-reference its own commit SHA. The Payload SHA
> is the last substantive commit whose result was verified (code, tests, CI). The State/Docs
> SHA is the commit that updated PROJECT_STATE/documentation after verification, if distinct.

## Active Workstreams

### H0 — Flaky test_backoff_respected_on_second_run ✅ RESOLVED
- **Verdict: confirmed timing flake, not real backoff regression.**
- Root cause: `_make_engine_and_clean()` only deleted `test.relay.%` events. Foreign pending/failed outbox events from other test suites (pop, campaigns) survived cleanup and consumed the shared `fail_next(1)` token.
- Fix (SHA 39dc8bc): `_make_engine_and_clean()` now deletes ALL pending/failed events regardless of event_type. Added +1s margin + 0.1s sleep in per-test isolation.
- CI proof: Run #29515994509 — 34/34 green, behavioural success.
- 10/10 local, 9/9 outbox relay suite.

### C1 — Creative Moderation + Campaign Approval RLS ✅ CLOSED
- Merged to main (SHA 09dc77a). CI #29522278631 — 34/34 green, ADR-008 behavioural success.
- Fix applied: 4 endpoints under NOBYPASSRLS, 8 behavioural tests (all pass).
- Bug fixed: `AdvertiserOrganization.name` → `legal_name` (4 places).
- Seed gap closed: `creatives.moderate` in role_permissions for system_admin/security_admin.

### C2 — LDAPS certificate validation ✅ RESOLVED
- **Verdict: real bug — two paths silently dropped TLS to CERT_NONE.**
- Root cause 1: `_connect()` gated TLS creation on `ad_use_tls` flag. When False, `tls=None` and ldap3 defaulted to `CERT_NONE`.
- Root cause 2: `elif` chain had no fallback — unrecognised `cert_val` (typo, etc.) left `tls_kwargs` empty → `tls=None`.
- Fix (SHA 47e7d44): removed `ad_use_tls` gate; TLS always created from cert policy. Added fail-secure `else` → `CERT_REQUIRED`. Fixed no-op test `test_connect_tls_required_uses_cert_required`.
- New tests: unknown cert_val → CERT_REQUIRED; ad_use_tls=False → still CERT_REQUIRED; source-inspection: fail-secure else, no ad_use_tls gate.
- CI proof: Run #29519917049 — 34/34 green, ADR-008 behavioural success.
- ldap3 already in requirements.txt and CI — no dependency fix needed.
- Auth model unchanged beyond LDAPS cert validation scope.

### D1 — Extracted TZ table reattachment ✅ RESOLVED
- **Verdict: documentation integrity fix — tables divorced from sections.**
- Root cause: sequential extraction numbering did not match section numbering. Gaps at sections 9, 13, 21, 22 shifted all subsequent assignments.
- Fix (SHA 9216a54): content-based semantic mapping of 36 tables to 25 sections. Section 14 now correctly shows security requirements (auth/RBAC/devices/API/personal data), not device statuses.
- 0 orphan `## TABLE` headers remain. Original `.docx` untouched.

### D3 — Roadmap coverage audit vs TZ ✅ RESOLVED
- **Verdict: 15 TZ gaps found, 28 rows added to roadmap.**
- Sheet 1 (Технический): 91→107 строк. Sheet 2 (Бизнес-функции): 38→50 строк.
- SHA: 76b3fdf.
- No code/CI changes — docs-only.

### A4 / S-089 — Inventory simulation ✅ RESOLVED
- POST /inventory/simulate — aggregates availability + conflicts + applied rules
- 🧪 Симуляция button in campaign overview (draft, canApprove)
- Results panel: overall_fit, per-surface fill%, conflicts
- 13 backend tests (8 schema + 5 endpoint) + 3 frontend tests
- **Fix (SHA 80276f1):** removed `le=100.0` cap on `slot_fill_percent` — overbook scenarios (>100%) were rejecting their own valid output. Added real endpoint tests via TestClient.
### A5 / S-090 — Campaign dashboard ✅ RESOLVED
- **Verdict: dashboard tab added to admin-web CampaignDetailPage.**
- Plan/Fact: plan from placement max_impressions, fact from PoP summary.
- Deviation with color coding (green/yellow/red), delivery status, underdelivery warning.
- By-day + by-surface breakdowns. Device health with honest limitation note (S-097).
- No backend changes — reuses existing PoP reporting endpoints.
- 5 vitest tests: plan/fact, empty, critical underdelivery, device health, by-day.
- CI: #29529434884 — 34/34 green. Admin-web: 132/132 (127 + 5).
- **Follow-up (SHA 38aa844):** added loading state, error state, by-surface table tests. Now 8 S-090 tests, 135/135 admin-web green.

## Open Issues

| Priority | Count | Details |
|----------|-------|---------|
| Critical | 0 | — |
| High | 0 | — |
| Medium/Low | 0 open; see `docs/product/audit-v4-remediation-plan.md` for closed v0.6.1 findings |

> **Audit note:** audit-v4 documents reference SHA `00060cc` for CRITICAL-1 (LDAPS) and
> CRITICAL-2 (moderation RLS). These were closed at v0.6.1, but C2 later found the LDAPS
> fix incomplete — C2 fix SHA is `47e7d44` (CI #29519917049). Current canonical status
> is in this PROJECT_STATE.md, not in the audit docs.

## Next Active Workstream

**A6 / S-091 — Emergency controls.** ✅ RESOLVED

## Completed (Player Blockers A1–A6)

| ID | Task | Status |
|----|------|--------|
| A1 S-086 | Inventory availability forecast | ✅ |
| A2 S-087 | Sold-out alternatives | ✅ |
| A3 S-088 | Rules management UI | ✅ |
| A4 S-089 | Inventory simulation | ✅ |
| A5 S-090 | Campaign dashboard | ✅ |
| A6 S-091 | Emergency controls | ✅ |

## Pending

| ID | Task | Status |
|----|------|--------|
| —   | —     | —      |

## Environment

- **PostgreSQL:** Docker `rmp-phase1-postgres-1` (port 5432)
- **App role:** `retail_media_app` (NOBYPASSRLS)
- **Owner role:** `retail_media_owner` (fixtures)
- **Behavioural:** `RUN_BEHAVIORAL_TESTS=1` + BEHAVIORAL_DB_URL + BEHAVIORAL_APP_DB_URL

## Constraints

- `main` = stable releases, `develop` = active integration
- Protected: `.env`, Docker/deploy scripts, destructive migrations
- RLS on all tenant-scoped tables, NOBYPASSRLS enforced
- Only Hermes pushes to GitHub; ASUSTOR = local canon
