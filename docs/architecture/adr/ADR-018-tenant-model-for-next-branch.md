# ADR-018 — Tenant Model for v2.6 Next Branch

| **Status:** Proposed
| **Date:** 2026-07-11
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

Если сейчас начать реализацию v2.6 без явного решения tenant model,
придётся переписывать attribution, finance, targeting, competitive separation
и часть RLS при переходе к multi-retailer.

## Decision (Proposed — НЕ принято)

Для **текущего первого ТЗ (v2.5):** не переписывать существующие таблицы.
Текущий single-retailer RLS остаётся.

Для **новых доменов v2.6:** до начала реализации принять явное решение
по одному из вариантов ниже.

## Options

### Вариант A: Permanent Single-Retailer Platform

**Суть:** платформа навсегда для одной сети (Верный). Никакой multi-tenancy.

**Плюсы:**
- Минимальная сложность. Все текущие решения валидны.
- Не нужно переписывать RLS, scopes, таблицы.
- Быстрее до production.

**Минусы:**
- Невозможно продать платформу другой сети.
- Любая попытка multi-retailer в будущем = полный рерайт доменов.
- Attribution/competitive separation — либо не нужны, либо только внутри одной сети.

### Вариант B: Future Multi-Retailer / Syndication-Ready

**Суть:** архитектура, готовая к нескольким ритейлерам на одной платформе.

**Плюсы:**
- Platform business model возможна.
- Attribution между ритейлерами, competitive separation, syndication.
- Не надо переписывать v2.6 домены позже.

**Минусы:**
- Требует `retailer_id` / `network_id` на всех новых таблицах.
- RLS нужно расширять до multi-tenant (retailer + advertiser).
- Сложнее, дольше до первого результата.
- Нужно решить: общий пул рекламодателей или per-retailer?

## Recommendation

**Для текущего первого ТЗ:** держать single-retailer, не трогать существующие таблицы.

**Для v2.6 доменов:** до написания первого кода провести explicit P0 review
и выбрать вариант A или B. Решение зафиксировать в этом ADR (status: Accepted).

**Временная рекомендация:** если v2.6 начнётся в ближайшие 3-6 месяцев —
вариант B (multi-retailer ready) с минимальным оверхедом (поле `retailer_id`
на новых таблицах). Если v2.6 откладывается на 12+ месяцев — отложить решение.

## Consequences

- **Без решения:** v2.6 домены будут написаны под single-retailer, и любая
  попытка multi-tenancy потребует миграции данных и переписывания логики.
- **Вариант A:** быстрее, но замораживает архитектуру навсегда.
- **Вариант B:** медленнее сейчас, но сохраняет platform-амбиции.

## References

- `docs/product/requirements/TZ_Retail_Media_Platform_v2_6_Next_Branch_2026-07-11.docx`
- `docs/product/requirements/README.md`
- ADR-006 (User Identity and RBAC)
- ADR-009 (Fail-Closed Scopes and PostgreSQL RLS)
- ADR-010 (Advertiser Domain Foundation)
