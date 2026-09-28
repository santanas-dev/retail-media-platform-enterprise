# Журнал этапов исправлений (RF)

> **Не канон.** Операционная память агента между сессиями: что сделано, на чём
> остановились, что нельзя сломать. Канонический статус — `PROJECT_STATE.md`.
> Команды `/start` и `/finish` читают и дополняют этот файл. Записи этапов не
> переписываются задним числом — только дополняются.

## Текущее состояние

| | |
|---|---|
| Активный этап | — |
| Последний завершённый | RF-01 — finished, PR ждёт merge (`gh pr list --head fix/RF-01`); RF-00 — merged (PR #9, `7762434`) |
| Следующий шаг | merge PR RF-01 владельцем → RM-STAB-018 `done` после CI develop (решение владельца) → выбор следующего черновика → `/start RF-<N>` |
| Базовая линия | `origin/develop @ 6bc9ac0` (2026-09-28, merge RF-CI; push-run `develop` 36407616564 → success; то же дерево — push-run `fix/RF-CI` 36404147483, 41/41). Снимок аудита RF-00 — `b166419`; ветка `fix/RF-00` получила `6bc9ac0` merge-коммитом `3892552` |
| Источник находок | `docs/audit/2026-09-27-claude-code-review-main-8ad0228.md` (снято на `main @ 8ad0228`; develop на 64 коммита впереди) |

## Инварианты (не ломать)

Поведения, доказанные завершёнными этапами. Каждый `/start` и `/finish` прогоняет
все команды отсюда. Добавляются только в `/finish`, с командой проверки.

| # | Инвариант | Команда проверки | Добавлен этапом |
|---|---|---|---|
| I-0 | Границы импорта (ADR-014) | `python scripts/ci/check-import-boundaries.py` | исходное правило проекта |
| I-1 | Refresh-токены: повтор после окна отзывает семью (+audit), в окне — нет; одна ветка при гонке; семья сериализована; отзыв переживает 401 (RM-STAB-018) | шаги job `behavioral-postgres-tests` (PostgreSQL, `retail_media_app` NOBYPASSRLS), затем `python3 -m pytest tests/behavioral/test_rm_stab_018_refresh_replay.py -v` → 7 passed | RF-01 |

## Решения владельца, влияющие на этапы

| Дата | Решение |
|---|---|
| 2026-09-27 | Этапы запускаются `/start`, закрываются `/finish`; ревью `code-reviewer` автоматически, до 3 кругов |
| 2026-09-27 | Git: ветка `fix/<id>` от `develop` → PR в `develop`; merge делает только владелец |
| 2026-09-27 | `/start` одобряет только Protected Boundaries, перечисленные в карточке этапа |
| 2026-09-27 | Первый этап — пересверка находок на develop (RF-00); дальнейшие этапы — пакеты задач `roadmap.yaml` |
| 2026-09-28 | Запись RF-CI (карточка, журнал, checkpoint) — в PR #9: предложено агентом в отчёте RF-CI, владелец продолжил `/finish`; синхронизация `fix/RF-00` с develop — merge-коммитом (решение владельца) |
| 2026-09-28 | RF-01 = P0-7 + замена маскирующего теста `test_replay_calls_family_revoke` (одобрено); T7 и P0-6/P0-8 — в остаток черновика RF-01; задача RM-STAB-018 и OD-046 заводятся этапом; повтор ротированного refresh в окне 10 с — 401 без отзыва семьи, позже — отзыв семьи (вариант «a») |
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
