"""
Behavioral RLS proof — creative_upload_sessions (S-054).

Validates that Migration 013 RLS policies actually restrict
upload session visibility to the owning advertiser organization
under the NOBYPASSRLS app runtime role.

Requires: RUN_BEHAVIORAL_TESTS=1, PostgreSQL with retail_media_app role.
"""

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ORG_A_ID = "a0000000-0000-0000-0000-0000000000a1"
ORG_A_CODE = "S054-ORG-A"
ORG_B_ID = "b0000000-0000-0000-0000-0000000000b2"
ORG_B_CODE = "S054-ORG-B"

ASSET_ID = "c0000000-0000-0000-0000-0000000000c3"
ASSET_CODE = "S054-ASSET"
SESSION_ID = "d0000000-0000-0000-0000-0000000000d4"

ADMIN_DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/"
    "retail_media_platform",
)

APP_DB_URL = os.environ.get("BEHAVIORAL_APP_DB_URL", "").strip()
if not APP_DB_URL:
    APP_DB_URL = os.environ.get("DATABASE_URL", "").strip()
if not APP_DB_URL:
    APP_DB_URL = (
        "postgresql+asyncpg://retail_media_app:retail_media_app"
        "@localhost:5432/retail_media_platform"
    )


async def _setup_fixtures():
    engine = create_async_engine(ADMIN_DB_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL app.rmp_is_admin = 'true'"))
            await conn.execute(text("SET LOCAL app.rmp_scope_advertiser_ids = ''"))

            await conn.execute(text(f"""
                INSERT INTO advertiser_organizations (id,code,legal_name,display_name,status)
                VALUES ('{ORG_A_ID}','{ORG_A_CODE}','Test Org A','Org A','active')
                ON CONFLICT (id) DO NOTHING
            """))
            await conn.execute(text(f"""
                INSERT INTO advertiser_organizations (id,code,legal_name,display_name,status)
                VALUES ('{ORG_B_ID}','{ORG_B_CODE}','Test Org B','Org B','active')
                ON CONFLICT (id) DO NOTHING
            """))

            await conn.execute(text(f"""
                INSERT INTO creative_assets
                    (id,code,name,advertiser_organization_id,media_type,
                     storage_bucket,storage_key,
                     moderation_status,status,created_by,created_at,updated_at)
                VALUES
                    ('{ASSET_ID}','{ASSET_CODE}','S-054 Test Asset','{ORG_A_ID}',
                     'image','test-bucket','test/key.jpg',
                     'pending_review','metadata_only',
                     '00000000-0000-0000-0000-000000000001',NOW(),NOW())
                ON CONFLICT (id) DO NOTHING
            """))

            await conn.execute(text(f"""
                INSERT INTO creative_upload_sessions
                    (id,creative_asset_id,advertiser_organization_id,
                     storage_bucket,storage_key,filename,content_type,content_length,
                     expires_at,created_by,created_at)
                VALUES
                    ('{SESSION_ID}','{ASSET_ID}','{ORG_A_ID}',
                     'test-bucket','{ORG_A_ID}/test/file.jpg','file.jpg',
                     'image/jpeg',1024,
                     NOW() + INTERVAL '1 hour',
                     '00000000-0000-0000-0000-000000000001',NOW())
            """))
    finally:
        await engine.dispose()


async def _cleanup():
    engine = create_async_engine(ADMIN_DB_URL, echo=False)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SET LOCAL app.rmp_is_admin = 'true'"))
            await conn.execute(text(f"DELETE FROM creative_upload_sessions WHERE id = '{SESSION_ID}'"))
            await conn.execute(text(f"DELETE FROM creative_assets WHERE id = '{ASSET_ID}'"))
            await conn.execute(text(f"DELETE FROM advertiser_organizations WHERE code IN ('{ORG_A_CODE}','{ORG_B_CODE}')"))
    finally:
        await engine.dispose()


async def _count_visible(scope_org_id, is_admin):
    engine = create_async_engine(APP_DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', :v, true)"),
                {"v": "true" if is_admin else "false"},
            )
            await conn.execute(
                text("SELECT set_config('app.rmp_scope_advertiser_ids', :v, true)"),
                {"v": scope_org_id if scope_org_id else ""},
            )
            result = await conn.execute(
                text("SELECT count(*) FROM creative_upload_sessions WHERE id = :sid"),
                {"sid": SESSION_ID},
            )
            return result.scalar()
    except Exception:
        return -1
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Tests (use conftest db_available fixture for skip/enforcement)
# ---------------------------------------------------------------------------


class TestUploadSessionRls:

    @pytest.fixture(autouse=True)
    def _require_db(self, db_available):
        """Skip if DB not available (delegates to conftest db_available)."""
        pass

    @classmethod
    def setup_class(cls):
        asyncio.run(_setup_fixtures())

    @classmethod
    def teardown_class(cls):
        asyncio.run(_cleanup())

    def test_own_org_can_see_session(self):
        """Org A can see its own upload session under RLS."""
        count = asyncio.run(_count_visible(ORG_A_ID, is_admin=False))
        assert count == 1, f"Expected 1 visible session for org A, got {count}"

    def test_foreign_org_cannot_see_session(self):
        """Org B must NOT see org A's upload session under RLS."""
        count = asyncio.run(_count_visible(ORG_B_ID, is_admin=False))
        assert count == 0, f"RLS leak: org B sees {count} session(s)"

    def test_admin_can_see_session(self):
        """Admin bypass sees all upload sessions."""
        count = asyncio.run(_count_visible("", is_admin=True))
        assert count == 1, f"Admin must see session, got {count}"

    def test_no_scope_no_admin_sees_nothing(self):
        """Empty scope + not admin → zero visible rows (fail-closed)."""
        count = asyncio.run(_count_visible("", is_admin=False))
        assert count == 0, f"Fail-open: {count} visible rows with no scope"

    def test_session_count_all_orgs_consistent(self):
        """Under admin bypass, exactly 1 test row exists."""
        count = asyncio.run(_count_visible("", is_admin=True))
        assert count == 1, f"Expected exactly 1 session row, got {count}"
