# LDAPS Authentication Runbook — Retail Media Platform

| **Created:** 2026-07-13 |
| **Version:** 1.0 |
| **Service:** S-048 — Real LDAPS wiring |

## Architecture

Three auth providers coexist:

| Provider | Mode | User table required | Password check |
|----------|------|--------------------|----------------|
| `local_advertiser` | bcrypt local credentials | Yes | Local bcrypt hash |
| `local_break_glass` | bcrypt local credentials | Yes | Local bcrypt hash |
| `ad` | Real LDAPS bind + search | Yes (must exist locally) | AD LDAPS bind |

AD users MUST already exist in the `users` table with `auth_provider='ad'`
and `status='active'`.  No automatic provisioning from AD — this is a
conservative v0.6 baseline.  AD groups are not mapped to RMP roles yet.

## Required Environment Variables

```bash
# Enable AD auth
AD_ENABLED=true

# LDAPS server
AD_SERVER_URL=ldaps://dc.example.com:636
# or ldap://dc.example.com:389 for non-TLS (dev only)

# Directory structure
AD_BASE_DN=DC=example,DC=com
AD_USER_SEARCH_BASE=OU=Users,DC=example,DC=com
AD_USER_SEARCH_FILTER=(sAMAccountName={username})

# Service account (optional — anonymous bind if omitted)
AD_BIND_DN=CN=rmp-svc,OU=Service Accounts,DC=example,DC=com
AD_BIND_PASSWORD=***  # use secrets management, never commit

# TLS settings
AD_USE_TLS=true
AD_CERTIFICATE_VALIDATION=required  # required | optional | none
```

## Modes and Statuses

| Mode | Meaning | login behaviour |
|------|---------|-----------------|
| `disabled` | AD_ENABLED=false | AD login returns honest 503 |
| `misconfigured` | AD_ENABLED=true but no AD_SERVER_URL | AD login returns 503 |
| `configured` | Server reachable | Real LDAPS auth works |
| `unavailable` | Server not reachable | AD login returns 503 |

## How to Test Connection

Admin users with `users.manage` permission can use:

```
POST /api/v1/identity/auth/ad-settings/test
```

Returns:
- `status: "ok"` — server reachable, service bind works
- `status: "unavailable"` — server not reachable
- `status: "misconfigured"` — AD_ENABLED but no AD_SERVER_URL
- `status: "not_configured"` — AD_ENABLED=false

No password is sent in the test. Only service bind is attempted.

## Failure Modes

| Scenario | HTTP | error_code | User sees |
|----------|------|-----------|-----------|
| AD disabled | 503 | ad_disabled | "AD temporarily unavailable" |
| AD misconfigured | 503 | ad_misconfigured | "AD temporarily unavailable" |
| Server unreachable | 503 | ad_unavailable | "AD temporarily unavailable" |
| Bad credentials | 401 | AUTH_FAILED | "Invalid username or password" |
| AD user not found | 401 | AUTH_FAILED | "Invalid username or password" |
| User exists but inactive | 403 | USER_INACTIVE | "Account is deactivated" |
| User not provisioned locally | 401 | AUTH_FAILED | "Invalid username or password" |

**Security:** The client always sees the same generic message for
invalid credentials, unknown users, and AD errors.  No LDAP
diagnostic details are exposed to the client.

## Local Break-Glass

If AD is unavailable, administrators can still log in via
`local_break_glass` credentials.  These use local bcrypt hashes and
are seeded with `SEED_DEV_CREDENTIALS=true` in development.

## Production Checklist

Before enabling in production:

- [ ] AD server certificate is valid and trusted
- [ ] `AD_CERTIFICATE_VALIDATION=required`
- [ ] `AD_BIND_PASSWORD` is stored in secrets manager, not .env
- [ ] At least one `local_break_glass` admin account exists
- [ ] AD user accounts are created in RMP users table
- [ ] Test connection endpoint returns `ok`
- [ ] Production login tested with real AD credentials
- [ ] AD bind password is rotated periodically

## Logs

AD auth events are logged at INFO (success) / WARNING (unavailable) /
ERROR (unexpected).  Passwords and bind credentials are NEVER logged.

To check AD auth logs:
```bash
docker compose logs control-api | grep "rmp.ad"
```

## Verification

```bash
# Check AD settings
curl -s http://localhost:8000/api/v1/identity/auth/ad-settings \
  -H "Authorization: Bearer <admin-token>" | python3 -m json.tool

# Test AD connection
curl -s -X POST http://localhost:8000/api/v1/identity/auth/ad-settings/test \
  -H "Authorization: Bearer <admin-token>" | python3 -m json.tool

# Login via AD
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -c /tmp/cookies.txt \
  -d '{"username_or_email":"aduser","password":"...","auth_provider":"ad"}'
```
