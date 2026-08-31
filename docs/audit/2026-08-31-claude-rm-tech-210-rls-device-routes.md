# Claude — RM-TECH-210: RLS-контекст на device-маршрутах онбординга (стадия S)

Статус: **реализовано локально; `delivery_status: in_progress`; не закоммичено; ждёт CI-evidence и owner gate `device_contract`.**
База: `develop @ 236bda4`. Режим OD-042: **adapt** (REQ-SEC-002/003, REQ-CHAN-002); существующее поведение и контракты ответов сохранены.
Старт по OD-043: зависимость `RM-STAB-002` — done. Design-gate: `docs/architecture/rm-tech-210-device-onboarding-rls-bootstrap-design-gate.md`.

## 1. Дефект воспроизведён под ролью приложения

Одноразовая БД `postgres:16-alpine` (миграции до 036, seed, роль `retail_media_app` NOSUPERUSER NOBYPASSRLS — как CI-job).
Снятие allowlist элевации в `tests/behavioral/conftest.py`: **11 из 13** тестов `test_edge001_device_onboarding.py` падают —
`new row violates row-level security policy for table "device_onboarding_codes"` (`rm-tech-210-before.log`).

## 2. Изменения (продуктовый код — только `packages/api/device_routes/onboard.py` и миграция 037)

| Файл | Что |
|---|---|
| `apps/control-api/alembic/versions/037_device_onboarding_bootstrap_rls.py` | SELECT/UPDATE `device_onboarding_codes`: `+ OR code = app.rmp_device_code`; SELECT `physical_devices`: `+ OR hardware_fingerprint = app.rmp_device_fingerprint`; INSERT/UPDATE/DELETE политики устройств и INSERT кодов — без изменений; downgrade восстанавливает 022/023 |
| `packages/api/device_routes/onboard.py` (+45/−2) | `/identity/device-codes`: `_rls=Depends(set_rls_context)`; `/device/onboard`: `_set_onboarding_bootstrap` (is_admin=false, код, fingerprint) в начале транзакции; `_bind_retailer_scope(code.retailer_id)` после чтения кода перед licensing/созданием устройства; порядок проверок прежний |
| `tests/behavioral/conftest.py` | механизм `ENDPOINT_ELEVATION_ALLOWLIST`/`_path_allowlisted` снят целиком (последние 2 записи — эти маршруты) |
| `tests/behavioral/test_rls_context_strictness.py` | `TestAllowlistIsAccountable` → `TestNoRouteElevationRemains` (пин: механизма нет) |
| `tests/behavioral/test_edge001_device_onboarding.py` | +`TestRMTech210BootstrapRLS` (3 теста: оба маршрута без элевации; код виден только со своим `app.rmp_device_code`; устройство — только со своим fingerprint) |

## 3. Evidence (локально)

| Прогон | Результат |
|---|---|
| rehearsal миграции `downgrade 036 → upgrade head` | политики пересозданы, `alembic_version=037` |
| targeted: edge001 (16) + strictness + heartbeat + manifest delivery + license enrollment/decommission + import/tx boundaries | **97 passed** |
| unit `tests/test_edge001_device_onboarding.py` (mocks, чистое окружение) | **8 passed** |
| полный `tests/behavioral` #1 | **477 passed, 12 skipped, 0 failed** (4:37) |
| полный `tests/behavioral` #2 (та же БД, что #1) | 8 failed / 469 passed — все 8 в PoP-тестах (`test_edge003*`) из-за фиксированных `event_id`: на свежей БД финальный код даёт 11/11, повтор по той же БД — те же 8 падений. **Pre-existing неидемпотентность тестов, не регрессия** (находка BEHAVIORAL-POP-IDEMPOTENCE-001 → RM-STAB-011) |
| полный `tests/behavioral` #3 (свежая БД, финальный код) | **477 passed, 12 skipped, 0 failed** (4:36) |
| root-набор `tests/` (как CI «Python — Unit Tests», с env job) | **исправление после красного CI 33398575125**: `test_pilot_host_preflight`, `test_pilot_packaging`, `test_stand_identity_and_safe_smoke` пинили literal `036` как head репозитория; миграция 037 их уронила (мой первичный вывод «pre-existing» был ошибкой — untracked-миграция оставалась в дереве при проверке «на исходном коде»). Фикстуры переведены на `alembic_head.resolve_single_head` (динамический head); тест резолвера сверяется с независимым вычислением из имён файлов. Результат: см. итог в этой таблице ниже |

CI-evidence (job «Behavioral PostgreSQL Tests — ADR-008 Gate») — после разрешения владельца на commit/push. Registry `device.onboard`
→ `reachable` только по CI (OD-038); `done` — только после owner gate `device_contract`.

## 3a. Итог после фиксов фикстур

| Прогон | Результат |
|---|---|
| `pytest tests/` в окружении CI-job (после fix `53447ff`) | **1909 passed, 534 skipped, 0 failed** |
| CI **33400714049** (`53447ff`) | Unit, Packaging, Behavioral PostgreSQL, UI-Smoke, Schema, Guard — **success**; упал только «Stand Rollback Drill» — `tests/integration/test_stand_rollback_drill.py` пинил `OLD_HEAD/NEW_HEAD = 035/036` и имя файла `036_…py` |
| фикс drill (локально, docker как в CI) | пара head'ов выводится из миграций (NEW_HEAD = resolver, OLD_HEAD = down_revision, файл — glob); `RUN_STAND_ROLLBACK_DRILL=1` → **3 passed** |

Остальные литералы `036` в `tests/test_local_stand.py` — самосогласованные моки (lock ↔ db), Unit-job их проходит; не трогались.

## 4. Регрессионные критерии (traceability REQ-SEC-002/003)

Сохранены: коды ответов онбординга, идемпотентность, cross-retailer scope из кода, licensing choke-point; strict-режим RM-STAB-002 без исключений.
