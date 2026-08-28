# RM-GOV-009 — A3 применён к канону по решениям владельца (рабочее дерево, ждёт ACCEPT)

> ⚠️ **НЕ КАНОН** · тип: запись о применении кандидата A3 · SHA: `develop @ d8b6872` + рабочее дерево
> · дата: 2026-08-28 · автор: Claude Code · основание: решения владельца 2026-08-28 (OD-037, OD-038, blocks OD-013/024/025/028; OD-023 остаётся open)
> · открытых находок: 0 · Отменён: —
>
> Ничего не закоммичено и не запушено. Канонические файлы изменены в рабочем дереве; `decision_status: proposed`
> у 64 новых задач до owner ACCEPT очереди.

## 1. Что применено

| Файл | Изменение |
|---|---|
| `roadmap.yaml` | стадии `G E0 S C CORE U CH A POPS` (BT расформирован), `Gate-C`; OD-037/OD-038; `blocks` у OD-013/024/025/028; `blocked_features` +16 (device.onboard + 15 новых ID); 14 задач BT переставлены (+ RM-BIZ-003 → A, RM-TECH-208 → CH); Gate-U → Gate-S у 6 задач; редакции RM-STAB-006 (без «45/45»), RM-TECH-207B (+2 acceptance: Playlist state machine, manifest lifecycle/canonical PoP), RM-BIZ-002 (`blocked` до OD-013); notes «RM-GOV-009 (r421): …» у 10 задач; **64 новые задачи** |
| `roadmap.schema.json` | `stage` enum = 9 стадий; поле `owner_role` |
| `check-roadmap-schema.py` + fixture | `STAGE_ORDER` по OD-037; фикстура: BT → CORE, blocked_features под 21 blocked-функцию |
| `feature-registry.yaml` | `device.onboard` → blocked (OD-038, gap с причиной); +15 ID со статусом blocked; summary пересчитан |
| `requirements-traceability.yaml` | `roadmap_ids` у 51 REQ (disposition task/blocked), STAND-001/002 → RM-ENV-002; 15 PENDING-ID → `journey_ids` (map `mapped`); SC получили roadmap_ids |
| `roadmap-governance-guard.py` | metrics(c): проверяется тройка с маркером `Registry (current)`, исторические — записи на дату (+2 tamper-кейса); req: `PENDING-IS-CANONICAL` только для `awaiting_owner` |
| `PROJECT_STATE.md`, `generated/README.md` | маркер текущей тройки, запись RM-GOV-009, число задач; README без захардкоженных чисел |

## 2. Уточнения относительно кандидата, который проверял Codex

Validator (STAGE-ORDER/MISSING-OWNER-GATE/ref) потребовал 7 правок, кандидат перегенерирован с ними:
RM-BIZ-003 → A, RM-TECH-208 → CH (зависят от RM-TECH-207B в CH); RM-TECH-256 → A (зависит от RM-TECH-205);
RM-TECH-280 → CH (prerequisite для каналов и аналитики); RM-UX-010 → A (зависит от RM-BIZ-003);
RM-ENV-002 без зависимости от RM-STAB-011; owner gate `scope_decision`/`deployment` у 6 задач с owner-acceptance;
`ref` у artifact/owner/human acceptance. Покрытие и статусы не изменились.

## 3. Итоговые счётчики

| | |
|---|---|
| Задач | **107** (43 approved + 64 proposed): G 11, E0 3, S 18, C 11, CORE 22, U 11, CH 9, A 14, POPS 8 |
| Delivery | done 9, planned 80, blocked 16, verification 2 — `done` только прежние 9 |
| Owner decisions | 38 (OD-037/038 новые); гейты: Gate-G, Gate-S, Gate-U, Gate-C |
| Registry | 73 / 52 reachable / 21 blocked; blocked_features 21 |
| Traceability | REQ без roadmap_ids: **0**; PENDING-ID awaiting_owner: 8 (из 23) |

## 4. Проверки (локально)

check-roadmap-schema PASS + self-test PASS · roadmap-consistency-check 0 · roadmap-generate CLEAN ·
governance guard PASS, self-test **50/50, 11 измерений**. CI — после разрешения на commit/push.

## 5. Дальше

Владелец: ACCEPT очереди (proposed → approved, RM-GOV-009 done с ci_run) и разрешение commit/push.
Открыто: OD-023 (владелец master-данных), RM-GOV-010 (170 TBD, 8 PENDING-ID).

## 6. Дополнение 2026-08-28 — замечание Codex (дубликат в OD-013.blocks)

`add_blocks` дописал `RM-BIZ-002` к уже существовавшему списку — `OD-013.blocks` содержал элемент дважды.
Исправлено; введена проверка уникальности `blocks`/`aliases` у всех owner decisions на двух уровнях:
`roadmap.schema.json` (`uniqueItems`) и семантическое правило `OD-DUP-ITEM` в check-roadmap-schema
(2 tamper-кейса) + tamper-кейс guard `decisions` (51/51). Все проверки повторены — зелёные. CI —
только после commit/push (workflow_dispatch прогонит HEAD, не рабочее дерево).

