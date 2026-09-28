# Ревью кода по областям — main @ 8ad0228

> ## ⚠️ НЕ КАНОН — наблюдение на момент времени
>
> | | |
> |---|---|
> | **Тип** | Аудит (запись, не редактируется после публикации) |
> | **Снято на** | `main @ 8ad0228` (2026-08-24). **`develop` на 64 коммита впереди** (`b166419`, 2026-09-03) — часть находок там может быть исправлена |
> | **Дата** | 2026-09-27 |
> | **Предмет** | Полное ревью: backend API, домен, auth/security/воркеры, фронтенды, infra/CI, PR #8 |
> | **Автор** | Claude Code: 5 read-only ревьюеров по областям + ревью диффа PR #8 |
> | **Открытых находок** | 13 P0 · 18 P1 · ~40 P2 (на `main`; статус на `develop` — этап RF-00) |
> | **Отменён** | — |
>
> **Не переопределяет Tier 1–2 `AGENTS.md`.** Строки верны для `main @ 8ad0228`.
> **Перед действием перепроверьте против `develop`** — это задача этапа RF-00
> (`docs/remediation/stages.md`). Исполняемый статус находок — `PROJECT_STATE.md`.

Метод: чтение кода и путей вызова. Падения pilot-конфигурации (P0-2, P0-3, P0-4) воспроизведены
импортом в scratch-venv с pilot-env. Живых PostgreSQL/NATS не было; зависящие от них находки
помечены «вероятно». Полная версия с диаграммами: https://claude.ai/code/artifact/21989b86-400d-41eb-9cd3-8496b98d78b4

## P0 — блокеры

### Pilot-контур не поднимается

| ID | Где (на main) | Дефект | Последствие | Фикс |
|---|---|---|---|---|
| P0-1 | `infra/compose/docker-compose.pilot.yml:90-100`, `infra/compose/grant-app-role.py:25-28` | Роль `retail_media_app` никто не создаёт; `create-app-role.py` не подключён | `db-migrate` падает, ни один сервис не стартует | Вызывать `create-app-role.py` до grant, передать `POSTGRES_APP_PASSWORD` |
| P0-2 | `docker-compose.pilot.yml:149-161`, `apps/device-gateway/main.py:229`, `packages/security/config.py:270` | device-gateway без `CORS_ALLOWED_ORIGINS`; pilot валидируется как production | crash-loop на импорте (воспроизведено) | Пробросить CORS или не требовать его для сервисов без браузера |
| P0-3 | тот же блок compose, `packages/security/jwt.py:59-72`, `config.py:231-258` | device-gateway без `JWT_AUDIENCE` (в compose он есть только у control-api, строки 120-121) | все device-токены → 401 (воспроизведено) | Добавить `JWT_AUDIENCE`; требовать непустой в `_validate_production` |
| P0-4 | `packages/domain/delivery.py:703` (глотается на `:760`), compose `:180-193` | orchestrator без CORS и `METRICS_AUTH_TOKEN` → `get_security_config()` падает | каждый манифест failed, сообщение ack'ается (воспроизведено) | Worker-профиль валидации; не ack'ать при ошибке конфигурации |
| P0-5 | `scripts/ci/verify-pilot-run.sh:72, 120-170`, `infra/compose/Dockerfile.service:345-350` | Verify в `ENVIRONMENT=dev`, сам создаёт роль, сверяет версию с собственным env; таймауты ожидания не роняют проверку | P0-1…P0-4 невидимы, verify зелёный | `ENVIRONMENT=pilot`, без ручного CREATE ROLE, версия из образа, `exit 1` по таймауту |

### Безопасность

| ID | Где | Дефект | Сценарий | Фикс |
|---|---|---|---|---|
| P0-6 | `packages/api/dependencies.py:107-131`, `packages/domain/repository.py:155`, `packages/api/identity_routes/users.py:403` | `require_permission` учитывает права scoped-ролей (против ADR-009); `assign_role` без запрета self-assign и иерархии | scoped `system_admin`/`security_admin` → `PUT /users/{self}/roles` → глобальный админ | Только `global_permissions`; запрет self-assign и ролей выше своей |
| P0-7 | `packages/auth/repository.py:182, 201-210`, `packages/auth/service.py:475-513`, `packages/api/auth.py:~197` | Отзыв семьи недостижим (фильтр `rotated_at IS NULL`), откатывается 401; ротация без блокировки | украденный refresh живёт; два параллельных `/refresh` → две ветки | Поиск по хэшу без фильтра, commit отзыва до 401, `UPDATE … WHERE rotated_at IS NULL RETURNING` |
| P0-8 | `packages/api/dependencies.py:210`, `packages/domain/scopes.py:116-140` | Права не привязаны к конкретному advertiser-scope | роль в org A + membership в org B = `campaigns.manage` в B | `scoped_permissions[(type, id)]` по ADR-009 |
| P0-9 | `packages/domain/repository.py:1595-1630` | `update_campaign` не проверяет принадлежность договора/бренда | PATCH с договором чужой org; проверка окна договора молча пропускается | `_validate_*_belongs_to_org`; ненайденный договор = отказ |
| P0-10 | `.github/workflows/verify-pilot-images.yml:44`, `publish-pilot-images.yml`; GHCR; `infra/compose/docker-compose.preview.yml` | Script injection через `${{ inputs.* }}`; старые пакеты GHCR публичны; preview открывает в LAN Postgres-суперюзера, Redis, MinIO, NATS | команды с токеном `packages: write`; утечка образов; БД доступна из LAN | Inputs через `env:`; закрыть старые пакеты + гейт visibility; порты на `127.0.0.1` |

### Деньги и данные

| ID | Где | Дефект | Сценарий | Фикс |
|---|---|---|---|---|
| P0-11 | `packages/domain/repository.py:1842-1876, 5006, 5068-5105` | Бронь идемпотентна по `placement_id`; счётчики слота без `FOR UPDATE`; групповые таргеты не бронируются | второй флайт без брони; две заявки SoV 100% обе проходят — двойная продажа | Ключ (placement, slot); `FOR UPDATE`; атомарный `SET x = x + :n`; резолв групп |
| P0-12 | `repository.py:3222-3240`, `delivery.py:626-685`, `packages/services/campaign_event_handler.py:31-39`, `packages/domain/__init__.py:83` | Манифест одной кампании на устройство; pause/archive/complete не отзывают; дейпартинг и SoV игнорируются; из `paused` нет переходов | оплаченная кампания не крутится; кампания на паузе показывается | Общий манифест (Manifest v2); revoke на lifecycle; переходы из `paused` |
| P0-13 | `packages/api/dependencies.py:21-26` | Commit в teardown `get_db` после отправки ответа (FastAPI ≥0.118) | 2xx клиенту, данные откатились | Commit до ответа / `Depends(scope="function")` + пин версии |

## P1

| ID | Область | Где | Дефект |
|---|---|---|---|
| P1-1 | PoP | `packages/domain/pop_ingestion.py:103-116`, `models.py:1163`, `schemas.py:958-970` | Одно плохое событие (FK на asset, длина 64 vs 36, naive `rendered_at`) откатывает батч до 500 |
| P1-2 | PoP | `pop_ingestion.py:260-300` | Billing-grade accept без проверки окна флайта и статуса кампании |
| P1-3 | Tenancy | `create_campaign`, `create_delivery_manifest_record`, `reserve_*`; миграция 020 | `retailer_id` не передаётся, работает DEFAULT |
| P1-4 | Tenancy | `repository.py:2440-2485`; миграция 028 | Цели плейсмента не проверяются на ретейлера (вероятно); INSERT заявок `WITH CHECK (true)` |
| P1-5 | Устройства | `packages/api/device_routes/onboard.py:37, 128` | Онбординг без RLS-контекста под NOBYPASSRLS (вероятно) |
| P1-6 | NATS | `campaign_event_handler.py:377-443`, `jetstream_provisioning.py:45` | Consumer умирает при обрыве БД, health зелёный; `max_deliver=-1`, нет DLQ |
| P1-7 | NATS | `packages/services/outbox_relay.py:145`, `apps/orchestrator-worker/main.py:118-121` | Stream `RMP` только `campaign.>`; прочие события → dead_letter |
| P1-8 | Воркеры | `apps/orchestrator-worker/main.py:489-496` | Автозавершение кампаний без admin-контекста — под FORCE RLS видит 0 |
| P1-9 | Инвентарь | `repository.py:5216, 5397-5400, 5492` | TTL броней не вызывается; blackout сверяется с «сейчас»; `internal_block` блокирует всё |
| P1-10 | AD | `packages/auth/ad_provider.py:111-231`, `identity_routes/ad_settings.py:84-99` | Анонимный bind (вероятно); StartTLS не вызывается; sync LDAP в event loop; `users.manage` перенаправляет AD |
| P1-11 | Auth | `identity_routes/users.py:471`; `advertiser-web/src/auth/AuthContext.tsx:94` | Нет защиты последнего админа при снятии роли; `must_change_password` не соблюдается |
| P1-12 | Фронтенд | `admin-web/src/pages/CampaignDetailPage.tsx:553-575` | Бесконечный цикл запросов при 403/500 |
| P1-13 | Фронтенд | `*/src/auth/AuthContext.tsx`, `*/src/api/client.ts` | Нет тихого refresh (15 мин → логаут); гонка ротации; общая cookie двух порталов |
| P1-14 | Фронтенд | `advertiser-web/src/pages/CampaignDetailPage.tsx:1013-1044`, `CampaignCreatePage.tsx:155`, `admin-web/src/pages/CampaignCreatePage.tsx:207` | Даты сдвигаются на UTC-смещение при сохранении; время без зоны; потеря последнего дня |
| P1-15 | Фронтенд | `advertiser-web/src/pages/CampaignDetailPage.tsx:83-96`, `admin-web/src/pages/UsersPage.tsx:205`, `CampaignListPage.tsx:50` | Лимит 50 без пагинации; фильтр статуса по текущей странице |
| P1-16 | Infra | `infra/compose/docker-compose.phase1.yml:45-46, 74, 86` | clickhouse и minio на порту 9000; healthcheck nats через отсутствующий CLI |
| P1-17 | Миграции | `alembic/versions/020_*.py:272-286` (и 013, 019, 033, 034) | Downgrade оставляет RLS без политик — default-deny |
| P1-18 | PR #8 | `publish-pilot-images.yml:192`, `scripts/deploy/build-images.sh:143`, `scripts/ci/verify-pilot-run.sh:50`, `scripts/deploy/generate_release_lock.py:82` | `--clobber` переписывает lock; registry в 7 местах; lock утверждает удалённый `oci.source`; нет runbook `docker login ghcr.io` |

## P2 (кратко)

- **Infra/CI:** `Dockerfile.service` без `USER` (root); `phase1-ci.yml` без `permissions:`, actions/образы не запинены, `pip | tail` без pipefail; tooling в publish с ref запуска; базовые образы по тегу; observability-compose (`rmp-net`, нет bearer); миграция 030 без FORCE RLS; `alembic/env.py` (fallback на localhost, `%` в пароле); `GRANT ALL` в CI/drill; readiness `main.py:150` пропускает BYPASSRLS вне `production`.
- **Backend/security:** rate-limit только при `ENVIRONMENT=production`, обход XFF, in-memory; тайминг-энумерация логинов и lockout break-glass; `/metrics` сравнение не constant-time; MinIO `secure=False`, presigned PUT живёт после complete; inventory ValueError → 500, неограниченный диапазон; `users.code` коллизия; outbox без `SKIP LOCKED`; `delivery.py` `except Exception` без savepoint; `/auth/me` глотает исключения; correlation-id не подхватывается; `NATS_URL` и AD-логины в логах; логика в роутерах (ADR-014).
- **Домен:** `share_of_voice_pct or 100`; бюджеты не проверяются; истёкший тариф; двойной emergency override; частичные апдейты флайта → 500.
- **Плеер:** не умеет аутентифицироваться; `ModuleNotFoundError` при документированном запуске; подпись fail-open, общий HMAC.
- **Фронтенд:** гонка между кампаниями; дубли в мастере рекламодателя; «[object Object]»; маскировка 503/429; PATCH договора не очищает поля; округление бюджета и `RangeError` валюты.

## Пробелы тестов

Replay/параллельный refresh без моков; эскалация через `roles.manage`; мульти-org пользователь;
PATCH с чужим договором; commit после 2xx; онбординг под NOBYPASSRLS; `TestScopeAdminReset` не
запускается нигде; multi-flight и параллельная бронь; две кампании на устройстве и отзыв при паузе;
poison-событие PoP; обрыв БД в NATS-consumer; smoke-импорт сервисов с pilot-env; даты в UTC+3; сессия дольше TTL.

## Анализ дорожной карты

Выполнен по `docs/product/roadmap-s020-2026-07-10.xlsx` на `main`. На `develop` дорожная карта
переведена на `docs/product/roadmap.yaml` (RM-GOV-001…006), поэтому тот анализ в этот файл не
переносится и требует повторения по новой SSOT (см. документ по ссылке выше).
