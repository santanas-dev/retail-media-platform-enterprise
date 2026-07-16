"""Inventory reservation lifecycle tests (S-079).

Schema validation tests (no DB) + async integration tests for
reserve/commit/release/expire with SQLite in-memory.
"""

import unittest
from datetime import datetime, timedelta, timezone

import pytest


# ============================================================================
# Schema validation tests (no DB)
# ============================================================================


class TestReservationSchemas(unittest.TestCase):
    """Pydantic schema validation for CampaignInventoryReservationOut."""

    def setUp(self):
        from packages.domain.schemas import CampaignInventoryReservationOut
        self.Schema = CampaignInventoryReservationOut

    def test_valid_booking_schema(self):
        obj = self.Schema(
            booking_id="b-001", campaign_id="c-001", placement_id="p-001",
            slot_id="s-001", capacity_units=10, status="reserved",
            reserved_until="2026-07-20T14:00:00+00:00",
            created_at="2026-07-20T12:00:00+00:00",
        )
        self.assertEqual(obj.booking_id, "b-001")
        self.assertEqual(obj.status, "reserved")

    def test_minimal_schema(self):
        obj = self.Schema(booking_id="b-001", slot_id="s-001",
                          capacity_units=5, status="committed")
        self.assertEqual(obj.capacity_units, 5)

    def test_optional_fields_default(self):
        obj = self.Schema(booking_id="b-001", slot_id="s-001",
                          capacity_units=1, status="reserved")
        self.assertIsNone(obj.campaign_id)
        self.assertEqual(obj.release_reason, "")

    def test_status_values(self):
        for status in ("reserved", "committed", "released", "expired"):
            obj = self.Schema(booking_id="b-001", slot_id="s-001",
                              capacity_units=1, status=status)
            self.assertEqual(obj.status, status)


class TestReservationsResponseSchema(unittest.TestCase):

    def setUp(self):
        from packages.domain.schemas import (
            CampaignInventoryReservationOut,
            CampaignInventoryReservationsResponse,
        )
        self.Item = CampaignInventoryReservationOut
        self.Response = CampaignInventoryReservationsResponse

    def test_empty_list(self):
        resp = self.Response(campaign_id="c-001", reservations=[], total=0)
        self.assertEqual(resp.total, 0)

    def test_with_items(self):
        items = [
            self.Item(booking_id="b-1", slot_id="s-1", capacity_units=5, status="reserved"),
            self.Item(booking_id="b-2", slot_id="s-2", capacity_units=3, status="committed"),
        ]
        resp = self.Response(campaign_id="c-001", reservations=items, total=2)
        self.assertEqual(resp.total, 2)
        self.assertEqual(resp.reservations[0].booking_id, "b-1")


# ============================================================================
# Async DB helpers
# ============================================================================


async def _make_session():
    """Create an async SQLite session with inventory tables only."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    # Create only inventory tables to avoid JSONB column issues
    # (outbox_events uses JSONB which SQLite can't handle)
    async with engine.begin() as conn:
        await conn.run_sync(_create_inventory_tables)

    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    session = factory()
    return session, engine


def _create_inventory_tables(conn):
    """Create inventory tables manually to avoid pulling in JSONB tables."""
    from sqlalchemy import text
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory_slots (
            id VARCHAR(36) PRIMARY KEY,
            display_surface_id VARCHAR(36) NOT NULL,
            slot_date DATE NOT NULL,
            slot_hour INTEGER NOT NULL,
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
            id VARCHAR(36) PRIMARY KEY,
            campaign_id VARCHAR(36),
            campaign_placement_id VARCHAR(36),
            inventory_slot_id VARCHAR(36) NOT NULL REFERENCES inventory_slots(id),
            capacity_units INTEGER NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'reserved',
            reserved_until TIMESTAMP,
            committed_at TIMESTAMP,
            released_at TIMESTAMP,
            release_reason VARCHAR(512) NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS inventory_rules (
            id VARCHAR(36) PRIMARY KEY,
            scope_type VARCHAR(32) NOT NULL DEFAULT 'global',
            scope_id VARCHAR(36),
            rule_type VARCHAR(64) NOT NULL,
            priority INTEGER NOT NULL DEFAULT 100,
            value_json TEXT NOT NULL DEFAULT '{}',
            is_active BOOLEAN NOT NULL DEFAULT 1,
            starts_at TIMESTAMP,
            ends_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """))


async def _create_slot(session, surface_id="surf-001", slot_date=None,
                       slot_hour=14, total_capacity=100):
    from packages.domain.repository import get_or_create_inventory_slot
    if slot_date is None:
        slot_date = datetime(2026, 7, 20).date()
    return await get_or_create_inventory_slot(
        session, display_surface_id=surface_id,
        slot_date=slot_date, slot_hour=slot_hour,
        total_capacity=total_capacity,
    )


async def _count_bookings(session, placement_id):
    from sqlalchemy import select
    from packages.domain.models import InventoryBooking
    result = await session.execute(
        select(InventoryBooking).where(
            InventoryBooking.campaign_placement_id == placement_id,
        )
    )
    return result.scalars().all()


# ============================================================================
# Reserve tests
# ============================================================================


@pytest.mark.asyncio
async def test_reserve_creates_bookings():
    from packages.domain.repository import reserve_inventory_for_placement
    session, engine = await _make_session()
    try:
        await _create_slot(session)
        await session.flush()
        result = await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 16, 0, tzinfo=timezone.utc),
            capacity_units=10,
        )
        assert result["reserved"] is True
        assert result["bookings_created"] == 2
        await session.flush()

        bookings = await _count_bookings(session, "p-001")
        assert len(bookings) == 2
        for b in bookings:
            assert b.status == "reserved"
            assert b.capacity_units == 10
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_insufficient_capacity_rejected():
    from packages.domain.repository import reserve_inventory_for_placement
    session, engine = await _make_session()
    try:
        await _create_slot(session, total_capacity=5)
        await session.flush()
        with pytest.raises(ValueError, match="Insufficient capacity"):
            await reserve_inventory_for_placement(
                session, campaign_id="c-001", placement_id="p-001",
                display_surface_id="surf-001",
                starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
                ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
                capacity_units=10,
            )
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_idempotent():
    from packages.domain.repository import reserve_inventory_for_placement
    session, engine = await _make_session()
    try:
        await _create_slot(session)
        await session.flush()
        args = dict(
            session=session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=10,
        )
        r1 = await reserve_inventory_for_placement(**args)
        r2 = await reserve_inventory_for_placement(**args)
        assert r1["bookings_created"] == 1
        assert r2["bookings_created"] == 0
        assert r2["bookings_reused"] == 1
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_consumes_capacity():
    from packages.domain.repository import reserve_inventory_for_placement
    session, engine = await _make_session()
    try:
        slot = await _create_slot(session, total_capacity=100)
        await session.flush()
        assert slot.available_capacity == 100

        await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=30,
        )
        await session.flush()
        await session.refresh(slot)
        assert slot.reserved_capacity == 30
        assert slot.available_capacity == 70
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_reserve_sov_percent():
    from packages.domain.repository import reserve_inventory_for_placement
    session, engine = await _make_session()
    try:
        await _create_slot(session, total_capacity=200)
        await session.flush()
        result = await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            sov_percent=25,
        )
        assert result["bookings_created"] == 1
        bookings = await _count_bookings(session, "p-001")
        assert bookings[0].capacity_units == 50
    finally:
        await session.close()
        await engine.dispose()


# ============================================================================
# Commit tests
# ============================================================================


@pytest.mark.asyncio
async def test_commit_moves_capacity():
    from packages.domain.repository import (
        reserve_inventory_for_placement, commit_inventory_for_campaign,
    )
    session, engine = await _make_session()
    try:
        slot = await _create_slot(session, total_capacity=100)
        await session.flush()
        await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=40,
        )
        await session.flush()
        await session.refresh(slot)
        assert slot.reserved_capacity == 40

        committed = await commit_inventory_for_campaign(session, "c-001")
        assert committed == 1
        await session.flush()
        await session.refresh(slot)
        assert slot.reserved_capacity == 0
        assert slot.booked_capacity == 40
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_commit_no_reservations():
    from packages.domain.repository import commit_inventory_for_campaign
    session, engine = await _make_session()
    try:
        committed = await commit_inventory_for_campaign(session, "nonexistent")
        assert committed == 0
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_commit_updates_booking_status():
    from packages.domain.repository import (
        reserve_inventory_for_placement, commit_inventory_for_campaign,
    )
    session, engine = await _make_session()
    try:
        await _create_slot(session)
        await session.flush()
        await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=10,
        )
        await session.flush()
        await commit_inventory_for_campaign(session, "c-001")
        await session.flush()
        bookings = await _count_bookings(session, "p-001")
        assert bookings[0].status == "committed"
        assert bookings[0].committed_at is not None
    finally:
        await session.close()
        await engine.dispose()


# ============================================================================
# Release tests
# ============================================================================


@pytest.mark.asyncio
async def test_release_reserved():
    from packages.domain.repository import (
        reserve_inventory_for_placement, release_inventory_for_campaign,
    )
    session, engine = await _make_session()
    try:
        slot = await _create_slot(session, total_capacity=100)
        await session.flush()
        await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=30,
        )
        await session.flush()
        await session.refresh(slot)
        assert slot.reserved_capacity == 30

        released = await release_inventory_for_campaign(session, "c-001", "test")
        assert released == 1
        await session.flush()
        await session.refresh(slot)
        assert slot.reserved_capacity == 0
        assert slot.available_capacity == 100
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_release_committed():
    from packages.domain.repository import (
        reserve_inventory_for_placement, commit_inventory_for_campaign,
        release_inventory_for_campaign,
    )
    session, engine = await _make_session()
    try:
        slot = await _create_slot(session)
        await session.flush()
        await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=20,
        )
        await session.flush()
        await commit_inventory_for_campaign(session, "c-001")
        await session.flush()
        await session.refresh(slot)
        assert slot.booked_capacity == 20

        released = await release_inventory_for_campaign(session, "c-001")
        assert released == 1
        await session.flush()
        await session.refresh(slot)
        assert slot.booked_capacity == 0
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_release_sets_status():
    from packages.domain.repository import (
        reserve_inventory_for_placement, release_inventory_for_campaign,
    )
    session, engine = await _make_session()
    try:
        await _create_slot(session)
        await session.flush()
        await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=10,
        )
        await session.flush()
        await release_inventory_for_campaign(session, "c-001", "rejected")
        await session.flush()
        bookings = await _count_bookings(session, "p-001")
        assert bookings[0].status == "released"
        assert bookings[0].release_reason == "rejected"
    finally:
        await session.close()
        await engine.dispose()


# ============================================================================
# Expire tests
# ============================================================================


@pytest.mark.asyncio
async def test_expire_past_ttl():
    from packages.domain.repository import expire_inventory_reservations
    from packages.domain.models import InventoryBooking
    session, engine = await _make_session()
    try:
        slot = await _create_slot(session, total_capacity=100)
        await session.flush()
        past = datetime.now(timezone.utc) - timedelta(hours=25)
        booking = InventoryBooking(
            campaign_id="c-old", campaign_placement_id="p-old",
            inventory_slot_id=slot.id, capacity_units=15,
            status="reserved", reserved_until=past,
        )
        session.add(booking)
        slot.reserved_capacity = 15
        await session.flush()
        await session.refresh(slot)
        assert slot.reserved_capacity == 15

        expired = await expire_inventory_reservations(session)
        assert expired == 1
        await session.flush()
        await session.refresh(slot)
        assert slot.reserved_capacity == 0
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_no_expire_future_ttl():
    from packages.domain.repository import expire_inventory_reservations
    from packages.domain.models import InventoryBooking
    session, engine = await _make_session()
    try:
        slot = await _create_slot(session)
        await session.flush()
        future = datetime.now(timezone.utc) + timedelta(hours=10)
        booking = InventoryBooking(
            campaign_id="c-future", inventory_slot_id=slot.id,
            capacity_units=5, status="reserved", reserved_until=future,
        )
        session.add(booking)
        slot.reserved_capacity = 5
        await session.flush()
        expired = await expire_inventory_reservations(session)
        assert expired == 0
    finally:
        await session.close()
        await engine.dispose()


# ============================================================================
# Get reservations tests
# ============================================================================


@pytest.mark.asyncio
async def test_get_reservations_empty():
    from packages.domain.repository import get_inventory_reservations_for_campaign
    session, engine = await _make_session()
    try:
        result = await get_inventory_reservations_for_campaign(session, "none")
        assert result == []
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_reservations_returns_bookings():
    from packages.domain.repository import (
        reserve_inventory_for_placement,
        get_inventory_reservations_for_campaign,
    )
    session, engine = await _make_session()
    try:
        await _create_slot(session)
        await session.flush()
        await reserve_inventory_for_placement(
            session, campaign_id="c-001", placement_id="p-001",
            display_surface_id="surf-001",
            starts_at=datetime(2026, 7, 20, 14, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 7, 20, 15, 0, tzinfo=timezone.utc),
            capacity_units=10,
        )
        await session.flush()
        result = await get_inventory_reservations_for_campaign(session, "c-001")
        assert len(result) == 1
        assert result[0]["campaign_id"] == "c-001"
        assert result[0]["status"] == "reserved"
    finally:
        await session.close()
        await engine.dispose()


# ============================================================================
# Config tests
# ============================================================================


class TestConfigTTL(unittest.TestCase):

    def test_default_ttl(self):
        from packages.security.config import SecurityConfig
        cfg = SecurityConfig()
        self.assertEqual(cfg.inventory_reservation_ttl_hours, 24)

    def test_custom_ttl_from_env(self):
        import os
        os.environ["INVENTORY_RESERVATION_TTL_HOURS"] = "48"
        try:
            from packages.security.config import SecurityConfig
            cfg = SecurityConfig()
            self.assertEqual(cfg.inventory_reservation_ttl_hours, 48)
        finally:
            del os.environ["INVENTORY_RESERVATION_TTL_HOURS"]


# ============================================================================
# Import boundary
# ============================================================================


def test_inventory_reservation_functions_importable():
    from packages.domain.repository import (
        reserve_inventory_for_placement,
        commit_inventory_for_campaign,
        release_inventory_for_campaign,
        expire_inventory_reservations,
        get_inventory_reservations_for_campaign,
        check_inventory_available_for_campaign,
    )
    import inspect
    for fn in [
        reserve_inventory_for_placement,
        commit_inventory_for_campaign,
        release_inventory_for_campaign,
        expire_inventory_reservations,
        get_inventory_reservations_for_campaign,
        check_inventory_available_for_campaign,
    ]:
        assert inspect.iscoroutinefunction(fn), f"{fn.__name__} is not async"
