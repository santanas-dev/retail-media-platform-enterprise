# Claude — проверка отчёта Codex r424 и перепривязка карты требований на r424

Статус: **применено в рабочем дереве; не закоммичено** (указание владельца 2026-08-31).
База: `origin/develop @ cbffb3b` + локальные правки Codex r423/r424. Предыдущий шаг:
`2026-08-31-claude-tz-r423-traceability-rebuild.md` (r423 — сохраняется как запись на дату).

## 1. Проверка отчёта `2026-08-31-codex-independent-audit-tz-r424.md`

| # | Утверждение Codex | Проверка |
|---|---|---|
| 1 | все 27 DEC §29/Доп. I имеют один alias OD; DEC-022/024/026 ↔ OD-018/019/020 | **подтверждено**: 27 = 27 = 27 alias; все 27 строк Доп. I ссылаются на свой OD (r423 покрыл OD-018/019/020, r424 — остальные 16) |
| 2 | §6, §25, §26, AP не изменялись | **подтверждено**: `sha(§6) c81660073d53`, `sha(§25) 047269764cd5`, `sha(§26) 87ad03f6f972`, `sha(AP) 81f6af86dcda` = r419; REQ 101 / stories 41 / AC 326 |
| 3 | traceability устарела (r423) | верно; перепривязана ниже |
| 4 | блокеры APPROVED: 170 TBD, 23 PENDING-ID (8 awaiting_owner), OD-023, journeys/smoke/walkthrough | **подтверждено** счётчиками guard `req` и registry 73/52/21 (21 blocked ID без journey/smoke); walkthrough — `PENDING` по AQ |
| 5 | README требований: r424, ADR-018 Accepted | ADR-018 `Status: Accepted` (2026-07-17, PLAN-001) — верно. Формулировка «r424 дополняет … по OD-018/019/020» неточна: это r423; r424 — ссылки на OD-021…036 |

**Чего в отчёте нет** (найдено при проверке):

- **Sidecar r424 неверен**: `tz-v2.6-draft.sha256` содержал `29af88ce…`, байты драфта дают
  `7a09ee92…` (ни один вариант — без хвостового `\n`, с лишним, CRLF — не совпадает). Поймал
  новый гейт `req/SIDECAR-DRIFT`. Sidecar пересчитан по фактическим байтам r424.
- **Оборванная фраза** в changelog r424 (строка ~34): «…DEC-025→OD-036). Статусы и решения» —
  предложение не завершено. Драфт не правил (это редакция Codex, любая правка = r425 + sidecar).
- **Overclaim DEC-014**: строка Доп. I переписана в «approved boundary: read-only/non-authoritative
  monitoring; … фиксируются в OD-027», тогда как `OD-027` в `roadmap.yaml` — **open** («Требуется
  решение владельца с датой»), а §29 DEC-014 approved не заявляет. По правилу самого драфта строка
  с несовпадающим статусом должна нести `CONFLICT`, а не approved. Ждёт исправления Codex (r425).
  Ряды DEC-006/007/010 («SLA targets/retention/шкала approved; … открыта») — частичные approvals
  до r424, с open OD-009/OD-024 согласованы.

## 2. Перепривязка `requirements-traceability.yaml` на r424

Состав REQ/SC/story не менялся (нормативные разделы байт-в-байт с r419), содержимое карты не
перегенерировалось: `document.revision: …r423 → draft-2026-08-31-r424`, `document.sha256:
585a9069… → 7a09ee92…` (= пересчитанный sidecar = байты драфта), `source` у 101 REQ и 69 SC
(171 ссылка), комментарий в шапке. `document.status: ACCEPTED` (OD-017) — **не поднят до
APPROVED** и не будет до закрытия 170 TBD owner, 23 PENDING-ID journeys, `OD-023` и
operator walkthrough.

## 3. Прогоны (рабочее дерево)

| Проверка | До перепривязки | После |
|---|---|---|
| guard `req` | FAIL — `DRAFT-REVISION-DRIFT` (r423≠r424), `DRAFT-SHA-DRIFT`, `SIDECAR-DRIFT` | PASS |
| `check-roadmap-schema.py` | — | PASS |
| `roadmap-consistency-check.py` | — | 0 violations |
| `roadmap-generate.py --check` | — | CLEAN |
| guard, все модули | — | PASS (req: REQ 101 / SC 69 / без roadmap_ids 0; TBD 170) |
| guard `--self-test` | — | 53/53 |

CI не запускался — commit/push не выполнялись.

## 4. Счётчики

REQ 101 / SC 69 / без roadmap_ids 0 / pending journeys 23 (8 awaiting_owner, 15 mapped на blocked
registry ID) / TBD owner 170 / evidence 306 candidate, 0 verified / задач 107 / OD 38
(18 approved, 20 open) / registry 73 / 52 reachable / 21 blocked.

## 5. Оставшиеся расхождения

1. Codex r425: завершить фразу changelog r424; вернуть DEC-014 в Доп. I к «owner decision
   требуется (OD-027 open)» или пометить `CONFLICT`; уточнить README (r423 vs r424); пересчитать
   sidecar (`sha256sum` по файлу) — гейт `SIDECAR-DRIFT` проверит.
2. `OD-023` (DEC-005) open — цепочка RM-TECH-280…285 blocked.
3. Блокеры APPROVED без изменений: 170 TBD owner (RM-GOV-010), 8 awaiting_owner PENDING-ID + 15
   mapped без journey/smoke, operator walkthrough PENDING для всех UI stories.
4. Локальные изменения не закоммичены — CI evidence появится только после commit/push.
