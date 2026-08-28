# Полное ревью ТЗ v2.6 r416 — сплошное чтение и сверка с кодом

> ⚠️ **НЕ КАНОН** · тип: полное ревью · предмет: драфт **r416** (sidecar `87ceeb14…`, сходится), 2769 строк
> · сверено с: `packages/`, `apps/`, seed, живая БД (схема 036), v2.5/v2.6 extracted, registry, journeys, roadmap
> · SHA: `develop @ b21174f` + рабочее дерево · дата: 2026-08-27 · автор: Claude Code
> · находок: **41** (5 блокеров · 13 код · 4 источники · 9 внутренних · 5 форма · 5 решений) · Отменён: —
>
> Отличие от прежних ревью: те были адресными (трассировка, ID, счёт). Здесь прочитан каждый
> нормативный раздел и каждое утверждение о коде проверено прогоном. Ничего не изменено.

## 0. Вердикт

**Дорабатывать. Не утверждать.** Но впервые перечень правок конечен и разложен по адресатам:
Codex правит текст (§§B–E), владелец принимает решения (§H), я готовлю артефакты (§A).
После этого документ утверждаем как ТЗ v2.6 с явным перечнем `blocked`-доменов.

Что **подтверждено** и перепроверять не нужно — §F. Это больше половины утверждений драфта о коде.

## A. Блокеры утверждения — артефакты, не текст

| # | Блокер | Факт r416 |
|---|---|---|
| A1 | `requirements-traceability.yaml` | отсутствует; AP — prose-input (AC-01) |
| A2 | Карта REQ → roadmap task | 6 из 43 задач, 0 из 3 гейтов упомянуты; ни одной связи REQ→task |
| A3 | Непроверяемые требования | 51 из 90 REQ без story и без `SC-*`; `SC-*` — один сценарий |
| A4 | Два реестра решений | 21 DEC против 16 OD; 12 DEC без ссылки на OD/ADR |
| A5 | AC-реестр без статуса; приложение AH отсутствует | 326 строк, 2 колонки; порядок AO→AE→…→AN→AP→AQ |

## B. Расхождения с кодом — требование подано без пометки «не текущий факт»

По ADR-020 это не дефекты драфта как такового — это требования, которым не хватает маркера
`required`, либо дефекты кода, которым нужна задача. Каждая строка проверена прогоном.

| # | Раздел | Драфт | Код | Что делать |
|---|---|---|---|---|
| B1 | REQ-UX-001, §4, AP | ≥8 ролевых контуров (менеджер, модератор, согласующий, оператор, ИБ, аналитик, рекламодатель, admin) | seed и живая БД: **5 ролей** — `system_admin`, `security_admin`, `operator`, `analyst`, `advertiser`. Registry ссылается на `campaign_manager`, `moderator`, `approver`, `ops_operator` — их **нет**; смоуки логинятся break-glass admin | **DEC**: модель ролей; пометить `required`; это разрыв и канона (registry), не только драфта |
| B2 | §6 Emergency | 6-состоянийная машина `requested → … → closed` | `emergency_overrides.active` — **boolean**, `activated_by/at`, `deactivated_*` | пометить `required`, задача |
| B3 | §6 Advertiser application | `draft → submitted → under_review → approved/rejected → suspended/closed` | default `new`; `draft/submitted/under_review/suspended` в коде нет; invite default `pending` | пометить `required` |
| B4 | §6 Creative | `uploaded → scanning → qa_failed/approved → superseded` | `status` default `ready`; `moderation_status` `approved/rejected` | пометить `required` |
| B5 | §6 Playlist, Rollout | полные state machines | сущностей `Playlist`, `Rollout` нет | пометить `required` (в §3 сказано, в §6 — нет) |
| B6 | §6 Campaign | `active → paused → completed`; `draft/rejected → archived` явной командой | `ALLOWED_TRANSITIONS`: из `PAUSED` **нет ни одного перехода**; `/archive` пишет статус мимо `validate_transition` (AC-290 знает) | **дефект кода**: пауза терминальна — задача; пометить в §6 |
| B7 | §6 Commerce order | `draft/offered/booked → cancelled`; `closed` immutable | код: `OFFERED/BOOKED/CONFIRMED → CANCELLED`, из `DRAFT` отмены **нет**, из `CONFIRMED` — **есть** | согласовать в одну сторону (DEC или правка кода) |
| B8 | §13 PoP | «дубликат возвращает `409`» | batch отвечает `200` с `duplicate_count` (partial success); **ADR-017 требует 409 per event** | расхождение **кода** с ADR-017 → задача или amendment ADR; в драфте пометить |
| B9 | Доп. C | audit-формат с `actor_type`, `permission_code`, `scope`, `before/after_version`, `result`, `evidence_ref` | `audit_events_operational`: `actor_user_id, action, target_type, target_id, correlation_id, ip_address, details_json` | пометить `required` |
| B10 | §12 | `campaign_type` enum, inventory-статусы `free/reserved/sold/internal/emergency/fallback` | `campaign_type` нет; `InventorySlot` даёт `available/limited/sold_out/blocked` (AC-291 знает) | §12 целиком без маркировки факт/цель — добавить |
| B11 | Доп. B, Доп. E | permission-коды `campaign.create`, `campaign.publish`, `device.command`, `rollout.rollback`, `audit.export`… | backend: `campaigns.manage`, `campaigns.approve`… — **ни одного** кода из B/E нет; AP использует реальные коды | три схемы именования в одном документе; привести B/E к backend-кодам |
| B12 | §26 | 101 путь | 42 «фактических» существуют ✓; **37 без маркера** (21 есть, 16 нет: `/api/branches`, `/api/carriers*`, `/api/manifests`, `/api/rollouts`…); 13 proposed — нет ✓ | по правилу самого §26 немаркированное = UNVERIFIED; проставить маркер каждой группе |
| B13 | §11 | «прямые `kso_*`-зависимости не расширяются» | не проверял — вне объёма | — |

## C. Расхождения с источниками

| # | Драфт | Источник | Вердикт |
|---|---|---|---|
| C1 | REQ-NFR-001: «потеря PoP ≤0.1%» | v2.5: **0 вхождений** | число без источника → DEC или маркер `proposed` |
| C2 | REQ-NFR-006, §8: «до 100 admin» | v2.5: **0 вхождений** | то же |
| C3 | §16: «каналы и устройства всех типов» | v2.5:964 задаёт точные числа (2000 КСО, 500 Android/TV, 300 price checker, 50 ESL, 100 LED) | REQ-STAND-002 их несёт ✓ — §16 просто смягчил формулировку; сослаться на REQ-STAND-002 |
| C4 | §36 карта разделов | REQ-BIZ-017, REQ-UX-005 отсутствуют в карте | у них нет источника в v2.5 (они из registry) — пометить `source=registry`, иначе §36 неполон по собственному правилу |

Проверил и **снял** подозрение: порядок приоритетов §12 (`emergency → сеть → федеральная → …`)
есть в v2.5:818. Все прочие NFR-числа (5 мин/95 %, 60 с, 15 мин, 7 дней, 99.5/99.9, RTO 4 ч,
RPO 15 мин), размеры поверхностей и состав стенда — в источнике.

## D. Внутренние противоречия документа

| # | Противоречие |
|---|---|
| D1 | §1 и §20: «каждое требование получает `MUST/SHOULD/MAY`» — в §25 **0 из 90** строк несут нормативность |
| D2 | §37 объявляет обязательными `source, normative, owner, roadmap_ids, requirement_status, delivery_status, acceptance…` — таблица §25 имеет 3 колонки; ни одно поле не присутствует |
| D3 | §36 запрещает голое `§N` вне колонки «Источник v2.5» — нарушено ≥7 раз в нормативном тексте, включая заголовок Доп. J «Детальная карта §22» и DEC-014 «§R» |
| D4 | §18 запрещает «варианты без решения» в нормативной прозе — §32 задаёт retention диапазонами «12–18 месяцев», «3–5 лет», «90–180 дней» |
| D5 | Доп. U/§37 приводят `channel.publish` как пример канонического ID — его нет ни в registry, ни в journeys |
| D6 | §6: campaign/manifest/device/commerce снабжены оговорками «в текущем коде…», emergency/application/creative/playlist/rollout/PoP — нет. Один раздел, два стандарта маркировки |
| D7 | Доп. V понижен до legacy, но 26 несуществующих ID остаются в таблице; AP даёт `PENDING-ID` для тех же stories — читатель обязан знать, какая таблица главнее |
| D8 | §2.1 «Каналы первой архитектурной очереди: … price checker …» — REQ-CHAN-002 даёт размеры для KSO/TV/ESL/LED, но не для price checker |
| D9 | §22 gate 9 делает «проверку внешним monitoring-dashboard» условием APPROVED, тогда как §33, Доп. R и AGENTS.md запрещают ему быть источником истины — формулировку gate смягчить до «наблюдательный сигнал» |

## E. Форма — препятствия для утверждения людьми

| # | Наблюдение |
|---|---|
| E1 | **25 разделов более чем на 60 % латиница** (§6, §13, §26, AP — 94 %). Утверждают владелец, юрист, ИБ — на русском. Нужна языковая политика: нормативный текст по-русски, идентификаторы — как есть |
| E2 | Приложения A–E стоят между §17 и §18; F–AQ — после §38; AH пропущено; порядок AO→AE→AF→AG→AI→AD→AL→AJ→AK. Индекс лечит навигацию, не структуру |
| E3 | 2769 строк, 495 КБ в одном файле — §34 сам требует комплект из 12 артефактов; разрезать надо сейчас, а не «в финальной редакции» |
| E4 | Доп. R содержит IP `192.168.110.78:3200` внешнего dashboard; хост отсутствует в `environment-inventory.yaml`; ТЗ не место для адресов |
| E5 | Changelog r285–r416 — 130 записей в шапке документа; в ТЗ на утверждение — вынести в отдельный файл |

## F. Подтверждено — перепроверять не нужно

`ManifestStatus` = `generated/delivered/applied/expired/error` ✓ · `DeviceStatus` семь значений,
`pending/registered` отсутствуют ✓ · `ProofMode` семь режимов без `error/not_applied` ✓ ·
`CommercePaymentStatus` пять значений ✓ · `CommerceTariffStatus` три ✓ · `campaign` enum с
`rejected/archived` ✓ · ETag/304 на `manifest/latest` ✓ · PoP: JWT-subject, quarantine, batch ≤500 ✓ ·
outbox: lease/claim/`publishing`/`Nats-Msg-Id` ✓ · `ad-settings` GET/PUT/test ✓ · 42 «фактических»
маршрута §26 существуют ✓ · SHA всех четырёх источников ✓ · v2.5 — 25 разделов ✓ ·
REQ-STAND-002 = v2.5:964 ✓ · AP: 0 невалидных permission-кодов без метки PENDING ✓ ·
арифметика AM отозвана ✓ · V26-005 в §25 исправлен ✓ · `RM-TECH-210` в §11 ✓ · DEC 001–022
все определены ✓ · §36 не ссылается на несуществующие REQ ✓ · master-adapter и ESL —
квалифицированы верно ✓.

## G. План правок к согласованности — для Codex (r417)

Порядок — по стоимости ошибки, не по номеру раздела:

1. **§6 — единый стандарт маркировки.** Каждая state machine получает две строки:
   `текущий код:` и `требуется:`. Добавить B2–B7. Для campaign явно: `paused` терминален в коде.
2. **§25 — нормативность и поля.** Колонка `MUST/SHOULD/MAY` для всех 90; `source` для
   каждого (BIZ-017/UX-005 — `registry`); D1/D2 закрываются здесь же.
3. **Доп. B/E → backend-коды.** Заменить `campaign.create`→`campaigns.manage` и т.д.;
   несуществующие права (`device.command`, `rollout.rollback`, `audit.export`) пометить `PENDING`
   как в AP. Одна схема на документ.
4. **§26 — маркер на каждой группе.** Группа v2.5-shorthand (`/api/branches`…) → `target`;
   Device Gateway строка разбить на две.
5. **§12, Доп. C — маркер `required`.** По образцу §3/§13.
6. **NFR без источника** (C1, C2) → `proposed` + DEC-009.
7. **§32 диапазоны** → либо значения, либо `DEC-007 pending` вместо диапазона.
8. **§36-правило** — исправить 7 нарушений или ослабить правило до таблиц.
9. **Доп. V** — удалить таблицу, оставив ссылку на AP; 26 ID уходят вместе с ней.
10. **Роли** — добавить в §4/REQ-UX-001 факт «5 ролей в seed» и DEC на модель ролей (B1).
11. **Язык** — политика в §38; перевод §6/§13/§25/§26/AP в нормативную русскую форму.
12. **Структура** — приложения после §38 в алфавитном порядке; AH либо вернуть, либо
    перенумеровать; changelog — отдельный файл; §34-комплект начать резать сейчас.
13. **Доп. R** — убрать IP, сослаться на `environment-inventory.yaml` (куда добавить `.78`).

## H. Решения владельца — 5 прежних + 4 новых

Прежние (AQ.1 №1–5) подтверждены. Новые, вскрытые сплошным чтением:

6. **Модель ролей** (B1): ТЗ требует ≥8 контуров, система имеет 5 ролей, registry именует
   несуществующие. Расширять RBAC (задача) или сводить контуры к 5 (правка ТЗ и registry)?
7. **Семантика дубликата PoP** (B8): код отвечает `200 + duplicate_count`, ADR-017 требует
   `409` на событие. Править код под ADR или ADR под код?
8. **Пауза кампании** (B6): в коде из `paused` выхода нет. Дефект или намеренно?
9. **Числа без источника** (C1, C2): принять как требования (DEC-009) или снять.

## I. Что подготовлю я после решений

`requirements-traceability.yaml` + модуль гейта `req` (A1–A3); слияние DEC→OD (A4);
генерируемые ERD/OpenAPI/события/permissions под гейтом; prerequisite-задачи master-adapter и
второго канала; задачи по B6/B8, если владелец признаёт их дефектами кода.

## Приложение. Воспроизводимость

Все проверки — Python/grep по `packages/domain/__init__.py` (enum'ы и `ALLOWED_TRANSITIONS`),
`packages/domain/commerce_repository.py` (`_ORDER_TRANSITIONS`), `packages/domain/models.py`
(таблицы), `apps/control-api/seed.py` (роли, permissions), `SELECT code FROM roles` на
одноразовой БД после миграций 036, `packages/api/**` (маршруты с префиксами из
`identity.py`), `apps/device-gateway/main.py`, `docs/00-source-of-truth/*.extracted.md`
(NFR-числа, строка 818 — приоритеты, 964 — стенд).
