# Behavioral test suite - shared fixtures (Phase 3.4)
#
# These tests require a running PostgreSQL with the full schema applied.
# Set the environment variable RUN_BEHAVIORAL_TESTS=1 to enable them.
# Without it, every test is skipped with a clear reason.
#
# Quick setup:
#   docker compose -f infra/compose/docker-compose.phase1.yml up -d postgres
#   bash scripts/db/migrate.sh
#   python3 apps/control-api/seed.py
#   RUN_BEHAVIORAL_TESTS=1 python3 -m pytest tests/behavioral/ -v
