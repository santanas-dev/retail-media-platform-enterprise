# Промт Claude Code: финальная feasibility-проверка roadmap breakdown

Работай по `AGENTS.md` как единственный implementation agent, но **ничего не реализуй и не меняй**.
Прочитай только `docs/audit/2026-08-26-roadmap-task-breakdown-final-candidate.md`, свой
`2026-08-26-claude-task-breakdown-reconciliation.md` и точечно затронутые канонические секции.
Проверь на `develop/origin/develop`: 42 ID без дублей, ацикличность и полноту зависимостей,
coherent slicing одним агентом, file-overlap, проверяемость каждой приёмки, protected/external
owner gates и порядок `G → E0 → S → U → branches`. Не пересматривай восемь уже утверждённых
решений владельца. Не предлагай код и не меняй roadmap/канон/стенд. Запиши отдельный immutable
reconciliation-файл в `docs/audit/`: `ACCEPT` либо только конкретные блокирующие поправки с ID,
доказательством и точной заменой формулировки. Отчёт владельцу — не более 10 строк.
