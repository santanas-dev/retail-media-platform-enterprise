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


class TestMarkManifestHelpers:

    def _make_manifest(self):
        """Create a planned manifest and return (internal_id, external_id)."""
        from packages.domain.repository import create_delivery_manifest_record
        external = "sha256:test-mark-fn-001"

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                mid = await create_delivery_manifest_record(
                    session,
                    manifest_id_external=external,
                    campaign_id="00000000-0000-0000-0000-000000000220",
                    physical_device_id="00000000-0000-0000-0000-000000000020",
                    content_hash="sha256:content-test",
                )
                await session.commit()
                return mid
            await engine.dispose()

        return asyncio.run(_run()), external

    def _cleanup(self, mid):
        _raw_exec("DELETE FROM delivery_manifests WHERE id = :mid", {"mid": mid})

    def test_mark_generated(self, db_available):
        from packages.domain.repository import mark_manifest_generated
        mid, external = self._make_manifest()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await mark_manifest_generated(session, external,
                                              content_hash="sha256:gen-content")
                await session.commit()
            await engine.dispose()
        asyncio.run(_run())

        rows = _raw_sql(
            "SELECT status, generated_at FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )
        assert rows[0][0] == "generated"
        assert rows[0][1] is not None

        self._cleanup(mid)

    def test_mark_failed_stores_error(self, db_available):
        from packages.domain.repository import mark_manifest_failed
        mid, external = self._make_manifest()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await mark_manifest_failed(session, external,
                                           last_error="Target resolution: no surfaces")
                await session.commit()
            await engine.dispose()
        asyncio.run(_run())

        rows = _raw_sql(
            "SELECT status, last_error FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )
        assert rows[0][0] == "failed"
        assert "no surfaces" in rows[0][1]

        self._cleanup(mid)

    def test_mark_delivered(self, db_available):
        from packages.domain.repository import (
            mark_manifest_generated, mark_manifest_delivered,
        )
        mid, external = self._make_manifest()

        # First mark as generated
        async def _gen():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await mark_manifest_generated(session, external,
                                              content_hash="sha256:gen-content")
                await session.commit()
            await engine.dispose()
        asyncio.run(_gen())

        # Then mark as delivered
        async def _del():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await mark_manifest_delivered(session, external)
                await session.commit()
            await engine.dispose()
        asyncio.run(_del())

        rows = _raw_sql(
            "SELECT status, delivered_at FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )
        assert rows[0][0] == "delivered"
        assert rows[0][1] is not None

        self._cleanup(mid)

    def test_mark_generated_idempotent(self, db_available):
        """Second mark_generated on an already generated manifest is no-op."""
        from packages.domain.repository import mark_manifest_generated
        mid, external = self._make_manifest()

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                await mark_manifest_generated(session, external,
                                              content_hash="sha256:gen-1")
                await mark_manifest_generated(session, external,
                                              content_hash="sha256:gen-2")
                await session.commit()
            await engine.dispose()
        asyncio.run(_run())

        rows = _raw_sql(
            "SELECT status, content_hash FROM delivery_manifests WHERE id = :mid",
            {"mid": mid},
        )
        assert rows[0][0] == "generated"
        # Second call should not overwrite — content_hash stays from first call
        assert rows[0][1] == "sha256:gen-1"

        self._cleanup(mid)


class TestDeliveryAttempt:

    def test_create_attempt_succeeds(self, db_available):
        """create_delivery_attempt with valid external manifest_id."""
        from packages.domain.repository import (
            create_delivery_manifest_record, create_delivery_attempt,
        )

        async def _run():
            engine = create_async_engine(DB_URL, echo=False)
            AsyncSessionLocal = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False,
            )
            async with AsyncSessionLocal() as session:
                # Create manifest first
                mid = await create_delivery_manifest_record(
                    session,
                    manifest_id_external="sha256:attempt-test",
                    campaign_id="00000000-0000-0000-0000-000000000220",
                    physical_device_id="00000000-0000-0000-0000-000000000020",
                    content_hash="sha256:content-attempt",
                )
                await session.flush()  # ensure manifest row is visible for FK
                # Create attempt using external manifest_id
                aid = await create_delivery_attempt(
                    session,
                    manifest_id_external="sha256:attempt-test",
                )
                await session.commit()
                return mid, aid
            await engine.dispose()

        mid, aid = asyncio.run(_run())

        rows = _raw_sql(
            "SELECT manifest_id, status FROM delivery_attempts WHERE id = :aid",
            {"aid": aid},
        )
        assert len(rows) == 1
        assert rows[0][0] == "sha256:attempt-test"
        assert rows[0][1] == "pending"

        # Cleanup
        _raw_exec(
            "DELETE FROM delivery_attempts WHERE id = :aid;"
            " DELETE FROM delivery_manifests WHERE id = :mid",
            {"aid": aid, "mid": mid},
        )
