#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────
# scripts/smoke/prepare-ui-smoke-stack.sh
# Idempotent smoke stack preparation — run before any UI-smoke test.
#
# 1. Configures MinIO CORS for browser presigned-URL upload.
# 2. Resets inventory capacity for clean smoke runs.
#
# Usage (from repo root):
#   bash scripts/smoke/prepare-ui-smoke-stack.sh
#
# Prerequisites:
#   - Docker compose stack is UP (postgres, minio, control-api)
#   - Admin-web vite dev server is running on :3000
# ────────────────────────────────────────────────────────────────────
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-infra/compose/docker-compose.phase1.yml}"
PG_USER="${PG_USER:-retail_media_owner}"
PG_DB="${PG_DB:-retail_media_platform}"
MINIO_ALIAS="local"

echo "=== [1/3] MinIO CORS ==="

# Configure MinIO CORS for browser presigned-URL upload.
# The presigned URL uses localhost:9000; admin-web runs on localhost:3000.
# Without CORS, the browser blocks the cross-origin PUT.
docker compose -f "$COMPOSE_FILE" exec -T minio \
  mc alias set "$MINIO_ALIAS" http://localhost:9000 minioadmin minioadmin 2>/dev/null || true

docker compose -f "$COMPOSE_FILE" exec -T minio \
  mc admin config set "$MINIO_ALIAS" api \
  cors_allow_origin='http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173' \
  >/dev/null 2>&1 || true

echo "  CORS configured for localhost:3000, localhost:5173"

echo "=== [2/3] Inventory Reset ==="

# Clear inventory bookings and reset slots to available.
# Idempotent — safe to run multiple times.
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$PG_USER" -d "$PG_DB" -q -c "
    DELETE FROM inventory_bookings;
    UPDATE inventory_slots SET status = 'available', reserved_capacity = 0, booked_capacity = 0;
  " >/dev/null 2>&1

# Verify
BOOKINGS=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM inventory_bookings;" 2>/dev/null | tr -d ' ')
AVAILABLE=$(docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U "$PG_USER" -d "$PG_DB" -t -c "SELECT count(*) FROM inventory_slots WHERE status='available';" 2>/dev/null | tr -d ' ')

echo "  Inventory: $BOOKINGS bookings, $AVAILABLE slots available"

echo "=== [3/3] Verification ==="

# Quick health check
curl -sf http://localhost:8000/health/live >/dev/null 2>&1 && echo "  control-api: OK" || echo "  control-api: MISSING"
curl -sf http://localhost:3000/login >/dev/null 2>&1 && echo "  admin-web: OK" || echo "  admin-web: MISSING"
curl -sf http://localhost:9000/minio/health/live >/dev/null 2>&1 && echo "  minio: OK" || echo "  minio: MISSING"

echo ""
echo "✓ Smoke stack ready. Run:"
echo "  UI_SMOKE_RUN=1 UI_SMOKE_ADMIN_URL=http://localhost:3000 python3 -m pytest tests/ui-smoke/test_uismoke__campaign__activate.py -v -s"
