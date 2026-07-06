#!/usr/bin/env bash
#
# Behavioral PostgreSQL Tests — Local Runner
#
# Runs the behavioral test suite against a real PostgreSQL instance.
# Requires migrations and seed applied beforehand.
#
# Usage:
#   # With default local DB (migrations + seed must be done separately)
#   bash scripts/ci/behavioral-postgres-checks.sh
#
#   # With custom DB
#   BEHAVIORAL_DB_URL=postgresql+asyncpg://user:***@host:5432/db \
#     bash scripts/ci/behavioral-postgres-checks.sh
#
#   # With setup (migrations + seed)
#   bash scripts/ci/behavioral-postgres-checks.sh --setup
#
# Prerequisites:
#   - PostgreSQL 16 running
#   - python3 (3.11+)
#   - pip deps: sqlalchemy, alembic, asyncpg, pytest, httpx, bcrypt, PyJWT, greenlet, psycopg2-binary
#
# Environment variables:
#   RUN_BEHAVIORAL_TESTS        Set to "1" (auto-set if not present)
#   BEHAVIORAL_DB_URL           Async DB URL (default: localhost dev)
#   DATABASE_URL                Sync DB URL for migrations (needed with --setup)
#
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

DO_SETUP=false
BEHAVIORAL_ARGS=()

for arg in "$@"; do
    case "$arg" in
        --setup)
            DO_SETUP=true
            ;;
        *)
            BEHAVIORAL_ARGS+=("$arg")
            ;;
    esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

if [ -z "${RUN_BEHAVIORAL_TESTS:-}" ]; then
    echo "==> RUN_BEHAVIORAL_TESTS not set — forcing to 1"
    export RUN_BEHAVIORAL_TESTS=1
fi

if [ -z "${JWT_SECRET:-}" ]; then
    export JWT_SECRET="behavioral-test-secret-at-least-32-chars"
fi

if [ -z "${ENVIRONMENT:-}" ]; then
    export ENVIRONMENT="dev"
fi

# ---------------------------------------------------------------------------
# Setup (optional)
# ---------------------------------------------------------------------------

if [ "$DO_SETUP" = true ]; then
    echo "--- Setup: Migrations ---"
    echo "    DATABASE_URL: ${DATABASE_URL:-default dev}"

    cd apps/control-api
    alembic upgrade head
    cd "$REPO_ROOT"

    echo ""
    echo "--- Setup: Seed ---"
    python3 apps/control-api/seed.py
    echo ""
fi

# ---------------------------------------------------------------------------
# Behavioral Tests
# ---------------------------------------------------------------------------

echo "============================================"
echo " Behavioral PostgreSQL Tests"
echo "============================================"
echo ""
echo "  DB: ${BEHAVIORAL_DB_URL:-postgresql+asyncpg://...localhost:5432/retail_media_platform}"
echo "  RUN_BEHAVIORAL_TESTS: $RUN_BEHAVIORAL_TESTS"
echo ""

# Quick connectivity check
echo -n "  [db check] "
if python3 -c "
import asyncio, os
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
url = os.environ.get('BEHAVIORAL_DB_URL', 'postgresql+asyncpg://retail_media:***@localhost:5432/retail_media_platform')
async def check():
    engine = create_async_engine(url, echo=False)
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))
    await engine.dispose()
asyncio.run(check())
print('OK')
" 2>/dev/null; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL — PostgreSQL not reachable${NC}"
    echo ""
    echo "  Start PostgreSQL first:"
    echo "    docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres"
    echo "    bash scripts/db/migrate.sh"
    echo "    python3 apps/control-api/seed.py"
    echo ""
    exit 1
fi

echo ""
echo "--- Behavioral Tests ---"

if [ ${#BEHAVIORAL_ARGS[@]} -eq 0 ]; then
    BEHAVIORAL_ARGS=("tests/behavioral/")
fi

FAIL=0
if python3 -m pytest "${BEHAVIORAL_ARGS[@]}" -v 2>&1; then
    echo ""
    echo -e "${GREEN}=== All behavioral tests passed ===${NC}"
else
    FAIL=$?
    echo ""
    echo -e "${RED}=== Behavioral tests FAILED (exit $FAIL) ===${NC}"
fi

echo ""
echo "============================================"

exit $FAIL
