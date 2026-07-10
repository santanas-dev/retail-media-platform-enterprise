"""S-019: Role safety — verify three-role DB architecture.

Proves:
  - retail_media_app has NOBYPASSRLS (rolsuper=false, rolbypassrls=false)
  - retail_media_app cannot CREATE TABLE (no DDL privilege)
  - retail_media_owner can run migrations (SELECT 1 as proxy)
  - check_db_role_safety reports app role as safe
  - check_db_role_safety reports owner role as dev-safe (dev mode)

Requires:
  - PostgreSQL with two roles: retail_media_owner (superuser), retail_media_app (NOBYPASSRLS)
  - Run with: RUN_BEHAVIORAL_TESTS=1 python -m pytest tests/test_s019_role_safety.py -v
  - Skips without RUN_BEHAVIORAL_TESTS=1
"""

import os

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_BEHAVIORAL_TESTS"),
    reason="RUN_BEHAVIORAL_TESTS not set",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def owner_url() -> str:
    return os.environ.get(
        "DB_OWNER_URL",
        "postgresql+asyncpg://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
    )


@pytest.fixture
def app_url() -> str:
    return os.environ.get(
        "DB_APP_URL",
        "postgresql+asyncpg://retail_media_app:retail_media_app_pass@localhost:5432/retail_media_platform",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAppRoleAttributes:
    """retail_media_app must be NOBYPASSRLS, non-superuser."""

    async def test_app_role_not_superuser(self, app_url):
        engine = create_async_engine(app_url, echo=False)
        try:
            async with engine.connect() as conn:
                row = await conn.execute(text(
                    "SELECT rolsuper FROM pg_roles WHERE rolname = 'retail_media_app'"
                ))
                result = row.fetchone()
                assert result is not None, "retail_media_app role not found"
                assert result[0] is False, "retail_media_app must not be superuser"
        finally:
            await engine.dispose()

    async def test_app_role_no_bypassrls(self, app_url):
        engine = create_async_engine(app_url, echo=False)
        try:
            async with engine.connect() as conn:
                row = await conn.execute(text(
                    "SELECT rolbypassrls FROM pg_roles WHERE rolname = 'retail_media_app'"
                ))
                result = row.fetchone()
                assert result is not None, "retail_media_app role not found"
                assert result[0] is False, "retail_media_app must have NOBYPASSRLS"
        finally:
            await engine.dispose()

    async def test_app_role_cannot_create_table(self, app_url):
        """app role must not have DDL privileges."""
        engine = create_async_engine(app_url, echo=False)
        try:
            async with engine.connect() as conn:
                # Attempt CREATE TABLE — must fail
                with pytest.raises(Exception):
                    await conn.execute(text(
                        "CREATE TABLE _s019_probe (id int)"
                    ))
                    await conn.commit()
                # Clean up if somehow it succeeded
                await conn.rollback()
        finally:
            await engine.dispose()


class TestOwnerRole:
    """retail_media_owner can run migrations (DDL-capable)."""

    async def test_owner_can_query(self, owner_url):
        engine = create_async_engine(owner_url, echo=False)
        try:
            async with engine.connect() as conn:
                row = await conn.execute(text("SELECT 1"))
                assert row.scalar() == 1
        finally:
            await engine.dispose()

    async def test_owner_has_superuser(self, owner_url):
        """In dev compose, owner is superuser (bootstrap convenience)."""
        engine = create_async_engine(owner_url, echo=False)
        try:
            async with engine.connect() as conn:
                row = await conn.execute(text(
                    "SELECT rolsuper FROM pg_roles WHERE rolname = 'retail_media_owner'"
                ))
                result = row.fetchone()
                assert result is not None, "retail_media_owner role not found"
                assert result[0] is True, "retail_media_owner should be superuser in dev"
        finally:
            await engine.dispose()


class TestCheckDbRoleSafety:
    """check_db_role_safety reports correct status."""

    async def test_app_role_reported_safe(self, app_url):
        from packages.domain.database import check_db_role_safety

        engine = create_async_engine(app_url, echo=False)
        try:
            ok, info = await check_db_role_safety(engine, dev_mode=False)
            assert ok, f"app role should be safe, got {info}"
            assert info["db_role"] == "ok", f"app role status should be ok, got {info}"
            assert "NOBYPASSRLS" in info["db_role_details"]
        finally:
            await engine.dispose()

    async def test_owner_role_dev_safe(self, owner_url):
        """In dev mode, superuser reports ok with dev note."""
        from packages.domain.database import check_db_role_safety

        engine = create_async_engine(owner_url, echo=False)
        try:
            ok, info = await check_db_role_safety(engine, dev_mode=True)
            assert ok, f"owner should be dev-safe, got {info}"
            assert "dev:" in info["db_role_details"], (
                f"dev mode should note superuser, got {info}"
            )
        finally:
            await engine.dispose()

    async def test_owner_role_production_unsafe(self, owner_url):
        """In production mode, superuser must be rejected."""
        from packages.domain.database import check_db_role_safety

        engine = create_async_engine(owner_url, echo=False)
        try:
            ok, info = await check_db_role_safety(engine, dev_mode=False)
            assert not ok, f"owner should be unsafe in prod, got {info}"
            assert info["db_role"] == "unsafe"
        finally:
            await engine.dispose()


class TestSetWorkerAdminContext:
    """set_worker_admin_context sets app.rmp_is_admin=true."""

    async def test_worker_admin_context_set(self, app_url):
        from packages.domain.database import set_worker_admin_context

        engine = create_async_engine(app_url, echo=False)
        try:
            async with AsyncSession(engine) as session:
                await set_worker_admin_context(session)

                row = await session.execute(text(
                    "SELECT current_setting('app.rmp_is_admin', true)"
                ))
                val = row.scalar()
                assert val == "true", (
                    f"app.rmp_is_admin should be 'true', got {val}"
                )
        finally:
            await engine.dispose()
