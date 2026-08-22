#!/usr/bin/env python3
"""
Tamper tests for THEME-GUARD-001.

Creates a temporary raw hex in an admin-web page, runs the guard,
asserts the violation is detected, then cleans up.

Tests:
  1. CLEAN: current repo → 0 violations (strict exit 0)
  2. INJECT: add #ff0000 to a page → guard catches it (strict exit 1)
  3. REVERT: after cleanup → 0 violations again
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD_SCRIPT = REPO_ROOT / "scripts" / "ci" / "check-style-tokens.py"

# Target: a page file we can safely tamper with temporarily
TARGET = REPO_ROOT / "apps" / "admin-web" / "src" / "pages" / "ADSettingsPage.tsx"

passed = 0
failed = 0


def run_guard(strict=True):
    """Run the guard script. Returns (exit_code, stdout)."""
    args = [sys.executable, str(GUARD_SCRIPT)]
    if strict:
        args.append("--strict")
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    return result.returncode, result.stdout


def test(name, tamper_fn, expect_violation=True, expect_fail=True):
    """Tamper the target file, run guard, restore."""
    global passed, failed

    backup = TARGET.read_text(encoding="utf-8")

    try:
        tamper_fn()
        exit_code, stdout = run_guard(strict=True)

        if expect_violation:
            has_violation = "Violations:" in stdout and "0 violations" not in stdout
            guard_failed = exit_code != 0
            if has_violation and guard_failed:
                print(f"  ✅ PASS: {name}")
                print(f"     Guard exit={exit_code}, violations detected")
                passed += 1
            else:
                print(f"  ❌ FAIL: {name}")
                print(f"     Expected violation + exit≠0, got exit={exit_code}")
                print(f"     Output: {stdout[:300]}")
                failed += 1
        else:
            if exit_code == 0 and "0 violations" in stdout:
                print(f"  ✅ PASS: {name} (clean)")
                passed += 1
            else:
                print(f"  ❌ FAIL: {name}")
                print(f"     Expected clean + exit 0, got exit={exit_code}")
                print(f"     Output: {stdout[:300]}")
                failed += 1
    finally:
        TARGET.write_text(backup, encoding="utf-8")


print("=== THEME-GUARD-001 Tamper Tests ===\n")


# ── Test 1: Clean baseline ──
def noop():
    pass

test("Clean repo → 0 violations", noop, expect_violation=False)


# ── Test 2: Inject raw hex ──
def inject_hex():
    content = TARGET.read_text(encoding="utf-8")
    # Add a raw hex color in a style prop — should be caught
    injected = content + '\n// INJECTED-TAMPER-TEST\nconst _tamper = { color: "#ff0000" };\n'
    TARGET.write_text(injected, encoding="utf-8")

test("Inject #ff0000 → guard blocks", inject_hex, expect_violation=True)


# ── Test 3: Inject rgba (non-overlay) ──
def inject_rgba():
    content = TARGET.read_text(encoding="utf-8")
    injected = content + '\n// INJECTED-TAMPER-RGBA\nconst _tamper2 = { background: "rgba(255,0,0,0.5)" };\n'
    TARGET.write_text(injected, encoding="utf-8")

test("Inject rgba(255,0,0,0.5) → guard blocks", inject_rgba, expect_violation=True)


# ── Test 4: Allowlist entry passes ──
def inject_allowed():
    """Inject #52525b on the allowlisted line — should pass."""
    content = TARGET.read_text(encoding="utf-8")
    injected = content + '\n// This #52525b is NOT on the allowlist line, should be caught\nconst _tamper3 = { color: "#52525b" };\n'
    TARGET.write_text(injected, encoding="utf-8")

test("Inject #52525b outside allowlist → guard blocks", inject_allowed, expect_violation=True)


# ── Final: verify clean after all restores ──
exit_code, stdout = run_guard(strict=True)
if exit_code == 0:
    print(f"  ✅ PASS: Final restore → repo is clean")
    passed += 1
else:
    print(f"  ❌ FAIL: Final restore — repo not clean after tests!")
    failed += 1


print(f"\n=== Results: {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
