# Codex — независимый аудит канонического ТЗ v2.6 после RM-GOV-009

Статус: **доработано; требуется пересборка traceability**.

Проверено: текущий `origin/develop` — `cbffb3b`; драфт в `docs/product/requirements/`
имеет r422; roadmap содержит 38 owner decisions и 107 задач.

## Найденное и исправленное

- `roadmap.yaml` уже фиксировал DEC-022/024/026 как approved OD-018/019/020, тогда как
  §29 и Дополнение I драфта оставляли их `PENDING-OD` и описывали только рекомендации.
- В драфте это исправлено в редакции **r423**: добавлены выбранные варианты, даты,
  обязательные implementation/ADR-amendment follow-ups и ссылки на OD.
- Устаревшая metadata-ссылка r421 заменена на parent `origin/develop cbffb3b`.
- Sidecar SHA обновлён и должен быть проверен перед следующим commit.

## Оставшийся обязательный шаг

`docs/product/requirements-traceability.yaml` всё ещё pinned на `draft-2026-08-28-r422`.
После r423 его нужно пересобрать, иначе `DRAFT-REVISION-DRIFT` закономерно должен блокировать
CI. Только после пересборки следует повторить schema/consistency/governance checks.

Итог: это не новая функциональная недостача ТЗ, а исправленная синхронизация decision
registry. До пересборки A1 и нового CI документ не считать полностью согласованным.
