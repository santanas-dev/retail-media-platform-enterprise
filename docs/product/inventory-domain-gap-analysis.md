# Inventory Domain — Gap Analysis and Implementation Plan

**Document:** docs/product/inventory-domain-gap-analysis.md
**Created:** 2026-07-16
**Branch:** docs/S-072-inventory-domain-gap-analysis
**Status:** approved gap analysis
**Audit finding:** S-037 — «Инвентарь» сейчас является каталогом магазинов/поверхностей, но не полным доменом рекламного инвентаря по ТЗ §6.3.

---

## 1. Current State — What Exists Today

### 1.1 Models (Static Catalog)

| Table | Purpose | Inventory-relevant fields |
|-------|---------|---------------------------|
| `branches` | Филиалы (организационные единицы) | `id`, `code`, `name` |
| `clusters` | Кластеры магазинов | `id`, `code`, `name` |
| `stores` | Магазины | `id`, `code`, `name`, `address`, `branch_id`, `cluster_id`, `is_active` |
| `display_surfaces` | Рекламные поверхности (экраны) | `id`, `code`, `store_id`, `resolution_w`, `resolution_h`, `is_active` |
| `logical_carriers` | Логические носители | `id`, `code`, `display_surface_id`, `media_type_id`, `is_active` |
| `device_types` | Типы устройств | `id`, `code`, `name` |
| `channels` | Каналы | `id`, `code`, `name` |
| `physical_devices` | Физические устройства | `id`, `code`, `store_id`, `device_type_id`, `status`, `os_version`, `ip_address`, `last_seen_at`, `cache_size_bytes` |

### 1.2 Campaign / Placement Models

| Model | Inventory-relevant fields |
|-------|---------------------------|
| `campaigns` | `status`, `priority`, `budget_limit_amount`, `start_at`, `end_at`, `timezone` |
| `campaign_flights` | `start_at`, `end_at`, `dayparting_json`, `days_of_week`, `priority` |
| `campaign_placements` | `display_surface_id` / `store_id` / `cluster_id` / `branch_id`, `share_of_voice_pct`, `max_impressions`, `impressions_delivered`, `status` |
| `campaign_creatives` | `campaign_id`, `creative_asset_id`, `sort_order`, `duration_override_ms` |
| `delivery_manifests` | `campaign_id`, `physical_device_id`, `content_hash`, `manifest_version`, `status` |
| `delivery_manifest_surfaces` | `manifest_id`, `display_surface_id`, `slot_order` |

### 1.3 API Endpoints

| Endpoint | Description | What it DOES |
|----------|-------------|-------------|
| `GET /branches` | Справочник филиалов | Static list, no time/availability data |
| `GET /clusters` | Справочник кластеров | Static list |
| `GET /stores` | Справочник магазинов | Static list |
| `GET /display-surfaces` | Справочник поверхностей | Static list |
| `GET /inventory/stores` | Пагинированный список магазинов | Stores + surface_count + is_active flag |
| `GET /inventory/surfaces` | Пагинированный список поверхностей | Surfaces + store info + resolution + is_active |
| `PATCH /inventory/surfaces/{id}` | Toggle is_active на поверхности | **Единственная мутация инвентаря** |

### 1.4 Admin UI

`apps/admin-web/src/pages/InventoryPage.tsx`:
- Две вкладки: «Магазины» и «Поверхности»
- Поиск по коду/названию
- Таблица с пагинацией
- Для поверхностей — кнопка «Активировать» / «Деактивировать»
- Нет календаря, нет прогноза, нет конфликтов, нет sold-out, нет правил

### 1.5 Permissions

| Permission | Назначение |
|------------|------------|
| `inventory.read` | Чтение инвентаря (только просмотр stores/surfaces) |
| `inventory.manage` | Управление инвентарём (toggle is_active) |

### 1.6 Что УМЕЕТ текущий инвентарь

- ✅ Справочник магазинов и поверхностей
- ✅ Активация/деактивация поверхностей
- ✅ Привязка placement'ов к surface/store/cluster/branch
- ✅ Поля SOV и max_impressions в placement (данные, без enforcement)
- ✅ Manifest использует display_surfaces для распределения креативов по слотам
- ✅ PoP фиксирует факт показа с привязкой к placement

### 1.7 Что НЕ УМЕЕТ текущий инвентарь

- ❌ Нет эфирного времени / календаря доступности
- ❌ Нет прогноза показов по периоду/географии/времени/типу контента
- ❌ Нет booked vs available impressions
- ❌ Нет SOV enforcement — share_of_voice_pct только записывается, не проверяется
- ❌ Нет конфликт-детекции (пересечения расписания, превышение SOV, приоритетов, лимитов)
- ❌ Нет sold-out / overbooking detection
- ❌ Нет альтернативных предложений при sold-out
- ❌ Нет статусов инвентаря: свободно/зарезервировано/продано/внутренняя/emergency
- ❌ Нет цикла резервирования инвентаря
- ❌ Нет учёта влияния emergency mode на доступный инвентарь
- ❌ Нет учёта влияния офлайн-устройств на доступный инвентарь
- ❌ Нет правил инвентаря: max ad load, slot duration, prime time, priorities, filler
- ❌ Нет отчётов по инвентарю: свободно/занято, sold-out, прогноз, SLA размещения

### 1.8 Переиспользуемые активы

| Актив | Как переиспользовать |
|-------|---------------------|
| `stores`, `display_surfaces` | Базовая иерархия локаций — останется ядром |
| `branches`, `clusters` | Группировка инвентаря по оргструктуре |
| `campaign_flights` (dayparting_json, days_of_week) | Входные данные для calendar-based availability |
| `campaign_placements` (share_of_voice_pct, max_impressions) | Входные данные для SOV enforcement и лимитов |
| `delivery_manifests` (generated_at, status) | Подтверждение факта размещения — обратная связь для «занято» |
| `pop_events_raw` | Фактические показы — основа для план/факт |
| `physical_devices` (status, last_seen_at) | Онлайн-статус устройств для учёта доступности |
| `emergency_overrides` | Влияние emergency на статус инвентаря |

---

## 2. ТЗ §6.3 — Expected Inventory Domain

Из `docs/00-source-of-truth/TZ_Retail_Media_Platform_v2_5_Final_Hermes.extracted.md`:

### 2.1 Полный перечень требований

| # | Требование | Текущий статус |
|---|-----------|---------------|
| 1 | Доступное/занятое/зарезервированное эфирное время по сети/филиалу/кластеру/магазину/устройству | ❌ Нет |
| 2 | Прогноз доступных показов по периоду/времени/географии/типу контента при создании кампании | ❌ Нет |
| 3 | Конфликт-детекция: пересечение расписания + превышение SOV + приоритеты + лимиты | ❌ Нет (только поля данных) |
| 4 | Статусы инвентаря: свободно, зарезервировано, продано, внутренняя кампания, emergency/fallback | ❌ Нет |
| 5 | Sold-out обнаружение + предложение альтернативных магазинов/периодов/времени | ❌ Нет |
| 6 | Настройка правил инвентаря в админке: max ad load, slot duration, prime time, priorities, filler | ❌ Нет |
| 7 | Отчёт по инвентарю: свободно/занято/зарезервировано, sold-out, прогноз | ❌ Нет |
| 8 | Отчёт по SLA размещения: доля онлайн, недопоказы, причины, компенсационный объём | ❌ Нет |
| 9 | Влияние emergency на инвентарь | ❌ Нет (emergency есть, но без связи с инвентарём) |
| 10 | Влияние офлайн-устройств на инвентарь | ❌ Нет (health workspace есть, но без связи с инвентарём) |

### 2.2 Бизнес-контекст

Инвентарь — это **утверждение «мы можем показать вашу рекламу X раз на этих поверхностях в это время»**. Пока этого утверждения нет — нет ценообразования, нет продаж инвентаря внешним рекламодателям, нет гарантий размещения. Текущая реализация — каталог локаций с toggle, но не бизнес-домен.

### 2.3 Что пока НЕ делаем (явно deferred)

- ❌ Pricing / rate cards / billing — v2.6+
- ❌ Programmatic / RTB / DSP/SSP интеграция — v2.6+
- ❌ Sales lift / attribution — v2.6+
- ❌ Чековая аналитика (чеки × показы) — v2.6+
- ❌ ClickHouse для аналитики инвентаря — PostgreSQL first, ClickHouse deferred
- ❌ Audience targeting / DMP — v2.6+

---

## 3. Gap Table

| Gap ID | Требование ТЗ | Текущее состояние | Приоритет | Блокирует |
|--------|--------------|-------------------|-----------|-----------|
| G-INV-01 | Эфирное время / календарь доступности | Нет модели времени | **P0** | Player/KSO, ценообразование |
| G-INV-02 | Прогноз показов | Нет калькуляции | **P0** | Создание кампаний |
| G-INV-03 | Конфликт-детекция | Поля есть, логики нет | **P0** | Approval flow |
| G-INV-04 | Статусы инвентаря | Только is_active toggle | **P0** | Жизненный цикл размещения |
| G-INV-05 | Sold-out + альтернативы | Нет | **P1** | UX менеджера |
| G-INV-06 | Правила инвентаря в админке | Нет | **P1** | Настройка бизнес-правил |
| G-INV-07 | Отчёт по инвентарю | Нет | **P1** | Принятие решений |
| G-INV-08 | SLA размещения | Нет | **P1** | Ответственность перед рекламодателем |
| G-INV-09 | Emergency impact на инвентарь | Нет связи | **P1** | Корректность при авариях |
| G-INV-10 | Offline-device impact на инвентарь | Нет связи | **P2** | Точность прогноза |

---

## 4. Proposed Architecture

> **⚠️ S-076 design phase (2026-07-16):** Architecture document created.
> See `docs/architecture/inventory-domain-model.md` for the authoritative
> entity model, lifecycle, API candidates, and S-ticket sequence.
> Gap table below preserved for traceability; detailed design in the
> architecture document.

### 4.1 Data Model Candidates

**InventorySlot (новая таблица):**
```python
class InventorySlot(Base):
    __tablename__ = "inventory_slots"
    id: str (UUID)
    display_surface_id: str (FK → display_surfaces)
    date: date
    hour: int (0..23)
    slot_duration_s: int              # стандартная длительность слота (например 30с)
    total_slots: int                  # всего слотов в этом часе
    booked_slots: int                 # занято (утверждённые кампании)
    reserved_slots: int               # зарезервировано (pending approval)
    internal_slots: int               # внутренние кампании
    emergency_blocked: bool            # заблокирован emergency
    status: str                        # available / partial / sold_out / blocked
    created_at: datetime
    updated_at: datetime
```

**InventoryRule (новая таблица):**
```python
class InventoryRule(Base):
    __tablename__ = "inventory_rules"
    id: str (UUID)
    scope_type: str                    # network / branch / cluster / store / surface
    scope_id: str                      # FK в зависимости от scope_type
    max_ad_load_pct: int               # максимальная рекламная нагрузка (%)
    slot_duration_s: int               # длительность рекламного слота
    prime_time_start: time
    prime_time_end: time
    filler_creative_id: str (nullable) # FK → creative_assets
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

### 4.2 API Candidates

| Endpoint | Description |
|----------|-------------|
| `GET /inventory/calendar` | Календарь доступности: свободно/занято/зарезервировано по store/surface/date/hour |
| `GET /inventory/forecast` | Прогноз доступных показов по фильтрам (период, гео, тип контента) |
| `POST /inventory/reserve` | Зарезервировать слоты под кампанию (pending approval) |
| `POST /inventory/commit` | Подтвердить резервирование → booked (при approval) |
| `POST /inventory/release` | Освободить слоты (отказ/rejection/завершение кампании) |
| `GET /inventory/conflicts` | Проверка конфликтов для набора placement'ов |
| `GET /inventory/rules` | Список правил инвентаря |
| `POST/PATCH /inventory/rules` | Управление правилами |
| `GET /inventory/report/availability` | Отчёт: свободно/занято/зарезервировано |
| `GET /inventory/report/sla` | Отчёт по SLA размещения |

### 4.3 UI Candidates

- **Inventory Calendar** — визуальный календарь с цветовой кодировкой статусов
- **Forecast Panel** — прогноз при создании/редактировании кампании
- **Conflict Warning** — предупреждение о конфликтах в approval flow
- **Inventory Rules Admin** — настройка правил инвентаря
- **Sold-Out View** — магазины/периоды без доступного инвентаря + альтернативы

### 4.4 Integration Points

| Интеграция | Описание |
|------------|----------|
| Campaign creation | При создании placement'а — проверка доступности + резервирование |
| Approval flow | При approve — commit reservation; при reject — release |
| Manifest generation | Подтверждение: placement реально размещён → booked_slots учтены |
| PoP ingestion | План/факт: booked vs delivered |
| Emergency | Активация → emergency_blocked = True для всех слотов |
| Device health | Офлайн-устройства → снижение доступного инвентаря |

---

## 5. Recommended S-Ticket Sequence

> **Updated in S-076.** See `docs/architecture/inventory-domain-model.md` §8
> for the revised sequence:
> S-077 (schema) → S-078 (availability) → S-079 (booking + campaign integration)
> → S-080 (conflicts + rules) → S-081 (calendar UI) → S-082 (sold-out) → S-083 (reports)
> → S-084 (emergency) → S-085 (device health) → S-086 (forecast).

### Phase 1 — Foundation (MVP inventory domain)

| Ticket | Description | Dependencies | Status |
|--------|-------------|-------------|--------|
| S-076 | Inventory domain model — architecture design (5 entities, 8 conflict types, lifecycle) | — | ✅ done |
| S-077 | Inventory schema + repository skeleton — 3 таблицы, migration 015, Pydantic схемы, CRUD | S-076 | ✅ done |
| S-078 | Availability calculator — POST /inventory/availability, почасовые слоты, SOV→units, get-or-create | S-077 | ✅ done |
| S-079 | Booking/reservation lifecycle — reserve/commit/release API + campaign integration | S-078 | ✅ done |
| S-080 | Conflict detection engine — SOV enforcement, schedule overlap, priority/limit violation | S-079 | ✅ done |
| S-081 | Inventory calendar UI — admin-web: availability checker + conflict checker + rules placeholder (4 tabs). Backend: no changes. | S-080 | ✅ done |

### Phase 2 — Visibility & Reporting

| S-082 | Sold-out detection + альтернативы | S-079 | ⏳ запланирован |
| S-083 | Inventory reports: свободно/занято, план/факт, SLA | S-079 | 1 task |

### Phase 3 — Runtime Integration

| S-084 | Emergency impact on inventory — emergency_blocked flag propagation | S-071, S-079 | 1 task |
| S-085 | Device health impact on inventory — офлайн-устройства снижают ёмкость | S-070, S-079 | 1 task |
| S-086 | Forecast engine — предсказание доступных показов на основе истории | S-079, PoP data | 1 task |

### Phase 4 — v2.6+ (Deferred)

- Pricing/rate cards
- Billing integration
- Programmatic/RTB
- Sales lift / attribution
- ClickHouse migration for inventory analytics

---

## 6. Acceptance Criteria

- [ ] InventorySlot и InventoryRule модели созданы, миграция проходит
- [ ] Availability calculator вычисляет total_slots по дате/часу/поверхности
- [ ] Reserve → commit → release lifecycle работает транзакционно
- [ ] Conflict detection блокирует размещение при превышении SOV/лимитов/пересечении
- [ ] Campaign creation интегрировано: placement → проверка доступности
- [ ] Approval flow интегрирован: approve → commit, reject → release
- [ ] Inventory calendar UI показывает свободно/занято/зарезервировано
- [ ] Sold-out отображается корректно с альтернативами
- [ ] Emergency затрагивает инвентарь: emergency_blocked = True
- [ ] Офлайн-устройства снижают доступный инвентарь

---

## 7. Player/KSO Blocking Assessment

**Player/KSO можно начинать ДО полного inventory domain при соблюдении условий:**

1. **Контракт на manifest delivery стабилен** — manifest generation, подпись, доставка работают (сейчас: ✅ done)
2. **Placement resolution детерминирован** — placement → surface → device → slot mapping однозначен (сейчас: ✅ делается статически на основе is_active)
3. **Инвентарные конфликты не обрабатываются плеером** — плеер показывает то, что в manifest; конфликты решаются на уровне платформы

**РЕКОМЕНДАЦИЯ:** Player/KSO можно начинать параллельно с S-075 (модель), но НЕ РАНЬШЕ S-079 (campaign integration). Причина: без booking lifecycle placement'ы могут конфликтовать на уровне manifest, и плеер получит противоречивые инструкции. Минимальный контракт: placement → availability check (S-076) → reserve (S-077) → approve → commit (S-077) → manifest generation.

### Минимальный inventory contract для player/KSO

| # | Что нужно | Почему |
|---|----------|--------|
| 1 | Time-slot availability (S-076) | Знать, сколько слотов доступно |
| 2 | Reserve/commit/release (S-077) | Не допустить двойного бронирования |
| 3 | Campaign integration (S-079) | Placement creation проверяет доступность |
| **Без этого** | **Player получит manifest с conflict-placement'ами** | **Плеер не будет знать, какой креатив показывать** |

---

## 8. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Inventory model complexity заблокирует player/KSO | High | MVP: только slot availability + reserve, без forecast/rules |
| Overengineering: forecast до реальных данных | Medium | Forecast MVP — базовая ёмкость, без ML/истории |
| Inventory rules слишком сложны для v0.7 | Medium | Rules MVP: только max_ad_load + slot_duration |
| Несогласованность с ADR-018 (tenant model) | Low | Inventory slots — per-surface, не tenant-scoped |
| Emergency integration размазана по фазам | Low | S-084 явно выделен, emergency_blocked флаг простой |

---

## 9. What Remains Deferred to v2.6+

- Pricing / rate cards / billing
- Programmatic / RTB / DSP / SSP
- Sales lift / attribution
- Чековая аналитика
- ClickHouse for inventory analytics (PostgreSQL first)
- Audience targeting / DMP
- Competitor blocking
