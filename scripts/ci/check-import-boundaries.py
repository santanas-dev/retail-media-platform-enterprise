#!/usr/bin/env python3
"""Import boundary checker — ADR-014 enforcement.

Scans Python files against forbidden import rules defined in
``scripts/ci/import-boundaries.toml``.

Usage:
    python3 scripts/ci/check-import-boundaries.py          # scan all rules
    python3 scripts/ci/check-import-boundaries.py --quiet  # only print violations

Exit: 0 if clean, 1 if violations found.
"""

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
RE_IMPORT = re.compile(r"^\s*import\s+([\w.]+)")


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

        match = RE_FROM.match(line) or RE_IMPORT.match(line)
        if not match:
            continue

        imported = match.group(1)
        for pattern in forbidden_patterns:
            if re.search(pattern, imported):
                violations.append(f"  {filepath.relative_to(REPO_ROOT)}:{lineno}: imports '{imported}' (matches forbidden '{pattern}')")
                break  # one violation per line is enough

    return violations


def find_python_files(directory: Path) -> list[Path]:
    """Find all .py files under directory, excluding __pycache__."""
    if not directory.exists():
        return []
    return sorted(
        p for p in directory.rglob("*.py")
        if "__pycache__" not in str(p)
    )


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

    if total_violations > 0:
        print(f"\n{total_violations} import boundary violation(s) total.")
        sys.exit(1)

    if not quiet:
        print("\nAll import boundaries clean.")
    sys.exit(0)


if __name__ == "__main__":
    main()
