# Clean-Install Login — Dual Auth Readiness (S-016)

**Last updated:** 2026-07-10
**Applies to:** v0.1-admin-campaign-mvp and later

## Quick Start — Dev Environment

```bash
# 1. Start infrastructure
docker compose -f infra/compose/docker-compose.phase1.yml up -d

# 2. Apply migrations + seed
docker compose -f infra/compose/docker-compose.phase1.yml \
  --profile setup run --rm db-setup

# 3. Verify login
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username_or_email":"advertiser_test","password":"advertiser-dev-only","auth_provider":"local_advertiser"}'

# Expected: 200 + access_token + refresh cookie
```

## Seeded Users

Two users are seeded with local credentials when `ENVIRONMENT=dev` (or
`SEED_DEV_CREDENTIALS=***:

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
