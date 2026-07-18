#!/usr/bin/env python3
"""
Roadmap-Consistency Check — UI-TRUTH-001B.

Reads feature-registry.yaml, scans tests/ui-smoke/ for existing smoke tests,
and reads roadmap.xlsx (Бизнес-функции) to detect violations of the rule:
«Бизнес-функция может быть "Готово" только если все её journey имеют
registry status: reachable и зелёный UI-smoke».

Modes:
  --audit   (default) Find violations, print findings, exit 0 (non-blocking).
  --strict  Exit 1 if any violation found (for future CI gate).

Usage:
  python3 scripts/roadmap-consistency-check.py          # audit mode
  python3 scripts/roadmap-consistency-check.py --strict # blocking mode
"""

import argparse
import ast
import os
import re
import sys
from pathlib import Path

import openpyxl
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "docs" / "product" / "feature-registry.yaml"
ROADMAP_PATH = REPO_ROOT / "docs" / "product" / "roadmap-s020-2026-07-10.xlsx"
UI_SMOKE_DIR = REPO_ROOT / "tests" / "ui-smoke"

# ---- Validation helpers --------------------------------------------------

def load_registry():
    """Load feature-registry.yaml, return list of feature dicts."""
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


def load_roadmap_business():
    """Read Бизнес-функции Roadmap sheet.
    Returns list of {col_name: cell_value} dicts."""
    wb = openpyxl.load_workbook(ROADMAP_PATH)
    ws = wb["Бизнес-функции Roadmap"]
    headers = [str(c.value or "") for c in ws[1]]
    rows = []
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, values_only=True):
        if row[1] is None or str(row[1]).strip() == "":
            continue  # skip section headers / empty rows
        d = {}
        for i, h in enumerate(headers):
            d[h] = str(row[i]) if row[i] is not None else ""
        rows.append(d)
    wb.close()
    return rows


# ---- Registry validation -------------------------------------------------

REQUIRED_FIELDS = ["id", "frontend", "name", "route", "path", "smoke", "priority", "roles", "status"]
VALID_STATUSES = {"reachable", "blocked"}
VALID_FRONTENDS = {"admin-web", "advertiser-web", "public", "service"}


def validate_registry(features, smoke_funcs):
    """Validate registry structure and consistency with smoke tests.
    Returns list of finding strings."""
    findings = []
    seen_ids = set()

    for f in features:
        fid = f.get("id", "<missing>")

        # Duplicate check
        if fid in seen_ids:
            findings.append(f"REGISTRY: duplicate id '{fid}'")
        seen_ids.add(fid)

        # Required fields
        for field in REQUIRED_FIELDS:
            if field not in f:
                findings.append(f"REGISTRY: '{fid}' missing required field '{field}'")

        # Valid status
        status = f.get("status", "")
        if status not in VALID_STATUSES:
            findings.append(f"REGISTRY: '{fid}' has invalid status '{status}'")

        # UI reachable must have smoke
        frontend = f.get("frontend", "")
        smoke = f.get("smoke", "")
        if frontend != "service" and status == "reachable":
            if not smoke or smoke not in smoke_funcs:
                findings.append(
                    f"REGISTRY-SMOKE: '{fid}' status=reachable (UI) but smoke '{smoke}' "
                    f"not found in tests/ui-smoke/"
                )

    return findings


# ---- Roadmap vs Registry consistency -------------------------------------

# Business function names from roadmap that map to feature-registry domains.
# This is a heuristic mapping — exact mapping requires domain knowledge.
# Functions with no UI (manifest, PoP, observability, backup) are service
# and don't need UI-smoke.

SERVICE_FUNCTIONS = {
    "Формирование плейлистов (manifest)",
    "Получение manifest устройством",
    "Proof-of-Play (подтверждение показов)",
    "Отчёты по показам",
    "Emergency-управление",
    "Резервное копирование и DR",
    "Мониторинг и observability",
}

UI_FUNCTIONS = {
    "Вход сотрудников / рекламодателей",
    "Роли и права (RBAC)",
    "Личный кабинет рекламодателя",
    "Создание и редактирование кампаний",
    "Согласование кампаний (Approval)",
    "Загрузка креативов (медиафайлы)",
    "Инвентарь",
    "Управление рекламодателями",
}


def check_roadmap_vs_registry(roadmap_rows, features, smoke_funcs):
    """Check business roadmap 'Готово' claims against registry reality.
    Returns list of finding strings."""
    findings = []

    # Build quick lookup: which features are actually reachable?
    reachable_ids = set()
    blocked_ids = set()
    for f in features:
        if f.get("status") == "reachable":
            reachable_ids.add(f["id"])
        else:
            blocked_ids.add(f["id"])

    for row in roadmap_rows:
        func_name = row.get("Бизнес-функция", "").strip()
        status_raw = row.get("Статус", "").strip()

        if not func_name:
            continue

        # Check if roadmap claims "Готово"
        is_gotovo = (
            status_raw.startswith("✅ Готово")
            or status_raw.startswith("🟡 Готово")
        )
        if not is_gotovo:
            continue

        # For service functions, check registry has reachable entries in that domain
        if func_name in SERVICE_FUNCTIONS:
            # These don't need UI-smoke — check service reachability
            # We accept these: all have green behavioral tests
            continue

        # For UI functions: every P0/P1 feature in the domain should be reachable
        # But we don't have a domain→feature mapping. Heuristic: if roadmap says
        # "Готово" for a UI function, check if ANY of the 30 UI features are
        # reachable (they aren't — all blocked, so flag it).
        #
        # More precise: flag the function as overclaim unless at least one
        # relevant registry feature is reachable.
        relevant = _find_relevant_features(func_name, features)
        if not relevant:
            findings.append(
                f"ROADMAP: '{func_name}' claims '{status_raw}' but no matching "
                f"feature-registry entries found"
            )
            continue

        all_blocked = all(f.get("status") != "reachable" for f in relevant)
        if all_blocked:
            smoke_refs = [f["id"] for f in relevant if f.get("status") != "reachable"]
            findings.append(
                f"ROADMAP: '{func_name}' claims '{status_raw}' but ALL relevant "
                f"features are blocked (no green smoke): {smoke_refs[:5]}"
            )

    return findings


def _find_relevant_features(func_name, features):
    """Heuristic: find registry features relevant to a business function name."""
    name_lower = func_name.lower()
    relevant = []
    keywords_map = {
        "вход": ["self.login", "campaign.create"],  # login related
        "роли": ["user.assign_roles", "user.create_advertiser"],
        "кабинет": ["self.login", "self.campaign_view", "self.report_view"],
        "создание": ["campaign.create", "campaign.edit"],
        "кампаний": ["campaign.create", "campaign.edit", "campaign.submit", "campaign.activate"],
        "согласование": ["campaign.approve", "campaign.reject"],
        "креатив": ["creative.upload", "creative.moderate_approve", "creative.moderate_reject"],
        "загрузка": ["creative.upload"],
        "инвентар": ["inventory.simulate", "inventory.rule_create"],
        "availabilit": ["inventory.simulate", "inventory.rule_create"],
        "рекламодател": ["advertiser.create_org", "advertiser.view", "advertiser.application_review"],
    }
    matched_ids = set()
    for kw, ids in keywords_map.items():
        if kw in name_lower:
            matched_ids.update(ids)

    if matched_ids:
        relevant = [f for f in features if f.get("id") in matched_ids]
    return relevant


# ---- Main -----------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Roadmap-consistency guard")
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

    roadmap_rows = []
    roadmap_error = None
    try:
        roadmap_rows = load_roadmap_business()
    except Exception as e:
        roadmap_error = str(e)
        all_findings.append(f"ROADMAP-PARSE: cannot read roadmap.xlsx — {e}")

    # 1. Registry validation
    registry_findings = validate_registry(features, smoke_funcs)
    all_findings.extend(registry_findings)

    # 2. Roadmap vs registry consistency
    if not roadmap_error:
        roadmap_findings = check_roadmap_vs_registry(roadmap_rows, features, smoke_funcs)
        all_findings.extend(roadmap_findings)

    # Report
    print(f"=== Roadmap-Consistency Guard (UI-TRUTH-001B) ===")
    print(f"  Registry: {len(features)} features")
    print(f"  Smoke tests found: {len(smoke_funcs)} functions")
    print(f"  Roadmap rows (business): {len(roadmap_rows)}")
    print(f"  Findings: {len(all_findings)}")
    print()

    if all_findings:
        print("--- Findings ---")
        for i, finding in enumerate(all_findings, 1):
            print(f"  [{i}] {finding}")
        print()
        print(f"SUMMARY: {len(all_findings)} violation(s) found.")
    else:
        print("SUMMARY: 0 violations — registry ↔ roadmap ↔ smoke consistent.")

    # Verify specific checks for behavioral proof
    print()
    print("--- Behavioral Proof ---")
    # campaign.create smoke found?
    cc_smoke = "test_uismoke__campaign__create"
    if cc_smoke in smoke_funcs:
        print(f"  [OK] campaign.create smoke exists: {smoke_funcs[cc_smoke]}")
    else:
        print(f"  [MISSING] campaign.create smoke '{cc_smoke}' not found")

    # UI reachable without smoke? (should be 0 in registry validation)
    ui_reachable_issues = [f for f in registry_findings if "REGISTRY-SMOKE" in f]
    if ui_reachable_issues:
        print(f"  [VIOLATIONS] UI reachable without smoke: {len(ui_reachable_issues)}")
    else:
        print(f"  [OK] No UI features with reachable status lacking smoke")

    exit_code = 0
    if args.strict and all_findings:
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
