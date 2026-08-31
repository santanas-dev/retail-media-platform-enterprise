# RM-TECH-210 — mini-design: RLS-контекст на device-маршрутах онбординга

**Статус:** реализовано локально, `delivery_status: in_progress` — жду CI-прогона и owner gate `device_contract`
**Задача:** `RM-TECH-210` (этап S, зависит от `RM-STAB-002` — done)
**Закрывает находку:** `RLS-CONTEXT-DEVICE-001` (PROJECT_STATE, 2026-08-26): `RLS-CONTEXT-DEVICE-CODES-001`, `RLS-CONTEXT-DEVICE-ONBOARD-001`
**Режим (OD-042):** adapt — REQ-SEC-002 / REQ-SEC-003 / REQ-CHAN-002; существующее поведение сохраняется, политики расширяются аддитивно
**Owner gate:** `device_contract` — контракт публичного онбординга дополняется двумя транзакционными настройками сессии; требует ACCEPT владельца

---

## 1. Дефект (доказан под ролью приложения)

Снятие allowlist элевации в `tests/behavioral/conftest.py` (маска RM-STAB-002) даёт **11 из 13** падений
`test_edge001_device_onboarding.py`: `new row violates row-level security policy for table "device_onboarding_codes"`
(лог сессии `rm-tech-210-before.log`). Причины:

| Маршрут | Дефект |
|---|---|
| `POST /identity/device-codes` | не нёс `Depends(set_rls_context)`; INSERT-политика 022 требует admin или retailer scope → 0 строк в проде |
| `POST /device/onboard` | без JWT — код и есть авторизация; сессия без контекста → SELECT/UPDATE по коду отклонены → `403 INVALID_CODE` у каждого устройства |

## 2. Решение (аддитивно, по образцу миграции 023)

1. `POST /identity/device-codes` получает `_rls=Depends(set_rls_context)` — как все tenant-маршруты.
2. Миграция **037** (`037_device_onboarding_bootstrap_rls.py`):
   - `device_onboarding_codes` SELECT/UPDATE: `RETAILER_RLS OR code = current_setting('app.rmp_device_code')` — видна ровно одна строка, чей секрет вызывающий предъявил; INSERT-политика не меняется;
   - `physical_devices` SELECT: `… OR hardware_fingerprint = current_setting('app.rmp_device_fingerprint')` — глобальная проверка конфликта fingerprint сохраняется без раскрытия чужих устройств.
3. `POST /device/onboard`: в начале транзакции `app.rmp_is_admin=false`, `app.rmp_device_code`, `app.rmp_device_fingerprint`; после чтения кода — `app.rmp_scope_retailer_ids = code.retailer_id` (scope выводится сервером из кода, клиент выбрать не может — как и раньше). Admin-обход на публичном маршруте не ставится никогда.
4. Механизм `ENDPOINT_ELEVATION_ALLOWLIST` в conftest снят целиком (по требованию собственного теста «не оставлять заглушку»); пин — `TestNoRouteElevationRemains`.

Отклонённые альтернативы: admin-обход в публичном маршруте (повторяет маску в проде); SECURITY DEFINER функции (новый контур доверия, больше поверхности).

## 3. Доказательства (локально, одноразовая БД postgres:16-alpine, миграции head=037, роль `retail_media_app` NOSUPERUSER NOBYPASSRLS)

| Проверка | Результат |
|---|---|
| Rehearsal миграции: `alembic downgrade 036` → `upgrade head` | политики восстановлены/пересозданы, `alembic_version=037` |
| `test_edge001_device_onboarding.py` (13 старых + 3 новых RM-TECH-210) + `test_rls_context_strictness.py` + heartbeat + manifest delivery + license enrollment/decommission + import/tx boundaries | **97 passed** без элевации в фазе `call` |
| Прямой запрос под ролью приложения без контекста | 0 строк (fail-closed); с `app.rmp_device_code` = свой код — 1 строка, чужие коды — 0; с чужим секретом — 0 |
| Прямой запрос к `physical_devices` | без контекста 0; с чужим fingerprint 0; со своим — 1 |
| Полный behavioral-набор | #1 (свежая БД): 477 passed / 12 skipped / 0 failed; #2 по той же БД: 8 падений PoP-тестов = pre-existing неидемпотентность (fixed event_id), не регрессия; #3 (свежая БД, финальный код): **477 passed / 12 skipped / 0 failed** |

CI-evidence (job «Behavioral PostgreSQL Tests — ADR-008 Gate») — после разрешения владельца на commit/push. Registry `device.onboard`
возвращается в `reachable` только по этому CI-evidence (OD-038).

## 4. Что не менялось

Контракты ответов (`403 INVALID_CODE/CODE_REVOKED/CODE_ALREADY_USED/CODE_EXPIRED/FINGERPRINT_CONFLICT`, `409` лицензии, идемпотентность
same code + same fingerprint), device-gateway, heartbeat, manifest, licensing choke-point. Код вне `onboard.py`, миграции 037 и тестов не тронут.
