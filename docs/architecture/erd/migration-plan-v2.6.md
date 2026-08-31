# Migration plan v2.6 — additive-first (артефакт AG, RM-TECH-229)

> Статус: **candidate/prepared 2026-08-31 (OD-043)** — RM-TECH-229 остаётся planned до Gate-S; приёмка — внутри задачи, не сейчас. Сопоставление целевого inventory §13 ТЗ r428 с as-built ERD (62 таблиц, alembic head 036). Правила: только additive миграции (новые таблицы/колонки/индексы, nullable → backfill → NOT NULL), каждая миграция с down_revision, rehearsal up/down на стенде (owner gate `migration_application`), RLS-политика на каждую scope-таблицу, PII-класс/retention до включения записи (RM-TECH-253/RM-OPS-005). Исключения из аддитивности — только §3.1 (OD-018).

| Группа §13 | Целевая сущность | As-built | Статус | Задача |
|---|---|---|---|---|
| Hierarchy | `branches` | `branches` | present | — |
| Hierarchy | `clusters` | `clusters` | present | — |
| Hierarchy | `stores` | `stores` | present | — |
| Hierarchy | `store_groups` | — | missing | RM-TECH-240 |
| Devices | `devices` | `physical_devices` | present-as | compat/rename не требуется (alias в ERD) |
| Devices | `device_certificates` | `device_certificates` | present | — |
| Devices | `device_status` | `device_status_history` | present-as | compat/rename не требуется (alias в ERD) |
| Devices | `device_commands` | — | missing | RM-TECH-255/224/228 |
| Devices | `device_events` | — | missing | RM-TECH-255/224/228 |
| Devices | `device_heartbeats` | `physical_devices(heartbeat cols, 025)` | present-as | compat/rename не требуется (alias в ERD) |
| Devices | `device_errors` | — | missing | RM-TECH-255/224/228 |
| Identity | `users` | `users` | present | — |
| Identity | `roles` | `roles` | present | — |
| Identity | `permissions` | `permissions` | present | — |
| Identity | `user_roles` | `user_roles` | present | — |
| Identity | `access_scopes` | `access_scopes` | present | — |
| Commercial | `advertisers` | `advertiser_organizations` | present-as | compat/rename не требуется (alias в ERD) |
| Commercial | `brands` | `advertiser_brands` | present-as | compat/rename не требуется (alias в ERD) |
| Commercial | `contracts` | `advertiser_contracts` | present-as | compat/rename не требуется (alias в ERD) |
| Commercial | `orders` | `commerce_orders` | present-as | compat/rename не требуется (alias в ERD) |
| Commercial | `tariffs` | `commerce_tariff_versions` | present-as | compat/rename не требуется (alias в ERD) |
| Commercial | `price_lists` | `commerce_price_items` | present-as | compat/rename не требуется (alias в ERD) |
| Commercial | `discounts` | — | missing | RM-TECH-245…249, RM-TECH-246 |
| Commercial | `package_offers` | — | missing | RM-TECH-245…249, RM-TECH-246 |
| Commercial | `campaigns` | `campaigns` | present | — |
| Commercial | `campaign_flights` | `campaign_flights` | present | — |
| Commercial | `campaign_placements` | `campaign_placements` | present | — |
| Commercial | `placement_targets` | — | missing | RM-TECH-245…249, RM-TECH-246 |
| Commercial | `campaign_status_history` | `campaign_status_history` | present | — |
| Content | `media_assets` | `creative_assets` | present-as | compat/rename не требуется (alias в ERD) |
| Content | `creative_versions` | `campaign_creatives` | present-as | compat/rename не требуется (alias в ERD) |
| Content | `creative_moderation_tasks` | `campaign_creatives(status)` | present-as | compat/rename не требуется (alias в ERD) |
| Content | `content_renditions` | — | missing | RM-TECH-250/204 |
| Content | `rendition_moderation_tasks` | — | missing | RM-TECH-250/204 |
| Content | `rendition_requirements` | — | missing | RM-TECH-250/204 |
| Inventory | `inventory_rules` | `inventory_rules` | present | — |
| Inventory | `inventory_reservations` | `inventory_bookings` | present-as | compat/rename не требуется (alias в ERD) |
| Inventory | `inventory_snapshots` | — | missing | RM-TECH-203/202 |
| Inventory | `inventory_daily_snapshots` | — | missing | RM-TECH-203/202 |
| Delivery | `playlists` | `delivery_plans` | present-as | compat/rename не требуется (alias в ERD) |
| Delivery | `playlist_items` | — | missing | RM-TECH-207B/223/242 |
| Delivery | `playlist_versions` | — | missing | RM-TECH-207B/223/242 |
| Delivery | `manifests` | `delivery_manifests` | present-as | compat/rename не требуется (alias в ERD) |
| Delivery | `manifest_versions` | — | missing | RM-TECH-207B/223/242 |
| Delivery | `outbox_events` | `outbox_events` | present | — |
| Proof/analytics | `pop_events` | `pop_events_raw` | present-as | compat/rename не требуется (alias в ERD) |
| Proof/analytics | `channel_events` | — | missing | RM-TECH-226/227, RM-BIZ-003 |
| Proof/analytics | `campaign_daily_stats` | — | missing | RM-TECH-226/227, RM-BIZ-003 |
| Governance | `approval_tasks` | `campaign_approvals` | present-as | compat/rename не требуется (alias в ERD) |
| Governance | `approval_decisions` | `campaign_approvals` | present-as | compat/rename не требуется (alias в ERD) |
| Governance | `emergency_events` | `emergency_overrides` | present-as | compat/rename не требуется (alias в ERD) |
| Governance | `emergency_targets` | — | missing | RM-TECH-247/254, RM-STAB-014 |
| Governance | `audit_events_operational` | `audit_events_operational` | present | — |
| Governance | `audit_events` | `audit_events_operational (long-term — RM-STAB-014)` | present-as | compat/rename не требуется (alias в ERD) |
| Channels/vendors | `device_types` | `device_types` | present | — |
| Channels/vendors | `channel_types` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `device_capabilities` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `player_builds` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `channel_adapter_configs` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `esl_gateways` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `esl_labels` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `led_controllers` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `shelf_surfaces` | — | missing | RM-TECH-230/231/261/264 |
| Channels/vendors | `vendor_integration_events` | — | missing | RM-TECH-230/231/261/264 |
| v2.6 Extension | `sales_reference_records` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `campaign_attribution_windows` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `store_control_group_assignments` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `campaign_lift_reports` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `advertiser_self_service_settings` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `advertiser_budget_limits` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `competitive_separation_rules` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `store_audience_attributes` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `financial_exchange_batches` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `dynamic_content_bindings` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `field_device_confirmations` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `field_incidents` | — | missing | RM-TECH-280…289 |
| v2.6 Extension | `external_measurement_exports` | — | missing | RM-TECH-280…289 |

Итог: present/present-as **37**, missing **40** — все missing имеют задачу roadmap (стадии CORE/CH/A). Backfill: только идемпотентными скриптами с evidence; rollback: down-миграция + восстановление из drill-backup (RM-OPS-003). Полевые контракты новых сущностей v2.6 — §13 ТЗ (13 сущностей) переносятся в ERD задачами RM-TECH-280…289 без JSON `metadata`-маскировки.
