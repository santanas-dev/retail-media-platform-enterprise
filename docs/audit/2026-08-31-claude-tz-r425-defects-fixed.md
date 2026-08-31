# Claude — редакция r425: исправление трёх дефектов r424

Статус: **применено в рабочем дереве; не закоммичено** (указание владельца 2026-08-31).
База: `origin/develop @ cbffb3b` + рабочее дерево (r423/r424 Codex, перепривязка карты).
Находки — в `2026-08-31-claude-tz-r424-traceability-rebuild.md` §1.

## 1. Правки драфта (r424 → r425)

| # | Дефект r424 | Исправление r425 |
|---|---|---|
| 1 | sidecar `29af88ce…` ≠ байты драфта | `tz-v2.6-draft.sha256` пересчитан по фактическому файлу: `8688b5595d4d527f07684fb6a216f5e1659952f9359fbfe2f15b012381f81d2e`; `sha256sum -c` → OK |
| 2 | оборванная фраза changelog r424 («…Статусы и решения») | завершена: статусы DEC не менялись; ошибочная формулировка DEC-014 отмечена и отнесена к r425 |
| 3 | Доп. I DEC-014 «approved boundary» при open `OD-027` | строка возвращена в «предложенная boundary; **owner decision требуется** — `OD-027` open: scope, freshness/correlation, MON-DIVERGENCE, запрет записи статусов» (формулировка OD-027) |

Плюс: Revision `r424 → r425`, parent snapshot, changelog r425, хвост AQ «текущий объект — r425»,
`docs/product/requirements/README.md` (r425, точное разделение r423/r424). Нормативные разделы не
тронуты: `sha(§6) c81660073d53`, `sha(§25) 047269764cd5`, `sha(§26) 87ad03f6f972`, `sha(AP) 81f6af86dcda`
= r419; REQ 101 / stories 41 / AC 326 / DEC 27.

## 2. Карта требований

`document.revision → draft-2026-08-31-r425`, `document.sha256 → 8688b5595d4d…`, 171 source-ссылка,
шапка. Содержимое не перегенерировалось (состав REQ/SC/story не менялся). `document.status:
ACCEPTED` (OD-017) — **APPROVED не объявлен**: блокеры 170 TBD owner, 23 PENDING-ID (8 awaiting_owner),
`OD-023`, operator walkthrough.

## 3. Гейты

См. итог прогонов в отчёте владельцу; CI не запускался — commit/push не выполнялись.

## 4. Остаток

`OD-023` open; RM-GOV-010 (owner/RACI); PENDING-ID journeys; walkthrough. Codex: независимая
проверка r425.
