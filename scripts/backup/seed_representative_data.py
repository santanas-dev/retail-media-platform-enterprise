#!/usr/bin/env python3
"""Representative deterministic dataset for the restore drill (SCOPE D).

Creates test-owned data (ID prefix `drill-`) spanning every Layer-1 domain so
the restore drill can prove more than "the schema round-trips":

  - advertiser org + legal requisites (INN/KPP/OGRN/bank)
  - brand + contacts
  - contract (metadata + PDF object in MinIO, with SHA-256)
  - campaign + flight + placement
  - creative metadata + binary object in MinIO + SHA
  - commerce tariff + order + order lines + payment status
  - device + heartbeat (last_heartbeat_at)
  - license grant + open + released seats (exact peak)
  - device status history
  - campaign status history + audit event

Idempotent: ON CONFLICT DO NOTHING. Never mutates seed identities.
Never prints secrets. Deterministic: fixed IDs, fixed content → stable SHA-256.

Usage:
    DATABASE_URL=postgresql://owner:***@host:5432/retail_media_platform \
    MINIO_ENDPOINT=localhost:9000 MINIO_ACCESS_KEY=... MINIO_SECRET_KEY=... \
    python scripts/backup/seed_representative_data.py
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

# psycopg2 + minio are imported lazily inside functions: this module is imported
# at module level by tests/integration/test_restore_drill_verify.py, which is
# *collected* by the generic python-tests CI job (which does not install
# psycopg2). Keep collection dependency-free.

DRILL_PREFIX = "drill-"

# Deterministic IDs (36-char varchar). Prefix 'drill-' guarantees no collision
# with seed (00000000-…) or behavioral (beh-…) identities.
IDS = {
    "retailer":       "drill-ret-0000000000000000000000001",
    "branch":         "drill-br-00000000000000000000000001",
    "cluster":        "drill-cl-00000000000000000000000001",
    "store":          "drill-st-00000000000000000000000001",
    "channel":        "drill-ch-00000000000000000000000001",
    "device_type":    "drill-dt-00000000000000000000000001",
    "device":         "drill-dev-0000000000000000000000001",
    "carrier":        "drill-lc-00000000000000000000000001",
    "surface":        "drill-ds-00000000000000000000000001",
    "org":            "drill-org-0000000000000000000000001",
    "brand":          "drill-brnd-000000000000000000000001",
    "contract":       "drill-cont-000000000000000000000001",
    "contact_prim":   "drill-cp-00000000000000000000000001",
    "contact_bill":   "drill-cb-00000000000000000000000001",
    "campaign":       "drill-camp-0000000000000000000000001",
    "flight":         "drill-fl-00000000000000000000000001",
    "placement":      "drill-pl-00000000000000000000000001",
    "creative":       "drill-cr-00000000000000000000000001",
    "camp_creative":  "drill-cc-00000000000000000000000001",
    "camp_hist":      "drill-csh-00000000000000000000000001",
    "tariff":         "drill-tar-00000000000000000000000001",
    "price_item":     "drill-pi-00000000000000000000000001",
    "order":          "drill-ord-0000000000000000000000001",
    "order_line":     "drill-ol-00000000000000000000000001",
    "license_grant":  "drill-lg-00000000000000000000000001",
    "license_seat_open":   "drill-ls-open-000000000000000000001",
    "license_seat_rel":    "drill-ls-rel-0000000000000000000001",
    "device_hist":    "drill-dsh-00000000000000000000000001",
    "audit":          "drill-au-00000000000000000000000001",
}

# Deterministic binary content → stable SHA-256 for the drill verification.
CONTRACT_PDF_BYTES = b"%PDF-1.4 DRILL contract placeholder - deterministic\n%%EOF\n"
CREATIVE_BYTES = b"\x89PNG\r\n\x1a\n" + b"DRILL-CREATIVE-BINARY" * 200

CONTRACT_STORAGE_KEY = "drill/contracts/drill-contract.pdf"
CREATIVE_STORAGE_KEY = "drill/creatives/drill-banner.png"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _connect(url: str):
    import psycopg2
    u = urlparse(url)
    return psycopg2.connect(
        host=u.hostname,
        port=u.port or 5432,
        user=u.username,
        password=u.password,
        dbname=u.path.lstrip("/"),
    )


def _exec(conn, sql: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def seed_database(conn) -> dict[str, int]:
    """Insert deterministic rows. Returns control-table row counts."""
    ids = IDS
    now = _now()
    contract_sha = _sha(CONTRACT_PDF_BYTES)
    creative_sha = _sha(CREATIVE_BYTES)

    sql = f"""
    INSERT INTO retailers (id, code, legal_name, display_name, status)
    VALUES ('{ids['retailer']}', 'DRILL-RET', 'ООО Дрилл Ритейл', 'Drill Retail', 'active')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO branches (id, code, name, timezone, is_active)
    VALUES ('{ids['branch']}', 'DRILL-BR', 'Drill Branch', 'Europe/Moscow', true)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO clusters (id, branch_id, code, name, is_active)
    VALUES ('{ids['cluster']}', '{ids['branch']}', 'DRILL-CL', 'Drill Cluster', true)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO stores (id, cluster_id, code, name, is_active)
    VALUES ('{ids['store']}', '{ids['cluster']}', 'DRILL-ST', 'Drill Store', true)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO channels (id, code, name, is_active)
    VALUES ('{ids['channel']}', 'DRILL-CH', 'Drill Channel', true)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO device_types (id, channel_id, code, name, player_runtime)
    VALUES ('{ids['device_type']}', '{ids['channel']}', 'DRILL-DT', 'Drill DeviceType', 'chromium')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO physical_devices (id, store_id, device_type_id, code,
        serial_number, hardware_fingerprint, status, health_state, last_heartbeat_at, retailer_id)
    VALUES ('{ids['device']}', '{ids['store']}', '{ids['device_type']}', 'DRILL-DEV',
        'DRILL-SN-0001', 'drill-fp-0001', 'active', 'healthy', '{now}', '{ids['retailer']}')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO device_status_history (id, physical_device_id, old_status, new_status, changed_at, reason, source)
    VALUES ('{ids['device_hist']}', '{ids['device']}', 'unregistered', 'active', '{now}', 'drill seed', 'drill')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO logical_carriers (id, physical_device_id, code, carrier_type)
    VALUES ('{ids['carrier']}', '{ids['device']}', 'DRILL-LC', 'direct')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO display_surfaces (id, logical_carrier_id, store_id, code, resolution_w, resolution_h)
    VALUES ('{ids['surface']}', '{ids['carrier']}', '{ids['store']}', 'DRILL-DS', 1440, 1080)
    ON CONFLICT (id) DO NOTHING;

    -- Advertiser org with legal requisites
    INSERT INTO advertiser_organizations (id, code, legal_name, display_name, status, retailer_id,
        legal_entity_type, legal_form, inn, legal_address, settlement_account,
        correspondent_account, bik, bank_name, kpp, ogrn)
    VALUES ('{ids['org']}', 'DRILL-ADV', 'ООО Дрилл Реклама', 'Drill Advertiser', 'active', '{ids['retailer']}',
        'legal', 'ooo', '7700000001', '125000, Москва, ул. Дрилла, д. 1',
        '40702810000000000001', '30101810000000000001', '044525001', 'АО Дрилл Банк', '770001001', '1234567890123')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO advertiser_brands (id, advertiser_organization_id, code, name, status)
    VALUES ('{ids['brand']}', '{ids['org']}', 'DRILL-BRAND', 'Drill Brand', 'active')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO advertiser_contacts (id, advertiser_organization_id, contact_type,
        full_name, email, phone, is_primary, status)
    VALUES
      ('{ids['contact_prim']}', '{ids['org']}', 'primary', 'Иван Дриллов', 'ivan@drill.example', '+7 900 000-00-01', true, 'active'),
      ('{ids['contact_bill']}', '{ids['org']}', 'billing', 'Мария Дриллова', 'maria@drill.example', '+7 900 000-00-02', false, 'active')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO advertiser_contracts (id, advertiser_organization_id, code, name,
        contract_number, budget_limit_amount, budget_limit_currency, status,
        file_storage_key, file_name, file_size_bytes, file_sha256, file_content_type, file_uploaded_at)
    VALUES ('{ids['contract']}', '{ids['org']}', 'DRILL-CONTRACT', 'Drill Contract',
        'DRILL-2026-0001', 1500000.00, 'RUB', 'active',
        '{CONTRACT_STORAGE_KEY}', 'drill-contract.pdf', {len(CONTRACT_PDF_BYTES)}, '{contract_sha}', 'application/pdf', '{now}')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO campaigns (id, advertiser_organization_id, advertiser_brand_id,
        advertiser_contract_id, code, name, status, priority,
        budget_limit_amount, budget_limit_currency, start_at, end_at, timezone)
    VALUES ('{ids['campaign']}', '{ids['org']}', '{ids['brand']}', '{ids['contract']}',
        'DRILL-CAMP-001', 'Drill Campaign', 'active', 3,
        500000.00, 'RUB', '{now}', '{now}', 'Europe/Moscow')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO campaign_flights (id, campaign_id, name, start_at, end_at, priority)
    VALUES ('{ids['flight']}', '{ids['campaign']}', 'Drill Flight', '2026-08-01T08:00:00+00', '2026-08-07T22:00:00+00', 0)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO campaign_placements (id, campaign_id, display_surface_id, share_of_voice_pct, status)
    VALUES ('{ids['placement']}', '{ids['campaign']}', '{ids['surface']}', 100, 'active')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO creative_assets (id, advertiser_organization_id, code, name,
        media_type, storage_bucket, storage_key, sha256_checksum, file_size_bytes,
        resolution_w, resolution_h, status, moderation_status)
    VALUES ('{ids['creative']}', '{ids['org']}', 'DRILL-CREATIVE', 'Drill Banner',
        'image/png', 'drill-creatives', '{CREATIVE_STORAGE_KEY}', '{creative_sha}', {len(CREATIVE_BYTES)},
        1440, 1080, 'ready', 'approved')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO campaign_creatives (id, campaign_id, creative_asset_id, sort_order)
    VALUES ('{ids['camp_creative']}', '{ids['campaign']}', '{ids['creative']}', 0)
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO campaign_status_history (id, campaign_id, old_status, new_status, changed_by, changed_at, reason)
    VALUES ('{ids['camp_hist']}', '{ids['campaign']}', null, 'active',
        '00000000-0000-0000-0000-000000000150', '{now}', 'drill seed')
    ON CONFLICT (id) DO NOTHING;

    -- Commerce
    INSERT INTO commerce_tariff_versions (id, code, name, status, valid_from, currency)
    VALUES ('{ids['tariff']}', 'DRILL-TARIFF', 'Drill Tariff', 'active', '2026-01-01', 'RUB')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO commerce_price_items (id, tariff_version_id, surface_id, billing_unit, unit_price_amount, currency)
    VALUES ('{ids['price_item']}', '{ids['tariff']}', '{ids['surface']}', 'surface_day', 1250.50, 'RUB')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO commerce_orders (id, advertiser_organization_id, code, status, payment_status,
        tariff_version_id, total_amount, currency)
    VALUES ('{ids['order']}', '{ids['org']}', 'DRILL-ORDER-001', 'confirmed', 'paid',
        '{ids['tariff']}', 125050.00, 'RUB')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO commerce_order_lines (id, order_id, surface_id, date_from, date_to,
        quantity_days, unit_price_amount, line_amount)
    VALUES ('{ids['order_line']}', '{ids['order']}', '{ids['surface']}', '2026-08-01', '2026-08-31',
        31, 1250.50, 38765.50)
    ON CONFLICT (id) DO NOTHING;

    -- License grant + open + released seat (exact peak = 2)
    INSERT INTO license_grants (id, license_id, licensee_id, licensee_name, tier,
        issued_at, valid_from, max_devices, source, status)
    VALUES ('{ids['license_grant']}', 'DRILL-LIC-0001', 'drill-licensee', 'Drill Licensee', 'premium',
        '{now}', '{now}', 10, 'dev-ingest', 'current')
    ON CONFLICT (license_id) DO NOTHING;

    INSERT INTO license_seats (id, license_id, device_id, reserved_at, released_at)
    VALUES
      ('{ids['license_seat_open']}', '{ids['license_grant']}', '{ids['device']}', '{now}', NULL),
      ('{ids['license_seat_rel']}', '{ids['license_grant']}', '{ids['device']}', '{now}', '{now}')
    ON CONFLICT (id) DO NOTHING;

    INSERT INTO audit_events_operational (id, actor_user_id, action, target_type, target_id, ip_address, details_json)
    VALUES ('{ids['audit']}', NULL, 'drill.seed', 'campaign', '{ids['campaign']}', '127.0.0.1',
        '{{"origin": "restore-drill"}}')
    ON CONFLICT (id) DO NOTHING;
    """
    _exec(conn, sql)

    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for tbl in (
            "advertiser_organizations", "advertiser_brands", "advertiser_contracts",
            "advertiser_contacts", "campaigns", "campaign_flights", "campaign_placements",
            "creative_assets", "campaign_creatives", "campaign_status_history",
            "commerce_tariff_versions", "commerce_price_items", "commerce_orders",
            "commerce_order_lines", "physical_devices", "device_status_history",
            "license_grants", "license_seats", "audit_events_operational",
        ):
            cur.execute(f"SELECT count(*) FROM {tbl} WHERE id LIKE '{DRILL_PREFIX}%'")
            counts[tbl] = cur.fetchone()[0]
    return counts


def seed_minio(env: dict[str, str]) -> dict[str, dict[str, str]]:
    """Upload deterministic contract PDF + creative binary. Returns key→sha map."""
    endpoint = env.get("MINIO_ENDPOINT", "localhost:9000")
    access = env.get("MINIO_ACCESS_KEY", "")
    secret = env.get("MINIO_SECRET_KEY", "")
    creative_bucket = env.get("CREATIVE_STORAGE_BUCKET", "retail-media-creatives")
    contract_bucket = env.get("CONTRACT_STORAGE_BUCKET", "retail-media-contracts")

    from minio import Minio
    client = Minio(endpoint, access_key=access, secret_key=secret, secure=False)

    for bucket in (creative_bucket, contract_bucket):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

    client.put_object(
        contract_bucket, CONTRACT_STORAGE_KEY,
        io.BytesIO(CONTRACT_PDF_BYTES), len(CONTRACT_PDF_BYTES),
        content_type="application/pdf",
    )
    client.put_object(
        creative_bucket, CREATIVE_STORAGE_KEY,
        io.BytesIO(CREATIVE_BYTES), len(CREATIVE_BYTES),
        content_type="image/png",
    )
    return {
        "contract_pdf_sha256": _sha(CONTRACT_PDF_BYTES),
        "creative_sha256": _sha(CREATIVE_BYTES),
        "contract_storage_key": CONTRACT_STORAGE_KEY,
        "creative_storage_key": CREATIVE_STORAGE_KEY,
        "contract_bucket": contract_bucket,
        "creative_bucket": creative_bucket,
    }


def main() -> int:
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        print("ERROR: DATABASE_URL is not set", file=sys.stderr)
        return 1

    conn = _connect(db_url)
    try:
        counts = seed_database(conn)
    finally:
        conn.close()

    print("=== Representative Dataset Seeded ===")
    for tbl, cnt in sorted(counts.items()):
        print(f"  {tbl}: {cnt} drill row(s)")

    # MinIO objects
    if os.environ.get("MINIO_ENDPOINT", "").strip():
        meta = seed_minio(dict(os.environ))
        print("=== MinIO Objects ===")
        print(f"  contract PDF: {meta['contract_storage_key']} (sha256={meta['contract_pdf_sha256'][:16]}…)")
        print(f"  creative:     {meta['creative_storage_key']} (sha256={meta['creative_sha256'][:16]}…)")

    print("=== Status: SUCCESS ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
