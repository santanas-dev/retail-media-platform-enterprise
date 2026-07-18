# ADR-018 — Tenant Model for v2.6 Next Branch

| **Status:** Accepted
| **Date:** 2026-07-11 (proposed), 2026-07-17 (accepted — PLAN-001)
| **Author:** P.S. (via Hermes)
| **Replaces:** None
| **Superseded by:** None

## Context

Текущая платформа (первое ТЗ v2.5) спроектирована как **single-retailer**:
одна сеть магазинов, одна организация-владелец, один `advertiser_organizations`
пул. RLS построен вокруг `app.rmp_scope_advertiser_ids`, tenant = advertiser
organization.

v2.6 Next Branch вводит новые домены, которые фундаментально зависят от
понятия «кто владеет данными»:
- **Attribution & Sales Lift** — чьи продажи измеряем?
- **Finance / invoicing** — кто кому выставляет счета?
- **Competitive Separation** — кто чей конкурент?
- **Store-level audience targeting** — чьи магазины / аудитории?

## Decision (Accepted — PLAN-001, 2026-07-17)

**Вариант B: Multi-Retailer / Syndication-Ready.**

Решение владельца продукта (PLAN-001): мультиарендность закладываем сейчас.

### Tenant model

- **Уровень 1 — Retailer (retailer_id).** Верхний tenant boundary. Каждый
  ритейлер — отдельная сеть магазинов, со своими `advertiser_organizations`,
  кампаниями, устройствами, данными PoP.
- **Уровень 2 — Advertiser (advertiser_organization_id).** Второй уровень
  внутри retailer. Рекламодатели привязаны к конкретному ритейлеру.
- **Двухуровневая RLS:** каждая tenant-таблица получает `retailer_id` +
  существующий advertiser scope.
- **Admin bypass:** только для `system_admin` / `security_admin` с
  unscoped ролью (существующий паттерн ADR-009).

### Per-retailer advertiser pool

Advertiser принадлежит ровно одному ритейлеру. Cross-retailer advertiser
видимость невозможна. Advertiser_id внутри разных ритейлеров могут совпадать
(синтетические UUID) — изоляция гарантируется RLS на уровне `retailer_id`,
не на уровне совпадения id.

### Что изменяется

| Что | Было | Стало |
|-----|------|-------|
| Tenant boundary | advertiser_organization_id | retailer_id + advertiser_organization_id |
| RLS переменная | `app.rmp_scope_advertiser_ids` | + `app.rmp_scope_retailer_ids` |
| ScopeContext | `advertiser_scope_ids` | + `retailer_scope_ids` |
| RLS политики | 1 уровень (advertiser) | 2 уровня (retailer AND advertiser) |
| Таблицы | Без `retailer_id` | `retailer_id NOT NULL` на всех tenant-таблицах |

### Migration strategy

1. Создать таблицу `retailers` (id, code, legal_name, display_name, status).
2. Добавить `retailer_id` (NULLABLE) на все tenant-таблицы.
3. Создать default retailer (`code='default'`, `display_name='Default Retailer'`).
4. Заполнить `retailer_id` = default для всех existing rows.
5. `ALTER ... SET NOT NULL` для `retailer_id`.
6. Создать FK `retailer_id → retailers(id)`.
7. Обновить все RLS-политики на двухуровневые.
8. `ScopeContext` + `set_rls_context` добавить `app.rmp_scope_retailer_ids`.
9. `resolve_scope_context` резолвить retailer scope из `advertiser_organizations.retailer_id`.
10. Обновить seed/fixtures под default retailer.

### Compatibility impact

- **Существующие single-retailer данные:** backfill default retailer — без потерь.
- **API:** без изменений (retailer_id прозрачен для advertiser-scoped пользователей).
- **Cross-retailer:** невозможно случайно увидеть данные другого ритейлера
  благодаря двухуровневой RLS (fail-closed: пустой scope → deny-all).

## Consequences

- **ADR-018 реализован.** ADR-018-IMPL-001 добавляет retailer_id + двухуровневую RLS.
- **Следующий workstream:** Edge/player (фаза 1) — после green CI ADR-018-IMPL-001.
- **Отложено:** attribution/чеки (бизнес-решение), self-service (фаза 5),
  store-local time ADR (фаза 0.5, после ADR-018).

## References

- PLAN-001 — Strategic Product Decisions (2026-07-17)
- ADR-006 (User Identity and RBAC)
- ADR-009 (Fail-Closed Scopes and PostgreSQL RLS)
- ADR-010 (Advertiser Domain Foundation)
