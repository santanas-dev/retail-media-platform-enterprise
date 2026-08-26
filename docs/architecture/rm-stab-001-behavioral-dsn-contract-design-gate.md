# RM-STAB-001 — mini-design: единый контракт `BEHAVIORAL_APP_DB_URL`

**Статус:** реализовано, `delivery_status: verification` — жду первого прогона CI
**Задача:** `RM-STAB-001` (этап S, зависит от `RM-ENV-001`)
**Закрывает находку:** `BEHAVIORAL-ENV-CONTRACT-001` (мой аудит 2026-08-26)
**Утверждённая приёмка:** обе DSN-формы проходят один targeted behavioral command через
один helper.

---

## 1. Дефект

Переменная была перегружена двумя **несовместимыми** формами, и ни одно значение не
удовлетворяло обеим группам потребителей:

| Группа | Нужна форма | Что ломается на чужой форме |
|---|---|---|
| SQLAlchemy — `conftest`, `test_commerce_rls`, `test_license_*`, `test_creative_upload_sessions_rls`, `test_minio_upload` | `postgresql+asyncpg://` | `InvalidRequestError: The asyncio extension requires an async driver ... 'psycopg2' is not async` |
| raw `asyncpg.connect` — `test_authz_cross_portal_001_derived_rls`, `test_campaign_permission_split_001`, `test_edge001/002`, `test_adr018_multitenancy_rls` | `postgresql://` | `ClientConfigurationError: invalid DSN ... got 'postgresql+asyncpg'` |

В CI дефект невидим: **CI переменную не задаёт вовсе**, он выставляет `DATABASE_URL`, и
каждый файл падал на собственный корректный дефолт. Ловушка доставалась оператору,
которому раздел «Environment» в `PROJECT_STATE.md` прямо велел переменную выставить.

## 2. Решение

`tests/behavioral/dsn.py` — единственное место, читающее переменную. Значение задаётся
**любой** из двух форм; потребитель берёт нужную ему:

* `sqlalchemy_dsn()` → всегда `postgresql+asyncpg://`
* `raw_dsn()` → всегда `postgresql://`

Синхронные драйверы (`+psycopg2`, `+psycopg`) отвергаются с объяснением: behavioral-стек
асинхронный, и молчаливое их принятие дало бы отказ на несколько кадров ниже по стеку.

Переведены **12 потребителей**; прямых чтений переменной вне helper не осталось.
Обратная совместимость с CI сохранена: helper падает на `DATABASE_URL`, как раньше.

## 3. Доказательство

Одноразовая PostgreSQL (порт 55433, удалена после прогона): миграции до `036`, seed,
роль `retail_media_app` — `NOSUPERUSER`, `NOBYPASSRLS`, 37 таблиц с FORCE RLS.

| Прогон | Результат |
|---|---|
| `test_commerce_rls.py`, форма `postgresql+asyncpg://` | 9 passed |
| `test_commerce_rls.py`, форма `postgresql://` | 9 passed |
| SQLAlchemy + raw-asyncpg вместе, обе формы | 29 passed каждой формой |

**Tamper-цикл красный в обе стороны.** Убрал нормализацию голой формы → голый DSN уходит
в `create_async_engine` → `InvalidRequestError`. Убрал обратную → драйверный DSN уходит в
`asyncpg.connect` → `invalid DSN: scheme is expected to be either ...`. Восстановил —
снова зелено. Это те же две ошибки, которые я предъявил в аудите, то есть починено
именно заявленное.

## 4. Что НЕ моё — и как я это установил

Полный набор: **468 passed, 2 failed**. Упали
`test_edge003_pop_ingestion::test_accepted_event_increments_summary` и
`::test_duplicate_event_id_not_double_counted`.

Проверено прямым сравнением: те же два теста падают **на оригинале файла из git** и
**вовсе без переменной**. В CI на `75c4135` оба `PASSED`, всего `470 passed` — и мои
468 + 2 дают те же 470 собранных.

Причина — различие стенда, а не репозитория: CI поднимает PostgreSQL под owner-ролью
`retail_media_owner`, мой одноразовый стенд — под `retail_media`, поэтому владелец
таблиц другой. Дальше я не копал: это вне объёма `RM-STAB-001`, а выдавать
предположение за диагноз не буду.

## 5. Исправлен источник ловушки

Раздел «Environment» в `PROJECT_STATE.md` теперь говорит, что переменная принимает обе
формы и что приведением занимается helper. Раньше он отправлял оператора в дефект.

## 6. Почему `verification`, а не `done`

Приёмка заявляет `verified_by: command`, и команда прогнана с доказательством — формально
этого хватает. Ставлю `verification` сознательно: правка идёт в CI впервые, а в этой
сессии я **дважды** заявлял зелёное, проверив только на своей машине, и оба раза получал
красный прогон. Переведу в `done` после того, как behavioral-job подтвердит на раннере.

## 7. Проверяемая приёмка

```
# на любой БД со схемой 036 и ролью retail_media_app
RUN_BEHAVIORAL_TESTS=1 \
BEHAVIORAL_APP_DB_URL=postgresql://retail_media_app:retail_media_app@HOST:PORT/retail_media_platform \
  python3 -m pytest tests/behavioral/test_commerce_rls.py -q
RUN_BEHAVIORAL_TESTS=1 \
BEHAVIORAL_APP_DB_URL=postgresql+asyncpg://retail_media_app:retail_media_app@HOST:PORT/retail_media_platform \
  python3 -m pytest tests/behavioral/test_commerce_rls.py -q
```
