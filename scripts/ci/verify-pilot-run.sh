#!/usr/bin/env bash
# =============================================================================
# IMAGE-REGISTRY-001 (SCOPE E) — clean pull/run proof for published pilot images.
#
# Spins up the pilot compose from a release lock (digest-only refs) on a clean
# runner, proves the published images actually run, then tears everything down.
#
# Known gap (documented, IMAGE-REGISTRY-001): the v0.11.1-pilot-packaging
# compose does not create the retail_media_app DB role (init-db.sql is dev-only,
# and pilot forbids source bind mounts). This script provisions the role
# manually so the run proof can proceed with the immutable release images.
# The proper fix (create-app-role.py) is staged for the next patch release.
#
# Usage:
#   verify-pilot-run.sh <lock.json> <release-tag> <release-sha>
# =============================================================================
set -euo pipefail

LOCK="${1:?usage: verify-pilot-run.sh <lock.json> <release-tag> <release-sha>}"
TAG="${2:?release tag}"
SHA="${3:?release sha}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE="infra/compose/docker-compose.pilot.yml"
PROJECT="rmp-verify-${GITHUB_RUN_ID:-$$}"
ENV_FILE="$(mktemp /tmp/rmp-verify-env.XXXXXX)"

cleanup() {
  echo "=== cleanup ==="
  docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f "$ENV_FILE"
}
trap cleanup EXIT

# --- extract digests from lock ----------------------------------------------
digest_of() {
  python3 - "$LOCK" "$1" <<'PY'
import json, sys
lock = json.load(open(sys.argv[1]))
for img in lock["images"]:
    if img["service"] == sys.argv[2]:
        print(img["image_digest"])
        sys.exit(0)
sys.exit(1)
PY
}

REGISTRY="ghcr.io/santanas-dev/retail-media-platform-enterprise"
CA_D=$(digest_of control-api)
DG_D=$(digest_of device-gateway)
OW_D=$(digest_of orchestrator-worker)
AW_D=$(digest_of admin-web)
AVW_D=$(digest_of advertiser-web)

# --- generate ephemeral secrets ---------------------------------------------
OWNER_USER="retail_media_owner"
OWNER_PW="$(openssl rand -hex 24)"
APP_USER="retail_media_app"
APP_PW="$(openssl rand -hex 24)"
JWT_SECRET="$(openssl rand -hex 32)"
MANIFEST_KEY="$(openssl rand -hex 32)"
METRICS_TOKEN="$(openssl rand -hex 32)"
MINIO_USER="$(openssl rand -hex 16)"
MINIO_PW="$(openssl rand -hex 24)"
MINIO_AK="$(openssl rand -hex 16)"
MINIO_SK="$(openssl rand -hex 24)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$ENV_FILE" <<EOF
ENVIRONMENT=dev
RMP_VERSION=${TAG}
RMP_GIT_SHA=${SHA}
RMP_BUILD_TIME=${BUILD_TIME}
RMP_SCHEMA_HEAD=034
POSTGRES_OWNER_USER=${OWNER_USER}
POSTGRES_OWNER_PASSWORD=${OWNER_PW}
POSTGRES_DB=retail_media_platform
DATABASE_URL=postgresql+asyncpg://${APP_USER}:${APP_PW}@postgres:5432/retail_media_platform
MIGRATION_DATABASE_URL=postgresql+asyncpg://${OWNER_USER}:${OWNER_PW}@postgres:5432/retail_media_platform
JWT_SECRET=${JWT_SECRET}
JWT_AUDIENCE=rmp-control-api
MANIFEST_SIGNING_KEY=${MANIFEST_KEY}
METRICS_AUTH_TOKEN=${METRICS_TOKEN}
MINIO_ROOT_USER=${MINIO_USER}
MINIO_ROOT_PASSWORD=${MINIO_PW}
MINIO_INTERNAL_ENDPOINT=minio:9000
MINIO_PUBLIC_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=${MINIO_AK}
MINIO_SECRET_KEY=${MINIO_SK}
CREATIVE_STORAGE_BUCKET=retail-media-creatives
CONTRACT_STORAGE_BUCKET=retail-media-contracts
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
CORS_ALLOW_CREDENTIALS=true
CONTROL_API_IMAGE=${REGISTRY}/control-api@${CA_D}
DEVICE_GATEWAY_IMAGE=${REGISTRY}/device-gateway@${DG_D}
ORCHESTRATOR_WORKER_IMAGE=${REGISTRY}/orchestrator-worker@${OW_D}
ADMIN_WEB_IMAGE=${REGISTRY}/admin-web@${AW_D}
ADVERTISER_WEB_IMAGE=${REGISTRY}/advertiser-web@${AVW_D}
EOF

echo "=== project: ${PROJECT} ==="
echo "=== compose uses @sha256 (not tags)? ==="
if grep -qE 'IMAGE=.*:[^@].*(v[0-9]|sha-|latest)' "$ENV_FILE"; then
  echo "FAIL: env has tag-based image refs"; exit 1
fi
grep -oE '@sha256:[0-9a-f]{64}' "$ENV_FILE" | wc -l | xargs echo "  digest refs:"

# --- start postgres + provision app role (known gap) ------------------------
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" up -d postgres
echo "waiting for postgres healthy..."
for i in $(seq 1 60); do
  status=$(docker inspect --format '{{.State.Health.Status}}' "${PROJECT}-postgres-1" 2>/dev/null || echo "missing")
  [[ "$status" == "healthy" ]] && break
  sleep 2
done
[[ "$status" == "healthy" ]] || { echo "FAIL: postgres not healthy (status=$status)"; exit 1; }

docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" exec -T postgres \
  psql -U "$OWNER_USER" -d retail_media_platform -v ON_ERROR_STOP=1 <<SQL
CREATE ROLE ${APP_USER} LOGIN PASSWORD '${APP_PW}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
GRANT CONNECT ON DATABASE retail_media_platform TO ${APP_USER};
GRANT USAGE ON SCHEMA public TO ${APP_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO ${APP_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO ${APP_USER};
SQL
echo "app role ${APP_USER} provisioned (NOBYPASSRLS)"

# --- start the full stack ---------------------------------------------------
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" up -d

echo "waiting for db-migrate to complete..."
for i in $(seq 1 120); do
  state=$(docker inspect --format '{{.State.Status}}' "${PROJECT}-db-migrate-1" 2>/dev/null || echo "missing")
  [[ "$state" == "exited" ]] && break
  sleep 2
done
DB_MIGRATE_EXIT=$(docker inspect --format '{{.State.ExitCode}}' "${PROJECT}-db-migrate-1" 2>/dev/null || echo "missing")
if [[ "$DB_MIGRATE_EXIT" != "0" ]]; then
  echo "FAIL: db-migrate exit code=${DB_MIGRATE_EXIT}"
  docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" logs db-migrate
  exit 1
fi
echo "db-migrate completed (exit 0)"

echo "waiting for services healthy..."
for i in $(seq 1 90); do
  unhealthy=$(docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" ps --format json 2>/dev/null \
    | python3 -c "import sys,json; [print(x['Name']) for x in (json.loads(l) for l in sys.stdin) if x.get('Health') not in ('healthy','')]" | wc -l)
  [[ "$unhealthy" -eq 0 ]] && break
  sleep 3
done

echo "=== service health ==="
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" ps

# --- verify version identity + build-info ----------------------------------
echo "=== control-api /version ==="
curl -fsS http://localhost:8000/version | python3 -m json.tool
curl -fsS http://localhost:8000/version | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('version')=='${TAG}', d; assert d.get('git_sha')=='${SHA}', d; print('control-api version OK')"

echo "=== device-gateway /version ==="
curl -fsS http://localhost:8001/version | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('git_sha')=='${SHA}', d; print('device-gateway version OK')"

echo "=== admin-web /build-info.json ==="
curl -fsS http://localhost:3000/build-info.json | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('version')=='${TAG}', d; assert d.get('git_sha')=='${SHA}', d; print('admin-web build-info OK')"

echo "=== advertiser-web /build-info.json ==="
curl -fsS http://localhost:3001/build-info.json | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('version')=='${TAG}', d; assert d.get('git_sha')=='${SHA}', d; print('advertiser-web build-info OK')"

# --- verify NOBYPASSRLS ----------------------------------------------------
echo "=== NOBYPASSRLS check ==="
docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" exec -T postgres \
  psql -U "$OWNER_USER" -d retail_media_platform -tAc \
  "SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname='${APP_USER}'"
BYPASS=$(docker compose -p "$PROJECT" -f "$COMPOSE" --env-file "$ENV_FILE" exec -T postgres \
  psql -U "$OWNER_USER" -d retail_media_platform -tAc \
  "SELECT rolbypassrls FROM pg_roles WHERE rolname='${APP_USER}'" | tr -d '[:space:]')
[[ "$BYPASS" == "f" || "$BYPASS" == "false" ]] || { echo "FAIL: app role has BYPASSRLS ($BYPASS)"; exit 1; }
echo "NOBYPASSRLS confirmed (rolbypassrls=$BYPASS)"

echo ""
echo "=== VERIFY-PILOT-RUN PASSED ==="
