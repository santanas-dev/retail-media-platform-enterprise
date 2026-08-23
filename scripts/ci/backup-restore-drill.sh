#!/usr/bin/env bash
# Isolated backup + restore drill (PILOT-DEPLOYMENT-READINESS-001C, SCOPE H).
#
# Proves a real PostgreSQL + MinIO backup/restore cycle into a fully isolated
# disposable target, then runs the behavioral verification suite and the
# negative matrix.
#
# Run from repo root. Requires docker compose + psql.
# Synthetic (test-only) secrets — no production values.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_FILE="infra/compose/docker-compose.restore-drill.yml"
PROJECT="rmp-restore-drill"

# Synthetic test-only secrets (never production values).
SRC_OWNER_PW="drill_src_owner_pw_0123456789"
TGT_OWNER_PW="drill_tgt_owner_pw_0123456789"
MINIO_ROOT_USER_SRC="drill_src_minio_admin"
MINIO_ROOT_PW_SRC="drill_src_minio_pw_0123456789"
MINIO_ROOT_USER_TGT="drill_tgt_minio_admin"
MINIO_ROOT_PW_TGT="drill_tgt_minio_pw_0123456789"
APP_ROLE_PW="drill_app_role_pw_0123456789"

GIT_SHA="$(git rev-parse HEAD)"
VERSION="001C-drill"

BACKUP_ROOT="$(mktemp -d)/backups"
mkdir -p "$BACKUP_ROOT"
echo "backup root: $BACKUP_ROOT"

# ── helpers ────────────────────────────────────────────────────────────────
wait_healthy() {
  local svc="$1"; local tries="${2:-60}"
  for i in $(seq 1 "$tries"); do
    st="$(docker inspect -f '{{.State.Health.Status}}' "${PROJECT}-${svc}-1" 2>/dev/null || echo missing)"
    if [ "$st" = "healthy" ]; then echo "  $svc healthy"; return 0; fi
    sleep 2
  done
  echo "::error::$svc did not become healthy" >&2
  exit 1
}

cleanup() {
  echo "=== cleanup (exact project name only — no wildcard) ==="
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" down -v --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$(dirname "$BACKUP_ROOT")" 2>/dev/null || true
}
trap cleanup EXIT

# ── 1. bring up source + target contours ───────────────────────────────────
echo "=== 1. up (source + target) ==="
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up -d
wait_healthy src-postgres
wait_healthy src-minio
wait_healthy tgt-postgres
wait_healthy tgt-minio

# ── 2. migrate + seed source ───────────────────────────────────────────────
echo "=== 2. migrate source ==="
export DATABASE_URL="postgresql+asyncpg://retail_media_owner:${SRC_OWNER_PW}@127.0.0.1:15432/retail_media_platform"
pushd apps/control-api >/dev/null
alembic upgrade head
popd >/dev/null

echo "=== 3. seed source (dev baseline + representative dataset) ==="
python3 apps/control-api/seed.py

export DATABASE_URL="postgresql://retail_media_owner:${SRC_OWNER_PW}@127.0.0.1:15432/retail_media_platform"
export MINIO_ENDPOINT="127.0.0.1:19000"
export MINIO_ACCESS_KEY="${MINIO_ROOT_USER_SRC}"
export MINIO_SECRET_KEY="${MINIO_ROOT_PW_SRC}"
export CREATIVE_STORAGE_BUCKET="drill-creatives"
export CONTRACT_STORAGE_BUCKET="drill-contracts"
python3 scripts/backup/seed_representative_data.py

# ── 4. quiesced backup (source) ────────────────────────────────────────────
echo "=== 4. quiesced backup ==="
export PGHOST=127.0.0.1
export PGPORT=15432
export PGUSER=retail_media_owner
export PGPASSWORD="${SRC_OWNER_PW}"
export PGDATABASE=retail_media_platform
export MINIO_ENDPOINT="127.0.0.1:19000"
export MINIO_ACCESS_KEY="${MINIO_ROOT_USER_SRC}"
export MINIO_SECRET_KEY="${MINIO_ROOT_PW_SRC}"
export MINIO_BUCKETS="drill-creatives,drill-contracts"
export MINIO_SERVER_VERSION="RELEASE.2024-11-07T00-52-20Z"
export BACKUP_ROOT

python3 scripts/backup/quiesced_backup.py \
  --backup-root "$BACKUP_ROOT" \
  --git-sha "$GIT_SHA" \
  --version "$VERSION" \
  --environment drill \
  --quiesce-mode writers-stopped \
  --quiesce-evidence "CI drill: source contour runs no app writers (provisioned, migrated, seeded, then quiesced-by-construction)"

# ── 5. isolated restore into target ────────────────────────────────────────
echo "=== 5. isolated restore (target) ==="
export PGHOST=127.0.0.1
export PGPORT=15433
export PGUSER=retail_media_owner
export PGPASSWORD="${TGT_OWNER_PW}"
export PGDATABASE=retail_media_platform
export DATABASE_URL="postgresql://retail_media_owner:${TGT_OWNER_PW}@127.0.0.1:15433/retail_media_platform"
export MINIO_ENDPOINT="127.0.0.1:19001"
export MINIO_ACCESS_KEY="${MINIO_ROOT_USER_TGT}"
export MINIO_SECRET_KEY="${MINIO_ROOT_PW_TGT}"
export SOURCE_DATABASE_URL="postgresql://retail_media_owner:${SRC_OWNER_PW}@127.0.0.1:15432/retail_media_platform"
export SOURCE_MINIO_ENDPOINT="127.0.0.1:19000"

BACKUP_RUN_DIR="$(ls -d "$BACKUP_ROOT"/*/ | head -1)"
python3 scripts/restore/isolated_restore.py "$BACKUP_RUN_DIR" --drill

# ── 6. create app role (NOBYPASSRLS) on target ─────────────────────────────
echo "=== 6. app role (target) ==="
PGPASSWORD="${TGT_OWNER_PW}" psql -h 127.0.0.1 -p 15433 -U retail_media_owner -d retail_media_platform \
  -v ON_ERROR_STOP=1 <<'SQL'
DO $$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='retail_media_app') THEN
    CREATE ROLE retail_media_app LOGIN PASSWORD 'drill_app_role_pw_0123456789' NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
  END IF;
END $$;
GRANT USAGE ON SCHEMA public TO retail_media_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO retail_media_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO retail_media_app;
SQL

# ── 6b. start control-api against the restored target (version + health) ───
echo "=== 6b. start control-api (restored target) ==="
(
  cd apps/control-api
  ENVIRONMENT=dev \
  DATABASE_URL="postgresql+asyncpg://retail_media_app:${APP_ROLE_PW}@127.0.0.1:15433/retail_media_platform" \
  JWT_SECRET="drill-jwt-secret-at-least-32-chars-long" \
  JWT_AUDIENCE="drill-audience" \
  CORS_ALLOWED_ORIGINS="https://portal.pilot.example.com" \
  CORS_ALLOW_CREDENTIALS="true" \
  MANIFEST_SIGNING_KEY="drill-manifest-signing-key-at-least-32-chars" \
  MINIO_INTERNAL_ENDPOINT="127.0.0.1:19001" \
  MINIO_PUBLIC_ENDPOINT="127.0.0.1:19001" \
  MINIO_ACCESS_KEY="${MINIO_ROOT_USER_TGT}" \
  MINIO_SECRET_KEY="${MINIO_ROOT_PW_TGT}" \
  CREATIVE_STORAGE_BUCKET="drill-creatives" \
  CONTRACT_STORAGE_BUCKET="drill-contracts" \
  RMP_SERVICE="control-api" \
  RMP_VERSION="${VERSION}" \
  RMP_GIT_SHA="${GIT_SHA}" \
  RMP_BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  CONTROL_API_PORT=18000 \
  nohup uvicorn main:app --host 0.0.0.0 --port 18000 > /tmp/drill-control-api.log 2>&1 &
)
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:18000/health/live >/dev/null 2>&1; then
    echo "  control-api ready on :18000"
    break
  fi
  sleep 2
done

# ── 7. behavioral verification + negative matrix ───────────────────────────
echo "=== 7. verification suite ==="
export RUN_RESTORE_DRILL_TESTS=1
export RESTORE_TARGET_DATABASE_URL="postgresql://retail_media_owner:${TGT_OWNER_PW}@127.0.0.1:15433/retail_media_platform"
export RESTORE_TARGET_APP_DATABASE_URL="postgresql://retail_media_app:${APP_ROLE_PW}@127.0.0.1:15433/retail_media_platform"
export RESTORE_TARGET_MINIO_ENDPOINT="127.0.0.1:19001"
export MINIO_ACCESS_KEY="${MINIO_ROOT_USER_TGT}"
export MINIO_SECRET_KEY="${MINIO_ROOT_PW_TGT}"
export CREATIVE_STORAGE_BUCKET="drill-creatives"
export CONTRACT_STORAGE_BUCKET="drill-contracts"
export BACKUP_MANIFEST_PATH="${BACKUP_RUN_DIR}backup-manifest.json"
export BACKUP_DIR="$BACKUP_RUN_DIR"
export RMP_GIT_SHA="$GIT_SHA"
export RMP_VERSION="$VERSION"
export CONTROL_API_BASE_URL="http://127.0.0.1:18000"

python3 -m pytest tests/integration/test_restore_drill_verify.py -v --tb=short 2>&1 | tee /tmp/drill-verify.txt
PYTEST_EXIT=${PIPESTATUS[0]}

if ! grep -qE '[0-9]+ passed' /tmp/drill-verify.txt; then
  echo "::error::No restore drill verification tests passed — all skipped or zero collected" >&2
  exit 1
fi

echo "=== 8. negative matrix (re-run in drill context) ==="
python3 -m pytest tests/test_backup_restore_drill.py -v --tb=short 2>&1 | tee /tmp/drill-negative.txt

# ── 9. sanitized summary (no secrets) ──────────────────────────────────────
echo "=== Drill Summary ==="
echo "  git_sha:          $GIT_SHA"
echo "  alembic head:     $(PGPASSWORD="${TGT_OWNER_PW}" psql -h 127.0.0.1 -p 15433 -U retail_media_owner -d retail_media_platform -Atc 'SELECT version_num FROM alembic_version;')"
echo "  manifest path:    ${BACKUP_RUN_DIR}backup-manifest.json"
echo "  buckets restored: drill-creatives,drill-contracts"
echo "  negative matrix:  $(grep -cE 'PASSED' /tmp/drill-negative.txt || true) passed"

exit "$PYTEST_EXIT"
