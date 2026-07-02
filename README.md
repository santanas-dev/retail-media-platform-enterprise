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

## Quick Start

```bash
# 1. Infrastructure
docker compose -f infra/compose/docker-compose.phase1.yml up -d

# 2. Migrations
docker compose -f infra/compose/docker-compose.phase1.yml exec control-api \
  alembic -c apps/control-api/alembic.ini upgrade head

# 3. Seed dev data
docker compose -f infra/compose/docker-compose.phase1.yml exec control-api \
  python apps/control-api/seed.py

# 4. Health check
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
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
