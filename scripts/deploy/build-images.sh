#!/usr/bin/env bash
# =============================================================================
# Retail Media Platform — reproducible image build (PILOT-DEPLOYMENT-READINESS-001B, SCOPE F)
#
# Builds all production app images with immutable OCI labels and — optionally —
# pushes them to a registry and emits a lock manifest with real digests.
#
# Requirements:
#   - clean git tree (refuses to build otherwise)
#   - VERSION and GIT_SHA must be provided (or auto-derived from git)
#
# Usage:
#   scripts/deploy/build-images.sh [--version V] [--sha S] [--push] [--registry R]
#
#   --push       push to registry (requires docker login) and emit images.lock.json
#   --registry R registry prefix (default: ghcr.io/santanas-dev/retail-media-platform-enterprise)
#
# Without --push: builds locally and prints image IDs (no digest push, no lock write).
# Never uses `latest`.
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

VERSION="${VERSION:-}"
GIT_SHA="${GIT_SHA:-}"
PUSH=false
REGISTRY="${REGISTRY:-ghcr.io/santanas-dev/retail-media-platform-enterprise}"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --version) VERSION="$2"; shift 2 ;;
    --sha) GIT_SHA="$2"; shift 2 ;;
    --push) PUSH=true; shift ;;
    --registry) REGISTRY="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# --- Derive version/SHA from git if not provided ---------------------------
if [[ -z "$VERSION" ]]; then
  VERSION="$(git describe --tags --always 2>/dev/null || echo 'dev')"
fi
if [[ -z "$GIT_SHA" ]]; then
  GIT_SHA="$(git rev-parse HEAD)"
fi

# --- Require clean tree ----------------------------------------------------
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "ERROR: working tree is dirty. Commit or stash before building." >&2
  git status --short >&2
  exit 1
fi

# Validate GIT_SHA looks like a SHA
if [[ ! "$GIT_SHA" =~ ^[0-9a-f]{7,40}$ ]]; then
  echo "ERROR: GIT_SHA '$GIT_SHA' is not a valid git SHA" >&2
  exit 1
fi

echo "=== Build: version=$VERSION sha=$GIT_SHA build_time=$BUILD_TIME ==="
echo "=== Registry: $REGISTRY (push=$PUSH) ==="

# --- Service → image mapping ----------------------------------------------
# Backend services share the multi-arg Dockerfile; frontends have their own.
declare -a SERVICES=(
  "control-api|apps.control-api.main|8000|infra/compose/Dockerfile.service|control-api"
  "device-gateway|apps.device-gateway.main|8001|infra/compose/Dockerfile.service|device-gateway"
  "orchestrator-worker|apps.orchestrator-worker.main|8003|infra/compose/Dockerfile.service|orchestrator-worker"
  "admin-web||||apps/admin-web/Dockerfile|admin-web"
  "advertiser-web||||apps/advertiser-web/Dockerfile|advertiser-web"
)

build_image() {
  local name="$1" module="$2" port="$3" dockerfile="$4" short="$5"
  local image="${REGISTRY}/${name}"
  local ref="${image}:${GIT_SHA}"

  echo ""
  echo "--- Building ${name} (${ref}) ---"
  local -a build_args=(
    --build-arg "RMP_VERSION=${VERSION}"
    --build-arg "RMP_GIT_SHA=${GIT_SHA}"
    --build-arg "RMP_BUILD_TIME=${BUILD_TIME}"
  )
  if [[ -n "$module" ]]; then
    build_args+=(--build-arg "SERVICE_NAME=${short}" --build-arg "SERVICE_MODULE=${module}" --build-arg "SERVICE_PORT=${port}")
  fi

  docker build \
    -f "$dockerfile" \
    -t "$ref" \
    --label "org.opencontainers.image.revision=${GIT_SHA}" \
    --label "org.opencontainers.image.version=${VERSION}" \
    --label "org.opencontainers.image.source=https://github.com/santanas-dev/retail-media-platform-enterprise" \
    --label "org.opencontainers.image.created=${BUILD_TIME}" \
    "${build_args[@]}" \
    .

  local image_id
  image_id="$(docker image inspect --format '{{.Id}}' "$ref")"
  echo "  image_id=${image_id}"

  if [[ "$PUSH" == "true" ]]; then
    docker push "$ref"
    local digest
    digest="$(docker image inspect --format '{{index .RepoDigests 0}}' "$ref")"
    echo "  digest=${digest}"
    # return just the sha256:... digest for the lock manifest
    echo "${digest##*@}"
  else
    # no push — return image id only
    echo "sha256:$(docker image inspect --format '{{.Id}}' "$ref" | sed 's/^sha256://')"
  fi
}

# Collect digest/image-id per service for the summary (and lock if --push).
declare -A RESULT=()

for entry in "${SERVICES[@]}"; do
  IFS='|' read -r name module port dockerfile short <<< "$entry"
  digest="$(build_image "$name" "$module" "$port" "$dockerfile" "$short" | tail -1)"
  RESULT["$name"]="$digest"
done

echo ""
echo "=== Build summary ==="
for name in "${!RESULT[@]}"; do
  printf "  %-20s %s\n" "$name" "${RESULT[$name]}"
done

# --- Emit lock manifest (only with --push, so digests are real) ------------
if [[ "$PUSH" == "true" ]]; then
  LOCK="infra/deploy/images.lock.json"
  python3 - "$LOCK" "$VERSION" "$GIT_SHA" "$BUILD_TIME" "${RESULT[control-api]}" "${RESULT[device-gateway]}" "${RESULT[orchestrator-worker]}" "${RESULT[admin-web]}" "${RESULT[advertiser-web]}" <<'PYEOF'
import json, sys
lock_path = sys.argv[1]
version, sha, build_time = sys.argv[2], sys.argv[3], sys.argv[4]
digests = sys.argv[5:10]
services = ["control-api", "device-gateway", "orchestrator-worker", "admin-web", "advertiser-web"]
registry = "ghcr.io/santanas-dev/retail-media-platform-enterprise"
images = []
for s, d in zip(services, digests):
    # d is "sha256:<hex>" from the push digest, or "sha256:<id>" fallback
    images.append({
        "service": s,
        "repository": f"{registry}/{s}",
        "version": version,
        "git_sha": sha,
        "image_digest": d if d.startswith("sha256:") else f"sha256:{d}",
        "build_timestamp": build_time,
        "source_tag": version,
    })
lock = {"release": {"version": version, "git_sha": sha},
        "build_timestamp": build_time, "images": images}
with open(lock_path, "w") as f:
    json.dump(lock, f, indent=2)
print(f"lock manifest written → {lock_path}")
PYEOF
  echo "Validate: python scripts/deploy/validate-image-lock.py --lock $LOCK"
fi

echo ""
echo "=== Build complete ==="
