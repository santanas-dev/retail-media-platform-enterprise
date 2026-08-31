# OpenAPI + event/manifest JSON Schema — as-built и target v2.6 (артефакт AG, RM-TECH-220)

> Статус: **candidate/prepared 2026-08-31 (OD-043)** — as-built снят, target подготовлен как mini-design; задача RM-TECH-220 остаётся planned до Gate-S, приёмка — внутри задачи, не сейчас. REQ-ARCH-001, REQ-API-001/002/003, REQ-POP-*; SC-API-001, SC-ARCH-003.
> Источник as-built: `app.openapi()` control-api на develop @ 06ae22e (код = 4ac3ddb) → `openapi-as-built-v1.json` (OpenAPI 3.1.0, «RMP Control API» 0.3.0: 113 paths, 128 операций, 149 схем). Код не менялся.

## 1. As-built группы

| Префикс | Paths | Назначение |
|---|---|---|
| `/api/v1/identity` | 100 | User/identity API (портал) |
| `/api/v1/auth` | 5 | auth |
| `/api/v1/public` | 2 | публичные формы |
| `/api/v1/pop` | 1 | PoP ingestion (device JWT) |
| `/api/v1/device` | 1 | Device API (onboarding) |
| `/health/live` | 1 | liveness/readiness/identity/metrics |
| `/version` | 1 | liveness/readiness/identity/metrics |
| `/health/ready` | 1 | liveness/readiness/identity/metrics |
| `/metrics` | 1 | liveness/readiness/identity/metrics |

Существующие контракты: `packages/contracts/manifest_v1.schema.json`, `packages/contracts/proof_event_v1.schema.json` (+ `manifest_signing.py`), envelope событий outbox — `docs/architecture/events/event-envelope-v1.schema.json` (as-built из `outbox_relay.py`).
Health/identity: `GET /health/live`, `GET /health/ready` (db + NOBYPASSRLS check), `GET /version` (git_sha/schema_head/environment), `GET /metrics`.

## 2. Target v2.6 (§13, §26/AB ТЗ) — дельты к as-built

| # | Дельта | Режим | Задача | Acceptance |
|---|---|---|---|---|
| 1 | Версионирование: `openapi.info.version` = семантическая версия API, `x-deprecation` для alias-маршрутов, deprecation date в описании; contract tests сверяют as-built с этим документом | adapt | RM-TECH-220 | `tests/behavioral/test_rm_tech_220.py`; guard command |
| 2 | Канонический `POST /api/v1/pop/batch`; legacy `/device/pop/batch` — alias с deprecation date; ответ 200 + per-event `status=duplicate` c machine code 409 в теле (OD-019), 422 при невалидной схеме | adapt | RM-TECH-222, RM-TECH-225 | contract test PoP; amendment ADR-017 |
| 3 | Разделение User/Device/analytics/emergency API: device client (JWT device) не достигает `/api/v1/identity/*`; отдельный префикс Device API | adapt | RM-TECH-221 | negative test 403/404 для device JWT на identity |
| 4 | Manifest field contract: opaque `media_ref`, без MinIO-ключей, ACK-состояния runtime | adapt | RM-TECH-223 | schema + behavioral |
| 5 | Heartbeat `POST /api/v1/device/heartbeat`: дедуп, scope, clock drift, freshness, объявление поддерживаемых версий API/manifest | adapt | RM-TECH-224, RM-TECH-228 | behavioral |
| 6 | Для каждого endpoint: auth/scope, idempotency, pagination, error codes, retryability, rate limit, compatibility window, deprecation policy (§13) — таблица в §4 ниже заполняется по группам | adapt | RM-TECH-220 | документ + contract tests |
| 7 | Channel Adapter API / Worker API — versioned contract spec без реализации (ADR-019) | new (design) | RM-TECH-230 | docs/architecture contract |

## 3. События (as-built)

Envelope: `event_id, event_type, event_version, aggregate_type, aggregate_id, payload, headers, created_at`; subject = `event_type`; dedupe по `event_id`.
Типы: `campaign.creative.changed`, `campaign.flight.changed`, `campaign.placement.changed`, `delivery.manifest.generated`, `delivery.manifest.failed`, `pop.batch.ingested`, `pop.event.accepted`, `pop.event.quarantined`. Target: payload JSON Schema на каждый тип (RM-TECH-220), запрет secrets/PII в payload (§13), revocation/refresh manifest events (RM-TECH-242).

## 4. Инвентарь операций as-built (для контрактной таблицы §13)

| Метод | Path | Summary | Теги |
|---|---|---|---|
| POST | `/api/v1/auth/change-password` | Change Password | auth |
| POST | `/api/v1/auth/login` | Login | auth |
| POST | `/api/v1/auth/logout` | Logout | auth |
| GET | `/api/v1/auth/me` | Me | auth |
| POST | `/api/v1/auth/refresh` | Refresh | auth |
| POST | `/api/v1/device/onboard` | Device Onboard |  |
| GET | `/api/v1/identity/advertiser-applications` | List Applications | identity |
| GET | `/api/v1/identity/advertiser-applications/{application_id}` | Get Application | identity |
| GET | `/api/v1/identity/advertiser-applications/{application_id}/invite` | Get Application Invite | identity |
| POST | `/api/v1/identity/advertiser-applications/{application_id}/invite` | Create Application Invite | identity |
| POST | `/api/v1/identity/advertiser-applications/{application_id}/review` | Review Application | identity |
| GET | `/api/v1/identity/advertiser-brands` | List Advertiser Brands | identity |
| POST | `/api/v1/identity/advertiser-brands` | Create Advertiser Brand | identity |
| GET | `/api/v1/identity/advertiser-brands-by-org` | List Advertiser Brands By Org | identity |
| PATCH | `/api/v1/identity/advertiser-brands/{brand_id}` | Update Advertiser Brand | identity |
| GET | `/api/v1/identity/advertiser-contacts` | List Advertiser Contacts | identity |
| POST | `/api/v1/identity/advertiser-contacts` | Create Advertiser Contact | identity |
| GET | `/api/v1/identity/advertiser-contacts-by-org` | List Advertiser Contacts By Org | identity |
| PATCH | `/api/v1/identity/advertiser-contacts/{contact_id}` | Update Advertiser Contact | identity |
| GET | `/api/v1/identity/advertiser-contracts` | List Advertiser Contracts | identity |
| POST | `/api/v1/identity/advertiser-contracts` | Create Advertiser Contract | identity |
| GET | `/api/v1/identity/advertiser-contracts-by-org` | List Advertiser Contracts By Org | identity |
| PATCH | `/api/v1/identity/advertiser-contracts/{contract_id}` | Update Advertiser Contract | identity |
| POST | `/api/v1/identity/advertiser-contracts/{contract_id}/complete-upload` | Contract Complete Upload | identity |
| POST | `/api/v1/identity/advertiser-contracts/{contract_id}/upload-intent` | Contract Upload Intent | identity |
| GET | `/api/v1/identity/advertiser-organizations` | List Advertiser Organizations | identity |
| POST | `/api/v1/identity/advertiser-organizations` | Create Advertiser Organization | identity |
| GET | `/api/v1/identity/advertiser-organizations/{org_id}` | Get Advertiser Organization Detail | identity |
| PUT | `/api/v1/identity/advertiser-organizations/{org_id}/legal-requisites` | Update Advertiser Organization Legal Requisites | identity |
| GET | `/api/v1/identity/advertiser-user-memberships` | List Advertiser User Memberships | identity |
| GET | `/api/v1/identity/audit-events` | List Audit Events | identity |
| GET | `/api/v1/identity/auth/ad-settings` | Get Ad Settings | identity |
| PUT | `/api/v1/identity/auth/ad-settings` | Update Ad Settings | identity |
| POST | `/api/v1/identity/auth/ad-settings/test` | Test Ad Connection | identity |
| GET | `/api/v1/identity/branches` | List Branches | identity |
| GET | `/api/v1/identity/campaign-approvals` | List Campaign Approvals | identity |
| GET | `/api/v1/identity/campaign-briefs` | List Briefs | identity |
| POST | `/api/v1/identity/campaign-briefs` | Create Brief | identity |
| GET | `/api/v1/identity/campaign-briefs/{brief_id}` | Get Brief | identity |
| PATCH | `/api/v1/identity/campaign-briefs/{brief_id}` | Update Brief | identity |
| POST | `/api/v1/identity/campaign-briefs/{brief_id}/submit` | Submit Brief | identity |
| GET | `/api/v1/identity/campaign-creatives` | List Campaign Creatives | identity |
| GET | `/api/v1/identity/campaign-flights` | List Campaign Flights | identity |
| GET | `/api/v1/identity/campaign-placements` | List Campaign Placements | identity |
| GET | `/api/v1/identity/campaign-status-history` | List Campaign Status History | identity |
| GET | `/api/v1/identity/campaigns` | List Campaigns | identity |
| POST | `/api/v1/identity/campaigns` | Create Campaign Endpoint | identity |
| GET | `/api/v1/identity/campaigns/approval-queue` | Approval Queue Endpoint | identity |
| POST | `/api/v1/identity/campaigns/complete-expired` | Complete Expired Endpoint | identity |
| PATCH | `/api/v1/identity/campaigns/{campaign_id}` | Update Campaign Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/activate` | Activate Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/approve` | Approve Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/archive` | Archive Campaign Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/complete` | Complete Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/creatives` | Create Creative Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/creatives/attach` | Attach Creative Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/flights` | Create Flight Endpoint | identity |
| PATCH | `/api/v1/identity/campaigns/{campaign_id}/flights/{flight_id}` | Update Flight Endpoint | identity |
| GET | `/api/v1/identity/campaigns/{campaign_id}/inventory-conflicts` | Get Campaign Inventory Conflicts | identity |
| GET | `/api/v1/identity/campaigns/{campaign_id}/inventory-reservations` | List Campaign Inventory Reservations | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/pause` | Pause Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/placements` | Create Placement Endpoint | identity |
| PATCH | `/api/v1/identity/campaigns/{campaign_id}/placements/{placement_id}` | Update Placement Endpoint | identity |
| GET | `/api/v1/identity/campaigns/{campaign_id}/pop/by-day` | Get Campaign Pop By Day | identity |
| GET | `/api/v1/identity/campaigns/{campaign_id}/pop/by-surface` | Get Campaign Pop By Surface | identity |
| GET | `/api/v1/identity/campaigns/{campaign_id}/pop/export` | Export Campaign Pop Csv | identity |
| GET | `/api/v1/identity/campaigns/{campaign_id}/pop/summary` | Get Campaign Pop Summary | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/reject` | Reject Endpoint | identity |
| POST | `/api/v1/identity/campaigns/{campaign_id}/request-approval` | Request Approval Endpoint | identity |
| GET | `/api/v1/identity/clusters` | List Clusters | identity |
| GET | `/api/v1/identity/commerce/orders` | List Orders | identity |
| POST | `/api/v1/identity/commerce/orders` | Create Order | identity |
| GET | `/api/v1/identity/commerce/orders/{order_id}` | Get Order | identity |
| PATCH | `/api/v1/identity/commerce/orders/{order_id}` | Update Order | identity |
| GET | `/api/v1/identity/commerce/price-items` | List Price Items | identity |
| POST | `/api/v1/identity/commerce/price-items` | Create Price Item | identity |
| PATCH | `/api/v1/identity/commerce/price-items/{price_item_id}` | Update Price Item | identity |
| POST | `/api/v1/identity/commerce/quote` | Quote | identity |
| GET | `/api/v1/identity/commerce/tariff-versions` | List Tariff Versions | identity |
| POST | `/api/v1/identity/commerce/tariff-versions` | Create Tariff Version | identity |
| PATCH | `/api/v1/identity/commerce/tariff-versions/{tariff_id}` | Update Tariff Version | identity |
| GET | `/api/v1/identity/creative-assets` | List Creative Assets | identity |
| POST | `/api/v1/identity/creative-assets` | Create Creative Asset Endpoint | identity |
| GET | `/api/v1/identity/creative-assets/moderation-queue` | Moderation Queue Endpoint | identity |
| POST | `/api/v1/identity/creative-assets/{asset_id}/approve` | Approve Creative Endpoint | identity |
| POST | `/api/v1/identity/creative-assets/{asset_id}/complete-upload` | Complete Upload Endpoint | identity |
| POST | `/api/v1/identity/creative-assets/{asset_id}/reject` | Reject Creative Endpoint | identity |
| POST | `/api/v1/identity/creative-assets/{asset_id}/upload-intent` | Upload Intent Endpoint | identity |
| POST | `/api/v1/identity/device-codes` | Create Device Code |  |
| GET | `/api/v1/identity/devices` | List Devices | identity |
| GET | `/api/v1/identity/devices/summary` | Device Summary | identity |
| GET | `/api/v1/identity/devices/{device_id}` | Get Device | identity |
| POST | `/api/v1/identity/devices/{device_id}/decommission` | Decommission Device | identity |
| GET | `/api/v1/identity/display-surfaces` | List Display Surfaces | identity |
| POST | `/api/v1/identity/emergency/activate` | Emergency Activate | identity |
| POST | `/api/v1/identity/emergency/deactivate` | Emergency Deactivate | identity |
| GET | `/api/v1/identity/emergency/status` | Emergency Status | identity |
| POST | `/api/v1/identity/inventory/alternatives` | Suggest Alternatives | identity |
| POST | `/api/v1/identity/inventory/availability` | Check Availability | identity |
| POST | `/api/v1/identity/inventory/conflicts/check` | Check Inventory Conflicts | identity |
| GET | `/api/v1/identity/inventory/rules` | List Rules | identity |
| POST | `/api/v1/identity/inventory/rules` | Create Rule | identity |
| PATCH | `/api/v1/identity/inventory/rules/{rule_id}` | Update Rule | identity |
| POST | `/api/v1/identity/inventory/rules/{rule_id}/activate` | Activate Rule | identity |
| POST | `/api/v1/identity/inventory/rules/{rule_id}/deactivate` | Deactivate Rule | identity |
| POST | `/api/v1/identity/inventory/simulate` | Simulate Inventory | identity |
| GET | `/api/v1/identity/inventory/stores` | List Inventory Stores | identity |
| GET | `/api/v1/identity/inventory/surfaces` | List Inventory Surfaces | identity |
| PATCH | `/api/v1/identity/inventory/surfaces/{surface_id}` | Patch Inventory Surface | identity |
| GET | `/api/v1/identity/licenses/report` | License Report | identity |
| GET | `/api/v1/identity/permissions` | List Permissions | identity |
| GET | `/api/v1/identity/roles` | List Roles | identity |
| GET | `/api/v1/identity/stores` | List Stores | identity |
| GET | `/api/v1/identity/users` | List Users | identity |
| POST | `/api/v1/identity/users/local-advertiser` | Create Local Advertiser | identity |
| GET | `/api/v1/identity/users/{user_id}` | Get User | identity |
| POST | `/api/v1/identity/users/{user_id}/activate` | Activate User | identity |
| POST | `/api/v1/identity/users/{user_id}/deactivate` | Deactivate User | identity |
| POST | `/api/v1/identity/users/{user_id}/reset-password` | Reset Password | identity |
| PUT | `/api/v1/identity/users/{user_id}/roles` | Assign Role | identity |
| DELETE | `/api/v1/identity/users/{user_id}/roles/{assignment_id}` | Remove Role | identity |
| POST | `/api/v1/pop/batch` | Ingest Batch | pop |
| POST | `/api/v1/public/advertiser-applications` | Submit Application |  |
| POST | `/api/v1/public/advertiser-invites/{token}/accept` | Accept Invite |  |
| GET | `/health/live` | Health Live |  |
| GET | `/health/ready` | Health Ready |  |
| GET | `/metrics` | Metrics |  |
| GET | `/version` | Version |  |
