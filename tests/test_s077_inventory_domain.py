"""Inventory domain schema + model tests (S-077).

Covers: model table count, slot properties, schema validation.
Full repository tests require PostgreSQL (JSONB) — deferred to behavioural suite.
"""

import unittest
from datetime import date

from packages.domain.models import (
    InventorySlot,
    Base,
    REQUIRED_TABLES,
)
from packages.domain.schemas import (
    InventoryBookingCreate,
    InventoryRuleCreate,
    InventoryRuleUpdate,
    InventorySlotCreate,
)


# ---------------------------------------------------------------------------
# Model / metadata tests
# ---------------------------------------------------------------------------


class TestInventoryModelTableCount(unittest.TestCase):
    def test_required_tables_includes_inventory(self):
        self.assertIn("inventory_slots", REQUIRED_TABLES)
        self.assertIn("inventory_bookings", REQUIRED_TABLES)
        self.assertIn("inventory_rules", REQUIRED_TABLES)

    def test_metadata_table_count(self):
        count = len(Base.metadata.tables)
        self.assertEqual(count, 51, f"Expected 51 tables, got {count}")


# ---------------------------------------------------------------------------
# InventorySlot — model properties
# ---------------------------------------------------------------------------


class TestInventorySlotProperties(unittest.TestCase):
    def _slot(self, **kwargs):
        defaults = {
            "total_capacity": 0,
            "booked_capacity": 0,
            "reserved_capacity": 0,
            "internal_blocked_capacity": 0,
            "emergency_blocked_capacity": 0,
        }
        defaults.update(kwargs)
        # Build via ORM constructor — all kwargs passed explicitly to avoid
        # SQLAlchemy default-resolution edge cases with Integer columns.
        return InventorySlot(**defaults)

    def test_available_capacity_no_bookings(self):
        slot = self._slot(total_capacity=120)
        self.assertEqual(slot.available_capacity, 120)

    def test_available_capacity_partial(self):
        slot = self._slot(total_capacity=120, booked_capacity=80, reserved_capacity=10)
        self.assertEqual(slot.available_capacity, 30)

    def test_available_capacity_sold_out(self):
        slot = self._slot(total_capacity=120, booked_capacity=120)
        self.assertEqual(slot.available_capacity, 0)
        self.assertTrue(slot.is_sold_out)

    def test_available_capacity_emergency_blocked(self):
        slot = self._slot(total_capacity=120, emergency_blocked_capacity=1)
        self.assertEqual(slot.available_capacity, 0)

    def test_available_capacity_internal_blocked(self):
        slot = self._slot(total_capacity=120, internal_blocked_capacity=40)
        self.assertEqual(slot.available_capacity, 80)

    def test_recompute_status_available(self):
        slot = self._slot(total_capacity=120)
        self.assertEqual(slot.recompute_status(), "available")

    def test_recompute_status_limited(self):
        slot = self._slot(total_capacity=120, booked_capacity=1)
        self.assertEqual(slot.recompute_status(), "limited")

    def test_recompute_status_sold_out(self):
        slot = self._slot(total_capacity=120, booked_capacity=120)
        self.assertEqual(slot.recompute_status(), "sold_out")

    def test_recompute_status_blocked(self):
        slot = self._slot(total_capacity=120, emergency_blocked_capacity=1)
        self.assertEqual(slot.recompute_status(), "blocked")


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestInventorySchemaValidation(unittest.TestCase):
    def test_slot_create_valid(self):
        s = InventorySlotCreate(
            display_surface_id="00000000-0000-0000-0000-000000000001",
            slot_date=date(2026, 7, 20),
            slot_hour=14,
            total_capacity=120,
        )
        self.assertEqual(s.slot_hour, 14)

    def test_slot_create_hour_out_of_range(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            InventorySlotCreate(
                display_surface_id="00000000-0000-0000-0000-000000000001",
                slot_date=date(2026, 7, 20),
                slot_hour=24,
            )

    def test_booking_create_capacity_positive(self):
        b = InventoryBookingCreate(
            inventory_slot_id="00000000-0000-0000-0000-000000000001",
            capacity_units=5,
        )
        self.assertEqual(b.capacity_units, 5)

    def test_booking_create_capacity_zero_raises(self):
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            InventoryBookingCreate(
                inventory_slot_id="00000000-0000-0000-0000-000000000001",
                capacity_units=0,
            )

    def test_rule_create_defaults(self):
        r = InventoryRuleCreate(rule_type="max_ad_load")
        self.assertEqual(r.scope_type, "global")
        self.assertEqual(r.priority, 100)
        self.assertTrue(r.is_active)

    def test_rule_update_partial(self):
        r = InventoryRuleUpdate(is_active=False)
        self.assertFalse(r.is_active)
        self.assertIsNone(r.rule_type)
