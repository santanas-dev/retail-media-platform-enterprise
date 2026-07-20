# Retail Media Platform Agent Contract

This repository is built with AI assistance. Follow this contract before any
code change. The goal is a stable retail media product, not a pile of generated
features.

## Current Priority

Stabilization comes before new functionality.

## Source Of Truth

Before any architecture, planning, or implementation work, read:

1. `docs/00-source-of-truth/README.md`
2. `docs/00-source-of-truth/TZ_Retail_Media_Platform_v2_5_Final_Hermes.extracted.md`
3. `docs/00-source-of-truth/rmp_rewrite_starting_decisions.md`
4. `docs/00-source-of-truth/rmp_enterprise_architecture_review.md`
5. `docs/architecture/adr/ADR-001..ADR-015` — architecture decision records (current)
6. `docs/architecture/erd/erd-v2-5.md` — current ERD
7. `docs/architecture/api/api-groups-v1.md` — current API contracts
8. `docs/architecture/README.md` — index + superseded doc list

**ADR-011 (transactional outbox) must be read before implementing any
event producer, outbox relay worker, or NATS publishing code.**  Every
domain event from an OLTP transaction requires the outbox pattern.

**ADR-012 (async I/O) must be read before implementing any external
I/O integration (LDAP, S3/MinIO, file uploads, external APIs, report
generation).**  No sync SDK calls in async handlers.  Use native async,
`run_in_threadpool`, background workers, or streaming as appropriate.

**ADR-013 (edge runtime safety) must be read before implementing
device-gateway, player, sidecar, PoP ingestion, manifest delivery,
kill-switch, or any device-facing runtime code.**

**ADR-014 (layering) must be read before creating new packages,
modules, or imports.**  If import direction is unclear, stop and
review the layer hierarchy — do not guess.

**ADR-015 (campaign domain) must be read before implementing any
campaign, creative, placement, scheduling, approval, or PoP reporting
code.**  This ADR locks the entity graph, status lifecycle, placement
model (surfaces, not devices), outbox integration, and behavioral
test requirements for the entire campaign domain.

**ADR-016 (delivery/manifest) must be read before implementing any
manifest generation, delivery pipeline, or device manifest endpoint
code.**  This ADR locks eligibility, target resolution, manifest
schemas, versioning, outbox events, and the phase split (4.2b→4.2e).

**ADR-017 (PoP/reporting) must be read before implementing any PoP
ingestion endpoint, PoP storage tables, reporting API, or analytics
code.**  This ADR locks PoP source (runtime only), ingestion validation
(quarantine, dedup, clock drift), storage (PostgreSQL, ClickHouse
deferred), billing-grade reporting rules, outbox integration, and
behavioral proof requirements for Phase 4.3b→4.3e.

The source-of-truth folder overrides older generated phase reports unless a
newer approved ADR explicitly changes a decision. The original `.docx` in that
folder is traceability-only; agents should use the markdown extraction.

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

## NAS / Mirror Truth

- **GitHub `origin/develop` is the sole git-source-of-truth.** NAS/ASUSTOR at
  `\\192.168.110.118\project\retail-media-platform-enterprise` is a mirror —
  it may be stale.
- **Agent must NOT claim "NAS synced" without mirror-check proof.** Writing
  "NAS synced" as a fact requires either: (a) a successful `mirror-check.sh`
  run from an environment with both GitHub and NAS access, or (b) operator/santa2
  confirmation recorded in PROJECT_STATE.
- **SSH-unavailable is NOT proof.** If GitHub is unreachable via SSH (host key
  failure, "Not allowed at this time"), the honest status is **cannot verify
  from here** — not "stale" and not "synced."
- **Mirror-check pending is valid.** After a Hermes push, the expected state is
  "mirror-check pending — operator/santa2 will verify." Do not block DONE on
  mirror sync — GitHub + CI green is sufficient for task completion. Mirror
  status is tracked separately in PROJECT_STATE Repository Checkpoint.
- **Mirror-check script:** `docs/runbook/mirror-check.sh` uses HTTPS (not SSH)
  by default. Accepts `--expected-origin-sha` / `EXPECTED_ORIGIN_DEVELOP_SHA`.
  Returns: `verified` | `stale` | `cannot-verify-from-here`. Exit 0 for verified
  and cannot-verify (neutral statuses). Exit 1 for stale (real divergence — NAS
  needs pull). Exit 3 for script errors (bad args, missing deps).

## Что значит готово

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

## Reporting

Final reports must be short but concrete:

- what changed;
- files changed;
- commands/checks run;
- what remains risky.

Never write "all tests pass" unless they were actually run.
