# RF-00 — пересверка находок ревью `main @ 8ad0228` на `develop @ b166419`

> ## ⚠️ НЕ КАНОН — наблюдение на момент времени
>
> | | |
> |---|---|
> | **Тип** | Аудит-сверка (запись, не редактируется после публикации) |
> | **Снято на** | `develop @ b166419` (CI `Phase 1 — Quality Gates` run 33735361730 → success) |
> | **Дата** | 2026-09-27 |
> | **Предмет** | Статус каждой находки `2026-09-27-claude-code-review-main-8ad0228.md` на актуальном develop |
> | **Автор** | Claude Code, этап RF-00: 5 read-only агентов по областям + выборочная перепроверка |
> | **Строк сверки** | 94: 4 исправлено · 3 частично · 87 актуально · 0 неприменимо (открытых 90) |
> | **Статус** | Ожидает решения владельца (новые задачи и карточки RF-01…) |
> | **Отменён** | — |
>
> **Не переопределяет Tier 1–2 `AGENTS.md`.** Исполняемый статус находок — `PROJECT_STATE.md`;
> очерёдность — `docs/product/roadmap.yaml` после решения владельца.

## Метод

- Код на `8ad0228` (`git show`) против рабочего дерева `b166419`; коммиты `git log 8ad0228..b166419 -- <paths>`.
  `main` — предок `develop` (64 коммита впереди). PR #8 смержен в `main` как `8ad0228` (GitHub API);
  его находки — P0-10 и P1-18.
- Только чтение кода. Тесты, PostgreSQL, NATS, MinIO, сеть не запускались. Статус с пометкой
  «вероятно» требует живой инфраструктуры для доказательства.
- Составные находки разбиты на подстроки (`.a`, `.b`…); P2 и пробелы тестов получили ID
  (`P2-I*` infra, `P2-B*` backend, `P2-D*` домен, `P2-P*` плеер, `P2-F*` фронтенд, `T1…T14`).
- Статусы: `исправлено` (коммит + file:line), `актуально` (file:line на b166419), `частично`, `неприменимо`.
- Колонка «roadmap»: задача `roadmap.yaml`, которая **реально** покрывает дефект; «новая» — не покрывает никакая.
- Выборочно перепроверено вручную: P0-2, P0-5, P0-6, P0-7, P0-12.d, P0-13, P1-5, P1-7, P1-8, P1-17, P2-D1, P2-I11, T7.

## Сводка

| Группа | Строк | Исправлено | Частично | Актуально |
|---|---|---|---|---|
| P0 | 20 | 1 (P0-13) | 1 (P0-10.b) | 18 |
| P1 | 22 | 1 (P1-5) | 1 (P1-15) | 20 |
| P2 | 38 | 0 | 1 (P2-F3) | 37 |
| Пробелы тестов | 14 | 2 (T5, T6) | 0 | 12 |
| **Итого** | **94** | **4** | **3** | **87** |

`packages/domain/**` и `packages/services/**` между `8ad0228` и `b166419` не менялись; pilot compose
не менялся. Исправления на develop: API-TX-BOUNDARY-001 (`32948f3`, `4e4a3e5`) и RM-TECH-210 (`062c16f`).

## P0

| ID | Статус | Доказательство на b166419 | Коммиты | Тест | roadmap | 2026-08-26 / PROJECT_STATE |
|---|---|---|---|---|---|---|
| P0-1 | актуально | `infra/compose/docker-compose.pilot.yml:90-100` — `create-app-role.py` не вызывается, `POSTGRES_APP_PASSWORD` не передаётся | — (обход: `scripts/deploy/local_stand.py:551-584`) | нет | новая | — / `PROJECT_STATE.md:395` |
| P0-2 | актуально | pilot compose `:151-161` без `CORS_ALLOWED_ORIGINS`; `apps/device-gateway/main.py:229`; `packages/security/config.py:349-352` | `1f97c58` (обход только в overlay стенда) | `tests/test_local_stand.py::test_pilot_compose_still_omits_cors_for_device_gateway` **закрепляет дефект** | новая | — / `PROJECT_STATE.md:339` |
| P0-3 | актуально | pilot compose `:151-161` без `JWT_AUDIENCE` (есть только у control-api `:120`); fallback audience = issuer только в `_validate_dev` `config.py:257-258`; `packages/security/jwt.py:70` сверяет с `""`; `_validate_production` `config.py:311-335` пустой audience принимает; device-токен выпускает control-api (`packages/api/device_routes/onboard.py:151`) со своей audience | — | нет | новая | — / — |
| P0-4 | актуально | compose `:180-194`; `packages/domain/delivery.py:703-704`, глотается `:760-778`; ack — `packages/services/campaign_event_handler.py:112-124` | — | нет | новая (DLQ — RM-TECH-242/243) | — / — |
| P0-5 | актуально | `scripts/ci/verify-pilot-run.sh:72` `ENVIRONMENT=dev`; `:120-128` ручной CREATE ROLE; `:73-74,161-164` версия из своего env; `:134-139,148-153` таймауты без fail; `:76` `RMP_SCHEMA_HEAD=036` при head `037` | `da8d514`, `c088111` (только head) | нет | новая | — / `PROJECT_STATE.md:395,410` («Verify green») |
| P0-6 | актуально | `packages/api/dependencies.py:125-150`; `packages/domain/repository.py:155-176` (права всех ролей, scoped тоже); `packages/api/identity_routes/users.py:398-467` без запрета self-assign и иерархии | — | нет | новая; пересекается по коду с RM-STAB-004 (S, in_progress: `resolve_scope_context`, OD-044) | canon-and-architecture §2.4 / — |
| P0-7 | актуально | `packages/auth/repository.py:182` (`rotated_at IS NULL`) → replay-ветка `packages/auth/service.py:474-481` недостижима; ротация без блокировки `service.py:495-497`, `repository.py:201-209`; 401 без commit `packages/api/auth.py:190-196` | — | `tests/test_phase3_auth_service.py::TestRefreshTokenFamilyRevoke::test_replay_calls_family_revoke` мокает поиск и **маскирует дефект** | новая | — / — |
| P0-8 | актуально | `packages/domain/scopes.py:124,133,139`; `packages/api/dependencies.py:228` | — (`864293f` снял `campaigns.manage` с `advertiser`, модель не изменилась) | нет | новая; пересекается по коду с RM-STAB-004 (S, in_progress) | codex-independent-audit C3 (смежно) / — |
| P0-9 | актуально | `packages/domain/repository.py:1595-1629` (`setattr` любых kwargs, `:1625`); окно договора пропускается при `contract is None` `:1796`; валидаторы `:1460,1482` вызываются только в `create_campaign` | — | нет | новая | — / — |
| P0-10.a | актуально | все `${{ inputs.* }}` в `run:`: `.github/workflows/publish-pilot-images.yml:47-48,54-56,77-81,88,183,189,192-193`; `verify-pilot-images.yml:44-51,66,74,89-91` — `${{ inputs.* }}` в `run:` | — | нет | новая | — / — |
| P0-10.b | частично | `scripts/deploy/pilot_host_preflight.py:529-542` проверяет анонимный доступ, но первый digest (`:510-515`), fail-open при исключении (`:541-543`) и при любом `returncode != 0`, включая сетевую ошибку (`:534-537`), в CI `--skip-registry` (`phase1-ci.yml:757`) | `785f70f` | `tests/test_pilot_host_preflight.py:208` `skip_registry=True`; проверки registry нет | новая | — / `PROJECT_STATE.md:394,405-411` (старые пакеты PUBLIC) |
| P0-10.c | актуально | экспозиция — из `docker-compose.phase1.yml:27,58,69-70,86-87` (Postgres/MinIO/NATS/Redis на 0.0.0.0, файл не менялся); `infra/compose/docker-compose.preview.yml:9-12` лишь помечен SUPERSEDED и добавляет redis `:24-25` | `00d75a6` (только шапка) | нет | новая | — / — |
| P0-11.a | актуально | `repository.py:4995-5043` идемпотентность по `campaign_placement_id`; цикл флайтов `:1842-1862`; реактивация released-броней `:5021-5027` без проверки ёмкости | — | нет (`tests/test_s079_inventory_reservations.py::test_reserve_idempotent` покрывает только идентичный повтор — корректен, дефект не закрепляет) | RM-TECH-203 (частично) | canon-and-architecture §22.4 / — |
| P0-11.b | актуально, вероятно | `repository.py:4584-4614` без `FOR UPDATE`; check-then-add `:5080,5103` | — | нет | RM-TECH-203 | canon-and-architecture §22.4 / — |
| P0-11.c | актуально | `repository.py:1832` (и `:5304,5595,5979`) бронирует только `display_surface_id`; `delivery.py:171-204` разворачивает группы в манифест | — | нет | RM-TECH-241 (частично) | — / — |
| P0-12.a | актуально | `repository.py:3201-3235` последний манифест устройства; `DeliveryManifest.campaign_id` одно; генерация по кампании `delivery.py:634-700` | — | нет | новая | — / — |
| P0-12.b | актуально | `campaign_event_handler.py:31-39` без paused/completed/archived; выдача не проверяет статус `repository.py:3225-3230` | — | нет | RM-TECH-242 | — / — |
| P0-12.c | актуально | `delivery.py:677` `weight = sort_order or 1`; `:683-684` daypart = None | — | нет | RM-TECH-248 (частично) + новая (SoV→weight) | — / — |
| P0-12.d | актуально | `packages/domain/__init__.py:79-84` — у `PAUSED` нет переходов | — | `tests/test_campaign_status_guard.py::test_paused_to_active_rejected` **закрепляет дефект** | RM-TECH-245 | — / — |
| P0-13 | **исправлено** | `packages/api/dependencies.py:21-42`; все вызовы `Depends(get_db, scope="function")` (0 без scope); `apps/*/requirements.txt:5` `fastapi>=0.121.0` | `32948f3`, `4e4a3e5` | `tests/test_api_tx_boundary.py::test_commit_failure_cannot_return_2xx` и др. | вне roadmap (API-TX-BOUNDARY-001); пин версии → RM-STAB-009 | code-and-security §2.5 / `PROJECT_STATE.md:288-292` |

## P1

| ID | Статус | Доказательство на b166419 | Коммиты | Тест | roadmap | 2026-08-26 / PROJECT_STATE |
|---|---|---|---|---|---|---|
| P1-1 | актуально | `packages/domain/pop_ingestion.py:112-116`; `models.py:1155` `String(36)` vs `schemas.py:959` `max_length=64`; naive `rendered_at` `:172` | — | нет | RM-TECH-227 (частично) | — / — |
| P1-2 | актуально | `pop_ingestion.py:240-300` без окна флайта и статуса кампании; `_resolve_manifest` `:51-58` без фильтра статуса | — | нет | RM-TECH-248 (частично) | — / — |
| P1-3 | актуально | `repository.py:1561-1580`; `create_delivery_manifest_record` (`:2868+`); DEFAULT `020_multitenancy_retailer_id.py:137-139` | — | нет | RM-TECH-229 (частично) | code-and-security §2.1 (смежно по миграции 020, другой дефект) / — |
| P1-4 | актуально, вероятно | `repository.py:2440-2485` таргеты не сверяются; `028_public_advertiser_application_insert.py:19-23` `WITH CHECK (true)` без `TO` | — | нет | RM-STAB-004 / RM-TECH-229 (частично) | — / — |
| P1-5 | **исправлено** | `packages/api/device_routes/onboard.py:47-61,83` bootstrap-контекст; `:172` `set_rls_context` на `/identity/device-codes`; миграция `037_device_onboarding_bootstrap_rls.py:37-66` | `062c16f` | `tests/behavioral/test_edge001_device_onboarding.py::TestRMTech210BootstrapRLS::*` | RM-TECH-210 (done) | code-and-security §3.2 / `PROJECT_STATE.md:5-15` |
| P1-6.a | актуально, вероятно | `campaign_event_handler.py:421-423` `session_setup` вне try, rollback `:439` → `run()` `:385-387` останавливает цикл; `health_state.py:59` не следит за consumer/БД | — | нет | новая | — / — |
| P1-6.b | актуально | `packages/services/jetstream_provisioning.py:45` `max_deliver=-1`; DLQ consumer нет | — | нет | RM-TECH-243 (частично, relay) | — / — |
| P1-7 | актуально, вероятно | `outbox_relay.py:145` subject = event_type; stream только `campaign.>` (`jetstream_provisioning.py:151-152`, `apps/orchestrator-worker/main.py:120,131`); вне stream: `creative_asset.created`, `emergency.changed`, `pop.*`, `delivery.manifest.*` | — | нет | новая | — / `PROJECT_STATE.md:440` |
| P1-8 | актуально, вероятно | `apps/orchestrator-worker/main.py:489-496` сессия без `set_worker_admin_context` (у relay/consumer есть: `:279,410,460`); FORCE RLS `006_campaign_domain.py:111,135` | — | `tests/behavioral/test_campaign_completion.py` идёт под владельцем, RLS не проверяет | новая | code-and-security §3.2 BEHAVIORAL-ADMIN-MASK-001 (механизм маскировки) / `PROJECT_STATE.md:1391-1413` («real DB proof») |
| P1-9 | актуально | `expire_inventory_reservations` (`repository.py:5216`) не вызывается; правила по `now` `:5387-5400`; `internal_block` `:5492-5502` | — | `tests/test_s080_inventory_conflicts.py::test_internal_block_conflict` **закрепляет дефект** | RM-TECH-203 (частично) | — / — |
| P1-10 | актуально | `packages/auth/ad_provider.py:220-231` анонимный bind первым; `start_tls` нет; sync ldap3 из async (`service.py:211`); `identity_routes/ad_settings.py:62,82-99,120` | — | нет | RM-TECH-252, RM-STAB-012 (частично) | — / `PROJECT_STATE.md:1779` (другой дефект) |
| P1-11.a | актуально | `identity_routes/users.py:470-503` `remove_role` без защиты последнего админа (в `deactivate_user` есть, `:232-238`) | — | нет | новая | — / — |
| P1-11.b | актуально | `apps/advertiser-web/src/auth/AuthContext.tsx:53-59,84-90`; `components/ProtectedRoute.tsx:65-97` — только баннер `ProfilePage.tsx:160` | — | нет | новая | — / — |
| P1-12 | актуально | `apps/admin-web/src/pages/CampaignDetailPage.tsx:553-557,560-578` — цикл при любой ошибке загрузки | — | нет | новая | — / — |
| P1-13.a | актуально | `apps/admin-web/src/api/client.ts:98-101`, `apps/advertiser-web/src/api/client.ts:92-95` — 401 → логаут, refresh только при монтировании | — | нет | новая | — / — |
| P1-13.b | актуально | `AuthContext.tsx` (admin `:41-51`, advertiser `:46-63`) без single-flight; бэкенд — P0-7 | — | нет | новая | — / — |
| P1-13.c | актуально | `packages/api/auth.py:45-57` одна cookie `refresh_token`, path `/api/v1/auth`; порталы на одном хосте (`docker-compose.pilot.yml:215,229`) | `9a4855a`, `269e059` (guard admin-web, смягчение) | `apps/admin-web/src/__tests__/cross-portal-guard.test.tsx` (guard) | новая | — / `PROJECT_STATE.md:237` |
| P1-14 | актуально | advertiser `CampaignDetailPage.tsx:1017-1022,1043-1047`; advertiser `CampaignCreatePage.tsx:158-159`; admin `CampaignCreatePage.tsx:207-208` | — | нет | новая (смежно RM-TECH-248, OD-012) | open-legacy-items-triage OD-012 (тема) / — |
| P1-15 | частично | advertiser `CampaignDetailPage.tsx:88,96`, `CampaignListPage.tsx:24`; admin `UsersPage.tsx:205`, `CampaignListPage.tsx:51-53` | `27dc397` (смягчено подписью «фильтр по странице»; дефект поиска/пагинации не исправлен) | `apps/admin-web/src/__tests__/ux-primitives.test.tsx` (подпись) | RM-UX-002 (частично) | — / `PROJECT_STATE.md:150` |
| P1-16 | актуально | `infra/compose/docker-compose.phase1.yml:46,86` оба порт 9000 (факт); `:74` healthcheck `nats server check` — вероятно, отсутствие CLI в `nats:2-alpine` требует проверки образа | — | нет | новая | — / `PROJECT_STATE.md:395` (исправлено только в pilot) |
| P1-17 | актуально | downgrade `020_*.py:272-277`, `019_*.py:64`, `033_*.py:160-185`; `013_*.py` оставляет FORCE; для `034` неприменимо | — (035–037 корректны) | нет | новая (область RM-TECH-229) | code-and-security `:65-79` / `PROJECT_STATE.md:503` |
| P1-18 | актуально | `publish-pilot-images.yml:192` `--clobber`; литерал registry в ≥ 11 местах; `scripts/deploy/build-images.sh:155` игнорирует `--registry`; `scripts/deploy/generate_release_lock.py:82` `oci.source`; нет runbook `docker login ghcr.io` | `4635e72` (не затрагивает) | нет | новая | — / `PROJECT_STATE.md:406` (`oci.source` — решение) |

## P2

| ID | Статус | Доказательство на b166419 | roadmap | Примечание |
|---|---|---|---|---|
| P2-I1 | актуально | `infra/compose/Dockerfile.service:1-34` без `USER` | новая | |
| P2-I2 | актуально | `.github/workflows/phase1-ci.yml` без `permissions:` | новая | |
| P2-I3 | актуально | actions по тегам; `phase1-ci.yml:230` `minio/minio:latest`; `:208,512` `postgres:16-alpine` | новая (RM-STAB-009 — только pip) | code-and-security §3.4 CI-DEPS-UNPINNED-001 |
| P2-I4 | актуально | `phase1-ci.yml:74` `pip … \| tail -1` без pipefail | RM-STAB-009 (частично) | |
| P2-I5 | актуально | `publish-pilot-images.yml:67-70` checkout без `ref:` при комментарии «main» `:14-16` | новая | |
| P2-I6 | актуально | `Dockerfile.service:10`; `apps/admin-web/Dockerfile:16,43`; `apps/advertiser-web/Dockerfile:16,40` | новая | |
| P2-I7 | актуально | `infra/compose/docker-compose.observability.yml:57-60`; `infra/observability/prometheus.yml:13-27` | новая | |
| P2-I8 | актуально | `030_*.py:58` без FORCE RLS | новая (область RM-TECH-229) | |
| P2-I9 | актуально | `apps/control-api/alembic/env.py:21-25` fallback localhost, `%` не экранируется | новая | |
| P2-I10 | актуально | `phase1-ci.yml:313,583`; `scripts/ci/backup-restore-drill.sh:128` `GRANT ALL` | новая | |
| P2-I11 | актуально | `apps/control-api/main.py:150` `dev_mode` для всего, кроме `production` | новая | |
| P2-B1 | актуально | `packages/observability/rate_limit.py:35-38,55-56,93-101` | RM-STAB-013 | |
| P2-B2 | актуально | `packages/auth/service.py:83-146` | новая (частично RM-STAB-013) | |
| P2-B3 | актуально | `packages/security/config.py:519` `!=` | новая | |
| P2-B4 | актуально, вероятно | `packages/services/storage.py:39,51,125-141,167-181` | RM-STAB-016 | |
| P2-B5 | актуально | `identity_routes/inventory.py:165-202`; `repository.py:4848-4869` | новая | |
| P2-B6 | актуально | `repository.py:4548-4549` (accept-invite, не `_generate_user_code`) | новая | |
| P2-B7 | актуально, вероятно | `repository.py:2732-2760` без `SKIP LOCKED` | RM-TECH-243 | |
| P2-B8 | актуально, вероятно | `delivery.py:670-777` без savepoint; версия max+1 `repository.py:2932-2943` | новая | |
| P2-B9 | актуально | `packages/api/auth.py:280-289` | новая | |
| P2-B10 | актуально | `packages/observability/__init__.py:26-34,104` регистр заголовка | новая | |
| P2-B11 | актуально | `apps/orchestrator-worker/main.py:150,221,419-421`; `ad_provider.py:142-164` | RM-STAB-013 | |
| P2-B12 | актуально | `packages/api/auth.py:309-373`; `identity_routes/users.py:206-261`; `identity_routes/ad_settings.py:82-99` | новая | canon-and-architecture:72, codex-independent-audit:27 (только импорты) |
| P2-D1 | актуально | `repository.py:1861,5335,5617,6005` `or 100` при `ge=0` | новая | |
| P2-D2 | актуально | `repository.py:1568` бюджет только хранится | новая | |
| P2-D3 | актуально | `commerce_repository.py:56-78` `valid_to` не проверяется | новая | |
| P2-D4 | актуально, вероятно | `repository.py:4249-4271`; индекс `024_emergency_overrides.py:42` не уникальный | RM-TECH-254 (частично) | |
| P2-D5 | актуально | `identity_routes/campaigns.py:754-755`; причина — naive/aware `common.py:64,73-76` (и в POST) | RM-TECH-248 (частично) | |
| P2-P1 | актуально | `apps/kso-player-client/player_client/auth.py:40-42` — несуществующий `/api/v1/auth/token` | RM-TECH-207A/207B | Protected: device auth |
| P2-P2 | актуально | `apps/kso-player-client/main.py:5` — только форма `python -m` из docstring; runbook-команда рабочая | RM-TECH-207B | |
| P2-P3.a | актуально | `player_client/manifest.py:65-73` fail-open при пустом ключе (`config.py:70`) | RM-STAB-010, RM-TECH-207B | Protected: KSO runtime |
| P2-P3.b | актуально | `packages/contracts/manifest_signing.py:29-49` общий HMAC | RM-STAB-010 | canon-and-architecture §B1; codex-independent-audit п.3, п.6 |
| P2-F1 | актуально | admin `CampaignDetailPage.tsx:279-324,263-273` | новая | |
| P2-F2 | актуально | `apps/admin-web/src/components/AdvertiserWizard.tsx:171-191,236-258` | новая | мастер в admin-web |
| P2-F3 | частично | исправлено `864293f` в advertiser client; осталось `CreativeLibraryPage.tsx:100,176`, admin `api/client.ts:48` | новая | `PROJECT_STATE.md:194,1111` |
| P2-F4 | актуально | admin `LoginPage.tsx:31-35`; advertiser `LoginPage.tsx:18-23` | новая (бэкенд — RM-STAB-013) | |
| P2-F5 | актуально | admin `AdvertisersPage.tsx:1016-1024`; `api/campaigns.ts:213-221` | новая (смежно RM-UX-009) | |
| P2-F6 | актуально | admin `CampaignDetailPage.tsx:117-125`; `packages/domain/schemas.py:426,459` | новая | |

## Пробелы тестов

| ID | Статус | Доказательство | roadmap |
|---|---|---|---|
| T1 | актуально | только `tests/behavioral/test_auth_dual_e2e.py::TestRefreshLogoutCycle::test_refresh_replay_protection` (401 на повтор) | вместе с P0-7 |
| T2 | актуально | `tests/test_phase3_identity_api.py:1201-1307` — только успех, на моках | вместе с P0-6 |
| T3 | актуально | мульти-org теста нет | вместе с P0-8 |
| T4 | актуально | теста `update_campaign` с чужим договором нет | вместе с P0-9 |
| T5 | **исправлено** | `tests/test_api_tx_boundary.py::test_commit_failure_cannot_return_2xx` (`32948f3`) | — |
| T6 | **исправлено** | `tests/behavioral/test_edge001_device_onboarding.py::TestRMTech210BootstrapRLS::test_device_codes_and_onboard_work_without_elevation` (`062c16f`) | RM-TECH-210 |
| T7 | актуально | `tests/test_phase3_security.py:634` `TestScopeAdminReset` собирается только job python-tests без postgres → skip; behavioral-job собирает только `tests/behavioral/` | новая |
| T8 | актуально | concurrency-тестов брони нет | вместе с P0-11 |
| T9 | актуально | теста нет | вместе с P0-12 |
| T10 | актуально | `tests/behavioral/test_pop_ingestion.py` не покрывает FK/длину/naive | вместе с P1-1 |
| T11 | актуально | `tests/test_phase4_2b_consumer.py` — только ошибка handler | вместе с P1-6 |
| T12 | актуально | import smoke `phase1-ci.yml:67-88` только `ENVIRONMENT=dev` | вместе с P0-2…P0-4 |
| T13 | актуально | vitest без `TZ` | вместе с P1-14 |
| T14 | актуально | нет fake timers на истечение access | вместе с P1-13 |

## Уточнения к исходному ревью

1. **P0-5:** `Dockerfile.service:345-350` не существует (34 строки). Суть: `build-images.sh:89-91` передаёт
   `--build-arg RMP_VERSION`, Dockerfile его не объявляет — `/version` отражает env.
2. **P0-4:** воркер стартует; падает каждый манифест, сообщение ack'ается.
3. **P0-10:** preview compose публикует только redis; открытые порты — из `docker-compose.phase1.yml`.
   Токен `packages: write` только в publish.
4. **P0-11.a:** серьёзнее описания — повторная бронь реактивирует released-строки без проверки ёмкости;
   ключ (placement, slot) уже есть в БД (`uq_inventory_booking_placement_slot`), миграция не нужна.
5. **P0-12:** wire-схема `universal-manifest-v1` уже допускает мультикампанийный playlist, daypart, weight;
   «Manifest v2» как новая схема не обязателен, но меняются генератор, хранение, атрибуция PoP, плеер и
   ADR-016 — Protected Boundary «generated manifest compatibility».
6. **P1-6:** цикл убивают только сбой `session_setup` и сбой rollback; ошибки handler уходят в nak.
7. **P1-10:** анонимный bind — факт кода (пробуется первым), не «вероятно».
8. **P1-12:** цикл при любой ошибке, в двух эффектах.
9. **P1-17:** для 034 неприменимо; для 013 хуже — остаётся FORCE.
10. **P1-18:** литерал registry в ≥ 11 местах; строка `build-images.sh` — 155.
11. **P2-P2:** рабочая команда runbook; ломается только форма из docstring.
12. **P2-B6:** коллизия — в accept-invite, серверный `_generate_user_code` исправлен до `8ad0228` (`ed8cf22`).
13. **P2-D5:** причина 500 — naive datetime, и в POST тоже.

## Для решения владельца

**Расхождения канона с кодом** (сообщаются, не исправлялись — `CLAUDE.md`: противоречие = стоп):

| Канон | Код | Находка |
|---|---|---|
| `PROJECT_STATE.md:1391-1413` LIFECYCLE-COMPLETE-001/-FU «real DB proof» | `tests/behavioral/test_campaign_completion.py` идёт под владельцем БД; в воркере нет admin-контекста | P1-8 |
| `PROJECT_STATE.md:395,410` pilot «Verify green» | verify в `ENVIRONMENT=dev`, ручной CREATE ROLE, таймауты не роняют; head 036 при 037 | P0-5 |
| `canon-and-architecture.md` §2.4 арендность fail-closed | `retailer_id` по DEFAULT, таргеты не сверяются | P1-3, P1-4 |

**Тесты, закрепляющие дефекты** — исправление потребует их замены (не ослабления) с решением владельца:
`tests/test_local_stand.py::test_pilot_compose_still_omits_cors_for_device_gateway` (P0-2),
`tests/test_phase3_auth_service.py::TestRefreshTokenFamilyRevoke::test_replay_calls_family_revoke` (P0-7, мок),
`tests/test_campaign_status_guard.py::test_paused_to_active_rejected` (P0-12.d),
`tests/test_s080_inventory_conflicts.py::test_internal_block_conflict` (P1-9).

**Protected Boundaries**, которые затронут исправления: Docker/deployment (P0-1…P0-5, P0-10, P1-16, P1-18,
P2-I*); campaign publication flows и generated manifest compatibility (P0-12, P1-2); device auth / KSO
runtime (P2-P1, P2-P3); destructive migrations (P1-17 — downgrade).

**Внешние действия владельца:** закрыть видимость старых публичных пакетов GHCR (P0-10.b) — по коду
не проверяемо, сеть не использовалась.

Предлагаемые новые задачи и черновики карточек RF-01… — `docs/remediation/stages.md`, раздел
«Черновики (RF-00)». Статус `planned` — только после решения владельца.
