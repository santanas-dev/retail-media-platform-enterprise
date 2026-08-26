# Финальный кандидат task breakdown — редакция v2

> ## ⚠️ НЕ КАНОН — очередь ещё не разрешена к исполнению
>
> | | |
> |---|---|
> | **Тип** | Архитектурная редакция final candidate |
> | **База** | `develop @ 2b935bb` = `origin/develop @ 2b935bb` |
> | **Дата** | 2026-08-26 |
> | **Автор** | Codex, архитектор/ревьюер |
> | **Основание** | final candidate v1 + reconciliation Claude B-1…B-3 + решение владельца продолжить |
> | **Статус** | Ожидает только финального `ACCEPT` Claude и утверждения очереди владельцем |
> | **Состав** | 42 задачи; IDs, kind, зависимости, этапы и 8 решений владельца не изменены |
> | **Изменения продукта/канона/стенда** | Нет |
> | **Отменён** | — |

## 1. Как читать редакцию

Полный task breakdown задан файлом
`2026-08-26-roadmap-task-breakdown-final-candidate.md` с тремя обязательными заменами ниже.
Других изменений нет. При расхождении формулировок эта редакция v2 имеет приоритет только внутри
не-канонического proposal; она не переопределяет `AGENTS.md`, ADR, roadmap или PROJECT_STATE.

## 2. B-1 принят — initial `roadmap.yaml`

Приёмка `RM-GOV-002` заменяется на:

> disposition для 93 technical items, 13 SECTION и 57 business rows; 5 blocked features имеют
> gap/unblock; создан initial `docs/product/roadmap.yaml`, валидный по schema из `RM-GOV-001`,
> без overclaim: `delivery_status=done` запрещён без достаточных `evidence_refs`; счётчики
> воспроизводимы именованным скриптом.

Следствие: `RM-GOV-003` получает существующий валидный input, а `RM-GOV-005` выполняет cutover
только после детерминированной генерации из него.

## 3. B-2 принят — согласование с ADR-018

Приёмка `RM-STAB-003` заменяется на:

> mini-design фиксирует persona→permissions→scope и единственные bypass-роли из §1.3;
> ADR-018 явно дополнен либо superseded новым ADR в части retailer scope как самостоятельного
> источника scope, а не только `retailer_scope_ids`, производного от advertiser membership;
> решение ссылается на утверждённое ограничение §1.3 и
> `2026-08-26-operator-scope-experiment.md`; владелец принимает точную модель до кода.

Это не объявляет весь ADR-018 ошибочным: его tenant boundary и двухуровневая RLS сохраняются,
если новый ADR явно не изменит их.

## 4. B-3 принят с архитектурным уточнением — guard orchestration

В §2 final candidate добавляется правило:

> `RM-GOV-004` владеет единственной CI orchestration entrypoint для roadmap governance.
> `RM-GOV-001` добавляет schema-validation, `RM-GOV-006` — doc-consistency,
> `RM-STAB-006` — journey-spec, `RM-STAB-005` — smoke-semantics как независимо вызываемые
> модули общего guard. Модули могут иметь собственные targeted CLI/tests, но не создают
> конкурирующие обязательные CI gates и не дублируют чтение/интерпретацию одного правила.

Утверждение Claude о четырёх уже неизбежных CI jobs не считается доказанным: кандидат их не
предписывал. Исправляется неоднозначность владения, а не подтверждённый дефект реализации.

## 5. Неизменившиеся gates

- Порядок: `G → E0 → S → U → отдельно утверждаемые branches`.
- Excel остаётся generated projection: Claude меняет YAML/evidence, generator пересобирает XLSX,
  Codex проверяет, владелец утверждает бизнес-приоритет и итоговые gates.
- Код, migration application, deployment, merge, release и старт `RM-GOV-001` пока запрещены.
- После `ACCEPT` Claude владелец отдельно утверждает очередь и отдельно разрешает первую задачу.
