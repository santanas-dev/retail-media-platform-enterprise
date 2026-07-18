#!/usr/bin/env bash
# UI-TRUTH-001A — UI-smoke audit runner.
#
# Runs all ui-smoke tests against a live clean-boot stack.
# This is an AUDIT tool, NOT a CI gate. Expected failures are
# documented gaps (feature-registry.yaml).
#
# Usage:
#   scripts/ui-smoke-audit.sh          # all smoke tests
#   scripts/ui-smoke-audit.sh campaign # single feature
#
# Prerequisites:
#   - Clean-boot stack running (docker compose up)
#   - playwright + chromium installed (pip install pytest-playwright)
#   - UI_SMOKE_BASE_URL set or defaults to http://localhost:3000

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

HERMES_PYTHON="${HERMES_PYTHON:-/home/cobalt/.hermes/hermes-agent/venv/bin/python3}"

FEATURE="${1:-all}"

echo "╔══════════════════════════════════════════════════════════╗"
echo "║  UI-Smoke Audit — UI-TRUTH-001                         ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  Base URL: ${UI_SMOKE_BASE_URL:-http://localhost:3000}"
echo "  Feature:  ${FEATURE}"
echo ""
echo "  IMPORTANT: Failures below are EXPECTED if feature-registry"
echo "  marks the feature as 'blocked'. Green = gap is closed."
echo ""

if [ "$FEATURE" = "all" ]; then
    TEST_TARGET="tests/ui-smoke/"
else
    TEST_TARGET="tests/ui-smoke/"
fi

UI_SMOKE_RUN=1 "$HERMES_PYTHON" -m pytest "$TEST_TARGET" -v \
    --color=yes \
    --tb=short \
    -o "addopts=" \
    "$@"

echo ""
echo "──"
echo "  See docs/product/feature-registry.yaml for gap documentation."
echo "  G1 gaps are expected failures — not regressions."
