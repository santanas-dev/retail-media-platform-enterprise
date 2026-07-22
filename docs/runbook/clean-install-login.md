# Clean-Install Login — Dual Auth Readiness (S-016)

**Last updated:** 2026-07-22 (CLEAN-BOOT-002 — db-setup image sharing fix, all 28 migrations to head)

> **CLEAN-BOOT-002 (2026-07-22):** db-setup now shares the control-api Docker image
> (`image: rmp-phase1-control-api`). Previously db-setup had its own cached image
> that didn't include migrations 025-028. The fix: `docker-compose.phase1.yml`
> db-setup service now references the shared image. No commands changed.

## Quick Start — Dev Environment

```bash
# 1. Start infrastructure (postgres + redis + control-api)
docker compose \
  -f infra/compose/docker-compose.phase1.yml \
  -f infra/compose/docker-compose.preview.yml \
  up -d --build postgres redis control-api

# 2. Apply migrations + seed + grant app role (uses preview.yml for SEED_DEV_CREDENTIALS)
docker compose \
  -f infra/compose/docker-compose.phase1.yml \
  -f infra/compose/docker-compose.preview.yml \
  --profile setup run --rm db-setup

# 3. Verify login
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username_or_email":"advertiser_test","password":"advertiser-dev-only","auth_provider":"local_advertiser"}'

# Expected: 200 + access_token + refresh cookie
```

## Seeded Users

Two users are seeded with local credentials when `ENVIRONMENT=dev` (or
SEED_DEV_CREDENTIALS=true

| Username | Password (DEV ONLY) | auth_provider | Role | must_change_password |
|----------|--------------------|---------------|------|---------------------|
| `advertiser_test` | `advertiser-dev-only` | `local_advertiser` | advertiser (system_admin for test) | true |
| `break_glass_admin` | `break-glass-dev-only` | `local_break_glass` | system_admin | true |

## Auth Providers

Three provider types available on the login page:

| Provider | Status | Use case |
|----------|--------|----------|
| **Рекламодатель** (`local_advertiser`) | ✅ Works | Advertisers / agencies — production product path |
| **Break-glass Admin** (`local_break_glass`) | ✅ Works | Emergency bootstrap / AD outage |
| **Сотрудник / AD** (`ad`) | 🟡 Stub (503) | Internal staff — LDAPS not yet wired |

**AD returns honest 503** — this is correct behaviour per ADR-006 §2.8.
The LDAPS interface is defined (ADR-006) and the auth pipeline is ready,
but a real AD controller has not been provisioned.

## Production Deployment

### DB roles (S-019)

Runtime services (control-api, device-gateway, orchestrator-worker) connect
as `retail_media_app` — a **NOBYPASSRLS**, non-superuser role.  This ensures
PostgreSQL RLS policies (ADR-009, S-008) are enforced at the DB level as a
second defence layer.

Migrations and seed use `retail_media_owner` (DDL-capable).  The roles are
created by `infra/compose/init-db.sql` and granted table access by
`infra/compose/grant-app-role.py` during db-setup.

### Local credentials

In production (`ENVIRONMENT != dev`), the seed script **skips**
local_credentials by default and logs a clear warning:

```
WARNING: Skipping local_credentials seed — ENVIRONMENT is not dev,
SEED_DEV_CREDENTIALS is not true. No users will be able to log in
via local auth.
```

To enable dev credentials in any environment:

```bash
SEED_DEV_CREDENTIALS=true python apps/control-api/seed.py
```

For production, credentials should be provisioned via an external
secrets manager or environment-injected password hashes (future
`LOCAL_CREDENTIALS_OVERRIDE` mechanism).

## Verifying /me

After login, `/me` returns DB-backed truthful data:

```bash
TOKEN="<access_token from login>"
curl -s http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

Response includes:
- `username` — from DB, not JWT claims
- `display_name` — from DB
- `permissions` — sorted list from role_permissions
- `must_change_password` — true if credential was seeded

## admin-web Login

1. Open `http://localhost:3000`
2. Select provider: **Рекламодатель** (default) or **Break-glass Admin**
3. Enter username and password
4. If selecting **Сотрудник / AD** — "AD/LDAPS temporarily unavailable" message

## Troubleshooting

**"No users will be able to log in via local auth"** — set `ENVIRONMENT=dev` or `SEED_DEV_CREDENTIALS=true`

**Login returns 503 for AD** — expected. AD stub is active. Use local_advertiser or local_break_glass.

**Login returns 401 for seeded user** — re-run `db-setup` to apply seed with credentials.
