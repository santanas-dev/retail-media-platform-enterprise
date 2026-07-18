#!/usr/bin/env bash
# CLEAN-BOOT-001: Clean Docker Boot -> Login Smoke
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE1="$REPO_DIR/infra/compose/docker-compose.phase1.yml"
COMPOSE2="$REPO_DIR/infra/compose/docker-compose.preview.yml"
API_URL="${API_URL:-http://localhost:8000}"

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'
pass()  { echo -e "${GREEN}PASS${NC}: $*"; }
fail()  { echo -e "${RED}FAIL${NC}: $*"; exit 1; }

echo "=== CLEAN-BOOT-001: Clean Docker Boot -> Login Smoke ==="
echo ""

echo "--- Step 1: docker compose down -v ---"
docker compose -f "$COMPOSE1" -f "$COMPOSE2" down -v --remove-orphans 2>/dev/null || true
echo ""

echo "--- Step 2: Starting postgres + redis + control-api ---"
docker compose -f "$COMPOSE1" -f "$COMPOSE2" up -d --build postgres redis control-api
echo ""

echo "--- Step 3: Waiting for control-api healthy ---"
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w '%{http_code}' "$API_URL/api/v1/health" | grep -q 200; then
    pass "control-api healthy"
    break
  fi
  sleep 2
done
echo ""

echo "--- Step 4: Running db-setup ---"
docker compose -f "$COMPOSE1" -f "$COMPOSE2" --profile setup run --rm db-setup
pass "db-setup completed"
echo ""

echo "--- Step 5: Login ---"
LOGIN_JSON='{"username_or_email":"advertiser_test","password":"advertiser-dev-only","auth_provider":"local_advertiser"}'
RESP=$(curl -s -X POST "$API_URL/api/v1/auth/login" -H 'Content-Type: application/json' -d "$LOGIN_JSON")
HTTP=$(echo "$RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print('200' if 'access_token' in d else '401')")
[ "$HTTP" = "200" ] || fail "Login failed"
TOKEN=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
[ -n "$TOKEN" ] || fail "No access_token"
pass "Login 200 + token"
echo ""

echo "--- Step 6: Campaigns ---"
CAMP=$(curl -s "$API_URL/api/v1/identity/campaigns" -H "Authorization: Bearer $TOKEN")
TOTAL=$(echo "$CAMP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('total',0))")
[ -n "$TOTAL" ] && [ "$TOTAL" != "0" ] || fail "Campaigns total=$TOTAL"
pass "Campaigns 200, total=$TOTAL"
echo ""

echo "--- Step 7: local_credentials ---"
CRED=$(docker compose -f "$COMPOSE1" -f "$COMPOSE2" exec -T postgres \
  psql -U retail_media_owner -d retail_media_platform \
  -t -c 'SELECT count(*) FROM local_credentials;' 2>/dev/null | tr -d '[:space:]')
[ -n "$CRED" ] && [ "$CRED" != "0" ] || fail "local_credentials=$CRED"
pass "local_credentials count = $CRED"
echo ""

echo -e "${GREEN}=== ALL CHECKS PASSED ===${NC}"
echo "  login: 200 + token"
echo "  campaigns: 200 + $TOTAL items"
echo "  credentials: $CRED seeded"
