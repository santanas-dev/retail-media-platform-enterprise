# A2 — единый реестр решений: DEC как alias `roadmap.yaml:owner_decisions`

> ⚠️ **НЕ КАНОН** · тип: запись о выполнении артефакта A2 (AQ ledger «Два decision namespace DEC/OD»)
> · SHA: `develop @ e429f97` + рабочее дерево · дата: 2026-08-28 · автор: Claude Code
> · основание: OD-017 (ACCEPT r421), указание владельца «после зелёного CI переходи к A2»
> · открытых находок: 2 (§4) · Отменён: —

## 1. Что сделано

Второго реестра нет. Каждый из 27 `DEC-ID` §29 драфта представлен ровно одной записью
`owner_decisions` через новое поле `aliases`; поле `sources` называет, где решение
ратифицировано (ADR, `user-journeys.md §5.1/§3`, OD, §ТЗ).

| Слой | Изменение |
|---|---|
| `docs/product/roadmap.schema.json` | `owner_decisions[].aliases` (`^DEC-\d{3}$`, unique) и `sources` |
| `docs/product/roadmap.yaml` | alias у 10 существующих OD; **16 новых OD-021…OD-036** для DEC без записи; итог 36 OD (16 approved / 20 open) |
| `scripts/ci/check-roadmap-schema.py` | правило `DEC-ALIAS-DUP` + tamper-кейс; fixture с alias (18/18 CAUGHT) |
| `scripts/ci/roadmap-governance-guard.py` | модуль `decisions`: `DEC-UNMAPPED`, `ALIAS-UNKNOWN`, `ALIAS-DUP`, `ALIAS-SUPERSEDED`, `DEC-TABLES-DIVERGE`, `DRAFT-MISSING/NO-REGISTER`; драфт добавлен в sandbox; 5 tamper-кейсов с проверкой инертности — self-test **39/39**, 10 измерений |
| `scripts/ci/roadmap-generate.py` | таблица решений: колонки «DEC alias», «Источники»; проекции регенерированы, `--check-clean-diff` CLEAN |

## 2. Карта DEC → OD

| Статус | DEC → OD |
|---|---|
| approved, ратифицировано ранее | DEC-002→OD-022 (ADR-019, 2026-07-20) · DEC-003→OD-002 · DEC-011→OD-005 · DEC-021→OD-034 (§5.1, 2026-07-18) · DEC-023→OD-035 (Q2) · DEC-025→OD-036 (ADR-015, 2026-07-05) |
| approved 2026-08-28 | DEC-022→OD-018 · DEC-024→OD-019 · DEC-026→OD-020 |
| open, уже имели OD | DEC-004→OD-008 · DEC-006/007→OD-009 · DEC-008→OD-010 · DEC-009→OD-011 · DEC-027→OD-014 |
| open, новые OD | DEC-001→OD-021 · DEC-005→OD-023 · DEC-010→OD-024 · DEC-012→OD-025 (blocks RM-OPS-001) · DEC-013→OD-026 · DEC-014→OD-027 · DEC-015→OD-028 · DEC-016→OD-029 · DEC-017/018/019/020→OD-030…033 |

Правило статуса: OD `open`, если владельцу осталось что-то решить (OD-009-паттерн:
«дефолты приняты, остаток открыт»); `approved` — если остаток только implementation
(DEC-023, DEC-025).

## 3. Проверки

`check-roadmap-schema` PASS + self-test 18 CAUGHT · `roadmap-governance-guard` PASS, self-test 39/39
· `roadmap-generate --check-clean-diff` CLEAN · `roadmap-consistency-check` 0. Всё локально;
CI-прогон — после commit/push.

## 4. Остаток

1. **Драфт (Codex, r423):** колонка «Текущий источник» §29/Дополнения I ещё держит
   `PENDING-OD`/«не зафиксирован» для DEC-005/022/024/026 и не называет OD-021…036.
   Guard сверяет только множество DEC-ID, поэтому CI не краснеет; но по OD-001 драфт
   должен ссылаться на OD. Правка — одна колонка, нормативный текст не меняется.
2. **DEC-005 / OD-023:** имя владельца master-данных не получено — в указании стоял
   незаполненный шаблон `<имя/роль>`. После имени OD-023 → approved с датой.

Остальные 18 открытых OD — вопросы с триггерами; они не блокируют `APPROVED` ТЗ,
блокируют конкретные задачи (записано в `blocks`, где задача существует).

## 5. Дальше

A1: `requirements-traceability.yaml` + модуль `req` в guard + `SC-*` для 53 REQ → A3 task
breakdown (owner-gated: RM-GOV-007 «decision registry» получает эту запись и CI как evidence).
