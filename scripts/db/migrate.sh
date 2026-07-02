#!/usr/bin/env bash
#
# Retail Media Platform — Run Alembic Migrations
#
# Applies all pending migrations to the database.
# Uses DATABASE_URL from environment, or the default dev URL.
#
# Usage:
#   # Local (with default dev DB)
#   bash scripts/db/migrate.sh
#
#   # Local (with custom DB)
#   DATABASE_URL=postgresql://user:pass@host:5432/db bash scripts/db/migrate.sh
#
#   # Docker
#   docker compose -f infra/compose/docker-compose.phase1.yml \
#     exec control-api bash scripts/db/migrate.sh
#
#   # Or use the profile-gated one-shot service:
#   docker compose -f infra/compose/docker-compose.phase1.yml \
#     --profile setup run --rm db-setup
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ALEMBIC_DIR="$REPO_ROOT/apps/control-api"

cd "$ALEMBIC_DIR"

echo "==> Running Alembic migrations..."
echo "    Config: alembic.ini"
echo "    Database: ${DATABASE_URL:-'(default dev)'}"

alembic upgrade head

echo "==> Migrations complete."
