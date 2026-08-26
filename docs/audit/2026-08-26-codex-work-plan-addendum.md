# Дополнение Codex к плану работ по аудиту 2026-08-26

> ## ⚠️ НЕ КАНОН — предложение архитектора/ревьюера
>
> | | |
> |---|---|
> | **Основан на** | `develop @ 2b935bb`, независимый audit addendum |
> | **Статус** | Ожидает решения владельца |
> | **Изменяет roadmap** | Нет |
> | **Дата** | 2026-08-26 |
> | **Автор** | Codex, архитектор/ревьюер |
> | **Отменён** | — |

Документ дополняет, но не переписывает `2026-08-26-work-plan.md`. Оценки времени ориентировочны;
внешние действия, deployment, merge, release и protected boundaries не разрешаются.

## CA-1 · Восстановить валидность UI-smoke доказательств 🔴 P0 · 6–10 ч

**Scope:** только test infrastructure и затронутые smoke; без изменения продуктовой логики.

1. Убрать direct API setup из `audit.view`: создать проверяемое событие через UI-клики либо
   отделить подготовку данных в явно не-UI fixture, если владелец сначала изменит Done Gate.
2. Убрать `time.sleep`, reload/retry loop и broad `except Exception`.
3. В `self.campaign_view` возвращаться к списку видимой кнопкой/ссылкой, не deep-link `goto`.
4. Для invite acceptance явно решить: `/accept-invite/{token}` — разрешённая публичная entry-
   страница или journey должен получать ссылку через видимое действие.
5. Добавить AST/static guard: запрет `httpx/requests`, `sleep`, retry loops и `goto` вне
   разрешённого entry list в `tests/ui-smoke/test_uismoke__*.py`.

**Приёмка:** tamper-тест на каждое правило; исправленные smoke зелёные first-attempt; затем
полный CI subset и roadmap guard. До этого не повышать readiness по затронутым journeys.

## CA-2 · Закрыть journey coverage и actor/RBAC contract 🔴 P0/P1 · решение + 8–16 ч

**Сначала решение владельца:** продуктовые actors являются отдельными backend roles или
personas, отображаемыми на существующие permission bundles.

1. Добавить полноценные journey sections для 13 отсутствующих UI IDs.
2. Для каждого UI journey фиксировать actor, permission codes, entry page, `Happy-path: N
   шагов`, visible next-step, selectors и negative permission expectation.
3. Удалить устаревшие `Сейчас/Next` из нормативной части либо вынести их в датированный history.
4. Расширить guard: registry UI ID обязан иметь структурированный journey; reachable требует
   валидный smoke и actor proof.
5. Критические journeys прогонять не только под break-glass: positive intended-permission и
   negative missing-permission proof.

**Приёмка:** 45/45 UI entries представлены в journey-спецификации; 0 неизвестных role codes;
guard красный при удалении journey/actor proof и зелёный после возврата.

## CA-3 · Синхронизировать CI-контракт 🟡 P1 · 1–2 ч

Выбрать и записать фактическое решение: UI-smoke blocking или non-blocking. Текущий workflow и
roadmap реализуют blocking-вариант; если он остаётся, исправить пункт 6 Done Gate в `AGENTS.md`.
Изменение репозиторского контракта требует явного решения владельца.

**Приёмка:** AGENTS, CLAUDE, workflow и roadmap используют одну формулировку; тест release-gate
доказывает выбранную политику.

## CA-4 · Сделать roadmap-метрики воспроизводимыми 🟡 P1 · 3–5 ч

1. Исправить подпись 53/58: это registry reachability, а не UI reachability.
2. Либо определить формулы `pilot readiness`/`business completeness`, либо заменить проценты
   категориальными статусами с открытыми gates.
3. Явно зарегистрировать `roadmap.md` в Sources of Truth как sequencing/maturity view либо
   перенести его роль в уже индексированный `pre-pilot-journey-plan.md`.
4. Guard должен проверять обе публикуемые roadmap-проекции либо одна должна генерироваться из
   другой без ручного дублирования.

**Приёмка:** любая цифра пересчитывается одной командой из указанных источников; tamper вызывает
красный guard; нет двух self-declared owners одного измерения.

## CA-5 · Карантин устаревших mutator scripts 🟡 P1 · 2–4 ч

Минимальный безопасный вариант: перенести три one-off скрипта в явно historical каталог или
добавить fail-closed banner/exit, запрещающий запуск. Предпочтительный вариант: один
поддерживаемый updater с repository-relative path, schema validation, dry-run и backup/diff.

**Приёмка:** ни один штатный скрипт не может молча переписать 11-колоночный XLSX старой
5-колоночной схемой; тест запускается на временной копии и проверяет сохранение листов/колонок.

## CA-6 · Canon freshness overlay 🟡 P1 · 3–5 ч

1. Обновить requirements README: ADR-018 Accepted/Implemented, advertiser-web partial, Hermes
   retired; оригинальные DOCX не редактировать.
2. Добавить ADR-018/019 и реально активные domain documents в architecture index.
3. В historical pre-pilot plan убрать активные `Next`/blocked assertions либо пометить каждый
   старый status block датой и ссылкой на registry.
4. Исправить нестандартный header ADR-018 и добавить format check.

**Приёмка:** grep по активным индексам не выдаёт `ADR-018 proposed`, Hermes как активного агента
или `KSO-ENV-001 next`; status truth остаётся только в PROJECT_STATE/registry.

## Изменение приоритетов исходного work plan

| Исходный пункт | Решение Codex |
|---|---|
| WP-3 + WP-4 behavioral fidelity | Оставить первым implementation block вместе с CA-1/CA-2 |
| WP-1 truth hierarchy | P1 governance; требуется решение владельца, не runtime hotfix |
| WP-2 Ed25519/HMAC | Decision сейчас; реализация обязательна до Wave 3/device pilot, не раньше UX автоматически |
| WP-5 SLO | Зафиксировать уже принятые цифры как objectives; измерение — до pilot/production claim |
| WP-6 hygiene | Расширить CA-3…CA-6 |
| WP-7…WP-12 | Не ставить впереди утверждённого UX-first порядка без owner override |

## Рекомендуемая последовательность

`CA-1` → `WP-3/WP-4` → owner decision по `CA-2` → `CA-2` → `CA-3/CA-4` → `CA-5/CA-6` →
вернуться к `PORTAL-UX-POLISH-001A3` или переутвердить порядок владельцем.

Причина паузы A3 — не новый функциональный приоритет, а восстановление доверия к тем самым
journey/smoke gates, которыми A3 должен доказываться.
