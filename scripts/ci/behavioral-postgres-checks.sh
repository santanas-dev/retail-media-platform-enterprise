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

# Quick connectivity check + RLS safety audit
echo -n "  [db check] "
DB_CHECK_OUTPUT=$(python3 -c "
import asyncio, os, sys
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
url = os.environ.get('BEHAVIORAL_DB_URL', 'postgresql+asyncpg://retail_media:***@localhost:5432/retail_media_platform')
async def check():
    engine = create_async_engine(url, echo=False)
    async with engine.connect() as conn:
        await conn.execute(text('SELECT 1'))
        row = (await conn.execute(text(
            'SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user'
        ))).fetchone()
        if row:
            print(f'OK superuser={row[0]} bypassrls={row[1]}')
        else:
            print('OK role_unknown')
    await engine.dispose()
asyncio.run(check())
" 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$DB_CHECK_OUTPUT" ]; then
    echo -e "${GREEN}PASS${NC} ($DB_CHECK_OUTPUT)"
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

# Warn if running as superuser/BYPASSRLS (RLS policies not enforced at DB level)
if echo "$DB_CHECK_OUTPUT" | grep -qE 'superuser=True|bypassrls=True'; then
    echo ""
    echo -e "  ${YELLOW}WARNING: DB user has superuser/BYPASSRLS — RLS policies not enforced${NC}"
    echo "  Application-layer guards still tested, but PostgreSQL RLS bypassed."
    echo "  CI uses a non-BYPASSRLS app role. Local dev: this is expected."
    echo ""
fi

echo ""
echo "--- Behavioral Tests ---"

if [ ${#BEHAVIORAL_ARGS[@]} -eq 0 ]; then
    BEHAVIORAL_ARGS=("tests/behavioral/")
fi

pytest_output=$(python3 -m pytest "${BEHAVIORAL_ARGS[@]}" -v --tb=short 2>&1)
PYTEST_EXIT=$?
echo "$pytest_output"

# Guard: fail if zero tests passed (all skipped or zero collected)
if ! echo "$pytest_output" | grep -qE '[0-9]+ passed'; then
    echo ""
    echo -e "${RED}ERROR: No behavioral tests passed — all skipped or zero collected${NC}"
    exit 1
fi

if [ $PYTEST_EXIT -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== All behavioral tests passed ===${NC}"
else
    echo ""
    echo -e "${RED}=== Behavioral tests FAILED (exit $PYTEST_EXIT) ===${NC}"
fi

echo ""
echo "============================================"

exit $PYTEST_EXIT
