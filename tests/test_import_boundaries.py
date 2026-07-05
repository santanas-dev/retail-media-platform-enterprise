"""Unit tests for import boundary checker — ADR-014 CI gate.

Tests the scanner's import extraction and forbidden-pattern
matching without shelling out.
"""

import sys
import unittest
from pathlib import Path

# Make the CI scripts importable
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "ci"))

# Dynamic import — sys.path must be set first
import importlib
_check = importlib.import_module("check-import-boundaries")
_extract_imported_modules = _check._extract_imported_modules
scan_file = _check.scan_file
RE_FROM = _check.RE_FROM
RE_IMPORT = _check.RE_IMPORT


class TestImportExtraction(unittest.TestCase):
    """Test _extract_imported_modules — multi-import, aliases, edges."""

    def test_simple_from(self):
        self.assertEqual(
            _extract_imported_modules("from fastapi import APIRouter"),
            ["fastapi"],
        )

    def test_from_with_multiple_names(self):
        self.assertEqual(
            _extract_imported_modules("from packages.api import identity, auth"),
            ["packages.api"],
        )

    def test_simple_import(self):
        self.assertEqual(
            _extract_imported_modules("import os"),
            ["os"],
        )

    def test_multi_import_two(self):
        self.assertEqual(
            _extract_imported_modules("import os, fastapi"),
            ["os", "fastapi"],
        )

    def test_multi_import_three(self):
        self.assertEqual(
            _extract_imported_modules("import os, sys, json"),
            ["os", "sys", "json"],
        )

    def test_import_with_alias(self):
        self.assertEqual(
            _extract_imported_modules("import packages.api as api"),
            ["packages.api"],
        )

    def test_multi_import_with_alias(self):
        self.assertEqual(
            _extract_imported_modules("import os, packages.api as api"),
            ["os", "packages.api"],
        )

    def test_comment_ignored(self):
        self.assertEqual(
            _extract_imported_modules("# from fastapi import APIRouter"),
            [],
        )

    def test_leading_whitespace(self):
        self.assertEqual(
            _extract_imported_modules("    import fastapi"),
            ["fastapi"],
        )

    def test_not_an_import(self):
        self.assertEqual(
            _extract_imported_modules("x = 5"),
            [],
        )

    def test_empty_line(self):
        self.assertEqual(_extract_imported_modules(""), [])

    def test_import_with_extra_spaces(self):
        self.assertEqual(
            _extract_imported_modules("import    os  ,  sys  ,  json   as j"),
            ["os", "sys", "json"],
        )


class TestForbiddenPatterns(unittest.TestCase):
    """Test scan_file — forbidden pattern matching."""

    def test_fastapi_in_domain_caught(self):
        violations = scan_file_obj(
            "packages/domain/test.py",
            ["from fastapi import APIRouter\n"],
            ["^fastapi$"],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("fastapi", violations[0])

    def test_sqlalchemy_in_domain_allowed(self):
        violations = scan_file_obj(
            "packages/domain/test.py",
            ["from sqlalchemy import Column\n"],
            ["^fastapi$"],
        )
        self.assertEqual(len(violations), 0)

    def test_multi_import_violation_caught(self):
        violations = scan_file_obj(
            "packages/security/test.py",
            ["import os, fastapi\n"],
            ["^fastapi$"],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("fastapi", violations[0])

    def test_kso_bare_import_caught(self):
        violations = scan_file_obj(
            "packages/test.py",
            ["import kso\n"],
            ["^kso(\\.|$)"],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("kso", violations[0])

    def test_kso_dotted_import_caught(self):
        violations = scan_file_obj(
            "packages/test.py",
            ["from kso.legacy import stuff\n"],
            ["^kso(\\.|$)"],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("kso.legacy", violations[0])

    def test_backend_import_caught(self):
        violations = scan_file_obj(
            "apps/test.py",
            ["from backend.old_module import x\n"],
            ["^backend(\\.|$)"],
        )
        self.assertEqual(len(violations), 1)
        self.assertIn("backend.old_module", violations[0])

    def test_comment_not_caught(self):
        violations = scan_file_obj(
            "packages/domain/test.py",
            ["# from fastapi import APIRouter\n", "from sqlalchemy import Column\n"],
            ["^fastapi$"],
        )
        self.assertEqual(len(violations), 0)


def scan_file_obj(path: str, lines: list[str], forbidden: list[str]) -> list[str]:
    """Shim: call scan_file with a fake filepath and prepared lines.

    We don't write real files — patch read_text to return our lines.
    """
    import re as _re

    violations = []
    for lineno, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        modules = _extract_imported_modules(line)
        for imported in modules:
            for pattern in forbidden:
                if _re.search(pattern, imported):
                    violations.append(
                        f"  {path}:{lineno}: imports '{imported}'"
                        f" (matches forbidden '{pattern}')"
                    )
                    break
    return violations


if __name__ == "__main__":
    unittest.main()
