# Codex — независимая проверка A1

Статус: **ACCEPT с обязательной поправкой до commit**.

## Подтверждено

- `docs/product/requirements-traceability.yaml` содержит 101 REQ и 69 SC; schema/self-test
  и локальные governance-проверки заявлены зелёными.
- 23 PENDING-ID и 51 REQ без roadmap task корректно остаются открытыми входами для A3.
- 170 TBD owner полей закономерно блокируют `APPROVED`, но не обязаны блокировать локальную
  проверку A1.

## Обязательная поправка

В записи A1 (§1) одновременно указано «69 `SC-*`» и в строке coverage «SC — у 71».
Фактический YAML содержит `scenarios: 69`. До commit отчёт должен использовать одно число:
69.

## Методологический риск

`delivery_status: in_progress` нельзя выводить только из `feature-registry: reachable` или
наличия candidate-теста: registry описывает доступность journey, а не delivery-статус
требования. Нужна явная mapping-таблица/правило, либо такие записи должны быть `planned`/
`candidate` до доказанного roadmap delivery. Иначе A1 создаёт новый overclaim статуса.

После исправления числа и явной фиксации правила статусов A1 можно принимать и разрешать
commit/push; A3 должен закрыть 51 task gap, но не повышать `done` без evidence.
