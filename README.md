# Retail Media Platform — Enterprise Rewrite

Мультиканальная платформа управления рекламой на цифровых носителях розничной сети.

**Статус:** 🏗️ Phase 2 — Enterprise Foundation (идентичность, RBAC, RLS, аудит).

## Architecture

- **Channel-agnostic core** — KSO is the first channel, not the foundation.
- **PostgreSQL** — operational data (FastAPI + SQLAlchemy async + Alembic).
- **ClickHouse** — аналитика и PoP-события.
- **NATS JetStream** — асинхронная шина между сервисами.
- **React 19 + TypeScript + Vite** — admin-web и advertiser-web.

Документация: `docs/architecture/`

## Quick Start — Clean Setup (Docker)

```bash
# 1. Start only PostgreSQL
docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres

# 2. Run migrations + seed (one-shot, profile-gated)
docker compose -f infra/compose/docker-compose.phase1.yml \
  --profile setup run --rm db-setup

# 3. Start all services
docker compose -f infra/compose/docker-compose.phase1.yml up -d

# 4. Verify
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
