# RM-STAB-003 — mini-design: approved personas → permissions → retailer scope

**Статус:** **принят владельцем 2026-08-31 (`OD-044`, D1–D3)** — `delivery_status: verification`, `done` после commit/CI; реализация — RM-STAB-004
**Задача:** `RM-STAB-003` (этап S, зависит от `RM-STAB-002` — done); реализация — `RM-STAB-004` (migration_application), UI-proof — `RM-STAB-007`, control plane — `RM-STAB-015`
**Решения-основания:** `OD-035`/DEC-023 (продуктовая модель ролей Q2 принята; недостающие bundles создаются аддитивно, alias `operator` сохраняется), `OD-003` (retailer scope — первоклассная граница; bypass только system_admin/security_admin), ADR-018 (вариант B: `retailer_id` на tenant-таблицах), `OD-005` (managed-first), `OD-039` (роли владельцев)
**REQ:** REQ-UX-001, REQ-BIZ-015, REQ-SEC-002, REQ-UX-005, REQ-SEC-009 · **Режим (OD-042):** adapt — существующие роли/коды/RLS сохраняются, недостающее добавляется
**As-built источник:** `docs/product/role-scope-matrix.yaml` (кандидат, 2026-08-31), `packages/domain/scopes.py`, `packages/api/dependencies.py`, seed.py

---

## 1. Что есть (as-built, develop @ 236bda4)

| Слой | Факт |
|---|---|
| Роли seed | `system_admin`, `security_admin`, `operator`, `analyst`, `advertiser` (5) |
| Permission-коды | 30 (`campaigns.read/manage/approve`, `creatives.read/moderate`, `inventory.read/manage`, `advertisers.read/manage`, `advertisers.contacts.read/manage`, `advertiser_applications.read/review`, `commerce.tariff_read/manage`, `commerce.order_read/manage`, `devices.read/manage`, `emergency.read/manage`, `users.read/manage`, `roles.read/manage`, `audit.read`, `license.read`, `channels.read`, `organization.read`, `campaign_briefs.manage`) |
| Scope | unscoped роль → `global_permissions`; `user_roles.scope_type='advertiser'` + `advertiser_user_memberships` → `advertiser_scope_ids`; `retailer_scope_ids` выводятся **только** из advertiser-организаций (ADR-018); `branch/cluster/store` — deferred; `ADMIN_ROLE_CODES` = system_admin, security_admin → `app.rmp_is_admin=true` |
| Enforcement | `require_permission` / `require_scoped_permission(scope_type='advertiser')`; RLS на 38 таблицах по `app.rmp_is_admin` / `app.rmp_scope_retailer_ids` / `app.rmp_scope_advertiser_ids` |
| Расхождение с Q2 | нет bundles `campaign_manager`, `moderator`, `approver`, `ops_operator`; `security_admin` as-built шире Q2 (несёт `campaigns.manage/approve`, `creatives.moderate`, `inventory.manage`, `users.manage`); внутренние сотрудники **не имеют retailer scope** — все unscoped/global |

## 2. Целевая модель (Q2, OD-035, OD-003)

### 2.1 Persona → роль → bundle (только существующие коды; новых кодов не вводится)

| Persona (Q2) | Код роли | Bundle (permission codes) | Scope | Статус |
|---|---|---|---|---|
| Администратор системы | `system_admin` | все 30 | global (admin bypass) | as-built ✔ |
| Администратор безопасности | `security_admin` | `audit.read`, `emergency.read/manage`, `users.read` (просмотр AD-настроек/тест — через `users.manage`? см. D1), `campaigns.read`, `devices.read`, `license.read`, `roles.read` | global (admin bypass по OD-003) | as-built шире — **D1** |
| Менеджер кампаний | `campaign_manager` | `campaigns.read/manage`, `creatives.read`, `inventory.read/manage`, `advertisers.read/manage`, `advertisers.contacts.read/manage`, `advertiser_applications.read/review`, `commerce.tariff_read/manage`, `commerce.order_read/manage`, `organization.read`, `channels.read` | **retailer** | создать (RM-STAB-004) |
| Модератор креативов | `moderator` | `creatives.read`, `creatives.moderate`, `campaigns.read` | retailer | создать |
| Согласующий | `approver` | `campaigns.read`, `campaigns.approve`, `creatives.read` | retailer | создать |
| Оператор эксплуатации | `ops_operator` | `devices.read`, `emergency.read/manage`, `channels.read`, `campaigns.read` | retailer | создать; `operator` остаётся alias-ролью с тем же bundle на период миграции (OD-035) |
| Аналитик | `analyst` | as-built read-only (`audit.read`, `campaigns.read`, `channels.read`, `creatives.read`, `devices.read`, `organization.read`) | retailer | вне каталога Q2 §2 — **D2** |
| Рекламодатель | `advertiser` | `campaign_briefs.manage`, `campaigns.read`, `creatives.read`, `advertisers.read`, `advertisers.contacts.read`, `organization.read` | advertiser → retailer (ADR-018) | as-built ✔ (CAMPAIGN-PERMISSION-SPLIT-001) |
| Потенциальный рекламодатель | `public_lead` | без логина: `POST /api/v1/public/applications` | — | as-built ✔ |

Инвариант: **self-approval запрещён** — `approver` не несёт `campaigns.manage`; `campaign_manager` не несёт `campaigns.approve` (AC-126). `system_admin` несёт оба — это break-glass, а не рабочий персонаж (аудит фиксирует).

### 2.2 Retailer scope для внутренних ролей

- `user_roles.scope_type='retailer'`, `scope_id=<retailer_id>` (колонки существуют; миграции схемы не нужно).
- `resolve_scope_context`: ветка `scope_type == "retailer"` → `retailer_scope_ids.add(scope_id)`; permissions такой роли попадают в `all_permissions`, **не** в `global_permissions` (adapt: существующие unscoped-назначения продолжают работать).
- `require_scoped_permission(code, scope_type="retailer")` — новая ветка по образцу `advertiser`: есть `retailer_scope_ids` и permission → pass; есть scope без permission → `PERMISSION_DENIED`; нет scope → `SCOPE_RESTRICTED`.
- RLS уже фильтрует по `app.rmp_scope_retailer_ids` (миграции 020/022/033/035) — политики не меняются.
- Bypass retailer scope — только unscoped `system_admin`/`security_admin` (OD-003). Scoped admin ≠ global admin (сохраняется).
- Пилот — один retailer (seed): по умолчанию все внутренние не-admin учётки получают scope на seeded retailer — **D3**.

### 2.3 Миграция (RM-STAB-004, additive-first, owner gate `migration_application`)

1. Seed/миграция данных: 4 новых роли + `role_permissions` по таблице 2.1; `operator` не удаляется, его bundle = `ops_operator` (alias); существующие `user_roles` не трогаются.
2. `resolve_scope_context` + `require_scoped_permission('retailer')` (adapt, покрывается unit `tests/test_phase3_scope_context.py`, `tests/test_phase3_scoped_permission.py`).
3. Маршруты: `campaigns/creatives/inventory/advertisers/commerce/devices/emergency` переводятся на `require_scoped_permission(code, "retailer")` там, где сейчас `require_permission` (unscoped admin проходит как раньше).
4. Portal: permission-descriptions registry (D2 UX) пополняется новыми ролями (REQ-UX-005).
5. Rollback: down-миграция удаляет 4 роли и их role_permissions; `operator` и все существующие назначения остаются.

### 2.4 Acceptance/evidence (для RM-STAB-004/007)

| Проверка | Evidence |
|---|---|
| positive: каждая Q2-роль под intended-user проходит свои journeys; negative: без permission — 403 `PERMISSION_DENIED`; без scope — 403 `SCOPE_RESTRICTED` | `tests/behavioral/test_retailer_scope_rbac.py` (новый) |
| cross-retailer: `campaign_manager` ретейлера A не видит/не меняет кампании ретейлера B (RLS, роль приложения NOBYPASSRLS) | тот же файл + `tests/behavioral/test_scope_rls.py` |
| self-approval: `approver` не может создать/изменить кампанию; `campaign_manager` не может одобрить | `tests/behavioral/test_c1_moderation_approval_rls.py` (расширение) |
| alias `operator` == `ops_operator` bundle; существующие пользователи не теряют права | `tests/test_s019_role_safety.py`, `tests/test_phase3_user_management.py` |
| UI intended-role smokes для critical journeys | `tests/ui-smoke/ci-subset.txt` (RM-STAB-007) |

Регрессия (OD-042): существующие smokes/behavioral соседних journeys не меняются; `security_admin` — см. D1.

## 3. Решения владельца (owner gate `scope_decision`)

| # | Вопрос | Рекомендация |
|---|---|---|
| D1 | `security_admin` as-built шире Q2 | **Принято (OD-044):** сузить в RM-STAB-015 отдельной миграцией с negative-тестами; RM-STAB-004 существующий bundle не трогает |
| D2 | `analyst` отсутствует в каталоге Q2 §2 | **Принято (OD-044):** внутренняя read-only роль с retailer scope; добавлена в каталог `user-journeys.md` §2 |
| D3 | Retailer scope внутренним non-admin по умолчанию в pilot | **Принято (OD-044):** seed назначает scope на seeded retailer всем внутренним non-admin учёткам |

ACCEPT записан `OD-044` (2026-08-31); RM-STAB-006 стартовала; RM-STAB-004 стартует после RM-STAB-006 (OD-043).
