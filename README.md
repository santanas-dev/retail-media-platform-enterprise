# Retail Media Platform — Enterprise Rewrite

Мультиканальная платформа управления рекламой на цифровых носителях розничной сети.

**Статус:** 🏗️ Phase 4.1a — Campaign Domain Architecture Lock (ADR-015).

## Architecture

- **Channel-agnostic core** — KSO is the first channel, not the foundation.
- **PostgreSQL** — operational data (FastAPI + SQLAlchemy async + Alembic).
- **ClickHouse** — аналитика и PoP-события *(deferred — Phase 4+)*.
- **NATS JetStream** — асинхронная шина между сервисами.
- **React 19 + TypeScript + Vite** — admin-web и advertiser-web.

Документация: `docs/architecture/`

## Quick Start — Clean Setup (Docker)

```bash
# 1. Start only PostgreSQL
docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres

# 2. Build the db-setup image (first time only)
docker compose -f infra/compose/docker-compose.phase1.yml build db-setup

# 3. Run migrations + seed (one-shot, profile-gated)
docker compose -f infra/compose/docker-compose.phase1.yml \
  --profile setup run --rm db-setup

# 4. Start all services
docker compose -f infra/compose/docker-compose.phase1.yml up -d

# 5. Verify
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

## Quick Start — Development (local Python)

```bash
# 1. Start PostgreSQL
docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres

# 2. Run migrations
bash scripts/db/migrate.sh

# 3. Seed dev data
bash scripts/db/seed.sh

# 4. Start control-api
python apps/control-api/main.py
```

## Database Setup

```bash
# Migrations only
bash scripts/db/migrate.sh

# Seed only (idempotent — safe to run repeatedly)
bash scripts/db/seed.sh

# Custom database URL
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db bash scripts/db/migrate.sh
```

## Behavioral Tests (real PostgreSQL)

End-to-end auth/RBAC tests against the real database.  Require a running
PostgreSQL with migrations and seed applied.

```bash
# 1. Start PostgreSQL
docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres

# 2. Run migrations + seed
bash scripts/db/migrate.sh && python3 apps/control-api/seed.py

# 3. Run behavioral tests
RUN_BEHAVIORAL_TESTS=1 python3 -m pytest tests/behavioral/ -v
```

These tests are opt-in (skip cleanly without `RUN_BEHAVIORAL_TESTS=1`) and are
**required** before accepting future auth, RBAC, or tenant-isolation changes
(per ADR-008).

## Local Checks

```bash
bash scripts/ci/phase1-checks.sh
```

## Legacy Reference

Исходный репозиторий: [retail-media-platform](https://github.com/santanas-dev/retail-media-platform)

Оригинальный репозиторий содержит первоначальную реализацию платформы (FastAPI backend,
Jinja2 portal, KSO-плеер). Он является **reference-only** — справочным материалом
для понимания предметной области и бизнес-логики. Код из него не копируется напрямую;
архитектурные решения пересматриваются и фиксируются в `docs/architecture/adr/`.

Подробнее: [docs/architecture/legacy-reference.md](docs/architecture/legacy-reference.md)

## License

Внутренний проект компании.
