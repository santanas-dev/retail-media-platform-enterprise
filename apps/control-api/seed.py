"""
Retail Media Platform — Dev/Demo Seed.

Phase 2: Creates one minimal hierarchy for local development and testing.
Idempotent: safe to run multiple times (ON CONFLICT DO NOTHING).

Usage:
    DATABASE_URL=postgresql+asyncpg://... python apps/control-api/seed.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

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
    "advertisers.read":       "00000000-0000-0000-0000-000000000108",
    "advertisers.manage":     "00000000-0000-0000-0000-000000000109",
    "advertisers.contacts.read":  "00000000-0000-0000-0000-00000000010a",
    "advertisers.contacts.manage": "00000000-0000-0000-0000-00000000010b",
}
SEED_ROLE_IDS = {
    "system_admin":    "00000000-0000-0000-0000-000000000110",
    "security_admin":  "00000000-0000-0000-0000-000000000111",
    "operator":         "00000000-0000-0000-0000-000000000112",
    "analyst":          "00000000-0000-0000-0000-000000000113",
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


def _rp(n: int) -> str:
    """Generate deterministic role_permission UUID from numeric suffix."""
    return f"00000000-0000-0000-0000-{n:012d}"


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
VALUES ('{_rp(205)}', '{SEED_ROLE_IDS["operator"]}', '{SEED_PERM_IDS["advertisers.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- analyst: audit.read, organization.read, channels.read, devices.read
INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(151)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["audit.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(152)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["organization.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(153)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["channels.read"]}')
ON CONFLICT (role_id, permission_id) DO NOTHING;

INSERT INTO role_permissions (id, role_id, permission_id)
VALUES ('{_rp(154)}', '{SEED_ROLE_IDS["analyst"]}', '{SEED_PERM_IDS["devices.read"]}')
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

-- NOTE: No local_credentials, refresh_sessions, login_attempts,
--       or password_reset_tokens are seeded — these contain sensitive
--       material (password hashes, tokens) and must NOT appear in dev seed.

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
"""


async def seed():
    engine = create_engine()
    async with engine.begin() as conn:
        for statement in SEED_SQL.strip().split(";\n"):
            stmt = statement.strip()
            if stmt:
                await conn.execute(text(stmt + ";"))
    await engine.dispose()
    print("Seed complete: 1 branch → 1 cluster → 1 store → 1 KSO device → 1 surface "
          "+ 12 permissions, 4 roles, 25 role-permissions, 1 break-glass admin, "
          "1 advertiser org + 1 advertiser user, 2 brands, 1 contract, 2 contacts")


if __name__ == "__main__":
    asyncio.run(seed())
