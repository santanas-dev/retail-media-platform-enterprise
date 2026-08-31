# Claude — RM-GOV-012: выравнивание ТЗ ↔ roadmap ↔ хронология ↔ зависимости ↔ gates; единый план реализации

Статус: **кандидат; не закоммичено; ждёт проверки Codex и утверждения владельцем.** База: `develop @ 4ac3ddb` + рабочее дерево
(RM-GOV-010-A/B, r427). Указание владельца 2026-08-31 записано `OD-041`.

## 1. Пауза RM-UX-007 / walkthrough
`OD-041` approved 2026-08-31; RM-UX-007 остаётся `planned` (не done, не deferred), notes + ref приёмки; Gate-U — условие паузы;
`operator-walkthrough-dev.md` — баннер; PROJECT_STATE — `operator walkthrough: PENDING — приостановлен (OD-041)`.

## 2. Кросс-проверки (полный вывод — `scratchpad/alignment-checks*.txt` сессии; воспроизводимо из SSOT)
B1 зависимостей на более поздний этап — 0 · B2 этапов без gate — 5 (E0, CORE, CH, A, POPS) · B3 owner_gate без OD в тексте — 8
(гейты исполнения, не дефект) · B4 blocked без open OD — RM-TECH-263, RM-TECH-284 · B5 приёмок без ref — 5 · B6 blocked-функций без
feature_ids — 6 · B8 REQ planned при всех задачах blocked — 3 · B10 критические цепочки — POPS 29, portal 24, attribution 23.

## 3. Применено (см. план §9)
Gate-CORE/CH/A/POPS, Gate-C расширен; перенос RM-TECH-205/288/253, RM-OPS-005, RM-UX-011 → C; RM-TECH-231 (proposed);
RM-GOV-012 (proposed, in_progress по указанию владельца); feature_ids ×5; refs ×4 + owner-приёмка RM-ENV-003; RM-TECH-263 planned;
RM-TECH-284 OD-014; REQ-BIZ-009/V26-006/INT-003 blocked; драфт r428 (`ffb8cf7d192e…`); карта r428.
План: `docs/product/implementation-plan-v2.6.md` (roadmap sha `da0d93fecc5a…`).

## 4. Не сделано намеренно
AGENTS.md индекс канона (canon_change — после утверждения); нормативные разделы ТЗ; код.

## 4a. Правки по заключению Codex (2026-08-31)
- Явный **Gate-E0** (approver owner): условия — приёмка RM-ENV-003 как артефакта AG и зелёный guard env; `note` —
  историческая пометка: RM-ENV-001 закрыта 2026-08-26 до введения гейта и не переоценивается (правило GATE-NOT-APPROVED
  касается только done-задач с owner_gate canon_change — гейт зелёный без approved_on).
- Схема гейта получила поля `decision` (что означает утверждение) и `note` (пометка); у Gate-C входные условия (артефакты AG
  приняты по отдельности, contract tests, сверка Codex) отделены от решения (ТЗ → APPROVED, старт разработки по OD-041);
  маркеры «предложение RM-GOV-012» вынесены из условий в `note` у Gate-CORE/CH/A/POPS; пауза walkthrough — в `note` Gate-U.
- Сводки (PROJECT_STATE, план, запись) сверены с фактическими счётчиками roadmap.

## 5. Итог
109 задач (2 proposed) · OD 41 (22 approved / 19 open) · gates 9 · registry 79/52/27 · REQ delivery planned 88 / blocked 9 / in_progress 4.
