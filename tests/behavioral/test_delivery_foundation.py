"""
Behavioral tests — Delivery DB Foundation (Phase 4.2b).

Tests: create delivery plan, create manifest record with surfaces/assets,
rollback safety, commit safety.
Requires: RUN_BEHAVIORAL_TESTS=1, migration 008 applied.
"""

import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"
SKIP_REASON = "RUN_BEHAVIORAL_TESTS=1 not set."


def _raw_sql(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            result = await conn.execute(text(sql), params or {})
            rows = result.fetchall()
        await engine.dispose()
        return rows
    return asyncio.run(_run())


def _raw_exec(sql: str, params=None):
    async def _run():
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.begin() as conn:
            for stmt in sql.split(";"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s), params or {})
        await engine.dispose()
    asyncio.run(_run())


@pytest.fixture
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDeliveryPlan:

    def test_commit_stores_plan(self, db_available):
        from packages.domain.repository import create_delivery_plan

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                plan_id = await create_delivery_plan(
                    session,
                    campaign_id="00000000-0000-0000-0000-000000000220",
                    campaign_version_hash="sha256:abc123",
                    reason="test plan",
                )
                await session.commit()
                return plan_id
            await engine.dispose()

        plan_id = asyncio.run(_run())

        rows = _raw_sql(
            "SELECT id, campaign_id, status FROM delivery_plans WHERE id = :pid",
            {"pid": plan_id},
        )
        assert len(rows) == 1
        assert rows[0][2] == "planned"

        _raw_exec("DELETE FROM delivery_plans WHERE id = :pid", {"pid": plan_id})

    def test_rollback_discards_plan(self, db_available):
        from packages.domain.repository import create_delivery_plan

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                plan_id = await create_delivery_plan(
                    session,
                    campaign_id="00000000-0000-0000-0000-000000000220",
                    campaign_version_hash="sha256:rollback-test",
                )
                await session.rollback()
                return plan_id
            await engine.dispose()

        plan_id = asyncio.run(_run())

        rows = _raw_sql(
            "SELECT id FROM delivery_plans WHERE id = :pid",
            {"pid": plan_id},
        )
        assert len(rows) == 0


class TestDeliveryManifest:

    def test_commit_stores_manifest_with_surfaces(self, db_available):
        from packages.domain.repository import create_delivery_manifest_record

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                mid = await create_delivery_manifest_record(
                    session,
                    manifest_id_external="sha256:manifest-001",
                    campaign_id="00000000-0000-0000-0000-000000000220",
                    physical_device_id="00000000-0000-0000-0000-000000000020",
                    content_hash="sha256:content-abc",
                    surface_ids=["00000000-0000-0000-0000-000000000031"],
                )
                await session.commit()
                return mid
            await engine.dispose()

        mid = asyncio.run(_run())

        rows = _raw_sql(
            "SELECT id, manifest_id, status FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )
        assert len(rows) == 1
        assert rows[0][1] == "sha256:manifest-001"
        assert rows[0][2] == "planned"

        rows = _raw_sql(
            "SELECT id FROM delivery_manifest_surfaces WHERE manifest_id = :mid",
            {"mid": mid},
        )
        assert len(rows) == 1

        _raw_exec(
            "DELETE FROM delivery_manifest_surfaces WHERE manifest_id = :mid;"
            " DELETE FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )

    def test_rollback_discards_manifest(self, db_available):
        from packages.domain.repository import create_delivery_manifest_record

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                mid = await create_delivery_manifest_record(
                    session,
                    manifest_id_external="sha256:rollback-manifest",
                    campaign_id="00000000-0000-0000-0000-000000000220",
                    physical_device_id="00000000-0000-0000-0000-000000000020",
                    content_hash="sha256:content-rollback",
                )
                await session.rollback()
                return mid
            await engine.dispose()

        mid = asyncio.run(_run())

        rows = _raw_sql(
            "SELECT id FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )
        assert len(rows) == 0

    def test_manifest_with_assets(self, db_available):
        from packages.domain.repository import create_delivery_manifest_record

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                mid = await create_delivery_manifest_record(
                    session,
                    manifest_id_external="sha256:manifest-assets",
                    campaign_id="00000000-0000-0000-0000-000000000220",
                    physical_device_id="00000000-0000-0000-0000-000000000020",
                    content_hash="sha256:content-assets",
                    asset_records=[{
                        "creative_asset_id": "00000000-0000-0000-0000-000000000222",
                        "sha256_checksum": "deadbeef",
                        "duration_ms": 15000,
                        "media_type": "video/mp4",
                    }],
                )
                await session.commit()
                return mid
            await engine.dispose()

        mid = asyncio.run(_run())

        rows = _raw_sql(
            "SELECT creative_asset_id, media_type FROM delivery_manifest_assets "
            "WHERE manifest_id = :mid",
            {"mid": mid},
        )
        assert len(rows) == 1
        assert rows[0][1] == "video/mp4"

        _raw_exec(
            "DELETE FROM delivery_manifest_assets WHERE manifest_id = :mid;"
            " DELETE FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )
