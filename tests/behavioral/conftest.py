"""
Behavioral test suite - shared fixtures (Phase 3.4).

Tests run against real PostgreSQL. Skipped unless RUN_BEHAVIORAL_TESTS=1.
"""

import importlib.util
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

os.environ["ENVIRONMENT"] = "dev"
os.environ["JWT_SECRET"] = "behavioral-test-secret-at-least-32-chars"

import bcrypt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from packages.security.config import reset_security_config

DB_URL = os.environ.get(
    "BEHAVIORAL_DB_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

REQUIRE_ENV = os.environ.get("RUN_BEHAVIORAL_TESTS", "") == "1"

SKIP_REASON = (
    "RUN_BEHAVIORAL_TESTS=1 not set. "
    "See tests/behavioral/__init__.py for setup instructions."
)

# 26-char IDs to fit varchar(36)
USER_IDS = {
    "readonly":   "beh-ro-00000000000000000001",
    "noperms":    "beh-np-00000000000000000002",
    "disabled":   "beh-ds-00000000000000000003",
    "advertiser": "beh-av-00000000000000000004",
}

TEST_PASSWORD = "TestPassword123!"


async def _check_db():
    try:
        engine = create_async_engine(DB_URL, echo=False)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()
        return True
    except Exception:
        return False


async def _run_sql(sql: str):
    engine = create_async_engine(DB_URL, echo=False)
    async with engine.begin() as conn:
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s and not s.startswith("--"):
                await conn.execute(text(s))
    await engine.dispose()


def _setup_sql(ph):
    u = USER_IDS
    return f"""
    DELETE FROM login_attempts WHERE username_or_email_hash LIKE 'beh-test-%'
    ; DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-%'
    ; DELETE FROM local_credentials WHERE user_id LIKE 'beh-%'
    ; DELETE FROM user_roles WHERE user_id LIKE 'beh-%'
    ; DELETE FROM users WHERE id LIKE 'beh-%'
    ; INSERT INTO users (id,code,username,email,display_name,auth_provider,status) VALUES
      ('{u["readonly"]}','BEH-RO','beh-readonly','beh-ro@t.local','Beh RO','local_advertiser','active'),
      ('{u["noperms"]}','BEH-NP','beh-noperms','beh-np@t.local','Beh NP','local_advertiser','active'),
      ('{u["disabled"]}','BEH-DS','beh-disabled','beh-ds@t.local','Beh DS','local_advertiser','disabled'),
      ('{u["advertiser"]}','BEH-AV','beh-advertiser','beh-av@t.local','Beh AV','local_advertiser','active')
    ; INSERT INTO local_credentials (id,user_id,credential_type,password_hash,status) VALUES
      ('lc-beh-ro','{u["readonly"]}','local_advertiser','{ph}','active'),
      ('lc-beh-np','{u["noperms"]}','local_advertiser','{ph}','active'),
      ('lc-beh-ds','{u["disabled"]}','local_advertiser','{ph}','active'),
      ('lc-beh-av','{u["advertiser"]}','local_advertiser','{ph}','active')
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-ro','{u["readonly"]}',id FROM roles WHERE code='system_admin'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-np','{u["noperms"]}',id FROM roles WHERE code='operator'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-ds','{u["disabled"]}',id FROM roles WHERE code='system_admin'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-av','{u["advertiser"]}',id FROM roles WHERE code='advertiser'
    """


_CLEANUP = """
    DELETE FROM login_attempts WHERE username_or_email_hash LIKE 'beh-test-%'
    ; DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-%'
    ; DELETE FROM local_credentials WHERE user_id LIKE 'beh-%'
    ; DELETE FROM user_roles WHERE user_id LIKE 'beh-%'
    ; DELETE FROM users WHERE id LIKE 'beh-%'
"""


@pytest.fixture(scope="session")
def app():
    reset_security_config()
    os.environ["ENVIRONMENT"] = "dev"
    os.environ["JWT_SECRET"] = "behavioral-test-secret-at-least-32-chars"
    path = os.path.join(
        os.path.dirname(__file__), "..", "..",
        "apps", "control-api", "main.py",
    )
    spec = importlib.util.spec_from_file_location("control_api_main", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


@pytest.fixture(scope="session")
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)
    import asyncio
    if not asyncio.run(_check_db()):
        pytest.skip("PostgreSQL not reachable at " + DB_URL)


@pytest.fixture
def test_users(db_available):
    import asyncio
    ph = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    asyncio.run(_run_sql(_setup_sql(ph)))
    yield {**USER_IDS, "password": TEST_PASSWORD}
    asyncio.run(_run_sql(_CLEANUP))
