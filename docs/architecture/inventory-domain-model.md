# Inventory Domain — Architecture Design

**Document:** docs/architecture/inventory-domain-model.md
**Created:** 2026-07-16
**Branch:** docs/S-076-inventory-domain-model-design
**Status:** architecture design — pre-implementation. S-077 schema/repository implementation in progress.
**Predecessor:** `docs/product/inventory-domain-gap-analysis.md` (S-072)
**Audit:** Closes gap G-INV-01…G-INV-10 per ТЗ §6.3

---

## 1. Purpose

This document defines the architecture of the inventory domain — the
business subsystem responsible for answering: **«Мы можем показать вашу
рекламу X раз на этих поверхностях в это время»**.

It covers:

- Entity model (what data exists and how it relates)
- Lifecycle (how inventory moves through states)
- Conflict rules (what blocks a placement)
- Availability calculation (how capacity is computed)
- API candidates (what endpoints expose the domain)
- UI candidates (what admin sees)
- Acceptance criteria and implementation sequence

**Текущее состояние (v0.6.2):** каталог магазинов и поверхностей
с toggle `is_active`. Нет эфирного времени, нет бронирования, нет
конфликт-детекции.

---

## 2. Entity Model

### 2.0 Reused Entities (no changes)

| Entity | Table | Reuse |
|--------|-------|-------|
| Store | `stores` | Location hierarchy — leaf of branch→cluster→store→surface |
| DisplaySurface | `display_surfaces` | Target of placement — has resolution, is_active |
| Branch | `branches` | Organisational grouping |
| Cluster | `clusters` | Geographical grouping of stores |
| CampaignPlacement | `campaign_placements` | Source of SOV, max_impressions, target surface/store/cluster |
| CampaignFlight | `campaign_flights` | Source of date range, dayparting, days_of_week |
| DeliveryManifest | `delivery_manifests` | Confirmation: placement was actually delivered |
| EmergencyOverride | `emergency_overrides` | Impact: emergency_blocked on inventory slots |
| PhysicalDevice | `physical_devices` | Impact: offline devices reduce capacity |

### 2.1 InventorySlot — атомарная единица инвентаря

```
InventorySlot
├── id: UUID
├── display_surface_id: FK → display_surfaces.id
├── date: Date
├── hour: int (0..23)
├── slot_duration_s: int            — длительность стандартного рекламного слота (default 30)
├── total_slots: int                — всего доступных слотов в этом часе
├── booked_slots: int               — занято утверждёнными кампаниями
├── reserved_slots: int             — зарезервировано (pending approval)
├── internal_slots: int             — занято внутренними кампаниями сети
├── emergency_blocked: bool          — заблокировано emergency-режимом
├── offline_devices: int            — количество офлайн-устройств на этой поверхности
├── status: InventorySlotStatus     — computed: available/partial/sold_out/blocked
├── created_at: datetime
├── updated_at: datetime
```

**Purpose:** Атомарная единица инвентаря — один час одного рекламного
экрана. `total_slots` рассчитывается из пропускной способности
поверхности (resolution + device count). `booked_slots` изменяется
commit/release. `reserved_slots` изменяется reserve/commit/release.
`status` — вычисляемое поле, не хранится (computed column или property).

**Status values:**

| Status | Condition |
|--------|-----------|
| `available` | `booked_slots + reserved_slots < total_slots` и не `emergency_blocked` |
| `partial` | `0 < booked_slots + reserved_slots < total_slots` |
| `sold_out` | `booked_slots + reserved_slots >= total_slots` |
| `blocked` | `emergency_blocked = true` |

**Indexes:**
- `(display_surface_id, date, hour)` — unique, lookup by calendar
- `(date, hour)` — cross-surface queries (availability snapshot)
- `status` — filtered index for sold_out/blocked queries

**RLS:** `InventorySlot` не tenant-scoped напрямую. Доступ через
`display_surface_id → store_id → cluster_id → branch_id`.
Admin-only read/write. Advertiser — косвенно через availability check
(см. API).

**Audit/Outbox:** `inventory.slot.reserved`, `inventory.slot.committed`,
`inventory.slot.released`, `inventory.slot.emergency_blocked`,
`inventory.slot.emergency_unblocked`.

### 2.2 InventoryBooking — бронирование инвентаря

```
InventoryBooking
├── id: UUID
├── campaign_id: FK → campaigns.id
├── campaign_placement_id: FK → campaign_placements.id
├── inventory_slot_id: FK → inventory_slots.id
├── booked_slots: int               — сколько слотов забронировано
├── status: BookingStatus           — reserved / committed / released / expired
├── reserved_at: datetime
├── committed_at: datetime | null
├── released_at: datetime | null
├── reason: str | null              — причина release/expire
├── created_at: datetime
├── updated_at: datetime
```

**Purpose:** Связь «кампания → слот инвентаря». Одна кампания может
забронировать несколько слотов (несколько часов × несколько поверхностей).
`status` управляется lifecycle-методами.

**Indexes:**
- `(inventory_slot_id, status)` — active bookings per slot
- `(campaign_id, status)` — bookings per campaign
- `(campaign_placement_id)` — lookup by placement

**RLS:** Доступ через campaign → advertiser → organisation. Admin — full.
Advertiser — read own (через campaign_id). Tenant-защита через FK-цепочку.

**Audit/Outbox:** `inventory.booking.reserved`, `inventory.booking.committed`,
`inventory.booking.released`, `inventory.booking.expired`.

### 2.3 InventoryRule — бизнес-правила инвентаря

```
InventoryRule
├── id: UUID
├── scope_type: str                  — network / branch / cluster / store / surface
├── scope_id: UUID | null            — FK в зависимости от scope_type (null = network-wide)
├── rule_type: str                   — max_ad_load / slot_duration / prime_time / priority / filler
├── value_json: JSONB                — параметры правила (зависят от rule_type)
├── priority: int                    — приоритет правила (чем выше, тем приоритетнее)
├── is_active: bool
├── created_at: datetime
├── updated_at: datetime
```

**Rule types:**

| rule_type | value_json | Example |
|-----------|------------|---------|
| `max_ad_load` | `{"max_pct": 30}` | Не более 30% эфирного времени на рекламу |
| `slot_duration` | `{"duration_s": 30}` | Длительность рекламного слота 30 секунд |
| `prime_time` | `{"start": "17:00", "end": "21:00"}` | Прайм-тайм: 17:00–21:00 |
| `priority` | `{"campaign_priority": "high", "boost_pct": 20}` | Кампании high-приоритета получают +20% слотов |
| `filler` | `{"creative_asset_id": "uuid"}` | Filler-контент при отсутствии рекламы |
| `overbooking` | `{"allowed_pct": 10}` | Разрешённый overbooking в процентах (default: 0) |

**Scope resolution:** Правила применяются от более специфичных к общим:
surface → store → cluster → branch → network. При конфликте
побеждает более специфичное правило. `priority` работает внутри
одного scope.

**Indexes:**
- `(scope_type, scope_id, rule_type)` — lookup rules for scope
- `(is_active)` — filter active rules

**RLS:** Admin-only. Rules apply globally, не per-tenant.

**Audit/Outbox:** `inventory.rule.created`, `inventory.rule.updated`,
`inventory.rule.deleted`.

### 2.4 InventoryAvailabilitySnapshot — снимок доступности (вычисляемый)

**Not a physical table.** Это read-model, вычисляемая на лету из
`inventory_slots` + `inventory_rules` + `campaign_placements` + `physical_devices`.

Вычисляется для запроса: «сколько слотов доступно по
surface/store/cluster/branch/date/hour/time-window/шойс».

**Output shape (API response, not DB row):**

```json
{
  "surface_id": "uuid",
  "store_id": "uuid",
  "date": "2026-07-20",
  "hour": 14,
  "total_slots": 120,
  "booked_slots": 80,
  "reserved_slots": 10,
  "internal_slots": 5,
  "available_slots": 25,
  "sold_out": false,
  "blocked": false,
  "offline_devices": 0,
  "overbooking_allowed_pct": 0,
  "effective_capacity": 120
}
```

### 2.5 InventoryConflict — конфликт (вычисляемый)

**Not a physical table.** Вычисляется при проверке размещения (placement
creation, approval, pre-publication simulation).

**Conflict types:**

| Conflict | Detection | Severity | Blocking |
|----------|-----------|----------|----------|
| `schedule_overlap` | Два placement'а на одной поверхности в одном часу превышают capacity | Critical | Yes |
| `sov_overbooking` | Сумма SOV всех approved placement'ов > 100% | Critical | Yes |
| `inactive_surface` | `display_surface.is_active = false` | Critical | Yes |
| `inactive_store` | `store.is_active = false` | Critical | Yes |
| `emergency_blocked` | `inventory_slot.emergency_blocked = true` | Critical | Yes |
| `date_outside_flight` | Campaign date выходит за flight.start_at/end_at | High | Yes |
| `dayparting_violation` | Placement hour вне dayparting часов | High | Warning |
| `max_ad_load_exceeded` | Превышен max_ad_load для scope | High | Warning |
| `competitor_conflict` | Две кампании конкурирующих брендов на одной поверхности | Medium | Warning (MVP: deferred) |
| `priority_inversion` | Low-priority кампания блокирует high-priority | Medium | Warning |
| `offline_device_impact` | Часть устройств офлайн → реальная ёмкость ниже расчётной | Low | Info |

---

## 3. Booking Lifecycle

### 3.1 States

```
                 ┌──────────┐
    reserve ───► │ reserved │ ───► commit ───► ┌───────────┐
                 └──────────┘                   │ committed │
                      │                         └───────────┘
                      │ release                       │
                      ▼                               │ release/archive
                 ┌──────────┐                         ▼
                 │ released │ ◄─── release ──── ┌───────────┐
                 └──────────┘                    │ released  │
                                                 └───────────┘

  reserved ─── expire (TTL) ──► expired
  committed ─── expire (campaign end) ──► expired
```

### 3.2 Lifecycle transitions

| Transition | Trigger | Validation | Side effects |
|------------|---------|------------|-------------|
| `→ reserved` | Campaign placement created (draft) | Availability check returns `available_slots >= requested` | `reserved_slots += N` on InventorySlot. Outbox: `inventory.booking.reserved` |
| `reserved → committed` | Campaign approved | Slot still available (not sold_out/blocked). TTL not expired. | `reserved_slots -= N`, `booked_slots += N`. Outbox: `inventory.booking.committed` |
| `reserved → released` | Campaign rejected OR placement deleted | — | `reserved_slots -= N`. Outbox: `inventory.booking.released` |
| `committed → released` | Campaign archived/cancelled | — | `booked_slots -= N`. Outbox: `inventory.booking.released` |
| `reserved → expired` | TTL exceeded (default: 24h) | `reserved_at + TTL < now()` | `reserved_slots -= N`. Outbox: `inventory.booking.expired` |
| `committed → expired` | Campaign end_at passed | `campaign.end_at < now()` | `booked_slots -= N`. Outbox: `inventory.booking.expired` |

### 3.3 TTL strategy

- **Reservation TTL:** 24 часа. Если кампания не отправлена на
  согласование за 24 часа, резерв автоматически снимается.
  Background job (cron) или lazy-проверка при следующем запросе
  availability.
- **Commitment TTL:** Campaign `end_at`. Автоматический release после
  завершения кампании. Background job.

### 3.4 Overbooking policy

- **Default:** overbooking запрещён (`overbooking_allowed_pct = 0`).
- Правило `InventoryRule(rule_type='overbooking', value_json={"allowed_pct": 10})`
  разрешает до 10% сверх `total_slots`.
- Overbooking применяется только на уровне committed (approved), не на reserved.
- При превышении overbooking-лимита — conflict `sov_overbooking` (Critical).

---

## 4. Campaign Integration Points

| Campaign Lifecycle Event | Inventory Action |
|--------------------------|-----------------|
| `POST /campaigns/{id}/placements` (draft) | `POST /inventory/reservations` — проверка доступности + резервирование. При конфликте: 409 Conflict с перечнем конфликтов. |
| `POST /campaigns/{id}/request-approval` | `GET /inventory/conflicts?campaign_id=X` — проверка конфликтов перед отправкой на согласование. При Critical-конфликтах: 409 «Устраните конфликты перед согласованием». |
| `POST /campaigns/{id}/approve` | `POST /inventory/reservations/{id}/commit` — подтверждение всех reserved booking'ов кампании. Транзакционно с approve. |
| `POST /campaigns/{id}/reject` | `POST /inventory/reservations/{id}/release` — освобождение всех booking'ов. |
| `PATCH /campaigns/{id}` (archive) | `POST /inventory/reservations/{id}/release` — освобождение committed booking'ов. |
| `POST /emergency/activate` | Все активные InventorySlot'ы: `emergency_blocked = true`. Все reserved → release. Outbox: `inventory.slot.emergency_blocked`. |
| `POST /emergency/deactivate` | `emergency_blocked = false`. Outbox: `inventory.slot.emergency_unblocked`. |

---

## 5. Availability Calculation Contract

### 5.1 Input

```
GET /inventory/availability?surface_id=...&store_id=...&cluster_id=...&date=2026-07-20&hour=14&window_hours=4&sov_pct=30
```

| Param | Required | Description |
|-------|----------|-------------|
| `surface_id` | No | Конкретная поверхность. Если не указан — все активные поверхности scope. |
| `store_id` | No | Фильтр по магазину. |
| `cluster_id` | No | Фильтр по кластеру. |
| `branch_id` | No | Фильтр по филиалу. |
| `date` | Yes | Дата (YYYY-MM-DD). |
| `hour` | No | Час (0–23). Если не указан — все часы даты. |
| `window_hours` | No | Окно в часах от указанного `hour` (default: 1). |
| `sov_pct` | No | Запрашиваемая доля голоса. Если указана — проверяется, доступна ли. |

### 5.2 Output

```json
{
  "slots": [
    {
      "surface_id": "uuid",
      "surface_code": "KSK-001",
      "store_id": "uuid",
      "store_name": "Верный — Пушкина 42",
      "date": "2026-07-20",
      "hour": 14,
      "total_slots": 120,
      "booked_slots": 80,
      "reserved_slots": 10,
      "internal_slots": 5,
      "available_slots": 25,
      "available_sov_pct": 20.8,
      "sold_out": false,
      "blocked": false,
      "offline_devices": 0,
      "effective_capacity": 120
    }
  ],
  "summary": {
    "total_surfaces": 1,
    "total_slots": 120,
    "total_available": 25,
    "sold_out_surfaces": 0,
    "blocked_surfaces": 0
  },
  "requested_sov_available": true
}
```

### 5.3 Algorithm (MVP — deterministic, rule-based)

1. **Capacity baseline:** `total_slots = (3600 / slot_duration_s) × device_count`. `device_count` из `physical_devices` со `status = 'online'`.
2. **Rules application:** `slot_duration` и `max_ad_load` из `inventory_rules` (scope resolution: surface → store → cluster → branch → network).
3. **Bookings aggregation:** `booked_slots` = SUM(committed bookings for this slot). `reserved_slots` = SUM(reserved, not expired).
4. **Internal slots:** зарезервировано под `internal`-кампании (campaign.priority = 'internal').
5. **Emergency:** если любой EmergencyOverride активен → `blocked = true`, `available_slots = 0`.
6. **Offline devices:** `effective_capacity = total_slots × (online_devices / (online_devices + offline_devices))`.
7. **SOV check:** `available_sov_pct = available_slots / total_slots × 100`. Если `requested_sov_pct > available_sov_pct` → `requested_sov_available = false`.
8. **Forecast (future phase):** history-based prediction заменит статический capacity baseline.

---

## 6. API Candidates

### Admin-only

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| `GET` | `/inventory/availability` | `inventory.read` | Расчёт доступности — входные параметры §5.1 |
| `POST` | `/inventory/reservations` | `inventory.manage` | Зарезервировать слоты. Body: `{campaign_placement_id, slots: [{surface_id, date, hour, count}]}` |
| `POST` | `/inventory/reservations/{id}/commit` | `inventory.manage` | Подтвердить бронь (вызывается при campaign.approve) |
| `POST` | `/inventory/reservations/{id}/release` | `inventory.manage` | Освободить бронь (вызывается при campaign.reject/archive) |
| `GET` | `/inventory/conflicts` | `inventory.read` | Проверка конфликтов для campaign_id или placement_id |
| `GET` | `/inventory/calendar` | `inventory.read` | Календарь: свободно/занято/зарезервировано по store/surface/date/hour |
| `GET` | `/inventory/rules` | `inventory.read` | Список правил инвентаря |
| `POST` | `/inventory/rules` | `inventory.manage` | Создать правило |
| `PATCH` | `/inventory/rules/{id}` | `inventory.manage` | Изменить правило |
| `DELETE` | `/inventory/rules/{id}` | `inventory.manage` | Удалить правило |
| `GET` | `/inventory/report/availability` | `inventory.read` | Отчёт: свободно/занято/зарезервировано |
| `GET` | `/inventory/report/sla` | `inventory.read` | Отчёт по SLA размещения |

### Advertiser-visible (future release)

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| `GET` | `/inventory/availability-hint` | `campaigns.read` | Упрощённый availability hint при создании кампании («На этой поверхности доступно ~30% в это время»). Без детальных цифр. |

### Scope / RLS

- **Admin:** full access, no tenant filter. `require_permission(inventory.read)` / `inventory.manage`.
- **Advertiser:** только `availability-hint` (future). Фильтр через `campaign_placements → campaigns → advertiser_organization_id`.

---

## 7. UI Candidates

### Admin-web

| Page / Component | Description | Priority |
|-----------------|-------------|----------|
| **InventoryCalendarPage** | Календарь доступности — цветовая кодировка статусов (зелёный/жёлтый/красный/серый) по store/surface/date/hour. Фильтры: филиал, кластер, магазин, дата. | P0 (S-081) |
| **AvailabilityChecker** | Панель проверки доступности — ввод surface/date/hour/SOV → вывод available_slots + conflicts. Интеграция в CampaignCreatePage/CampaignDetailPage. | P0 (S-081) |
| **ConflictPanel** | Предупреждение о конфликтах в approval flow — список конфликтов с severity + блокирующие/неблокирующие. | P0 (S-080) |
| **InventoryRulesPage** | CRUD правил инвентаря — таблица + create/edit modal. Фильтр по scope_type / rule_type. | P1 (S-080) |
| **SoldOutView** | Магазины/периоды без доступного инвентаря + альтернативы (рекомендации ближайших доступных слотов). | P1 (S-082) |
| **InventoryReportPage** | Отчёт: свободно/занято/зарезервировано + SLA метрики. | P1 (S-083) |

### Advertiser-web (future)

| Component | Description |
|-----------|-------------|
| **AvailabilityHint** | При создании placement — индикатор доступности (✅ Доступно / 🟡 Частично / 🔴 Sold-out). Без детальных цифр. |

---

## 8. S-Ticket Sequence (revised from S-072)

### Phase 1 — Foundation (MVP inventory domain)

| Ticket | Description | Depends on | Deliverable |
|--------|-------------|-----------|-------------|
| **S-077** | Inventory schema + migrations + repository skeleton | S-076 | `inventory_slots`, `inventory_bookings`, `inventory_rules` tables. Migration. Repository methods (CRUD). Seed. |
| **S-078** | Availability calculator MVP | S-077 | `GET /inventory/availability`. `compute_availability()` in repository. Deterministic rule-based. Unit + behavioural tests. |
| **S-079** | Reservation lifecycle + campaign integration | S-077, S-078 | `POST /inventory/reservations` + `/commit` + `/release`. Integration: placement creation → reserve, approve → commit, reject → release. TTL expiry. |
| **S-080** | Conflict detection MVP | S-077, S-079 | `GET /inventory/conflicts`. 8 conflict types. Integration: approval gate. Inventory rules CRUD. |

### Phase 2 — Visibility & Reporting

| S-081 | Inventory calendar UI + availability checker | S-079, S-080 | Admin-web: InventoryCalendarPage. CampaignCreatePage integration. |
| S-082 | Sold-out detection + alternatives | S-079 | SoldOutView component. «Предложить альтернативный магазин/время». |
| S-083 | Inventory reports + SLA | S-079 | `/inventory/report/availability`, `/inventory/report/sla`. Admin-web reports. |

### Phase 3 — Runtime Integration

| S-084 | Emergency impact on inventory | S-071, S-079 | Emergency activate → `emergency_blocked = true`, release all reserved. |
| S-085 | Device health impact on inventory | S-070, S-079 | Offline devices reduce `effective_capacity`. Recalculate on device status change. |
| S-086 | Forecast engine | S-078, PoP data | History-based prediction. ML/statistical — deferred to separate spike. MVP: static capacity baseline. |

### Phase 4 — v2.6+ (Deferred)

- Pricing / rate cards / billing
- Programmatic / RTB / DSP / SSP
- Sales lift / attribution
- ClickHouse migration for inventory analytics
- Audience targeting / DMP
- Competitor blocking

---

## 9. Acceptance Criteria for S-077 Implementation

- [ ] `InventorySlot`, `InventoryBooking`, `InventoryRule` ORM models defined in `packages/domain/models.py`
- [ ] Migration creates three tables with correct columns, FK, indexes
- [ ] Seed data: sample slots for test surfaces (at least 3 days × 24 hours), one default rule (max_ad_load=30%)
- [ ] Repository: `create_slot`, `get_slots_by_surface_date`, `update_slot_counts`, `create_booking`, `get_bookings_by_campaign`, `update_booking_status`
- [ ] `get_or_create_slot()` — идемпотентное создание слота (дата/час/поверхность)
- [ ] `InventorySlotStatus` enum + computed property
- [ ] Unit tests: slot creation, count updates (reserved/booked), status transitions
- [ ] Behavioural tests: slot creation is idempotent, booking status lifecycle (reserved→committed→released)
- [ ] Permissions: `inventory.read`, `inventory.manage` (already exist in seed)
- [ ] RLS: `inventory_slots`, `inventory_bookings`, `inventory_rules` — admin-only. No advertiser access in MVP.

---

## 10. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Over-engineering slots — 365 дней × 24 часа × N surfaces = много строк | Medium | Lazy creation: `get_or_create_slot()` создаёт только когда запросили. Не прегенерируем год вперёд. |
| TTL expiry фоновой задачей нестабилен | Medium | Lazy expiry: проверка TTL при каждом `compute_availability()`. Фоновая задача — оптимизация, не обязана работать. |
| Forecast без ML — неточный | Low | MVP: static capacity baseline. «Прогноз = ёмкость». Честный disclaimer. ML-forecast — отдельный spike. |
| Booking idempotency при retry | Medium | `(campaign_placement_id, inventory_slot_id)` — unique constraint. Retry reserve возвращает существующий booking. |
| Race condition: concurrent reserve на один слот | Medium | `SELECT ... FOR UPDATE` на `inventory_slots` при reserve/commit/release. См. S-064 approval pattern. |
| Emergency impact — race с commit/release | Low | Emergency activate: `SELECT ... FOR UPDATE` на всех слотах, затем обновление. Транзакционно. |

---

## 11. Decision Log

| # | Decision | Rationale |
|---|----------|-----------|
| D1 | Slots per hour, not per minute/second | Час — достаточная гранулярность для MVP. 30-секундные слоты — 120/час — детализация через `slot_duration`. |
| D2 | `total_slots` — static capacity, не history-based | Прогноз на основе истории — отдельная фаза (S-086). MVP: capacity = resolution-based formula. |
| D3 | Booking, not Reservation naming | «Booking» — общепринятый термин в ad-tech. Reservation путается с restaurant/hotel domain. |
| D4 | `InventoryRule` — JSONB `value_json`, не отдельные колонки | Разные rule_type имеют разные параметры. JSONB позволяет добавить rule_type без миграции. |
| D5 | Admin-only inventory read/write в MVP | Advertiser получит availability-hint позже, когда будет advertiser-web campaign creation. |
| D6 | Overbooking default = 0% (запрещён) | ТЗ §21.5: «По умолчанию overbooking запрещён». Правило `overbooking` включает явно. |
| D7 | `emergency_blocked` на уровне слота, не всей поверхности | Позволяет частичную блокировку (например, только прайм-тайм). Сейчас emergency применяется глобально (S-071), но модель готова к гранулярности. |

---

## 12. References

- `docs/product/inventory-domain-gap-analysis.md` — S-072 gap analysis
- `docs/00-source-of-truth/TZ_Retail_Media_Platform_v2_5_Final_Hermes.extracted.md` — §6.3, §21, §23.6
- `docs/architecture/adr/ADR-015-campaign-domain.md` — campaign lifecycle, placement model
- `docs/architecture/adr/ADR-016-delivery-manifest.md` — manifest generation, eligibility
- `docs/architecture/adr/ADR-017-pop-reporting.md` — PoP ingestion, план/факт
- `packages/domain/models.py` — Store, DisplaySurface, CampaignPlacement, EmergencyOverride
- S-064 approval concurrency pattern — `SELECT ... FOR UPDATE` for atomic transitions
