# Claude — RM-STAB-006: нормативный формат UI journeys registry (стадия S)

Статус: **реализовано локально; `delivery_status: in_progress`; не закоммичено.** База `develop @ 236bda4`. Старт по OD-043 (RM-STAB-003 → verification, OD-044).
Режим OD-042: adapt/new (документ + governance tooling); продуктовый код не менялся.

## 1. Артефакт
`docs/product/journeys/journeys.yaml` — 79 journeys (число вычислено из `feature-registry.yaml`, UI со smoke 61, reachable 52). Поля каждого journey:
`id, name, frontend, kind (ui|service), route, roles, permission_codes, stories, actor_permission_scope, entry, happy_path («Happy-path: N шагов — …», вход всегда логин по §1),
selectors (data-testid, извлечены из smoke-файлов as-built — 43 reachable UI journeys), negative_path, smoke, status, walkthrough (PENDING), gap`.
Источники: registry (канон), user-journeys §6 и registry `path` (пути), ТЗ r428 Дополнение AP (actor/permission/entry/negative), role-scope-matrix (30 кодов), tests/ui-smoke (селекторы).

## 2. Валидатор `scripts/ci/check-journey-spec.py`
`--strict`: реестр ⇔ registry (MISSING/UNKNOWN/DUPLICATE), STATUS-DRIFT, SMOKE-DRIFT, WALKTHROUGH (PENDING|OK|замечания), BLOCKED-NO-GAP, PERMISSION-UNKNOWN;
для reachable UI: INCOMPLETE (actor/entry/negative), HAPPY-PATH (маркер, N ≥ 3), PERMISSION-MISSING, SELECTORS, SELECTOR-DRIFT (каждый селектор встречается в smoke-файле).
`--self-test`: 11 кейсов (baseline + 10 tamper). Результат: strict **PASS**, self-test **11/11**. Число journeys нигде не фиксируется (RM-GOV-009: «45/45» снято).

## 3. Приёмка RM-STAB-006
- validator (command) — `python3 scripts/ci/check-journey-spec.py --strict` → PASS локально;
- число journeys из registry — `python3 scripts/roadmap-consistency-check.py` → 0 violations.
`verification` — после CI; включение валидатора в CI-политику — RM-STAB-008.

## 4. D2 (OD-044)
`analyst` добавлен в каталог ролей `user-journeys.md` §2 (read-only, retailer scope).
