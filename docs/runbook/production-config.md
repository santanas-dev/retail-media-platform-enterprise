# Production Config Runbook

| **Created:** 2026-07-11
| **S-030:** Production CI gate + secrets validation

## Required Environment Variables

When `ENVIRONMENT=production`, these variables must be set with strong values:

| Variable | Min Length | Must NOT be |
|----------|-----------|-------------|
| `JWT_SECRET` | 32 chars | Missing, `CHANGE_ME`, weak words (secret, changeme, password, test, jwt_secret) |
| `MANIFEST_SIGNING_KEY` | 32 chars | Missing, weak words (signing_key, manifest_key, etc.) |
| `CORS_ALLOWED_ORIGINS` | — | Missing, wildcard `*`, localhost/127.0.0.1 |
| `MINIO_ACCESS_KEY` | — | `minioadmin` |
| `MINIO_SECRET_KEY` | — | `minioadmin` |
| `DATABASE_URL` | — | localhost/127.0.0.1 addresses, known dev passwords (retail_media_owner_pass, retail_media_app, postgres) |
| `SEED_DEV_CREDENTIALS` | — | Must NOT be `true`/`1`/`yes` |

## Example Production `.env`

```bash
ENVIRONMENT=production
JWT_SECRET=<generate: openssl rand -hex 32>
MANIFEST_SIGNING_KEY=<generate: openssl rand -hex 32>
CORS_ALLOWED_ORIGINS=https://portal.example.com,https://admin.example.com
MINIO_ACCESS_KEY=<strong-access-key>
MINIO_SECRET_KEY=<strong-secret-key>
DATABASE_URL=postgresql+asyncpg://rmp_user:<strong-password>@db-prod.internal:5432/rmp_prod
SEED_DEV_CREDENTIALS=false
```

## Local Validation

Run the production config gate tests:

```bash
ENVIRONMENT=production \
JWT_SECRET=<your-key> \
MANIFEST_SIGNING_KEY=<your-key> \
CORS_ALLOWED_ORIGINS=https://example.com \
DATABASE_URL=postgresql+asyncpg://user:pass@db.internal:5432/db \
python -m pytest tests/test_production_config_gate.py -v
```

Or validate a real prod config:

```bash
ENVIRONMENT=production \
JWT_SECRET=<your-prod-secret> \
MANIFEST_SIGNING_KEY=<your-prod-key> \
... \
python -c "
from packages.security.config import SecurityConfig
cfg = SecurityConfig()
print('Production config validated OK')
print(f'  JWT: *** ({len(cfg.jwt_secret)} chars)')
print(f'  CORS: {cfg.cors_allowed_origins}')
"
```

## CI

The `Production Config Gate — S-030` job runs on every push/PR. It sets `ENVIRONMENT=production` with CI-safe strong values and runs the 24 gate tests.

If this job fails:
1. Check which env var is missing or weak
2. Fix the production config
3. Re-run CI

## Dev/Preview

For dev and LAN preview, `ENVIRONMENT=dev` or `ENVIRONMENT` unset:
- All checks are relaxed
- JWT_SECRET defaults to `dev-secret-do-not-use-in-production`
- CORS accepts localhost
- MANIFEST_SIGNING_KEY can be empty
- MinIO can use minioadmin
- SEED_DEV_CREDENTIALS can be enabled
