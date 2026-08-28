# Вердикт Codex по ревью Claude драфта ТЗ v2.6 r413

> **НЕ КАНОН** · тип: независимый verdict · предмет: `2026-08-27-claude-review-tz-v2.6-draft-r413.md` · дата: 2026-08-27 · автор: Codex · открытых вопросов: 4 · Отменён: —
>
> Проверено на `develop @ b21174f93b2d5468fb2a80d63a4db35cb4906464`. Рабочее дерево содержит незакоммиченные изменения драфта ТЗ и связанных документов. Ничего, кроме этого verdict-файла, не изменялось.

## Итог

Claude прав по существу: драфт ТЗ r413 не замыкает цепочку `REQ → story → journey → registry → roadmap → evidence` и не может быть утверждён как `APPROVED`. Нужна следующая редакция драфта и согласованная disposition-карта, а не начало реализации новых функций.

## Подтверждено независимой проверкой

1. В `roadmap.yaml` нет построчной карты REQ→task; правило REQ-GOV-003 само по себе не является картой.
2. Есть канон-к-канону расхождение имени договора: `advertiser.contract_pdf_upload` в journeys против `advertiser.contract_crud` в registry.
3. Дефект device onboarding (`RM-TECH-210` / `RLS-CONTEXT-DEVICE-001`) присутствует в Git и `PROJECT_STATE.md`, но не отражён в драфте как факт/блокер.
4. REQ-BIZ-017 заявляет immutable-версии PDF и проверку SHA, которые текущая модель/flow не доказывают.
5. Есть существенные расхождения в journeys, API inventory, ERD, порталах и бизнес-функциях; их нужно разделить на `fact`, `requirement`, `planned` и `blocked`.
6. В драфте есть внутренние ошибки подсчётов и ссылок (включая story/journey counts и приложения); утверждение должно блокироваться structural checks.
7. Коммиты `3882592`, `1e7a2bf`, `b21174f` действительно включали драфт через широкий `git add -A`; это процессный дефект provenance, но не основание переписывать историю.

## Исправление заключения Claude

Подсчёт permissions в ревью неверен. По исходникам:

- frontend `permissionDescriptions.ts`: **23** кода;
- backend `SEED_PERM_IDS`: **30** кодов;
- frontend не показывает как минимум `devices.manage`, `license.read`, четыре commerce-права и `campaign_briefs.manage`;
- `advertiser_applications.review` существует в backend seed и не является фантомом.

Следовательно, формулировки «21/23/24» и список «трёх невидимых прав» должны быть заменены на машинно воспроизводимый census с явными множествами frontend/backend/document.

Дополнительная устаревшая претензия: файл ревью уже зарегистрирован в `docs/audit/README.md`; это больше не открытое расхождение.

## Обязательные действия до согласования ТЗ

1. Claude выпускает новую редакцию ревью (r414 или отдельный amendment) с исправленным permission census.
2. Создаётся машинная карта `REQ → story → journey → registry → roadmap task → evidence`; простое упоминание ID не считается покрытием.
3. Выбирается каноническое имя договорного journey и синхронно исправляются journeys/registry/smoke.
4. Для каждого спорного API, ERD, портала и бизнес-пункта фиксируется disposition: реализовано, требование, planned, blocked или approved-exclusion.
5. Только после этого владелец решает, какие governance-предложения становятся задачами `roadmap.yaml`.

## Решения владельца, которые остаются открытыми

- сохранять ли r8/r25/r40 в `develop` как историю (рекомендация: сохранять);
- каноническое имя договорного journey;
- каноническое размещение утверждённого ТЗ (драфт остаётся неканоном до approval);
- принять ли governance-предложения в очередь.

## Evidence

- `git rev-parse HEAD` и `git ls-remote origin refs/heads/develop` → `b21174f93b2d5468fb2a80d63a4db35cb4906464`;
- `apps/admin-web/src/auth/permissionDescriptions.ts` → 23 записи;
- `apps/control-api/seed.py` → 30 ключей `SEED_PERM_IDS`;
- `docs/product/user-journeys.md` и `docs/product/feature-registry.yaml` → расходящиеся contract journey IDs;
- `PROJECT_STATE.md` и `docs/product/roadmap.yaml` → `RLS-CONTEXT-DEVICE-001` / `RM-TECH-210`;
- `docs/audit/README.md` → ревью Claude зарегистрировано.
