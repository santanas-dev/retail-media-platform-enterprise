# Журнал этапов исправлений (RF)

> **Не канон.** Операционная память агента между сессиями: что сделано, на чём
> остановились, что нельзя сломать. Канонический статус — `PROJECT_STATE.md`.
> Команды `/start` и `/finish` читают и дополняют этот файл. Записи этапов не
> переписываются задним числом — только дополняются.

## Текущее состояние

| | |
|---|---|
| Активный этап | — |
| Последний завершённый | RF-CI — merged (PR #10, `6bc9ac0`); RF-00 — finished, PR #9 ждёт merge |
| Следующий шаг | merge PR RF-00 владельцем → решение по черновикам RF-01…RF-09 → `/start RF-<N>` |
| Базовая линия | `origin/develop @ 6bc9ac0` (2026-09-28, merge RF-CI; push-run `develop` 36407616564 → success; то же дерево — push-run `fix/RF-CI` 36404147483, 41/41). Снимок аудита RF-00 — `b166419`; ветка `fix/RF-00` получила `6bc9ac0` merge-коммитом `3892552` |
| Источник находок | `docs/audit/2026-09-27-claude-code-review-main-8ad0228.md` (снято на `main @ 8ad0228`; develop на 64 коммита впереди) |

## Инварианты (не ломать)

Поведения, доказанные завершёнными этапами. Каждый `/start` и `/finish` прогоняет
все команды отсюда. Добавляются только в `/finish`, с командой проверки.

| # | Инвариант | Команда проверки | Добавлен этапом |
|---|---|---|---|
| I-0 | Границы импорта (ADR-014) | `python scripts/ci/check-import-boundaries.py` | исходное правило проекта |

## Решения владельца, влияющие на этапы

| Дата | Решение |
|---|---|
| 2026-09-27 | Этапы запускаются `/start`, закрываются `/finish`; ревью `code-reviewer` автоматически, до 3 кругов |
| 2026-09-27 | Git: ветка `fix/<id>` от `develop` → PR в `develop`; merge делает только владелец |
| 2026-09-27 | `/start` одобряет только Protected Boundaries, перечисленные в карточке этапа |
| 2026-09-27 | Первый этап — пересверка находок на develop (RF-00); дальнейшие этапы — пакеты задач `roadmap.yaml` |
| 2026-09-28 | Запись RF-CI (карточка, журнал, checkpoint) — в PR #9: предложено агентом в отчёте RF-CI, владелец продолжил `/finish`; синхронизация `fix/RF-00` с develop — merge-коммитом (решение владельца) |
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
