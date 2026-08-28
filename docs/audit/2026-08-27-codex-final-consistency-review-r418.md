# Codex — финальная независимая сверка ТЗ v2.6 r418

Статус: **PARTIAL ACCEPT / DRAFT**, до состояния согласованности ещё не дошло.

## Итог

- Claude корректно закрыл большую часть формальных замечаний r417, но его вывод «26/26 решений открыты» отклонён: принятые ADR/OD и продуктовые решения уже закрывают часть вопросов.
- В r418 исправлены пропущенные авторитетные решения: ADR-015 (persisted `scheduled` и полный lifecycle), ADR-018 (двухуровневый retailer/advertiser scope), ADR-019 (Orchestrator/Adapter только после второго реального канала), ADR-002/OD-002 и утверждённые SLA/retention/scale defaults.
- Каталог содержит 101 уникальное REQ (88 baseline + 11 V26 + 2 registry-derived). 41 story; 53 REQ пока не имеют story/scenario mapping — это реальный traceability gap, а не повод объявлять ТЗ покрытым.
- Исправлены `inventory.simulate`, несоответствие seed-ролей каноническим ролям, rejected→draft revision, неверные candidate-ID `RM-V26-*` (теперь `CAND-V26-*`, не roadmap IDs).

## Что остаётся до APPROVED

1. Машинный `requirements-traceability.yaml`: каждый REQ → story/scenario → task/decision → evidence.
2. Зарегистрированные SC-контракты для 53 технических/security/ops/governance REQ, включая selectors, smoke и operator walkthrough там, где применимо.
3. Единый decision/roadmap cutover с owner status; `CAND-V26-*` можно переносить только после явного ACCEPT.
4. Разбор доказуемых prerequisites: price/SKU master, sales reference и lift methodology, audience/privacy, dynamic binding/rendition, второй реальный канал.

## Вердикт по ключевым спорным пунктам

- Lifecycle: требование не переписывать под текущий код; реализация должна соответствовать ADR-015 либо нужен формальный amendment.
- Tenant model: новый tenant ADR не нужен, проверяется реализация ADR-018 и RLS.
- Orchestrator: до второго канала отдельный mock/orchestrator не добавлять.
- Решения владельца: открыты только вопросы, явно отмеченные в OD/DEC (включая OD-008…015 и DEC-022/024/026/027); принятые решения не переоткрываются.

Изменён только драфт ТЗ и audit-артефакты; код, roadmap.yaml, registry и канон не изменялись. Следующий шаг — передать r418 Claude на повторную проверку, затем согласовать traceability-пакет и только после этого переводить ТЗ в состояние согласованности.
