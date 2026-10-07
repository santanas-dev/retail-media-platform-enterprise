# Этапы исправлений (RF) — карточки

> **Не канон.** Рабочий план этапов для команд `/start` и `/finish`. Исполняемый статус
> задач и функций ведётся в `PROJECT_STATE.md`, `docs/product/roadmap.yaml` и
> `docs/product/feature-registry.yaml` по правилам `AGENTS.md`. При конфликте побеждает канон.
> Новые этапы появляются здесь только после решения владельца.

Статусы: `planned` → `in_progress` → `ready_to_finish` → `finished` (PR открыт) → `merged`.

## Шаблон карточки

```markdown
## RF-NN — <название>

| Поле | Значение |
|---|---|
| Статус | planned |
| Цель | <одно предложение: что будет доказано> |
| Задачи roadmap.yaml | <ID или «—»> |
| Находки | <ID из аудита или «—»> |
| Скоуп (в) | <файлы/модули/поведение> |
| Скоуп (вне) | <что явно не трогаем> |
| Protected Boundaries | <какие из AGENTS.md разрешены или «нет»> |
| mini-design | да / нет |
| Входные условия | <предыдущий этап смержен; решения OD-…> |
| Гейт | <команды из phase1-ci.yml и тесты, которые должны быть зелёными> |
| Канон, который меняется | <PROJECT_STATE / roadmap.yaml / registry или «только checkpoint PROJECT_STATE»> |
```

---

## RF-00 — Пересверка находок ревью на актуальном develop

| Поле | Значение |
|---|---|
| Статус | finished |
| Цель | Каждая находка ревью `main @ 8ad0228` получает доказанный статус на актуальном `origin/develop` |
| Задачи roadmap.yaml | — (этап производит предложения задач) |
| Находки | Все из `docs/audit/2026-09-27-claude-code-review-main-8ad0228.md` (P0-1…P0-13, P1-1…P1-18, P2, PR #8, пробелы тестов) |
| Скоуп (в) | Чтение кода develop; новый аудит-файл сверки; строки в `docs/audit/README.md`; предложение карточек RF-01… в этом файле; журнал |
| Скоуп (вне) | Любые изменения кода, тестов, CI, compose, миграций, `roadmap.yaml`, `feature-registry.yaml` |
| Protected Boundaries | нет |
| mini-design | нет |
| Входные условия | Клон на `develop`, дерево чистое, кроме локальных исключённых файлов |
| Гейт | (1) у каждой находки статус: `исправлено` (коммит + file:line), `актуально` (file:line на SHA), `частично`, `неприменимо` — 0 без статуса; (2) каждая актуальная находка сопоставлена с задачей `roadmap.yaml` или помечена «новая»; (3) пересечения с `docs/audit/2026-08-26-*` отмечены; (4) ревьюер выборочно перепроверил ≥ 10 статусов, вердикт APPROVE*; (5) CI-проверки документов (`roadmap-governance-guard`, schema) зелёные, если их затрагивает коммит |
| Канон, который меняется | Только checkpoint в `PROJECT_STATE.md` («ожидает решения владельца») |

**Результат для владельца:** таблица «находка → статус на develop → задача roadmap.yaml / новая»,
предложение новых задач для `roadmap.yaml` и черновики карточек RF-01… в порядке, согласованном
со стадиями `roadmap.yaml`. Карточки получают статус `planned` только после решения владельца.

---

## RF-CI — CI снова собирается (внеплановый, решение владельца 2026-09-28)

| Поле | Значение |
|---|---|
| Статус | merged |
| Цель | `Phase 1 — Quality Gates` снова зелёный после внешнего дрейфа (SQLAlchemy 2.1, `minio/minio`, `dl.min.io`) |
| Задачи roadmap.yaml | — (смежно RM-STAB-009 — пины зависимостей) |
| Находки | push-run `fix/RF-00` 36392472274 (6 failure + 3 cancelled); P2-I3 (частично) |
| Скоуп (в) | `phase1-ci.yml`; requirements трёх сервисов; compose restore-drill / phase1 / pilot (образ, healthcheck, `user: "0"` в pilot и phase1); `backup-restore-drill.sh` (`MINIO_SERVER_VERSION`) |
| Скоуп (вне) | Код приложений, тесты (кроме CI-скрипта drill), миграции, переход на SQLAlchemy 2.1, non-root MinIO, зеркало в GHCR |
| Protected Boundaries | Docker/deployment/backup — MinIO в CI, compose restore-drill/phase1/pilot и drill-скрипте (ответ владельца «CI + drill + phase1 + pilot»); `user: "0"` в pilot — одобрено, в phase1 — ожидает подтверждения |
| mini-design | нет |
| Входные условия | решение владельца «вариант 1» |
| Гейт | CI `Phase 1 — Quality Gates` всё зелёное; import boundaries; roadmap guard |
| Канон, который меняется | только checkpoint PROJECT_STATE |

## RF-01 — Refresh-токены: обнаружение повтора и атомарная ротация (решение владельца 2026-09-28)

| Поле | Значение |
|---|---|
| Статус | merged |
| Цель | Повтор ротированного refresh-токена отзывает семью, ротация атомарна, отзыв переживает ответ 401 — доказано на PostgreSQL под `retail_media_app` |
| Задачи roadmap.yaml | RM-STAB-018 (OD-046) |
| Находки | P0-7; маскирующий тест `tests/test_phase3_auth_service.py::TestRefreshTokenFamilyRevoke::test_replay_calls_family_revoke` |
| Скоуп (в) | `packages/auth/repository.py` (поиск по хэшу с блокировкой, условная ротация, отзыв семьи без `last_error`); `packages/auth/service.py` (`refresh_session`: повтор, окно 10 с, audit); `packages/api/auth.py` (`/refresh`: отзыв коммитится до 401); `packages/security/config.py` (окно повтора); замена маскирующего теста (одобрено владельцем); новый behavioral-тест; RM-STAB-018/OD-046 в `roadmap.yaml`, ссылка в `requirements-traceability.yaml` (REQ-SEC-001), генерация представлений |
| Скоуп (вне) | P0-6, P0-8, P1-11.a, T1–T3, T7 (остаток черновика RF-01); фронтенд single-flight P1-13.b (RF-08); миграции; logout; RM-STAB-004 |
| Protected Boundaries | нет (auth портала не в списке `AGENTS.md`) |
| mini-design | нет — поведение согласовано владельцем (OD-046: окно 10 с, строгий отзыв после окна) |
| Входные условия | PR #9 (RF-00) смержен — `develop @ 7762434` |
| Гейт | behavioral под `retail_media_app` NOBYPASSRLS: новый тест RM-STAB-018 + `tests/behavioral/test_auth_dual_e2e.py`; job python-tests (`python -m pytest tests/`); I-0; `roadmap-governance-guard` + `--self-test`; ruff по изменённым файлам |
| Канон, который меняется | `roadmap.yaml` (RM-STAB-018, OD-046) + генерация; `requirements-traceability.yaml` (roadmap_ids REQ-SEC-001); checkpoint `PROJECT_STATE.md` |

## RF-05 — Pilot-контур поднимается, verify честный (решение владельца 2026-09-29)

| Поле | Значение |
|---|---|
| Статус | merged |
| Цель | Pilot-compose с `ENVIRONMENT=pilot` поднимается с нуля без ручных шагов (роль приложения, CORS, audience, конфиг воркера), а `verify-pilot-run.sh` падает, если это не так |
| Задачи roadmap.yaml | новая в области RM-PILOT-002 (одобрено владельцем 2026-09-29) |
| Находки | P0-1, P0-2, P0-3, P0-4 (конфиг; ack при ошибке — RF-04), P0-5, P1-16, P2-I9, P2-I11, T12 |
| Скоуп (в) | Защищённая зона (список утверждён владельцем 2026-09-29): `infra/compose/docker-compose.pilot.yml`, `infra/compose/create-app-role.py`, `scripts/ci/verify-pilot-run.sh`, `infra/compose/docker-compose.local-stand.yml`, `infra/compose/docker-compose.phase1.yml`, `.github/workflows/phase1-ci.yml` (import smoke под pilot + новый job «pilot compose smoke»), `infra/compose/Dockerfile.service` (версия в образе), `infra/deploy/.env.pilot.example` (только заглушки). Код: `packages/security/config.py` (`JWT_AUDIENCE` в prod), `apps/control-api/main.py` (readiness), `apps/control-api/alembic/env.py`. Тесты: замена `test_pilot_compose_still_omits_*` / `test_overlay_supplies_*` и FU5 `test_pilot_healthchecks_still_use_localhost` / `test_overlay_healthcheck_avoids_localhost_ambiguity` (одобрено владельцем), новые тесты; фикстуры `JWT_AUDIENCE` в `test_phase2_health.py`, `test_phase3_security.py`, `test_production_config_gate.py` и `requirements-traceability.yaml` (REQ-ARCH-004 → RM-PILOT-002A) — подтверждено владельцем 2026-09-29 |
| Скоуп (вне) | прод-конфигурация и CI/CD-пайплайны деплоя в прод; ack/DLQ воркера (RF-04); supply chain и GHCR (RF-06); non-root MinIO |
| Protected Boundaries | «Docker, deployment scripts» — одобрено владельцем 2026-09-29 с условиями: без секретов в Dockerfile/compose/скриптах (только env или secret-механизм, в репозитории — `.env.example` с заглушками); без root в контейнерах без обоснования в PR; только pilot-контур; список файлов — владельцу до правок |
| mini-design | нет |
| Входные условия | RF-01 смержен (PR #11, `develop @ d8dbd62`) |
| Гейт | локальный прогон скрипта pilot compose smoke (`ENVIRONMENT=pilot`, образы собраны из ветки) → db-migrate 0, все сервисы healthy, роль NOBYPASSRLS, версия из образа, device-токен принят, конфиг воркера; I-0; I-1 и job behavioral под `retail_media_app`; job python-tests; `roadmap-governance-guard` + `--self-test`; ruff по изменённым файлам; `docker compose config` pilot/phase1/local-stand |
| Канон, который меняется | `roadmap.yaml` (новая задача RM-PILOT-*) + генерация; checkpoint `PROJECT_STATE.md` |

## RF-04 — Оркестратор: сбои не маскируются (решение владельца 2026-09-29)

| Поле | Значение |
|---|---|
| Статус | merged |
| Цель | Системный сбой генерации манифеста не ack'ается; consumer переживает сбой отдельного сообщения, а его остановку видит readiness; воркер завершения кампаний работает под RLS — доказано на PostgreSQL под `retail_media_app` |
| Задачи roadmap.yaml | RM-STAB-019 (новая, стадия S); попутно RM-PILOT-002A → `done` (решение владельца 2026-09-29) |
| Находки | P0-4 (ack при ошибке), P1-6.a, P1-8, T11 |
| Скоуп (в) | P0-4: системные ошибки (конфиг безопасности, БД/сессия) → rollback + nak, failed не пишется, счётчик health; ошибка данных устройства — как сейчас (failed + `delivery.manifest.failed` + ack) — `packages/domain/delivery.py`, `packages/services/campaign_event_handler.py`. P1-6.a: сбой `session_setup`/rollback → nak + счётчик ошибок, цикл продолжается; consumer подключён, но цикл не работает → `/health/ready` 503 — `campaign_event_handler.py`, `packages/services/health_state.py`, `apps/orchestrator-worker/main.py`. P1-8: `set_worker_admin_context` в сессии воркера завершения, один проход — функция. Тесты: unit consumer/handler (T11); новый behavioral под `retail_media_app` (NOBYPASSRLS), падающий до исправления. `roadmap.yaml` + генерация |
| Скоуп (вне) | DLQ/`max_deliver` (P1-6.b), stream subjects (P1-7), `SKIP LOCKED` (P2-B7) — отдельный этап с RM-TECH-243; формат манифеста; lifecycle-переходы; compose/Docker/CI; существующий `tests/behavioral/test_campaign_completion.py` не меняется; `requirements-traceability.yaml` — только решением владельца |
| Protected Boundaries | нет (решение владельца 2026-09-29) |
| mini-design | нет |
| Входные условия | RF-05 смержен (PR #12, `develop @ af6810c`) |
| Гейт | job behavioral под `retail_media_app` (новый тест + I-1); job python-tests; I-0; I-2 (`tests/test_rf05_pilot_boot.py`; pilot compose smoke локально); `roadmap-governance-guard` + `--self-test`; ruff по изменённым файлам |
| Канон, который меняется | `roadmap.yaml` (RM-STAB-019; RM-PILOT-002A → `done`) + генерация; checkpoint `PROJECT_STATE.md` |

## RF-10 — События не пропадают молча: DLQ consumer и полный stream (решение владельца 2026-09-30)

| Поле | Значение |
|---|---|
| Статус | merged |
| Цель | Сообщение consumer, исчерпавшее лимит доставок, сохраняется в PostgreSQL и может быть повторено; каждое событие outbox попадает в stream, а не в `dead_letter` relay |
| Задачи roadmap.yaml | RM-STAB-020 (новая, стадия S); попутно RM-STAB-019 → `done` (решение владельца 2026-10-01) |
| Находки | P1-6.b, P1-7 |
| Скоуп (в) | Лимит 7 доставок в приложении (`msg.metadata.num_delivered`), backoff nak 5с/30с/2м/10м/30м/60м (env, дефолты в коде), серверный `max_deliver` остаётся −1; на 7-й неудаче — строка DLQ (отдельная транзакция, worker admin context) + `term()`, сбой записи → nak 60 мин; счётчик `consumer_dead_lettered` + лог `event_id`; CLI `list / replay <id> / replay --all` (replay — новое outbox-событие + `replayed` в одной транзакции); stream RMP — только `campaign.>` (durable без серверного фильтра, не пересоздаётся), stream RMP_EVENTS — `delivery.>`, `pop.>`, `emergency.>`, `creative_asset.>` (1 GiB, 7 суток, DiscardOld; решение владельца 2026-10-01 после ревью); без auto-provision воркер сверяет subjects обоих; риск `max_ack_pending=100` при backoff принят владельцем 2026-10-01; миграция 038; `roadmap.yaml` + генерация |
| Скоуп (вне) | API/UI DLQ; DLQ stub-consumer; P2-B7; остаток RM-TECH-243; новые потребители не-campaign событий; compose, Dockerfile, CI. Адаптация 3 тестов воркера в `tests/test_phase4_production_readiness.py` под новый provisioning — одобрена владельцем 2026-10-01 |
| Protected Boundaries | Только миграция 038 (create table, FORCE RLS, политика «только `app.rmp_is_admin`»); downgrade удаляет лишь новую таблицу и её политики; без DROP/TRUNCATE/DELETE существующих таблиц (решение владельца 2026-09-30) |
| mini-design | да — одобрен владельцем 2026-09-30 (журнал RF-10) |
| Входные условия | RF-04 смержен (PR #13, `develop @ b219fad`) |
| Гейт | job behavioral (новые тесты + I-1 + I-3); job python-tests; I-0; I-2 (pilot smoke) + subjects stream; `roadmap-governance-guard` + `--self-test`; ruff по изменённым файлам; миграция upgrade → downgrade → upgrade на PostgreSQL |
| Канон, который меняется | `roadmap.yaml` (RM-STAB-020; RM-STAB-019 → `done`) + генерация; checkpoint `PROJECT_STATE.md` |

## RF-11 — Надёжность NATS: хранилище на томе и fail-fast provisioning (решение владельца 2026-10-01)

| Поле | Значение |
|---|---|
| Статус | merged |
| Цель | JetStream хранит streams и сообщения в смонтированном томе и переживает пересоздание контейнера NATS; воркер не запускает relay без проверенных streams |
| Задачи roadmap.yaml | RM-STAB-021 (новая, стадия S); попутно RM-STAB-020 → `done` (решение владельца 2026-10-01) |
| Находки | ревью RF-10 круг 3: 🟠 provisioning при сбое; наблюдение `-sd /data` (подтверждено на стенде) |
| Скоуп (в) | `-sd /data` в command NATS — `infra/compose/docker-compose.pilot.yml`, `infra/compose/docker-compose.phase1.yml`; описание — `scripts/backup/backup_manifest.py`, `docs/runbook/nats-backup-restore.md`; воркер: provisioning при любом `NATS_URL`, сбой provisioning/сверки subjects завершает старт до relay (`main()` не глотает), кроме `OUTBOX_RELAY_ALLOW_STUB=true` — лог; runbook `delivery-runtime.md`; `roadmap.yaml` + генерация |
| Скоуп (вне) | образ/пользователь/порты NATS; CI и `verify-pilot-run.sh`; restore-drill compose; переподключение relay к NATS во время работы; остальной долг RF-10 |
| Protected Boundaries | «Docker, deployment» — только 2 compose-файла (флаг хранилища) + описание в `backup_manifest.py` и runbook (решение владельца 2026-10-01) |
| mini-design | нет — решения владельца 2026-10-01 (fail-fast, список файлов) |
| Входные условия | RF-10 смержен (PR #14, `develop @ 2151153`) |
| Гейт | локально pilot-стек: publish в RMP → `up --force-recreate nats` → stream и сообщение на месте (на compose develop — пропадают); unit `tests/test_rm_stab_021_nats_durability.py`; behavioral (I-1, I-3, I-4); python-tests; I-0; I-2; `docker compose config` pilot/phase1; `roadmap-governance-guard` + `--self-test`; ruff |
| Канон, который меняется | `roadmap.yaml` (RM-STAB-021; RM-STAB-020 → `done`) + генерация; checkpoint `PROJECT_STATE.md` |

## RF-GOV-0 — Новые правила работы (документальный; решение владельца 2026-10-05)

| Поле | Значение |
|---|---|
| Статус | merged |
| Цель | Новый `CLAUDE.md` владельца (единая точка входа: источники по вопросам, цикл этапа, матрица субагентов, память между сессиями, ведение roadmap) и аудит управления 2026-10-05 приняты в git; guard документов зелёный |
| Задачи roadmap.yaml | — (работа над процессом и документами; без задачи roadmap — решение владельца 2026-10-05) |
| Находки | `docs/audit/2026-10-05-claude-governance-review.md`: G-5, G-6 (в части `CLAUDE.md`); G-2 — частично: таблица «вопрос → источник» добавлена, линейный блок Truth Priority сохранён до этапа с guard и `AGENTS.md` |
| Скоуп (в) | `CLAUDE.md` и `docs/audit/2026-10-05-claude-governance-review.md` — правки владельца, вход этапа, агент их содержание не меняет; карточка в `stages.md`; `journal.md`; короткий checkpoint в `PROJECT_STATE.md`; строка в `docs/audit/README.md` |
| Скоуп (вне) | Код, тесты, CI, compose; `scripts/ci/roadmap-governance-guard.py` и его self-test; `AGENTS.md`; `roadmap.yaml` и реестр (RM-STAB-021 → `done` — в следующем этапе с кодом); `CLAUDE.local.md`, `.claude/` (вне git); каталог `o/`; шапки `journal.md`/`stages.md`, правила `docs/audit/README.md` — следующий документальный этап вместе с `AGENTS.md` и guard |
| Protected Boundaries | нет |
| mini-design | нет |
| Входные условия | RF-11 смержен (PR #15, `develop @ e2e3f63`); карточка подтверждена владельцем 2026-10-05 |
| Гейт | `roadmap-governance-guard` PASS + `--self-test` 55/55 (под `.venv`); I-0; `git diff --name-only origin/develop` + неотслеживаемые = только файлы скоупа (`o/` не входит); `code-reviewer` и, на `/finish`, `canon-auditor` — APPROVE*; CI `Phase 1 — Quality Gates` на PR |
| Канон, который меняется | `CLAUDE.md`; checkpoint `PROJECT_STATE.md` |

## RF-12 — Управление ролями не даёт эскалации (решение владельца 2026-10-05)

| Поле | Значение |
|---|---|
| Статус | finished |
| Цель | Scoped-роль не даёт глобальных прав на маршрутах `require_permission`; нельзя назначить роль себе или выше своей; нельзя снять роль с последнего администратора; нельзя сбросить пароль, реактивировать или деактивировать учётку с правами выше своих — доказано на PostgreSQL под `retail_media_app` |
| Задачи roadmap.yaml | RM-STAB-022 (новая, стадия S; решение владельца 2026-10-05); попутно RM-STAB-021 → `done` (решение владельца 2026-10-05, вариант «а») |
| Находки | P0-6, P1-11.a, T2 |
| Скоуп (в) | `packages/api/dependencies.py` (`require_permission`), `packages/domain/repository.py` (`get_user_permissions`), `packages/api/identity_routes/users.py` (`assign_role`, `remove_role`, `deactivate_user`; расширение по решениям владельца 2026-10-05 после «СТОП-А» и ревью круга 2: `reset_password`, `activate_user`, `deactivate_user` — запрет действовать над учёткой, чьи глобальные права не входят в права актора, break-glass — только `system_admin`); новый behavioral-тест `tests/behavioral/test_rm_stab_022_role_escalation.py` и статический `tests/test_rm_stab_022_advertiser_portal_routes.py`; замена тестов, закрепляющих дефект (принципиальное согласие владельца 2026-10-05; окончательное «да» — после списка в мини-дизайне: каждый заменённый тест строже прежнего, ни один не удаляется без замены); `roadmap.yaml` и генерация; RF-GOV-0 → `merged` |
| Скоуп (вне) | P0-8 и T3 (права по конкретной организации — отдельный этап после RF-12), `PUT /auth/ad-settings` (отдельный этап с мини-дизайном — решение владельца 2026-10-05), T7, P1-11.b (фронтенд), RM-STAB-004, RM-STAB-015, миграции, порталы, CI |
| Protected Boundaries | нет |
| mini-design | да — меняется контракт прав; одобрен владельцем 2026-10-05 с дополнениями А–Д и расширениями (журнал RF-12) |
| Входные условия | PR #16 (RF-GOV-0) смержен — `develop @ 5cf482b`; push-run develop 37309852950 → success 42/42 |
| Гейт | job behavioral под `retail_media_app` (новый тест `tests/behavioral/test_rm_stab_022_role_escalation.py`, I-1, I-3, I-4); job python-tests; I-0; I-2 и I-5 — по CI или записи журнала; `roadmap-governance-guard` + `--self-test`; ruff по изменённым файлам |
| Канон, который меняется | `roadmap.yaml` (RM-STAB-022; RM-STAB-021 → `done`; RM-STAB-023 — новая `planned`, решение владельца 2026-10-05) + генерация; checkpoint `PROJECT_STATE.md` |

## Остальное

Определяются по итогам RF-00 и решению владельца.

### Черновики (RF-00) — статус `draft`, не `planned`

> Основание: `docs/audit/2026-09-27-claude-rf-00-recheck-develop-b166419.md`. Черновики — предложение.
> Номер, порядок, состав и Protected Boundaries утверждает владелец; новые задачи сначала вносятся в
> `roadmap.yaml` решением владельца (OD), затем карточка получает `planned`.
> Порядок ниже — по риску (безопасность → деньги → доставка → надёжность → pilot → UI → P2); сопоставление
> со стадиями `roadmap.yaml` (G→E0→S→C→CORE→U→CH→A→POPS) — в колонке «Стадия», решение за владельцем:
> большинство пунктов относятся к CORE/POPS, тогда как текущая стадия — S.

| Черновик | Название | Находки | Задачи roadmap.yaml | Стадия | Protected Boundaries | mini-design |
|---|---|---|---|---|---|---|
| RF-01-остаток (номер — владелец) | Авторизация: scoped-права, эскалация (P0-7 выделена в RF-01, решение владельца 2026-09-28) | P0-6, P0-8, P1-11.a, T1, T2, T3, T7 | новая; пересекается по коду с RM-STAB-004 (S, in_progress) — риск конфликта правок `dependencies.py`/`scopes.py`, решает владелец; смежно RM-STAB-015 | CORE (безопасность) | нет (auth портала не в списке) | да — модель `scoped_permissions[(type,id)]` по ADR-009 |
| RF-02 | Деньги: договор кампании и бронь инвентаря | P0-9, P0-11.a–c, P1-9, P2-D1, T4, T8 | RM-TECH-203, RM-TECH-241 (частично) + новая | CORE | campaign submit/approval (бронь в `request_campaign_approval`) | да |
| RF-03 | Доставка: мультикампанийный манифест, отзыв, resume, daypart/SoV, PoP-окна | P0-12.a–d, P1-2, P2-B8, T9 | RM-TECH-242, RM-TECH-245, RM-TECH-248 + новая | CORE / CH | generated manifest compatibility; campaign publication; KSO runtime (плеер) | да (ADR-016) |
| RF-04 → карточка выше (узкий состав; P1-6.b, P1-7, P2-B7 — отдельный этап) | Надёжность событий: consumer, stream subjects, воркер завершения | P1-6.a–b, P1-7, P1-8, P0-4 (ack при ошибке), P2-B7, T11 | RM-TECH-243 (частично) + новая | CORE (outbox) | требует проверки: P0-4/P1-8 затрагивают генерацию манифестов и lifecycle кампании (близко к publication flows / manifest compatibility) | нет |
| RF-05 → карточка выше | Pilot-контур поднимается, verify честный | P0-1, P0-2, P0-3, P0-4 (конфиг), P0-5, P1-16, P2-I9, P2-I11, T12 | новая (область RM-PILOT-002) | POPS / E0 | Docker, deployment scripts | нет |
| RF-06 | Supply chain CI и образы | P0-10.a–c, P1-18, P2-I1–I7, P2-I10 | RM-STAB-009 (частично) + новая | S / POPS | Docker, deployment scripts; внешнее действие владельца — GHCR visibility | нет |
| RF-07 | Tenancy и миграции | P1-3, P1-4, P1-17, P2-I8 | RM-TECH-229, RM-STAB-004 (частично) | C / CORE | destructive migrations (downgrade) | да (ERD/migration plan) |
| RF-08 | Портал: сессия, даты, циклы запросов | P1-11.b, P1-12, P1-13.a–c (фронт), P1-14, P1-15, P2-F1–F6, T13, T14 | RM-UX-002 (частично) + новая | U (Gate-U приостановлен OD-041) | нет (не редизайн); P1-13.c требует правки бэкенда `packages/api/auth.py` (refresh-cookie) | нет |
| RF-09 | P2-хвост backend/домен/плеер | P2-B1–B6, P2-B9–B12, P2-D2–D5, P2-P1–P3, P1-1, P1-10, T10 | RM-STAB-012/013/016, RM-TECH-207A/B, 227, 252, 254 + новая | S / CORE / CH | device auth, KSO runtime (P2-P*) | по пунктам |

Замена тестов, закрепляющих дефекты (перечень — в файле сверки, раздел «Для решения владельца»),
входит в соответствующий черновик и требует явного одобрения владельца в карточке.
