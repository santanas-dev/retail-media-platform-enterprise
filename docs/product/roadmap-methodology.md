# Методика honest-процентов готовности

<!-- Выделено из `docs/product/roadmap.md` при canonical cutover RM-GOV-005, 2026-08-26. Содержание перенесено без изменений; изменился только адрес. Последовательность работ живёт в `docs/product/roadmap.yaml`, производные представления — в `docs/product/generated/`. -->


Единый процент готовности не выводится намеренно — измерения несоизмеримы.

| Измерение | Значение | Методика |
|---|---|---|
| Функциональная реализация | **91%** | 53 reachable / 58 registry |
| CI-закрепление UI-journey | **74%** | 43 в блокирующем UI-smoke / 58 |
| Готовность локального стенда | **OPERATIONAL**, browser-verified **9%** | стенд работает; 4 journey из 43 UI пройдены реальным браузером |
| Business journey completeness | **~60%** | 4 из 6 ролей замыкаются до-плеерно; КСО и отчёт рекламодателя не замкнуты |
| UX maturity | **низкая** | 9 открытых дефектов, 4 из них high; advertiser-web не аудирован; walkthrough 0 |
| Pilot readiness | **~25%** | tooling готов, host preflight `NEEDS_OWNER_INPUT`, 15 owner inputs открыты |
| Production readiness | **0% — NO-GO** | нет TLS/CD/мониторинга/бэкапа прода; deployed SHA UNKNOWN |

> **53/58 — это не 91% готовности продукта.** Это доля функций, достижимых в UI.
