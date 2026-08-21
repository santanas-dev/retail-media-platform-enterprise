"""EPIC-L-SEAT-LEDGER-001A3 — unit exact-peak matrix (pure, no DB).

Covers the canonical half-open monthly-peak policy without a database:
the 10-case matrix from SCOPE E. The DB-query path (``peak_seats_for_month``)
is proven separately in ``tests/behavioral/test_license_decommission.py``.
"""

from datetime import datetime, timezone

import pytest

from packages.domain.licensing_repository import (
    _month_bounds,
    _peak_from_intervals,
)

UTC = timezone.utc

# Month window under test: 2026-08-01 .. 2026-09-01 (UTC).
MS = datetime(2026, 8, 1, tzinfo=UTC)
NMS = datetime(2026, 9, 1, tzinfo=UTC)


def dt(day: int, hour: int = 0) -> datetime:
    return datetime(2026, 8, day, hour, tzinfo=UTC)


def peak(intervals) -> int:
    return _peak_from_intervals(intervals, MS, NMS)


def test_one_seat_one_day():
    assert peak([(dt(1), dt(2))]) == 1


def test_three_overlapping_intervals():
    assert peak([
        (dt(1), dt(10)),
        (dt(2), dt(11)),
        (dt(3), dt(12)),
    ]) == 3


def test_sequential_non_overlapping():
    # [1,5), [5,10), [10,15) — each ends exactly when the next starts.
    assert peak([
        (dt(1), dt(5)),
        (dt(5), dt(10)),
        (dt(10), dt(15)),
    ]) == 1


def test_interval_crossing_month_start():
    # Reserved in July, still open into August → counted from month start.
    before = datetime(2026, 7, 20, tzinfo=UTC)
    assert peak([(before, dt(5))]) == 1


def test_release_exactly_at_month_start_excluded():
    # [before, month_start) clips to zero length → excluded.
    before = datetime(2026, 7, 20, tzinfo=UTC)
    assert peak([(before, MS)]) == 0


def test_reserve_exactly_at_next_month_start_excluded():
    # [next_month_start, later) clips to zero length → excluded.
    assert peak([(NMS, datetime(2026, 9, 5, tzinfo=UTC))]) == 0


def test_open_interval_counts_to_month_end():
    # released_at is None → occupied through next_month_start.
    assert peak([(dt(10), None)]) == 1


def test_release_and_reserve_same_instant_no_false_peak():
    # Seat A released at T, seat B reserved at T — the seat passes hands.
    t = dt(10, 12)
    assert peak([
        (dt(1), t),
        (t, dt(20)),
    ]) == 1


def test_no_intervals():
    assert peak([]) == 0


@pytest.mark.parametrize(
    "year,month",
    [
        (0, 1),
        (10000, 1),
        (2026, 0),
        (2026, 13),
        (2026, -1),
        (2026, 2.5),
        ("2026", 8),
    ],
)
def test_invalid_month_bounds_raises(year, month):
    with pytest.raises(ValueError):
        _month_bounds(year, month, UTC)


def test_month_bounds_december_rollover():
    start, next_start = _month_bounds(2026, 12, UTC)
    assert start == datetime(2026, 12, 1, tzinfo=UTC)
    assert next_start == datetime(2027, 1, 1, tzinfo=UTC)
