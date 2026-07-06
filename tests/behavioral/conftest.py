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

# Phase 4.3b — PoP persistence fixture IDs
POP_IDS = {
    "branch":      "beh-pop-br-000000000000000001",
    "cluster":     "beh-pop-cl-000000000000000001",
    "store":       "beh-pop-st-000000000000000001",
    "channel":     "beh-pop-ch-000000000000000001",
    "device_type": "beh-pop-dt-000000000000000001",
    "device":      "beh-pop-dev-000000000000000001",
    "adv_org":     "beh-pop-adv-000000000000000001",
    "creative":    "beh-pop-cr-000000000000000001",
    "campaign":    "beh-pop-camp-00000000000000001",
    "manifest":    "beh-pop-manifest-pop-test-001",
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
    ; DELETE FROM advertiser_user_memberships WHERE user_id LIKE 'beh-%'
    ; DELETE FROM users WHERE id LIKE 'beh-%'
    ; INSERT INTO users (id,code,username,email,display_name,auth_provider,status) VALUES
      ('{u["readonly"]}','BEH-RO','beh-readonly','beh-ro@t.local','Beh RO','local_advertiser','active'),
      ('{u["noperms"]}','BEH-NP','beh-noperms','beh-np@t.local','Beh NP','local_advertiser','active'),
      ('{u["disabled"]}','BEH-DS','beh-disabled','beh-ds@t.local','Beh DS','local_advertiser','disabled'),
      ('{u["advertiser"]}','BEH-AV','beh-advertiser','beh-av@t.local','Beh AV','local_advertiser','active'),
      ('{u["secoff"]}','BEH-SO','beh-secoff','beh-so@t.local','Beh SO','local_advertiser','active'),
      ('{u["analyst"]}','BEH-AN','beh-analyst','beh-an@t.local','Beh AN','local_advertiser','active')
    -- Phase 4.1c: clean up campaign data referencing behavioral users
    ; DELETE FROM outbox_events WHERE aggregate_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_status_history WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_placements WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_creatives WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_flights WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_approvals WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaigns WHERE created_by LIKE 'beh-%'
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
    -- Phase 4.1b: advertiser role needs campaigns.read for campaign endpoints
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-adv-campread','00000000-0000-0000-0000-000000000114',id
      FROM permissions WHERE code='campaigns.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id='00000000-0000-0000-0000-000000000114'
        AND permission_id=(SELECT id FROM permissions WHERE code='campaigns.read')
      )
    -- Phase 4.1b: advertiser role needs creatives.read for creative asset access
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-adv-creatread','00000000-0000-0000-0000-000000000114',id
      FROM permissions WHERE code='creatives.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id='00000000-0000-0000-0000-000000000114'
        AND permission_id=(SELECT id FROM permissions WHERE code='creatives.read')
      )
    -- Phase 4.1b: ensure campaign-related permissions exist (idempotent)
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-00000000010c','campaigns.read','Просмотр кампаний')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-00000000010f','creatives.read','Просмотр креативов')
      ON CONFLICT (code) DO NOTHING
    -- Phase 4.1b: ensure campaign permissions on system_admin (idempotent)
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-sa-campread',r.id,p.id
      FROM roles r CROSS JOIN permissions p
      WHERE r.code='system_admin' AND p.code='campaigns.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=r.id AND permission_id=p.id
      )
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-sa-creatread',r.id,p.id
      FROM roles r CROSS JOIN permissions p
      WHERE r.code='system_admin' AND p.code='creatives.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id=r.id AND permission_id=p.id
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
    -- Phase 4.2: campaign.manage permission + advertiser role grant
    ; INSERT INTO permissions (id, code, name) VALUES
      ('00000000-0000-0000-0000-00000000010d','campaigns.manage','Управление кампаниями')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO role_permissions (id,role_id,permission_id)
      SELECT 'rp-beh-adv-campmg','00000000-0000-0000-0000-000000000114',id
      FROM permissions WHERE code='campaigns.manage'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_id='00000000-0000-0000-0000-000000000114'
        AND permission_id=(SELECT id FROM permissions WHERE code='campaigns.manage')
      )
    """


_CLEANUP = """
    DELETE FROM outbox_events WHERE aggregate_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_status_history WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_placements WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_creatives WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_flights WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaign_approvals WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE created_by LIKE 'beh-%'
    )
    ; DELETE FROM campaigns WHERE created_by LIKE 'beh-%'
    ; DELETE FROM campaign_approvals WHERE reviewed_by LIKE 'beh-%'
    ; DELETE FROM campaign_status_history WHERE changed_by LIKE 'beh-%'
    ; DELETE FROM login_attempts WHERE username_or_email_hash LIKE 'beh-test-%'
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


# ---------------------------------------------------------------------------
# Phase 4.3b — PoP persistence fixtures
# ---------------------------------------------------------------------------


def _setup_pop_sql():
    p = POP_IDS
    return f"""
    -- Device chain: branch → cluster → store → channel → device_type → physical_device
    INSERT INTO branches (id,code,name,timezone,is_active) VALUES
      ('{p["branch"]}','BEH-POP-BR','PoP Test Branch','Europe/Moscow',true)
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO clusters (id,branch_id,code,name,is_active) VALUES
      ('{p["cluster"]}','{p["branch"]}','BEH-POP-CL','PoP Test Cluster',true)
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO stores (id,cluster_id,code,name,address,timezone,is_active) VALUES
      ('{p["store"]}','{p["cluster"]}','BEH-POP-ST','PoP Test Store','Test Address','Europe/Moscow',true)
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO channels (id,code,name,is_active) VALUES
      ('{p["channel"]}','BEH-POP-CH','PoP Test Channel',true)
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO device_types (id,channel_id,code,name,is_active) VALUES
      ('{p["device_type"]}','{p["channel"]}','BEH-POP-DT','PoP Test DeviceType',true)
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO physical_devices (id,store_id,device_type_id,code,serial_number,status) VALUES
      ('{p["device"]}','{p["store"]}','{p["device_type"]}','BEH-POP-DEV','POP-SN-001','active')
      ON CONFLICT (code) DO NOTHING
    -- Advertiser org + creative asset
    ; INSERT INTO advertiser_organizations (id,code,legal_name,display_name,status) VALUES
      ('{p["adv_org"]}','BEH-POP-ADV','PoP Test Advertiser LLC','PoP Test Advertiser','active')
      ON CONFLICT (code) DO NOTHING
    ; INSERT INTO creative_assets (id,advertiser_organization_id,code,name,media_type,
        storage_bucket,storage_key,sha256_checksum,file_size_bytes,duration_ms,status,moderation_status)
      VALUES
      ('{p["creative"]}','{p["adv_org"]}','BEH-POP-CR','PoP Test Creative','video/mp4',
       'test-bucket','test-key.mp4','sha256:deadbeef',1024,5000,'ready','approved')
      ON CONFLICT (advertiser_organization_id,code) DO NOTHING
    -- Campaign (for campaign_id FK — soft, but useful for accepted-event tests)
    ; INSERT INTO campaigns (id,advertiser_organization_id,code,name,status,created_by) VALUES
      ('{p["campaign"]}','{p["adv_org"]}','BEH-POP-CAMP','PoP Test Campaign','approved','{USER_IDS["advertiser"]}')
      ON CONFLICT (code) DO NOTHING
    """


_POP_CLEANUP = """
    DELETE FROM pop_events_raw WHERE event_id LIKE 'beh-pop-%'
    ; DELETE FROM pop_dedup_index WHERE event_id LIKE 'beh-pop-%'
    ; DELETE FROM pop_ingestion_batches WHERE id LIKE 'beh-pop-%'
    ; DELETE FROM physical_devices WHERE code='BEH-POP-DEV'
    ; DELETE FROM device_types WHERE code='BEH-POP-DT'
    ; DELETE FROM channels WHERE code='BEH-POP-CH'
    ; DELETE FROM stores WHERE code='BEH-POP-ST'
    ; DELETE FROM clusters WHERE code='BEH-POP-CL'
    ; DELETE FROM branches WHERE code='BEH-POP-BR'
    ; DELETE FROM campaign_creatives WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE code='BEH-POP-CAMP'
    )
    ; DELETE FROM campaign_flights WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE code='BEH-POP-CAMP'
    )
    ; DELETE FROM campaign_placements WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE code='BEH-POP-CAMP'
    )
    ; DELETE FROM campaign_approvals WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE code='BEH-POP-CAMP'
    )
    ; DELETE FROM campaign_status_history WHERE campaign_id IN (
        SELECT id FROM campaigns WHERE code='BEH-POP-CAMP'
    )
    ; DELETE FROM campaigns WHERE code='BEH-POP-CAMP'
    ; DELETE FROM creative_assets WHERE code='BEH-POP-CR'
    ; DELETE FROM advertiser_organizations WHERE code='BEH-POP-ADV'
"""


@pytest.fixture
def pop_fixtures(db_available):
    asyncio.run(_run_sql(_setup_pop_sql()))
    yield POP_IDS
    asyncio.run(_run_sql(_POP_CLEANUP))
