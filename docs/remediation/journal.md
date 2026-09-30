# Журнал этапов исправлений (RF)

> **Не канон.** Операционная память агента между сессиями: что сделано, на чём
> остановились, что нельзя сломать. Канонический статус — `PROJECT_STATE.md`.
> Команды `/start` и `/finish` читают и дополняют этот файл. Записи этапов не
> переписываются задним числом — только дополняются.

## Текущее состояние

| | |
|---|---|
| Активный этап | — |
| Последний завершённый | RF-04 — finished, PR ждёт merge (`gh pr list --head fix/RF-04`); RF-05 — merged (PR #12 → `develop @ af6810c`, push-run develop 36571330932 → success 42/42); RF-01 — merged (PR #11); RF-00 — merged (PR #9) |
| Следующий шаг | merge PR RF-04 владельцем → RM-STAB-019 `done` после CI develop (решение владельца); P1-6.b как условие выката на pilot-хост → `/start RF-<N>` |
| Базовая линия | `origin/develop @ af6810c` (2026-09-29, merge RF-05; push-run 36571330932 → success 42/42). Прежняя: `origin/develop @ d8dbd62` (2026-09-29, merge RF-01; push-run 36475858226 → success 41/41). Прежняя: `origin/develop @ 6bc9ac0` (2026-09-28, merge RF-CI; push-run `develop` 36407616564 → success; то же дерево — push-run `fix/RF-CI` 36404147483, 41/41). Снимок аудита RF-00 — `b166419`; ветка `fix/RF-00` получила `6bc9ac0` merge-коммитом `3892552` |
| Источник находок | `docs/audit/2026-09-27-claude-code-review-main-8ad0228.md` (снято на `main @ 8ad0228`; develop на 64 коммита впереди) |

## Инварианты (не ломать)

Поведения, доказанные завершёнными этапами. Каждый `/start` и `/finish` прогоняет
все команды отсюда. Добавляются только в `/finish`, с командой проверки.

| # | Инвариант | Команда проверки | Добавлен этапом |
|---|---|---|---|
| I-0 | Границы импорта (ADR-014) | `python scripts/ci/check-import-boundaries.py` | исходное правило проекта |
| I-1 | Refresh-токены: повтор после окна отзывает семью (+audit), в окне — нет; одна ветка при гонке; семья сериализована; отзыв переживает 401 (RM-STAB-018) | шаги job `behavioral-postgres-tests` (PostgreSQL, `retail_media_app` NOBYPASSRLS), затем `python3 -m pytest tests/behavioral/test_rm_stab_018_refresh_replay.py -v` → 7 passed | RF-01 |
| I-2 | Pilot-compose под `ENVIRONMENT=pilot` поднимается без ручных шагов: роль приложения из `db-migrate`, все сервисы healthy, readiness строгий, identity образа, device-токен control-api принят device-gateway (RM-PILOT-002A) | CI job `pilot-compose-smoke` (`build-images.sh` без push → `verify-pilot-run.sh --images-from-env <version> <sha>`); локально — сборка образов с теми же build-args и тот же вызов; `python -m pytest tests/test_rf05_pilot_boot.py` | RF-05 |
| I-3 | Оркестратор не маскирует сбои: системный сбой генерации → nak без failed, ошибка данных устройства → failed + ack; сбой сессии не останавливает consumer, остановка цикла → `/health/ready` 503; воркер завершения работает под RLS (RM-STAB-019) | шаги job `behavioral-postgres-tests` (`retail_media_app` NOBYPASSRLS), затем `python3 -m pytest tests/behavioral/test_rm_stab_019_orchestrator_rls.py -v` → 7 passed; `python -m pytest tests/test_rm_stab_019_orchestrator_failures.py` → 11 passed | RF-04 |

## Решения владельца, влияющие на этапы

| Дата | Решение |
|---|---|
| 2026-09-27 | Этапы запускаются `/start`, закрываются `/finish`; ревью `code-reviewer` автоматически, до 3 кругов |
| 2026-09-27 | Git: ветка `fix/<id>` от `develop` → PR в `develop`; merge делает только владелец |
| 2026-09-27 | `/start` одобряет только Protected Boundaries, перечисленные в карточке этапа |
| 2026-09-27 | Первый этап — пересверка находок на develop (RF-00); дальнейшие этапы — пакеты задач `roadmap.yaml` |
| 2026-09-28 | Запись RF-CI (карточка, журнал, checkpoint) — в PR #9: предложено агентом в отчёте RF-CI, владелец продолжил `/finish`; синхронизация `fix/RF-00` с develop — merge-коммитом (решение владельца) |
| 2026-09-28 | RF-01 = P0-7 + замена маскирующего теста `test_replay_calls_family_revoke` (одобрено); T7 и P0-6/P0-8 — в остаток черновика RF-01; задача RM-STAB-018 и OD-046 заводятся этапом; повтор ротированного refresh в окне 10 с — 401 без отзыва семьи, позже — отзыв семьи (вариант «a») |
| 2026-09-29 | Следующий этап — RF-05, карточка `planned`, номер и состав как в черновике. Protected Boundary «Docker, deployment scripts» — с условиями: без секретов в Dockerfile/compose/скриптах (env или secret-механизм; в репозитории — `.env.example` с заглушками); без root в контейнерах без обоснования в PR; не трогать прод-конфигурацию и CI/CD деплоя в прод — только pilot-контур; список файлов — владельцу до правок. Новая задача в области RM-PILOT-002 — одобрена. RM-STAB-018 → `done`, если run 36475858226 зелёный. RF-01-остаток не начинать; справка по RM-STAB-004. Ревью в конце этапа — «/reviewer» |
| 2026-09-29 | RF-05 после СТОП на круге 3: п.1 (schema head в lock-режиме verify) — вариант «а» (lock `release.schema_head`, иначе head из миграций на коммите релиза); п.3 — подтверждены ссылка `RM-PILOT-002A` в `requirements-traceability.yaml` (REQ-ARCH-004) и адаптация фикстур `JWT_AUDIENCE` в 3 тестовых файлах; п.4 — принято: `verify-pilot-images.yml` не проходит для релизов, собранных до RF-05 (в образах нет ENV identity). П.2 (`JWT_AUDIENCE` в `validate-pilot-env.py`/`local_stand.py`) — ответа нет, остаётся открытым риском |
| 2026-09-29 | RF-05 смержен; RM-PILOT-002A → `done`. Следующий этап — RF-04, узкий состав: P0-4 (ack при ошибке; системные ошибки → nak, ошибки данных устройства — failed + ack), P1-6.a (цикл переживает сбой сообщения, остановка → `/health/ready` 503), P1-8 (новый behavioral под `retail_media_app`, существующий тест не менять), T11; P1-6.b/P1-7/P2-B7 — отдельный этап с RM-TECH-243. Protected Boundaries — нет. Задача RM-STAB-019, стадия S |
| 2026-09-28 | Красный CI PR #9 из-за внешнего дрейфа — отдельный этап RF-CI (вариант 1); SQLAlchemy `<2.1` в CI и requirements; MinIO → Chainguard по digest; скоуп CI + drill + phase1 + pilot, Protected Boundary «Docker/deployment» — по ответу владельца «CI + drill + phase1 + pilot»: образ/healthcheck MinIO в `phase1-ci.yml`, compose restore-drill/phase1/pilot и версия MinIO в `backup-restore-drill.sh`; pilot `user: "0"` + долг. `user: "0"` в phase1 добавлен агентом на круге ревью 2 по аналогии — **ожидает подтверждения владельца** |

---

## Шаблон записи этапа

```markdown
## RF-NN — <название>

- Статус: in_progress | ready_to_finish | finished (PR ждёт merge) | merged
- Ветка: fix/RF-NN · Основа: develop @ <sha>
- Baseline: <команда → результат> …
- План: <задача, домены, Protected Boundaries из карточки, чем докажем>

### Сделано
- <файл/поведение → тест>

### Решения
- <что решили и почему>

### Ревью
| Круг | Замечание | Уровень | Решение | Риск исправления | Доказательство |
|---|---|---|---|---|---|

### Гейт
- <команда → результат>

### Итог (заполняет /finish)
- Коммит: <sha> · PR: `gh pr list --head fix/RF-NN` · CI: <run id → итог>
- Долг: …
- Новые инварианты: …
- Следующий шаг: …
```

---

<!-- записи этапов ниже -->

## RF-00 — Пересверка находок ревью на актуальном develop

- Статус: finished (PR ждёт merge владельцем)
- Ветка: fix/RF-00 · Основа: develop @ b166419 (= `origin/develop`, `git ls-remote` 2026-09-27)
- CI на основе: `Phase 1 — Quality Gates` run 33735361730, attempt 1 → success (GitHub API, без авторизации; `gh` не залогинен — нужен к `/finish`)
- Baseline (2026-09-27, venv `.venv`, Python 3.12.3, `set -o pipefail`; guard и self-test — только интерпретатором `.venv` (`openpyxl`, `pyyaml`, `jsonschema`), системный `python3` даёт ложный `MODULE-ERROR`):
  - I-0 `python scripts/ci/check-import-boundaries.py` → rc 0, «All import boundaries clean.»
  - `python3 scripts/ci/roadmap-governance-guard.py` → rc 0, «PASS — все модули чисты»
  - `python3 scripts/ci/roadmap-governance-guard.py --self-test` → 1-й прогон rc 1 «54/55 passed»
    (упавший кейс не сохранён — вывод был обрезан `tail`); следующие 6 прогонов подряд → rc 0 «55/55 passed».
    Не воспроизводится; причина не установлена. Наблюдение для владельца, не дефект этапа.
  - JSON Schema job — не затрагивается этапом (изменений в `packages/contracts/` нет), не прогонялся.
- План:
  - Задача: для каждой находки `docs/audit/2026-09-27-claude-code-review-main-8ad0228.md`
    (P0-1…P0-13, P1-1…P1-18, P2 по пунктам, пробелы тестов) установить статус на `develop @ b166419`
    чтением кода: `исправлено` (коммит + file:line) / `актуально` (file:line) / `частично` / `неприменимо`;
    сопоставить с задачей `roadmap.yaml` или «новая»; отметить пересечения с `docs/audit/2026-08-26-*`.
  - Домены: только чтение (все области); запись — только документы: новый аудит-файл сверки,
    строка в `docs/audit/README.md`, черновики карточек RF-01… в `stages.md` (статус `draft`), журнал.
  - Protected Boundaries: нет (карточка). Код, тесты, CI, compose, миграции, `roadmap.yaml`, registry — не трогаются.
  - Доказательство: file:line на SHA `b166419` в таблице; ревьюер выборочно перепроверяет ≥ 10 статусов;
    guard + self-test + I-0 зелёные после изменений.
  - Метод: разбор по областям параллельными read-only агентами, затем собственная выборочная перепроверка.

### Сделано
- 5 read-only агентов по областям (infra/CI, auth, домен, устройства/NATS, фронтенд) → таблицы статусов;
  собственная перепроверка 13 статусов (P0-2, P0-5, P0-6, P0-7, P0-12.d, P0-13, P1-5, P1-7, P1-8, P1-17,
  P2-D1, P2-I11, T7) — совпали; уточнена строка P1-5 (`onboard.py:172`, не `:160`).
- `docs/audit/2026-09-27-claude-rf-00-recheck-develop-b166419.md` — 94 строки: 4 исправлено (P0-13, P1-5, T5, T6),
  4 частично (P0-10.b, P0-10.c, P1-15, P2-F3), 86 актуально [до ревью; после круга 1 — 3 частично / 87 актуально], 0 без статуса; счёт — скриптом по таблицам.
- `docs/audit/README.md` — 2 строки (исходное ревью и сверка).
- `stages.md` — «Черновики (RF-00)»: RF-01…RF-09 со статусом `draft`, покрыты все актуальные/частичные ID.
- Самопроверка: I-0 rc 0; guard rc 0 PASS; self-test 55/55 rc 0.

### Решения
- Порядок черновиков — по риску, не по стадиям roadmap; расхождение со стадиями (текущая S, пункты CORE/POPS)
  вынесено владельцу, не разрешено агентом.
- Расхождения канона с кодом (PROJECT_STATE LIFECYCLE-COMPLETE «real DB proof», pilot «Verify green»,
  canon §2.4) — только сообщены в файле сверки; канон не правился (CLAUDE.md: противоречие = стоп для правки).
- Незатреканные `docs/audit/2026-09-27-claude-code-review-main-8ad0228.md` и `docs/remediation/` — входы
  этапа (CLAUDE.local.md: «коммитится в RF-00»), не чужая работа; перенесены на ветку как есть.

### Ревью
| Круг | Замечание | Уровень | Решение | Риск исправления | Доказательство |
|---|---|---|---|---|---|
| 1 | P0-10.c «частично» с коммитом `9b88ae8` — риск не уменьшился, preview правил `00d75a6` | 🟠 | исправлено: «актуально», `00d75a6`; сводка 4/3/87, шапка, README | нет (документ) | `git log 8ad0228..b166419 -- infra/compose/docker-compose.preview.yml` → только `00d75a6`; `git show --stat 9b88ae8` — только `docs/runbook/local-preview.md` |
| 1 | `test_reserve_idempotent` ошибочно в «закрепляющих дефект» | 🟠 | исправлено: колонка «Тест» уточнена, тест убран из списка на замену | нет | `tests/test_s079_inventory_reservations.py:256-278` — идентичный повтор, корректная идемпотентность |
| 1 | P0-10.a: `:64` — `with: ref:`, пропущены `:183,189,193` | 🟡 | исправлено сразу (документ, нулевой риск) | нет | `grep -n 'inputs\.' publish-pilot-images.yml` |
| 1 | Смещённые строки: `phase1-ci.yml:757`, `delivery.py:681-682` | 🟡 | исправлено | нет | `grep -n skip-registry`; `sed -n 674,684p delivery.py` |
| 1 | Шапка «Открытых находок: 94» противоречива | 🟡 | исправлено: «Строк сверки… (открытых 90)» | нет | файл сверки, шапка |
| 1 | Журнал устарел (следующий шаг, CI, `proposed`) | 🟡 | исправлено | нет | journal.md, «Текущее состояние» |
| 1 | RF-04/RF-08: Protected Boundaries «нет» слишком уверенно | 🟡 | исправлено: «требует проверки» с причиной; решение — владельцу | нет | stages.md, черновики |
| 1 | P1-15 «частично» мягче критерия | 🟡 | исправлено: примечание «смягчено подписью, дефект не исправлен»; статус оставлен (подпись — реальное изменение по находке) | нет | admin `CampaignListPage.tsx`, `27dc397` |
| 2 | Строки ревью круга 1 попали в шаблон журнала, таблица RF-00 пуста | 🟠 | исправлено: строки перенесены в RF-00, шаблон восстановлен | нет | journal.md: шаблон без строк, RF-00 → «Ревью» |
| 2 | P0-6/P0-8 — «новая», без пересечения с RM-STAB-004 (S, in_progress, те же `dependencies.py`/`scopes.py`) | 🟡 | исправлено: пересечение отмечено в сверке и RF-01; риск конфликта — владельцу | нет | roadmap-index: `RM-STAB-004 S in_progress` |
| 2 | P1-8 без ссылки на BEHAVIORAL-ADMIN-MASK-001; P1-3 §2.1 связан слабо | 🟡 | исправлено | нет | code-and-security §3.2, §2.1 |
| 2 | P0-10.b: «всюду skip_registry» сильнее факта; второй fail-open при `returncode != 0` | 🟡 | исправлено | нет | `grep -c skip_registry` → 1; `pilot_host_preflight.py:534-537` |
| 2 | P1-18: `generate_release_lock.py:83` → `:82` | 🟡 | исправлено | нет | `sed -n 82p` |
| 3 | P0-12.c daypart: `:681-682` неверно — поправка круга 1 была ошибочной | 🟡 | исправлено: возвращено `:683-684`; урок — принимать номера строк ревьюера только после собственного `grep -n` | нет | `grep -n '"start_time"\|"days_of_week"' delivery.py` → 683, 684 |
| 3 | P1-16: часть про CLI `nats` без пометки «вероятно» | 🟡 | исправлено: пометка «требует проверки образа» | нет | образ не проверялся (без Docker-запусков в RF-00) |
| 3 | Не указан интерпретатор guard — системный `python3` даёт ложный красный | 🟡 | исправлено: в baseline записан `.venv` | нет | ревьюер: системный `python3` → `MODULE-ERROR: openpyxl` |
| 3 | P0-3: доказательство без dev-fallback audience и источника токена | 🟡 | исправлено: добавлены `config.py:257-258`, `onboard.py:151`, compose `:120` | нет | `sed -n 255,258p config.py` |
| Δ1 | Push записи не даст зелёный CI: workflow только на `push` по дереву ветки, в `fix/RF-00` нет правок RF-CI | 🔴 | исправлено: merge `origin/develop` → `3892552` (решение владельца), текст плана переписан | низкий: merge без конфликтов, история не переписана | `on: push` в `phase1-ci.yml`; runs `event: push` |
| Δ1 | Базовая линия `6bc9ac0` противоречила основе ветки `b166419` | 🟠 | исправлено: разделены базовая линия, снимок аудита, merge-коммит | нет | journal «Текущее состояние» |
| Δ1 | «9 fail» — фактически 6 failure + 3 cancelled | 🟠 | исправлено во всех местах | нет | `gh run view 36392472274` |
| Δ1 | «CI PR» — на деле push-run ветки | 🟠 | исправлено | нет | `event: push` |
| Δ1 | Запись RF-CI в PR #9 без записанного одобрения; формулировка Protected Boundary | 🟡 | исправлено: строки в «Решения владельца» | нет | — |
| Δ1 | Шапка `Last updated` в PROJECT_STATE устарела (2026-08-31) | 🟡 | долг: шапка ведётся отдельными записями, не менялась этапом | — | — |
| Δ2 | Одобрение Protected Boundary записано уже фактического диффа; `user: "0"` в phase1 — после решения | 🟠 | исправлено: запись по ответу владельца, phase1 `user` — «ожидает подтверждения» | нет | ответ владельца «CI + drill + phase1 + pilot» |
| Δ2 | Необратимый апгрейд pilot MinIO защищён только текстом | 🟠 | вынесено владельцу (вне скоупа RF-00), долг RF-CI | — | overlay `docker-compose.local-stand.yml` поверх pilot |
| Δ2 | Базовая линия — ссылка на run ветки, а не develop; «в этой ветке»; ретро-правка записи; порядкозависимые тесты не в долге | 🟡 | исправлено: run 36407616564; ветка названа; исходная строка восстановлена + «Дополнение»; долг добавлен | нет | `gh run view 36407616564` → push develop success |

### Гейт
2026-09-27, `.venv`, `set -o pipefail`, после круга 3:
- (1) статусы: скрипт по таблицам сверки → 94 строки, 0 дублей, 0 без статуса: 4 исправлено · 3 частично · 87 актуально.
- (2) каждая актуальная/частичная строка имеет задачу `roadmap.yaml` или «новая» (колонка roadmap); ID задач существуют (ревьюер, круги 1–2: 23/23).
- (3) пересечения с `docs/audit/2026-08-26-*` — колонка «2026-08-26 / PROJECT_STATE».
- (4) ревью: круг 1 — 27 ID, круг 2 — 33 ID, круг 3 — 23 ID перепроверены; вердикты APPROVE WITH COMMENTS ×3, 🔴 нет, все 🟠/🟡 закрыты.
- (5) `python3 scripts/ci/roadmap-governance-guard.py` → rc 0 PASS; `--self-test` → rc 0 55/55;
  I-0 `python scripts/ci/check-import-boundaries.py` → rc 0; `git diff --check` → rc 0.
  JSON Schema job — не затрагивается (нет изменений `packages/contracts/`), не запускался.
- Не выполнено в RF-00 (по скоупу): живые PostgreSQL/NATS/MinIO/Docker для строк «вероятно»; видимость GHCR; CI ветки — на `/finish`.

### Итог
- Статус: finished (PR ждёт merge владельцем)
- Коммит и PR: `gh pr list --head fix/RF-00` · CI: результат проверок PR — в отчёте `/finish` (в коммит не входит)
- Дополнение 2026-09-28: Коммит `6bb5b2c` · PR #9 · push-run 36392472274 attempt 1 → failure (6 failure + 3 cancelled) — внешний дрейф (SQLAlchemy 2.1, `minio/minio`, `dl.min.io`), не RF-00; исправлено этапом RF-CI (PR #10). `phase1-ci.yml` запускается только на `push` по дереву ветки (PR-триггер — только `main`), поэтому `develop @ 6bc9ac0` влит в ветку merge-коммитом `3892552` (решение владельца 2026-09-28); повторный CI — push-run ветки с этой записью
- Доказано: статус каждой из 94 строк находок ревью `8ad0228` на `develop @ b166419` с file:line;
  4 исправлено (P0-13, P1-5, T5, T6), 3 частично (P0-10.b, P1-15, P2-F3), 87 актуально.
- Долг / ожидает решения владельца:
  - порядок и состав черновиков RF-01…RF-09 (`stages.md`, статус `draft`); новые задачи в `roadmap.yaml` через OD;
  - RF-01 пересекается по коду с RM-STAB-004 (S, in_progress);
  - 3 расхождения канона с кодом (PROJECT_STATE LIFECYCLE-COMPLETE «real DB proof», pilot «Verify green», canon §2.4);
  - 4 теста, закрепляющие дефекты, — замена только с одобрения владельца;
  - 9 строк «вероятно» — доказательство на живых PostgreSQL/NATS/MinIO в своих этапах; видимость старых пакетов GHCR — внешнее действие владельца;
  - разовый self-test 54/55 в baseline (не воспроизведён, причина не установлена).
- Новые инварианты: нет (этап документальный, поведение не менял).
- Следующий шаг: merge PR владельцем → решение по черновикам → `/start RF-<N>`.

## RF-CI — CI снова собирается (внеплановый этап)

- Статус: merged (PR #10 → `develop @ 6bc9ac0`, владелец 2026-09-28)
- Ветка: fix/RF-CI · Основа: develop @ b166419 · Коммит `ebc1832`
- Причина: push-run `fix/RF-00` 36392472274 → 6 failure + 3 cancelled по внешним причинам, воспроизведено локально:
  SQLAlchemy 2.1.1 (`postgresql://` → psycopg v3; без `[asyncio]` нет greenlet); Docker Hub `minio/minio` —
  анонимный pull запрещён на всех тегах, quay.io — нет манифеста; `dl.min.io` mc → HTTP 410.
- План и решения владельца — см. «Решения владельца» (2026-09-28). Карточка и журнал RF-CI записаны в ветке `fix/RF-00`
  (`docs/remediation/` на `fix/RF-CI` отсутствовал), после merge PR #10.

### Сделано
- `phase1-ci.yml`: `"sqlalchemy>=2.0,<2.1"` во всех `pip install`; MinIO `cgr.dev/chainguard/minio@sha256:6a1d0b45…`;
  шаг «Wait for MinIO» (curl до 200, `--retry-all-errors`, ≤120 с); `mc` из `cgr.dev/chainguard/minio-client@sha256:b2bd7824…`
  с явным pull, без `|| true`; `pipefail` у import smoke.
- requirements control-api / device-gateway / orchestrator-worker: `<2.1` с комментарием причины.
- compose restore-drill / phase1 / pilot: образ по digest, healthcheck через bash `/dev/tcp`; pilot и phase1 — `user: "0"`.
- `backup-restore-drill.sh`: `MINIO_SERVER_VERSION` = `RELEASE.2026-09-22T19-25-18Z`.

### Доказательства
- Локально: import smoke 5 сервисов — на 2.1.1 `ImportError greenlet`, с pin 5× OK; `alembic upgrade head` на PostgreSQL 16
  через `postgresql://` → 037; `test_stand_rollback_drill.py` 3 passed; drill MinIO `up --wait` → Healthy; healthcheck 200 → 0,
  403 → 1; шаги CI Wait/Setup под `bash -e` rc 0 (повтор rc 0, без сервера rc 7 за 60 с); UID 65532 на root-томе с данными →
  `file access denied` (основание `user: "0"`).
- CI: push-run ветки `fix/RF-CI` (head `ebc1832`) 36404147483 attempt 1 → success, 41/41 (UI-Smoke, Backup/Restore Drill, Behavioral, Rollback Drill, release-gate).
- Не запускалось локально: Backup/Restore Drill (нет `pg_dump`), UI-smoke — доказаны CI.
- Наблюдение: локальный `pytest tests/` — 7 падений и на чистом develop (зависят от порядка, по отдельности проходят); в CI зелёно.

### Ревью
| Круг | Замечание | Уровень | Решение | Риск исправления | Доказательство |
|---|---|---|---|---|---|
| 1 | `mc` с `2>/dev/null \|\| true` — недоступный образ молча не создаст бакеты | 🟠 | исправлено: явный `docker pull`, `mb --ignore-existing`, без подавления | низкий: шаг строже | шаг под `bash -e` rc 0, повтор rc 0 |
| 1 | Апгрейд pilot-тома 2024-11 → 2026-09 не проверен, откат не описан | 🟠 | отклонено с обоснованием → долг: старый образ недоступен нигде — ни тест, ни откат невозможны | — | `docker manifest inspect` Docker Hub/quay → denied / no manifest |
| 1 | Нет карточки RF-CI с одобрением Protected Boundary | 🟠 | одобрение владельца получено в сессии 2026-09-28; записано здесь и в PR #10 | — | «Решения владельца» 2026-09-28 |
| 1 | Digest Chainguard может исчезнуть (free tier — только `latest`) | 🟠 | долг: не проверяемо кодом; вариант — зеркало в GHCR | — | — |
| 2 | phase1 compose: существующие dev-тома под UID 65532 | 🟠 | исправлено: `user: "0"` как в pilot | низкий | `compose config` OK |
| 2 | Комментарий pin неточен (greenlet приходит с `[asyncio]` и в 2.1) | 🟡 | исправлено: причина — psycopg v3 | нет | `pip install --dry-run "sqlalchemy[asyncio]==2.1.1"` → greenlet |
| 2 | `mc ls \|\| true` | 🟡 | исправлено | нет | шаг rc 0 |
| 3 | `pip \| tail` без pipefail (строка правилась) | 🟡 | исправлено | низкий | CI 41/41 |
| 3 | Ожидание MinIO не ограничено по времени целиком | 🟡 | исправлено: `--retry-max-time 120 --connect-timeout 2 --max-time 5` | нет | без сервера rc 7 за 60 с |
| 1–3 | `MINIO_SERVER_VERSION` захардкожена; runbook `minio/minio:latest`; двойной CORS; голые `postgresql://`; `prepare-ui-smoke-stack.sh` с mc | 🟡 | долг | — | — |

### Итог
- Коммит `ebc1832` · PR #10 · push-run 36404147483 → success · merged `6bc9ac0`.
- Долг: апгрейд pilot MinIO на живом томе не проверен и необратим — **бэкап MinIO перед обновлением stand-81**; non-root MinIO
  после `chown -R 65532` томов (операция владельца); сохранность digest Chainguard / зеркало в GHCR; снять pin после явных
  `postgresql+psycopg2://` (RM-STAB-009); runbook `pilot-deployment-readiness.md`; `prepare-ui-smoke-stack.sh`; двойной CORS;
  `MINIO_SERVER_VERSION`; 7 порядкозависимых падений локального `pytest tests/` (есть и на чистом develop, в CI зелёно) —
  дефект изоляции тестов, не разбирался; runbook/preflight без шага бэкапа MinIO перед апгрейдом stand-81.
- Новые инварианты: нет отдельной команды — зелёный `Phase 1 — Quality Gates` (включая UI-Smoke и drill) и есть проверка.
- Следующий шаг: `develop @ 6bc9ac0` влит в `fix/RF-00` (`3892552`); push-run ветки RF-00 → зелёный → merge PR #9 владельцем.

## RF-01 — Refresh-токены: обнаружение повтора и атомарная ротация

- Статус: finished (PR ждёт merge владельцем)
- Дополнение 2026-09-29: merged — PR #11 → `develop @ d8dbd62`; push-run develop 36475858226 attempt 1 → success 41/41; RM-STAB-018 → `done` (решение владельца 2026-09-29, в ветке `fix/RF-05`)
- Ветка: fix/RF-01 · Основа: develop @ 7762434 (merge PR #9)
- Baseline (2026-09-28, `.venv` Python 3.12.3, зависимости — дословно из `phase1-ci.yml`, `set -o pipefail`, код = develop):
  - I-0 `python scripts/ci/check-import-boundaries.py` → rc 0 «All import boundaries clean.»
  - `python scripts/ci/roadmap-governance-guard.py` → rc 0 PASS (после записи RM-STAB-018/OD-046 и генерации); `--self-test` → 55/55
  - python-tests (`python -m pytest tests/ -v`, env job) → rc 0: 1909 passed, 534 skipped.
    Первый прогон шёл параллельно с behavioral и дал 2 failed `TestScopeAdminReset` — тест пробует сокет `localhost:5432`
    и при живом порте ходит в `DATABASE_URL=db.ci.internal`; артефакт локальной среды, без PostgreSQL на 5432 — зелёно.
  - behavioral (шаги job дословно: postgres:16-alpine, migrations, seed, `retail_media_app` NOBYPASSRLS) → rc 0: 477 passed, 12 skipped.
- План:
  - Задача: повтор ротированного refresh-токена позже 10 с отзывает всю семью (+audit `auth.refresh.replay_detected`), в пределах
    10 с — 401 без отзыва; ротация атомарна (блокировка строки + условный UPDATE); отзыв коммитится до 401.
  - Домен: `packages/auth` (repository, service), `packages/api/auth.py` (роутер), `packages/security/config.py`. ADR-014: api → auth → domain, не меняется.
  - Protected Boundaries: нет. Миграций нет.
  - Доказательство: `tests/behavioral/test_rm_stab_018_refresh_replay.py` под `retail_media_app` (падает на develop), замена
    маскирующего unit-теста, существующие `test_auth_dual_e2e.py` и python-tests зелёные.

### Сделано
- RM-STAB-018 (S, in_progress) и OD-046 в `roadmap.yaml`; RM-STAB-018 в `roadmap_ids` REQ-SEC-001; `roadmap-generate.py`.
- Карточка RF-01 в `stages.md`; строка черновика RF-01 → «RF-01-остаток».
- `packages/auth/repository.py`: `lock_refresh_session` — поиск по хэшу в любом состоянии + `FOR UPDATE`; `rotate_refresh_session`
  условный (`rotated_at IS NULL AND revoked_at IS NULL`) → bool; `revoke_refresh_token_family` без `last_error`/`reason`; убран
  неиспользуемый импорт `delete`.
- `packages/auth/service.py::refresh_session`: revoked → REFRESH_FAILED; rotated ≤ окна → REFRESH_FAILED без отзыва; rotated > окна →
  отзыв семьи + audit `auth.refresh.replay_detected` (actor = владелец сессии, target = предъявленная сессия, details: семья, число
  отозванных) → REFRESH_REPLAY; expired → REFRESH_FAILED; проигранная гонка ротации → REFRESH_FAILED.
- `packages/api/auth.py::refresh`: `await db.commit()` перед 401 (как `login`).
- `packages/security/config.py`: `refresh_reuse_grace_seconds = 10`.
- `tests/behavioral/test_rm_stab_018_refresh_replay.py` (3 теста): на develop-коде 2 failed (семья не отозвана; 4 параллельных
  refresh → `[200, 200, 200, 200]`), после — 3 passed. Tamper: без `db.commit()` перед 401 → тест повтора красный.
- `tests/test_phase3_auth_service.py`: `test_replay_calls_family_revoke` заменён (одобрено) на 4 теста — компиляция UPDATE семьи
  под PostgreSQL, запрос блокировки без фильтров rotated/revoked + FOR UPDATE, повтор после окна → отзыв + audit, отозванный токен →
  без повторного отзыва. Адаптированы без ослабления (цель патча `find_active_refresh_session` → `lock_refresh_session`/
  `rotate_refresh_session`, снят аргумент `reason`): `test_refresh_success`, `test_refresh_invalid_token_fails`,
  `test_rotated_token_is_not_active` (мок теперь — ротированная в окне сессия + проверка «семья не отозвана»),
  `test_revoke_refresh_token_family_revokes_all_active`, `test_revoke_family_leaves_unrelated_family_active`,
  `test_normal_refresh_does_not_revoke_family` (добавлены отсутствовавшие проверки «семья не отозвана», «ротация вызвана»).
- Круг 1 ревью: advisory-lock семьи в `lock_refresh_session`; audit `auth.refresh.reuse_within_grace`; тесты
  `TestFamilySerialisation` (2), `test_inactive_user_refresh_revokes_session`; unit `test_lock_unknown_token_takes_no_lock`,
  переименование; приёмка RM-STAB-018 дополнена сериализацией.
- Круг 2 ревью: порядок проверок в `refresh_session` (rotated → revoked); unit `test_replay_of_burned_family_is_not_audited_again`
  (заменил свой же тест круга 1 `test_revoked_token_fails_without_family_revoke`), `test_revoked_unrotated_token_fails_without_family_revoke`;
  behavioral `test_replay_detected_after_session_limit_revoked_rotated_row`.
- Самопроверка после круга 2: behavioral 484 passed / 12 skipped rc 0 (RM-STAB-018 7/7); python-tests 1914 passed / 541 skipped rc 0;
  I-0 rc 0; guard PASS; self-test 55/55; `git diff --check` rc 0; ruff — новых ошибок нет.
- Самопроверка после круга 1: behavioral 483 passed / 12 skipped rc 0; python-tests 1913 passed / 540 skipped rc 0; I-0 rc 0;
  guard PASS; self-test 55/55; `git diff --check` rc 0; ruff — новых ошибок нет.
- Самопроверка (до ревью): behavioral 480 passed / 12 skipped rc 0; python-tests 1912 passed / 537 skipped rc 0; I-0 rc 0; guard PASS;
  self-test 55/55; `git diff --check` rc 0; ruff по изменённым файлам — новых ошибок нет (repository 1→0, service 5→5, api/auth 3→3,
  config 0, тест-файлы 19→19 и 0; старые ошибки — долг, вне скоупа).

### Решения
- Найден второй скрытый дефект: `revoke_refresh_token_family` пишет несуществующую колонку `last_error` →
  `CompileError: Unconsumed column names: last_error` (проверено компиляцией). Исправляется без миграции; причина — в audit.
- Окно повтора — поле `SecurityConfig.refresh_reuse_grace_seconds = 10`, без env-переменной (иначе правка `.env.example` —
  Protected Boundary).

### Ревью
| Круг | Замечание | Уровень | Решение | Риск исправления | Доказательство |
|---|---|---|---|---|---|
| 1 | Отзыв семьи не сериализован с refresh той же семьи: преемник переживает «сожжённую» семью; два повтора → deadlock → 500 | 🟠 | исправлено: `lock_refresh_session` читает семью, берёт `pg_advisory_xact_lock(18, hashtext(family))` ДО блокировки строки; 2 behavioral-теста | средний: новый lock на горячем пути refresh; одна семья = одна сессия пользователя, конкуренция только внутри неё; logout/login/admin revoke-all advisory не берут — цикл на блокировках строк с ними возможен (круг 2 п.2, круг 3 п.1 — долг) | до исправления на PostgreSQL: `DeadlockDetectedError` и выживший `revoked_at=None`; после — 6/6 passed, 3 повтора подряд стабильно |
| 1 | Повтор внутри окна не оставляет следа | 🟠 | исправлено: audit `auth.refresh.reuse_within_grace` без отзыва семьи (OD-046 не меняется) | низкий: +1 строка аудита на гонку вкладок | behavioral `test_replay_within_grace_keeps_family` проверяет ровно одну запись; unit |
| 1 | Окно сравнивает часы разных инстансов (`rotated_at` из Python) | 🟡 | долг: `expires_at`/`issued_at` во всём auth тоже на часах Python; переход на часы БД — отдельная правка всего модуля; требование NTP для multi-instance | — | — |
| 1 | `db.commit()` при любом отказе сохраняет и revoke на USER_INACTIVE — не описано | 🟡 | исправлено: behavioral `test_inactive_user_refresh_revokes_session`; записано здесь | нет (исправление: раньше revoke откатывался) | тест passed |
| 1 | Имя `test_rotated_token_is_not_active` не отражает проверку | 🟡 | исправлено: `test_rotated_within_grace_fails_without_family_revoke` | нет | unit 57 passed |
| 1 | Параллельный тест не доказывает, что гонка была | 🟡 | закрыто фактом: на develop-коде в этой сессии `[200, 200, 200, 200]` | — | журнал «Сделано», прогон до исправления |
| 2 | Лимит сессий при login отзывает ротированные строки → их повтор попадал в ветку «revoked», семья и преемник вора живы | 🟠 | исправлено (вариант «а», в скоупе refresh): `rotated_at` проверяется до `revoked_at`; отзыв семьи идемпотентен, audit только при `revoked > 0`; дефект самого лимита (ротированные строки занимают квоту) — долг, это login | низкий: повтор уже сожжённой семьи даёт REPLAY вместо FAILED — оба 401 `INVALID_TOKEN`, клиент не различает | behavioral `test_replay_detected_after_session_limit_revoked_rotated_row` через реальные 5 login: до правки FAILED (преемник жив), после — passed |
| 2 | logout и админский revoke-all не берут advisory-lock семьи: редкий deadlock/выживший преемник | 🟡 | долг: logout/admin вне скоупа карточки | — | — |
| 2 | Окно 10 с: ложный отзыв при потерянном ответе и повторе > 10 с; вор первым в окне | 🟡 | долг/остаточный риск принятого OD-046 — в отчёт владельцу | — | — |
| 2 | +2 round-trip на refresh; коллизии `hashtext` лишь сериализуют чужие семьи | 🟡 | принято, информационно | — | — |
| 2 | Гоночный тест не проверяет коды ответов (500 прошёл бы) | 🟡 | исправлено: коды ⊆ {200, 401} | нет | 7/7 passed |
| 3 | Deadlock login (`revoke_oldest_sessions`, строки по `issued_at`) × повтор (FOR UPDATE строки + UPDATE семьи); запись круга 1 «цикла нет» неверна | 🟡 | долг (login вне скоупа; связан с дефектом квоты ротированных строк); запись круга 1 исправлена | — | по коду, не воспроизводилось |
| 3 | notes RM-STAB-018: «гонка вкладок закрыта окном» — сильнее факта | 🟡 | исправлено: семья не отзывается, 401 проигравшей вкладке — до RF-08 | нет | `roadmap.yaml`, генерация, guard PASS |
| 3 | Нет rate limit на `/refresh`: повторы в окне пишут audit без ограничения | 🟡 | долг (нужен валидный только что ротированный токен, 10 с) | — | — |

### Гейт
2026-09-28, `.venv`, `set -o pipefail`, после круга 3 (код не менялся с круга 2):
- behavioral (шаги job `behavioral-postgres-tests` дословно, `retail_media_app` NOBYPASSRLS) → rc 0: 484 passed, 12 skipped;
  `test_rm_stab_018_refresh_replay.py` 7/7 и `test_auth_dual_e2e.py` 8/8 — PASSED.
- python-tests (`python -m pytest tests/ -v`, env job) → rc 0: 1914 passed, 541 skipped.
- I-0 → rc 0; `roadmap-governance-guard` → PASS; `--self-test` → 55/55; `git diff --check` → rc 0.
- ruff по изменённым файлам: 27 = ровно ошибки develop (service 5, api/auth 3, test_phase3_auth_service 19); repository 1 → 0; новых нет.
- Ревью: 3 круга, APPROVE WITH COMMENTS ×3; 🔴 нет; 🟠 — 3, все исправлены с тестом, падавшим до исправления; 🟡 — исправлены или в долге.
- Не запускалось: frontend/UI-smoke (не затронуты); CI — на `/finish`.

### Долг (к `/finish`)
- Остаточные риски OD-046: ложный отзыв семьи при потерянном ответе и повторе позже 10 с; вор, первым успевший в окне, сохраняет сессию, если законный клиент не повторит после окна.
- Квота сессий (`count_active_sessions`/`revoke_oldest_sessions`) считает ротированные строки активными — живые сессии других устройств отзываются раньше срока (было до RF-01; login).
- logout, admin revoke-all и login-лимит не берут advisory-lock семьи: редкий deadlock → 500 / выживший преемник.
- Окно сравнивает часы Python разных инстансов (NTP для multi-instance); весь auth на часах Python.
- Нет rate limit на `/refresh`; audit `reuse_within_grace` на каждый повтор в окне.
- Старые ошибки ruff в `service.py`, `api/auth.py`, `test_phase3_auth_service.py`.
- Проигравшая вкладка портала получает 401 до single-flight (P1-13.b, RF-08).

### Итог (заполняет /finish)
- Коммит и PR: `gh pr list --head fix/RF-01` · CI: результат проверок PR — в отчёте `/finish` (в коммит не входит).
- Доказано: P0-7 закрыта на PostgreSQL под `retail_media_app` — повтор после 10 с отзывает семью с audit, в окне — 401 без отзыва
  с audit `reuse_within_grace`; параллельные refresh → одна ветка; повтор против refresh и два повтора одной семьи — без выживших и
  без deadlock; повтор строки, отозванной лимитом сессий, всё равно сжигает семью; отзыв и revoke USER_INACTIVE переживают 401.
  Каждый сценарий — тест, падавший на коде до исправления.
- RM-STAB-018 остаётся `in_progress`: `done` — после merge и зелёного CI develop, решением владельца.
- Долг — раздел «Долг (к `/finish`)» выше; отклонённых 🟠 нет.
- Новые инварианты: I-1.
- Следующий шаг: merge PR владельцем → выбор следующего черновика (остаток RF-01: P0-6/P0-8 vs RM-STAB-004; RF-05; RF-02…) → `/start RF-<N>`.

## RF-05 — Pilot-контур поднимается, verify честный

- Статус: finished (PR ждёт merge владельцем)
- Ветка: fix/RF-05 · Основа: develop @ d8dbd62 (merge PR #11)
- Сделано до правок (решения владельца 2026-09-29): RM-STAB-018 → `done` в `roadmap.yaml` с `evidence_refs`
  (behavioral + ci_run 36475858226), генерация; guard PASS, self-test 55/55. `PROJECT_STATE.md` ещё пишет «RM-STAB-018 —
  `in_progress`», checkpoint обновится на `/finish`. Журнал RF-01 → merged. Карточка RF-05 → `planned`.
- Факты, собранные для плана (код `d8dbd62`):
  - `ENVIRONMENT=pilot` → `_is_dev()` false → `_validate_production` (`packages/security/config.py:47-54`).
  - `Dockerfile.service:30` уже копирует `infra/compose/` в образ; `create-app-role.py` в образе есть, но в `db-migrate` не вызывается,
    `POSTGRES_APP_PASSWORD` не передаётся; docstring «STAGED» устарел.
  - device-gateway: CORS-middleware из `get_security_config()` (`apps/device-gateway/main.py:229`), в pilot-compose нет
    `CORS_ALLOWED_ORIGINS`, `JWT_AUDIENCE`; orchestrator — нет CORS и `METRICS_AUTH_TOKEN`.
  - `Dockerfile.service` не объявляет `ARG RMP_VERSION` — build-args `build-images.sh:89-91` не попадают в образ; версия приходит
    только из env compose, verify сверяет её с тем, что сам же передал.
  - Тесты, закрепляющие дефекты pilot-compose и workaround overlay стенда: `tests/test_local_stand.py`
    (`test_pilot_compose_still_omits_cors_for_device_gateway`, `test_pilot_compose_still_omits_manifest_key_for_control_api`).
  - `verify-pilot-run.sh` запускается только `verify-pilot-images.yml` (workflow_dispatch, образы из GHCR).
- Решения владельца по плану (2026-09-29, AskUserQuestion): список файлов защищённой зоны 1–8 целиком
  (`docker-compose.pilot.yml`, `create-app-role.py`, `verify-pilot-run.sh`, `docker-compose.local-stand.yml`,
  `docker-compose.phase1.yml`, `phase1-ci.yml`, `Dockerfile.service`, `.env.pilot.example`); тесты-маски
  `test_pilot_compose_still_omits_*` (+ парные `test_overlay_supplies_*`) — заменить; доказательство — новый CI-job
  «pilot compose smoke» + локальный прогон. Не трогаются: `verify-pilot-images.yml`, `publish-pilot-images.yml`,
  `build-images.sh`, `scripts/deploy/local_stand.py`, прод-конфигурация.
- Baseline (2026-09-29, `.venv` Python 3.12.3, `set -o pipefail`, код = `d8dbd62`):
  - I-0 → rc 0 «All import boundaries clean.»
  - I-1 / behavioral (шаги job дословно, postgres:16-alpine, `retail_media_app` NOBYPASSRLS) → rc 0: 484 passed, 12 skipped;
    RM-STAB-018 7/7 PASSED.
  - python-tests (`python -m pytest tests/ -v`, env job) → rc 0: 1914 passed, 541 skipped.
  - `roadmap-governance-guard` → PASS; `--self-test` → 55/55 (после правки RM-STAB-018).
- План:
  - Задача: pilot-compose с `ENVIRONMENT=pilot` поднимается с нуля: `db-migrate` создаёт роль приложения (`create-app-role.py`),
    сервисы получают недостающие env (device-gateway: CORS, `JWT_AUDIENCE`; воркер: CORS, `METRICS_AUTH_TOKEN`; control-api:
    `MANIFEST_SIGNING_KEY`); `_validate_production` требует непустой `JWT_AUDIENCE`; версия запекается в образ
    (`Dockerfile.service` ARG/ENV); verify — `ENVIRONMENT=pilot`, без ручной роли, таймаут = fail, head из миграций,
    версия образа сверяется с lock; readiness control-api строг во всех строгих окружениях (P2-I11); alembic env —
    экранирование `%`, без localhost-fallback в строгих окружениях (P2-I9); phase1 dev-compose — порты и healthcheck nats
    (P1-16); import smoke под `ENVIRONMENT=pilot` (T12).
  - Домены: infra/compose, scripts/ci, `packages/security/config.py`, `apps/control-api` (readiness, alembic env).
    ADR-014 не меняется.
  - Protected Boundaries: «Docker, deployment scripts» (одобрено с условиями) + `.env.pilot.example` (файл 8 списка).
  - Доказательство: CI-job «Pilot compose smoke» (и локальный прогон того же скрипта) — db-migrate exit 0, все сервисы healthy,
    роль NOBYPASSRLS создана compose, версия из образа, device-токен control-api принят device-gateway, `get_security_config()`
    в воркере; unit-тесты валидатора и compose; замена тестов-масок.

### Сделано
- Тесты сначала: `tests/test_rf05_pilot_boot.py` — на коде `d8dbd62` 11 из 14 падали (config каждого backend-сервиса под
  `ENVIRONMENT=pilot` из env compose; device-токен control-api → device-gateway; `JWT_AUDIENCE` обязателен; `db-migrate`
  создаёт роль; readiness pilot/staging; alembic `%` и fallback), после — 14/14; +2 теста phase1 (на compose develop — 2 failed).
- `docker-compose.pilot.yml`: `db-migrate` вызывает `create-app-role.py` до grant, получает `POSTGRES_APP_USER`
  (`:-retail_media_app` — grant всё равно жёстко на эту роль) и `POSTGRES_APP_PASSWORD`; control-api ← `MANIFEST_SIGNING_KEY`;
  device-gateway ← `JWT_AUDIENCE`, CORS; orchestrator-worker ← `JWT_AUDIENCE`, CORS, `METRICS_AUTH_TOKEN`; healthcheck
  frontend → `127.0.0.1` (FU5 — найден локальным прогоном, решение владельца «исправить»). Все секреты — `${VAR}`; `user: "0"`
  MinIO не менялся (обоснование в комментарии, RF-CI).
- `packages/security/config.py::_validate_production`: пустой `JWT_AUDIENCE` → ValueError.
- `apps/control-api/main.py` readiness: строгая проверка роли БД везде, кроме `dev|development|local|test` (было: только `production`).
- `apps/control-api/alembic/env.py`: `%` → `%%` для ConfigParser; без `DATABASE_URL` вне dev — RuntimeError вместо localhost.
- `Dockerfile.service`: `ARG`/`ENV RMP_VERSION|RMP_GIT_SHA|RMP_BUILD_TIME` (build-args `build-images.sh` теперь в образе).
- `verify-pilot-run.sh`: переписан — `ENVIRONMENT=pilot`, без ручного `CREATE ROLE`, `compose up --wait --wait-timeout`
  (таймаут = fail), exit `db-migrate`, роль LOGIN/NOSUPERUSER/NOBYPASSRLS, readiness, identity из `docker image inspect` = ожидаемой,
  `/version` и `/build-info.json`, device-токен control-api принят device-gateway (не 401), конфиг воркера; режим
  `--images-from-env <version> <sha>` для CI. Отдельный файл `pilot-run-proof.sh` был создан и удалён — вне утверждённого списка.
- `docker-compose.local-stand.yml`: сняты дубли обходов FU2 (`MANIFEST_SIGNING_KEY`), FU3 (CORS device-gateway), FU5 (healthcheck).
- `tests/test_local_stand.py`: заменены (одобрено) `test_pilot_compose_still_omits_manifest_key_for_control_api`,
  `test_overlay_supplies_manifest_key_to_control_api`, `test_pilot_compose_still_omits_cors_for_device_gateway`,
  `test_overlay_supplies_cors_to_device_gateway`, `test_pilot_healthchecks_still_use_localhost`,
  `test_overlay_healthcheck_avoids_localhost_ambiguity` → положительные проверки pilot + «overlay не дублирует».
- `docker-compose.phase1.yml`: ClickHouse native на хосте 9002 (9000 — MinIO); healthcheck nats → `wget :8222/healthz`
  (в `nats:2-alpine` нет CLI `nats` — проверено `command -v`).
- `.env.pilot.example`: `RMP_SCHEMA_HEAD=REPLACE_WITH_LOCK_SCHEMA_HEAD` (было устаревшее `034`), комментарии; только заглушки.
- `phase1-ci.yml`: шаг import smoke под `ENVIRONMENT=pilot` для 3 pilot-сервисов (CI-заглушки, не секреты); job
  `pilot-compose-smoke` (`build-images.sh` без push → `verify-pilot-run.sh --images-from-env`), добавлен в `release-gate`.
- Локальное доказательство: образы собраны из ветки (флаги как в `build-images.sh`, он отказывает на грязном дереве),
  `verify-pilot-run.sh --images-from-env` → rc 0 «VERIFY-PILOT-RUN PASSED», 9 сервисов healthy, device-токен → 404 (не 401).
  1-й прогон упал на FU5 (advertiser-web unhealthy). Tamper: pilot-compose из develop → rc 1 «FAIL: db-migrate exit code=1».

- Задача `RM-PILOT-002A` (POPS, in_progress) в `roadmap.yaml`, ссылка в REQ-ARCH-004 `roadmap_ids`, генерация.
- Адаптация фикстур «сильный prod-конфиг» без ослабления (тот же приём, что S-065 для `METRICS_AUTH_TOKEN`): `JWT_AUDIENCE` в
  `tests/test_production_config_gate.py::_prod_config`, `test_phase3_security.py::TestSecurityConfig.setUp`,
  `test_phase2_health.py::TestCorsConfig.setUp`; +2 теста gate (`JWT_AUDIENCE` отсутствует / пробелы → ValueError).
  До адаптации — 32 failed (ошибка `JWT_AUDIENCE` раньше ожидаемой или отказ «accepts»).
- Самопроверка (до ревью): python-tests → rc 0: 1933 passed, 541 skipped (skipped = baseline); behavioral → rc 0: 484 passed,
  12 skipped (RM-STAB-018 7/7); I-0 rc 0; guard PASS; self-test 55/55; `git diff --check` rc 0; ruff — новых нет (`main.py` 5→5,
  `test_local_stand.py` 1→1 — ошибки develop); shellcheck `verify-pilot-run.sh` rc 0; `compose config` pilot / phase1 /
  pilot+local-stand → OK; локальный pilot proof rc 0.

### Решения
- Логика доказательства — внутри `verify-pilot-run.sh` (режим `--images-from-env`), а не новым скриптом: новый файл в защищённой
  зоне не входил в утверждённый список.
- «Версия из образа» проверяется через `docker image inspect` (ENV образа = lock/ожидание); compose по-прежнему передаёт
  `RMP_VERSION` из env — снятие этого из compose меняет контракт `validate-pilot-env.py`/`local_stand.py`, вне скоупа.
- CORS для сервисов без браузера передаётся через compose (вариант «a»), валидатор не ослабляется.

### Ревью
| Круг | Замечание | Уровень | Решение | Риск исправления | Доказательство |
|---|---|---|---|---|---|
| 1 | Проверка device-токена в verify принимает любой статус ≠ 401 (500 прошёл бы) | 🟠 | исправлено: ровно 404 + `"Device not found"` — доказывает и путь через БД под `retail_media_app` | низкий: проверка строже | `dependencies.py:359`, `device-gateway/main.py:181`; прогон rc 0 «404 Device not found» |
| 1 | Обязательный `JWT_AUDIENCE` может уронить стенд (`.env.stand` без него; `validate_stand_env` не проверяет) | 🟠 | отклонено как правка кода: `scripts/deploy/local_stand.py` вне утверждённого списка файлов → владельцу: перед выкаткой на стенд проверить `JWT_AUDIENCE` в `.env.stand`; долг — проверка в `validate_stand_env` | — | `grep JWT_AUDIENCE scripts/deploy/local_stand.py` → пусто; preflight pilot требует её (`pilot_host_preflight.py:80`) |
| 1 | `verify-pilot-images.yml` на старых релизах теперь падает (в их образах нет ENV identity) | 🟠 | отклонено с обоснованием: fail-closed — цель P0-5 (версия из образа); контракт workflow меняется — записано в долг и в PR для решения владельца | — | develop `Dockerfile.service` без ARG/ENV |
| 1 | `/version` сверяет значения, которые скрипт сам записал; комментарий Dockerfile сильнее факта | 🟡 | исправлено: комментарий уточнён; снятие `RMP_VERSION` из compose — долг (контракт `.env.pilot`) | нет | Dockerfile.service |
| 1 | Pilot import smoke для воркера ничего не доказывает | 🟡 | исправлено: шаг явно грузит `get_security_config()` и требует `dev_mode=False`; комментарий о границе доказательства | низкий | тело шага локально под `bash -e` → 3× «import OK (pilot)» |
| 1 | `create-app-role.py`: существующая роль не сверяется (атрибуты, пароль), имя без валидации | 🟡 | долг (атрибуты ловит строгий readiness; `POSTGRES_APP_USER` по умолчанию `retail_media_app`) | — | — |
| 1 | Разные списки «dev» (main/alembic vs `_is_dev`); пустой `ENVIRONMENT` в alembic → dev | 🟡 | долг: общий хелпер; alembic при **незаданном** `ENVIRONMENT` сохраняет прежнее dev-поведение (пустая строка — строгий режим) | — | — |
| 1 | Docstring теста ссылается на несуществующий скрипт | 🟡 | исправлено | нет | — |
| 1 | Регулярка не видит `${VAR:-default}` | 🟡 | исправлено: default учитывается в подстановке и в проверке `.env.pilot.example` | нет | 16 passed |
| 1 | Нет `timeout-minutes` у job | 🟡 | исправлено: 30 | нет | yaml |
| 1 | Непонятная ошибка при отсутствии контейнера db-migrate | 🟡 | исправлено: явный `fail` | нет | shellcheck rc 0 |
| 2 | `JWT_AUDIENCE` не проверяется `validate-pilot-env.py`/`validate_stand_env` до старта | 🟠 | то же, что круг 1 п.2: файлы вне утверждённого списка → решение владельца до выкатки на стенд/pilot-хост; риск открыт | — | `grep JWT_AUDIENCE scripts/deploy/validate-pilot-env.py scripts/deploy/local_stand.py` → пусто |
| 2 | Lock-режим verify брал schema head из checkout, а не из релиза | 🟠 | исправлено: `release.schema_head` из lock (понятный FAIL, если нет); `--images-from-env` — из миграций | низкий | shellcheck rc 0; example-lock без поля → '' → FAIL; живой lock-режим не запускался (нужен релиз в GHCR) |
| 2 | Пароль приложения может попасть в `docker logs` (traceback SQLAlchemy) и лог PG (`log_min_error_statement`) | 🟠 | исправлено: ошибка печатается без текста (класс + SQLSTATE); под суперпользователем `SET LOCAL log_min_error_statement = panic` перед DDL; DDL через `exec_driver_sql` (в `text()` `:` в пароле — bind-параметр); имя роли — `^[a-z_][a-z0-9_]{0,62}$`, `db_name` — quote_ident | низкий: owner с CREATEROLE без superuser работает (SET пропускается) | живой PG 16.4: пароль с `'`/`:`/`%` → роль создана, вход OK; сбой CREATE ROLE под superuser → в выводе и логе PG 0 вхождений, контроль без SET → 1; unit 5 тестов |
| 2 | CI job ещё не запускался | 🟠 | принято: доказательство CI — на `/finish`; при падении `--wait` — чинить, не маскировать | — | локальный прогон rc 0 (compose v5.5.1) |
| 2 | `.env.pilot.example`: комментарий подразумевал смену пароля | 🟡 | исправлено | нет | — |
| 2 | Docstring readiness «production only» | 🟡 | исправлено | нет | — |
| 2 | Тест секретов пропускал `${SECRET:-literal}` | 🟡 | исправлено: для секретных ключей — `${VAR}` без default | нет | 24→ passed |
| 2 | Тест readiness без unset/регистра/пробелов | 🟡 | исправлено: `" Pilot "`, unset, `DEV` | нет | passed |
| 2 | Compose healthcheck — `/health/live`, строгий readiness виден только через `/health/ready` | 🟡 | граница доказательства: verify вызывает `/health/ready` явно; перевод healthcheck — долг | — | — |
| 2 | Разные списки dev-окружений | 🟡 | долг (круг 1) | — | — |
- Самопроверка после круга 2: пересборка образов → verify `--images-from-env` rc 0; python-tests rc 0: 1941 passed, 541 skipped;
  I-0 rc 0; guard PASS; `git diff --check` rc 0; ruff — новых нет; shellcheck rc 0.
| 3 | Lock-режим verify требует `release.schema_head`, а `generate_release_lock.py` (публикация) его не пишет → `verify-pilot-images.yml` падает на любом релизе, включая будущие | 🔴 | **открыто — СТОП после 3-го круга**, регрессия круга 2 (моя правка); варианты — владельцу | — | `generate_release_lock.py:90-95` без `schema_head`; `publish-pilot-images.yml:127-129` build-args identity передаёт (identity у новых релизов будет) |
| 3 | Обязательный `JWT_AUDIENCE` не проверяется до старта стенда/pilot | 🟠 | открыто, решение владельца (файлы вне списка) | — | круги 1–2 |
| 3 | Вне карточки: `requirements-traceability.yaml` (RM-PILOT-002A в REQ-ARCH-004) и адаптация фикстур 3 тестовых файлов | 🟠 | открыто: нужно подтверждение владельца или откат traceability | — | дифф |
| 3 | `POSTGRES_APP_USER` настраивается наполовину (grant жёстко на `retail_media_app`) | 🟡 | открыто | — | `database.py:210,215` |
| 3 | Пароль в логе PG при `log_statement=ddl/all` | 🟡 | открыто (вариант: SCRAM-verifier или `SET LOCAL log_statement='none'`) | — | — |
| 3 | Pilot import smoke: `except SystemExit: pass` может скрыть отказ | 🟡 | открыто | — | — |
| 3 | Устаревший docstring `local_stand.py::provision_app_role` | 🟡 | долг (файл вне списка) | — | — |
| 3 | Разные списки dev-окружений | 🟡 | долг (круги 1–2) | — | — |

- Итог ревью: 3 круга — APPROVE WITH COMMENTS, APPROVE WITH COMMENTS, **REQUEST CHANGES** (🔴 п.1 круга 3). По `/start` шаг 7.4 — СТОП, этап
  не переведён в `ready_to_finish`. Ревьюер круга 3 локально получил 7 failed в полном `pytest tests/` (`DATABASE_URL refers to a localhost`)
  и те же 7 на снимке develop — порядкозависимые падения, известные с RF-CI; в env job python-tests у меня rc 0 (1941 passed).
| 3→Δ | 🔴 п.1 круга 3 | 🔴 | исправлено по решению владельца (вариант «а»): lock `release.schema_head`, иначе `git fetch --depth 1` коммита релиза (если его нет) → `git archive` миграций → `alembic_head.py --versions-dir`; невытягиваемый SHA → FAIL | низкий: только lock-режим; `--images-from-env` не менялся | harness блока: полный репо, lock без поля, `c088111` → 036; lock с полем → его значение; мелкий клон → fetch → 036; несуществующий SHA → rc 1 «not fetchable»; shellcheck rc 0 |
| 3→Δ | 🟠 п.3 круга 3 (вне карточки) | 🟠 | закрыто решением владельца 2026-09-29 | — | «Решения владельца» |
| 4 | Lock-режим verify целиком не запускался | 🟠 | принято: ветка schema head проверена harness-ом (4 случая, см. «3→Δ»); полный lock-режим требует релиза в GHCR — не доказан, в PR и долг | — | — |
| 4 | Старые релизы не проходят verify | 🟠 | закрыто решением владельца 2026-09-29 (п.4) | — | — |
| 4 | `JWT_AUDIENCE` на стенде | 🟠 | открыто, решение владельца (п.2) | — | — |
| 4 | Журнал неверно описывал пустой `ENVIRONMENT` в alembic | 🟡 | исправлено | нет | — |
| 4 | `POSTGRES_APP_USER` настраивается наполовину | 🟡 | исправлено в `.env.pilot.example` (комментарий «должно быть retail_media_app»); проверка в скрипте — долг | нет | — |
| 4 | `strip()` audience только в валидаторе | 🟡 | долг | — | — |
| 4 | Разные статусы RF-05 в `stages.md` | 🟡 | исправлено | нет | — |
| 4 | Устаревший docstring `local_stand.py` | 🟡 | долг (вне списка) | — | — |
| 4 | Контейнер `rf05-pg` мешал ревьюеру (2 failed `TestScopeAdminReset`) | 🟡 | артефакт параллельного прогона: ревью шло одновременно с моим behavioral-гейтом; скрипт удаляет контейнер в конце; после гейта контейнеров нет, python-tests гейта шёл после behavioral | нет | `docker ps -a` — пусто |

### Гейт
2026-09-29, `.venv` Python 3.12.3, `set -o pipefail`, после круга 4 (код после этого не менялся; правки круга 4 — комментарий `.env.pilot.example` и документы):
- Pilot proof: `verify-pilot-run.sh --images-from-env` на образах из ветки → rc 0 «VERIFY-PILOT-RUN PASSED» (9 сервисов healthy, роль создана
  `db-migrate`, readiness строгий, identity из образа, `404 Device not found`, конфиг воркера). Tamper: pilot-compose develop → rc 1.
- I-1 / behavioral (шаги job дословно, `retail_media_app` NOBYPASSRLS) → rc 0: 484 passed, 12 skipped; RM-STAB-018 7/7.
- python-tests (env job) → rc 0: 1941 passed, 541 skipped (skipped = baseline).
- I-0 rc 0; `roadmap-governance-guard` PASS; `--self-test` 55/55; `git diff --check` rc 0; ruff — новых нет; shellcheck rc 0;
  `compose config` pilot / phase1 / pilot+local-stand — OK.
- Ревью: 4 круга — APPROVE WITH COMMENTS, APPROVE WITH COMMENTS, REQUEST CHANGES (🔴 — моя регрессия круга 2, СТОП, решение владельца
  «а», исправлено), APPROVE WITH COMMENTS.
- Не запускалось: CI (на `/finish`, включая первый запуск job `pilot-compose-smoke`); lock-режим verify на реальном релизе; frontend/UI-smoke
  (не затронуты).

### Долг (к `/finish`)
- **Открытый риск (п.2 владельцу):** `JWT_AUDIENCE` не проверяется `validate-pilot-env.py` / `validate_stand_env`; перед обновлением стенда
  проверить ключ в `.env.stand`, иначе три backend-сервиса не стартуют.
- Lock-режим `verify-pilot-run.sh` полностью не доказан (нужен релиз в GHCR); старые релизы не проходят verify (принято владельцем).
- `generate_release_lock.py` не пишет `release.schema_head` (RF-06).
- `create-app-role.py`: пароль существующей роли не меняется; при `log_statement=ddl/all` пароль в логе PG (вариант — SCRAM-verifier);
  `POSTGRES_APP_USER` ≠ `retail_media_app` падает на grant.
- Compose healthcheck — `/health/live`; строгий readiness только через `/health/ready`.
- Снять `RMP_VERSION`/`RMP_GIT_SHA` из compose, чтобы рантайм брал identity образа (контракт `.env.pilot`).
- Общий хелпер dev-окружений (`main.py`, alembic, `_is_dev`); `strip()` audience в jwt; `except SystemExit` в import smoke.
- Устаревший docstring `local_stand.py::provision_app_role`; ручное создание роли там остаётся (идемпотентно).
- Старые ошибки ruff: `main.py` E402 ×5, `test_local_stand.py` F841.

### Итог (заполняет /finish)
- Статус: finished (PR ждёт merge владельцем). Коммит и PR: `gh pr list --head fix/RF-05`; CI — в отчёте `/finish` (в коммит не входит).
- Доказано: pilot-compose под `ENVIRONMENT=pilot` поднимается с нуля без ручных шагов (P0-1…P0-4 + FU5), verify честный (P0-5):
  локальный прогон rc 0 на образах ветки, тот же скрипт на compose develop — rc 1; валидатор/compose/readiness/alembic/phase1 —
  тесты, падавшие на коде до исправления; `create-app-role.py` не пишет пароль в вывод и лог PG (живой PG 16.4, контроль без защиты — утечка).
- RM-PILOT-002A остаётся `in_progress`: `done` — после merge и зелёного CI develop (включая `pilot-compose-smoke`), решением владельца.
- Отклонённые 🟠: `JWT_AUDIENCE` в `validate-pilot-env.py`/`local_stand.py` (вне списка файлов, открытый риск — владельцу);
  старые релизы в verify (принято владельцем). Долг — «Долг (к `/finish`)» выше.
- Новые инварианты: I-2.
- Следующий шаг: merge PR владельцем → решение по `JWT_AUDIENCE` на стенде и RM-STAB-004/RF-01-остаток → `/start RF-<N>`.

## RF-04 — Оркестратор: сбои не маскируются

- Статус: finished (PR ждёт merge владельцем)
- Ветка: fix/RF-04 · Основа: develop @ af6810c (merge PR #12)
- Сделано до правок (решения владельца 2026-09-29): RM-PILOT-002A → `done` в `roadmap.yaml` с `evidence_refs` (ci_run 36571330932,
  command — job `pilot-compose-smoke` и `pytest tests/test_rf05_pilot_boot.py tests/test_production_config_gate.py` → 59 passed локально);
  RM-STAB-019 (S, in_progress) заведена; генерация. Карточка RF-04 → `in_progress`, RF-05 → `merged`.
- Факты для плана (код `af6810c`):
  - P0-4: `generate_manifests_for_campaign` ловит любое исключение устройства (`delivery.py:760`), пишет failed и продолжает;
    `get_security_config()` грузится внутри цикла по устройствам (`:703`) → при сломанном конфиге каждое устройство failed,
    handler возвращает `True` → ack.
  - P1-6.a: в `_process_one` `session_setup` вне `try`, rollback в `except` может бросить → исключение уходит в `run()` → цикл
    завершается (`except Exception: logger.exception(...)`), `consumer_running` в health не сбрасывается; readiness считается только
    по `db_ok`/`nats_connected`.
  - P1-8: `_campaign_completion_maintenance` (`apps/orchestrator-worker/main.py`) — сессия без `set_worker_admin_context`;
    `tests/behavioral/test_campaign_completion.py` ходит через `BEHAVIORAL_DB_URL` (владелец БД).
  - Compose healthcheck воркера — `/health/live` (pilot/phase1); 503 на `/health/ready` Docker **не увидит** (уточнение к формулировке
    варианта в вопросе владельцу; compose вне скоупа — долг RF-05 «healthcheck → /health/ready»).
- Baseline (2026-09-29, `.venv` Python 3.12.3, `set -o pipefail`, код = `af6810c`):
  - I-0 → rc 0 «All import boundaries clean.»
  - I-1 / behavioral (шаги job дословно, postgres:16-alpine, `retail_media_app` NOBYPASSRLS) → rc 0: 484 passed, 12 skipped; RM-STAB-018 7/7.
  - python-tests (`python -m pytest tests/ -v`, env job) → rc 0: 1941 passed, 541 skipped.
  - I-2: push-run develop 36571330932 — job «Pilot Compose Smoke — RF-05» success; `tests/test_rf05_pilot_boot.py` входит в python-tests (rc 0).
  - `roadmap-governance-guard` → PASS; `--self-test` → 55/55 (до и после правок roadmap).
- План:
  - Задача: см. карточку. Домены (ADR-014): `packages/domain` (delivery), `packages/services` (consumer, health_state),
    `apps/orchestrator-worker`. Границы импорта не меняются.
  - Protected Boundaries: нет. Формат манифеста, lifecycle-переходы, compose/CI не трогаются.
  - Доказательство (уточнено после ревью круга 1): `tests/test_rm_stab_019_orchestrator_failures.py` (unit: сбой session_setup/rollback →
    цикл жив; остановка цикла → readiness 503) и `tests/behavioral/test_rm_stab_019_orchestrator_rls.py` (под `retail_media_app`:
    конфиг-сбой / ошибка БД → nak без failed; ошибка данных → failed + ack; проход воркера завершения).

### Сделано
- Тесты сначала (на коде `af6810c`):
  - `tests/test_rm_stab_019_orchestrator_failures.py` (unit, T11) — 5 из 9 падали: сбой `session_setup` / rollback уходил из
    `_process_one` исключением; цикл `run()` останавливался на первом таком сообщении; `consumer_ready` без работающего цикла → `ok`;
    вылет цикла не сбрасывал `consumer_running`. 4 контрольных (commit-сбой → не ack, readiness без consumer, shutting_down) проходили.
  - `tests/behavioral/test_rm_stab_019_orchestrator_rls.py` (PostgreSQL, путь consumer под `retail_media_app` + `set_worker_admin_context`)
    — 3 из 7 падали: сломанный конфиг безопасности → ack (ожидался nak без failed); ошибка БД при записи манифеста → ack;
    проход воркера завершения (функции не было). Контрольные: роль NOBYPASSRLS; ошибка данных устройства → failed + ack;
    рабочий конфиг → generated + ack; без admin-контекста RLS прячет кампанию (механизм P1-8) — проходили.
- `packages/domain/delivery.py`: `get_security_config()` грузится один раз до цикла по устройствам (вне обработки ошибок устройства);
  `SQLAlchemyError` внутри цикла пробрасывается (транзакция непригодна) → handler `False` → rollback + nak; прочие ошибки устройства —
  как раньше (failed + `delivery.manifest.failed`). Формат манифеста и подпись не менялись.
- `packages/services/campaign_event_handler.py::NatsJetStreamCampaignConsumer`: `_process_one` — весь путь сессии (setup, handler,
  commit, rollback, close) внутри `try`; сбой → `errors`+1, `bump_consumer_errors`, nak; ack только после успешного commit.
  `run()` в `finally` сбрасывает `consumer_running` в health.
- `packages/services/health_state.py::to_dict`: `consumer_ready and not consumer_running` → `degraded` (`/health/ready` 503);
  `shutting_down` имеет приоритет.
- `apps/orchestrator-worker/main.py`: `_campaign_completion_pass(session_factory)` — одна транзакция с `set_worker_admin_context`;
  `_campaign_completion_maintenance` вызывает её (лог — после commit).
- `roadmap.yaml`: acceptance RM-STAB-019 → behavioral-файл для P0-4 и P1-8, unit — для P1-6.a; генерация.
- После исправлений: unit 9/9 + `test_phase4_2b_consumer.py` → 47 passed; behavioral файл 7/7; ruff — новых нет (delivery 10→10,
  main 3→3); I-0 rc 0; guard PASS; self-test 55/55; `git diff --check` rc 0.

- Полный python-tests после правок → 2 failed: `tests/test_phase4_production_readiness.py::TestHealthEndpoint::
  test_ready_endpoint_includes_all_components` и `test_ready_returns_200_when_status_ok` — «готовое» состояние строилось с
  `consumer_ready=True` без `consumer_running` (второй — через общий singleton после первого). Решение владельца 2026-09-30:
  адаптировать фикстуру — `set_consumer_running(True)` в обоих, ассерты не менялись.
- Самопроверка (2026-09-30, `.venv` Python 3.12.3, `set -o pipefail`):
  - behavioral (шаги job дословно, `retail_media_app` NOBYPASSRLS) → rc 0: 491 passed, 12 skipped (baseline 484 + 7 новых); RM-STAB-018 7/7.
  - python-tests (env job) → rc 0: 1950 passed, 548 skipped (541 baseline + 7 новых behavioral без env).
  - I-2: образы из ветки (флаги `build-images.sh`), `verify-pilot-run.sh --images-from-env rf04-local <sha>` → rc 0
    «VERIFY-PILOT-RUN PASSED». Дополнительно копией verify из scratchpad (репозиторий не менялся): `/health/ready` оркестратора в
    pilot-стеке с реальным JetStream consumer → 200 `ok`, consumer ready + running.
  - I-0 rc 0; guard PASS; self-test 55/55; ruff — новых нет; `git diff --check` rc 0.

### Решения
- P0-4 доказан на PostgreSQL, а не unit-моками: генерация манифеста — десятки запросов, мок сессии ничего бы не доказал.
  Граница: ошибка БД в тесте — подменённая `OperationalError` (доказывает ветку `except SQLAlchemyError: raise` на живой PG-транзакции),
  а не реально оборванное соединение.
- Системные ошибки = сбой загрузки конфига безопасности и `SQLAlchemyError`; остальное — ошибка данных устройства (контракт прежний).
- Подсчёт: сбой сессии/handler'а теперь увеличивает и `nakd`, и `errors` (раньше только `nakd`) — видно в health.
- `StubCampaignEventConsumer` (dev/test) не менялся — P1-6.a про реальный consumer; долг.
- Readiness: 503 виден только на `/health/ready`; compose healthcheck — `/health/live` (долг RF-05), compose вне скоупа.

### Ревью
| Круг | Замечание | Уровень | Решение | Риск исправления | Доказательство |
|---|---|---|---|---|---|
| 1 | P0-4 закрыт частично: сбой подписи / ошибки кода внутри цикла устройства → failed + ack | 🟠 | отклонено с обоснованием: деление «системная / ошибка данных» по типу исключения — решение владельца; вариант «все устройства упали → nak» без DLQ даёт бесконечный nak для детерминированной ошибки данных кампании с одним устройством; граница записана в notes RM-STAB-019; пересмотр — на этапе DLQ (P1-6.b) | — | `delivery.py` except-ветки; notes RM-STAB-019 |
| 1 | Все устройства failed → handler считает `manifest_skipped`, не `failed` | 🟠 | долг: правка требует адаптации существующих тестов `test_phase4_2b_consumer.py` (результат генерации — `MagicMock`, `failure_count > 0` → TypeError) — вне карточки | — | `MagicMock().failure_count > 0` → TypeError (проверено) |
| 1 | `checks.consumer` = `ready` при умершем цикле | 🟡 | долг: правка ломает существующий `test_phase4_production_readiness.py::test_publisher_and_consumer_ready` (вне карточки); причина видна в `components.consumer.running` | — | прогон: 1 failed при правке, откат |
| 1 | `consumer_running` выставляется в `main.py` до `create_task`; ранний `return` в `run()` не сбрасывает | 🟡 | исправлено: `run()` сам ставит `True` при старте цикла и `False` при `_sub is None` и в `finally`; ссылка на task — долг | низкий: флаг тот же, источник — сам цикл | +2 unit-теста |
| 1 | 503 на readiness никто не использует (healthcheck `/health/live`) | 🟡 | долг RF-05 (compose вне скоупа); отмечено в notes RM-STAB-019 | — | — |
| 1 | Бесконечный nak при детерминированной ошибке БД | 🟡 | зафиксировано в «Риск регрессии» RM-STAB-019 (до DLQ, P1-6.b); регрессии нет — раньше PendingRollbackError давал тот же nak | — | notes |
| 1 | Журнал: неверное имя behavioral-файла и распределение проверок в «План» | 🟡 | исправлено | нет | — |
| 1 | Тест ошибки БД — мок, не реальный обрыв | 🟡 | исправлено: оговорка в «Решения» | нет | — |
- Самопроверка после круга 1: behavioral rc 0 — 491 passed, 12 skipped; python-tests rc 0 — 1952 passed, 548 skipped; I-0 rc 0; guard PASS;
  self-test 55/55; ruff изменённых файлов — новых нет; `git diff --check` rc 0.
| 2 | Системный сбой → nak каждые 5 с без ограничения (`max_deliver=-1`) | 🟠 | отклонено с обоснованием: бесконечные повторы при nak приняты владельцем при выборе варианта P0-4 (вопрос прямо это оговаривал); backoff/лимит — дизайн DLQ (P1-6.b, отдельный этап); риск в notes RM-STAB-019. **Для владельца:** P1-6.b — условие выката RF-04 на pilot-хост | — | `jetstream_provisioning.py:45`, `nak_delay=5.0` |
| 2 | Умерший цикл не перезапускается, `/health/live` 200 | 🟠 | долг: владелец выбрал «выжить + readiness», не fail-fast; супервизор / liveness по consumer — отдельная задача; compose вне скоупа | — | notes RM-STAB-019 |
| 2 | `StubCampaignEventConsumer._handle_one` — старый шаблон | 🟡 | долг (dev/test, вне P1-6.a) | — | — |
| 2 | Системный сбой увеличивает `consumer_manifest_failed` | 🟡 | долг (отдельный счётчик — вместе с п.2 круга 1) | — | — |
| 2 | Тест ошибки БД искусственный; старый код при реальном обрыве тоже давал nak (PendingRollbackError) | 🟡 | принято: оговорка уже в «Решения»; «падает до исправления» для ветки БД — только для подменённой ошибки | нет | — |
| 2 | Сбой драйвера, не обёрнутый SQLAlchemy (`OSError`, `TimeoutError`), → failed + ack | 🟡 | долг | — | — |
- Ревьюер круга 2 локально получил 7 failed в `pytest tests/` без env job — те же 7 без новых файлов, порядкозависимые (известны с RF-CI);
  в env job python-tests — rc 0 (см. гейт).

### Гейт
2026-09-30, `.venv` Python 3.12.3, `set -o pipefail`; код не менялся после самопроверки круга 1 (правки круга 2 — только журнал):
- behavioral (шаги job дословно, `retail_media_app` NOBYPASSRLS) → rc 0: 491 passed, 12 skipped; RM-STAB-019 7/7; I-1 RM-STAB-018 7/7.
- python-tests (env job) → rc 0: 1952 passed, 548 skipped (541 baseline + 7 новых behavioral без env); включает `tests/test_rf05_pilot_boot.py`.
- I-2: образы пересобраны из ветки после круга 1 → `verify-pilot-run.sh --images-from-env rf04-local <sha>` rc 0 «VERIFY-PILOT-RUN PASSED»;
  копия verify с проверкой `/health/ready` оркестратора → 200 `ok`, consumer running=true; контейнеров `rmp-verify-*` после прогона нет.
- I-0 rc 0; `roadmap-governance-guard` PASS; `--self-test` 55/55; ruff — новых нет; `git diff --check` rc 0.
- Ревью: 2 круга — APPROVE WITH COMMENTS, APPROVE WITH COMMENTS.
- Не запускалось: CI (на `/finish`); frontend/UI-smoke (не затронуты); `docker compose config` (compose не менялся).

### Долг (к `/finish`)
- P0-4 частично: сбой подписи / ошибки кода внутри генерации по устройству → failed + ack; сбой драйвера вне SQLAlchemy → failed + ack.
- Бесконечный nak каждые 5 с при системном сбое до DLQ (P1-6.b) — **условие выката на pilot-хост, решение владельца**.
- Умерший цикл consumer не перезапускается; compose healthcheck на `/health/live` (долг RF-05); ссылка на task `consumer.run()` не хранится.
- Наблюдаемость: все устройства failed → `manifest_skipped`; системный сбой → `manifest_failed`; `checks.consumer` = `ready` при умершем цикле
  (правки требуют адаптации существующих тестов вне карточки).
- `StubCampaignEventConsumer` не переведён на новую структуру.
- `requirements-traceability.yaml`: ссылка RM-STAB-019 (кандидат REQ-ORCH-002) — решением владельца.
- Старые ошибки ruff в изменённых файлах (delivery 10, main 3).

### Итог (заполняет /finish)
- Статус: finished (PR ждёт merge владельцем). Коммит и PR: `gh pr list --head fix/RF-04`; CI — в отчёте `/finish` (в коммит не входит).
- Доказано: системный сбой генерации (конфиг, БД) → nak без failed-строк, ошибка данных устройства → failed + ack — на PostgreSQL путём consumer
  под `retail_media_app`; сбой сессии не останавливает цикл, остановка цикла видна в `/health/ready`; воркер завершения работает под RLS.
  Тесты падали на коде до исправления (unit 5/9, behavioral 3/7).
- RM-STAB-019 остаётся `in_progress`: `done` — после merge и зелёного CI develop, решением владельца. RM-PILOT-002A — `done`.
- Отклонённые 🟠: частичный P0-4 (деление по типу исключения — решение владельца; «все устройства упали → nak» без DLQ = бесконечный nak);
  бесконечный nak до DLQ (принят владельцем при выборе варианта). Долг — «Долг (к `/finish`)» выше.
- Новые инварианты: I-3.
- Следующий шаг: merge PR владельцем → решение: P1-6.b (DLQ/backoff) как условие выката RF-04 на pilot-хост; ссылка RM-STAB-019 в traceability →
  `/start RF-<N>`.
