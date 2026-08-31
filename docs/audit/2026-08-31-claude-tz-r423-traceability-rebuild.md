# Claude — проверка r423 (Codex) и пересборка карты требований на r423

Статус: **применено в рабочем дереве; не закоммичено** (по указанию владельца 2026-08-31).
База: `origin/develop @ cbffb3b` + локальные правки Codex (запись
`2026-08-31-codex-independent-audit-tz-r423.md`).

## 1. Что изменил Codex (r423)

| Файл | Суть |
|---|---|
| `docs/product/requirements/tz-v2.6-draft.md` | Revision `r422 → r423`; parent → `origin/develop cbffb3b`; changelog r423; §29 строки DEC-022/024/026 — выбранные варианты и ссылки на OD-018/019/020; Дополнение I — колонка источника `PENDING-OD` → `OD-018/019/020`; хвост AQ — историческая запись про r419 |
| `docs/product/requirements/tz-v2.6-draft.sha256` | `70f097c7… → 585a9069…` — **совпадает с байтами файла** (проверено `sha256sum`) |
| `docs/audit/README.md` | строка записи Codex |

Инварианты r423 (метод записи r420, эталон r419): REQ §25 **101**, AP stories **41**, AC **326**;
`sha(§6) c81660073d53`, `sha(§25) 047269764cd5`, `sha(§26) 87ad03f6f972`, `sha(AP) 81f6af86dcda` —
**все равны r419**. Изменились только §29 и Дополнение I (ненормативные для карты). Слово
`PENDING-OD` в драфте осталось единственный раз — в changelog r423 как описание того, что снято.

## 2. Синхронизация DEC-022/024/026 ↔ OD-018/019/020 — подтверждена

| DEC | OD (roadmap) | §29 драфта | Дополнение I | Содержание совпадает |
|---|---|---|---|---|
| DEC-022 | OD-018 approved 2026-08-28 | «approved OD-018: только §3.1 delivery/priority engine; иное — новое решение» | `OD-018, v2.6 addendum §0.3/§8.3` | да — OD-018: только §3.1 (competitive separation), остальное запрещено без нового решения |
| DEC-024 | OD-019 approved 2026-08-28 | «approved OD-019: HTTP 200 batch, per-event `duplicate` + код 409 в теле, без повторного учёта; amendment ADR-017 + behavioral evidence» | `OD-019, ADR-017` | да — OD-019 слово в слово по семантике |
| DEC-026 | OD-020 approved 2026-08-28 | «approved OD-020: `draft → cancelled`; `confirmed` — только reversal/compensation; код и тесты приводятся» | `OD-020, commerce lifecycle` | да — OD-020: то же + `_ORDER_TRANSITIONS` отдельной задачей |

Guard `decisions`: 27 DEC §29 = 27 DEC Дополнения I = 27 alias в `owner_decisions`, чисто.

## 3. Пересборка `requirements-traceability.yaml` на r423

Состав REQ/SC/story не менялся (§25/§26/AP байт-в-байт с r419), поэтому пересборка — это
перепривязка документа, а не перегенерация содержимого:

- `document.revision: draft-2026-08-28-r422 → draft-2026-08-31-r423`;
- `document.sha256: 70f097c7… → 585a9069…` (= sidecar = байты драфта);
- `source` у 101 REQ и 69 SC: `draft-2026-08-28-r422 §25 → draft-2026-08-31-r423 §25` (171 ссылка);
- комментарий в шапке: r423 = r421 (ACCEPT OD-017) + пути (r422) + синхронизация §29/Доп. I.
- Не тронуты: `status`/`accepted_by`/`accepted_on`, статусы, owner, evidence, roadmap_ids.

Сверка после пересборки: REQ драфт↔карта **101/101** (расхождений 0), story_ids ⊆ AP (0 вне AP),
без roadmap_ids **0**, pending journeys 23 (8 awaiting_owner), TBD owner **170**, evidence
306 candidate / 0 verified — как до пересборки.

## 4. Guard: закрыт пробел, который вскрыл r423

- Tamper-кейс «карта привязана к другой ревизии драфта» держал литерал `` `draft-2026-08-28-r422` ``
  и после r423 стал бы **инертным** (self-test красный по детектору инертности). Заменён на
  `_bump_draft_revision` — читает текущий `rN` и поднимает его.
- Новые правила модуля `req`: `DRAFT-SHA-DRIFT` (`document.sha256` ≠ sha256 байтов драфта),
  `SIDECAR-DRIFT` / `SIDECAR-MISSING` (sidecar ≠ байты драфта). До этого guard сверял только
  `revision`, и драфт можно было править «под тем же r», не трогая карту — Codex просил проверять
  SHA перед commit вручную; теперь это делает гейт.
- Sidecar добавлен в `SANDBOX_PATHS`; два новых tamper-кейса (правка драфта под тем же revision;
  испорченный sidecar). Self-test **53/53**, 11 измерений.

## 5. Прогоны (рабочее дерево)

| Проверка | Результат |
|---|---|
| `scripts/ci/check-roadmap-schema.py` | PASS |
| `scripts/roadmap-consistency-check.py` | 0 violations |
| `scripts/ci/roadmap-generate.py --check` | CLEAN |
| `scripts/ci/roadmap-governance-guard.py` | PASS — все 9 модулей чисты (req: REQ 101 / SC 69 / без roadmap_ids 0; TBD 170) |
| `--self-test` | 53/53 |

CI не запускался — нет commit/push.

## 6. Оставшиеся расхождения (не блокируют CI)

1. **Дополнение I, колонка «Источник»** — у 16 DEC нет ссылки на свой OD из `owner_decisions`
   (все OD-021…036, кроме OD-018/019/020 и старых OD-002/005/008/009/010/011/014):
   DEC-001→OD-021, DEC-002→OD-022, DEC-005→OD-023, DEC-010→OD-024, DEC-012→OD-025,
   DEC-013→OD-026, DEC-014→OD-027, DEC-015→OD-028, DEC-016→OD-029, DEC-017→OD-030,
   DEC-018→OD-031, DEC-019→OD-032, DEC-020→OD-033, DEC-021→OD-034, DEC-023→OD-035,
   DEC-025→OD-036. Статусы при этом семантически согласованы (approved DEC-002/021/023/025
   помечены approved/«закрыто», остальные — open). Косметика для r424; guard `decisions`
   держит связь по alias, а не по тексту колонки.
2. `OD-023` (DEC-005, владелец master-данных) — open; цепочка RM-TECH-280…285 blocked.
3. `document.status: ACCEPTED` по OD-017 относится к содержанию r421; r422/r423 нормативных
   разделов не меняли (SHA §6/§25/§26/AP = r419) — отдельный ACCEPT не требуется, но
   при первой нормативной правке потребуется новый OD.
4. r423 не закоммичен: после commit/push потребуется CI-прогон как evidence.
