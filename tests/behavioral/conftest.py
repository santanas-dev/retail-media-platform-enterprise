"""
Behavioral test suite - shared fixtures (Phase 3.4).

Tests run against real PostgreSQL. Skipped unless RUN_BEHAVIORAL_TESTS=1.
"""

import asyncio
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
    "secoff":     "beh-so-00000000000000000005",
    "analyst":    "beh-an-00000000000000000006",
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
        # Bypass RLS for test fixture setup/cleanup
        await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
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
      ('{u["advertiser"]}','BEH-AV','beh-advertiser','beh-av@t.local','Beh AV','local_advertiser','active'),
      ('{u["secoff"]}','BEH-SO','beh-secoff','beh-so@t.local','Beh SO','local_advertiser','active'),
      ('{u["analyst"]}','BEH-AN','beh-analyst','beh-an@t.local','Beh AN','local_advertiser','active')
    ; INSERT INTO local_credentials (id,user_id,credential_type,password_hash,status) VALUES
      ('lc-beh-ro','{u["readonly"]}','local_advertiser','{ph}','active'),
      ('lc-beh-np','{u["noperms"]}','local_advertiser','{ph}','active'),
      ('lc-beh-ds','{u["disabled"]}','local_advertiser','{ph}','active'),
      ('lc-beh-av','{u["advertiser"]}','local_advertiser','{ph}','active'),
      ('lc-beh-so','{u["secoff"]}','local_advertiser','{ph}','active'),
      ('lc-beh-an','{u["analyst"]}','local_advertiser','{ph}','active')
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-ro','{u["readonly"]}',id FROM roles WHERE code='system_admin'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-np','{u["noperms"]}',id FROM roles WHERE code='operator'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-ds','{u["disabled"]}',id FROM roles WHERE code='system_admin'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-av','{u["advertiser"]}',id FROM roles WHERE code='advertiser'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-so','{u["secoff"]}',id FROM roles WHERE code='security_admin'
    ; INSERT INTO user_roles (id,user_id,role_id)
      SELECT 'ur-beh-an','{u["analyst"]}',id FROM roles WHERE code='analyst'
    -- Ensure advertiser role exists (not in seed)
    ; INSERT INTO roles (id,code,name,description,is_system)
      SELECT '00000000-0000-0000-0000-000000000114','advertiser','Advertiser','Advertiser cabinet user',false
      WHERE NOT EXISTS (SELECT 1 FROM roles WHERE code='advertiser')
    -- Phase 4.0b: ensure advertiser-scoped permissions exist (idempotent)
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-000000000108','advertisers.read','Просмотр рекламодателей')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-00000000010a','advertisers.contacts.read','Просмотр контактов рекламодателей')
      ON CONFLICT (code) DO NOTHING
    -- Ensure advertiser role has organization.read permission
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-adv-org','00000000-0000-0000-0000-000000000114',id
      FROM permissions WHERE code='organization.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id='00000000-0000-0000-0000-000000000114'
        AND permission_id=(SELECT id FROM permissions WHERE code='organization.read')
      )
    -- Phase 4.0b: advertiser role needs advertisers.read for brands/contracts
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-adv-read','00000000-0000-0000-0000-000000000114',id
      FROM permissions WHERE code='advertisers.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id='00000000-0000-0000-0000-000000000114'
        AND permission_id=(SELECT id FROM permissions WHERE code='advertisers.read')
      )
    -- Phase 4.0b: advertiser role needs advertisers.contacts.read for PII-gated contacts
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-adv-contacts','00000000-0000-0000-0000-000000000114',id
      FROM permissions WHERE code='advertisers.contacts.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id='00000000-0000-0000-0000-000000000114'
        AND permission_id=(SELECT id FROM permissions WHERE code='advertisers.contacts.read')
      )
    ; INSERT INTO advertiser_user_memberships (id,user_id,advertiser_organization_id,status)
      SELECT 'aum-beh-av','{u["advertiser"]}',id,'active'
      FROM advertiser_organizations WHERE code='ADV-001'
    -- Phase 4.0b: ensure system_admin has advertisers.read + contacts.read
    -- (seed may not have been re-run yet, these inserts are idempotent)
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-sa-read',r.id,p.id
      FROM roles r CROSS JOIN permissions p
      WHERE r.code='system_admin' AND p.code='advertisers.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=r.id AND permission_id=p.id
      )
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-sa-contacts',r.id,p.id
      FROM roles r CROSS JOIN permissions p
      WHERE r.code='system_admin' AND p.code='advertisers.contacts.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=r.id AND permission_id=p.id
      )
    """


_CLEANUP = """
    DELETE FROM login_attempts WHERE username_or_email_hash LIKE 'beh-test-%'
    ; DELETE FROM refresh_sessions WHERE user_id LIKE 'beh-%'
    ; DELETE FROM advertiser_user_memberships WHERE user_id LIKE 'beh-%'
    ; DELETE FROM local_credentials WHERE user_id LIKE 'beh-%'
    ; DELETE FROM user_roles WHERE user_id LIKE 'beh-%'
    ; DELETE FROM users WHERE id LIKE 'beh-%'
"""


# ---------------------------------------------------------------------------
# App loader — fails loudly if the control-api module can't be found
# ---------------------------------------------------------------------------


def _load_control_api_app():
    """Load the FastAPI app from apps/control-api/main.py.

    Uses importlib because the directory name ``control-api`` contains a
    hyphen, which prevents normal ``import``.  Every failure mode produces
    a clear, actionable error message.
    """
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    main_path = os.path.join(repo_root, "apps", "control-api", "main.py")

    if not os.path.exists(main_path):
        raise FileNotFoundError(
            f"control-api main.py not found at {main_path}. "
            f"Ensure the repo is checked out correctly."
        )

    spec = importlib.util.spec_from_file_location("control_api_main", main_path)
    if spec is None or spec.loader is None:
        raise ImportError(
            f"Could not create module spec for {main_path}. "
            f"Check that the file is valid Python."
        )

    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:
        raise ImportError(
            f"Failed to load control-api module from {main_path}: {exc}"
        ) from exc

    if not hasattr(mod, "app"):
        raise AttributeError(
            f"Module at {main_path} does not export 'app'. "
            f"Expected a FastAPI instance named 'app' at module level."
        )

    return mod.app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    """Load the control-api FastAPI app once per test session."""
    reset_security_config()
    return _load_control_api_app()


@pytest.fixture(scope="session")
def db_available():
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)
    if not asyncio.run(_check_db()):
        pytest.skip("PostgreSQL not reachable at " + DB_URL)


@pytest.fixture
def test_users(db_available):
    ph = bcrypt.hashpw(TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()
    asyncio.run(_run_sql(_setup_sql(ph)))
    yield {**USER_IDS, "password": TEST_PASSWORD}
    asyncio.run(_run_sql(_CLEANUP))
