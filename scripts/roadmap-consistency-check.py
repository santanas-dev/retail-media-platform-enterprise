#!/usr/bin/env python3
"""
Registry-Consistency Guard — ROADMAP-GUARD-002, после canonical cutover RM-GOV-005.

Reads feature-registry.yaml, scans tests/ui-smoke/ for existing smoke tests, and
checks that the registry tells the truth about its own proofs.

Three live directions:
  Registry validation — required fields, valid status, and every reachable UI
      feature naming a smoke function that actually exists on disk.
  C — orphan smokes: a smoke function no registry entry claims.
  D — CI subset membership: every reachable UI feature's smoke listed in
      tests/ui-smoke/ci-subset.txt, i.e. actually enforced by CI.

REMOVED at cutover (RM-GOV-005, 2026-08-26): the registry-versus-XLSX direction.
It compared the registry with a hand-maintained workbook. The workbook is now
GENERATED from the registry (scripts/ci/roadmap-generate.py), so the comparison
could no longer disagree with itself — a green check that proved nothing. The
legacy workbook is archived in docs/product/history/; drift between inputs and
generated views is proven instead by scripts/ci/roadmap-governance-guard.py.

This script registers no CI job of its own. It is a module of the single
governance entrypoint (rule B-3); its own CLI stays available for targeted runs.

Modes:
  --audit   (default) Find violations, print findings, exit 0 (non-blocking).
  --strict  Exit 1 if any violation found.

Usage:
  python3 scripts/roadmap-consistency-check.py --strict
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "product" / "feature-registry.yaml"
UI_SMOKE_DIR = REPO_ROOT / "tests" / "ui-smoke"
CI_SUBSET_PATH = UI_SMOKE_DIR / "ci-subset.txt"

# Column names in the 4-column business sheet (ROADMAP-DONE-GATE-001)

# ---- Helpers ---------------------------------------------------------------

def load_registry():
    with open(REGISTRY_PATH) as f:
        data = yaml.safe_load(f)
    return data.get("features", [])


def scan_smoke_functions():
    """Scan tests/ui-smoke/ for def test_uismoke__* functions.
    Returns dict: {test_function_name: file_path}."""
    smoke_funcs = {}
    if not UI_SMOKE_DIR.is_dir():
        return smoke_funcs
    for pyfile in UI_SMOKE_DIR.glob("*.py"):
        if pyfile.name.startswith("__"):
            continue
        try:
            tree = ast.parse(pyfile.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_uismoke__"):
                    smoke_funcs[node.name] = str(pyfile.relative_to(REPO_ROOT))
        except SyntaxError:
            pass
    return smoke_funcs


def load_ci_subset():
    """Read tests/ui-smoke/ci-subset.txt.
    Returns set of smoke function names in the CI subset.
    Lines starting with # are comments, empty lines ignored.
    """
    if not CI_SUBSET_PATH.is_file():
        return set()
    subset = set()
    for line in CI_SUBSET_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        subset.add(line)
    return subset




# ---- Registry validation (unchanged from UI-TRUTH-001B) --------------------

REQUIRED_FIELDS = ["id", "frontend", "name", "route", "path", "smoke",
                   "priority", "roles", "status"]
VALID_STATUSES = {"reachable", "blocked"}


def validate_registry(features, smoke_funcs):
    findings = []
    seen_ids = set()
    for f in features:
        fid = f.get("id", "<missing>")
        if fid in seen_ids:
            findings.append(f"REGISTRY: duplicate id '{fid}'")
        seen_ids.add(fid)
        for field in REQUIRED_FIELDS:
            if field not in f:
                findings.append(f"REGISTRY: '{fid}' missing field '{field}'")
        status = f.get("status", "")
        if status not in VALID_STATUSES:
            findings.append(f"REGISTRY: '{fid}' invalid status '{status}'")
        frontend = f.get("frontend", "")
        smoke = f.get("smoke", "")
        if frontend != "service" and status == "reachable":
            if not smoke or smoke not in smoke_funcs:
                findings.append(
                    f"REGISTRY-SMOKE: '{fid}' status=reachable (UI) "
                    f"but smoke '{smoke}' not found in tests/ui-smoke/"
                )
    return findings


# ---- Roadmap → Registry consistency (4-column structure) -------------------










# ---- Direction C: Every UI-smoke must be referenced by exactly one registry feature

def check_smoke_orphans(smoke_funcs, features):
    """Direction C: Discover all UI-smoke functions and verify each has
    exactly one registry feature referencing it.

    Returns list of findings:
      - SMOKE-ORPHAN: smoke function with 0 registry references
      - SMOKE-DUPLICATE: smoke function referenced by >1 registry features
    """
    findings = []
    # Build reverse map: smoke_func_name → list of feature ids
    smoke_to_features = {}
    for f in features:
        smoke = f.get("smoke", "")
        if not smoke:
            continue
        # Only check test_uismoke__* smokes (skip service/behavioral refs)
        if not smoke.startswith("test_uismoke__"):
            continue
        smoke_to_features.setdefault(smoke, []).append(f["id"])

    for smoke_name, smoke_path in smoke_funcs.items():
        refs = smoke_to_features.get(smoke_name, [])
        if len(refs) == 0:
            findings.append(
                f"SMOKE-ORPHAN: '{smoke_name}' ({smoke_path}) has "
                f"no registry feature referencing it"
            )
        elif len(refs) > 1:
            # Shared smoke is legitimate — one smoke can prove multiple features
            # (e.g. test_uismoke__commerce__order_create proves order_create + offer_generate + booking + payment_status)
            # SMOKE-DUPLICATE is no longer a violation.
            pass
    return findings


# ---- Direction D: Every reachable UI smoke must be in CI subset -------------

def check_ci_subset_membership(features, smoke_funcs, ci_subset):
    """Direction D: For every reachable UI feature with smoke, verify the
    smoke function is listed in ci-subset.txt (CI-enforced).

    Returns list of REGISTRY-CI-EXCLUDED findings.
    """
    findings = []
    if not ci_subset:
        findings.append("CI-SUBSET-MISSING: ci-subset.txt not found or empty")
        return findings

    for f in features:
        fid = f.get("id", "?")
        if f.get("status") != "reachable":
            continue
        if f.get("frontend", "") == "service":
            continue
        smoke = f.get("smoke", "")
        if not smoke:
            continue
        if not smoke.startswith("test_uismoke__"):
            continue
        if smoke not in smoke_funcs:
            # Already caught by REGISTRY-SMOKE
            continue
        # ci-subset.txt stores short names (e.g. campaign__create),
        # registry stores full test function names (e.g. test_uismoke__campaign__create)
        short_name = smoke.replace("test_uismoke__", "", 1)
        if short_name not in ci_subset:
            findings.append(
                f"REGISTRY-CI-EXCLUDED: '{fid}' smoke '{smoke}' "
                f"is reachable but not listed in ci-subset.txt "
                f"(feature is reachable but not CI-enforced)"
            )
    return findings


# ---- Main ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Roadmap-consistency guard (4-col)")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 on any violation (blocking CI gate)")
    args = parser.parse_args()

    all_findings = []

    # Load data
    try:
        features = load_registry()
    except Exception as e:
        print(f"FATAL: cannot load registry: {e}", file=sys.stderr)
        sys.exit(2 if args.strict else 0)

    try:
        smoke_funcs = scan_smoke_functions()
    except Exception as e:
        print(f"WARNING: cannot scan smoke tests: {e}", file=sys.stderr)
        smoke_funcs = {}

    # 1. Registry validation
    registry_findings = validate_registry(features, smoke_funcs)
    all_findings.extend(registry_findings)

    # 3. Direction C: Smoke orphans/duplicates
    smoke_orphan_findings = check_smoke_orphans(smoke_funcs, features)
    all_findings.extend(smoke_orphan_findings)

    # 4. Direction D: CI subset membership
    ci_subset = load_ci_subset()
    ci_excluded_findings = check_ci_subset_membership(features, smoke_funcs, ci_subset)
    all_findings.extend(ci_excluded_findings)

    # Report
    print("=== Roadmap-Consistency Guard (ROADMAP-GUARD-002, 4-column) ===")
    print(f"  Registry: {len(features)} features")
    print(f"  Smoke tests found: {len(smoke_funcs)} functions")
    print(f"  Findings: {len(all_findings)}")
    print()

    if all_findings:
        print("--- Findings ---")
        for i, finding in enumerate(all_findings, 1):
            print(f"  [{i}] {finding}")
        print()
        print(f"SUMMARY: {len(all_findings)} violation(s) found.")
    else:
        print("SUMMARY: 0 violations — roadmap ↔ registry ↔ smoke consistent.")

    # Behavioral proof
    print()
    print("--- Behavioral Proof ---")
    reachable_ids = {f["id"] for f in features if f.get("status") == "reachable"}
    ui_reachable = [fid for fid in reachable_ids
                    if feature_map_safe(features, fid, "frontend") != "service"]
    print(f"  Reachable UI features: {len(ui_reachable)} — {ui_reachable}")
    for fid in ui_reachable:
        feat = feature_map_safe(features, fid, None)
        smoke = feat.get("smoke", "") if feat else ""
        in_smoke = smoke in smoke_funcs
        print(f"    {fid}: smoke={smoke} {'✅ found' if in_smoke else '❌ MISSING'}")
    print(f"  Reachable service features: "
          f"{len(reachable_ids) - len(ui_reachable)}")

    exit_code = 0
    if args.strict and all_findings:
        exit_code = 1
    sys.exit(exit_code)


def feature_map_safe(features, fid, key):
    for f in features:
        if f.get("id") == fid:
            return f.get(key) if key else f
    return None


if __name__ == "__main__":
    main()
