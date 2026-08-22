#!/usr/bin/env python3
"""A1b: Replace #fff by context + low-count exact-match tokens."""

import re, sys, os

BASE = "apps/admin-web/src"
DIRS = ["pages", "components"]

FILES = []
for d in DIRS:
    for root, _, files in os.walk(os.path.join(BASE, d)):
        for f in files:
            if f.endswith((".tsx", ".ts")):
                FILES.append(os.path.join(root, f))

changes = 0
for filepath in FILES:
    with open(filepath, "r") as f:
        content = f.read()
    original = content

    # --- Phase 1a: color: "#fff" → text-inverse ---
    # Match: color: "#fff"  or  color: "#fff" (with any spacing)
    content = re.sub(
        r'\bcolor:\s*"#fff"',
        'color: "var(--rmp-text-inverse)"',
        content,
    )

    # --- Phase 1b: background: "#fff" → bg-surface ---
    # Only standalone background: "#fff" (not in ternary with other tokens)
    content = re.sub(
        r'\bbackground:\s*"#fff"(?!\s*\})',
        'background: "var(--rmp-bg-surface)"',
        content,
    )

    # --- Phase 2: low-count exact matches ---
    content = content.replace('"#eff6ff"', '"var(--rmp-primary-50)"')
    content = content.replace('"#1e40af"', '"var(--rmp-primary-700)"')
    content = content.replace('"#fffbeb"', '"var(--rmp-warning-50)"')
    content = content.replace('"#fef3c7"', '"var(--rmp-warning-100)"')
    content = content.replace('"#d97706"', '"var(--rmp-warning-600)"')

    if content != original:
        with open(filepath, "w") as f:
            f.write(content)
        count = 1 if "#fff" in original else 0
        count += original.count('"#eff6ff"')
        count += original.count('"#1e40af"')
        count += original.count('"#fffbeb"')
        count += original.count('"#fef3c7"')
        count += original.count('"#d97706"')
        changes += count
        print(f"  {filepath}: {count} replacement(s)")

print(f"\nTotal replacements: {changes}")
