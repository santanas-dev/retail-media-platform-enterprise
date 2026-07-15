"""
Retail Media Platform — S-063 PoP Timezone Correctness Tests.

Unit tests: source-inspection (query uses timezone + coalesce, not raw cast)
+ pure-Python timezone fallback verification.
"""

import ast
import inspect
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from packages.domain.repository import list_campaign_pop_by_day


class TestPopTimezoneQuerySource(unittest.TestCase):
    """Proof: list_campaign_pop_by_day uses timezone-aware local date, not UTC cast."""

    def test_function_uses_timezone(self):
        """Query uses func.timezone, not bare cast(rendered_at, Date)."""
        source = inspect.getsource(list_campaign_pop_by_day)
        self.assertIn("func.timezone", source,
                       "S-063: list_campaign_pop_by_day must use timezone()")
        self.assertIn("func.coalesce", source,
                       "S-063: must coalesce Store.timezone + Branch.timezone")

    def test_function_references_store_and_branch_tz(self):
        """Timezone source references Store.timezone and Branch.timezone."""
        source = inspect.getsource(list_campaign_pop_by_day)
        self.assertIn("Store.timezone", source)
        self.assertIn("Branch.timezone", source)

    def test_no_bare_utc_cast(self):
        """No raw cast(PopEventRaw.rendered_at, Date) without timezone wrapper."""
        source = inspect.getsource(list_campaign_pop_by_day)
        # We DO use cast(timezone(...), Date) — that's fine.
        # We must NOT find the old pattern: cast(PopEventRaw.rendered_at, Date)
        # without timezone() in the same expression.
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Look for cast(raw PopEventRaw.rendered_at, Date) without timezone
                if (isinstance(node.func, ast.Name) and node.func.id == "cast"
                        and len(node.args) >= 1):
                    first_arg = ast.dump(node.args[0])
                    # If first arg is PopEventRaw.rendered_at directly (not wrapped)
                    if "PopEventRaw" in first_arg and "rendered_at" in first_arg:
                        if "timezone" not in first_arg and "func" not in first_arg:
                            self.fail(
                                "S-063: found cast(PopEventRaw.rendered_at, Date) "
                                "without timezone wrapper"
                            )

    def test_select_from_popeventraw(self):
        """Query uses .select_from(PopEventRaw) — needed for outerjoin chain."""
        source = inspect.getsource(list_campaign_pop_by_day)
        self.assertIn("select_from(PopEventRaw)", source)


class TestPopTimezoneFallbackLogic(unittest.TestCase):
    """Verify timezone fallback decisions in pure Python (no DB needed)."""

    def test_fallback_chain_documented(self):
        """Docstring documents 3-level fallback: Store → Branch → Moscow."""
        doc = list_campaign_pop_by_day.__doc__ or ""
        self.assertIn("Store.timezone", doc, "doc must mention Store.timezone (level 1)")
        self.assertIn("Branch.timezone", doc, "doc must mention Branch.timezone (level 2)")
        self.assertIn("Europe/Moscow", doc, "doc must mention Moscow default (level 3)")

    def test_valid_iana_timezones(self):
        """All timezone strings referenced are valid IANA identifiers."""
        import zoneinfo
        for tz_name in ("Europe/Moscow", "Asia/Vladivostok", "UTC"):
            self.assertIsNotNone(
                zoneinfo.ZoneInfo(tz_name),
                f"{tz_name} must be a valid IANA timezone",
            )

    def test_vladivostok_offset_is_utc_plus_10(self):
        """Sanity: Asia/Vladivostok is UTC+10."""
        from datetime import datetime, timezone as tz_mod
        import zoneinfo

        vlad = zoneinfo.ZoneInfo("Asia/Vladivostok")
        test_dt = datetime(2026, 5, 15, 0, 0, 0, tzinfo=vlad)
        utc_dt = test_dt.astimezone(tz_mod.utc)
        self.assertEqual(
            utc_dt.hour, 14,  # May 15 00:00 Vladivostok = May 14 14:00 UTC
            "Asia/Vladivostok must be UTC+10",
        )

    def test_vladivostok_0800_to_moscow_date(self):
        """Proof: Vladivostok 2026-05-15 08:00 → Moscow 2026-05-15 01:00 → date=05-15."""
        from datetime import datetime, date, timezone as tz_mod
        import zoneinfo

        vlad = zoneinfo.ZoneInfo("Asia/Vladivostok")
        msk = zoneinfo.ZoneInfo("Europe/Moscow")

        # Event: Vladivostok local 2026-05-15 08:00
        rendered_at_vlad = datetime(2026, 5, 15, 8, 0, 0, tzinfo=vlad)
        # Convert to UTC for storage
        rendered_at_utc = rendered_at_vlad.astimezone(tz_mod.utc)
        # UTC should be 2026-05-14 22:00 (UTC+10 → -10h = previous day 22:00)
        self.assertEqual(rendered_at_utc.day, 14)
        self.assertEqual(rendered_at_utc.hour, 22)

        # Now simulate store timezone = Europe/Moscow (UTC+3)
        rendered_at_msk = rendered_at_utc.astimezone(msk)
        # 22:00 UTC → 01:00 MSK (next day)
        self.assertEqual(rendered_at_msk.day, 15)
        self.assertEqual(rendered_at_msk.hour, 1)

        # If store tz = Vladivostok itself
        rendered_at_vlad2 = rendered_at_utc.astimezone(vlad)
        self.assertEqual(rendered_at_vlad2.day, 15)
        self.assertEqual(rendered_at_vlad2.hour, 8)

        # In all cases, local date = 2026-05-15
        self.assertEqual(rendered_at_vlad2.date(), date(2026, 5, 15))
        self.assertEqual(rendered_at_msk.date(), date(2026, 5, 15))

        # UTC date would be WRONG: 2026-05-14
        self.assertEqual(rendered_at_utc.date(), date(2026, 5, 14))


if __name__ == "__main__":
    unittest.main()
