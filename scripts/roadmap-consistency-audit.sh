#!/usr/bin/env bash
# UI-TRUTH-001B — Roadmap-Consistency Audit Runner.
#
# Runs the consistency check in non-blocking audit mode.
# Findings are printed but the script always exits 0.
# This is intentionally separate from the main CI pipeline.
#
# Usage:
#   bash scripts/roadmap-consistency-audit.sh
#
# CI integration (non-blocking):
#   The CI job runs this script.  Exit code is always 0
#   (even on violations) — the CI job reports findings
#   but does NOT turn the build red.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

echo "=== UI-TRUTH-001B: Roadmap-Consistency Audit ==="
echo ""

pip install -q openpyxl pyyaml 2>/dev/null || true

python3 scripts/roadmap-consistency-check.py

echo ""
echo "=== Audit complete (non-blocking) ==="
