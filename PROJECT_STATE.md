# Retail Media Platform — Project State

**Last updated:** 2026-07-17 (EDGE-001 v2 closure)
**Repository (local):** `/home/cobalt/retail-media-platform-enterprise`
**Canon (ASUSTOR):** `\\192.168.110.118\project\retail-media-platform-enterprise`
**Remote:** `github.com:santanas-dev/retail-media-platform-enterprise`

## Repository Checkpoint

| Branch  | Payload SHA | State/Docs SHA | Note |
|---------|-------------|----------------|------|
| develop | 2dad5f0     | e2bbb2d         | EDGE-001 v2 — FINGERPRINT_CONFLICT, revert_claim, concurrent proof, CI #29589031870 ✅ |
| main    | cab9014     | —               | C1 merged (v0.8) |

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

## Strategic Product Decisions (PLAN-001, 2026-07-17)

1. **Мультиарендность закладываем сейчас.** `retailer_id` + двухуровневая RLS
   (retailer + advertiser). ADR-018 — следующий активный воркстрим. Без этого
   нельзя: финансы, атрибуция, competitive separation.

2. **Продуктовая модель — цифровая вывеска.** Proof-of-Play достаточно для
   подтверждения показов. Attribution / интеграция с чеками **отложены по
   решению бизнеса** — это не пробел, а осознанный выбор.

3. **Время кампаний — по местному времени магазина.** Требуется ADR и
   доработка модели: campaign start/end, PoP-агрегация по дням.

4. **Рекламодатели: managed + self-service.** Self-service нужен, но не первым.
   Сначала managed/core flow. Self-service — medium priority (фаза 5).

## Roadmap Phases (PLAN-001)

| Фаза | Содержание | Статус |
|------|-----------|--------|
| **0.5 — Архитектура** | ADR-018 multitenancy, ADR store-local time, fix PoP-by-day | 🚧 В работе |
| **1 — Edge / один КСО** | Device onboarding, manifest signing, kill-switch player-side, real player, build distribution | ⚪ Не начато |
| **2 — Масштаб дёшево** | Redis cache + rate-limit, HTTP 304, retention/partitioning | ⚪ Не начато |
| **3 — Эксплуатация** | Device fleet health, underdelivery/compensation, staged rollout, §14 security ops | ⚪ Не начато |
| **4 — Каналы** | КСО scale, кассиры, mobile/push, Android/ESL/LED | ⚪ Не начато |
| **5 — Self-service guardrails** | Self-service, attribution deferred, programmatic/dynamic later | ⚪ Не начато |

## Next Active Workstream

**EDGE-001 ✅ RESOLVED** — CI #29589031870 ✅ (34/34). FINGERPRINT_CONFLICT + revert_claim + concurrent proof.
**PLAYER-AUD-001 ✅ COMPLETED** — аудит старого player/sidecar (commit `b1846c1`). Результат ниже.
Следующий workstream: **EDGE-002** manifest delivery hardening / heartbeat foundation (рекомендация аудита).

## PLAYER-AUD-001 — Audit Report (2026-07-17)

**Source:** `santanas-dev/retail-media-platform` (old repo), commit `b1846c1`.
**Scope:** `apps/kso_player` + `apps/kso_sidecar_agent`, read-only, no code transfer.
**Discovery commands:** `PYTHONPATH=apps/kso_player:apps/kso_sidecar_agent python3 -m pytest`.
**Tests:** 262/262 player, 327/327 sidecar (with cross-PATH), 0 skipped, all pure Python stdlib — no external deps.

## EDGE-001 — Device Onboarding Contract ✅ RESOLVED (hardened 2026-07-17)

- **Verdict v2: active code + existing fingerprint → 403 FINGERPRINT_CONFLICT. Idempotent only for used code + same device_id.**
- **Model:** `DeviceOnboardingCode` (54th table). `PhysicalDevice.retailer_id` added to ORM.
- **API:**
  - `POST /api/v1/device/onboard` — public (no JWT), atomic claim via `UPDATE ... WHERE status='active' RETURNING id`
  - `POST /api/v1/identity/device-codes` — admin only (`require_permission("devices.manage")`)
- **Permission:** `devices.manage` added to seed/conftest, granted to system_admin.
- **RLS:** Migration 022 — ENABLE/FORCE RLS + SELECT/INSERT/UPDATE policies with retailer scope + admin bypass.
- **Atomic claim:** raw SQL `UPDATE ... RETURNING id` prevents concurrent double-onboarding.
- **Fail-closed:** invalid/expired/revoked/used code → 403. Cross-retailer: retailer from code, not client.
- **v2 FINGERPRINT_CONFLICT:** new active code + already-registered fingerprint → 403. Claim reverted via `revert_claim()` — code stays reusable.
- **Idempotent:** used code + same fingerprint + same device_id returns existing device identity.
- **Tests (21 total):**
  - 8 unit: success, 5× rejection (incl. FINGERPRINT_CONFLICT), idempotent, admin code creation
  - 13 behavioral (real PostgreSQL, no mocks): non-admin/noperms 403, admin creates code, onboard success, expired rejection, used-code rejection, idempotent, **FINGERPRINT_CONFLICT (new code + registered fp → 403)**, **revert-proof (code reusable after conflict)**, **concurrent same code → single device**, cross-retailer, direct DB RLS proof (NOBYPASSRLS: scope A → A codes, empty→deny, admin→all)
- **Deferred:** real certificate issuance, device RLS behavioral for physical_devices, heartbeat/PoP/manifest.
- **v1 CI:** #29586874099 ✅, **v2 CI:** #29589031870 ✅ (34/34 green, incl. Behavioural PostgreSQL + ADR-008).
- **v2 Proof (5 behavioral gates):**
  - `test_active_new_code_existing_fingerprint_conflict` — active code + registered fp → 403 FINGERPRINT_CONFLICT
  - `test_used_code_same_fingerprint_idempotent` — used code + same fp + same device_id → 200
  - `test_already_used_code_rejected_different_fingerprint` — used code + different fp → 403 CODE_ALREADY_USED
  - `test_reverted_code_remains_usable_after_conflict` — claim откатывается, код переиспользуем
  - `test_concurrent_same_code_single_device` — конкурентный запрос → один device_id

## ADR-018-IMPL-001 — Multitenancy Foundation ✅ RESOLVED

- **Verdict: retailer_id + two-level RLS (retailer + advertiser) implemented and proven.**
- **Model:** `Retailer` table (53rd). `retailer_id` on 31 tenant-scoped tables via migration 020.
- **RLS:** Two-level policies (retailer + advertiser) on all tenant tables. `advertiser_organizations` uses `id`, `advertiser_applications` uses `organization_id` — special RLS blocks.
- **ScopeContext:** `retailer_scope_ids` added. `set_rls_context` sets `app.rmp_scope_retailer_ids`.
- **Scope resolution:** `resolve_scope_context` loads retailer IDs from `advertiser_organizations.retailer_id`.
- **Seed:** Default retailer (`code='default'`). `advertiser_organizations` INSERT includes `retailer_id`.
- **Backfill:** Migration backfills existing rows to default retailer. DEFAULT on `retailer_id` for pilot safety.
- **Behavioral proof (8 tests, strengthened 2026-07-17):**
  - `test_retailer_a_sees_only_own_briefs` — scoped user sees BRIEF_A, NOT BRIEF_B/BRIEF_A2
  - `test_retailer_a_cannot_get_retailer_b_brief` — cross-retailer detail → 404
  - `test_same_retailer_advertiser_scope_isolation` — two advertisers same retailer isolated
  - `test_same_retailer_cross_org_brief_detail_404` — cross-org detail → 404
  - `test_same_data_other_retailer_hidden` — analogous brief in other retailer invisible
  - `test_empty_scope_denies_all` — no-scope user sees nothing (403 or 200+empty)
  - `test_admin_sees_both_retailers` — system_admin bypass sees all briefs
  - `test_direct_db_rls_proof_retailer_isolation` — asyncpg NOBYPASSRLS: SET LOCAL scope A → A rows, not B; empty→deny-all; admin→all
- **Key fix (512cca9):** fixture brief INSERTs must set explicit `retailer_id` — DB default assigns `DEFAULT_RETAILER_ID`, which RLS then filters out for scoped users in other retailers.
- **CI:** #29579774858 ✅ (34/34 green, incl. Behavioural PostgreSQL + ADR-008).

## BP-004 — Campaign Brief / Placement Request ✅ RESOLVED

- **Verdict: advertiser can create draft briefs, submit them, view detail; cross-org isolated.**
- **Model:** `CampaignBrief` (52nd table) — draft/submitted/reviewing/accepted/rejected lifecycle.
- **Repository:** list/get/create/update/submit with `scope_advertiser_ids` tenant scoping; empty frozenset = deny-all (fail-closed).
- **RLS:** migration 019 — ENABLE/FORCE ROW LEVEL SECURITY + SELECT/INSERT/UPDATE policies on `campaign_briefs`.
- **Router:** advertiser-scoped endpoints: list/detail (campaigns.read), create/update/submit (campaigns.manage).
- **Frontend:** BriefListPage (empty/list/loading/error), BriefCreatePage (form+validation), BriefDetailPage (detail+submit+readonly submitted state).
- **Navigation:** «Заявки» item added to advertiser portal sidebar.
- **Backend tests:** 16/16 unit (list/detail/create/update/submit/cross-org/403/no-secrets).
- **Behavioral tests:** 7/7 (list scoping, cross-org detail 404, cross-org update/submit denied, create-uses-scope, direct RLS proof).
- **Frontend tests:** 7/7 vitest (empty, list, loading, error, detail draft, detail submitted, submit button).
- Payload SHA: f5d5a52. CI: #29570688800 ✅ (34/34 green, incl. Behavioural PostgreSQL + ADR-008).

## BP-003 — Advertiser Portal Shell / «Мой кабинет» ✅ RESOLVED

- **Verdict: advertiser dashboard with real org/user data, nav, honest empty states.**
- **Backend:** `/me` now returns `advertiser_organization_id` + `advertiser_organization` (resolved from scoped user_role in `get_advertiser_org_for_user` repo function). Graceful fallback for mock DB tests.
- **DashboardPage:** org card (legal name, display name, code, status badge) + user card (display name, login, access type, provider) + permissions list.
- **Navigation:** Кабинет, Кампании, Креативы, Документы (deferred), Поддержка (deferred), Профиль.
- **Empty states:** DocumentsPlaceholderPage, SupportPlaceholderPage — честные формулировки без обещаний.
- **Frontend tests:** 5 dashboard tests (org info, no-org, loading, expired session, permissions).
- **Backend:** 85 tests (incl. /me tests). **Admin-web:** 150/150. **Advertiser-web:** 84/84 + 2 skipped.
- Payload SHA: 61004f4. CI: #29567469569 ✅ (34/34 green, incl. Behavioural PostgreSQL).

## BP-002 — Advertiser Invite / Access Activation ✅ RESOLVED (follow-up closure)

- **Verdict: invite→accept→login→cross-org isolation proven with behavioural tests.**
- **Model:** `AdvertiserInvite` table (token, status pending/accepted/expired, 7-day TTL).
- **Race condition fix:** `SELECT ... FOR UPDATE` on token lookup in `accept_advertiser_invite`.
- **Admin:** `POST .../invite` creates CSPRNG token, `GET .../invite` shows current status.
- **Accept:** `POST /public/advertiser-invites/{token}/accept` → `create_local_advertiser_user()`.
- **Behavioral proof (9 tests, no mocks):** accept creates User+Credential+UserRole+Membership; login; /me; cross-org isolation (brands); token reuse/expired/invalid rejection; concurrent double-accept → single user.
- **Backend:** 31 unit + 9 behavioural. **Admin-web:** 150/150. **Advertiser-web:** 79/79.
- Payload SHA: da5a0d8. CI: #29564594270 ✅ (34/34 green incl. ADR-008 Behavioural PostgreSQL).

## BP-001 Follow-up — Anti-spam + Reviewing + Public form ✅ RESOLVED

- **Verdict: BP-001 gaps closed.**
- **Anti-spam:** IP-based rate limit on public endpoint (`PUBLIC_APPLICATION_RATE_LIMIT`=3/min, 429).
- **Reviewing:** new → reviewing → approve/reject transitions, backend validation, UI buttons.
- **Public form:** `/become-advertiser` page in advertiser-web (outside auth), 4 tests.
- **No-access proof:** structural test — approve creates `AdvertiserOrganization` only.
- **Backend:** 13→18 tests. **Admin-web:** 6→8 tests, 150/150 total. **Advertiser-web:** +5 tests, 79/79 total.
- Payload SHA: 0b82fab. CI: #29535773165 ✅ (34/34 green).

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
