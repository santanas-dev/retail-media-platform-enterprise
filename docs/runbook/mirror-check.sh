#!/usr/bin/env bash
# mirror-check.sh — Verify NAS mirror is synced with GitHub origin
#
# SOURCE-TRUTH-001: GitHub origin/develop is the sole git-source-of-truth.
# NAS/ASUSTOR is a mirror — may be stale. This script checks mirror status.
#
# Uses HTTPS (not SSH) by default — no deploy key, no known_hosts trust needed.
#
# Usage:
#   # Check if NAS matches expected origin SHA:
#   EXPECTED_ORIGIN_DEVELOP_SHA=c3ae9bf ./mirror-check.sh
#
#   # Or pass as argument:
#   ./mirror-check.sh --expected-origin-sha c3ae9bf
#
#   # Discover origin SHA from GitHub HTTPS (no local clone needed):
#   ./mirror-check.sh --discover-origin
#
#   # Combined: discover + compare against NAS HEAD
#   ./mirror-check.sh --discover-origin --nas-path /mnt/nas/repo
#
# Exit codes:
#   0 — verified (NAS matches expected origin SHA)
#   0 — cannot-verify-from-here (network/GitHub/NAS unreachable — neutral, not a failure)
#   1 — stale (NAS behind or diverged; pull needed)
#   3 — script error (bad args, missing deps)

set -euo pipefail

GITHUB_HTTPS_URL="https://github.com/santanas-dev/retail-media-platform-enterprise.git"
NAS_DEFAULT_PATH="/mnt/nas/retail-media-platform-enterprise"

EXPECTED_SHA="${EXPECTED_ORIGIN_DEVELOP_SHA:-}"
NAS_PATH="$NAS_DEFAULT_PATH"
DISCOVER_ORIGIN=false

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Options:
  --expected-origin-sha SHA    Expected origin/develop SHA to compare against
  --nas-path PATH              Path to NAS mirror clone (default: $NAS_DEFAULT_PATH)
  --discover-origin            Fetch origin SHA from GitHub HTTPS (no local clone needed)
  -h, --help                   Show this help

Environment:
  EXPECTED_ORIGIN_DEVELOP_SHA  Same as --expected-origin-sha

Exit codes:
  0 = verified or cannot-verify-from-here (neutral)
  1 = stale (NAS behind/diverged, pull needed)
  3 = script error
EOF
  exit 3
}

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expected-origin-sha) EXPECTED_SHA="$2"; shift 2 ;;
    --nas-path) NAS_PATH="$2"; shift 2 ;;
    --discover-origin) DISCOVER_ORIGIN=true; shift ;;
    -h|--help) usage ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

# Discover origin SHA if requested
if $DISCOVER_ORIGIN; then
  echo ":: Discovering origin/develop SHA from GitHub HTTPS..."
  ORIGIN_REF=$(git ls-remote --heads "$GITHUB_HTTPS_URL" refs/heads/develop 2>/dev/null | awk '{print $1}')
  if [[ -z "$ORIGIN_REF" ]]; then
    echo "STATUS: cannot-verify-from-here"
    echo "REASON: GitHub HTTPS unreachable (git ls-remote failed on $GITHUB_HTTPS_URL)"
    exit 0
  fi
  ORIGIN_SHA="${ORIGIN_REF:0:7}"
  echo ":: GitHub origin/develop: $ORIGIN_SHA (full: $ORIGIN_REF)"
  EXPECTED_SHA="$ORIGIN_SHA"
fi

# --discover-origin without NAS comparison
if $DISCOVER_ORIGIN && [[ -z "${NAS_PATH:-}" || "$NAS_PATH" == "/dev/null" ]]; then
  echo "STATUS: origin-only-check"
  echo "ORIGIN_SHA: $EXPECTED_SHA"
  exit 0
fi

# Need expected SHA
if [[ -z "$EXPECTED_SHA" ]]; then
  echo "STATUS: cannot-verify-from-here"
  echo "REASON: no --expected-origin-sha or EXPECTED_ORIGIN_DEVELOP_SHA provided"
  echo "HINT: run with --discover-origin to fetch from GitHub, or provide the SHA directly"
  exit 0
fi

# Check NAS path
if [[ ! -d "$NAS_PATH/.git" ]]; then
  echo "STATUS: cannot-verify-from-here"
  echo "REASON: NAS mirror path not accessible: $NAS_PATH"
  echo "HINT: mount NAS first, or run from santa2 where NAS is mounted"
  exit 0
fi

# Get NAS HEAD
NAS_HEAD=$(git -C "$NAS_PATH" rev-parse --short HEAD 2>/dev/null) || {
  echo "STATUS: cannot-verify-from-here"
  echo "REASON: cannot read git HEAD from NAS mirror at $NAS_PATH"
  exit 0
}

# Compare
if [[ "$NAS_HEAD" == "${EXPECTED_SHA:0:7}" ]]; then
  echo "STATUS: verified"
  echo "NAS_HEAD: $NAS_HEAD"
  echo "EXPECTED: ${EXPECTED_SHA:0:7}"
  echo "NOTE: NAS mirror matches expected origin SHA"
  exit 0
fi

# Check if NAS is ancestor of expected (behind)
if git -C "$NAS_PATH" merge-base --is-ancestor "$NAS_HEAD" "${EXPECTED_SHA}" 2>/dev/null; then
  echo "STATUS: stale"
  echo "NAS_HEAD: $NAS_HEAD"
  echo "EXPECTED: ${EXPECTED_SHA:0:7}"
  echo "ACTION: git fetch origin && git reset --hard origin/develop on NAS mirror"
  exit 1
fi

# Diverged or ahead — also stale from mirror perspective
echo "STATUS: stale"
echo "NAS_HEAD: $NAS_HEAD"
echo "EXPECTED: ${EXPECTED_SHA:0:7}"
echo "NOTE: NAS HEAD does not match expected origin SHA. Pull recommended."
exit 1
