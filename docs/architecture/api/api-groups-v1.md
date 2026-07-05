# API Groups v1 — Retail Media Platform

**Version:** 1.0
**Phase:** 0 (Architecture Lock)
**Source:** ТЗ v2.5 Table 20; §16.1, §24.11

---

## API Architecture

Four logically separated API groups, each with its own authentication, rate limiting, and versioning.

```
┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐
│ User API     │  │ Device API    │  │ Internal API │  │ Analytics API│
│ /api/v1/*    │  │ /device/v1/*  │  │ /internal/*  │  │ /analytics/* │
│ Control Plane│  │ Device Gateway│  │ Inter-service│  │ Read-only BI │
│ AD/SSO + MFA │  │ JWT (device)  │  │ Service auth │  │ AD/SSO       │
└──────────────┘  └───────────────┘  └──────────────┘  └──────────────┘
```

---

## 1. Auth API

> **Status: Phase 3.2d — Implemented.** See ADR-006 for architecture decisions.
> Endpoints live, auth service wired. No RBAC/middleware enforcement yet.
>
> **Cookie security:** Refresh token cookie is `HttpOnly; SameSite=Strict; Path=/api/v1/auth`. `Secure` flag is **on in production, off in local dev** (HTTP). See `packages/security/config.py:refresh_token_cookie_secure`.
>
> **Next phases:**
> - **Phase 3.3** — All non-health endpoints protected by JWT + RBAC middleware. Identity endpoints (`/api/v1/identity/*`) require `users.read` permission. ✅
> - **Phase 3.4** — Real PostgreSQL behavioral auth/RBAC tests. ✅
> - **Phase 3.5a** — Scope/RLS architecture lock (ADR-009): fail-closed two-layer defense, `advertiser_organizations` pilot target.
> - **Phase 3.5b** — PostgreSQL RLS implementation: `SET LOCAL` session vars, RLS policies, `ScopeContext` dependency, behavioral tests.

### Identity Types (ADR-006)

Three distinct identity types share `/api/v1/auth/*` endpoints, distinguished by `auth_provider`:

| Type | `auth_provider` | Auth method | Use case |
|------|-----------------|-------------|----------|
| Internal staff | `ad` | LDAPS bind/search | Admin, managers, analysts |
| Advertiser user | `local_advertiser` | Email + bcrypt password | Advertiser cabinet |
| Break-glass admin | `local_break_glass` | Local bcrypt (emergency) | AD outage recovery |

Auth endpoints determine `auth_provider` from the login payload or by username/email lookup.

### Auth Protocol: LDAP bind/search (ADR-006)

- Primary identity provider for internal staff: Active Directory via LDAPS (port 636)
- Advertiser auth: local credentials in separate `local_credentials` table (not in `users`)
- Break-glass: emergency local access only, fully audited, CRITICAL-level events
- Session: JWT access token (15 min) + opaque refresh token (8 h) in HttpOnly Secure SameSite cookie
- MFA: deferred until AD/IdP mechanism is confirmed

### Planned Endpoints (Phase 3.2+)

> **Phase 3.2d (implemented):** Login, refresh, logout, me.

| Method | Endpoint | Auth | Permission | Description | Status |
|--------|----------|------|------------|-------------|--------|
| POST | `/api/v1/auth/login` | None | — | Login for all identity types. Returns `{access_token, expires_in, user}` + `Set-Cookie` refresh token. | ✅ 3.2d |
| POST | `/api/v1/auth/refresh` | Refresh token cookie | — | Rotate refresh token, return new access token + Set-Cookie | ✅ 3.2d |
| POST | `/api/v1/auth/logout` | Refresh token cookie | — | Revoke session, clear cookie | ✅ 3.2d |
| GET | `/api/v1/auth/me` | JWT | — | Current user claims (sub, auth_provider) decoded from JWT | ✅ 3.2d |
| POST | `/api/v1/auth/mfa/verify` | JWT (partial) | — | MFA second factor | deferred |

**Advertiser-specific (planned, Phase 3.2+):**

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-------------|-------------|
| POST | `/api/v1/auth/register` | None | — | Self-registration (advertiser). Email verification required. |
| POST | `/api/v1/auth/verify-email` | Verification token | — | Confirm email address |
| POST | `/api/v1/auth/password-reset/request` | None | — | Send reset link. Generic response — no user enumeration. |
| POST | `/api/v1/auth/password-reset/confirm` | Reset token | — | Set new password |

### Security: No User Enumeration

Login and password-reset endpoints return **identical responses** whether the user/email exists or not:

- Login failure: `{"error": {"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"}}` (HTTP 401) — regardless of whether the email is registered
- Password reset request: `{"message": "If this email is registered, a reset link has been sent"}` (HTTP 200) — always, even for unknown emails
- Rate limits are per-identifier but errors are generic

---

## 2. Users & RBAC API

> **Phase 3.0 (previously unprotected):** Endpoints are now **protected** as of Phase 3.3.
> All identity endpoints require JWT + appropriate permission:
> - `GET /api/v1/identity/users` → `users.read`
> - `GET /api/v1/identity/roles` → `roles.read`
> - `GET /api/v1/identity/permissions` → `roles.read`
> - `GET /api/v1/identity/audit-events` → `audit.read`
>
> **Phase 3.5 complete:** Auth + RBAC + advertiser RLS pilot + app-layer
> scoped permission guard + behavioral proof.
>
> Tenant RLS/scopes deferred to Phase 3.5. **Architecture locked in ADR-009** —
> fail-closed two-layer defense: app `ScopeContext` + PostgreSQL RLS.
> **Implemented (Phase 3.5b–3.5c):**
> - `GET /api/v1/identity/advertiser-organizations` — scoped permission
>   (`organization.read` global OR advertiser scope) + PostgreSQL RLS
> - RLS on `advertiser_organizations` / `advertiser_user_memberships`
> - Tenant RLS expansion to campaigns/placements deferred to 3.6+
>
> **Implemented (Phase 3.0, protected in 3.3):**
> - `GET /api/v1/identity/users` — list users (paginated, limit/offset)
> - `GET /api/v1/identity/roles` — list roles
> - `GET /api/v1/identity/permissions` — list permissions
> - `GET /api/v1/identity/audit-events` — list operational audit events (paginated)
>
> **Planned (Phase 3.2+, after auth middleware):**
> - All endpoints require JWT + permission
> - Paths may be consolidated under `/api/v1/*` or remain at `/api/v1/identity/*`
> - Mutation endpoints (create/update/assign/block) per original table below

### Full Planned Surface (post-Phase 3.2)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/users` | JWT | `users.read` | List users (paginated, filterable) |
| POST | `/api/v1/users` | JWT | `users.create` | Create user |
| GET | `/api/v1/users/{id}` | JWT | `users.read` | Get user details |
| PATCH | `/api/v1/users/{id}` | JWT | `users.manage` | Update user |
| POST | `/api/v1/users/{id}/roles` | JWT | `roles.manage` | Assign role to user |
| DELETE | `/api/v1/users/{id}/roles/{role_id}` | JWT | `roles.manage` | Remove role |
| POST | `/api/v1/users/{id}/block` | JWT | `users.manage` | Block/unlock user |
| GET | `/api/v1/roles` | JWT | `roles.read` | List roles |
| GET | `/api/v1/permissions` | JWT | `permissions.read` | List permissions |
| GET | `/api/v1/users/{id}/scopes` | JWT | `users.read` | Get RLS scopes |

---

## 3. Organization API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/branches` | JWT | `hierarchy.read` | List branches |
| POST | `/api/v1/branches` | JWT | `hierarchy.manage` | Create branch |
| GET | `/api/v1/clusters` | JWT | `hierarchy.read` | List clusters (filter by branch) |
| GET | `/api/v1/stores` | JWT | `hierarchy.read` | List stores (filter by cluster) |
| GET | `/api/v1/store-zones` | JWT | `hierarchy.read` | List store zones |

---

## 4. Advertiser API

> **Status: Phase 4.0b — Read-only foundation complete.**
> All advertiser endpoints require JWT + `require_scoped_permission` +
> PostgreSQL RLS (two-layer defense per ADR-009).  Contacts are PII-gated
> behind `advertisers.contacts.read` (separate from `advertisers.read`).
> Architecture locked in ADR-010.

### Read-Only Endpoints (Phase 4.0b — ✅ Implemented)

All live under `/api/v1/identity/`.

| Method | Endpoint | Auth | Permission | Scope | Status |
|--------|----------|------|------------|-------|--------|
| GET | `/api/v1/identity/advertiser-organizations` | JWT | `organization.read` | Global: all orgs. Advertiser scoped: own org only (RLS). | ✅ 4.0b |
| GET | `/api/v1/identity/advertiser-brands` | JWT | `advertisers.read` | Filtered by org scope (RLS). | ✅ 4.0b |
| GET | `/api/v1/identity/advertiser-contracts` | JWT | `advertisers.read` | Filtered by org scope (RLS). | ✅ 4.0b |
| GET | `/api/v1/identity/advertiser-contacts` | JWT | `advertisers.contacts.read` | Filtered by org scope (RLS). PII-gated. | ✅ 4.0b |

**Behavioral proof:** advertiser-domain behavioral tests cover auth (401),
scoped access (403 / 200), RLS row visibility, and the contacts PII gate
(`advertisers.contacts.read` required separately from `advertisers.read`).

### Mutations (deferred — Phase 4.0c+)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| POST | `/api/v1/advertisers/organizations` | JWT | `advertisers.manage` | Create organization |
| PATCH | `/api/v1/advertisers/organizations/{id}` | JWT | `advertisers.manage` | Update organization |
| POST | `/api/v1/advertisers/brands` | JWT | `advertisers.manage` | Create brand |
| POST | `/api/v1/advertisers/contracts` | JWT | `advertisers.manage` | Create contract |
| POST | `/api/v1/advertisers/{id}/contacts` | JWT | `advertisers.contacts.manage` | Add contact |
| PATCH | `/api/v1/advertisers/contacts/{id}` | JWT | `advertisers.contacts.manage` | Update contact |

> **Security invariants (from ADR-010):**
> - Every endpoint: negative behavioral test required before acceptance
>   (no-token 401, wrong-scope 403, scoped sees own, admin sees all)
> - Contact email/phone never in audit event details
> - No hard delete for orgs with campaigns/contracts
> - `advertiser_organizations` is tenant root for all advertiser-scoped data

---

## 5. Channels & Devices API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/channels` | JWT | `channels.read` | List channels |
| GET | `/api/v1/device-types` | JWT | `devices.read` | List device types |
| GET | `/api/v1/device-types/{id}/capabilities` | JWT | `devices.read` | Capability profile |
| GET | `/api/v1/devices` | JWT | `devices.read` | List physical devices (paginated) |
| POST | `/api/v1/devices` | JWT | `devices.manage` | Register device (manual) |
| GET | `/api/v1/devices/{id}` | JWT | `devices.read` | Device details |
| PATCH | `/api/v1/devices/{id}` | JWT | `devices.manage` | Update device |
| POST | `/api/v1/devices/{id}/commands` | JWT | `devices.command` | Send command to device |
| GET | `/api/v1/logical-carriers` | JWT | `devices.read` | List logical carriers |
| GET | `/api/v1/display-surfaces` | JWT | `devices.read` | List display surfaces |
| GET | `/api/v1/player-builds` | JWT | `devices.read` | List player versions |

---

## 6. Advertisers API (Legacy — superseded by §4)

> **Superseded by ADR-010 (Phase 4.0a).**  See §4 Advertiser API above for
> current planned endpoints with proper scoping, RLS, and behavioral test
> requirements.

---

## 7. Campaigns & Placements API

> **Status: Phase 4.1b — Implemented (read-only).**
> All campaign endpoints live under `/api/v1/identity/` in Phase 4.1b
> (provisional flat list-all paths).  Nested REST paths under
> `/api/v1/campaigns/{code}/...` are planned for mutation/detail phases
> (4.1c+).  Architecture locked in ADR-015.
>
> **Current (Phase 4.1b) endpoints:**
>
> | Method | Endpoint | Auth | Permission | Status | Description |
> |--------|----------|------|------------|--------|-------------|
> | GET | `/api/v1/identity/campaigns` | JWT | `campaigns.read` | ✅ 4.1b | List all campaigns (scoped + RLS) |
> | GET | `/api/v1/identity/campaign-flights` | JWT | `campaigns.read` | ✅ 4.1b | List all flights (scoped + RLS) |
> | GET | `/api/v1/identity/campaign-creatives` | JWT | `campaigns.read` | ✅ 4.1b | List campaign-creative links |
> | GET | `/api/v1/identity/creative-assets` | JWT | `creatives.read` | ✅ 4.1b | List creative assets (metadata only) |
> | GET | `/api/v1/identity/campaign-placements` | JWT | `campaigns.read` | ✅ 4.1b | List placements |
> | GET | `/api/v1/identity/campaign-approvals` | JWT | `campaigns.read` | ✅ 4.1b | List approval records |
> | GET | `/api/v1/identity/campaign-status-history` | JWT | `campaigns.read` | ✅ 4.1b | List status history |
>
> **Future REST paths (Phase 4.1c+):**

### Phase 4.1c — Mutations (planned, deferred)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| POST | `/api/v1/campaigns` | JWT | `campaigns.create` | Create campaign (draft) |
| PATCH | `/api/v1/campaigns/{code}` | JWT | `campaigns.manage` or owner | Update campaign (draft/rejected only) |
| POST | `/api/v1/campaigns/{code}/submit` | JWT | `campaigns.create` or owner | Submit for approval |
| PATCH | `/api/v1/campaigns/{code}/status` | JWT | `campaigns.manage` | Force status transition |
| POST | `/api/v1/campaigns/{code}/placements` | JWT | `campaigns.manage` or owner | Add placement |
| DELETE | `/api/v1/campaigns/{code}/placements/{id}` | JWT | `campaigns.manage` or owner | Remove placement |
| POST | `/api/v1/campaigns/{code}/creatives` | JWT | `campaigns.manage` or owner | Link creative |
| DELETE | `/api/v1/campaigns/{code}/creatives/{id}` | JWT | `campaigns.manage` or owner | Unlink creative |
| POST | `/api/v1/campaigns/{code}/flights` | JWT | `campaigns.manage` or owner | Add flight/period |
| PATCH | `/api/v1/campaigns/{code}/flights/{id}` | JWT | `campaigns.manage` or owner | Update flight |
| DELETE | `/api/v1/campaigns/{code}/flights/{id}` | JWT | `campaigns.manage` or owner | Remove flight |
| POST | `/api/v1/creatives/upload` | JWT | `creatives.upload` | Upload creative asset (presigned) |

### Phase 4.1d — Approval Workflow (planned, deferred)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| POST | `/api/v1/campaigns/{code}/approve` | JWT | `campaigns.approve` | Approve campaign (operator/admin) |
| POST | `/api/v1/campaigns/{code}/reject` | JWT | `campaigns.approve` | Reject campaign with reason |
| GET | `/api/v1/campaigns/{code}/approvals` | JWT | `campaigns.read` | Approval history |

> **Security invariants (from ADR-015):**
> - Every endpoint: negative behavioral test required before acceptance.
> - Campaign cannot reach `scheduled`/`active` without an approval record.
> - All campaign mutations produce outbox events in the same transaction.
> - Advertiser users see only their organization's campaigns (RLS).
> - Contact PII never exposed through campaign endpoints.
> - Placements target at surface level or above (store/cluster/branch);
>   resolved to concrete surface IDs at manifest generation time.
> - `storage_key` is opaque — presigned URLs generated at read time, never stored.

---

## 8. Inventory API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/inventory/availability` | JWT | `inventory.read` | Query free/busy/reserved |
| GET | `/api/v1/inventory/forecast` | JWT | `inventory.read` | Forecast impressions |
| POST | `/api/v1/inventory/reserve` | JWT | `inventory.reserve` | Reserve inventory |
| DELETE | `/api/v1/inventory/reservations/{id}` | JWT | `inventory.reserve` | Release reservation |
| GET | `/api/v1/inventory/rules` | JWT | `inventory.read` | List rules |
| POST | `/api/v1/inventory/rules` | JWT | `inventory.manage` | Create/update rule |

---

## 9. Content & Creatives API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| POST | `/api/v1/media/upload` | JWT | `media.upload` | Upload media asset |
| GET | `/api/v1/media` | JWT | `media.read` | List media (paginated) |
| GET | `/api/v1/media/{id}` | JWT | `media.read` | Media detail |
| GET | `/api/v1/media/{id}/preview` | JWT | `media.read` | Preview/thumbnail |
| POST | `/api/v1/media/{id}/versions` | JWT | `media.upload` | Upload new version |
| GET | `/api/v1/creatives/{id}/renditions` | JWT | `media.read` | List renditions for creative |
| POST | `/api/v1/creatives/{id}/renditions` | JWT | `media.upload` | Upload rendition |
| POST | `/api/v1/moderation/{id}/review` | JWT | `media.moderate` | Review creative/rendition |

---

## 10. Playlist & Manifest API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/playlists` | JWT | `playlists.read` | List playlists |
| POST | `/api/v1/playlists` | JWT | `playlists.manage` | Create playlist |
| GET | `/api/v1/playlists/{id}/versions` | JWT | `playlists.read` | List versions |
| POST | `/api/v1/playlists/{id}/publish` | JWT | `publications.publish` | Publish → generate manifests |
| GET | `/api/v1/manifests` | JWT | `manifests.read` | List manifests (paginated) |
| GET | `/api/v1/manifests/{id}` | JWT | `manifests.read` | Manifest detail |
| POST | `/api/v1/manifests/preview` | JWT | `manifests.read` | Dry-run manifest generation |

---

## 11. Approval API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/approvals` | JWT | `approvals.read` | List approval tasks (assigned) |
| POST | `/api/v1/approvals/{id}/decide` | JWT | `approvals.approve` | Approve/reject |
| GET | `/api/v1/approvals/{id}/history` | JWT | `approvals.read` | Approval history |

---

## 12. Emergency API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| POST | `/api/v1/emergency/stop` | JWT + MFA | `emergency.execute` | Stop all advertising |
| POST | `/api/v1/emergency/message` | JWT + MFA | `emergency.execute` | Replace with emergency message |
| POST | `/api/v1/emergency/resume` | JWT + MFA | `emergency.execute` | Resume normal play |
| GET | `/api/v1/emergency/status` | JWT | `emergency.read` | Emergency status |
| GET | `/api/v1/emergency/history` | JWT | `emergency.read` | Emergency command history |

---

## 13. Analytics API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/analytics/dashboard` | JWT | `analytics.read` | Network KPI dashboard |
| GET | `/api/v1/analytics/campaign/{code}` | JWT | `analytics.read` | Campaign analytics |
| GET | `/api/v1/analytics/store/{id}` | JWT | `analytics.read` | Store/device analytics |
| GET | `/api/v1/analytics/inventory` | JWT | `analytics.read` | Inventory occupancy report |
| GET | `/api/v1/analytics/sla` | JWT | `analytics.read` | SLA compliance report |
| POST | `/api/v1/analytics/export` | JWT | `analytics.export` | Export PDF/XLSX/CSV |
| GET | `/api/v1/analytics/advertiser/{code}/report` | JWT | `analytics.read` | Advertiser report (scoped) |

---

## 14. Audit API

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| GET | `/api/v1/audit/events` | JWT | `audit.read` | Query audit events (paginated) |

---

## 15. Device Gateway API (separate auth)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|------------|-------------|
| POST | `/device/v1/register` | device_code | — | Register device, get credentials |
| POST | `/device/v1/session` | device HMAC | — | Establish session, get JWT |
| POST | `/device/v1/session/refresh` | device JWT | — | Refresh JWT |
| GET | `/device/v1/manifest` | device JWT | — | Pull latest manifest for this device (ETag/304). Manifest may contain `display_surfaces[]` for multi-surface devices. |
| POST | `/device/v1/manifest/ack` | device JWT | — | Acknowledge manifest applied |
| POST | `/device/v1/heartbeat` | device JWT | — | Device heartbeat |
| POST | `/device/v1/pop/batch` | device JWT | — | Submit PoP batch |
| GET | `/device/v1/commands` | device JWT | — | Poll pending commands |
| POST | `/device/v1/commands/{id}/result` | device JWT | — | Report command execution |
| GET | `/device/v1/capabilities` | device JWT | — | Report device capabilities |

---

## Common Patterns

- **Authentication (Phase 3.2+):** All non-health endpoints require JWT `Authorization: Bearer` header. See ADR-006.
- **Pagination:** `?limit=20&offset=0` (allowed limit: 1–100)
- **Filtering:** `?status=active&channel_type=KSO&search=term`
- **Sorting:** `?sort_by=created_at&sort_order=desc`
- **Idempotency:** `Idempotency-Key: <uuid>` header for POST/PATCH
- **Versioning:** `/api/v1/`, `/device/v1/`
- **Error format:** `{"error": {"code": "CONFLICT", "message": "...", "details": {...}}}`
- **Correlation:** `X-Correlation-ID: <uuid>` propagated across services

## References

- TZ v2.5 Table 20 (API Groups)
- TZ v2.5 §16.1 (API Groups), §24.11 (API versioning)
- TZ v2.5 §21.5 (API-first contract development)
