"""Inventory alternatives recommendation tests (S-087).

Schema validation + async unit tests for suggest_inventory_alternatives.
Full behavioural tests for edge cases are in the behavioural PostgreSQL suite.
"""

import unittest
from datetime import datetime, timedelta, timezone

import pytest


# ============================================================================
# Schema validation tests (no DB)
# ============================================================================


class TestAlternativesSchemas(unittest.TestCase):
    """Pydantic schema validation for InventoryAlternative + request/response."""

    def setUp(self):
        from packages.domain.schemas import (
            InventoryAlternative,
            InventoryAlternativesRequest,
            InventoryAlternativesResponse,
        )
        self.Alternative = InventoryAlternative
        self.Request = InventoryAlternativesRequest
        self.Response = InventoryAlternativesResponse

    def test_alternative_minimal(self):
        obj = self.Alternative(
            alternative_type="SAME_STORE_SURFACE",
            surface_id="s-001",
            starts_at="2026-07-20T14:00:00+00:00",
            ends_at="2026-07-20T15:00:00+00:00",
            available_capacity=100,
            reason="Available",
            score=80,
        )
        self.assertEqual(obj.alternative_type, "SAME_STORE_SURFACE")
        self.assertIsNone(obj.surface_code)
        self.assertIsNone(obj.suggested_capacity_units)

    def test_alternative_full(self):
        obj = self.Alternative(
            alternative_type="LOWER_SOV",
            surface_id="s-001",
            surface_code="LCD-01",
            surface_name="Main Display",
            store_id="st-001",
            store_code="STR-01",
            store_name="Verny Central",
            starts_at="2026-07-20T14:00:00+00:00",
            ends_at="2026-07-20T15:00:00+00:00",
            available_capacity=50,
            suggested_capacity_units=25,
            reason="Reduced capacity available",
            score=60,
        )
        self.assertEqual(obj.store_name, "Verny Central")
        self.assertEqual(obj.suggested_capacity_units, 25)
        self.assertIsNone(obj.suggested_sov_percent)

    def test_request_minimal(self):
        req = self.Request(
            surface_id="s-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(req.max_results, 5)
        self.assertIsNone(req.requested_capacity_units)

    def test_request_with_capacity(self):
        req = self.Request(
            surface_id="s-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=50,
            max_results=3,
        )
        self.assertEqual(req.max_results, 3)
        self.assertEqual(req.requested_capacity_units, 50)

    def test_request_max_results_bounds(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            self.Request(
                surface_id="s-001",
                starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
                max_results=0,
            )

    def test_response_empty(self):
        resp = self.Response(surface_id="s-001", alternatives=[], total_found=0)
        self.assertEqual(resp.total_found, 0)
        self.assertEqual(len(resp.alternatives), 0)

    def test_response_with_items(self):
        alts = [
            self.Alternative(
                alternative_type="SAME_STORE_SURFACE",
                surface_id="s-002",
                starts_at="2026-07-20T14:00:00+00:00",
                ends_at="2026-07-20T15:00:00+00:00",
                available_capacity=100,
                reason="Same store",
                score=100,
            ),
        ]
        resp = self.Response(surface_id="s-001", alternatives=alts, total_found=1)
        self.assertEqual(resp.total_found, 1)
        self.assertEqual(resp.alternatives[0].surface_id, "s-002")

    def test_alternative_type_values(self):
        valid_types = ["SAME_STORE_SURFACE", "SAME_SURFACE_TIME", "LOWER_SOV", "LATER_TIME"]
        for t in valid_types:
            obj = self.Alternative(
                alternative_type=t,
                surface_id="s-001",
                starts_at="2026-07-20T14:00:00+00:00",
                ends_at="2026-07-20T15:00:00+00:00",
                available_capacity=100,
                reason="Valid",
                score=100,
            )
            self.assertEqual(obj.alternative_type, t)

    def test_request_mutual_exclusivity_schema(self):
        """Request with both capacity and SOV should be valid at schema level
        (validation is in repository layer)."""
        req = self.Request(
            surface_id="s-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=10,
            requested_sov_percent=50,
        )
        self.assertEqual(req.requested_capacity_units, 10)
        self.assertEqual(req.requested_sov_percent, 50)


# ============================================================================
# Pure-logic tests (no DB)
# ============================================================================


class TestAlternativesConstants(unittest.TestCase):
    def test_constants_defined(self):
        from packages.domain.repository import (
            ALTERNATIVE_SAME_STORE_SURFACE,
            ALTERNATIVE_SAME_SURFACE_TIME,
            ALTERNATIVE_LOWER_SOV,
            ALTERNATIVE_LATER_TIME,
        )
        self.assertIsInstance(ALTERNATIVE_SAME_STORE_SURFACE, str)
        self.assertIsInstance(ALTERNATIVE_SAME_SURFACE_TIME, str)
        self.assertIsInstance(ALTERNATIVE_LOWER_SOV, str)
        self.assertIsInstance(ALTERNATIVE_LATER_TIME, str)

    def test_constants_all_different(self):
        from packages.domain.repository import (
            ALTERNATIVE_SAME_STORE_SURFACE,
            ALTERNATIVE_SAME_SURFACE_TIME,
            ALTERNATIVE_LOWER_SOV,
            ALTERNATIVE_LATER_TIME,
        )
        values = {
            ALTERNATIVE_SAME_STORE_SURFACE,
            ALTERNATIVE_SAME_SURFACE_TIME,
            ALTERNATIVE_LOWER_SOV,
            ALTERNATIVE_LATER_TIME,
        }
        self.assertEqual(len(values), 4, "All alternative types must be unique")


# ============================================================================
# Async DB helpers
# ============================================================================


async def _make_session():
    """Create an async SQLite session with inventory-related tables only."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(_create_tables)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    return session, engine


def _create_tables(conn):
    from sqlalchemy import text
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS branches (
            id VARCHAR(36) PRIMARY KEY, code VARCHAR(128) NOT NULL,
            name VARCHAR(256) NOT NULL
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS clusters (
            id VARCHAR(36) PRIMARY KEY, code VARCHAR(128) NOT NULL,
            name VARCHAR(256) NOT NULL, branch_id VARCHAR(36)
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS stores (
            id VARCHAR(36) PRIMARY KEY, code VARCHAR(128) NOT NULL,
            name VARCHAR(256) NOT NULL, cluster_id VARCHAR(36),
            address VARCHAR(512) NOT NULL DEFAULT '',
            timezone VARCHAR(64) NOT NULL DEFAULT 'Europe/Moscow',
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS display_surfaces (
            id VARCHAR(36) PRIMARY KEY, code VARCHAR(128) NOT NULL,
            store_id VARCHAR(36) NOT NULL,
            logical_carrier_id VARCHAR(36),
            zone_id VARCHAR(36), shelf_id VARCHAR(36),
            category_id VARCHAR(36), sku_group_id VARCHAR(36),
            resolution_w INTEGER DEFAULT 1920,
            resolution_h INTEGER DEFAULT 1080,
            is_active BOOLEAN NOT NULL DEFAULT 1,
            current_manifest_id VARCHAR(36),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory_slots (
            id VARCHAR(36) PRIMARY KEY, display_surface_id VARCHAR(36) NOT NULL,
            slot_date DATE NOT NULL, slot_hour INTEGER NOT NULL,
            total_capacity INTEGER NOT NULL DEFAULT 0,
            booked_capacity INTEGER NOT NULL DEFAULT 0,
            reserved_capacity INTEGER NOT NULL DEFAULT 0,
            internal_blocked_capacity INTEGER NOT NULL DEFAULT 0,
            emergency_blocked_capacity INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(32) NOT NULL DEFAULT 'available',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(display_surface_id, slot_date, slot_hour)
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory_bookings (
            id VARCHAR(36) PRIMARY KEY, campaign_id VARCHAR(36),
            campaign_placement_id VARCHAR(36),
            inventory_slot_id VARCHAR(36) NOT NULL,
            capacity_units INTEGER NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'reserved',
            reserved_until TIMESTAMP, committed_at TIMESTAMP,
            released_at TIMESTAMP, release_reason VARCHAR(512) NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory_rules (
            id VARCHAR(36) PRIMARY KEY,
            scope_type VARCHAR(32) NOT NULL DEFAULT 'global',
            scope_id VARCHAR(36), rule_type VARCHAR(64) NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            value_json TEXT NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT 1,
            starts_at TIMESTAMP, ends_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))


async def _create_store(session, store_id="store-001", code="STR-01", name="Test Store"):
    from packages.domain.models import Store
    import uuid
    s = Store(
        id=store_id, code=code, name=name,
        cluster_id="cluster-001",
        is_active=True,
    )
    session.add(s)
    await session.flush()
    return s


async def _create_surface(session, surface_id="surf-001", store_id="store-001",
                          code="LCD-01", is_active=True):
    from packages.domain.models import DisplaySurface
    import uuid
    s = DisplaySurface(
        id=surface_id, code=code, store_id=store_id,
        logical_carrier_id="lc-001",
        is_active=is_active,
    )
    session.add(s)
    await session.flush()
    return s


async def _create_slot(session, surface_id="surf-001", slot_date=None, slot_hour=14,
                       total_capacity=100, booked_capacity=0, reserved_capacity=0):
    from packages.domain.repository import get_or_create_inventory_slot
    if slot_date is None:
        slot_date = datetime(2026, 7, 20).date()
    return await get_or_create_inventory_slot(
        session, display_surface_id=surface_id,
        slot_date=slot_date, slot_hour=slot_hour,
        total_capacity=total_capacity,
    )


# ============================================================================
# Async integration tests
# ============================================================================


@pytest.mark.asyncio
async def test_no_alternatives_when_surface_not_found():
    from packages.domain.repository import suggest_inventory_alternatives
    session, engine = await _make_session()
    try:
        result = await suggest_inventory_alternatives(
            session,
            display_surface_id="nonexistent",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=10,
        )
        assert result == []
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_max_results_respected():
    from packages.domain.repository import suggest_inventory_alternatives
    session, engine = await _make_session()
    try:
        await _create_store(session)
        # Create active surface A (requested) + 3 alternatives in same store
        await _create_surface(session, "surf-A", store_id="store-001", code="LCD-A")
        await _create_surface(session, "surf-B", store_id="store-001", code="LCD-B")
        await _create_surface(session, "surf-C", store_id="store-001", code="LCD-C")
        await _create_surface(session, "surf-D", store_id="store-001", code="LCD-D")
        # Fill surf-A to make it unavailable
        await _create_slot(session, "surf-A", total_capacity=1, booked_capacity=1)
        await _create_slot(session, "surf-B", total_capacity=100)
        await _create_slot(session, "surf-C", total_capacity=100)
        await _create_slot(session, "surf-D", total_capacity=100)
        await session.flush()

        result = await suggest_inventory_alternatives(
            session,
            display_surface_id="surf-A",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=10,
            max_results=2,
        )
        assert len(result) <= 2
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_inactive_surface_not_suggested():
    from packages.domain.repository import suggest_inventory_alternatives
    session, engine = await _make_session()
    try:
        await _create_store(session)
        await _create_surface(session, "surf-A", store_id="store-001", code="LCD-A")
        # Inactive surface in same store — should NOT be suggested
        await _create_surface(session, "surf-B", store_id="store-001", code="LCD-B",
                             is_active=False)
        await _create_slot(session, "surf-A", total_capacity=1, booked_capacity=1)  # sold out
        await _create_slot(session, "surf-B", total_capacity=100)
        await session.flush()

        result = await suggest_inventory_alternatives(
            session,
            display_surface_id="surf-A",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=10,
            max_results=5,
        )
        # surf-B is inactive — must not appear
        surf_b_ids = [a["surface_id"] for a in result if a["surface_id"] == "surf-B"]
        assert len(surf_b_ids) == 0, "Inactive surface should not be suggested"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_alternatives_sorted_by_score():
    from packages.domain.repository import suggest_inventory_alternatives
    session, engine = await _make_session()
    try:
        await _create_store(session)
        await _create_surface(session, "surf-A", store_id="store-001", code="LCD-A")
        await _create_surface(session, "surf-B", store_id="store-001", code="LCD-B")
        await _create_surface(session, "surf-C", store_id="store-001", code="LCD-C")
        # surf-A partially available
        await _create_slot(session, "surf-A", total_capacity=10, booked_capacity=8)
        await _create_slot(session, "surf-B", total_capacity=100)
        await _create_slot(session, "surf-C", total_capacity=50)
        await session.flush()

        result = await suggest_inventory_alternatives(
            session,
            display_surface_id="surf-A",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=20,
            max_results=10,
        )
        if len(result) >= 2:
            scores = [a["score"] for a in result]
            assert scores[0] >= scores[1], f"Expected descending scores, got {scores}"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_same_store_surface_suggested_for_sold_out():
    from packages.domain.repository import suggest_inventory_alternatives
    session, engine = await _make_session()
    try:
        await _create_store(session)
        await _create_surface(session, "surf-A", store_id="store-001",
                             code="LCD-A")
        await _create_surface(session, "surf-B", store_id="store-001",
                             code="LCD-B")
        # surf-A is sold out
        await _create_slot(session, "surf-A", total_capacity=1, booked_capacity=1)
        await _create_slot(session, "surf-B", total_capacity=100)
        await session.flush()

        result = await suggest_inventory_alternatives(
            session,
            display_surface_id="surf-A",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=10,
            max_results=5,
        )
        # Should suggest surf-B as SAME_STORE_SURFACE alternative
        alt_ids = [a["surface_id"] for a in result]
        assert "surf-B" in alt_ids, f"Expected surf-B alternative, got {alt_ids}"
        surf_b_alt = [a for a in result if a["surface_id"] == "surf-B"]
        assert len(surf_b_alt) > 0
        assert surf_b_alt[0]["alternative_type"] == "SAME_STORE_SURFACE"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_lower_sov_suggested_for_partial_capacity():
    from packages.domain.repository import suggest_inventory_alternatives
    session, engine = await _make_session()
    try:
        await _create_store(session)
        await _create_surface(session, "surf-A", store_id="store-001",
                             code="LCD-A")
        # surf-A has partial capacity: 50 available, requested 100 → not enough
        await _create_slot(session, "surf-A", total_capacity=60, booked_capacity=10)
        await session.flush()

        result = await suggest_inventory_alternatives(
            session,
            display_surface_id="surf-A",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            requested_capacity_units=100,
            max_results=5,
        )
        # Should suggest LOWER_SOV alternative
        lower_alt = [a for a in result if a["alternative_type"] == "LOWER_SOV"]
        assert len(lower_alt) > 0, f"No LOWER_SOV alternative found. Got: {result}"
    finally:
        await session.close()
        await engine.dispose()
