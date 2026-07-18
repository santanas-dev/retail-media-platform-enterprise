# Retail Media Platform — Project State

**Last updated:** 2026-07-18 (UI-TRUTH-001A-FU — state hygiene + CI #29656035552 green)

R1 ✅ **RELEASED** — baseline to main (3d201d6), CI #29642225070 green (34/34), tag v0.8.0-r1-edge-safety-runtime → 3d201d6.
T1 ✅ **RESOLVED** — BehBuilder module, K1 converted, CI #29645034680 green (324 passed).
EDGE-003 ✅ **RESOLVED** — PoP ingestion endpoint behavioural proof (admin bypass), CI #29649000788 green (6/6).
EDGE-003-FU ✅ **RESOLVED** — PoP ingestion RLS / non-admin device proof (NOBYPASSRLS), CI #29652235623 green (5/5).
EDGE-004 ✅ **RESOLVED** — Device Heartbeat initial implementation.
EDGE-004-FU ✅ **RESOLVED** — Heartbeat proof hardened (12 tests, no admin bypass, honest state).
UI-TRUTH-001A ✅ **RESOLVED** — Feature registry + smoke harness + G1 proof, CI #29656035552 green.
**Repository (local):** `/home/cobalt/retail-media-platform-enterprise`
**Canon (ASUSTOR):** `\\192.168.110.118\project\retail-media-platform-enterprise`
**Remote:** `github.com:santanas-dev/retail-media-platform-enterprise`

## Repository Checkpoint

| Branch  | Payload SHA | State/Docs SHA | Note |
|---------|-------------|----------------|------|
| develop | 91053c4 | 6becd92 | UI-TRUTH-001A-FU — state hygiene, CI green |
| main    | 3d201d6     | —               | R1 release — K1/K2/RM1/CLEAN-BOOT-001 |

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

**EDGE-001 ✅ RESOLVED** — CI #29589031870 ✅.
**PLAYER-AUD-001 ✅ COMPLETED** — audit report.
**EDGE-002 ✅ RESOLVED (v4 production-safe)** — app.rmp_device_id bootstrap, no owner lookup, CI #29635004193 ✅.

Приоритет после внешнего аудита 2026-07-18 (P0 safety first):
1. **K1** ✅ — emergency override → manifest.
2. **K2** ✅ — manifest signature verification before player execution.
3. **RM1** ✅ — roadmap/docs/release process hygiene.
4. **CLEAN-BOOT-001** ✅ — P1: clean docker boot → login smoke. **RESOLVED.**
5. **R1** ✅ — release baseline to main, CI #29642225070 green, tag v0.8.0-r1-edge-safety-runtime.
6. **T1** ✅ — behavioural test data builder. BehBuilder + K1 converted. CI #29645034680 green (324 passed).
7. **EDGE-003** ✅ — PoP ingestion endpoint behavioural proof (admin bypass, 6/6). CI #29649000788.
8. **EDGE-003-FU** ✅ — PoP ingestion RLS / non-admin proof (NOBYPASSRLS, 5/5). CI #29652235623.

## R1 — Release Baseline to Main ✅ RELEASED (2026-07-18)

- **Verdict:** develop (b439dcf) merged to main → 3d201d6. CI #29642225070 green (34/34).
- **Contents:** K1 (emergency override), K2 (manifest signature), RM1 (roadmap sync), CLEAN-BOOT-001 (clean boot smoke).
- **Tag:** v0.8.0-r1-edge-safety-runtime → 3d201d6 (annotated, merge commit on main).
- **Next:** heartbeat / PLAYER-IMPORT (на выбор пользователя).

## T1 — Behavioural Test Data Builder ✅ RESOLVED (2026-07-18)

- **Verdict:** minimal reusable `BehBuilder` class in `tests/behavioral/builder.py`.
  K1 (emergency manifest) converted from 11 manual `_run_sql` inserts to 7 builder calls.
- **Builder API:** `retailer()`, `store_chain()`, `channel_device_type()`,
  `advertiser()`, `campaign()`, `device()`, `manifest()`, `emergency_override()`,
  `deactivate_emergency()`, `cleanup()`.
- **ID scheme:** `prefix-entity-NNNN` — auto-generated, no manual naming clashes.
- **Cleanup:** single `b.cleanup()` call deletes by prefix in FK-safe order.
- **CI:** #29645034680 ✅ (324 passed, 12 skipped, ADR-008 green).
- **Not done:** remaining behavioural tests not yet converted — deferred to separate task.

## CLEAN-BOOT-001 — Clean Docker Boot Login Smoke ✅ RESOLVED (2026-07-18)

**Status:** ✅ RESOLVED.

**Verdict:** Три бага мешали чистому `docker compose up → login` по runbook.
Все исправлены, smoke пройден: 8/8 checks.

**Root cause:**
- D-BOOT-2 (seed credential split): `split(";\n")` в `_build_credentials_sql()` не
  разрезал `ON CONFLICT (user_id) DO NOTHING;  -- comment` — `;` после `DO NOTHING`
  отделён пробелами от `\n`. Оба INSERT в одном chunk → asyncpg глотал молча.
- D-BOOT-3 (grant-app-role.py): `--no-cache` при build только для control-api,
  db-setup использовал кэш старого образа без `COPY infra/compose/`.
- Smoke health check: `/api/v1/health` → 404, control-api был жив.

**Fixes (SHA a16737e):**
- seed.py: inline-комментарии перенесены перед INSERT (не после `;`).
  Split: 3 части → comments (skip) + 2 INSERT (exec).
- smoke: health URL → `/health/live`, `--no-cache` для db-setup.

**Smoke proof (full clean boot):**
| Step | Result |
|------|--------|
| docker compose down -v | ✅ |
| build control-api + db-setup (--no-cache) | ✅ |
| compose up postgres + redis + control-api | ✅ |
| control-api healthy | ✅ (2s) |
| db-setup (migrations + seed + grant-app-role) | ✅ (exit 0) |
| POST /api/v1/auth/login | ✅ (200 + token) |
| GET /api/v1/identity/campaigns | ✅ (200, total=1) |
| local_credentials count | ✅ (2 seeded) |

**Payload SHA:** `a16737e`.

## K2 — Manifest Signature Verification Before Player Execution ✅ RESOLVED (2026-07-18)

- **Verdict: runtime/player-side проверка подписи манифеста — реальная, не placeholder.**
- **Fix:** вынес `sign_manifest_payload` + `verify_manifest_signature` + `canonical_json` в нейтральный слой `packages/contracts/manifest_signing.py` (HMAC-SHA256, canonical JSON, sort_keys, compact). Заменил placeholder-проверку `== "INVALID"` в `RuntimeSimulator.apply_manifest()` на реальную `verify_manifest_signature()`.
- **Verifier location:** `RuntimeSimulator` (ADR-013 runtime contract) — подпись проверяется ДО atomic swap, ДО любых side effects.
- **Signing key:** `RuntimeSimulator(signing_key=...)` — если ключ передан, требует валидную подпись и отвергает: missing signature, wrong key, wrong signature, unsupported algorithm (не HMAC-SHA256). Без ключа — backward compat (dev mode).
- **Security:** старый magic-string `"INVALID"` явно отвергается (никогда не принимается).
- **Tests (27 unit):**
  - 11 signing-module: canonical_json (deterministic, sorted, compact, excludes signature), sign/verify (hex digest, valid/wrong-key/wrong-sig/empty/tampered)
  - 16 runtime: valid signed → accepted, wrong sig → rejected, wrong key → rejected, unsupported algo → rejected, missing sig → rejected, tampered (retailer_id, playlist, emergency, content_hash, device_id, version) → rejected, last-known-good preserved after tamper, no playback after sig failure, backward compat unsigned accepted, INVALID magic string still rejected
- **Existing tests:** 41/41 simulator + 38/38 manifest/device-gateway — 0 регрессий.
- **CI:** #29638045838 ✅ (34/34 green).
- **Payload SHA:** `4a35179`.
- **Deferred/not done:** player-side enforcement на реальном KSO, heartbeat.

## K1 — Emergency Override → Device Manifest ✅ RESOLVED (2026-07-18)

- **Verdict: real emergency override теперь попадает в device manifest, не placeholder.**
- **Fix:** `get_latest_manifest_metadata()` запрашивает `emergency_overrides` (глобальная таблица, без RLS). `get_latest_manifest_for_device()` использует `repository_row["emergency_active"]` вместо хардкода `emergency.active=False`.
- **ETag/cache:** `content_hash` включает `emergency_active` — активация emergency меняет ETag, 304 не отдаёт stale `active=false`.
- **Security:** `emergency_overrides` — глобальная таблица без `retailer_id`, без RLS. App-роль читает напрямую. Запись только через admin endpoint (A6/S-091), не затронута. NO owner/bypass в manifest request path.
- **Migration:** 024 — создание таблицы `emergency_overrides` (id, reason, activated_by, activated_at, deactivated_at, is_active, индексы).
- **Behavioural proof (4 tests, NOBYPASSRLS):**
  - `test_emergency_active_appears_in_manifest` — активация emergency → manifest `emergency.active=true`
  - `test_emergency_deactivate_clears_manifest` — деактивация → `active=false`
  - `test_no_active_emergency_returns_inactive` — нет активного override → `active=false`
  - `test_emergency_cache_bust` — ETag меняется после активации, curl с `If-None-Match` возвращает 200 (не 304)
- **Unit tests:** 1297 passed (без регрессий).
- **Behavioural ADR-008:** 324 passed, 12 skipped.
- **CI:** #29636889061 ✅ (34/34 green).
- **Payload SHA:** `8b9fef2` (code) + `71b5c4b` (migration).
- **Deferred/not done:** player-side enforcement на реальном KSO, store/device-level emergency.

## Verified Audit Backlog — 2026-07-18

Внешний аудит 2026-07-18 проверил состояние репозитория после EDGE-002.
Зарегистрированы подтверждённые backlog-пункты — ничего не отмечено done,
это только регистрация.

### P0 — safety / must-fix

| Код | Описание | Done = |
|-----|----------|--------|
| **K1** ✅ | Emergency override не доходит до manifest — backend-состояние меняется, но device manifest возвращает `emergency.active=false` | Behavioural test: admin активирует emergency → следующий device manifest имеет `emergency.active=true` под NOBYPASSRLS | CI #29636889061 |
| **K2** ✅ | Manifest signature verification before player execution не доказана — server signing существует, но runtime/player verification placeholder/deferred | Tampered manifest rejected before apply/play | CI #29638045838 |
| **RM1** ✅ | Roadmap stale vs PROJECT_STATE — roadmap-ячейки не синхронизированы с фактическим статусом в PROJECT_STATE | Roadmap cells updated on both sheets, no structure changes | SHA 7bcc570 |
| **R1** ✅ | Release point v0.8 — зафиксировать baseline для внешнего аудита | merge develop→main, CI #29642225070 green (34/34), tag v0.8.0-r1-edge-safety-runtime |
| **T1** ✅ | Behavioral test data builder — тесты создают фикстуры вручную, нет переиспользуемого builder-паттерна | BehBuilder module + K1 converted, CI #29645034680 green (324 passed) |

### P1 — important / should-fix

| Код | Описание | Done = |
|-----|----------|--------|
| **M1** | Default retailer masks missing scope — `retailer_id DEFAULT '00000000-...'` скрывает ошибки, когда scope не установлен | Behavioural test: INSERT без scope → fails loudly |
| **P1s** | PROJECT_STATE self-SHA/checkpoint churn — `(this commit)` placeholder и цикл amend→новый SHA | Agreed process removes placeholder/self-reference loop |

### P2 — operations / cross-cutting

| Код | Описание | Кто |
|-----|----------|-----|
| **B1** | Device fleet health/rollback before 300+ devices | Код |
| **B2** | Read-only CI access for independent audit | HUMAN |
| **B3** | Physical KSO or exact OS image — параллельно с EDGE-003/004 | HUMAN |
| **B4** | PoP quality/honesty differentiation strategy | HUMAN |

## PLAYER-AUD-001 — Audit Report (2026-07-17)

**Source:** `santanas-dev/retail-media-platform` (old repo), commit `b1846c1`.
**Scope:** `apps/kso_player` + `apps/kso_sidecar_agent`, read-only, no code transfer.
**Discovery commands:** `PYTHONPATH=apps/kso_player:apps/kso_sidecar_agent python3 -m pytest`.
**Tests:** 262/262 player, 327/327 sidecar (with cross-PATH), 0 skipped, all pure Python stdlib — no external deps.

### Key files covering playback, manifest, media sync, PoP, heartbeat, kill-switch

| Concern | Old repo files |
|---------|---------------|
| **Playback cycle** | `kso_player/runtime_daemon.py`, `runtime_loop.py`, `runtime_cycle.py`, `display_cycle.py` |
| **Manifest fetch/store** | `kso_sidecar_agent/manifest_client.py`, `manifest_store.py`, `run_cycle_manifest.py`, `kso_gateway_client.py`, `kso_manifest_gateway_extractor.py` |
| **Manifest → playlist** | `kso_player/playlist.py`, `render_plan.py` |
| **Media sync/cache** | `kso_sidecar_agent/media_client.py`, `media_cache.py`, `run_cycle_media.py` |
| **PoP local write** | `kso_player/pop_writer.py`, `events.py` |
| **PoP pickup → send** | `kso_sidecar_agent/pop_pickup.py`, `pop_sender.py`, `pop_sender_retry.py`, `pop_sender_runner.py`, `pop_batch.py`, `pop_send_package.py`, `pop_scoped_send.py` |
| **PoP rotation** | `kso_sidecar_agent/pop_rotation_plan.py`, `pop_rotation_apply.py`, `pop_rotation_files.py`, `pop_rotation_materializer.py` |
| **Heartbeat** | `kso_sidecar_agent/heartbeat_client.py`, `run_cycle_heartbeat.py` |
| **Kill-switch** | `kso_player/kill_switch.py` |
| **Runtime gate (state)** | `kso_player/runtime_gate.py`, `state_observer.py` |
| **Safety gate** | `kso_player/safety.py` |
| **Session / item select** | `kso_player/session.py`, `simulator.py` |
| **Render shell (HTML/JS)** | `kso_player/player_shell/` (bootstrap.js, player.js, index.html, styles.css, bootstrap_snapshot.js) |
| **Snapshot writer** | `kso_player/runtime_snapshot_writer.py`, `shell_snapshot.py` |
| **Sidecar orchestrator** | `kso_sidecar_agent/run_cycle.py`, `kso_sidecar_daemon.py` |
| **Retry/backoff** | `kso_sidecar_agent/retry_backoff.py` |
| **CLI (both)** | `kso_player/cli.py`, `kso_sidecar_agent/cli.py` |

### Transfer table: KSO Player (`kso_player/` — 37 modules + `player_shell/`)

| Компонент | Ключевые файлы | Что делает | Статус | Причина |
|-----------|---------------|-----------|--------|--------|
| Runtime gate | `runtime_gate.py` | Читает `state/kso_state.json`, fail-closed: play только при `idle` + свежий timestamp | Адаптировать | Нужен новый источник состояния — не локальный JSON, а endpoint или sidecar IPC |
| Kill-switch | `kill_switch.py` | Файл-флаг `/run/verny/kso/kill_switch`: есть → hide, нет → show, ошибка → hide | Перенести как есть | 65 строк, pure Python, fail-safe, без зависимостей |
| Safety gate | `safety.py` | 9 состояний КСО → play/hold/stop. Fail-closed | Перенести как есть | Core logic без интеграции |
| Playlist | `playlist.py` | Читает `manifest/current_manifest.json` → `PlayerPlaylist` | Адаптировать | Manifest-схема изменится (ADR-016), core логика переиспользуема |
| Session | `session.py` | In-memory session state, round-robin выбор item | Перенести как есть | Pure logic, нет путей/секретов |
| Simulator | `simulator.py` | `simulate_playback_step()` — полный пайплайн без реального playback | Перенести как есть | Ключевой для тестирования без Chromium |
| PoP writer | `pop_writer.py` | Append-only JSONL + flush+fsync | Адаптировать | Схема PoP изменится под enterprise |
| Display cycle | `display_cycle.py` | gate → snapshot → wait → PoP | Адаптировать | Привязка к локальному state |
| Runtime daemon | `runtime_daemon.py` | Long-running loop: подготовка → циклы → stop_check → health JSON | Адаптировать | Нужны: device JWT, systemd unit |
| Runtime loop | `runtime_loop.py` | Multi-cycle с живой ротацией snapshot | Адаптировать | Та же причина |
| Visible runtime | `visible_runtime.py` | Подготовка workspace + Chromium launch | Адаптировать | Пути к chromium/shell переедут |
| Snapshot writer | `runtime_snapshot_writer.py` | Atomic write `bootstrap_snapshot.js` | Перенести как есть | Без бэкенда |
| Shell snapshot | `shell_snapshot.py` | Сборка render-snapshot для JS-оболочки | Адаптировать | Manifest-схема |
| Render shell | `player_shell/` (5 файлов) | HTML+JS+CSS: Chromium kiosk-оболочка | Перенести как есть | Чистый фронт |
| Display profiles | `profiles/` (2 файла) | Профили: portrait 768×1366 | Перенести как есть | |
| CLI | `cli.py` (673 строки) | 15+ команд | Адаптировать | Команды переподключить к enterprise |
| Events | `events.py` | `build_playback_event_draft/completed` | Адаптировать | Схема событий под enterprise |
| X11 renderer | `x11_click_through_renderer.py`, `x11_screensaver_runner.py` | X11-специфичный рендерер | Не переносить | X11-специфичен; enterprise — Chromium kiosk |
| X11 proof | `x11_click_through_proof.py` | X11-харнесс | Не переносить | Та же причина |
| Portrait smoke | `portrait_smoke.py` | Дымовой тест портретного профиля | Перенести как есть | |
| Interaction hide | `interaction_hide.py` | Скрытие при касании экрана | Адаптировать | Зависит от KSO-специфичного input |
| Local demo | `local_demo_fixture.py`, `local_chromium_demo_runner.py`, `local_visual_demo_prepare.py` | Demo-fixture для локального тестирования | Перенести как есть | Ключевые для dev-цикла |

### Transfer table: KSO Sidecar Agent (`kso_sidecar_agent/` — 50 модулей)

| Компонент | Ключевые файлы | Что делает | Статус | Причина |
|-----------|---------------|-----------|--------|--------|
| Run cycle | `run_cycle.py` (~1160 строк) | Оркестратор: auth → manifest → media → heartbeat → PoP → report | Адаптировать | Ключевой модуль. Нужен enterprise device JWT + новый manifest/PoP API |
| Auth | `run_cycle_auth.py`, `device_auth_client.py`, `token_state.py` | Device auth: secret_store → token → refresh | Адаптировать | Заменить на enterprise `/device/onboard` + device JWT |
| Manifest sync | `manifest_client.py`, `manifest_store.py`, `run_cycle_manifest.py`, `kso_gateway_client.py`, `kso_manifest_gateway_extractor.py`, `kso_safe_manifest_context.py` | Fetch → extract → save manifest | Адаптировать | Новый endpoint `/device/manifest/latest` (ETag, ADR-016) |
| Media sync | `media_client.py`, `media_cache.py`, `run_cycle_media.py` | Download → cache media files | Адаптировать | Новый media endpoint, enterprise MinIO |
| PoP pickup | `pop_pickup.py`, `pop_pending_lock.py`, `pop_pending_rewrite.py` | Читает JSONL от player → готовит к отправке | Перенести как есть | Локальный I/O, не зависит от backend API |
| PoP send | `pop_sender.py`, `pop_sender_retry.py`, `pop_sender_runner.py`, `pop_send_package.py`, `pop_scoped_send.py` | Отправка PoP в backend с retry | Адаптировать | Новый PoP endpoint, нужен device JWT |
| PoP rotation | `pop_rotation_plan.py`, `pop_rotation_apply.py`, `pop_rotation_files.py`, `pop_rotation_materializer.py` | Ротация sent → quarantine → delete | Перенести как есть | Локальная файловая логика |
| PoP batch | `pop_batch.py` | Пакетная отправка PoP | Адаптировать | Новый batch endpoint |
| Heartbeat | `heartbeat_client.py`, `run_cycle_heartbeat.py` | HTTP heartbeat: device state → backend | Адаптировать | Нужен enterprise heartbeat endpoint |
| Runtime config | `runtime_config_client.py`, `runtime_config_store.py`, `run_cycle_runtime_config.py` | Fetch + save runtime config | Адаптировать | Нужен enterprise runtime-config endpoint |
| Media report | `media_cache_report_client.py`, `run_cycle_media_report.py` | Отправка отчёта о media cache | Адаптировать | Новый endpoint |
| Retry | `retry_backoff.py` | Retry с exponential backoff | Перенести как есть | Pure logic |
| CLI | `cli.py` | 20+ команд CLI | Адаптировать | Переподключить к enterprise endpoints |
| Daemon | `kso_sidecar_daemon.py` | Демон-процесс (pid/lock/stop) | Адаптировать | Нужен systemd unit |
| Secret store | `secret_store.py` | Локальное хранение device secret | Не переносить | Заменяется enterprise device JWT из EDGE-001 |
| Player readiness | `player_readiness.py` | Проверка готовности player (manifest + media) | Перенести как есть | Локальная проверка |
| HTTP client | `http_client.py` | Общий HTTP-клиент | Адаптировать | URL'ы под enterprise |
| Local config | `local_config.py` | Чтение локального конфига | Перенести как есть | |
| Atomic I/O | `atomic_io.py` | Atomic file write | Перенести как есть | |
| Safe logger | `safe_logger.py` | Безопасное логирование (без forbidden substrings) | Перенести как есть | |
| Pop payload | `pop_payload.py` | Построение PoP payload | Адаптировать | Новая схема + retailer_id |

### Gap-list до Фазы 1 (register → manifest → play → PoP → heartbeat)

| # | Gap | Блокирует | Что нужно |
|---|-----|-----------|-----------|
| 1 | Enterprise manifest endpoint (`/device/manifest/latest`) | Весь цикл | EDGE-002 — manifest delivery с ETag, подписью, ADR-016 |
| 2 | Enterprise heartbeat endpoint | Фаза 1 | Новый endpoint в control-api |
| 3 | Enterprise PoP ingestion endpoint | Фаза 1 | Новый endpoint, схема с retailer_id, валидация |
| 4 | Device JWT в sidecar | Sidecar→backend auth | EDGE-001 даёт JWT — sidecar должен использовать его вместо secret_store |
| 5 | Runtime state source | Player gate | Нужен IPC от sidecar или state-adapter вместо локального `kso_state.json` |
| 6 | systemd units | Production deploy | `.service` + `.timer` для player-daemon и sidecar-daemon |
| 7 | Chromium kiosk на целевом KSO | Визуальный playback | Проверка совместимости Chromium с Sherman-J 5.1 |
| 8 | Manifest schema migration | Player playlist | Старый manifest (schemaVersion 1) → enterprise ADR-016 manifest |
| 9 | Backend kill-switch | Безопасность | Сейчас kill-switch — локальный файл. Нужен backend → sidecar → player propagation |

### Совместимость с enterprise backend (ADR-018 / EDGE-001)

| Возможность | Статус в старом коде | Совместимость |
|-------------|---------------------|---------------|
| Device JWT | `device_auth_client.py` читает из secret_store | Заменить на EDGE-001 `/device/onboard` JWT |
| retailer_id | Отсутствует | Добавить во все структуры (PoP, manifest, heartbeat) |
| `/device/onboard` | Нет аналога | EDGE-001 реализован |
| `/device/manifest/latest` | Старый gateway-manifest endpoint | Нужен EDGE-002 |
| PoP contract | Локальный JSONL → batch → POST | Нужен enterprise PoP endpoint |
| Heartbeat contract | `POST /device/heartbeat` | Нужен enterprise endpoint |
| RLS | Не применимо (нет БД на player/sidecar) | N/A — backend-зона |

### Что НЕ проверено и почему

| Пункт | Причина |
|-------|---------|
| Реальный Chromium launch | Требует X11/дисплей — невозможно в CI/headless без GPU |
| Интеграция с КСО Sherman-J 5.1 | Нет доступа к реальному терминалу |
| systemd unit | В репозитории нет `.service` файлов — не реализовано |
| Сетевые тесты sidecar (`test_pop_sender_http.py`, `test_run_cycle_e2e.py`) | Таймаутятся без реального backend — исключены из прогона |
| X11-специфичные тесты без X11 | 2 файла с X11-зависимостью — пропущены, помечены «не переносить» |
| Производительность на целевом KSO | Нет целевого железа |

### Recommendation: EDGE-002 (not PLAYER-IMPORT-001)

**Why not PLAYER-IMPORT-001:**
- Старый player/sidecar доказал работоспособность (589 тестов, 100% pass)
- Переносить код сейчас нельзя — нет enterprise manifest endpoint. Player/sidecar завязаны на manifest/media URLs, которых в enterprise ещё нет.
- EDGE-002 закрывает gap #1 (manifest delivery) → появляется контракт, под который можно адаптировать player.
- Последовательность: EDGE-002 (manifest) → EDGE-003 (PoP ingestion) → EDGE-004 (heartbeat) → PLAYER-IMPORT-001 (перенос адаптированного кода).
- PLAYER-AUD-001 дал полную карту для планирования, но не для переноса.

### Transfer summary

- **Перенести как есть:** 16 компонентов (kill-switch, safety gate, session, simulator, render shell, profiles, snapshot writer, local demo, player_readiness, retry_backoff, PoP pickup/rotation, local_config, atomic_io, safe_logger, portrait_smoke)
- **Адаптировать:** 24 компонента (runtime gate, playlist, PoP writer, display cycle, daemon/loop, visible runtime, CLI×2, events, interaction hide, run_cycle, auth, manifest/媒体 sync, PoP send/batch, heartbeat, runtime/media config, HTTP client, pop_payload)
- **Не переносить:** 3 компонента (X11 renderer/proof, secret_store)

## EDGE-002 — Device Manifest Delivery ✅ RESOLVED (v4 production-safe, 2026-07-18)

- **Endpoint:** `GET /api/v1/device/manifest/latest` — device-gateway (port 8001)
- **Auth:** device JWT (auth_provider="device", sub=device_id) — no user tokens accepted
- **ETag/304:** lightweight metadata query first → 304 if If-None-Match matches → Redis cache → full assembly
- **Fail-closed:** inactive/revoked/unregistered device → 403, nonexistent → 404, missing/invalid token → 401
- **Manifest schema v1:** `packages/contracts/manifest_v1.schema.json` — retailer_id + emergency in `required`
- **Tenant isolation:** retailer_id from device record (not client). RLS proven under NOBYPASSRLS
- **Signing:** HMAC-SHA256 when MANIFEST_SIGNING_KEY configured
- **Deferred:** full manifest generation campaign-aware (uses pre-generated DeliveryManifest), Redis (optional/fail-open)
- **Resolved by K1:** emergency backend propagation — no longer a placeholder; manifest returns real emergency state from `emergency_overrides` table

### EDGE-002-FU v2 (weak proof) — 5 tests, CI green but behavioural insufficient
- `test_device_a_200_manifest` — allowed both 200 AND 404 (weak)
- `test_304_etag` — skipped on "no manifest"
- Cross-retailer: DB-level RLS proof only, no real endpoint tests
- **Verdict:** rejected — proof too weak.

### EDGE-002-FU v4 (production-safe bootstrap) — 13 tests, CI #29635004193 ✅
- **Root cause:** v3 used `BEHAVIORAL_DB_URL` (owner role) for device lookup — works in CI but chicken-and-egg in production under FORCE RLS.
- **Fix:** Migration 023 adds `id = app.rmp_device_id` to `physical_devices` SELECT RLS policy. `set_device_rls_context` now uses the REQUEST session: set `app.rmp_device_id` → read retailer_id (visible via bootstrap) → clear bootstrap → set `app.rmp_scope_retailer_ids` → return. No owner/bypass in request path.
- **Endpoint simplified:** `retailer_id` param removed, RLS context set entirely in dependency.
- **Direct DB RLS proof (3 tests):** app-role with `app.rmp_device_id=A` sees only device A (not B), no bootstrap sees zero devices, bootstrap B sees device B not A.
- **CI:** Unit Tests ✅, Behavioural ADR-008 ✅ (320 passed, 12 skipped)
- **Payload SHA:** `2f43951`
- **Honest v3 verdict:** v3 was strict assertion-wise but production bootstrap was test-env dependent — `set_device_rls_context` used owner-role connection in CI, would fail under FORCE RLS in production.

## EDGE-004 — Device Heartbeat / Health Endpoint ✅ RESOLVED

- **Verdict: device heartbeat with RLS security proof under NOBYPASSRLS. Proof hardened in EDGE-004-FU.**
- **Endpoint:** `POST /api/v1/device/heartbeat` — device-gateway (port 8001)
- **Auth:** device JWT required (auth_provider="device", sub=device_id); user/admin tokens → 401
- **RLS context:** `set_device_rls_context` (EDGE-002-FU v4) sets retailer scope on request session before handler runs
- **Migration (025):** `physical_devices` extended with `last_heartbeat_at`, `health_state`, `runtime_version`, `player_version`
- **Model:** `PhysicalDevice` columns added; `record_device_heartbeat()` atomic update in repository
- **Payload rejected:** `device_id`, `retailer_id` — neither is a field in `HeartbeatRequest`
- **Fail-closed:** inactive/revoked device → 403, missing/invalid/non-device token → 401, nonexistent → 404
- **Response:** `{"status": "accepted", "server_time": "<ISO>", "health_state": "<state>"}`
- **Deferred:** command channel / remote control, UI fleet health dashboard, staged rollout
- **Tests (12/12, no admin bypass):**
  - 9 endpoint: device A → 200, defaults healthy, **strict heartbeat DB proof (pre-read NULL → POST → post-read: non-null + payload match + timestamp freshness)**, user token 401, no auth 401, invalid token 401, inactive device 403, device A cannot touch device B, client device_id spoof ignored
  - 3 direct DB RLS: bootstrap A → sees device A not B, bootstrap B → sees device B not A, no bootstrap → sees zero
- **CI (FU):** #29655140733 ✅ (34/34 green — 347 passed, 12 skipped)
- **Root cause fix:** device-gateway `get_db` didn't have `session.begin()` — writes (ORM or raw SQL) didn't persist. Added `async with session.begin(): yield session`.
- **Payload SHA:** `cb14704`

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
| UI-TRUTH-001B | Next: roadmap consistency guard (or G1 fix) | 🚧 awaiting prioritisation |
| PLAYER-IMPORT-001 | Deferred: player import (PLAYER-AUD-001 recommendation) | ⏸️ deferred |

## UI-TRUTH-001 — Feature Truth Registry & Smoke Proof 🚧 in progress

**New Done Gate for business functions:**
- Was: backend tests + API proof = feature done.
- Now: backend + **reachable UI** + green UI-smoke = feature done.
- UI-smoke runs against clean-boot stack, uses only real UI clicks (no direct goto, no API, no localStorage).

### UI-TRUTH-001A ✅ RESOLVED — harness + G1 proof

- **Feature registry:** `docs/product/feature-registry.yaml` — campaign.create as first entry.
- **Smoke harness:** `tests/ui-smoke/conftest.py` — Playwright, login-only `page.goto()`, stable `#id` selectors.
- **G1 proof:** `test_uismoke__campaign_create` — break-glass admin → login → sidebar → campaign list → no «Создать кампанию» button.
- **Run:** `scripts/ui-smoke-audit.sh` (not blocking CI, `UI_SMOKE_RUN=1` gate).
- **CI (ordinary):** #29656035552 ✅ green — ui-smoke excluded via `pytest_ignore_collect` when `UI_SMOKE_RUN` not set.
- **CI (smoke):** not in CI pipeline — manual audit only. When invoked, expected-red on G1.

### Confirmed Gaps (G1–G4)

| Gap | Description | Status |
|-----|-------------|--------|
| G1 | CampaignListPage: no «Создать кампанию» button → /campaigns/new unreachable by real user | ✅ confirmed by UI-smoke |
| G2 | UsersPage: creates only local_advertiser; no role/permission assignment UI | 🟡 confirmed (audit) |
| G3 | AdvertisersPage: list/detail only; no UI for creating advertiser org | 🟡 confirmed (audit) |
| G4 | ADSettingsPage: GET / POST test only; no save/persist | 🟡 confirmed (audit) |

### Next after UI-TRUTH-001A

roadmap-consistency or G1 fix (add «Создать кампанию» button), NOT PLAYER-IMPORT.

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
