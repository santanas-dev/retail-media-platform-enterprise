# Независимый аудит Codex — дополнение к аудиту 2026-08-26

> ## ⚠️ НЕ КАНОН — независимое ревью на момент времени
>
> | | |
> |---|---|
> | **Тип** | Аудит / review addendum |
> | **Снято на** | `develop @ 2b935bb980028a3e67db51718377836bb6242da9` |
> | **Дата** | 2026-08-26 |
> | **Автор** | Codex, архитектор/ревьюер |
> | **Изменения продукта** | Нет |
> | **Открытых находок** | 8: 2 🔴 · 5 🟡 · 1 🟢 |
> | **Отменён** | — |
> | **Назначение** | Независимая сверка аудитов Claude Code с Git, кодом, тестами, CI, ТЗ, ADR, journeys и roadmap |

Этот документ не меняет статусы функций, порядок работ или решения владельца. Существующие
аудиты Claude Code не редактировались: ниже отдельно зафиксированы подтверждения, уточнения и
новые находки.

## 1. Проверенная база

- Локальный `HEAD` совпал с live `origin/develop`: `2b935bb980028a3e67db51718377836bb6242da9`.
- GitHub Actions run `32952474953` для этого SHA завершён `success`; в нём зелёные unit,
  frontend, behavioral PostgreSQL, UI-smoke, roadmap, backup/restore, rollback и release gate.
- `python3 scripts/roadmap-consistency-check.py --strict`: 58 registry entries, 38 smoke-
  функций, 57 строк business-roadmap, 0 нарушений по текущим правилам guard.
- `python3 scripts/ci/check-import-boundaries.py`: все границы ADR-014 чистые.
- Узкий независимый прогон contract/security/transaction/import tests: `110 passed`, одно
  предупреждение о deprecated связке Starlette TestClient/httpx.
- Проиндексирована вся документация; первичные требования, актуальные product-документы,
  19 ADR, DOCX v2.6 (176 абзацев), оба листа XLSX, runbooks и исполняемый CI проверены точечно
  по заявленным контрактам и найденным расхождениям.
- Проверка относительных Markdown-ссылок по `docs/**/*.md`: 0 битых ссылок.

## 2. Сопоставление с аудитами Claude Code

### Подтверждено

1. `BEHAVIORAL-ENV-CONTRACT-001` подтверждается кодом: один env-key потребляется и как
   SQLAlchemy async URL, и как raw asyncpg DSN.
2. `BEHAVIORAL-ADMIN-MASK-001` подтверждается кодом: общий behavioral `get_db` начинает
   request-сессию с `app.rmp_is_admin=true`; строгая фикстура локальна одному файлу.
3. `LICENSE-PEAK-GRANT-SCOPE-001` подтверждается статически как латентный риск до продления;
   DB-сценарий этого аудита повторно не запускался.
4. `CI-DEPS-UNPINNED-001` подтверждён. Локальное предупреждение Starlette/httpx показывает,
   что риск уже наблюдаем, хотя текущий CI зелёный.
5. A3/A4/A5/A6 документационного аудита подтверждены: requirements README устарел,
   архитектурный индекс не содержит ADR-018/019, заголовок ADR-018 нестандартен, ссылки на
   retired Hermes остаются в активных документах.
6. Расхождение Ed25519/HMAC подтверждено: исходное решение требует Ed25519 для production,
   а код и production-config gate реализуют HMAC-SHA256.

### Требует уточнения

1. **A2 — не просто «два канонических roadmap».** Репозиторский `AGENTS.md` уже определяет
   XLSX как производную business-карту, а `pre-pilot-journey-plan.md` делегирует текущую
   последовательность `roadmap.md`. Реальный дефект: `roadmap.md` задаёт действующий порядок,
   но отсутствует в едином индексе Sources of Truth; self-declaration внутри файла не делает
   его каноном по правилам того же `AGENTS.md`.
2. **A1 — реальное противоречие, но не runtime P0.** Верхний репозиторский контракт даёт
   приоритет Git/code/tests, а source-of-truth README — ТЗ до нового ADR. Это блокирует
   корректное принятие решений, но не доказывает текущий отказ продукта.
3. **B1 HMAC/Ed25519 — обязательный decision gate до device/pilot/production, но не текущий
   аварийный P0.** Pilot не развёрнут, production NO-GO, ближайший pilot scope — control-plane.
   Срочность возрастает до P0 перед Wave 3 или первым реальным устройством.
4. **D1 ClickHouse — capacity risk, не доказанное превышение.** Расчёт 57,6 млн/сутки верен
   только при предположении «один PoP на устройство в минуту»; фактическая частота и профиль
   batch-ingestion пока не зафиксированы. Нужен измеряемый триггер, а не утверждение о уже
   превышенном пороге.
5. **D3 пересчитан:** в корне `docs/architecture` 47 Markdown-файлов, явный superseded-banner
   есть у 34, а не у 38. Навигационный долг подтверждён, точное число исходного аудита — нет.
6. Состояние живых DEV/PROD из code/security audit независимо не перепроверялось: доступ к
   контурам не использовался. Оно остаётся свидетельством Claude Code, не доказательством этой
   сессии.

## 3. Новые находки

### C1 · UI-smoke нарушают собственный Done Gate 🔴

`AGENTS.md` разрешает `page.goto()` только для `/login` либо единственной публичной entry-
страницы и запрещает прямые API-вызовы. `CLAUDE.md` запрещает `sleep` и retry loops как способ
стабилизации UI.

Найдены как минимум три однозначных нарушения:

- `test_uismoke__audit__view.py`: прямой API-login, API activate/deactivate, `time.sleep(0.3)`
  и цикл reload/retry;
- `test_uismoke__self__campaign_view.py`: прямой `page.goto(.../campaigns)` вместо возврата
  кликами после проверки detail;
- `test_uismoke__advertiser__invite.py`: цикл до трёх повторных выборов строки с перехватом
  любого `Exception`.

Дополнительно `self.login` делает несколько `goto`, включая deep-link принятия приглашения.
Для invite-link может быть оправдана отдельная публичная entry semantics, но она должна быть
явно разрешена journey/Done Gate, а не подразумеваться тестом.

**Влияние:** зелёный CI доказывает прохождение тестов, но не соблюдение обязательного способа
доказательства. Guard проверяет наличие функции по имени, а не её семантику. Затронутые
`reachable`-claims требуют исправленного smoke и повторного прогона.

### C2 · 13 UI-функций не имеют нормативной journey-спецификации 🔴

Программная сверка 45 UI entries registry со структурированными journey-записями в
`user-journeys.md` нашла 13 функций без нормативного пути/actor/happy-path:

`user.split_internal_advertiser`, `advertiser.contact_crud`, `advertiser.brand_crud`,
`advertiser.contract_crud`, `advertiser.legal_requisites`, семь `commerce.*` функций и
`system.theme_switch`. Семь `commerce.*` ID упомянуты позднее только в implementation/status
таблицах, но не описаны как journeys; остальные шесть не представлены даже такими строками.

При этом большинство из них имеют `status: reachable`. Это нарушает Done Gate: функция не
может считаться готовой без journey. Текущий roadmap guard не читает `user-journeys.md`,
поэтому сообщает `0 violations`. В документе всего 10 вхождений `Happy-path:` при 45 UI-
функциях; для старых неизменённых journeys grandfathering не определён.

### C3 · Product roles не совпадают с исполняемой RBAC-моделью 🟡

`user-journeys.md` и registry назначают actor codes `campaign_manager`, `moderator`,
`approver`, `ops_operator`. Seed создаёт только `system_admin`, `security_admin`, `operator`,
`analyst`, `advertiser`. Большинство admin UI-smoke исполняется как всесильный
`break_glass_admin`, даже когда комментарий теста заявляет `campaign_manager`.

**Влияние:** достижимость пути системным администратором не доказывает достижимость целевой
ролью и не доказывает отрицательную границу permissions. Нужно либо ратифицировать persona →
permission-bundle mapping без вымышленных role codes, либо добавить утверждённые роли. Это
продуктовое/RBAC-решение владельца, не автоматическая правка seed.

### C4 · CI и Done Gate описывают противоположную политику UI-smoke 🟡

`AGENTS.md` утверждает «UI-smoke не блокирует CI». Фактически `phase1-ci.yml` включает job
`ui-smoke` в `release-gate`, который требует literal `success`. `roadmap.md` уже называет его
blocking gate. Рабочая реализация однозначна, но контракт агента устарел.

### C5 · Roadmap truth имеет непроверяемые и ошибочно подписанные метрики 🟡

- `roadmap.md` корректно считает 53 reachable = 43 UI + 10 service, но ниже называет 53/58
  «долей функций, достижимых в UI» — это неверно для десяти service features.
- `Pilot readiness ~25%` и `Business journey completeness ~60%` не имеют воспроизводимой
  формулы, входных данных или guard. Это экспертные оценки, оформленные как численные факты.
- Strict guard проверяет XLSX ↔ registry ↔ имя smoke-функции, но не `roadmap.md`, содержание
  journey, actor/permissions, запрет API/goto/retry или попадание smoke в CI subset.

### C6 · В репозитории лежат опасно устаревшие roadmap-mutator scripts 🟡

- `generate_roadmap.py` генерирует старую 5-колоночную business-схему, содержит устаревшие
  статусы и пишет в `/home/cobalt/...`;
- `fix_roadmap_qa.py` также привязан к `/home/cobalt/...` и к старому состоянию продукта;
- `update_roadmap_v26.py` пишет в текущий XLSX по относительному пути, добавляя повторно
  устаревшие строки (`ADR-018 proposed`, advertiser-web not started) и английские статусы.

Они не вызываются CI, но выглядят как поддерживаемые инструменты. Случайный запуск третьего
скрипта реально испортит каноническую business-карту.

### C7 · Канонические документы содержат активные, а не только исторические расхождения 🟡

- `pre-pilot-journey-plan.md` внизу всё ещё объявляет `backup.restore` deferred и
  `KSO-ENV-001 next`, хотя registry уже помечает backup reachable, а текущий Next —
  `PORTAL-UX-POLISH-001A3`;
- `user-journeys.md` смешивает спецификацию с append-only status log, имеет повторную секцию
  `## 6`, старые `❌ G1/G2/G3` и устаревшие `Next`, хотя файл — Tier 2 спецификация;
- активные `epic-l-licensing.md` и `inventory-domain-model.md` не перечислены в архитектурном
  индексе, хотя другие канонические документы ссылаются на них как на design freeze/model;
- v2.6 DOCX закономерно сохраняет исходный baseline, но requirements README не накладывает
  актуальный overlay: ADR-018 уже принят/реализован, advertiser-web существует, self-service
  реализован частично.

### C8 · Existing audit inventory needs reproducible counters 🟢

Markdown links intact, current CI and import boundaries green. Но числа «47 architecture
docs / 38 historical / 15 runbooks» нельзя использовать как проверяемые факты без команды:
сейчас 47 root Markdown architecture files, 34 явных superseded-banner и 16 Markdown runbooks
(17 файлов с `mirror-check.sh`). Это не продуктовый дефект, а требование к следующему аудиту.

## 4. Приоритеты после независимой сверки

1. **P0 truth repair:** C1 + C2. Нельзя строить readiness на smoke, нарушающем Done Gate, и
   на UI features без обязательной journey-спецификации.
2. **P1 security-test fidelity:** `BEHAVIORAL-ENV-CONTRACT-001` +
   `BEHAVIORAL-ADMIN-MASK-001`; они предотвращают повторение tenant/RLS-регрессии.
3. **P1 product/RBAC decision:** C3 — утвердить actors/permission bundles и добавить
   positive/negative proof не под break-glass.
4. **P1 governance:** A1/A2, C4/C5/C7; один индекс, один порядок, воспроизводимые метрики.
5. **Перед Wave 3 / device pilot:** решение Ed25519 vs HMAC и устранение C6.
6. **До EPIC-L Layer 2:** `LICENSE-PEAK-GRANT-SCOPE-001`.
7. Остальные gaps ТЗ, ClickHouse capacity model и Creative QA планировать после утверждённого
   control-plane UX/walkthrough либо отдельного override владельца.

Конкретная нарезка и критерии приёмки — в
`2026-08-26-codex-work-plan-addendum.md`.
