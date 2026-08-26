# Полный task breakdown после утверждения roadmap governance

> ## ⚠️ НЕ КАНОН — проект задач, реализация запрещена до согласования
>
> | | |
> |---|---|
> | **Тип** | Архитектурный task breakdown |
> | **База** | `develop @ 2b935bb`; live stand baseline `stand-27dc397`, schema `036` |
> | **Дата** | 2026-08-26 |
> | **Автор** | Codex, архитектор/ревьюер |
> | **Основание** | RG-1…RG-5 утверждены владельцем в исправленной редакции |
> | **Статус** | Ожидает feasibility/reconciliation Claude и утверждения порядка владельцем |
> | **Всего proposed tasks** | 40 |
> | **Изменения продукта/канона/стенда** | Нет |
> | **Отменён** | — |

## 1. Обязательные правила исполнения

- До утверждения этого breakdown владельцем ни одна задача не начинается.
- Claude Code — единственный implementation agent; Codex проектирует и независимо проверяет.
- Финальный approver — владелец. `REJECT` Codex блокирует автоматическое повышение статуса,
  но владелец может явно переопределить решение.
- Один implementation task за раз. Следующий начинается после evidence, ревью Codex и
  синхронизации canonical status Claude.
- Merge, release, deploy, изменение protected boundary и стенда — отдельное поштучное разрешение.
- `stand-27dc397` — baseline локального стенда, но не pilot и не production.
- Полный CI UI-smoke на общем stateful stand запрещён; используется stand-safe runner и
  отдельно согласованные browser-targeted/full-journey проверки.
- Ручные правки generated `roadmap.md`/XLSX запрещены после cutover.

## 2. Этап G — единая система roadmap (5 задач)

| ID | Результат | Зависит от | Приёмка |
|---|---|---|---|
| **RM-GOV-001** | Schema/mini-design `roadmap.yaml`: RM-BIZ/RM-TECH/RM-GOV, зависимости, decisions, acceptance, evidence, maturity | — | schema валидируется; не дублирует registry, journeys, ADR и PROJECT_STATE; mini-design утверждён владельцем |
| **RM-GOV-002** | Reconciliation/migration manifest старых roadmap-данных | RM-GOV-001 | все 93 technical items, 13 section rows и 57 business rows имеют disposition: migrate/deduplicate/history/drop-with-reason; все 5 blocked features имеют структурные gap/unblock conditions; создан initial YAML без overclaim |
| **RM-GOV-003** | Односторонний generator `roadmap.yaml + registry + evidence → roadmap.md + XLSX + metrics` | RM-GOV-001…002 | детерминированный output; 2 XLSX sheets/ожидаемые колонки; 0 ручных derived status; повторная генерация даёт чистый diff |
| **RM-GOV-004** | Roadmap governance guard | RM-GOV-003 | ловит ручной drift generated files, schema/status/dependencies, формулы метрик, journey semantics, smoke semantics, maturity gates и единственность sequencing SSOT; tamper matrix красная |
| **RM-GOV-005** | Canonical cutover | RM-GOV-003…004 | `AGENTS.md` индексирует один sequencing SSOT; maintenance rules superseded; pre-pilot plan только history без Active Next; stale mutators quarantined; PROJECT_STATE фиксирует approved Next; CI green |

**Gate G:** Codex подтверждает генерацию и tamper matrix; владелец утверждает canonical cutover.

## 3. Этап S — стабилизация доказательств и границ (11 задач)

| ID | Результат | Зависит от | Приёмка |
|---|---|---|---|
| **RM-STAB-001** | Единый контракт `BEHAVIORAL_APP_DB_URL` | Gate G | обе формы DSN нормализуются одним helper; одинаково зелёный targeted behavioral run |
| **RM-STAB-002** | Strict RLS context по умолчанию behavioral suite | RM-STAB-001 | admin elevation только в setup; endpoint coverage allowlist; tamper снятием context красный; behavioral suite зелёный |
| **RM-STAB-003** | Mini-design/ADR internal personas и retailer scope | RM-STAB-002 | persona→role→permissions→scope; least privilege; `system_admin/security_admin` — единственный bypass; owner approval до кода |
| **RM-STAB-004** | Реализация approved retailer-scope/RBAC модели | RM-STAB-003 | migration/API/portal guards согласованы; operator/analyst positive+negative RLS behavioral proof; cross-retailer isolation |
| **RM-STAB-005** | Исправление C1 UI-smoke | RM-STAB-002 | нет direct API, deep goto, sleep/broad retry; audit event связан с текущим run; AST guard и tamper; first-attempt green |
| **RM-STAB-006** | 45/45 нормативных UI journey | Gate G, RM-STAB-003 | actor, permission, entry, Happy-path, selectors, negative expectation; 0 status/history внутри normative spec |
| **RM-STAB-007** | UI proof под intended roles, не только break-glass | RM-STAB-004, RM-STAB-006 | critical journeys имеют positive intended-role и negative missing-permission proof; registry синхронизирован только после green |
| **RM-STAB-008** | Единая политика UI-smoke/CI | RM-STAB-005…007 | ordinary pytest отделён; develop/release/status gate blocking; AGENTS, workflow и generated roadmap совпадают; release-gate tamper красный |
| **RM-STAB-009** | Воспроизводимые CI dependencies | RM-STAB-001 | CI ставит зафиксированные project requirements/lock; протестированная версия совпадает с поставляемой; dependency drift guard |
| **RM-STAB-010** | Решение Ed25519/HMAC и честный production gate | Gate G | ADR владельца; gate не объявляет production-ready по неподходящему алгоритму; device contract не меняется без отдельного approval |
| **RM-STAB-011** | W0 rebaseline | RM-STAB-001…010 | targeted → behavioral → UI subset → guards; live stand только read-only/stand-safe; новые counts/evidence generated; Codex ACCEPT |

**Gate S:** только после RM-STAB-011 разрешено возвращаться к UX. До Gate S текущие
`reachable` сохраняются как исторический registry status, но спорные proof помечаются debt,
а не молча переписываются.

## 4. Этап U — ранее утверждённый UX-порядок (7 задач)

| ID | Результат | Зависит от | Приёмка |
|---|---|---|---|
| **RM-UX-001 / A3** | Accessibility оставшихся форм | S | FormField/labels/ARIA/axe; targeted vitest; соответствующие journeys не регрессируют |
| **RM-UX-002 / A2** | Поиск/сортировка/усечение таблиц | U1 | серверная семантика для paginated data; нет client-only ложного поиска; UX/UI proof |
| **RM-UX-003 / A4** | Остаточная responsive-проверка | U2 | 390px без overflow/обрезки на согласованной route matrix |
| **RM-UX-004 / A6** | Визуальная/терминологическая согласованность | U3 | единые состояния, локализация, loading; без broad redesign |
| **RM-UX-005 / A1b** | Массовая adoption доказанных primitives | U4 | маленькие slices; каждый отдельно tested/reviewed; `main.py` и protected boundaries не затронуты |
| **RM-UX-006 / A5** | Advertiser-web UX audit/fixes | U5 | отдельная безопасная test persona; 15 routes audited; backlog и journey proofs обновлены |
| **RM-UX-007 / A7** | Human operator walkthrough | U1–U6 | выполняет человек на exact stand bundle; PASS/FAIL и замечания записывает только владелец/аудитор |

**Gate U:** владелец принимает walkthrough. Автоматические тесты не заменяют этот gate.

## 5. Этап B/T — бизнесовые и технические разрывы (12 задач)

| ID | Результат | Зависит от | Приёмка / decision gate |
|---|---|---|---|
| **RM-BIZ-001** | Решение scope self-service | U | владелец выбирает состав control-plane pilot: `self.campaign_create` входит/не входит; roadmap фиксирует решение |
| **RM-BIZ-002** | `self.campaign_create` | RM-BIZ-001: входит в scope | mini-design, journey, backend/UI/RLS, smoke intended advertiser role, walkthrough |
| **RM-TECH-201** | Таксономия причин недопоказа | U | 8 категорий ТЗ; ручные/автоматические источники; report contract; историчность |
| **RM-TECH-202** | Вытеснение и объяснимые приоритеты | 201 | версия правил; кто кого вытеснил и почему; negative publication gate; без ретроизменения отчётов |
| **RM-TECH-203** | Overbooking policy | 202 | default deny; platform setting; simulation/publication enforcement; audit |
| **RM-TECH-204** | Creative QA | U | media metadata checks; antivirus/executable deny; HTML5 owner/ИБ decision; immutable QA result |
| **RM-TECH-205** | SLO objectives и измерение | U | каждое число ТЗ имеет формулу/window/owner/metric либо честное `not measurable`; без readiness-процента на глаз |
| **RM-TECH-206** | License peak/grant boundary | U | owner architecture decision; renewal scenario behavioral proof; billing peak не обнуляется при occupied seats |
| **RM-TECH-207** | Реальная KSO environment + player/playlist | U, owner hardware inputs | environment audit → import/design → playback/manifest/PoP full chain; отдельный protected device approval |
| **RM-BIZ-003** | `self.report_view` plan/fact | 201, 207 | реальные PoP, причины, RLS advertiser scope, UI journey/smoke/walkthrough; без synthetic-ready claim |
| **RM-TECH-208** | Signed licensing Layer 2 + Ed25519 compatibility | 206–207, S10 | offline verify, kid/rotation/revocation, upload/view UI, tamper/rollback; protected-boundary approval |
| **RM-TECH-209** | ClickHouse capacity trigger | 207 | измеряемый PoP rate/retention threshold и migration decision gate; без преждевременной миграции |

## 6. Этап E/P — окружения, pilot и production (5 задач)

| ID | Результат | Зависит от | Приёмка / внешняя граница |
|---|---|---|---|
| **RM-ENV-001** | Инвентарь окружений `.77/.81/DEV/PROD` | G | owner решает retire/upgrade/preserve; `.77` только `unreachable at check time`; ни один клик по stale env не считается proof |
| **RM-PILOT-001** | Control-plane pilot scope + 001D inputs/host proof | S, U | все owner inputs закрыты; exact bundle/host/rollback/TLS decision; pilot scope явно исключает device claims |
| **RM-PILOT-002** | Pilot deployment plan/preflight | P1 | immutable lock, backup/restore, migration rehearsal, secrets/TLS/monitoring gates; dry-run evidence |
| **RM-PILOT-003** | Controlled control-plane pilot deploy | P2 + отдельное разрешение | deployed SHA/lock/schema, health, stand-safe/targeted journey proof, rollback readiness; без production claim |
| **RM-OPS-001** | Production hardening/readiness | P3, B/T по утверждённому scope | TLS/CD, secrets rotation, monitoring/SLO, backup/DR, load/HA, security review; отдельный owner GO |

## 7. Явно deferred — не превращать в активные задачи

- Channel Orchestrator остаётся deferred по ADR-019 до второго канала.
- Android/Android TV, Price Checker, ESL, LED, mobile field ops, programmatic и dynamic creative
  не активируются без нового owner decision.
- ClickHouse не реализуется по прогнозу; только по RM-TECH-209 trigger.
- Device/KSO contracts и deployment не меняются внутри control-plane задач.

## 8. Предлагаемая очередь после feasibility review

`GOV-001…005` → `STAB-001…011` → `UX-001…007` → затем две развилки, которые владелец
утверждает отдельно:

1. **control-plane pilot:** `ENV-001 → PILOT-001…003` после Gate U;
2. **product/device expansion:** `BIZ/TECH` по зависимостям §5 → device pilot → OPS-001.

Так control-plane pilot не блокируется отсутствующим КСО и одновременно не выдаётся за device
или production readiness.

## 9. Что должен проверить Claude

1. Все 40 задач исполнимы как отдельные coherent changes одним implementation agent.
2. Нет скрытых file-overlap/dependency cycles и пропущенных audit findings.
3. Acceptance проверяема конкретными командами, CI или live proof.
4. Protected boundaries и external actions вынесены в owner gates.
5. Предложить только изменения slicing/dependencies; код, канон, roadmap и стенд не менять.

После reconciliation Codex принимает/корректирует замечания, владелец утверждает окончательную
очередь. Только после этого Claude начинает RM-GOV-001.
