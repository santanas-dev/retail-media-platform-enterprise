# `docs/audit/` — аудиты и предложения

> **Этот каталог — НЕ канон.** Файлы здесь фиксируют наблюдения на конкретный SHA и предложения,
> ожидающие решения владельца. Они **не переопределяют** Tier 1–2 индекса источников истины
> `AGENTS.md` и не задают очерёдность работ.
>
> Регистрация каталога в индексе `AGENTS.md` **предложена, но ещё не выполнена** — см.
> `2026-08-26-doc-governance-proposal.md`, П6.

## Зачем каталог отдельный

Аудит привязан к SHA и устаревает со следующим коммитом. Канон (`docs/product/`,
`docs/architecture/`, `docs/00-source-of-truth/`) описывает, как система устроена **сейчас**.
Если положить их рядом, читающий агент примет устаревшее наблюдение за действующее правило —
в репозитории уже есть такие случаи (`Status: active` от 11–14 июля на закрытых работах).

## Правила

1. **Шапка обязательна.** Первое в файле после заголовка — блок статуса: тип, SHA, дата,
   предмет, автор, число открытых находок, поле «Отменён». Образец — любой файл этого каталога.
2. **Аудит не редактируется после публикации.** Это запись. Появилась новая оценка — новый
   датированный файл, а в старом проставляется `Отменён: <файл>`.
3. **План — предложение**, пока в шапке стоит «Ожидает решения владельца». После утверждения
   пункты уходят в канонический документ очерёдности, а план получает
   `Отменён: перенесён в <документ>`.
4. **Исполняемый статус находок — в `PROJECT_STATE.md`**, не здесь. Аудит — доказательство,
   `PROJECT_STATE.md` — трекер. Находка, живущая только здесь, выпадает из цикла чтения агентов.
5. **Имя файла:** `YYYY-MM-DD-<тема>.md`. Дата — когда снято наблюдение.
6. **При конфликте с каноном побеждает канон.** Расхождение сообщается владельцу, а не
   разрешается агентом самостоятельно (`CLAUDE.md`: «A contradiction between sources means STOP»).

## Содержимое

| Файл | Тип | Снято на | Статус |
|---|---|---|---|
| `2026-08-26-code-and-security.md` | аудит | `develop @ 2b935bb` | 4 открытые находки |
| `2026-08-26-canon-and-architecture.md` | аудит | `develop @ 2b935bb` | 3 🔴 · 5 🟡 · 3 🟢 · 5 разрывов ТЗ |
| `2026-08-26-work-plan.md` | план (предложение) | `develop @ 2b935bb` | ожидает решения владельца |
| `2026-08-26-doc-governance-proposal.md` | предложение | `develop @ 2b935bb` | ожидает решения владельца |
| `2026-08-26-codex-independent-audit.md` | независимый audit addendum | `develop @ 2b935bb` | 8 дополнительных находок + уточнение приоритетов |
| `2026-08-26-codex-work-plan-addendum.md` | дополнение к плану | `develop @ 2b935bb` | ожидает решения владельца |
| `2026-08-26-claude-response-to-codex.md` | ответ на ревью | `develop @ 2b935bb` | 4 корректировки приняты · 3 возражения · 1 новая улика |
| `2026-08-26-operator-scope-experiment.md` | эксперимент | `develop @ 2b935bb` | C3 подтверждена поведенчески: `operator` и `analyst` видят 0 строк |
| `2026-08-26-codex-claude-convergence.md` | архитектурная сверка / decision package | `develop @ 2b935bb` | ожидает 4 решения владельца |
| `2026-08-26-roadmap-governance-audit.md` | аудит technical/business roadmap + формат/RACI | `develop @ 2b935bb` | 8 находок; ожидает сверки Claude и 5 решений владельца |
| `2026-08-26-claude-reconciliation.md` | reconciliation | `develop @ 2b935bb` | R1–R8 подтверждены · возражений нет · 2 счётчика расходятся · +4 наблюдения |
| `2026-08-26-roadmap-task-breakdown-draft.md` | task breakdown (proposal) | `develop @ 2b935bb` | 40 задач; ожидает feasibility Claude и утверждения порядка владельцем |
| `2026-08-26-claude-task-breakdown-reconciliation.md` | feasibility reconciliation | `develop @ 2b935bb` | 40 задач · граф ацикличен · 11 находок не названы · 10 поправок |
| `2026-08-26-roadmap-task-breakdown-final-candidate.md` | финальный кандидат task breakdown | `develop @ 2b935bb` | 42 задачи; 8 решений владельца учтены; ожидает final feasibility и утверждения очереди |
| `2026-08-26-claude-final-feasibility-prompt.md` | handoff-промт Claude | `develop @ 2b935bb` | только read-only feasibility; реализация запрещена |
| `2026-08-26-claude-final-feasibility-reconciliation.md` | финальная feasibility | `develop @ 2b935bb` | НЕ ACCEPT — 3 блокирующие поправки (B-1…B-3), остальное принято |
| `2026-08-26-roadmap-task-breakdown-final-candidate-v2.md` | финальная редакция task breakdown | `develop @ 2b935bb` | B-1/B-2 приняты, B-3 уточнена; 42 задачи; ожидает final ACCEPT Claude |
| `2026-08-26-claude-final-acceptance-prompt-v2.md` | handoff-промт Claude | `develop @ 2b935bb` | только финальный ACCEPT/доказанный блокер; реализация запрещена |
| `2026-08-26-claude-final-acceptance-v2.md` | финальный acceptance | `develop @ 2b935bb` | **ACCEPT** — блокеров нет; 42/42 ID, DAG ацикличен, гейты на месте |
| `2026-08-26-session-handoff.md` | передача состояния | `develop @ 2b935bb` | RM-GOV-001 ACCEPT · RM-GOV-002 ждёт ACCEPT · далее RM-GOV-003 |

## Чего здесь не бывает

- Изменений канона. Аудит **описывает** расхождение, а не устраняет его.
- Статусов функций. Их источник — `docs/product/feature-registry.yaml`.
- Очерёдности работ. Её источник — канонический roadmap
  (какой именно — открытый вопрос A2, см. предложение, раздел 4).
| `2026-08-26-open-legacy-items-triage.md` | triage | 19 открытых legacy-пунктов → 13 тем: 2 закрыты, 11 сведены в OD-009…OD-015 |
| `2026-08-27-claude-review-tz-v2.6-draft-r413.md` | ревью драфта ТЗ v2.6 (r413) | `develop @ b21174f` + рабочее дерево | отменён → ed2 |
| `2026-08-27-codex-verdict-claude-tz-r413.md` | вердикт Codex по ревью Claude | `develop @ b21174f` | 7 подтверждено, 1 исправление, 4 решения владельца |
| `2026-08-27-claude-amendment-tz-r413-verdict-check.md` | поправка + проверка вердикта | `develop @ b21174f` + рабочее дерево | отменён → ed2 |
| `2026-08-27-codex-verdict-claude-amendment-tz-r413.md` | вердикт Codex №2 | `develop @ b21174f` | 5 замечаний к поправке |
| `2026-08-27-claude-review-tz-v2.6-draft-r413-ed2.md` | ревью r413, редакция 2 (консолидированная) | `develop @ b21174f` + рабочее дерево | отменён → ed3 |
| `2026-08-27-codex-verdict-claude-review-r413-ed2.md` | вердикт Codex №3 (на ed2) | `develop @ b21174f` | PARTIAL ACCEPT, 4 остатка |
| `2026-08-27-claude-review-tz-v2.6-draft-r414-ed3.md` | ревью r414, редакция 3 | `develop @ b21174f` + рабочее дерево | 26 расхождений r413; 12 закрыто в r414; 11 остатков; 5 решений |
| `2026-08-26-tz-v2.6-design-draft.md` | immutable redirect: драфт перенесён в `docs/product/requirements/tz-v2.6-draft.md` | `r421` ACCEPT → OD-017 | содержание ACCEPTED 2026-08-28; статус документа DRAFT до артефактов AG |
| `2026-08-27-codex-response-claude-r414-ed3.md` | ответ Codex на ed3 | `develop @ b21174f` + r415 | 10 принято, 1 оспорено; 4 текстовых коррекции |
| `2026-08-27-claude-verdict-r416.md` | вердикт по r416 и ответу Codex | `develop @ b21174f` + рабочее дерево | 10 подтверждено, 1 отозван; **решение: дорабатывать, не утверждать** — 4 блокера, план из 4 шагов |
| `2026-08-27-claude-full-review-tz-r416.md` | полное ревью r416 (сплошное чтение + код) | `develop @ b21174f` + рабочее дерево | 41 находка: 5 блокеров, 13 код, 4 источники, 9 внутренних, 5 форма; 4 новых решения владельца |
| `2026-08-27-codex-response-claude-full-review-r416.md` | ответ Codex + дельта draft r417 | `develop @ b21174f` + рабочее дерево | PARTIAL ACCEPT: факты исправлены; A5/D2/D8/D9 и часть формы оспорены; 4 pending DEC |
| `2026-08-27-codex-response-claude-full-review-r416.md` | ответ Codex на полное ревью | `develop @ b21174f` + r417 | PARTIAL ACCEPT; 20 закрыто в r417, DEC-023…026 |
| `2026-08-27-claude-review-r417-stability.md` | ревью дельты r417 + оценка стабильности | `develop @ b21174f` + рабочее дерево | отменён → final-verdict (счёт 26/26 неверен) |
| `2026-08-27-codex-final-consistency-review-r418.md` | независимая финальная сверка r418 | `develop @ b21174f` + рабочее дерево | PARTIAL ACCEPT; ADR-015/018/019 reconciled; 4 artifact blockers |
| `2026-08-28-claude-final-verdict-tz-r418.md` | окончательный вердикт Claude по r418 | `develop @ b21174f` + рабочее дерево | текст согласован; 2 счётчика и DEC-014 требуют r419 |
| `2026-08-28-codex-verdict-claude-r418.md` | проверка вердикта Claude | `develop @ b21174f` + рабочее дерево | PARTIAL ACCEPT; исправлено в r419: 101/53, DEC-014 owner decision |
| `2026-08-28-claude-confirmation-r419.md` | подтверждение r419 Claude | `develop @ b21174f` + рабочее дерево | текст подтверждён; следующий этап — A1–A4 и owner decisions |
| `2026-08-28-codex-verdict-claude-confirmation-r419.md` | проверка подтверждения Claude | `develop @ b21174f` + рабочее дерево | ACCEPT текста; stale handoff исправлен в r420 |
| `2026-08-28-codex-check-claude-r419-confirmation.md` | проверка подтверждения Claude r419 | `develop @ b21174f` + рабочее дерево | ACCEPT текста; stale AQ handoff исправлен в r421; AG artifacts уточнены |
| `2026-08-27-codex-final-consistency-review-r418.md` | финальная сверка Codex | `develop @ b21174f` + r418 | PARTIAL ACCEPT; 9 DEC закрыты каноном; заявлено 101 REQ |
| `2026-08-28-claude-final-verdict-tz-r418.md` | **окончательный вердикт** | `develop @ b21174f` + рабочее дерево | текст согласован; REVIEW→ACCEPTED после r419; APPROVED после 4 артефактов; 17 открытых DEC, 3 блокируют |
| `2026-08-28-codex-verdict-claude-r418.md` | вердикт Codex на финальный вердикт | `develop @ b21174f` + r419 | 101 REQ подтверждено; 53/101 без story; DEC-014 понижен |
| `2026-08-28-claude-confirmation-r419.md` | **подтверждение r419 + определение итоговой версии** | `develop @ b21174f` + рабочее дерево | текст согласован; цикл ревью закрыт; 4 условия итоговой версии |
| `2026-08-28-codex-verdict-claude-confirmation-r419.md` | Codex: ACCEPT текста r419 → r420 | `develop @ b21174f` + r420 | добавлен критерий полноты AG |
| `2026-08-28-tz-v2.6-consistency-reached-r420.md` | **согласованность драфта достигнута** | `develop @ b21174f` + рабочее дерево | цикл ревью закрыт обеими сторонами; 5 действий владельца; распределение AG |
