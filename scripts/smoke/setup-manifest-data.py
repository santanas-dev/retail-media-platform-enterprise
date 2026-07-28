#!/usr/bin/env python3
"""Setup manifest data for PLAYER-001B-FU smoke proof.

Idempotent: safe to run multiple times.
Creates a deterministic active campaign + manifest for the seed device.

Usage:
  DATABASE_URL=postgresql+asyncpg://... python scripts/smoke/setup-manifest-data.py
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# Ensure dev mode — SecurityConfig must not enforce production gates
os.environ.setdefault("ENVIRONMENT", "dev")

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://retail_media_owner:retail_media_owner_pass@localhost:5432/retail_media_platform",
)

SEED_CAMPAIGN_ID = "00000000-0000-0000-0000-000000000220"
SEED_DEVICE_ID = "00000000-0000-0000-0000-000000000020"
SEED_ADV_ORG_ID = "00000000-0000-0000-0000-000000000200"


async def _raw_exec(db_url: str, sql: str, params=None):
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', true)"))
        for stmt in sql.split(";"):
            s = stmt.strip()
            if s and not s.startswith("--"):
                await conn.execute(text(s), params or {})
    await engine.dispose()


async def _raw_sql(db_url: str, sql: str, params=None):
    engine = create_async_engine(db_url, echo=False)
    async with engine.connect() as conn:
        await conn.execute(text("SELECT set_config('app.rmp_is_admin', 'true', false)"))
        await conn.commit()
        result = await conn.execute(text(sql), params or {})
        rows = result.fetchall()
    await engine.dispose()
    return rows


async def prepare(db_url: str) -> bool:
    """Set up campaign + device state, generate manifests. Returns True if manifest generated."""
    # 1. Ensure campaign is approved
    await _raw_exec(
        db_url,
        "UPDATE campaigns SET status = 'approved' WHERE id = :cid",
        {"cid": SEED_CAMPAIGN_ID},
    )
    print("[1/5] campaign → approved")

    # 2. Ensure device is active
    await _raw_exec(
        db_url,
        "UPDATE physical_devices SET status = 'active' WHERE id = :did",
        {"did": SEED_DEVICE_ID},
    )
    print("[2/5] device → active")

    # 3. Update flight window to current time
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    end = now + timedelta(days=7)
    await _raw_exec(
        db_url,
        "UPDATE campaign_flights SET start_at = :start, end_at = :end WHERE campaign_id = :cid",
        {"start": start, "end": end, "cid": SEED_CAMPAIGN_ID},
    )
    print(f"[3/5] flight window {start.isoformat(timespec='seconds')} → {end.isoformat(timespec='seconds')}")

    # 4. Clear previous manifests
    await _raw_exec(
        db_url,
        """
        DELETE FROM delivery_attempts;
        DELETE FROM delivery_manifest_assets;
        DELETE FROM delivery_manifest_surfaces;
        DELETE FROM delivery_manifests;
        DELETE FROM delivery_plans;
        DELETE FROM outbox_events WHERE event_type LIKE 'delivery.manifest.%';
        """,
    )
    print("[4/5] cleared previous manifest data")

    # 5. Generate manifests
    from packages.domain.delivery import generate_manifests_for_campaign

    engine = create_async_engine(db_url, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SELECT set_config('app.rmp_scope_advertiser_ids', :ids, false)"),
            {"ids": SEED_ADV_ORG_ID},
        )
        result = await generate_manifests_for_campaign(session, SEED_CAMPAIGN_ID)
        await session.commit()

    await engine.dispose()

    count_rows = await _raw_sql(db_url, "SELECT COUNT(*) FROM delivery_manifests")
    count = count_rows[0][0] if count_rows else 0
    print(f"[5/5] manifests generated: {result.manifest_count} (DB count: {count})")

    return result.manifest_count >= 1


if __name__ == "__main__":
    db_url = DB_URL
    success = asyncio.run(prepare(db_url))
    if not success:
        print("FAILED: no manifests generated", file=sys.stderr)
        sys.exit(1)
    print("OK: manifest data ready for player client")
