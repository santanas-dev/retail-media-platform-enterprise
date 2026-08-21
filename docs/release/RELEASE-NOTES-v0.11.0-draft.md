# Release Notes — Draft (R4 pilot/control-plane)

> **Status: DRAFT** — подготовлено в R4-READINESS-001 (evidence-based audit).
> Тег **НЕ создан**. Merge в main **НЕ выполнен**. Production-ready **НЕ заявляется**.

**Proposed version/tag:** `v0.11.0-pilot-control-plane`
(альтернатива: `v0.11.0-rc1`)

**Candidate SHA:** `c14dd3e` (develop, 2026-08-21) — включает UI-SMOKE-STABILITY-004,
EPIC-L A1–A4 (Layer 1), Commerce Contour 2, advertiser onboarding, theme/tokens.

---

## Что вошло после R3 (main `96b5159` → candidate `c14dd3e`)

- **204 commits**, **199 файлов** (+24 460 / −1 436).
- **6 migrations** (029–034), линейная цепочка, один head.

## Migrations 029–034

| # | Назначение |
|---|-----------|
| 029 | Legal requisites columns → `advertiser_organizations` (nullable) |
| 030 | File metadata → `advertiser_contracts` + `contract_upload_sessions` |
| 031 | `user_id` FK (SET NULL) + `title` → `advertiser_contacts` |
| 032 | Commerce Contour 2 foundation tables |
| 033 | Commerce RLS (ENABLE + FORCE) |
| 034 | License seat ledger tables + RLS (ENABLE + FORCE) |

## Feature-результаты (17 стали reachable после R3)

Программно пересчитано: **58 total / 52 reachable / 6 blocked** (на R3 было 40/35/5).

- **Commerce Contour 2 (7):** tariff_manage, price_list_manage, order_create,
  offer_generate, booking, payment_status, order_close.
- **Advertiser onboarding (4):** legal_requisites, brand_crud, contract_crud, contact_crud.
- **Licensing Layer 1 (3):** enforce, seat_release, report.
- **Прочее (3):** system.theme_switch (dark theme), user.split_internal_advertiser,
  campaign.complete.

## Основные направления

- **Commerce Contour 2** — коммерческий движок продаж (тарифы, прайс-листы, заказы,
  офферы, бронирование, статус оплаты, закрытие заказа) + DB-level RLS backstop.
- **RLS / pricing hardening** — scope context, текущий-over-revoked, grandfather
  reconciliation.
- **Advertiser onboarding UX** — legal/brand/contract/contact, приглашения, RLS.
- **CI truth / stability** — UI-SMOKE-STABILITY-004: production bundle smoke,
  concurrency group, 3×38/38.
- **Theme / tokens** — dark theme + semantic tokens (`data-theme="dark"`).
- **Campaign completion** — автоматическое завершение по концу рейса.
- **EPIC-L Layer 1** — unsigned dev-ingest licensing: seat ledger, enrollment
  enforcement, decommission release, exact UTC monthly peak, report API,
  reconciliation, import boundary.

## Breaking / config changes

- `GET /licenses/report?year&month` — новый endpoint, `license.read` permission
  (system_admin/security_admin). Seed пополнится при следующем `seed.py`.
- `POST /devices/{device_id}/decommission` — новый endpoint, `devices.manage`.
- **FORCE ROW LEVEL SECURITY** на `commerce_*` (033) и `license_*` (034):
  `retail_media_app` обязан выставлять RLS-контекст (`app.rmp_is_admin`). Без него
  эти таблицы пусты — by design (DB-level backstop).

## Известные ограничения

- 6 blocked feature IDs: `self.report_view` (PoP/player path), `self.campaign_create`
  (deferred P2), `playlist.build` (service-deferred), `backup.restore` (нет restore
  drill), `license.view` / `license.upload` (Layer 2 signed-license/UI).
- EPIC-L Layer 1 = **unsigned** dev-ingest; signed `.lic` (JWS/Ed25519, kid/CRL,
  offline verify) — Layer 2, не реализовано.
- KSO client — hardware-independent контракт, **не** реальный player; KSO proof отсутствует.
- CD workflow отсутствует; deployed production SHA не отслеживается.
- Operator walkthrough — PENDING.

## Rollback prerequisites

- **Код-rollback безопасен:** R3 binary работает после schema 034 (029–034 добавляют
  только nullable-колонки + новые таблицы + RLS на новых таблицах; существующие
  таблицы не ломаются).
- **Schema-downgrade (034→028) — lossy** для commerce/license данных. Если после R4
  записаны бизнес-данные, downgrade их удалит → обязательный **restore-from-backup**
  (но `backup.restore` остаётся blocked до реального restore drill).
