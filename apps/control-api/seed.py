"""
Retail Media Platform — Dev/Demo Seed.

Phase 2: Creates one minimal hierarchy for local development and testing.
Idempotent: safe to run multiple times (ON CONFLICT DO NOTHING).

Usage:
    DATABASE_URL=postgresql+asyncpg://... python apps/control-api/seed.py
"""

from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import bcrypt
from sqlalchemy import text
from packages.domain.database import create_engine


SEED_BRANCH_ID = "00000000-0000-0000-0000-000000000001"
SEED_CLUSTER_ID = "00000000-0000-0000-0000-000000000002"
SEED_STORE_ID = "00000000-0000-0000-0000-000000000003"
SEED_CHANNEL_ID = "00000000-0000-0000-0000-000000000010"
SEED_DEVICE_TYPE_ID = "00000000-0000-0000-0000-000000000011"
SEED_CAPABILITY_ID = "00000000-0000-0000-0000-000000000012"
SEED_DEVICE_ID = "00000000-0000-0000-0000-000000000020"
SEED_CARRIER_ID = "00000000-0000-0000-0000-000000000030"
SEED_SURFACE_ID = "00000000-0000-0000-0000-000000000031"

# Identity seed IDs (Phase 2.1)
SEED_PERM_IDS = {
    "users.read":      "00000000-0000-0000-0000-000000000100",
    "users.manage":    "00000000-0000-0000-0000-000000000101",
    "roles.read":      "00000000-0000-0000-0000-000000000102",
    "roles.manage":    "00000000-0000-0000-0000-000000000103",
    "audit.read":      "00000000-0000-0000-0000-000000000104",
    "organization.read": "00000000-0000-0000-0000-000000000105",
    "channels.read":   "00000000-0000-0000-0000-000000000106",
    "devices.read":    "00000000-0000-0000-0000-000000000107",
    "emergency.read":  "00000000-0000-0000-0000-000000000115",
    "emergency.manage":"00000000-0000-0000-0000-000000000116",
    "advertiser_applications.read":  "00000000-0000-0000-0000-000000000119",
    "advertiser_applications.review": "00000000-0000-0000-0000-00000000011a",
    "advertisers.read":       "00000000-0000-0000-0000-000000000108",
    "advertisers.manage":     "00000000-0000-0000-0000-000000000109",
    "advertisers.contacts.read":  "00000000-0000-0000-0000-00000000010a",
    "advertisers.contacts.manage": "00000000-0000-0000-0000-00000000010b",
    "campaigns.read":     "00000000-0000-0000-0000-00000000010c",
    "campaigns.manage":   "00000000-0000-0000-0000-00000000010d",
    "campaigns.approve":  "00000000-0000-0000-0000-00000000010e",
    "creatives.read":     "00000000-0000-0000-0000-00000000010f",
    "creatives.moderate": "00000000-0000-0000-0000-000000000117",
    "inventory.read":    "00000000-0000-0000-0000-000000000118",
    "inventory.manage":  "00000000-0000-0000-0000-000000000119",
}
SEED_ADV_ROLE_ID = "00000000-0000-0000-0000-000000000114"
SEED_ADV_USER_ROLE_ID = "00000000-0000-0000-0000-000000000204"

SEED_ROLE_IDS = {
    "system_admin":    "00000000-0000-0000-0000-000000000110",
    "security_admin":  "00000000-0000-0000-0000-000000000111",
    "operator":         "00000000-0000-0000-0000-000000000112",
    "analyst":          "00000000-0000-0000-0000-000000000113",
    "advertiser":       "00000000-0000-0000-0000-000000000114",
}
SEED_BG_USER_ID =      "00000000-0000-0000-0000-000000000150"
SEED_BG_USER_ROLE_ID = "00000000-0000-0000-0000-000000000160"

# Auth persistence seed IDs (Phase 3.2a)
SEED_ADV_ORG_ID =         "00000000-0000-0000-0000-000000000200"
SEED_ADV_MEMBERSHIP_ID =  "00000000-0000-0000-0000-000000000201"
SEED_ADV_USER_ID =        "00000000-0000-0000-0000-000000000202"

# Advertiser domain seed IDs (Phase 4.0b)
SEED_ADV_BRAND_1_ID =    "00000000-0000-0000-0000-000000000210"
SEED_ADV_BRAND_2_ID =    "00000000-0000-0000-0000-000000000211"
SEED_ADV_CONTRACT_ID =   "00000000-0000-0000-0000-000000000212"
SEED_ADV_CONTACT_1_ID =  "00000000-0000-0000-0000-000000000213"
SEED_ADV_CONTACT_2_ID =  "00000000-0000-0000-0000-000000000214"

# Campaign domain seed IDs (Phase 4.1b)
SEED_CAMPAIGN_ID =        "00000000-0000-0000-0000-000000000220"
SEED_CAMPAIGN_FLIGHT_ID = "00000000-0000-0000-0000-000000000221"
SEED_CREATIVE_ASSET_ID =  "00000000-0000-0000-0000-000000000222"
SEED_CAMPAIGN_CREATIVE_ID = "00000000-0000-0000-0000-000000000223"
SEED_CAMPAIGN_PLACEMENT_ID = "00000000-0000-0000-0000-000000000224"
SEED_CAMPAIGN_APPROVAL_ID  = "00000000-0000-0000-0000-000000000225"
SEED_CAMPAIGN_STATUS_HIST_ID = "00000000-0000-0000-0000-000000000226"


def _rp(n: int) -> str:
    """Generate deterministic role_permission UUID from numeric suffix."""
    return f"00000000-0000-0000-0000-{n:012d}"


# ── Dev credential helpers (S-016) ──

SEED_BG_CREDENTIAL_ID = "00000000-0000-0000-0000-000000000161"
SEED_ADV_CREDENTIAL_ID = "00000000-0000-0000-0000-000000000203"

_DEV_PASSWORDS = {
    "break_glass_admin": b"break-glass-dev-only",
    "advertiser_test": b"advertiser-dev-only",
}


def _hash_password(plain: bytes) -> str:
    """Return bcrypt hash of a plaintext password (12 rounds)."""
    return bcrypt.hashpw(plain, bcrypt.gensalt(rounds=12)).decode()


def _should_seed_credentials() -> bool:
    """Gate: seed dev credentials only in dev/test or with explicit opt-in.

    Returns True when:
      - ENVIRONMENT is dev/development/local
      - SEED_DEV_CREDENTIALS is true/1/yes
      - Running under pytest

    In production without the flag, returns False — credentials are skipped
    with a warning.
    """
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env in ("dev", "development", "local"):
        return True
    flag = os.environ.get("SEED_DEV_CREDENTIALS", "").lower()
    if flag in ("true", "1", "yes"):
        return True
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return True
    return False


def _build_credentials_sql() -> tuple[str, str, str]:
    """Build the local_credentials INSERT statements for seeded users.

    Returns (sql_fragment, bg_password_hash, adv_password_hash).
    Caller uses the hashes to log dev passwords in dev mode.
    """
    bg_hash = _hash_password(_DEV_PASSWORDS["break_glass_admin"])
    adv_hash = _hash_password(_DEV_PASSWORDS["advertiser_test"])
    sql = f"""
-- Pilot-local bootstrap credentials (S-016 — dual auth readiness)
-- DEV ONLY — seeded when ENVIRONMENT=dev or SEED_DEV_CREDENTIALS=true.
-- In production these must be overridden via env-provided password hashes
-- or an external secrets manager.  See docs/runbook/clean-install-login.md.

-- Break-glass admin credential
INSERT INTO local_credentials (id, user_id, credential_type, password_hash,
    password_hash_algorithm, must_change_password, status)
VALUES ('{SEED_BG_CREDENTIAL_ID}', '{SEED_BG_USER_ID}', 'local_break_glass',
    '{bg_hash}', 'bcrypt', true, 'active')
ON CONFLICT (user_id) DO NOTHING;

-- Test advertiser credential (product path — local_advertiser)
INSERT INTO local_credentials (id, user_id, credential_type, password_hash,
    password_hash_algorithm, must_change_password, status)
VALUES ('{SEED_ADV_CREDENTIAL_ID}', '{SEED_ADV_USER_ID}', 'local_advertiser',
    '{adv_hash}', 'bcrypt', true, 'active')
ON CONFLICT (user_id) DO NOTHING;
"""
    return sql, bg_hash, adv_hash


SEED_SQL = f"""
-- Organization
INSERT INTO branches (id, code, name, timezone)
VALUES ('{SEED_BRANCH_ID}', 'BR-001', 'Центральный филиал', 'Europe/Moscow')
ON CONFLICT (code) DO NOTHING;

INSERT INTO clusters (id, branch_id, code, name)
VALUES ('{SEED_CLUSTER_ID}', '{SEED_BRANCH_ID}', 'CL-001', 'Кластер Москва')
ON CONFLICT (code) DO NOTHING;

INSERT INTO stores (id, cluster_id, code, name, address, timezone)
VALUES ('{SEED_STORE_ID}', '{SEED_CLUSTER_ID}', 'ST-001', 'Магазин №42',
        'г. Москва, ул. Тестовая, д. 1', 'Europe/Moscow')
ON CONFLICT (code) DO NOTHING;

-- Channel model
INSERT INTO channels (id, code, name, description, sort_order)
VALUES ('{SEED_CHANNEL_ID}', 'KSO', 'Кассы самообслуживания',
        'Первый канал внедрения — экраны касс самообслуживания', 1)
ON CONFLICT (code) DO NOTHING;

INSERT INTO device_types (id, channel_id, code, name, player_runtime)
VALUES ('{SEED_DEVICE_TYPE_ID}', '{SEED_CHANNEL_ID}', 'KSO_V1',
        'КСО (x86 Linux + Chromium)', 'chromium')
ON CONFLICT (code) DO NOTHING;

INSERT INTO capability_profiles (id, device_type_id, code, resolution_w, resolution_h,
    orientation, supported_formats, max_file_size_bytes, max_duration_sec,
    supports_video, supports_animation, supports_interactive, pop_mode)
VALUES ('{SEED_CAPABILITY_ID}', '{SEED_DEVICE_TYPE_ID}', 'KSO_V1_DEFAULT',
        1440, 1080, 'landscape',
        '{{image/png,image/jpeg,image/webp,video/mp4}}'::text[],
        10485760, 30, true, false, false, 'real_playback')
ON CONFLICT (code) DO NOTHING;

-- Physical test KSO
INSERT INTO physical_devices (id, store_id, device_type_id, code, serial_number,
    status, cache_size_bytes)
VALUES ('{SEED_DEVICE_ID}', '{SEED_STORE_ID}', '{SEED_DEVICE_TYPE_ID}',
        'KSO-001', 'SN-KSO-TEST-001', 'unregistered', 0)
ON CONFLICT (code) DO NOTHING;

-- Logical carrier + display surface
INSERT INTO logical_carriers (id, physical_device_id, code, carrier_type)
VALUES ('{SEED_CARRIER_ID}', '{SEED_DEVICE_ID}', 'LC-KSO-001', 'direct')
ON CONFLICT (code) DO NOTHING;

INSERT INTO display_surfaces (id, logical_carrier_id, store_id, code,
    resolution_w, resolution_h)
VALUES ('{SEED_SURFACE_ID}', '{SEED_CARRIER_ID}', '{SEED_STORE_ID}',
        'SURF-001', 1440, 1080)
ON CONFLICT (code) DO NOTHING;

-- Identity / RBAC (Phase 2.1)
-- Permissions
INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["users.read"]}', 'users.read', 'Просмотр пользователей')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["users.manage"]}', 'users.manage', 'Управление пользователями')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["roles.read"]}', 'roles.read', 'Просмотр ролей')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["roles.manage"]}', 'roles.manage', 'Управление ролями')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["audit.read"]}', 'audit.read', 'Просмотр аудита')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["organization.read"]}', 'organization.read', 'Просмотр организации')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["channels.read"]}', 'channels.read', 'Просмотр каналов')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["devices.read"]}', 'devices.read', 'Просмотр устройств')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["emergency.read"]}', 'emergency.read', 'Просмотр аварийного режима')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["emergency.manage"]}', 'emergency.manage', 'Управление аварийным режимом')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["advertiser_applications.read"]}', 'advertiser_applications.read', 'Просмотр заявок рекламодателей')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["advertiser_applications.review"]}', 'advertiser_applications.review', 'Рассмотрение заявок рекламодателей')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["advertisers.read"]}', 'advertisers.read', 'Просмотр рекламодателей')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["advertisers.manage"]}', 'advertisers.manage', 'Управление рекламодателями')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["advertisers.contacts.read"]}', 'advertisers.contacts.read', 'Просмотр контактов рекламодателей')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["advertisers.contacts.manage"]}', 'advertisers.contacts.manage', 'Управление контактами рекламодателей')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["campaigns.read"]}', 'campaigns.read', 'Просмотр кампаний')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["campaigns.manage"]}', 'campaigns.manage', 'Управление кампаниями')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["campaigns.approve"]}', 'campaigns.approve', 'Согласование кампаний')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["creatives.read"]}', 'creatives.read', 'Просмотр креативов')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["creatives.moderate"]}', 'creatives.moderate', 'Модерация креативов')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["inventory.read"]}', 'inventory.read', 'Просмотр инвентаря')
ON CONFLICT (code) DO NOTHING;

INSERT INTO permissions (id, code, name)
VALUES ('{SEED_PERM_IDS["inventory.manage"]}', 'inventory.manage', 'Управление инвентарём')
ON CONFLICT (code) DO NOTHING;

-- Roles
INSERT INTO roles (id, code, name, description, is_system)
VALUES ('{SEED_ROLE_IDS["system_admin"]}', 'system_admin',
        'Системный администратор', 'Полный доступ ко всем функциям платформы', true)
ON CONFLICT (code) DO NOTHING;

INSERT INTO roles (id, code, name, description, is_system)
VALUES ('{SEED_ROLE_IDS["security_admin"]}', 'security_admin',
        'Администратор безопасности',
        'Управление пользователями, ролями и аудитом', true)
ON CONFLICT (code) DO NOTHING;

INSERT INTO roles (id, code, name, description, is_system)
VALUES ('{SEED_ROLE_IDS["operator"]}', 'operator',
        'Оператор', 'Просмотр организации, каналов и устройств', false)
ON CONFLICT (code) DO NOTHING;

INSERT INTO roles (id, code, name, description, is_system)
VALUES ('{SEED_ROLE_IDS["analyst"]}', 'analyst',
        'Аналитик', 'Просмотр аудита, организации, каналов и устройств', false)
ON CONFLICT (code) DO NOTHING;

-- Advertiser role — scoped, non-system role for advertiser portal access
INSERT INTO roles (id, code, name, description, is_system)
VALUES ('{SEED_ROLE_IDS["advertiser"]}', 'advertiser',
        'Рекламодатель', 'Доступ к личному кабинету рекламодателя: просмотр и управление своими кампаниями и креативами', false)
ON CONFLICT (code) DO NOTHING;

-- Role → Permission assignments
-- system_admin: all 8 permissions
INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(120)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["users.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(121)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["users.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(122)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["roles.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(123)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["roles.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(124)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["audit.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(125)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["organization.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(126)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["channels.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(127)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["devices.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(162)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["emergency.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(163)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["emergency.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(164)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["advertiser_applications.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(165)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["advertiser_applications.review"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(128)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["advertisers.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(129)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["advertisers.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(201)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["advertisers.contacts.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(202)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["advertisers.contacts.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(205)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["campaigns.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(206)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["campaigns.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(207)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["campaigns.approve"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(208)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["creatives.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(217)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["creatives.moderate"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(219)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["inventory.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(220)}', '{SEED_ROLE_IDS["system_admin"]}', '{SEED_PERM_IDS["inventory.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- security_admin: users.read, users.manage, roles.read, roles.manage, audit.read
INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(131)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["users.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(132)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["users.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(133)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["roles.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(134)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["roles.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(135)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["audit.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(203)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["advertisers.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(204)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["advertisers.contacts.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(209)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["campaigns.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(210)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["campaigns.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(211)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["campaigns.approve"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(212)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["creatives.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(218)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["creatives.moderate"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(221)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["inventory.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(222)}', '{SEED_ROLE_IDS["security_admin"]}', '{SEED_PERM_IDS["inventory.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;


-- operator: organization.read, channels.read, devices.read
INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(141)}', '{SEED_ROLE_IDS["operator"]}', '{SEED_PERM_IDS["organization.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(142)}', '{SEED_ROLE_IDS["operator"]}', '{SEED_PERM_IDS["channels.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(143)}', '{SEED_ROLE_IDS["operator"]}', '{SEED_PERM_IDS["devices.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(216)}', '{SEED_ROLE_IDS["operator"]}', '{SEED_PERM_IDS["advertisers.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(213)}', '{SEED_ROLE_IDS["operator"]}', '{SEED_PERM_IDS["campaigns.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;


-- analyst: audit.read, organization.read, channels.read, devices.read
INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(151)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["audit.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(152)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["organization.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(214)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["campaigns.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(215)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["creatives.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(153)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["channels.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(154)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["devices.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- advertiser: organization.read, advertisers.read, advertisers.contacts.read, campaigns.read, campaigns.manage, creatives.read
INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(250)}', '{SEED_ROLE_IDS["advertiser"]}', '{SEED_PERM_IDS["organization.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(251)}', '{SEED_ROLE_IDS["advertiser"]}', '{SEED_PERM_IDS["advertisers.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(252)}', '{SEED_ROLE_IDS["advertiser"]}', '{SEED_PERM_IDS["advertisers.contacts.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(253)}', '{SEED_ROLE_IDS["advertiser"]}', '{SEED_PERM_IDS["campaigns.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(254)}', '{SEED_ROLE_IDS["advertiser"]}', '{SEED_PERM_IDS["campaigns.manage"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(255)}', '{SEED_ROLE_IDS["advertiser"]}', '{SEED_PERM_IDS["creatives.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- Break-glass admin user (no auth implementation — record only)
INSERT INTO users (id, code, username, email, display_name, auth_provider,
    status, is_break_glass)
VALUES ('{SEED_BG_USER_ID}', 'U-BG-001', 'break_glass_admin',
        'break_glass@retail-media.local',
        'Break-Glass Administrator', 'local_break_glass', 'active', true)
ON CONFLICT (username) DO NOTHING;

-- Assign system_admin to break-glass admin (unscoped — global role)
INSERT INTO user_roles (id, user_id, role_id)
VALUES ('{SEED_BG_USER_ROLE_ID}', '{SEED_BG_USER_ID}',
        '{SEED_ROLE_IDS["system_admin"]}')
ON CONFLICT (user_id, role_id) WHERE scope_type IS NULL AND scope_id IS NULL DO NOTHING;

-- Auth persistence (Phase 3.2a)

-- Test advertiser organization
INSERT INTO advertiser_organizations (id, code, legal_name, display_name)
VALUES ('{SEED_ADV_ORG_ID}', 'ADV-001',
        'ООО «Рекламный Альянс»', 'Рекламный Альянс')
ON CONFLICT (code) DO NOTHING;

-- Test advertiser user (no credential — record only)
INSERT INTO users (id, code, username, email, display_name, auth_provider,
    status, is_break_glass)
VALUES ('{SEED_ADV_USER_ID}', 'U-ADV-001', 'advertiser_test',
        'test@advertiser.example.com',
        'Тестовый Рекламодатель', 'local_advertiser', 'active', false)
ON CONFLICT (username) DO NOTHING;

-- Link advertiser user to organization
INSERT INTO advertiser_user_memberships (id, user_id, advertiser_organization_id)
VALUES ('{SEED_ADV_MEMBERSHIP_ID}', '{SEED_ADV_USER_ID}', '{SEED_ADV_ORG_ID}')
ON CONFLICT (user_id, advertiser_organization_id) DO NOTHING;

-- Assign advertiser role to advertiser_test (scoped to ADV-001).
-- get_user_permissions() now returns permissions from ALL roles regardless
-- of scope_type; tenant access is enforced by resolve_scope_context/RLS.
INSERT INTO user_roles (id, user_id, role_id, scope_type, scope_id)
VALUES ('{SEED_ADV_USER_ROLE_ID}', '{SEED_ADV_USER_ID}',
        '{SEED_ROLE_IDS["advertiser"]}', 'advertiser', '{SEED_ADV_ORG_ID}')
ON CONFLICT (user_id, role_id, scope_type, scope_id) DO NOTHING;

-- NOTE: local_credentials for break_glass_admin + advertiser_test are
-- seeded dynamically by the seed() function below when
-- _should_seed_credentials() returns True (ENVIRONMENT=dev or
-- SEED_DEV_CREDENTIALS=true).  In production without the flag they
-- are skipped — see docs/runbook/clean-install-login.md.

-- Advertiser domain foundation (Phase 4.0b)

-- Test brands for ADV-001
INSERT INTO advertiser_brands (id, advertiser_organization_id, code, name, description, status)
VALUES ('{SEED_ADV_BRAND_1_ID}', '{SEED_ADV_ORG_ID}', 'BRAND-COLA',
        'Cola Classic', 'Основной бренд — классическая кола', 'active')
ON CONFLICT (advertiser_organization_id, code) DO NOTHING;

INSERT INTO advertiser_brands (id, advertiser_organization_id, code, name, description, status)
VALUES ('{SEED_ADV_BRAND_2_ID}', '{SEED_ADV_ORG_ID}', 'BRAND-ZERO',
        'Cola Zero', 'Без сахара', 'active')
ON CONFLICT (advertiser_organization_id, code) DO NOTHING;

-- Test contract for ADV-001
INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name,
    contract_number, budget_limit_amount, budget_limit_currency, valid_from, status)
VALUES ('{SEED_ADV_CONTRACT_ID}', '{SEED_ADV_ORG_ID}', 'CTR-2026-001',
        'Годовой контракт 2026', '2026/ADV-001',
        5000000.00, 'RUB', '2026-01-01T00:00:00+03:00', 'active')
ON CONFLICT (advertiser_organization_id, code) DO NOTHING;

-- Test contacts for ADV-001
INSERT INTO advertiser_contacts (id, advertiser_organization_id, contact_type,
    full_name, email, phone, is_primary, status)
VALUES ('{SEED_ADV_CONTACT_1_ID}', '{SEED_ADV_ORG_ID}', 'primary',
        'Иван Петров', 'ivan@advertiser.example.com',
        '+7 (999) 123-45-67', true, 'active')
ON CONFLICT DO NOTHING;

INSERT INTO advertiser_contacts (id, advertiser_organization_id, contact_type,
    full_name, email, phone, is_primary, status)
VALUES ('{SEED_ADV_CONTACT_2_ID}', '{SEED_ADV_ORG_ID}', 'billing',
        'Мария Счетоводова', 'maria@advertiser.example.com',
        '+7 (999) 765-43-21', false, 'active')
ON CONFLICT DO NOTHING;

-- Campaign domain foundation (Phase 4.1b)

-- Test campaign for ADV-001
INSERT INTO campaigns (id, advertiser_organization_id, advertiser_brand_id,
    advertiser_contract_id, code, name, status, priority,
    start_at, end_at, timezone, created_by)
VALUES ('{SEED_CAMPAIGN_ID}', '{SEED_ADV_ORG_ID}', '{SEED_ADV_BRAND_1_ID}',
    '{SEED_ADV_CONTRACT_ID}', 'CAMP-2026-001', 'Тестовая кампания №1',
    'draft', 5,
    '2026-08-01 00:00:00+03', '2026-08-31 23:59:59+03', 'Europe/Moscow',
    '{SEED_ADV_USER_ID}')
ON CONFLICT DO NOTHING;

-- Test flight for CAMP-2026-001
INSERT INTO campaign_flights (id, campaign_id, name, start_at, end_at, priority)
VALUES ('{SEED_CAMPAIGN_FLIGHT_ID}', '{SEED_CAMPAIGN_ID}',
    'Основной пролёт', '2026-08-01 08:00:00+03', '2026-08-07 22:00:00+03', 0)
ON CONFLICT DO NOTHING;

-- Test creative asset (metadata only — no binary)
INSERT INTO creative_assets (id, advertiser_organization_id, code, name,
    media_type, storage_bucket, storage_key, sha256_checksum, file_size_bytes,
    duration_ms, resolution_w, resolution_h, status, created_by)
VALUES ('{SEED_CREATIVE_ASSET_ID}', '{SEED_ADV_ORG_ID}', 'CREATIVE-001',
    'Приветственный баннер', 'image/png', 'retail-media-creatives',
    'adv-001/creatives/001/welcome.png',
    'ff61a0aee58f05289a5d6f0eba484cbbc397777ad2bb9b12ba6e9ba154f40513',
    245760, null, 1440, 1080, 'ready', '{SEED_ADV_USER_ID}')
ON CONFLICT DO NOTHING;

-- Link creative to campaign
INSERT INTO campaign_creatives (id, campaign_id, creative_asset_id, sort_order)
VALUES ('{SEED_CAMPAIGN_CREATIVE_ID}', '{SEED_CAMPAIGN_ID}',
    '{SEED_CREATIVE_ASSET_ID}', 0)
ON CONFLICT DO NOTHING;

-- Test placement (targets display surface)
INSERT INTO campaign_placements (id, campaign_id, display_surface_id,
    share_of_voice_pct, status)
VALUES ('{SEED_CAMPAIGN_PLACEMENT_ID}', '{SEED_CAMPAIGN_ID}',
    '{SEED_SURFACE_ID}', 100, 'active')
ON CONFLICT DO NOTHING;

-- Test status history (creation + submission)
INSERT INTO campaign_status_history (id, campaign_id, old_status, new_status,
    changed_by, reason)
VALUES ('{SEED_CAMPAIGN_STATUS_HIST_ID}', '{SEED_CAMPAIGN_ID}',
    null, 'draft', '{SEED_ADV_USER_ID}', 'Campaign created via seed')
ON CONFLICT DO NOTHING;

"""


async def seed() -> None:
    engine = create_engine()
    async with engine.begin() as conn:
        for statement in SEED_SQL.strip().split(";\n"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt + ";"))
        # Conditionally seed local_credentials (S-016)
        if _should_seed_credentials():
            cred_sql, bg_hash, adv_hash = _build_credentials_sql()
            for stmt in cred_sql.strip().split(";\n"):
                s = stmt.strip()
                if s and not s.startswith("--"):
                    await conn.execute(text(s + ";"))
            print(f"Seeded local_credentials: break_glass_admin + advertiser_test "
                  f"(must_change_password=true)")
        else:
            print("WARNING: Skipping local_credentials seed — "
                  "ENVIRONMENT is not dev, SEED_DEV_CREDENTIALS is not true. "
                  "No users will be able to log in via local auth. "
                  "Set ENVIRONMENT=dev or SEED_DEV_CREDENTIALS=true to enable "
                  "dev credentials, or provide production password hashes via "
                  "LOCAL_CREDENTIALS_OVERRIDE (future).")
    await engine.dispose()
    print("Seed complete: 1 branch → 1 cluster → 1 store → 1 KSO device → 1 surface "
          "+ 16 permissions, 5 roles (incl advertiser), campaign role-permissions, 1 break-glass admin, "
          "1 advertiser org + 1 advertiser user (with advertiser role + scoped assignment), 2 brands, 1 contract, 2 contacts, "
          "1 campaign + 1 flight + 1 creative + 1 placement + 1 status history")


if __name__ == "__main__":
    asyncio.run(seed())
