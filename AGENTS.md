# Retail Media Platform Agent Contract

This repository is built with AI assistance. Follow this contract before any
code change. The goal is a stable retail media product, not a pile of generated
features.

## Current Priority

Stabilization comes before new functionality.

## Sources of Truth (единый индекс)

Единственный авторитетный перечень. При конфликте — верхний уровень побеждает нижний.
Никакой файл вне этого индекса не является каноном без явного упоминания здесь.

### Tier 1 — Git & Code (непререкаемо)

- **GitHub `origin/develop`** — единственная git-истина. Все SHA, CI, и состояние кода
  верифицируются через `git ls-remote origin refs/heads/develop` и GitHub Actions.
- `git log`, `git status`, `gh run list` — первичные инструменты для Git/CI truth.

### Tier 2 — Продукт & Journeys (что строим)

| Файл | Назначение | Приоритет |
|------|-----------|-----------|
| `docs/product/user-journeys.md` | **Спецификация** journey: id, роли, путь, Given/When/Then | Авторитет по спецификации (id, формат, приёмка) |
| `docs/product/pre-pilot-journey-plan.md` | Порядок закрытия journeys по волнам 1–6 | Побеждает ad-hoc приоритизацию |
| `docs/product/feature-registry.yaml` | **Статус** journey (reachable/blocked), smoke, frontend | Авторитет по статусу. При конфликте статуса registry главнее roadmap |
| `docs/product/roadmap-s020-2026-07-10.xlsx` | Бизнес-карта (4 колонки): Бэкенд/UI/Юзер-стори/Итог | Производная от registry + smoke; не переопределяет их |

### Done Gate (встроен в Sources of Truth)

Бизнес-функция считается **готовой** только при выполнении всех условий ниже.
Бэкенд + API proof недостаточно — пользователь обязан достичь функции через
реальный UI кликами.

1. **Journey обязателен.** Бизнес-функцию нельзя пометить «Готово», если для
   неё нет journey в `docs/product/user-journeys.md`. Journey содержит: id
   (в формате `<domain>.<action>`), роль, стартовую страницу, пошаговые
   клики до целевого экрана, ожидаемый результат, стабильные
   `data-testid`-селекторы.

2. **UI-smoke обязателен.** Бизнес-функцию нельзя пометить «Готово», если
   для её journey id нет зелёного UI-smoke-теста. Имя теста:
   `test_uismoke__<domain>__<action>` (точки → двойное подчёркивание).

3. **Только реальные клики.** `page.goto()` в UI-smoke разрешён **только**
   на `/login` или на публичную entry-страницу, указанную в journey как
   стартовая. Весь дальнейший путь — **реальные клики** по UI
   (кнопки, ссылки, табы). Никаких `page.goto("/campaigns/new")`,
   `localStorage.setItem(...)`, прямых API-вызовов.

4. **Feature-registry синхронизирован.** Каждая новая бизнес-фича должна
   обновлять **три** источника синхронно по одному journey id:
   - `docs/product/user-journeys.md` — путь,
   - `docs/product/feature-registry.yaml` — запись в реестре,
   - `tests/ui-smoke/test_uismoke__<domain>__<action>.py` — зелёный тест.

5. **Частичная готовность — честный статус.** Если бэкенд готов, но
   journey/smoke отсутствует, статус: **«бэкенд готов, UI нет»** или
   **«частично»**. Слово «Готово» без выполненного UI-smoke — запрещено.

6. **UI-smoke не блокирует CI.** Тесты в `tests/ui-smoke/` запускаются
   только при `UI_SMOKE_RUN=1` и не собираются обычным pytest. Они —
   инструмент аудита, а не CI-gate.

7. **Roadmap-синхронизация обязательна.** Если задача довела journey до
   зелёного UI-smoke, та же задача обязана поднять в бизнес-вкладке roadmap
   (`docs/product/roadmap-s020-2026-07-10.xlsx`, лист «Бизнес-функции
   Roadmap») колонки «UI» + «Юзер-стори» и пересчитать колонку «Итог».
   Итог=«✅ Готово/Юзабельно» только при Бэкенд ✅ + UI ✅ + Юзер-стори ✅.
   Без зелёного UI-smoke по journey id — запрещён. Частичные фичи
   маркируются «🟠 Частично» с указанием, какая часть не reachable.

8. **Прогон оператором (human walkthrough).** UI journey / wave нельзя закрыть как
   «Готово/Юзабельно», пока человек-оператор или аудитор не прошёл happy-path
   в реальном DEV-портале без пошаговой инструкции и не подтвердил, что путь
   понятен: основное действие видно без поиска, на каждом шаге ясен следующий
   шаг, нет спрятанных обязательных многофазных переходов. UI-smoke этого не
   проверяет — он доказывает достижимость для робота. Результат фиксируется
   одной строкой в `PROJECT_STATE.md`: `operator walkthrough: OK` или
   `operator walkthrough: замечания <перечень>`.

9. **Happy-path глазами пользователя.** Каждый новый или изменяемый UI journey
   в `docs/product/user-journeys.md` и каждый промпт на UI-фичу обязан содержать
   блок/строку `Happy-path: N шагов`, где каждый шаг = одно видимое действие
   пользователя + видимый next-step. Проектируем от мысленной модели
   пользователя, а не от формы API. Если happy-path выходит за разумный бюджет
   шагов или содержит скрытую обязательную кнопку/переход, это UX-дефект и он
   фиксируется до закрытия journey.

### Tier 3 — Задачи & Статус (что делаем сейчас)

- **`PROJECT_STATE.md`** — канонический статус всех workstreams: активные, resolved,
  pending, deferred. Repository Checkpoint (Payload SHA / State SHA). Единственный
  источник для «что сейчас в работе» и «какой SHA актуален».
- **`AGENTS.md`** (этот файл) — правила работы агентов, границы, definitions of done.

### Tier 4 — Архитектура (как устроено)

- **`docs/architecture/adr/ADR-001..ADR-019`** — architecture decision records.
  ADR переопределяет design gates, correction plans, и phase reports.
- `docs/architecture/erd/erd-v2-5.md` — текущая ERD.
- `docs/architecture/api/api-groups-v1.md` — текущие API-контракты.
- `docs/architecture/README.md` — индекс + список superseded документов.
- `docs/00-source-of-truth/` — извлечение ТЗ (read-only, traceability). Оригинал
  `.docx` — только для истории; агенты используют `.extracted.md`.

### Tier 5 — Производные (НЕ авторские источники)

- **NAS mirror** (`\\192.168.110.118\project\…`, локальный mount `/mnt/asustor-project/`) — зеркало GitHub, может быть stale.
  - **GitHub `origin/develop` — единственная git-истина.** NAS — зеркало, не авторский источник.
  - **Hermes owns mirror sync freshness.** Cron job `c0687f5ced4d` (script `nas-mirror-sync.sh`) синхронизирует NAS каждые 3 минуты через CIFS mount.
  - **Агенты НЕ пишут «NAS synced/verified» без проверки:** NAS HEAD == origin/develop.
    Проверять: `git -C /mnt/asustor-project/retail-media-platform-enterprise rev-parse HEAD` против `git ls-remote origin refs/heads/develop`.
  - **santa2 relay DEPRECATED** — заменён на Hermes-owned sync (NAS-SYNC-OWNER-001).
  - **Mirror-check pending — допустимо.** После пуша ожидаемое состояние:
    «mirror pending — Hermes cron syncs every 3 min». Зеркало не блокирует DONE:
    GitHub + CI green достаточно. Статус зеркала отслеживается в PROJECT_STATE
    Repository Checkpoint.
  - **Mount unavailable — честный статус.** Если `/mnt/asustor-project/` не примонтирован,
    статус: `pending | mount unavailable`. Не `verified`. Оператор отвечает за mount; Hermes за sync.
- **`for-agents/`** на NAS — **DEPRECATED staging.** Все файлы оттуда перенесены
  в `docs/product/` репозитория. `for-agents/` не является авторитетным источником;
  агенты читают только git-репо.

### ADR Precedence

**ADRs override all other architecture documents.** If a design-gate doc,
correction plan, or migration checklist conflicts with an ADR, the ADR wins.
When you encounter a conflict:

1. Stop — do not implement from the old document.
2. Check `docs/architecture/README.md` for the superseded doc list.
3. If uncertain, ask the user or review the relevant ADR.

Superseded documents in `docs/architecture/` carry a banner:

```
<!-- SUPERSEDED: This document is retained for historical context only. ... -->
```

**Do not implement from a file marked SUPERSEDED** when it conflicts with an ADR.
Source-inspection tests are not behavioral proof — static checks on old code
do not validate runtime RBAC/RLS behavior.

**ADR quick-reference (обязательное чтение по домену):**

- ADR-011 — transactional outbox (events, NATS, relay worker)
- ADR-012 — async I/O (no sync SDK in handlers)
- ADR-013 — edge runtime safety (device-gateway, player, PoP, manifest, kill-switch)
- ADR-014 — layering (import direction: apps → api → auth → domain)
- ADR-015 — campaign domain (entity graph, status lifecycle, placements)
- ADR-016 — delivery/manifest (eligibility, target resolution, schemas)
- ADR-017 — PoP/reporting (ingestion, validation, billing-grade rules)
- ADR-019 — Channel Orchestrator deferred (PRAGMATISM, до второго канала)

Fix critical platform risks first:

- PostgreSQL readiness must be real, not optimistic.
- Admin audit events must use valid actor UUIDs.
- Alembic configuration must use valid URLs and load model metadata.
- Production secrets must be hardened.
- Portal/backend RBAC must not drift.
- Outbox relay + orchestration runtime wiring is pending (S-012).

Do not start Android TV, ESL, LED, mobile, or broad UI redesign work until the
stabilization backlog is green or the user explicitly overrides this.

## Required Workflow

For every task:

1. Restate the exact task and scope.
2. Inspect existing code before proposing changes.
3. Name the domain boundary being touched.
4. Make the smallest coherent change.
5. Add or update targeted tests for the changed behavior.
6. Run the narrowest relevant tests first, then broader checks if risk warrants it.
7. Report changed files, verification results, and remaining risks honestly.

For new features, write a mini-design first and wait for explicit approval.
For bug fixes, do root-cause analysis first and include the failing condition in
the test or verification.

## Required Hermes Skills

Load these skills for this project work:

- `retail-media-platform`
- `critical-assessment`
- `systematic-debugging` for bugs, regressions, failing tests, runtime issues
- `project-audit` for audits and stabilization
- `retail-media-platform-backend` for backend changes
- `retail-media-platform-portal` and `portal-qa-testing` for portal changes
- `backend-api-hardening` for auth, RBAC, RLS, safe projection, audit, or API work

Do not use offensive/security-hunt skills for normal product development unless
the user explicitly asks for a security test or pentest task.

## Hermes Memory Rules

Use Hermes memory only for durable project facts:

- architecture decisions and approved product constraints;
- stable commands, ports, paths, and operational pitfalls;
- current stabilization priorities and verified baseline facts.

Never store API keys, tokens, passwords, cookies, raw customer data, temporary
logs, or unverified test counts in `MEMORY.md` or `USER.md`. Credentials belong
in protected environment files or secret storage. If a memory fact becomes
wrong, replace it instead of adding a contradictory entry.

## Protected Boundaries

Do not change these without explicit approval:

- `.env`, `.env.example`, production secrets, local credentials
- Docker, deployment, backup, and rollback scripts
- destructive migrations, `DROP`, `TRUNCATE`, broad `DELETE`
- campaign submit/approval/publication flows
- generated manifest compatibility
- device authentication and KSO runtime contracts
- large portal rewrites or broad CSS redesign

If a fix seems to require touching a protected boundary, stop and explain why.

## Architecture Rules

- Keep core channel-agnostic. KSO is the first channel, not the architecture.
- Routers validate and authorize; services own business logic.
- Permissions use backend permission codes, not role names.
- RLS/scope checks must use the authenticated user, not an unused `_` dependency.
- Device-facing APIs must not expose internal IDs, storage keys, paths, tokens, or secrets.
- Portal pages must use backend data or clearly marked safe demo data.
- Portal route guards must match backend permissions.
- Prefer existing domain modules over new parallel models.
- **No sync I/O in async handlers.**  Use native async libraries,
  `run_in_threadpool`, background workers, or streaming.  See ADR-012.
- **Layer discipline.**  Imports flow downward: apps → api → auth → domain.
  Domain never imports api or fastapi.  No cross-service imports between
  apps/.  No shared package may import from apps/.  See ADR-014.

## Editing Rules

- Prefer targeted patches over full file rewrites, especially for large files.
- Do not rewrite `apps/portal-web/main.py` wholesale.
- Do not create duplicate helpers if an equivalent local helper exists.
- Keep comments rare and useful.
- Preserve unrelated user changes.
- Never claim a baseline is green without running or inspecting it.

## Verification Rules

Minimum checks by area:

- Backend config/DB: import/config test, readiness test, affected unit tests.
- Auth/RBAC/audit: negative permission test and audit integrity check.
- Alembic: migration URL sanity and metadata/model import check.
- Portal: template/source inspection plus route/RBAC smoke where possible.
- Device/KSO: contract tests and no-secrets/no-path projection checks.

If dependencies or infrastructure are unavailable, say exactly what was not run
and provide the closest static or targeted verification.

## Reporting

Final reports must be short but concrete:

- what changed;
- files changed;
- commands/checks run;
- what remains risky.

Never write "all tests pass" unless they were actually run.
