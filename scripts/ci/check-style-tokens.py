#!/usr/bin/env python3
"""
Style-Token Guard — THEME-GUARD-001.

Scans apps/admin-web/src/{pages,components} for raw color literals
(#hex, rgb, rgba, hsl, hsla) and blocks them unless they appear in
the documented allowlist.

Modes:
  --audit   (default) Print violations, exit 0 (non-blocking).
  --strict  Exit 1 if any violation found (blocking CI gate).

Usage:
  python3 scripts/ci/check-style-tokens.py          # audit mode
  python3 scripts/ci/check-style-tokens.py --strict # blocking CI
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# ── Scanned directories ────────────────────────────────────────────────────
SCAN_DIRS = [
    REPO_ROOT / "apps" / "admin-web" / "src" / "pages",
    REPO_ROOT / "apps" / "admin-web" / "src" / "components",
]

# ── Excluded files (entire file whitelisted) ───────────────────────────────
EXCLUDED_FILES = {
    "ErrorBoundary.tsx",  # Fallback component — must work pre-CSS
}

# ── Per-line allowlist (file_basename: {line_number: {hex_value, ...}}) ─────
LINE_ALLOWLIST = {
    "CampaignDetailPage.tsx": {
        1730: {"#52525b"},  # Creative-upload filename — single-use, no token group
    },
}

# ── Patterns ────────────────────────────────────────────────────────────────
# Hex: #RGB or #RRGGBB (word-bounded to avoid matching CSS var hex in tokens.css)
HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})\b")

# CSS color functions: rgb(…), rgba(…), hsl(…), hsla(…)
COLOR_FUNC_RE = re.compile(
    r"\b(?:rgb|rgba|hsl|hsla)\s*\(\s*[\d.,%\s]+\s*\)",
    re.IGNORECASE,
)

# Token reference: check if line already uses var(--rmp-*)
TOKEN_RE = re.compile(r"var\(--rmp-")

# ── Helpers ─────────────────────────────────────────────────────────────────

def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    """Scan a file for raw color violations. Returns [(line_no, raw_literal, hint), ...]."""
    violations = []
    file_basename = filepath.name

    try:
        lines = filepath.read_text(encoding="utf-8").splitlines()
    except Exception:
        return violations

    line_allowlist = LINE_ALLOWLIST.get(file_basename, {})

    for i, line in enumerate(lines, start=1):
        # Check per-line allowlist — skip entire line if it contains only allowed hex
        allowed_on_line = line_allowlist.get(i, set())
        if allowed_on_line:
            line_hexes = set(HEX_RE.findall(line.lower()))
            if line_hexes.issubset(allowed_on_line):
                # Line has only allowed hex + maybe tokens → pass
                # But must verify no OTHER violations
                non_allowed = line_hexes - allowed_on_line
                if not non_allowed:
                    # Skip the hex check for allowed values, but still check color functions
                    pass

        # ── Hex check ──
        for m in HEX_RE.finditer(line):
            hex_val = m.group().lower()
            # Skip if this hex is on the line allowlist
            if hex_val in allowed_on_line:
                continue
            # Skip inline token definitions like #RRGGBB; (tokens.css is excluded anyway)
            violations.append((
                i,
                m.group(),
                "use var(--rmp-*) design token",
            ))

        # ── Color function check ──
        for m in COLOR_FUNC_RE.finditer(line):
            func_call = m.group()
            # If line already has a token var(...), the rgb might be inside it — skip
            if TOKEN_RE.search(line):
                # The token usage is fine; color function after a var() is suspicious
                # but could be e.g. `box-shadow: ... rgba(...)` mixed with var().
                # Do a narrow check: if the exact func call is right after var(token)
                # it's likely intentional shadow/focus styling.
                # We flag it anyway because the guard is conservative.
                pass
            violations.append((
                i,
                func_call,
                "use var(--rmp-*) design token",
            ))

    return violations


def scan_all() -> dict[str, list[tuple[int, str, str]]]:
    """Scan all relevant files. Returns {rel_path: [(line, literal, hint), ...]}."""
    all_violations = {}

    for scan_dir in SCAN_DIRS:
        if not scan_dir.is_dir():
            continue
        for tsx_file in sorted(scan_dir.rglob("*.tsx")):
            if tsx_file.name in EXCLUDED_FILES:
                continue
            violations = scan_file(tsx_file)
            if violations:
                rel = str(tsx_file.relative_to(REPO_ROOT))
                all_violations[rel] = violations

    return all_violations


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Style-token guard — block raw color literals in admin-web"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 on any violation (blocking CI gate)",
    )
    args = parser.parse_args()

    violations = scan_all()
    total = sum(len(v) for v in violations.values())

    print("=== Style-Token Guard (THEME-GUARD-001) ===")
    print(f"  Scanned dirs: {len(SCAN_DIRS)}")
    print(f"  Violations:   {total}")
    print()

    if violations:
        print("--- Violations ---")
        for filepath, file_violations in sorted(violations.items()):
            print(f"  {filepath}:")
            for line_no, literal, hint in file_violations:
                print(f"    L{line_no:>4}: {literal}  ← {hint}")
        print()
        print(f"SUMMARY: {total} raw color literal(s) in admin-web pages/components.")
        print("Replace with var(--rmp-*) tokens from apps/admin-web/src/styles/tokens.css.")
        print(f"Allowlist: ErrorBoundary.tsx (pre-CSS fallback), "
              f"CampaignDetailPage.tsx:1730 (#52525b).")
    else:
        print("SUMMARY: 0 violations — admin-web is token-clean.")

    if args.strict and total > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
