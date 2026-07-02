#!/usr/bin/env bash
#
# Retail Media Platform — Run Dev Seed
#
# Seeds the database with idempotent dev/demo data.
# Safe to run multiple times (ON CONFLICT DO NOTHING).
#
# Usage:
#   # Local (with default dev DB)
#   bash scripts/db/seed.sh
#
#   # Local (with custom DB)
#   DATABASE_URL=postgresql+asyncpg://user:***@host:5432/db bash scripts/db/seed.sh
#
#   # Docker
#   docker compose -f infra/compose/docker-compose.phase1.yml \
#     exec control-api bash scripts/db/seed.sh
#
#   # Or use the profile-gated one-shot service:
#   docker compose -f infra/compose/docker-compose.phase1.yml \
#     --profile setup run --rm db-setup
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"

echo "==> Seeding database..."
echo "    Database: ${DATABASE_URL:-'(default dev)'}"

python3 apps/control-api/seed.py

echo "==> Seed complete."
