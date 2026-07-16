"""Inventory rules management tests (S-088).

Schema validation + async integration for create/list/update/activate/deactivate.
"""

import unittest
from datetime import datetime, timedelta, timezone

import pytest


# ============================================================================
# Schema validation tests (no DB)
# ============================================================================


class TestRulesSchemas(unittest.TestCase):
    """Pydantic schema validation for InventoryRuleOut/Create/Update."""

    def setUp(self):
        from packages.domain.schemas import (
            InventoryRuleOut,
            InventoryRuleCreate,
            InventoryRuleUpdate,
        )
        self.Out = InventoryRuleOut
        self.Create = InventoryRuleCreate
        self.Update = InventoryRuleUpdate

    def test_out_valid(self):
        obj = self.Out(
            id="r-001", rule_type="blackout",
            created_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(obj.rule_type, "blackout")
        self.assertTrue(obj.is_active)

    def test_create_minimal(self):
        obj = self.Create(rule_type="max_sov", value_json={"max_sov_percent": 50})
        self.assertEqual(obj.scope_type, "global")
        self.assertIsNone(obj.scope_id)

    def test_create_with_scope(self):
        obj = self.Create(
            rule_type="internal_block",
            scope_type="surface", scope_id="s-001",
            value_json={"capacity_units": 10},
        )
        self.assertEqual(obj.scope_type, "surface")

    def test_update_partial(self):
        obj = self.Update(priority=200)
        self.assertEqual(obj.priority, 200)
        self.assertIsNone(obj.rule_type)

    def test_update_is_active(self):
        obj = self.Update(is_active=False)
        self.assertFalse(obj.is_active)


# ============================================================================
# Async DB helpers (SQLite)
# ============================================================================


async def _make_session():
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


# ============================================================================
# Async integration tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_blackout_rule():
    from packages.domain.repository import create_inventory_rule
    session, engine = await _make_session()
    try:
        rule = await create_inventory_rule(
            session, rule_type="blackout",
            scope_type="surface", scope_id="s-001",
            value_json={"reason": "Ремонт"},
        )
        await session.flush()
        assert rule.id is not None
        assert rule.rule_type == "blackout"
        assert rule.scope_type == "surface"
        assert rule.is_active is True
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_internal_block_validates_capacity():
    from packages.domain.repository import create_inventory_rule
    session, engine = await _make_session()
    try:
        rule = await create_inventory_rule(
            session, rule_type="internal_block",
            value_json={"capacity_units": 5},
        )
        await session.flush()
        assert rule.rule_type == "internal_block"
        assert rule.value_json["capacity_units"] == 5
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_max_sov_rule():
    from packages.domain.repository import create_inventory_rule
    session, engine = await _make_session()
    try:
        rule = await create_inventory_rule(
            session, rule_type="max_sov",
            value_json={"max_sov_percent": 30},
        )
        await session.flush()
        assert rule.rule_type == "max_sov"
        assert rule.value_json["max_sov_percent"] == 30
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_rules():
    from packages.domain.repository import create_inventory_rule, list_inventory_rules
    session, engine = await _make_session()
    try:
        await create_inventory_rule(session, rule_type="blackout")
        await create_inventory_rule(session, rule_type="max_sov", value_json={"max_sov_percent": 50})
        await session.flush()
        items = await list_inventory_rules(session)
        assert len(items) == 2
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_activate_deactivate_rule():
    from packages.domain.repository import (
        create_inventory_rule, set_inventory_rule_active,
    )
    session, engine = await _make_session()
    try:
        rule = await create_inventory_rule(session, rule_type="blackout")
        await session.flush()
        rid = rule.id
        # Deactivate
        r2 = await set_inventory_rule_active(session, rule_id=rid, is_active=False)
        assert r2 is not None
        assert r2.is_active is False
        # Activate
        r3 = await set_inventory_rule_active(session, rule_id=rid, is_active=True)
        assert r3 is not None
        assert r3.is_active is True
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_update_rule_partial():
    from packages.domain.repository import (
        create_inventory_rule, update_inventory_rule,
    )
    session, engine = await _make_session()
    try:
        rule = await create_inventory_rule(session, rule_type="blackout", priority=100)
        await session.flush()
        rid = rule.id
        updated = await update_inventory_rule(session, rule_id=rid, priority=200, is_active=False)
        assert updated is not None
        assert updated.priority == 200
        assert updated.is_active is False
        assert updated.rule_type == "blackout"  # unchanged
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_update_nonexistent_rule():
    from packages.domain.repository import update_inventory_rule
    session, engine = await _make_session()
    try:
        result = await update_inventory_rule(session, rule_id="nonexistent", priority=100)
        assert result is None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_rules_filter_active():
    from packages.domain.repository import create_inventory_rule, list_inventory_rules
    session, engine = await _make_session()
    try:
        await create_inventory_rule(session, rule_type="blackout", is_active=True)
        await create_inventory_rule(session, rule_type="max_sov", is_active=False, value_json={"max_sov_percent": 50})
        await session.flush()
        active = await list_inventory_rules(session, is_active=True)
        inactive = await list_inventory_rules(session, is_active=False)
        assert len(active) == 1
        assert len(inactive) == 1
    finally:
        await session.close()
        await engine.dispose()
