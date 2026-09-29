#!/usr/bin/env bash
# =============================================================================
# Pilot run proof under ENVIRONMENT=pilot (IMAGE-REGISTRY-001 SCOPE E, RF-05).
#
# Brings up infra/compose/docker-compose.pilot.yml from the given images with
# ephemeral secrets, exactly as a pilot host would (no manual DB steps), and
# fails on the first thing that is not true:
#   - db-migrate exits 0 and itself creates retail_media_app (NOSUPERUSER, NOBYPASSRLS);
#   - every service becomes healthy within the timeout (compose --wait);
#   - control-api readiness is green with its strict DB-role check;
#   - the build identity baked into the backend images matches the expected
#     release, and /version + /build-info.json report it;
#   - a device token issued by control-api is accepted by device-gateway;
#   - orchestrator-worker loads the shared security config (manifest path).
#
# Usage:
#   verify-pilot-run.sh <lock.json> <release-tag> <release-sha>
#       published release: digest-only refs resolved from the lock
#       (workflow verify-pilot-images.yml);
#   verify-pilot-run.sh --images-from-env <version> <git-sha>
#       images already present locally, refs in CONTROL_API_IMAGE,
#       DEVICE_GATEWAY_IMAGE, ORCHESTRATOR_WORKER_IMAGE, ADMIN_WEB_IMAGE,
#       ADVERTISER_WEB_IMAGE (CI job "Pilot compose smoke", built from the commit).
# Optional env: WAIT_TIMEOUT (seconds, default 300).
# Secrets are generated per run into a temp env file that is removed on exit.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

USAGE="usage: verify-pilot-run.sh <lock.json> <release-tag> <release-sha> | --images-from-env <version> <git-sha>"
if [[ "${1:-}" == "--images-from-env" ]]; then
  EXPECT_VERSION="${2:?$USAGE}"
  EXPECT_SHA="${3:?$USAGE}"
  : "${CONTROL_API_IMAGE:?}" "${DEVICE_GATEWAY_IMAGE:?}" "${ORCHESTRATOR_WORKER_IMAGE:?}"
  : "${ADMIN_WEB_IMAGE:?}" "${ADVERTISER_WEB_IMAGE:?}"
  # Images built from this checkout expect this checkout's schema head.
  SCHEMA_HEAD="$(python3 scripts/deploy/alembic_head.py)"
else
  LOCK="${1:?$USAGE}"
  EXPECT_VERSION="${2:?release tag}"
  EXPECT_SHA="${3:?release sha}"

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

  REGISTRY="ghcr.io/santanas-dev/rmp-pilot"
  CONTROL_API_IMAGE="${REGISTRY}/control-api@$(digest_of control-api)"
  DEVICE_GATEWAY_IMAGE="${REGISTRY}/device-gateway@$(digest_of device-gateway)"
  ORCHESTRATOR_WORKER_IMAGE="${REGISTRY}/orchestrator-worker@$(digest_of orchestrator-worker)"
  ADMIN_WEB_IMAGE="${REGISTRY}/admin-web@$(digest_of admin-web)"
  ADVERTISER_WEB_IMAGE="${REGISTRY}/advertiser-web@$(digest_of advertiser-web)"

  echo "=== image refs are digests (not tags)? ==="
  for ref in "$CONTROL_API_IMAGE" "$DEVICE_GATEWAY_IMAGE" "$ORCHESTRATOR_WORKER_IMAGE" \
             "$ADMIN_WEB_IMAGE" "$ADVERTISER_WEB_IMAGE"; do
    [[ "$ref" =~ @sha256:[0-9a-f]{64}$ ]] || { echo "FAIL: not a digest ref: $ref"; exit 1; }
  done
  echo "  digest refs: 5"
  # A release expects its own schema head, not this checkout's: the lock's
  # release.schema_head when recorded (build-images.sh --push), otherwise the
  # head resolved from the migration files at the release commit
  # (generate_release_lock.py does not record it).
  SCHEMA_HEAD="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('release', {}).get('schema_head') or '')" "$LOCK")"
  if [[ -z "$SCHEMA_HEAD" ]]; then
    git cat-file -e "${EXPECT_SHA}^{commit}" 2>/dev/null \
      || git fetch --quiet --depth 1 origin "$EXPECT_SHA" \
      || { echo "FAIL: release commit ${EXPECT_SHA} is not fetchable"; exit 1; }
    VERSIONS_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rmp-verify-versions.XXXXXX")"
    git archive "$EXPECT_SHA" apps/control-api/alembic/versions | tar -x -C "$VERSIONS_DIR"
    SCHEMA_HEAD="$(python3 scripts/deploy/alembic_head.py --versions-dir "$VERSIONS_DIR/apps/control-api/alembic/versions")"
    rm -rf "$VERSIONS_DIR"
    echo "  schema head at release commit: ${SCHEMA_HEAD}"
  fi
  [[ -n "$SCHEMA_HEAD" ]] || { echo "FAIL: no schema head for release ${EXPECT_SHA}"; exit 1; }
fi

COMPOSE_FILE="infra/compose/docker-compose.pilot.yml"
PROJECT="rmp-verify-${GITHUB_RUN_ID:-$$}"
WAIT_TIMEOUT="${WAIT_TIMEOUT:-300}"
ENV_FILE="$(mktemp "${TMPDIR:-/tmp}/rmp-verify-env.XXXXXX")"

dc() { docker compose -p "$PROJECT" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" "$@"; }

cleanup() {
  local rc=$?
  if [[ $rc -ne 0 ]]; then
    echo "=== FAILED (rc=$rc) — service state and logs ==="
    dc ps -a || true
    dc logs --no-color --tail 80 || true
  fi
  echo "=== cleanup ==="
  dc down -v --remove-orphans >/dev/null 2>&1 || true
  rm -f "$ENV_FILE"
}
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }

# --- build identity must come from the images --------------------------------
image_env() {  # image var -> value of that ENV baked into the image ("" if absent)
  docker image inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$1" \
    | sed -n "s/^$2=//p"
}
BUILD_TIME=""
for ref in "$CONTROL_API_IMAGE" "$DEVICE_GATEWAY_IMAGE" "$ORCHESTRATOR_WORKER_IMAGE"; do
  v="$(image_env "$ref" RMP_VERSION)"; s="$(image_env "$ref" RMP_GIT_SHA)"; t="$(image_env "$ref" RMP_BUILD_TIME)"
  [[ "$v" == "$EXPECT_VERSION" ]] || fail "$ref carries RMP_VERSION='$v', expected '$EXPECT_VERSION'"
  [[ "$s" == "$EXPECT_SHA" ]] || fail "$ref carries RMP_GIT_SHA='$s', expected '$EXPECT_SHA'"
  [[ -n "$t" ]] || fail "$ref carries no RMP_BUILD_TIME"
  BUILD_TIME="$t"
done
echo "image identity: version=$EXPECT_VERSION git_sha=$EXPECT_SHA"

# --- ephemeral pilot env (never written anywhere but the temp file) ----------
OWNER_USER="retail_media_owner"
OWNER_PW="$(openssl rand -hex 24)"
APP_USER="retail_media_app"
APP_PW="$(openssl rand -hex 24)"
DB="retail_media_platform"
cat > "$ENV_FILE" <<EOF
ENVIRONMENT=pilot
RMP_VERSION=${EXPECT_VERSION}
RMP_GIT_SHA=${EXPECT_SHA}
RMP_BUILD_TIME=${BUILD_TIME}
RMP_SCHEMA_HEAD=${SCHEMA_HEAD}
POSTGRES_OWNER_USER=${OWNER_USER}
POSTGRES_OWNER_PASSWORD=${OWNER_PW}
POSTGRES_APP_USER=${APP_USER}
POSTGRES_APP_PASSWORD=${APP_PW}
POSTGRES_DB=${DB}
DATABASE_URL=postgresql+asyncpg://${APP_USER}:${APP_PW}@postgres:5432/${DB}
MIGRATION_DATABASE_URL=postgresql+asyncpg://${OWNER_USER}:${OWNER_PW}@postgres:5432/${DB}
JWT_SECRET=$(openssl rand -hex 32)
JWT_AUDIENCE=rmp-control-api
MANIFEST_SIGNING_KEY=$(openssl rand -hex 32)
METRICS_AUTH_TOKEN=$(openssl rand -hex 32)
MINIO_ROOT_USER=$(openssl rand -hex 16)
MINIO_ROOT_PASSWORD=$(openssl rand -hex 24)
MINIO_INTERNAL_ENDPOINT=minio:9000
MINIO_PUBLIC_ENDPOINT=media.pilot-proof.invalid
MINIO_ACCESS_KEY=$(openssl rand -hex 16)
MINIO_SECRET_KEY=$(openssl rand -hex 24)
CREATIVE_STORAGE_BUCKET=retail-media-creatives
CONTRACT_STORAGE_BUCKET=retail-media-contracts
CORS_ALLOWED_ORIGINS=https://admin.pilot-proof.invalid,https://ads.pilot-proof.invalid
CORS_ALLOW_CREDENTIALS=true
CONTROL_API_IMAGE=${CONTROL_API_IMAGE}
DEVICE_GATEWAY_IMAGE=${DEVICE_GATEWAY_IMAGE}
ORCHESTRATOR_WORKER_IMAGE=${ORCHESTRATOR_WORKER_IMAGE}
ADMIN_WEB_IMAGE=${ADMIN_WEB_IMAGE}
ADVERTISER_WEB_IMAGE=${ADVERTISER_WEB_IMAGE}
EOF

# --- bring the stack up: no manual DB step, bounded state-based wait ---------
echo "=== project: ${PROJECT} (ENVIRONMENT=pilot, wait ≤ ${WAIT_TIMEOUT}s) ==="
set +e
dc up -d --wait --wait-timeout "$WAIT_TIMEOUT"
UP_RC=$?
set -e
MIGRATE_ID="$(dc ps -a -q db-migrate)"
[[ -n "$MIGRATE_ID" ]] || fail "db-migrate container was never created (compose rc=${UP_RC})"
MIGRATE_EXIT="$(docker inspect --format '{{.State.ExitCode}}' "$MIGRATE_ID")"
[[ "$MIGRATE_EXIT" == "0" ]] || fail "db-migrate exit code=${MIGRATE_EXIT}"
[[ $UP_RC -eq 0 ]] || fail "stack did not become healthy within ${WAIT_TIMEOUT}s (compose rc=${UP_RC})"
dc ps

# --- app role: created by the compose itself ---------------------------------
ROLE="$(dc exec -T postgres psql -U "$OWNER_USER" -d "$DB" -tAc \
  "SELECT rolcanlogin::text || ',' || rolsuper::text || ',' || rolbypassrls::text FROM pg_roles WHERE rolname='${APP_USER}'" | tr -d '[:space:]')"
[[ "$ROLE" == "true,false,false" ]] || fail "app role (login,super,bypassrls)='${ROLE}', expected true,false,false"
echo "app role ${APP_USER}: LOGIN NOSUPERUSER NOBYPASSRLS (created by db-migrate)"

# --- readiness (strict DB-role check outside dev) ----------------------------
curl -fsS http://localhost:8000/health/ready | python3 -c "
import sys, json; d = json.load(sys.stdin)
assert d['status'] == 'ok', d
print('control-api ready:', d['checks'])"

# --- version identity --------------------------------------------------------
for spec in control-api:8000 device-gateway:8001; do
  curl -fsS "http://localhost:${spec##*:}/version" | python3 -c "
import sys, json; d = json.load(sys.stdin)
assert d.get('version') == '${EXPECT_VERSION}' and d.get('git_sha') == '${EXPECT_SHA}', d
assert d.get('environment') == 'pilot', d
print('${spec%%:*} /version OK')"
done
for port in 3000 3001; do
  curl -fsS "http://localhost:${port}/build-info.json" | python3 -c "
import sys, json; d = json.load(sys.stdin)
assert d.get('version') == '${EXPECT_VERSION}' and d.get('git_sha') == '${EXPECT_SHA}', d
print(':${port} /build-info.json OK')"
done

# --- device token: issued by control-api, accepted by device-gateway ---------
DEVICE_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
TOKEN="$(dc exec -T control-api python -c \
  "from packages.security.jwt import create_access_token; print(create_access_token('${DEVICE_ID}', 'device'))" | tr -d '\r')"
BODY="$(mktemp)"
STATUS="$(curl -sS -o "$BODY" -w '%{http_code}' -H "Authorization: Bearer ${TOKEN}" \
  http://localhost:8001/api/v1/device/manifest/latest)"
# Exactly 404 "Device not found": the token verified (401 = audience/secret
# mismatch) AND the device lookup ran under retail_media_app with RLS bootstrap
# (a missing grant or broken policy would be a 5xx, not 404).
if [[ "$STATUS" != "404" ]] || ! grep -q '"Device not found"' "$BODY"; then
  cat "$BODY"; rm -f "$BODY"
  fail "device-gateway answered HTTP ${STATUS} to a control-api device token for an unregistered device (expected 404 Device not found)"
fi
echo "device-gateway accepted the control-api device token (404 Device not found for an unregistered device)"
rm -f "$BODY"

# --- orchestrator-worker: the config manifest generation loads ---------------
dc exec -T orchestrator-worker python -c \
  "from packages.security.config import get_security_config; c = get_security_config(); assert not c.dev_mode; print('orchestrator-worker security config OK')"

echo ""
echo "=== VERIFY-PILOT-RUN PASSED ==="
