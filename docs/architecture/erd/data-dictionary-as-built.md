# Data dictionary — as-built ERD (артефакт AG, RM-TECH-229)

> Статус: **candidate/prepared 2026-08-31 (OD-043; RM-TECH-229 planned до Gate-S, без приёмки)** — as-built из `packages/domain/models.py` (SQLAlchemy metadata) на develop @ 06ae22e (код = 4ac3ddb): 62 таблиц, 622 колонок, 97 FK; RLS включён у 38 таблиц (pg_tables.rowsecurity, preview-БД santa2, схема 036). PII-класс/retention/owner на колонку — заполняются RM-TECH-253 (data classes) и RM-OPS-005 (retention, OD-009). Код не менялся.

| Таблица | RLS | Колонок | FK → | Индексы/уникальность |
|---|---|---|---|---|
| `ad_settings` | — | 10 | — | 0 idx / 0 uniq |
| `branches` | ✔ | 6 | — | 1 idx / 0 uniq |
| `channels` | — | 7 | — | 1 idx / 0 uniq |
| `commerce_tariff_versions` | ✔ | 9 | — | 3 idx / 0 uniq |
| `inventory_rules` | ✔ | 11 | — | 2 idx / 0 uniq |
| `license_grants` | ✔ | 20 | — | 2 idx / 1 uniq |
| `login_attempts` | — | 8 | — | 4 idx / 0 uniq |
| `outbox_events` | — | 14 | — | 0 idx / 0 uniq |
| `permissions` | — | 5 | — | 1 idx / 0 uniq |
| `pop_dedup_index` | — | 2 | — | 0 idx / 0 uniq |
| `retailers` | — | 7 | — | 1 idx / 0 uniq |
| `roles` | — | 7 | — | 1 idx / 0 uniq |
| `users` | — | 11 | — | 2 idx / 1 uniq |
| `advertiser_organizations` | ✔ | 20 | retailers | 2 idx / 0 uniq |
| `audit_events_operational` | — | 9 | users | 6 idx / 0 uniq |
| `clusters` | ✔ | 6 | branches | 2 idx / 0 uniq |
| `device_types` | — | 7 | channels | 2 idx / 0 uniq |
| `emergency_overrides` | — | 11 | users | 0 idx / 0 uniq |
| `local_credentials` | — | 11 | users | 1 idx / 0 uniq |
| `password_reset_tokens` | — | 6 | users | 2 idx / 0 uniq |
| `refresh_sessions` | — | 11 | users | 3 idx / 0 uniq |
| `role_permissions` | — | 4 | permissions, roles | 2 idx / 1 uniq |
| `user_roles` | — | 6 | roles, users | 3 idx / 1 uniq |
| `advertiser_applications` | ✔ | 15 | advertiser_organizations, users | 1 idx / 0 uniq |
| `advertiser_brands` | ✔ | 8 | advertiser_organizations | 2 idx / 1 uniq |
| `advertiser_contacts` | ✔ | 12 | advertiser_organizations, users | 3 idx / 0 uniq |
| `advertiser_contracts` | ✔ | 19 | advertiser_organizations | 2 idx / 1 uniq |
| `advertiser_user_memberships` | ✔ | 5 | advertiser_organizations, users | 2 idx / 1 uniq |
| `campaign_briefs` | ✔ | 15 | advertiser_organizations, users | 1 idx / 0 uniq |
| `capability_profiles` | — | 14 | device_types | 2 idx / 0 uniq |
| `commerce_orders` | ✔ | 10 | advertiser_organizations, commerce_tariff_versions | 5 idx / 0 uniq |
| `creative_assets` | ✔ | 18 | advertiser_organizations, users | 2 idx / 1 uniq |
| `stores` | ✔ | 8 | clusters | 2 idx / 0 uniq |
| `access_scopes` | — | 8 | branches, clusters, stores | 4 idx / 0 uniq |
| `advertiser_invites` | ✔ | 11 | advertiser_applications, advertiser_organizations, users | 4 idx / 0 uniq |
| `campaigns` | ✔ | 18 | advertiser_brands, advertiser_contracts, advertiser_organizations, users | 2 idx / 1 uniq |
| `contract_upload_sessions` | ✔ | 13 | advertiser_contracts, advertiser_organizations, users | 2 idx / 0 uniq |
| `creative_upload_sessions` | ✔ | 12 | advertiser_organizations, creative_assets, users | 2 idx / 0 uniq |
| `physical_devices` | ✔ | 19 | device_types, retailers, stores | 3 idx / 0 uniq |
| `campaign_approvals` | ✔ | 9 | campaigns, users | 1 idx / 0 uniq |
| `campaign_creatives` | ✔ | 6 | campaigns, creative_assets | 1 idx / 1 uniq |
| `campaign_flights` | ✔ | 9 | campaigns | 1 idx / 0 uniq |
| `campaign_status_history` | ✔ | 7 | campaigns, users | 1 idx / 0 uniq |
| `delivery_manifests` | ✔ | 12 | campaigns, physical_devices, retailers | 3 idx / 0 uniq |
| `delivery_plans` | ✔ | 7 | campaigns | 1 idx / 0 uniq |
| `device_certificates` | — | 10 | physical_devices | 1 idx / 0 uniq |
| `device_onboarding_codes` | ✔ | 12 | device_types, physical_devices, retailers, stores, users | 2 idx / 0 uniq |
| `device_status_history` | — | 8 | physical_devices | 1 idx / 0 uniq |
| `license_seats` | ✔ | 6 | license_grants, physical_devices | 2 idx / 0 uniq |
| `logical_carriers` | — | 9 | physical_devices | 2 idx / 0 uniq |
| `pop_events_raw` | ✔ | 19 | creative_assets, physical_devices, retailers | 8 idx / 0 uniq |
| `pop_ingestion_batches` | ✔ | 7 | physical_devices | 2 idx / 0 uniq |
| `user_access_scopes` | — | 4 | access_scopes, users | 2 idx / 1 uniq |
| `delivery_attempts` | — | 7 | delivery_manifests | 1 idx / 0 uniq |
| `delivery_manifest_assets` | ✔ | 7 | creative_assets, delivery_manifests | 2 idx / 0 uniq |
| `display_surfaces` | ✔ | 13 | logical_carriers, stores | 3 idx / 0 uniq |
| `campaign_placements` | ✔ | 11 | branches, campaigns, clusters, display_surfaces, stores | 1 idx / 0 uniq |
| `commerce_order_lines` | ✔ | 9 | commerce_orders, display_surfaces | 3 idx / 0 uniq |
| `commerce_price_items` | ✔ | 8 | commerce_tariff_versions, display_surfaces | 3 idx / 1 uniq |
| `delivery_manifest_surfaces` | ✔ | 5 | delivery_manifests, display_surfaces | 2 idx / 0 uniq |
| `inventory_slots` | ✔ | 12 | display_surfaces | 3 idx / 1 uniq |
| `inventory_bookings` | ✔ | 12 | campaign_placements, campaigns, inventory_slots | 5 idx / 1 uniq |

## Колонки

### `ad_settings`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | INTEGER | нет | ✔ |  |  |
| `enabled` | BOOLEAN | нет |  |  |  |
| `server_url` | TEXT | нет |  |  |  |
| `base_dn` | TEXT | нет |  |  |  |
| `user_search_base` | TEXT | нет |  |  |  |
| `user_search_filter` | TEXT | нет |  |  |  |
| `bind_dn` | TEXT | нет |  |  |  |
| `use_tls` | BOOLEAN | нет |  |  |  |
| `certificate_validation` | VARCHAR(16) | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `branches`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `timezone` | VARCHAR(64) | нет |  |  |  |
| `is_active` | BOOLEAN | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `channels`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `description` | TEXT | нет |  |  |  |
| `is_active` | BOOLEAN | нет |  |  |  |
| `sort_order` | INTEGER | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `commerce_tariff_versions`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `valid_from` | DATE | нет |  |  |  |
| `valid_to` | DATE | да |  |  |  |
| `currency` | VARCHAR(3) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `inventory_rules`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `scope_type` | VARCHAR(32) | нет |  |  |  |
| `scope_id` | VARCHAR(36) | да |  |  |  |
| `rule_type` | VARCHAR(64) | нет |  |  |  |
| `priority` | INTEGER | нет |  |  |  |
| `value_json` | JSONB | нет |  |  |  |
| `is_active` | BOOLEAN | нет |  |  |  |
| `starts_at` | DATETIME | да |  |  |  |
| `ends_at` | DATETIME | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `license_grants`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `license_id` | VARCHAR(128) | нет |  |  |  |
| `licensee_id` | VARCHAR(128) | нет |  |  |  |
| `licensee_name` | VARCHAR(255) | нет |  |  |  |
| `tier` | VARCHAR(64) | нет |  |  |  |
| `issued_at` | DATETIME | нет |  |  |  |
| `valid_from` | DATETIME | нет |  |  |  |
| `valid_until` | DATETIME | да |  |  |  |
| `max_devices` | INTEGER | нет |  |  |  |
| `overage_allowance` | INTEGER | нет |  |  |  |
| `grace_days` | INTEGER | нет |  |  |  |
| `features` | JSONB | да |  |  |  |
| `installation_binding` | VARCHAR(255) | да |  |  |  |
| `nonce` | VARCHAR(255) | да |  |  |  |
| `schema_version` | INTEGER | нет |  |  |  |
| `kid` | VARCHAR(255) | да |  |  |  |
| `source` | VARCHAR(32) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `login_attempts`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `username_or_email_hash` | VARCHAR(128) | нет |  |  |  |
| `auth_provider` | VARCHAR(32) | нет |  |  |  |
| `success` | BOOLEAN | нет |  |  |  |
| `failure_reason` | VARCHAR(64) | да |  |  |  |
| `ip_address` | VARCHAR(45) | да |  |  |  |
| `correlation_id` | VARCHAR(64) | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `outbox_events`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `event_type` | VARCHAR(128) | нет |  |  |  |
| `event_version` | VARCHAR(16) | нет |  |  |  |
| `aggregate_type` | VARCHAR(64) | нет |  |  |  |
| `aggregate_id` | VARCHAR(36) | нет |  |  |  |
| `partition_key` | VARCHAR(128) | да |  |  |  |
| `payload_json` | JSONB | нет |  |  |  |
| `headers_json` | JSONB | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `attempts` | INTEGER | нет |  |  |  |
| `next_attempt_at` | DATETIME | нет |  |  |  |
| `published_at` | DATETIME | да |  |  |  |
| `last_error` | TEXT | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `permissions`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(128) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `description` | TEXT | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `pop_dedup_index`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `event_id` | VARCHAR(36) | нет | ✔ |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `retailers`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `legal_name` | VARCHAR(255) | нет |  |  |  |
| `display_name` | VARCHAR(255) | нет |  |  |  |
| `status` | VARCHAR(20) | нет |  |  | active |
| `created_at` | DATETIME | нет |  |  | now() |
| `updated_at` | DATETIME | нет |  |  | now() |

### `roles`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `description` | TEXT | нет |  |  |  |
| `is_system` | BOOLEAN | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `users`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `username` | VARCHAR(128) | нет |  |  |  |
| `email` | VARCHAR(255) | да |  |  |  |
| `display_name` | VARCHAR(255) | нет |  |  |  |
| `auth_provider` | VARCHAR(32) | нет |  |  |  |
| `external_subject` | VARCHAR(255) | да |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `is_break_glass` | BOOLEAN | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `advertiser_organizations`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `retailer_id` | VARCHAR(36) | нет |  | retailers.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `legal_name` | VARCHAR(255) | нет |  |  |  |
| `display_name` | VARCHAR(255) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |
| `legal_entity_type` | VARCHAR(32) | да |  |  |  |
| `legal_form` | VARCHAR(32) | да |  |  |  |
| `legal_form_other` | VARCHAR(255) | да |  |  |  |
| `inn` | VARCHAR(32) | да |  |  |  |
| `legal_address` | TEXT | да |  |  |  |
| `settlement_account` | VARCHAR(32) | да |  |  |  |
| `correspondent_account` | VARCHAR(32) | да |  |  |  |
| `bik` | VARCHAR(16) | да |  |  |  |
| `bank_name` | VARCHAR(255) | да |  |  |  |
| `kpp` | VARCHAR(16) | да |  |  |  |
| `ogrn` | VARCHAR(32) | да |  |  |  |
| `ogrnip` | VARCHAR(32) | да |  |  |  |

### `audit_events_operational`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `actor_user_id` | VARCHAR(36) | да |  | users.id |  |
| `action` | VARCHAR(128) | нет |  |  |  |
| `target_type` | VARCHAR(64) | нет |  |  |  |
| `target_id` | VARCHAR(36) | да |  |  |  |
| `correlation_id` | VARCHAR(64) | да |  |  |  |
| `ip_address` | VARCHAR(45) | нет |  |  |  |
| `details_json` | JSONB | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `clusters`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `branch_id` | VARCHAR(36) | нет |  | branches.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `is_active` | BOOLEAN | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `device_types`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `channel_id` | VARCHAR(36) | нет |  | channels.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `player_runtime` | VARCHAR(64) | нет |  |  |  |
| `is_active` | BOOLEAN | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `emergency_overrides`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `level` | VARCHAR(32) | нет |  |  |  |
| `target_id` | VARCHAR(36) | да |  |  |  |
| `active` | BOOLEAN | нет |  |  |  |
| `reason` | VARCHAR(512) | нет |  |  |  |
| `activated_by` | VARCHAR(36) | да |  | users.id |  |
| `activated_at` | DATETIME | да |  |  |  |
| `deactivated_by` | VARCHAR(36) | да |  | users.id |  |
| `deactivated_at` | DATETIME | да |  |  |  |
| `deactivated_reason` | VARCHAR(512) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `local_credentials`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `user_id` | VARCHAR(36) | нет |  | users.id |  |
| `credential_type` | VARCHAR(32) | нет |  |  |  |
| `password_hash` | VARCHAR(255) | нет |  |  |  |
| `password_hash_algorithm` | VARCHAR(32) | нет |  |  |  |
| `password_changed_at` | DATETIME | нет |  |  |  |
| `email_verified_at` | DATETIME | да |  |  |  |
| `must_change_password` | BOOLEAN | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `password_reset_tokens`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `user_id` | VARCHAR(36) | нет |  | users.id |  |
| `token_hash` | VARCHAR(128) | нет |  |  |  |
| `expires_at` | DATETIME | нет |  |  |  |
| `used_at` | DATETIME | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `refresh_sessions`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `user_id` | VARCHAR(36) | нет |  | users.id |  |
| `token_hash` | VARCHAR(128) | нет |  |  |  |
| `token_family_id` | VARCHAR(36) | нет |  |  |  |
| `issued_at` | DATETIME | нет |  |  |  |
| `expires_at` | DATETIME | нет |  |  |  |
| `rotated_at` | DATETIME | да |  |  |  |
| `revoked_at` | DATETIME | да |  |  |  |
| `ip_address` | VARCHAR(45) | да |  |  |  |
| `user_agent` | TEXT | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `role_permissions`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `role_id` | VARCHAR(36) | нет |  | roles.id |  |
| `permission_id` | VARCHAR(36) | нет |  | permissions.id |  |
| `created_at` | DATETIME | нет |  |  |  |

### `user_roles`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `user_id` | VARCHAR(36) | нет |  | users.id |  |
| `role_id` | VARCHAR(36) | нет |  | roles.id |  |
| `scope_type` | VARCHAR(32) | да |  |  |  |
| `scope_id` | VARCHAR(36) | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `advertiser_applications`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `company_name` | VARCHAR(255) | нет |  |  |  |
| `contact_name` | VARCHAR(255) | нет |  |  |  |
| `email` | VARCHAR(255) | нет |  |  |  |
| `phone` | VARCHAR(64) | да |  |  |  |
| `website` | VARCHAR(512) | да |  |  |  |
| `comment` | TEXT | да |  |  |  |
| `consent` | BOOLEAN | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `reviewer_id` | VARCHAR(36) | да |  | users.id |  |
| `review_reason` | TEXT | да |  |  |  |
| `reviewed_at` | DATETIME | да |  |  |  |
| `organization_id` | VARCHAR(36) | да |  | advertiser_organizations.id |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `advertiser_brands`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `description` | TEXT | да |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `advertiser_contacts`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `user_id` | VARCHAR(36) | да |  | users.id |  |
| `contact_type` | VARCHAR(32) | нет |  |  |  |
| `full_name` | VARCHAR(255) | нет |  |  |  |
| `email` | VARCHAR(255) | нет |  |  |  |
| `phone` | VARCHAR(32) | да |  |  |  |
| `title` | VARCHAR(255) | да |  |  |  |
| `is_primary` | BOOLEAN | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `advertiser_contracts`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `contract_number` | VARCHAR(128) | да |  |  |  |
| `budget_limit_amount` | NUMERIC(18, 2) | да |  |  |  |
| `budget_limit_currency` | VARCHAR(3) | нет |  |  |  |
| `valid_from` | DATETIME | нет |  |  |  |
| `valid_until` | DATETIME | да |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `terms_url` | TEXT | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |
| `file_storage_key` | VARCHAR(512) | да |  |  |  |
| `file_name` | VARCHAR(255) | да |  |  |  |
| `file_size_bytes` | BIGINT | да |  |  |  |
| `file_sha256` | VARCHAR(64) | да |  |  |  |
| `file_content_type` | VARCHAR(64) | да |  |  |  |
| `file_uploaded_at` | DATETIME | да |  |  |  |

### `advertiser_user_memberships`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `user_id` | VARCHAR(36) | нет |  | users.id |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `campaign_briefs`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `title` | VARCHAR(255) | нет |  |  |  |
| `objective` | TEXT | да |  |  |  |
| `product_category` | VARCHAR(255) | да |  |  |  |
| `target_period_from` | DATE | да |  |  |  |
| `target_period_to` | DATE | да |  |  |  |
| `budget_amount` | NUMERIC(18, 2) | да |  |  |  |
| `budget_currency` | VARCHAR(3) | нет |  |  |  |
| `preferred_channels` | TEXT | да |  |  |  |
| `comment` | TEXT | да |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_by` | VARCHAR(36) | да |  | users.id |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `capability_profiles`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `device_type_id` | VARCHAR(36) | нет |  | device_types.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `resolution_w` | INTEGER | нет |  |  |  |
| `resolution_h` | INTEGER | нет |  |  |  |
| `orientation` | VARCHAR(16) | нет |  |  |  |
| `supported_formats` | ARRAY | нет |  |  |  |
| `max_file_size_bytes` | INTEGER | нет |  |  |  |
| `max_duration_sec` | INTEGER | нет |  |  |  |
| `supports_video` | BOOLEAN | нет |  |  |  |
| `supports_animation` | BOOLEAN | нет |  |  |  |
| `supports_interactive` | BOOLEAN | нет |  |  |  |
| `pop_mode` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `commerce_orders`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `payment_status` | VARCHAR(32) | нет |  |  |  |
| `tariff_version_id` | VARCHAR(36) | да |  | commerce_tariff_versions.id |  |
| `total_amount` | NUMERIC(14, 2) | да |  |  |  |
| `currency` | VARCHAR(3) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `creative_assets`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `media_type` | VARCHAR(32) | нет |  |  |  |
| `storage_bucket` | VARCHAR(128) | нет |  |  |  |
| `storage_key` | VARCHAR(512) | нет |  |  |  |
| `sha256_checksum` | VARCHAR(64) | нет |  |  |  |
| `file_size_bytes` | INTEGER | нет |  |  |  |
| `duration_ms` | INTEGER | да |  |  |  |
| `resolution_w` | INTEGER | да |  |  |  |
| `resolution_h` | INTEGER | да |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `moderation_status` | VARCHAR(32) | нет |  |  |  |
| `moderation_notes` | TEXT | да |  |  |  |
| `created_by` | VARCHAR(36) | да |  | users.id |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `stores`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `cluster_id` | VARCHAR(36) | нет |  | clusters.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `address` | TEXT | нет |  |  |  |
| `timezone` | VARCHAR(64) | нет |  |  |  |
| `is_active` | BOOLEAN | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `access_scopes`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `scope_type` | VARCHAR(32) | нет |  |  |  |
| `branch_id` | VARCHAR(36) | да |  | branches.id |  |
| `cluster_id` | VARCHAR(36) | да |  | clusters.id |  |
| `store_id` | VARCHAR(36) | да |  | stores.id |  |
| `advertiser_id` | VARCHAR(36) | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `advertiser_invites`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_application_id` | VARCHAR(36) | да |  | advertiser_applications.id |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `token` | VARCHAR(128) | нет |  |  |  |
| `contact_email` | VARCHAR(255) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_by` | VARCHAR(36) | да |  | users.id |  |
| `created_at` | DATETIME | нет |  |  |  |
| `expires_at` | DATETIME | нет |  |  |  |
| `accepted_at` | DATETIME | да |  |  |  |
| `accepted_by_user_id` | VARCHAR(36) | да |  | users.id |  |

### `campaigns`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `advertiser_brand_id` | VARCHAR(36) | да |  | advertiser_brands.id |  |
| `advertiser_contract_id` | VARCHAR(36) | нет |  | advertiser_contracts.id |  |
| `code` | VARCHAR(64) | нет |  |  |  |
| `name` | VARCHAR(255) | нет |  |  |  |
| `description` | TEXT | да |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `priority` | INTEGER | нет |  |  |  |
| `budget_limit_amount` | NUMERIC(18, 2) | да |  |  |  |
| `budget_limit_currency` | VARCHAR(3) | нет |  |  |  |
| `start_at` | DATETIME | да |  |  |  |
| `end_at` | DATETIME | да |  |  |  |
| `timezone` | VARCHAR(64) | нет |  |  |  |
| `placement_basis` | VARCHAR(32) | нет |  |  |  |
| `created_by` | VARCHAR(36) | да |  | users.id |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `contract_upload_sessions`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `contract_id` | VARCHAR(36) | нет |  | advertiser_contracts.id |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `storage_bucket` | VARCHAR(128) | нет |  |  |  |
| `storage_key` | VARCHAR(512) | нет |  |  |  |
| `filename` | VARCHAR(255) | нет |  |  |  |
| `content_type` | VARCHAR(64) | нет |  |  |  |
| `content_length` | BIGINT | нет |  |  |  |
| `sha256_checksum` | VARCHAR(64) | да |  |  |  |
| `created_by` | VARCHAR(36) | да |  | users.id |  |
| `created_at` | DATETIME | нет |  |  |  |
| `expires_at` | DATETIME | нет |  |  |  |
| `completed_at` | DATETIME | да |  |  |  |

### `creative_upload_sessions`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `creative_asset_id` | VARCHAR(36) | нет |  | creative_assets.id |  |
| `advertiser_organization_id` | VARCHAR(36) | нет |  | advertiser_organizations.id |  |
| `storage_bucket` | VARCHAR(128) | нет |  |  |  |
| `storage_key` | VARCHAR(512) | нет |  |  |  |
| `filename` | VARCHAR(255) | нет |  |  |  |
| `content_type` | VARCHAR(64) | нет |  |  |  |
| `content_length` | INTEGER | нет |  |  |  |
| `expires_at` | DATETIME | нет |  |  |  |
| `completed_at` | DATETIME | да |  |  |  |
| `created_by` | VARCHAR(36) | да |  | users.id |  |
| `created_at` | DATETIME | нет |  |  |  |

### `physical_devices`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `store_id` | VARCHAR(36) | нет |  | stores.id |  |
| `device_type_id` | VARCHAR(36) | нет |  | device_types.id |  |
| `code` | VARCHAR(128) | нет |  |  |  |
| `serial_number` | VARCHAR(255) | нет |  |  |  |
| `hardware_fingerprint` | VARCHAR(255) | нет |  |  |  |
| `os_version` | VARCHAR(64) | нет |  |  |  |
| `ip_address` | VARCHAR(45) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `last_seen_at` | DATETIME | да |  |  |  |
| `last_heartbeat_at` | DATETIME | да |  |  |  |
| `health_state` | VARCHAR(32) | нет |  |  |  |
| `runtime_version` | VARCHAR(64) | нет |  |  |  |
| `player_version` | VARCHAR(128) | нет |  |  |  |
| `current_manifest_id` | VARCHAR(36) | да |  |  |  |
| `retailer_id` | VARCHAR(36) | да |  | retailers.id |  |
| `cache_size_bytes` | INTEGER | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `campaign_approvals`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `campaign_id` | VARCHAR(36) | нет |  | campaigns.id |  |
| `requested_by` | VARCHAR(36) | нет |  | users.id |  |
| `requested_at` | DATETIME | нет |  |  |  |
| `reviewed_by` | VARCHAR(36) | да |  | users.id |  |
| `reviewed_at` | DATETIME | да |  |  |  |
| `decision` | VARCHAR(32) | да |  |  |  |
| `rejection_reason` | TEXT | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `campaign_creatives`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `campaign_id` | VARCHAR(36) | нет |  | campaigns.id |  |
| `creative_asset_id` | VARCHAR(36) | нет |  | creative_assets.id |  |
| `sort_order` | INTEGER | нет |  |  |  |
| `duration_override_ms` | INTEGER | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `campaign_flights`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `campaign_id` | VARCHAR(36) | нет |  | campaigns.id |  |
| `name` | VARCHAR(255) | да |  |  |  |
| `start_at` | DATETIME | нет |  |  |  |
| `end_at` | DATETIME | нет |  |  |  |
| `dayparting_json` | JSONB | да |  |  |  |
| `days_of_week` | ARRAY | да |  |  |  |
| `priority` | INTEGER | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `campaign_status_history`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `campaign_id` | VARCHAR(36) | нет |  | campaigns.id |  |
| `old_status` | VARCHAR(32) | да |  |  |  |
| `new_status` | VARCHAR(32) | нет |  |  |  |
| `changed_by` | VARCHAR(36) | нет |  | users.id |  |
| `changed_at` | DATETIME | нет |  |  |  |
| `reason` | TEXT | да |  |  |  |

### `delivery_manifests`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `manifest_id` | VARCHAR(128) | нет |  |  |  |
| `campaign_id` | VARCHAR(36) | нет |  | campaigns.id |  |
| `physical_device_id` | VARCHAR(36) | нет |  | physical_devices.id |  |
| `content_hash` | VARCHAR(128) | нет |  |  |  |
| `manifest_version` | INTEGER | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `generated_at` | DATETIME | да |  |  |  |
| `delivered_at` | DATETIME | да |  |  |  |
| `last_error` | TEXT | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `retailer_id` | VARCHAR(36) | нет |  | retailers.id |  |

### `delivery_plans`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `campaign_id` | VARCHAR(36) | нет |  | campaigns.id |  |
| `campaign_version_hash` | VARCHAR(128) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `reason` | TEXT | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `device_certificates`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `physical_device_id` | VARCHAR(36) | нет |  | physical_devices.id |  |
| `certificate_type` | VARCHAR(32) | нет |  |  |  |
| `public_key` | TEXT | нет |  |  |  |
| `fingerprint` | VARCHAR(128) | нет |  |  |  |
| `issued_at` | DATETIME | нет |  |  |  |
| `expires_at` | DATETIME | да |  |  |  |
| `revoked_at` | DATETIME | да |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `device_onboarding_codes`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `code` | VARCHAR(128) | нет |  |  |  |
| `retailer_id` | VARCHAR(36) | нет |  | retailers.id |  |
| `store_id` | VARCHAR(36) | да |  | stores.id |  |
| `device_type_id` | VARCHAR(36) | да |  | device_types.id |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `hardware_fingerprint_bound` | VARCHAR(255) | да |  |  |  |
| `physical_device_id` | VARCHAR(36) | да |  | physical_devices.id |  |
| `created_by` | VARCHAR(36) | да |  | users.id |  |
| `created_at` | DATETIME | нет |  |  |  |
| `expires_at` | DATETIME | нет |  |  |  |
| `used_at` | DATETIME | да |  |  |  |

### `device_status_history`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `physical_device_id` | VARCHAR(36) | нет |  | physical_devices.id |  |
| `old_status` | VARCHAR(32) | нет |  |  |  |
| `new_status` | VARCHAR(32) | нет |  |  |  |
| `changed_at` | DATETIME | нет |  |  |  |
| `reason` | VARCHAR(255) | нет |  |  |  |
| `source` | VARCHAR(32) | нет |  |  |  |
| `details_json` | JSONB | да |  |  |  |

### `license_seats`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `license_id` | VARCHAR(36) | нет |  | license_grants.id |  |
| `device_id` | VARCHAR(36) | нет |  | physical_devices.id |  |
| `reserved_at` | DATETIME | нет |  |  |  |
| `released_at` | DATETIME | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `logical_carriers`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `physical_device_id` | VARCHAR(36) | нет |  | physical_devices.id |  |
| `code` | VARCHAR(128) | нет |  |  |  |
| `carrier_type` | VARCHAR(32) | нет |  |  |  |
| `vendor_name` | VARCHAR(255) | нет |  |  |  |
| `vendor_config_json` | JSONB | да |  |  |  |
| `labels_count` | INTEGER | да |  |  |  |
| `led_panels_count` | INTEGER | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `pop_events_raw`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `event_id` | VARCHAR(36) | нет |  |  |  |
| `schema_version` | VARCHAR(8) | нет |  |  |  |
| `device_id` | VARCHAR(36) | нет |  | physical_devices.id |  |
| `manifest_id` | VARCHAR(128) | да |  |  |  |
| `campaign_id` | VARCHAR(36) | да |  |  |  |
| `campaign_verified` | BOOLEAN | нет |  |  |  |
| `creative_asset_id` | VARCHAR(36) | нет |  | creative_assets.id |  |
| `surface_id` | VARCHAR(36) | нет |  |  |  |
| `rendered_at` | DATETIME | нет |  |  |  |
| `event_recorded_at` | DATETIME | нет |  |  |  |
| `duration_ms` | INTEGER | нет |  |  |  |
| `playback_result` | VARCHAR(32) | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `quarantine_reason` | VARCHAR(128) | да |  |  |  |
| `expires_at` | DATETIME | да |  |  |  |
| `received_at` | DATETIME | нет |  |  |  |
| `batch_id` | VARCHAR(36) | да |  |  |  |
| `retailer_id` | VARCHAR(36) | нет |  | retailers.id |  |

### `pop_ingestion_batches`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `device_id` | VARCHAR(36) | нет |  | physical_devices.id |  |
| `received_at` | DATETIME | нет |  |  |  |
| `event_count` | INTEGER | нет |  |  |  |
| `accepted_count` | INTEGER | нет |  |  |  |
| `rejected_count` | INTEGER | нет |  |  |  |
| `quarantined_count` | INTEGER | нет |  |  |  |

### `user_access_scopes`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `user_id` | VARCHAR(36) | нет |  | users.id |  |
| `access_scope_id` | VARCHAR(36) | нет |  | access_scopes.id |  |
| `created_at` | DATETIME | нет |  |  |  |

### `delivery_attempts`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `manifest_id` | VARCHAR(128) | нет |  | delivery_manifests.manifest_id |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `attempted_at` | DATETIME | нет |  |  |  |
| `error_code` | VARCHAR(64) | да |  |  |  |
| `error_message` | TEXT | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `delivery_manifest_assets`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `manifest_id` | VARCHAR(36) | нет |  | delivery_manifests.id |  |
| `creative_asset_id` | VARCHAR(36) | нет |  | creative_assets.id |  |
| `sha256_checksum` | VARCHAR(64) | нет |  |  |  |
| `duration_ms` | INTEGER | да |  |  |  |
| `media_type` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `display_surfaces`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `logical_carrier_id` | VARCHAR(36) | нет |  | logical_carriers.id |  |
| `store_id` | VARCHAR(36) | нет |  | stores.id |  |
| `code` | VARCHAR(128) | нет |  |  |  |
| `zone_id` | VARCHAR(36) | да |  |  |  |
| `shelf_id` | VARCHAR(36) | да |  |  |  |
| `category_id` | VARCHAR(36) | да |  |  |  |
| `sku_group_id` | VARCHAR(36) | да |  |  |  |
| `resolution_w` | INTEGER | нет |  |  |  |
| `resolution_h` | INTEGER | нет |  |  |  |
| `is_active` | BOOLEAN | нет |  |  |  |
| `current_manifest_id` | VARCHAR(36) | да |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `campaign_placements`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `campaign_id` | VARCHAR(36) | нет |  | campaigns.id |  |
| `display_surface_id` | VARCHAR(36) | да |  | display_surfaces.id |  |
| `store_id` | VARCHAR(36) | да |  | stores.id |  |
| `cluster_id` | VARCHAR(36) | да |  | clusters.id |  |
| `branch_id` | VARCHAR(36) | да |  | branches.id |  |
| `share_of_voice_pct` | INTEGER | нет |  |  |  |
| `max_impressions` | BIGINT | да |  |  |  |
| `impressions_delivered` | BIGINT | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `commerce_order_lines`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `order_id` | VARCHAR(36) | нет |  | commerce_orders.id |  |
| `surface_id` | VARCHAR(36) | нет |  | display_surfaces.id |  |
| `date_from` | DATE | нет |  |  |  |
| `date_to` | DATE | нет |  |  |  |
| `quantity_days` | INTEGER | нет |  |  |  |
| `unit_price_amount` | NUMERIC(12, 2) | нет |  |  |  |
| `line_amount` | NUMERIC(14, 2) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `commerce_price_items`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `tariff_version_id` | VARCHAR(36) | нет |  | commerce_tariff_versions.id |  |
| `surface_id` | VARCHAR(36) | нет |  | display_surfaces.id |  |
| `billing_unit` | VARCHAR(32) | нет |  |  |  |
| `unit_price_amount` | NUMERIC(12, 2) | нет |  |  |  |
| `currency` | VARCHAR(3) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `delivery_manifest_surfaces`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `manifest_id` | VARCHAR(36) | нет |  | delivery_manifests.id |  |
| `display_surface_id` | VARCHAR(36) | нет |  | display_surfaces.id |  |
| `slot_order` | INTEGER | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |

### `inventory_slots`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `display_surface_id` | VARCHAR(36) | нет |  | display_surfaces.id |  |
| `slot_date` | DATE | нет |  |  |  |
| `slot_hour` | INTEGER | нет |  |  |  |
| `total_capacity` | INTEGER | нет |  |  |  |
| `booked_capacity` | INTEGER | нет |  |  |  |
| `reserved_capacity` | INTEGER | нет |  |  |  |
| `internal_blocked_capacity` | INTEGER | нет |  |  |  |
| `emergency_blocked_capacity` | INTEGER | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

### `inventory_bookings`

| Колонка | Тип | Null | PK | FK | Default |
|---|---|---|---|---|---|
| `id` | VARCHAR(36) | нет | ✔ |  |  |
| `campaign_id` | VARCHAR(36) | да |  | campaigns.id |  |
| `campaign_placement_id` | VARCHAR(36) | да |  | campaign_placements.id |  |
| `inventory_slot_id` | VARCHAR(36) | нет |  | inventory_slots.id |  |
| `capacity_units` | INTEGER | нет |  |  |  |
| `status` | VARCHAR(32) | нет |  |  |  |
| `reserved_until` | DATETIME | да |  |  |  |
| `committed_at` | DATETIME | да |  |  |  |
| `released_at` | DATETIME | да |  |  |  |
| `release_reason` | VARCHAR(512) | нет |  |  |  |
| `created_at` | DATETIME | нет |  |  |  |
| `updated_at` | DATETIME | нет |  |  |  |

