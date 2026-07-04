<!--
SUPERSEDED: This document is retained for historical context only.
Current source of truth:
- ADR-007 for analytics/ClickHouse boundary
- ADR-008 for testing/phase gates
- ADR-009 for fail-closed RBAC/RLS and PostgreSQL RLS
- ADR-010 for advertiser domain foundation
Do not implement from this document when it conflicts with ADRs.
See docs/architecture/README.md for full source-of-truth ordering.
-->

# ERD v2.5 — PostgreSQL Target Model

> **Дата:** 2026-06-29 | **Этап:** A.2  
> **Основание:** ТЗ v2.5 Tables 17-18 + Architecture v2.5 Sections 23-24  
> **Статус:** ПРОЕКТ (БД не меняется, миграции не создаются)

---

## 1. Entity Relationship Summary

Целевая модель: **channel-agnostic core** + **channel-specific extension tables**.
Новые каналы подключаются добавлением справочников, профилей и адаптеров — без изменения бизнес-таблиц (campaigns, placements, inventory).

```
Channel → DeviceType → CapabilityProfile
                       ↓
           PhysicalDevice → DeviceCertificate
                ↓
           LogicalCarrier
                ↓
           DisplaySurface (размеры, зона, ориентация)
                       ↓
           Placement.target_surfaces
                       ↓
           ManifestVersion → AdapterPayload
                       ↓
           ProofEvent (normalized)
```

---

## 2. Core / Hierarchy

### branches
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK, gen_random_uuid() | |
| name | VARCHAR(255) | NOT NULL | Название филиала |
| code | VARCHAR(50) | UNIQUE, NOT NULL | Стабильный код |
| timezone | VARCHAR(50) | DEFAULT 'Europe/Moscow' | |
| is_active | BOOLEAN | DEFAULT true | |
| created_at | TIMESTAMPTZ | DEFAULT now() | |
| updated_at | TIMESTAMPTZ | DEFAULT now() | |

**Статус:** ✅ EXISTS  
**Индексы:** code (unique)  
**RLS:** branch_scope

### clusters
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK | |
| name | VARCHAR(255) | NOT NULL | |
| code | VARCHAR(50) | nullable | |
| branch_id | UUID | FK→branches, NOT NULL, INDEX | |
| is_active | BOOLEAN | DEFAULT true | |
| created_at/updated_at | TIMESTAMPTZ | | |

**Статус:** ✅ EXISTS  
**Индексы:** (branch_id, code) UNIQUE  
**RLS:** через branch

### stores
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK | |
| name | VARCHAR(255) | NOT NULL | |
| code | VARCHAR(50) | UNIQUE, NOT NULL | |
| cluster_id | UUID | FK→clusters, NOT NULL, INDEX | |
| address | TEXT | | Адрес магазина (не ПДн) |
| format | VARCHAR(50) | | Формат магазина |
| status | VARCHAR(20) | DEFAULT 'active' | active/inactive/maintenance |
| timezone | VARCHAR(50) | DEFAULT 'Europe/Moscow' | |
| is_active | BOOLEAN | DEFAULT true | |
| created_at/updated_at | TIMESTAMPTZ | | |

**Статус:** ✅ EXISTS  
**Индексы:** code (unique)  
**RLS:** store_scope

### store_groups
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK | |
| name | VARCHAR(255) | NOT NULL | |
| code | VARCHAR(50) | UNIQUE | |
| group_type | VARCHAR(30) | 'custom'/'pilot'/'region' | |
| is_active | BOOLEAN | DEFAULT true | |
| created_at/updated_at | TIMESTAMPTZ | | |

**Статус:** ❌ НУЖНО СОЗДАТЬ  
**Связи:** store_group_members (store_id, group_id)

---

## 3. Advertisers & Commercial

### advertisers
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK | |
| name | VARCHAR(255) | NOT NULL | |
| legal_name | VARCHAR(500) | | Юридическое наименование |
| inn | VARCHAR(12) | UNIQUE | ИНН |
| kpp | VARCHAR(9) | | КПП |
| status | VARCHAR(20) | DEFAULT 'active' | |
| contacts_json | JSONB | DEFAULT '{}' | ⚠️ Может содержать ПДн |
| comment | TEXT | | ⚠️ Не вводить ПДн |
| created_at/updated_at | TIMESTAMPTZ | | |

**Статус:** ✅ EXISTS  
**RLS:** advertiser_scope

### brands
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| advertiser_id | UUID | FK→advertisers, NOT NULL, INDEX |
| name | VARCHAR(255) | NOT NULL |
| category | VARCHAR(100) | |
| status | VARCHAR(20) | DEFAULT 'active' |
| created_at/updated_at | TIMESTAMPTZ | |

**Статус:** ✅ EXISTS  
**Уникальность:** (advertiser_id, name)

### contracts
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| advertiser_id | UUID | FK→advertisers, NOT NULL, INDEX |
| number | VARCHAR(100) | NOT NULL |
| valid_from/valid_to | DATE | NOT NULL |
| status | VARCHAR(20) | DEFAULT 'draft' |
| amount_limit | NUMERIC(15,2) | |
| currency | VARCHAR(3) | DEFAULT 'RUB' |
| comment | TEXT | |
| created_at/updated_at | TIMESTAMPTZ | |

**Статус:** ✅ EXISTS  

### orders
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| advertiser_id | UUID | FK→advertisers, NOT NULL, INDEX |
| brand_id | UUID | FK→brands, INDEX |
| contract_id | UUID | FK→contracts, INDEX |
| number | VARCHAR(100) | NOT NULL |
| name | VARCHAR(500) | NOT NULL |
| status | VARCHAR(20) | DEFAULT 'draft' |
| planned_budget | NUMERIC(15,2) | |
| currency | VARCHAR(3) | DEFAULT 'RUB' |
| planned_start_date/end_date | DATE | |
| comment | TEXT | |
| created_at/updated_at | TIMESTAMPTZ | |

**Статус:** ✅ EXISTS  
**Индексы:** (advertiser_id, number) UNIQUE

---

## 4. Campaigns & Placements

### campaigns
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK | |
| order_id | UUID | FK→orders, NOT NULL | |
| advertiser_id | UUID | FK→advertisers, NOT NULL, INDEX | RLS scope |
| brand_id | UUID | FK→brands | |
| campaign_code | VARCHAR(64) | UNIQUE, INDEX | Стабильный код |
| name | VARCHAR(255) | NOT NULL | |
| objective | VARCHAR(100) | | |
| status | VARCHAR(20) | DEFAULT 'draft' | draft→in_review→approved→live→paused→completed→archived |
| campaign_type | VARCHAR(20) | DEFAULT 'commercial' | commercial/internal/compensation/test/filler |
| planned_start_date/end_date | DATE | NOT NULL | |
| priority | INTEGER | DEFAULT 0, CHECK ≥ 0 | |
| budget | NUMERIC(15,2) | | |
| currency | VARCHAR(3) | DEFAULT 'RUB' | |
| comment | TEXT | | |
| created_by | UUID | FK→users, NOT NULL | |
| approved_by | UUID | FK→users | |
| approved_at | TIMESTAMPTZ | | |
| rejection_reason | TEXT | | |
| created_at/updated_at | TIMESTAMPTZ | | |

**Статус:** ✅ EXISTS (нужно добавить campaign_type)  
**Check:** planned_start_date ≤ planned_end_date  
**RLS:** advertiser_scope
**Audit:** campaign_status_history

### campaign_status_history ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| campaign_id | UUID | FK→campaigns, NOT NULL, INDEX |
| from_status | VARCHAR(20) | |
| to_status | VARCHAR(20) | NOT NULL |
| changed_by | UUID | FK→users, NOT NULL |
| changed_at | TIMESTAMPTZ | DEFAULT now() |
| reason | TEXT | |
| details_json | JSONB | |

### placements ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK | |
| campaign_id | UUID | FK→campaigns, NOT NULL, INDEX | Кампания 1→N размещений |
| placement_code | VARCHAR(64) | UNIQUE, INDEX | Стабильный код |
| name | VARCHAR(255) | NOT NULL | |
| status | VARCHAR(20) | DEFAULT 'draft' | draft→scheduled→live→paused→completed→archived |
| priority | INTEGER | DEFAULT 0 | Приоритет размещения |
| frequency_cap | INTEGER | | Макс. показов за период |
| start_date/end_date | DATE | NOT NULL | |
| created_by | UUID | FK→users, NOT NULL | |
| created_at/updated_at | TIMESTAMPTZ | | |

### placement_targets ❌ НУЖНО СОЗДАТЬ (заменяет campaign_targets)
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| placement_id | UUID | FK→placements, NOT NULL, INDEX |
| target_type | VARCHAR(20) | 'branch'/'cluster'/'store'/'surface'/'zone' |
| branch_id | UUID | FK→branches |
| cluster_id | UUID | FK→clusters |
| store_id | UUID | FK→stores |
| display_surface_id | UUID | FK→display_surfaces |
| store_zone_id | UUID | FK→store_zones |
| logical_carrier_id | UUID | FK→logical_carriers |
| created_at | TIMESTAMPTZ | DEFAULT now() |

**Примечание:** Заменяет `campaign_targets`. Целевые поверхности определяются через Channel Orchestrator, а не прямые ссылки на КСО.

### campaign_creatives
**Статус:** ✅ EXISTS — сохранить как link table campaign_id↔creative_code

---

## 5. Channels (архитектурный фундамент v2.5)

### channels ✅ EXISTS
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | NOT NULL |
| code | VARCHAR(50) | UNIQUE, NOT NULL — 'KSO'/'ANDROID_TV'/'PRICE_CHECKER'/'ESL'/'LED_SHELF' |
| description | TEXT | |
| is_active | BOOLEAN | DEFAULT true |
| created_at/updated_at | TIMESTAMPTZ | |

### channel_adapters ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| channel_id | UUID | FK→channels, NOT NULL, INDEX |
| adapter_code | VARCHAR(50) | UNIQUE |
| adapter_version | VARCHAR(20) | |
| status | VARCHAR(20) | DEFAULT 'active' |
| config_json | JSONB | DEFAULT '{}' |
| health_check_url | VARCHAR(500) | |
| created_at/updated_at | TIMESTAMPTZ | |

### channel_capabilities ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| channel_id | UUID | FK→channels, NOT NULL |
| supports_video | BOOLEAN | DEFAULT false |
| supports_animation | BOOLEAN | DEFAULT false |
| supports_interactive | BOOLEAN | DEFAULT false |
| supports_audio | BOOLEAN | DEFAULT false |
| proof_modes | JSONB | DEFAULT '[]' — ["real_playback","idle_impression",...] |
| sla_config_json | JSONB | DEFAULT '{}' |
| created_at/updated_at | TIMESTAMPTZ | |

### device_types ✅ EXISTS
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| channel_id | UUID | FK→channels, NOT NULL, INDEX |
| name | VARCHAR(255) | NOT NULL |
| code | VARCHAR(50) | UNIQUE |
| description | TEXT | |
| is_active | BOOLEAN | DEFAULT true |
| created_at/updated_at | TIMESTAMPTZ | |

### capability_profiles ✅ EXISTS
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| device_type_id | UUID | FK→device_types, NOT NULL |
| name | VARCHAR(255) | NOT NULL |
| code | VARCHAR(50) | UNIQUE |
| resolution_width/height | INTEGER | |
| orientation | VARCHAR(20) | 'landscape'/'portrait' |
| supported_formats | JSONB | DEFAULT '[]' |
| max_file_size | BIGINT | |
| max_duration_seconds | FLOAT | |
| refresh_rate | INTEGER | |
| created_at/updated_at | TIMESTAMPTZ | |

### media_constraints ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| capability_profile_id | UUID | FK→capability_profiles, NOT NULL, INDEX |
| format | VARCHAR(20) | 'MP4'/'WEBM'/'JPG'/'PNG'/'GIF' |
| max_width/max_height | INTEGER | |
| max_file_size | BIGINT | |
| max_duration_seconds | FLOAT | |
| codecs_allowed | JSONB | DEFAULT '[]' |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### proof_capabilities ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| capability_profile_id | UUID | FK→capability_profiles, NOT NULL, INDEX |
| proof_type | VARCHAR(30) | 'real_playback'/'idle_impression'/'template_applied'/'controller_ack'/'delivery_ack' |
| is_primary | BOOLEAN | DEFAULT false |
| verification_method | VARCHAR(30) | 'device_signature'/'gateway_ack'/'hmac' |
| created_at | TIMESTAMPTZ | DEFAULT now() |

---

## 6. Devices & Surfaces (универсальная модель)

### physical_devices ✅ EXISTS (частично)
| Поле | Тип | Ограничения | Примечание |
|---|---|---|---|
| id | UUID | PK | |
| device_type_id | UUID | FK→device_types, NOT NULL, INDEX | |
| store_id | UUID | FK→stores, NOT NULL, INDEX | |
| external_code | VARCHAR(64) | UNIQUE, INDEX | **← ДОБАВИТЬ** — device_code из kso_devices |
| serial_number | VARCHAR(255) | | |
| hardware_fingerprint | VARCHAR(255) | | |
| status | VARCHAR(20) | DEFAULT 'offline' | online/offline/degraded/error/maintenance/revoked |
| device_properties | JSONB | DEFAULT '{}' | **← ДОБАВИТЬ** — KSO-specific: hidden_on_touch, ukms_version |
| zone_label | VARCHAR(100) | | |
| installed_at | TIMESTAMPTZ | | |
| last_heartbeat_at | TIMESTAMPTZ | | |
| created_at/updated_at | TIMESTAMPTZ | | |

**Миграция A.3:** kso_devices → physical_devices (см. kso-duplicate-mapping-a2.md)

### device_certificates ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| device_id | UUID | FK→physical_devices, NOT NULL, INDEX |
| cert_type | VARCHAR(20) | 'mTLS'/'JWT'/'api_key' |
| cert_fingerprint | VARCHAR(255) | UNIQUE |
| public_key_pem | TEXT | |
| issued_at/expires_at | TIMESTAMPTZ | |
| revoked | BOOLEAN | DEFAULT false |
| revoked_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### runtime_versions ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| device_type_id | UUID | FK→device_types, NOT NULL, INDEX |
| version | VARCHAR(20) | NOT NULL |
| manifest_schema_version | VARCHAR(10) | |
| api_versions | JSONB | DEFAULT '[]' |
| release_notes | TEXT | |
| is_active | BOOLEAN | DEFAULT false |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### logical_carriers ✅ EXISTS
**Статус:** ✅ EXISTS — для ESL/LED: один gateway управляет множеством носителей

### display_surfaces ✅ EXISTS
**Статус:** ✅ EXISTS — поверхность показа с размерами и зоной

### surface_groups ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| name | VARCHAR(255) | NOT NULL |
| code | VARCHAR(50) | UNIQUE |
| channel_id | UUID | FK→channels, NOT NULL |
| store_id | UUID | FK→stores |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### store_zones ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| store_id | UUID | FK→stores, NOT NULL, INDEX |
| name | VARCHAR(255) | NOT NULL |
| zone_type | VARCHAR(30) | 'checkout'/'entrance'/'shelf'/'wall'/'ceiling' |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### device_status / device_commands / device_events
**Статус:** ✅ EXISTS (device_gateway domain) — расширить для multi-channel

---

## 7. Content / Media

### creatives ✅ EXISTS
### creative_versions ✅ EXISTS
**Поля:** Добавить `rendition_targets` — для каких каналов подготовлен рендер

### creative_renditions ❌ НУЖНО СОЗДАТЬ (заменяет/расширяет renditions)
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| creative_version_id | UUID | FK→creative_versions, NOT NULL, INDEX |
| channel_id | UUID | FK→channels, NOT NULL |
| capability_profile_id | UUID | FK→capability_profiles |
| rendition_code | VARCHAR(64) | UNIQUE |
| file_path | VARCHAR(1000) | NOT NULL |
| mime_type | VARCHAR(100) | |
| file_size | BIGINT | |
| sha256 | VARCHAR(64) | NOT NULL |
| width/height | INTEGER | |
| duration_seconds | FLOAT | |
| status | VARCHAR(20) | DEFAULT 'pending' |
| created_at/updated_at | TIMESTAMPTZ | |

### rendition_validations ✅ EXISTS
### channel_previews ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| rendition_id | UUID | FK→creative_renditions |
| channel_id | UUID | FK→channels |
| preview_path | VARCHAR(1000) | |
| generated_at | TIMESTAMPTZ | DEFAULT now() |

### creative_moderation_tasks ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| creative_id | UUID | FK→creatives, NOT NULL, INDEX |
| moderator_id | UUID | FK→users |
| decision | VARCHAR(20) | 'approved'/'rejected'/'changes_requested' |
| comment | TEXT | |
| checks_passed | JSONB | DEFAULT '[]' |
| created_at/decided_at | TIMESTAMPTZ | |

---

## 8. Inventory

### inventory_rules ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| channel_id | UUID | FK→channels |
| scope_type | VARCHAR(20) | 'network'/'branch'/'cluster'/'store'/'surface' |
| scope_id | UUID | |
| rule_type | VARCHAR(30) | 'max_ad_load'/'slot_duration'/'prime_time'/'priority_tiers'/'overbooking' |
| rule_value_json | JSONB | NOT NULL |
| effective_from | TIMESTAMPTZ | NOT NULL |
| effective_to | TIMESTAMPTZ | |
| is_active | BOOLEAN | DEFAULT true |
| created_by | UUID | FK→users |
| created_at/updated_at | TIMESTAMPTZ | |

### inventory_reservations ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| placement_id | UUID | FK→placements |
| surface_id | UUID | FK→display_surfaces |
| date | DATE | NOT NULL |
| slot_start/slot_end | TIME | NOT NULL |
| status | VARCHAR(20) | 'reserved'/'sold'/'internal'/'emergency' |
| reserved_by | UUID | FK→users |
| reserved_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ | |

### inventory_snapshots ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| scope_type/scope_id | VARCHAR(20)/UUID | |
| channel_id | UUID | FK→channels |
| snapshot_date | DATE | NOT NULL |
| total_capacity | BIGINT | |
| reserved | BIGINT | |
| sold | BIGINT | |
| free | BIGINT | |
| internal_use | BIGINT | |
| emergency_occupied | BIGINT | |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### capacity_units ✅ EXISTS (inventory_units)
### conflict_checks ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| placement_id | UUID | FK→placements, NOT NULL, INDEX |
| check_type | VARCHAR(30) | 'schedule_overlap'/'ad_load_exceeded'/'priority_conflict'/'capacity_exceeded' |
| result | VARCHAR(20) | 'pass'/'warning'/'block' |
| details_json | JSONB | |
| checked_at | TIMESTAMPTZ | DEFAULT now() |

---

## 9. Manifest & Orchestrator

### playlist_versions ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| placement_id | UUID | FK→placements, NOT NULL, INDEX |
| version | INTEGER | NOT NULL |
| status | VARCHAR(20) | DEFAULT 'draft' |
| generated_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### manifest_versions ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| manifest_code | VARCHAR(64) | UNIQUE, INDEX |
| playlist_version_id | UUID | FK→playlist_versions |
| device_id | UUID | FK→physical_devices, INDEX |
| surface_id | UUID | FK→display_surfaces |
| manifest_schema_version | VARCHAR(10) | NOT NULL |
| valid_from/valid_to | TIMESTAMPTZ | NOT NULL |
| offline_ttl_seconds | INTEGER | |
| signature | VARCHAR(512) | HMAC/Ed25519 |
| signature_algorithm | VARCHAR(20) | |
| status | VARCHAR(20) | DEFAULT 'generated' |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### manifest_targets ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| manifest_version_id | UUID | FK→manifest_versions, NOT NULL, INDEX |
| target_type | VARCHAR(20) | 'device'/'surface'/'group' |
| target_id | UUID | |
| delivery_status | VARCHAR(20) | DEFAULT 'pending' |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### adapter_payloads ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| manifest_version_id | UUID | FK→manifest_versions, NOT NULL, INDEX |
| channel_id | UUID | FK→channels, NOT NULL |
| adapter_id | UUID | FK→channel_adapters |
| payload_json | JSONB | NOT NULL |
| payload_schema_version | VARCHAR(10) | |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### orchestrator_tasks ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| task_code | VARCHAR(64) | UNIQUE |
| placement_id | UUID | FK→placements, INDEX |
| task_type | VARCHAR(30) | 'publish'/'update'/'rollback'/'emergency' |
| status | VARCHAR(20) | DEFAULT 'pending' |
| total_targets | INTEGER | |
| completed_targets | INTEGER | DEFAULT 0 |
| created_by | UUID | FK→users |
| created_at/completed_at | TIMESTAMPTZ | |

### adapter_delivery_attempts ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| manifest_target_id | UUID | FK→manifest_targets, NOT NULL, INDEX |
| adapter_id | UUID | FK→channel_adapters |
| attempt_number | INTEGER | DEFAULT 1 |
| result | VARCHAR(20) | 'delivered'/'failed'/'timeout' |
| error_code | VARCHAR(50) | |
| attempted_at | TIMESTAMPTZ | DEFAULT now() |

---

## 10. Proof / Events

### proof_events ❌ НУЖНО СОЗДАТЬ (ClickHouse primary)
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| event_code | VARCHAR(128) | UNIQUE — idempotency key |
| proof_type | VARCHAR(30) | NOT NULL — real_playback/idle_impression/template_applied/label_ack/controller_ack/delivery_ack |
| device_id | UUID | FK→physical_devices, INDEX |
| store_id | UUID | FK→stores |
| surface_id | UUID | FK→display_surfaces |
| campaign_id | UUID | FK→campaigns |
| placement_id | UUID | FK→placements |
| creative_id | UUID | FK→creatives |
| rendition_id | UUID | FK→creative_renditions |
| manifest_id | UUID | FK→manifest_versions |
| started_at/ended_at | TIMESTAMPTZ | |
| duration_ms | INTEGER | |
| media_sha256 | VARCHAR(64) | |
| playback_result | VARCHAR(20) | 'success'/'skipped'/'failed'/'interrupted' |
| failure_reason | VARCHAR(100) | |
| device_signature | VARCHAR(512) | HMAC/Ed25519 |
| channel_type | VARCHAR(20) | |
| received_at | TIMESTAMPTZ | NOT NULL |
| created_at | TIMESTAMPTZ | DEFAULT now() |

**Индексы (ClickHouse):** (device_id, received_at), (campaign_id, received_at), (event_code)

### apply_ack_events ❌ НУЖНО СОЗДАТЬ (ClickHouse)
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| event_code | VARCHAR(128) | UNIQUE |
| device_id | UUID | FK→physical_devices, INDEX |
| manifest_id | UUID | FK→manifest_versions |
| ack_type | VARCHAR(20) | 'applied'/'error'/'rejected' |
| error_code | VARCHAR(50) | |
| applied_at | TIMESTAMPTZ | NOT NULL |
| received_at | TIMESTAMPTZ | DEFAULT now() |

### delivery_events ❌ НУЖНО СОЗДАТЬ (ClickHouse)
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| event_code | VARCHAR(128) | UNIQUE |
| manifest_target_id | UUID | FK→manifest_targets |
| adapter_id | UUID | FK→channel_adapters |
| delivery_result | VARCHAR(20) | 'delivered'/'failed' |
| attempted_at | TIMESTAMPTZ | |
| received_at | TIMESTAMPTZ | DEFAULT now() |

### device_telemetry ❌ НУЖНО СОЗДАТЬ (ClickHouse)
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| device_id | UUID | FK→physical_devices, INDEX |
| heartbeat_at | TIMESTAMPTZ | NOT NULL |
| cpu_percent | FLOAT | |
| memory_mb | INTEGER | |
| disk_free_mb | INTEGER | |
| cache_size_mb | INTEGER | |
| player_version | VARCHAR(20) | |
| chromium_version | VARCHAR(20) | |
| manifest_applied | VARCHAR(64) | |
| error_count | INTEGER | DEFAULT 0 |
| received_at | TIMESTAMPTZ | DEFAULT now() |

### idempotency_keys ❌ НУЖНО СОЗДАТЬ (Redis + PostgreSQL fallback)
| Поле | Тип | Ограничения |
|---|---|---|
| key | VARCHAR(128) | PK |
| event_type | VARCHAR(30) | |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| expires_at | TIMESTAMPTZ | TTL |

---

## 11. Emergency & Operations

### emergency_events ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| emergency_code | VARCHAR(64) | UNIQUE |
| action | VARCHAR(20) | 'stop_ads'/'show_message'/'fallback'/'resume' |
| level | VARCHAR(20) | 'network'/'branch'/'cluster'/'store'/'device' |
| level_id | UUID | |
| message_text | TEXT | |
| requested_by | UUID | FK→users, NOT NULL |
| reason | TEXT | NOT NULL |
| status | VARCHAR(20) | DEFAULT 'pending' |
| requested_at/applied_at | TIMESTAMPTZ | |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### emergency_targets ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| emergency_event_id | UUID | FK→emergency_events, NOT NULL, INDEX |
| device_id | UUID | FK→physical_devices |
| delivery_status | VARCHAR(20) | 'pending'/'delivered'/'failed' |
| delivered_at | TIMESTAMPTZ | |

### rollout_plans ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| plan_code | VARCHAR(64) | UNIQUE |
| target_type | VARCHAR(20) | 'player_version'/'manifest_schema'/'adapter_config' |
| target_version | VARCHAR(20) | |
| total_devices | INTEGER | |
| created_by | UUID | FK→users |
| status | VARCHAR(20) | DEFAULT 'draft' |
| created_at/updated_at | TIMESTAMPTZ | |

### rollout_steps ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| rollout_plan_id | UUID | FK→rollout_plans, NOT NULL, INDEX |
| step_order | INTEGER | NOT NULL |
| step_label | VARCHAR(100) | 'lab'/'5 stores'/'50 stores'/'300 stores'/'10%'/'50%'/'all' |
| target_count | INTEGER | |
| error_threshold | FLOAT | Допустимый % ошибок |
| status | VARCHAR(20) | 'pending'/'in_progress'/'completed'/'auto_paused'/'rollback' |
| started_at/completed_at | TIMESTAMPTZ | |

### adapter_health ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| adapter_id | UUID | FK→channel_adapters, NOT NULL, INDEX |
| status | VARCHAR(20) | 'healthy'/'degraded'/'down' |
| last_heartbeat_at | TIMESTAMPTZ | |
| error_count_1h | INTEGER | DEFAULT 0 |
| latency_p95_ms | INTEGER | |
| checked_at | TIMESTAMPTZ | DEFAULT now() |

### feature_flags ❌ НУЖНО СОЗДАТЬ
| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| flag_code | VARCHAR(50) | UNIQUE |
| description | TEXT | |
| enabled | BOOLEAN | DEFAULT false |
| scope_type | VARCHAR(20) | 'global'/'branch'/'store'/'device_type'/'percentage' |
| scope_value_json | JSONB | DEFAULT '{}' |
| changed_by | UUID | FK→users |
| changed_at | TIMESTAMPTZ | DEFAULT now() |
| reason | TEXT | |

---

## 12. Audit

### admin_audit_events ✅ EXISTS
### login_audit_events ✅ EXISTS
### audit_events_operational ❌ НУЖНО СОЗДАТЬ (ClickHouse)

| Поле | Тип | Ограничения |
|---|---|---|
| id | UUID | PK |
| trace_id | VARCHAR(64) | INDEX |
| actor_user_id | UUID | |
| action | VARCHAR(100) | NOT NULL |
| target_type | VARCHAR(64) | |
| target_ref | VARCHAR(255) | |
| domain | VARCHAR(30) | 'campaign'/'inventory'/'content'/'channel'/'proof'/'emergency'/'operations' |
| details_json | JSONB | Без secrets/tokens |
| ip_hash | VARCHAR(128) | |
| user_agent_hash | VARCHAR(128) | |
| occurred_at | TIMESTAMPTZ | NOT NULL |

---

## 13. Deprecated / To Migrate

| Таблица | Действие | Замена |
|---|---|---|
| `kso_devices` | Мигрировать → physical_devices (A.3) | physical_devices (channel_type='KSO') |
| `kso_placements` | Мигрировать → placements + placement_targets | placements |
| `kso_proof_of_play_events` | Мигрировать → proof_events | proof_events (proof_type='real_playback') |
| `campaign_targets` | Заменить → placement_targets | placement_targets |
| `campaign_channels` | Сохранить как link table | Через placement_targets |
| `campaign_renditions` | Расширить → creative_renditions | creative_renditions |
| `publication_batches` | Legacy → manifest_versions + orchestrator_tasks | manifest_versions |
| `gateway_devices` | Мигрировать → physical_devices | physical_devices |
| `device_*` (device_gateway) | Расширить для multi-channel | Универсальные таблицы |

---

## 14. Статистика

| Категория | EXISTS | НУЖНО СОЗДАТЬ | ДЕПРЕКЕЙТЕД |
|---|---|---|---|
| Core/Hierarchy | 4 | 1 | 0 |
| Advertisers | 4 | 0 | 0 |
| Campaigns | 3 | 3 | 1 |
| Channels | 3 | 5 | 0 |
| Devices/Surfaces | 6 | 5 | 1 |
| Content | 5 | 3 | 0 |
| Inventory | 1 | 4 | 0 |
| Manifest/Orchestrator | 0 | 6 | 1 |
| Proof/Events | 0 | 5 | 1 |
| Emergency/Ops | 0 | 6 | 0 |
| Audit | 2 | 1 | 0 |
| **Итого** | **28** | **39** | **4** |
