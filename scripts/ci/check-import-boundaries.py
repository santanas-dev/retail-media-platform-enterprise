#!/usr/bin/env python3
"""Import boundary checker — ADR-014 enforcement.

Scans Python files against forbidden import rules defined in
``scripts/ci/import-boundaries.toml``.

Usage:
    python3 scripts/ci/check-import-boundaries.py          # scan all rules
    python3 scripts/ci/check-import-boundaries.py --quiet  # only print violations

Exit: 0 if clean, 1 if violations found.
"""

import ast
import re
import sys
from pathlib import Path

# Python 3.11+ — use tomllib; fall back to tomli for older interpreters
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        print("ERROR: tomllib or tomli required (stdlib tomllib available in Python 3.11+)")
        sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = Path(__file__).resolve().parent / "import-boundaries.toml"

# Patterns that look like imports
RE_FROM = re.compile(r"^\s*from\s+([\w.]+)\s+import")
RE_IMPORT = re.compile(r"^\s*import\s+(.+)$")


def _extract_imported_modules(line: str) -> list[str]:
    """Extract all top-level module names from an import line.

    Handles:
        import os                           → ['os']
        import os, fastapi                  → ['os', 'fastapi']
        import packages.api as api          → ['packages.api']
        from fastapi import APIRouter       → ['fastapi']
        from packages.api import a, b       → ['packages.api']
    """
    m = RE_FROM.match(line)
    if m:
        return [m.group(1)]

    m = RE_IMPORT.match(line)
    if m:
        names_part = m.group(1)
        modules = []
        for segment in names_part.split(","):
            # Strip whitespace and `as alias` suffix
            segment = segment.strip()
            if not segment:
                continue
            # Remove 'as alias' if present
            if " as " in segment:
                segment = segment.split(" as ", 1)[0].strip()
            modules.append(segment)
        return modules

    return []


def scan_file(filepath: Path, forbidden_patterns: list[str]) -> list[str]:
    """Scan a single .py file for forbidden imports. Returns violation lines."""
    violations = []
    try:
        lines = filepath.read_text().splitlines()
    except Exception:
        return violations

    for lineno, line in enumerate(lines, 1):
        # Skip comments and docstrings
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        modules = _extract_imported_modules(line)
        for imported in modules:
            for pattern in forbidden_patterns:
                if re.search(pattern, imported):
                    violations.append(f"  {filepath.relative_to(REPO_ROOT)}:{lineno}: imports '{imported}' (matches forbidden '{pattern}')")
                    break  # one violation per module per pattern

    return violations


def find_python_files(directory: Path) -> list[Path]:
    """Find all .py files under directory, excluding __pycache__."""
    if not directory.exists():
        return []
    return sorted(
        p for p in directory.rglob("*.py")
        if "__pycache__" not in str(p)
    )


# ---------------------------------------------------------------------------
# Licensing boundary (EPIC-L-SEAT-LEDGER-001A4 SCOPE E) — AST-based
# ---------------------------------------------------------------------------

def _docstring_constant_ids(tree: ast.Module) -> set[int]:
    """Return ``id()`` of Constant nodes that are module/class/function docstrings."""
    ids: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr):
                val = body[0].value
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    ids.add(id(val))
    return ids


def scan_licensing_boundary(
    filepath: Path,
    allowed_models: list[str],
    forbidden_imports: list[str],
    forbidden_literals: list[str],
) -> list[str]:
    """Scan a licensing file for boundary violations.

    Checks:
      1. ``from packages.domain.models import X`` — every ``X`` must be in the
         explicit ``allowed_models`` allowlist (models.py is monolithic).
      2. imports of forbidden modules (commerce / advertiser).
      3. string literals (excluding docstrings) referencing forbidden table
         prefixes (``commerce_*`` / ``advertiser_*``).
    """
    violations: list[str] = []
    rel = filepath.relative_to(REPO_ROOT)
    try:
        tree = ast.parse(filepath.read_text())
    except SyntaxError:
        return violations

    docstring_ids = _docstring_constant_ids(tree)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "packages.domain.models":
                for alias in node.names:
                    if alias.name not in allowed_models:
                        violations.append(
                            f"  {rel}:{node.lineno}: imports disallowed models "
                            f"symbol '{alias.name}'"
                        )
            for pattern in forbidden_imports:
                if re.search(pattern, module):
                    violations.append(
                        f"  {rel}:{node.lineno}: imports forbidden module "
                        f"'{module}' (matches '{pattern}')"
                    )
        elif isinstance(node, ast.Import):
            for alias in node.names:
                for pattern in forbidden_imports:
                    if re.search(pattern, alias.name):
                        violations.append(
                            f"  {rel}:{node.lineno}: imports forbidden module "
                            f"'{alias.name}' (matches '{pattern}')"
                        )
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
        ):
            for literal in forbidden_literals:
                if literal in node.value:
                    violations.append(
                        f"  {rel}:{node.lineno}: references forbidden table/"
                        f"literal '{literal}'"
                    )

    return violations


def main():
    quiet = "--quiet" in sys.argv

    try:
        config_text = CONFIG_PATH.read_text()
        config = tomllib.loads(config_text)
    except FileNotFoundError:
        print(f"ERROR: config not found: {CONFIG_PATH}")
        sys.exit(2)
    except Exception as e:
        print(f"ERROR: failed to parse {CONFIG_PATH}: {e}")
        sys.exit(2)

    rules = config.get("rule", [])
    if not rules:
        print("No rules found in config.")
        sys.exit(0)

    total_violations = 0

    for rule in rules:
        path_rel = rule["path"]
        label = rule.get("label", path_rel)
        forbidden = rule.get("forbidden", [])

        directory = REPO_ROOT / path_rel
        py_files = find_python_files(directory)

        if not py_files:
            if not quiet:
                print(f"[{label}] SKIP — no .py files under {path_rel}/")
            continue

        violations = []
        for py_file in py_files:
            violations.extend(scan_file(py_file, forbidden))

        if violations:
            total_violations += len(violations)
            print(f"[{label}] FAIL — {len(violations)} violation(s):")
            for v in violations:
                print(v)
            print()
        elif not quiet:
            print(f"[{label}] PASS ({len(py_files)} file(s))")

    # ── Licensing boundary rules (EPIC-L-SEAT-LEDGER-001A4) ──
    for lb in config.get("licensing_boundary", []):
        file_list = lb.get("files", [])
        allowed_models = lb.get("allowed_models", [])
        forbidden_imports = lb.get("forbidden_imports", [])
        forbidden_literals = lb.get("forbidden_literals", [])

        if not file_list:
            continue

        violations = []
        for file_rel in file_list:
            filepath = REPO_ROOT / file_rel
            if not filepath.exists():
                continue
            violations.extend(scan_licensing_boundary(
                filepath, allowed_models, forbidden_imports, forbidden_literals,
            ))

        if violations:
            total_violations += len(violations)
            print(f"[licensing-boundary] FAIL — {len(violations)} violation(s):")
            for v in violations:
                print(v)
            print()
        elif not quiet:
            print(f"[licensing-boundary] PASS ({len(file_list)} file(s))")

    if total_violations > 0:
        print(f"\n{total_violations} import boundary violation(s) total.")
        sys.exit(1)

    if not quiet:
        print("\nAll import boundaries clean.")
    sys.exit(0)


if __name__ == "__main__":
    main()
