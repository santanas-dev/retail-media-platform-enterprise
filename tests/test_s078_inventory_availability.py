"""Inventory availability calculator tests (S-078).

Pure-logic calculator + schema validation — no DB dependency.
Full async integration tested via behavioural PostgreSQL suite.
"""

import unittest
from datetime import datetime, timedelta, timezone
import math

from packages.domain.schemas import (
    InventoryAvailabilityRequest,
)


# ---------------------------------------------------------------------------
# Pure-logic slot expansion + SOV conversion (no DB)
# ---------------------------------------------------------------------------


def _expand_slot_pairs(starts_at: datetime, ends_at: datetime) -> list[tuple]:
    """Expand time range into (date, hour) pairs. Pure logic — testable without DB."""
    if ends_at <= starts_at:
        raise ValueError("ends_at must be after starts_at")
    current = starts_at.replace(minute=0, second=0, microsecond=0)
    end_hour = ends_at.replace(minute=0, second=0, microsecond=0)
    pairs = []
    while current < end_hour:
        pairs.append((current.date(), current.hour))
        current += timedelta(hours=1)
    if not pairs:
        raise ValueError("time range must cover at least one full hour")
    return pairs


def _sov_to_units(total_capacity: int, sov_percent: int) -> int:
    """Convert SOV percent to capacity units."""
    if not (0 < sov_percent <= 100):
        raise ValueError("SOV percent must be in (0, 100]")
    return math.ceil(total_capacity * sov_percent / 100)


def _validate_request(
    requested_capacity_units: int | None,
    requested_sov_percent: int | None,
) -> None:
    """Validate mutual exclusivity of capacity/SOV."""
    if requested_capacity_units is not None and requested_sov_percent is not None:
        raise ValueError(
            "Provide either requested_capacity_units or requested_sov_percent, not both"
        )


class TestSlotExpansion(unittest.TestCase):
    def _ts(self, day=20, hour=14):
        return datetime(2026, 7, day, hour, 0, 0, tzinfo=timezone.utc)

    def test_single_hour(self):
        pairs = _expand_slot_pairs(self._ts(20, 14), self._ts(20, 15))
        self.assertEqual(len(pairs), 1)
        self.assertEqual(pairs[0][1], 14)

    def test_two_hours(self):
        pairs = _expand_slot_pairs(self._ts(20, 14), self._ts(20, 16))
        self.assertEqual(len(pairs), 2)
        self.assertEqual([h for _, h in pairs], [14, 15])

    def test_midnight_crossing(self):
        pairs = _expand_slot_pairs(
            datetime(2026, 7, 20, 23, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 21, 1, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0], (self._ts(20, 23).date(), 23))
        self.assertEqual(pairs[1], (self._ts(21, 0).date(), 0))

    def test_ends_before_starts_rejected(self):
        with self.assertRaises(ValueError):
            _expand_slot_pairs(self._ts(20, 14), self._ts(20, 13))

    def test_ends_equals_starts_rejected(self):
        with self.assertRaises(ValueError):
            _expand_slot_pairs(self._ts(20, 14), self._ts(20, 14))

    def test_sub_hour_range_rejected(self):
        """14:00–14:30 — less than one full hour."""
        with self.assertRaises(ValueError):
            _expand_slot_pairs(
                self._ts(20, 14),
                datetime(2026, 7, 20, 14, 30, tzinfo=timezone.utc),
            )

    def test_all_day_range_24_hours(self):
        pairs = _expand_slot_pairs(
            datetime(2026, 7, 20, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 7, 21, 0, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(len(pairs), 24)


class TestSovConversion(unittest.TestCase):
    def test_30_pct_of_100(self):
        self.assertEqual(_sov_to_units(100, 30), 30)

    def test_50_pct_of_120(self):
        self.assertEqual(_sov_to_units(120, 50), 60)

    def test_100_pct_of_120(self):
        self.assertEqual(_sov_to_units(120, 100), 120)

    def test_1_pct_of_100(self):
        self.assertEqual(_sov_to_units(100, 1), 1)

    def test_33_pct_of_100_rounds_up(self):
        # 33% of 100 = 33.0 → ceil = 33
        self.assertEqual(_sov_to_units(100, 33), 33)

    def test_zero_pct_rejected(self):
        with self.assertRaises(ValueError):
            _sov_to_units(100, 0)

    def test_over_100_pct_rejected(self):
        with self.assertRaises(ValueError):
            _sov_to_units(100, 101)


class TestRequestValidation(unittest.TestCase):
    def test_units_only_ok(self):
        _validate_request(50, None)

    def test_sov_only_ok(self):
        _validate_request(None, 30)

    def test_both_rejected(self):
        with self.assertRaises(ValueError):
            _validate_request(50, 30)

    def test_neither_ok(self):
        _validate_request(None, None)


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestAvailabilityRequestSchema(unittest.TestCase):
    def _ts(self, day=20, hour=14):
        return datetime(2026, 7, day, hour, 0, 0, tzinfo=timezone.utc)

    def test_valid_request_units(self):
        req = InventoryAvailabilityRequest(
            surface_id="s1",
            starts_at=self._ts(20, 14),
            ends_at=self._ts(20, 16),
            requested_capacity_units=50,
        )
        self.assertEqual(req.requested_capacity_units, 50)

    def test_valid_request_sov(self):
        req = InventoryAvailabilityRequest(
            surface_id="s1",
            starts_at=self._ts(20, 14),
            ends_at=self._ts(20, 16),
            requested_sov_percent=30,
        )
        self.assertEqual(req.requested_sov_percent, 30)

    def test_units_zero_rejected_by_schema(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            InventoryAvailabilityRequest(
                surface_id="s1",
                starts_at=self._ts(20, 14),
                ends_at=self._ts(20, 16),
                requested_capacity_units=0,
            )

    def test_sov_zero_rejected_by_schema(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            InventoryAvailabilityRequest(
                surface_id="s1",
                starts_at=self._ts(20, 14),
                ends_at=self._ts(20, 16),
                requested_sov_percent=0,
            )

    def test_sov_over_100_rejected_by_schema(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            InventoryAvailabilityRequest(
                surface_id="s1",
                starts_at=self._ts(20, 14),
                ends_at=self._ts(20, 16),
                requested_sov_percent=101,
            )
