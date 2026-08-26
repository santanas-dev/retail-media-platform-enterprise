# Финальный кандидат task breakdown после reconciliation

> ## ⚠️ НЕ КАНОН — очередь ещё не разрешена к исполнению
>
> | | |
> |---|---|
> | **Тип** | Архитектурный task breakdown, final candidate |
> | **База** | `develop @ 2b935bb`; `origin/develop @ 2b935bb`; stand baseline `stand-27dc397`, schema `036` |
> | **Дата** | 2026-08-26 |
> | **Автор** | Codex, архитектор/ревьюер |
> | **Основание** | draft Codex + feasibility Claude + восемь решений владельца от 2026-08-26 |
> | **Статус** | Ожидает финальной feasibility-проверки Claude и утверждения очереди владельцем |
> | **Всего задач** | 42: G 6 + S 11 + U 7 + B/T 13 + E/P 5 |
> | **Изменения продукта/канона/стенда** | Нет |
> | **Отменён** | — |

## 1. Утверждённые ограничения

1. Код/тесты описывают фактическое поведение; ТЗ/ADR — требуемое. Расхождение является
   дефектом до явного ADR, а не основанием молча переписать требование.
2. Ed25519 обязателен для device pilot/production. HMAC допустим только для dev и
   control-plane stand; он не является production evidence.
3. Retailer scope — первоклассная граница. Внутренние роли работают по least privilege;
   bypass разрешён только `system_admin` и `security_admin`.
4. UI-smoke отделён от ordinary pytest, но является blocking gate для `develop`, release и
   повышения journey до `reachable`. Правка контракта выполняется только отдельной задачей.
5. `self.campaign_create` исключён из ближайшего control-plane pilot; первый pilot managed-first.
6. При renewal занятые seats старого grant атомарно закрываются и продолжаются под новым grant;
   история и billing peak сохраняются.
7. Активный baseline — `.81 / stand-27dc397`. `.77` убирается из активных ссылок, но называется
   только `unreachable at check time`; старые DEV/PROD не являются evidence до отдельного решения.
8. MFA и NATS регистрируются как открытые решения: MFA обязателен до production, согласование
   NATS с ИТ/ops — до pilot deployment. Они не блокируют выравнивание roadmap.

Эти решения не разрешают код, migration application, deployment, merge или release.

## 2. Правила исполнения и доказательств

- Claude Code — единственный implementation agent; Codex проектирует и независимо проверяет;
  владелец утверждает архитектуру, protected boundaries и внешние действия.
- Одна implementation-задача за раз. `kind: governance|design|implementation|human|external` не
  означает, что decision-задачи исчезают из журнала работ.
- Каждая приёмка обязана назвать команду, CI job, behavioral/live proof или versioned artifact.
- `roadmap.yaml` хранит `proof_granularity: dedicated|shared:<smoke-id>` и `evidence_refs` со
  статусом `verified|disputed|superseded`; спорный proof не меняет registry молча.
- `RM-GOV-004` владеет структурным guard. `RM-STAB-005` расширяет его smoke-semantics правилами,
  а не создаёт параллельный guard.
- Любое применение миграции к stand/pilot и любое изменение device contract требует отдельного
  owner approval; destructive migration остаётся protected boundary.
- Полный UI-smoke на общем stateful stand запрещён; только stand-safe runner или отдельно
  согласованный изолированный target.

## 3. Этап G — единая система roadmap (6 задач)

| ID | Kind | Результат | Зависит от | Проверяемая приёмка |
|---|---|---|---|---|
| **RM-GOV-001** | design | Schema/mini-design `roadmap.yaml` | — | schema validator; поля `kind`, dependency, acceptance, maturity, `proof_granularity`, `evidence_refs`; owner approval |
| **RM-GOV-002** | governance | Reconciliation/migration manifest | G001 | disposition для 93 technical items, 13 SECTION и 57 business rows; 5 blocked features имеют gap/unblock; счётчики воспроизводимы скриптом |
| **RM-GOV-003** | implementation | Односторонний generator YAML + registry + evidence → Markdown/XLSX/metrics | G001–002 | deterministic generation; повторный run даёт clean diff; обе XLSX sheets и формулы проверены |
| **RM-GOV-004** | implementation | Структурный roadmap guard | G003 | tamper matrix красная для drift/schema/dependencies/metrics/SSOT и зелёная на baseline; smoke AST сюда пока не входит |
| **RM-GOV-006** | governance | Единое правило факта и требования | G001 | approved правило §1.1 записано без конфликта в индекс/ADR-процесс; targeted doc guard зелёный |
| **RM-GOV-005** | governance | Canonical cutover | G003–004, G006 | один sequencing SSOT в `AGENTS.md`; stale mutators quarantined; generated views read-only; PROJECT_STATE Next синхронизирован; CI green; owner approval |

**Gate G:** Codex проверяет generator и tamper matrix; владелец утверждает cutover. До Gate G
канонические файлы и текущий Next не изменяются.

## 4. Этап E0 — окружения сразу после Gate G

| ID | Kind | Результат | Зависит от | Проверяемая приёмка |
|---|---|---|---|---|
| **RM-ENV-001** | governance | Инвентарь `.77/.81/DEV/PROD` и очистка активных ссылок | Gate G | versioned environment inventory; `.81/stand-27dc397` baseline; `.77` только `unreachable at check time`; DEV/PROD `not evidence`; retire/upgrade остаётся owner decision |

## 5. Этап S — стабилизация доказательств и границ (11 задач)

| ID | Kind | Результат | Зависит от | Проверяемая приёмка |
|---|---|---|---|---|
| **RM-STAB-001** | implementation | Единый контракт `BEHAVIORAL_APP_DB_URL` | E0 | обе DSN-формы проходят один targeted behavioral command через один helper |
| **RM-STAB-002** | implementation | Strict RLS context по умолчанию | S001 | admin elevation только setup; endpoint allowlist; context tamper красный; behavioral subset зелёный |
| **RM-STAB-003** | design | Зафиксировать approved personas/retailer-scope | S002 | mini-design/ADR: persona→permissions→scope; единственные bypass-роли из §1.3; owner принимает точную модель до кода |
| **RM-STAB-006** | governance | 45/45 нормативных UI journeys | S003 | validator: actor, permission, entry, `Happy-path: N`, selectors, negative expectation; 0 status/history в spec |
| **RM-STAB-004** | implementation | Реализовать approved RBAC/RLS scope | S003, S006 | API/portal/migration согласованы; intended-role positive+negative behavioral proof; cross-retailer isolation; применение миграции отдельно разрешается |
| **RM-STAB-007** | implementation | UI proof под intended roles | S004, S006 | critical journeys имеют positive intended-role и negative missing-permission proof; registry меняется только после green |
| **RM-STAB-005** | implementation | Исправить C1 UI-smoke и расширить общий guard | E0 | нет API/deep goto/sleep/broad retry; current-run audit event; AST tamper красный; first-attempt green |
| **RM-STAB-009** | implementation | Воспроизводимые CI dependencies | E0 | CI ставит project lock/requirements; tested=shipped version; drift tamper красный |
| **RM-STAB-010** | governance | Зафиксировать signing gate | E0 | ADR/roadmap отражают §1.2; HMAC не даёт device/production maturity; device contract не меняется |
| **RM-STAB-008** | implementation | Единая blocking-политика UI-smoke | S005, S007 | ordinary pytest отделён; develop/release/reachable gates blocking; workflow/AGENTS/generated view совпадают; release tamper красный; owner review contract patch |
| **RM-STAB-011** | governance | W0 rebaseline | S001–010 | named targeted → behavioral → UI subset → guards; disputed evidence записано в YAML; live только read-only/stand-safe; Codex ACCEPT |

**Gate S:** новые counts и evidence воспроизводимы. Исторический registry status не понижается
без отдельной доказанной причины; сомнительное доказательство отмечается в `evidence_refs`.

## 6. Этап U — утверждённый UX-порядок (7 задач)

| ID | Kind | Результат | Зависит от | Проверяемая приёмка |
|---|---|---|---|---|
| **RM-UX-001 / A3** | implementation | Accessibility оставшихся форм + route matrix | Gate S | labels/ARIA/axe/targeted vitest; versioned `docs/product/ux-route-matrix.yaml` принят |
| **RM-UX-002 / A2** | implementation | Поиск/сортировка/усечение таблиц | U001 | server semantics для pagination; targeted UI/API proof; нет client-only ложного поиска |
| **RM-UX-003 / A4** | implementation | Responsive-проверка | U002 | все routes из `ux-route-matrix.yaml` проверены на 390px без overflow/crop; именованный artifact результата |
| **RM-UX-004 / A6** | implementation | Согласованность состояний и терминов | U003 | route matrix покрывает empty/loading/error/403/success и locale-key check; targeted visual/DOM proof |
| **RM-UX-005 / A1b** | implementation | Adoption доказанных primitives малыми slices | U004 | каждый slice имеет отдельный diff/test/review; без wholesale `main.py` и broad redesign |
| **RM-UX-006 / A5** | implementation | Advertiser-web UX audit/fixes | U005 | versioned `docs/product/advertiser-route-matrix.yaml` с точным списком 15 routes; safe persona; journey proofs |
| **RM-UX-007 / A7** | human | Human operator walkthrough | U001–006 | человек проходит exact stand bundle; только человек пишет PASS/FAIL и замечания в PROJECT_STATE |

**Gate U:** только владелец принимает walkthrough. Автоматические тесты его не заменяют.

## 7. Этап B/T — бизнесовые и технические разрывы (13 задач)

| ID | Kind | Результат | Зависит от | Проверяемая приёмка / gate |
|---|---|---|---|---|
| **RM-BIZ-001** | governance | Записать managed-first scope | Gate U | roadmap явно исключает `self.campaign_create` из ближайшего control-plane pilot |
| **RM-BIZ-002** | implementation | `self.campaign_create` в будущей ветке | B001 + новый owner scope | mini-design, journey, backend/UI/RLS, intended-role smoke, walkthrough |
| **RM-TECH-201** | design | Таксономия причин недопоказа | Gate U | 8 категорий ТЗ, source/report/history contract и owner-approved artifact |
| **RM-TECH-202** | implementation | Вытеснение и объяснимые приоритеты | T201 | versioned rules; displacement reason; negative publication test; историчность отчётов |
| **RM-TECH-203** | implementation | Overbooking policy | T202 | default deny; setting, simulation/publication enforcement и audit behavioral tests |
| **RM-TECH-204** | implementation | Creative QA без неутверждённого HTML5 | Gate U | metadata/antivirus/executable deny и immutable QA result; HTML5 остаётся отдельным owner/ИБ decision gate |
| **RM-TECH-205** | governance | SLO objectives и измерение | Gate U | каждое число ТЗ имеет formula/window/owner/metric либо `not measurable`; versioned SLO artifact |
| **RM-TECH-206** | implementation | License renewal/grant boundary | Gate U | атомарная семантика §1.6; concurrency/rollback behavioral proof; billing peak не обнуляется |
| **RM-TECH-207A** | design | KSO environment + player/playlist design | Gate U + hardware inputs | versioned environment audit, import/contract mini-design и test plan; owner отдельно принимает device boundary |
| **RM-TECH-207B** | implementation | KSO player/playlist/PoP chain | T207A + отдельный device approval | contract tests и playback→manifest→PoP behavioral proof; no-secrets/no-path projection checks |
| **RM-BIZ-003** | implementation | `self.report_view` plan/fact | T201, T207B | реальные PoP/причины/RLS, journey/smoke/walkthrough; без synthetic-ready claim |
| **RM-TECH-208** | implementation | Signed licensing Layer 2 | T206, T207B, S010 | Ed25519 offline verify, kid/rotation/revocation, UI, tamper/rollback; protected-boundary approval |
| **RM-TECH-209** | governance | ClickHouse capacity trigger | T207B | измеряемый PoP rate/retention threshold и owner migration gate; без преждевременной миграции |

## 8. Этап P/OPS — внешние действия (4 задачи; вместе с E0 = 5)

| ID | Kind | Результат | Зависит от | Проверяемая приёмка / внешняя граница |
|---|---|---|---|---|
| **RM-PILOT-001** | design | Managed control-plane pilot scope | Gate S, Gate U, E001 | exact bundle/host/rollback/TLS; self-service и device claims исключены; owner inputs закрыты |
| **RM-PILOT-002** | external-plan | Deployment plan/preflight | P001 | immutable lock, backup/restore, migration rehearsal, secrets/TLS/monitoring; NATS IT/ops decision закрыт; dry-run evidence |
| **RM-PILOT-003** | external | Controlled pilot deploy | P002 + отдельный owner GO | SHA/lock/schema/health, stand-safe journeys, rollback readiness; без production claim |
| **RM-OPS-001** | external | Production readiness | P003 + отдельно утверждённый production scope | не запускается автоматически после pilot; MFA, TLS/CD, secrets, SLO, DR, load/HA, security review; отдельный owner GO |

## 9. Очередь и развилки

```text
GOV-001 → GOV-002 → GOV-003 → GOV-004 ─┐
           GOV-001 → GOV-006 ───────────┴→ GOV-005 → Gate G → ENV-001

STAB-001 → 002 → 003 → 006 → 004 → 007 ─┐
STAB-005 · STAB-009 · STAB-010 ──────────┴→ STAB-008 → STAB-011 → Gate S

UX-001 → 002 → 003 → 004 → 005 → 006 → UX-007 (human) → Gate U

Ветка 1: PILOT-001 → 002 → owner GO → 003
Ветка 2: BIZ/TECH по зависимостям → device pilot
Production: только новый scope + отдельный owner GO → OPS-001
```

Stage S начинается с цепочки спецификации `S003 → S006` до реализации `S004`. `ENV-001`
выполняется до любых новых live-proof. `OPS-001` не является автоматическим продолжением pilot.

## 10. Deferred и следующий gate процесса

- Channel Orchestrator остаётся deferred по ADR-019; Android/TV/ESL/LED/mobile/programmatic не
  активируются без нового owner decision; ClickHouse — только после `RM-TECH-209` trigger.
- Открытые decisions: retire/upgrade DEV/PROD, HTML5 policy, точный MFA mechanism, NATS topology.
- Следующий шаг — только feasibility-проверка Claude: IDs, DAG, file-overlap, проверяемость
  acceptance и protected/external gates. После неё владелец отдельно утверждает очередь и старт
  `RM-GOV-001`.
