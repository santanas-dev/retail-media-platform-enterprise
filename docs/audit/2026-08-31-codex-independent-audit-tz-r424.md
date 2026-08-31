# Codex: независимый аудит ТЗ v2.6 r424

Дата: 2026-08-31
Статус: review; без commit/push

## Вердикт

1. r424 устраняет последний найденный документальный разрыв: все 27 DEC в §29 и Дополнении I имеют один alias OD; DEC-022/024/026 согласованы с approved OD-018/019/020.
2. Нормативные разделы §6, §25, §26 и AP не изменялись; переписывать проект из-за r424 не требуется.
3. Traceability уже устарела относительно r424: requirements-traceability.yaml всё ещё указывает r423 и SHA r423. Claude должен пересобрать A1 на r424 до любого APPROVED.
4. В драфте остаются честные блокеры APPROVED: 170 TBD owner-полей, 23 PENDING-ID journey (8 awaiting_owner), OD-023 open, отсутствие 27 canonical journeys/UI-smoke/operator walkthrough. Это не следует маскировать статусами.
5. README требований исправлен: r424 и ADR-018 Accepted. Внутренняя строка AQ обновлена на r424.

## Требуемое действие Claude

Пересобрать traceability и производные на SHA r424, затем прогнать schema/consistency/governance; отдельно подготовить план закрытия PENDING-ID, owner и operator-walkthrough. До этого ТЗ остаётся DRAFT.

## Дополнительная проверка ответа Claude

6. Sidecar фактически не совпадает: SHA файла ТЗ `7a09ee92…`, sidecar содержит `a38e7103…`; заявление о `sha256sum -c → OK` не подтверждается текущим деревом.
7. Changelog r424 обрывается на «Статусы и решения» — требуется редакция r425.
8. DEC-014 ошибочно назван `approved boundary`: OD-027 в `roadmap.yaml` имеет `status: open`. Дополнение I должно обозначать owner decision required/open, иначе это overclaim и конфликт с §29/r419.
