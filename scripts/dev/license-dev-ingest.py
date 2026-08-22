"""
EPIC-L — Dev/test license ingest (Layer 1).

Idempotent dev-ingest fixture for the seat ledger. NOT a production endpoint
and NOT an implementation of license.upload.

Fail-closed contract:
- Runs ONLY when BOTH:
    * ENVIRONMENT is dev/development/local/test, AND
    * LICENSE_DEV_INGEST_ENABLED is true/1/yes
  otherwise it exits non-zero WITHOUT touching the database.
- Creates a single deterministic grant with source='dev-ingest'.
- Re-running is idempotent: the deterministic license_id is upserted, so no
  duplicate grants are created.
- Produces no seats — enrollment reserve happens later (A2).

Usage:
    ENVIRONMENT=dev LICENSE_DEV_INGEST_ENABLED=true \
        python3 scripts/dev/license-dev-ingest.py
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

# Deterministic dev-ingest grant identity.
DEV_LICENSE_ID = "dev-ingest-0001"
DEV_LICENSEE_ID = "dev-operator-0001"
DEV_LICENSEE_NAME = "DEV Operator (dev-ingest)"
DEV_TIER = "dev"
DEV_MAX_DEVICES = 1000
DEV_OVERAGE_ALLOWANCE = 100
DEV_GRACE_DAYS = 0
DEV_FEATURES = ["seat_ledger", "soft_enforcement"]


def _env_allowed() -> bool:
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env not in ("dev", "development", "local", "test"):
        return False
    flag = os.environ.get("LICENSE_DEV_INGEST_ENABLED", "").lower()
    return flag in ("true", "1", "yes")


async def _ingest() -> int:
    if not _env_allowed():
        print(
            "ERROR: dev-ingest license refused. "
            "Requires ENVIRONMENT in (dev,development,local,test) AND "
            "LICENSE_DEV_INGEST_ENABLED=true.",
            file=sys.stderr,
        )
        return 2

    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        db_url = (
            "postgresql+asyncpg://retail_media:retail_media_dev"
            "@localhost:5432/retail_media_platform"
        )

    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.begin() as conn:
            # Dev-ingest runs as owner/admin context — this is a fixture path,
            # not an app request. Set admin GUC so RLS admits the write.
            await conn.execute(
                text("SELECT set_config('app.rmp_is_admin', 'true', true)")
            )
            now = datetime.now(timezone.utc)
            await conn.execute(
                text(
                    """
                    INSERT INTO license_grants (
                        id, license_id, licensee_id, licensee_name, tier,
                        issued_at, valid_from, valid_until,
                        max_devices, overage_allowance, grace_days,
                        features, installation_binding, nonce,
                        schema_version, kid, source, status
                    ) VALUES (
                        :id, :license_id, :licensee_id, :licensee_name, :tier,
                        :issued_at, :valid_from, :valid_until,
                        :max_devices, :overage_allowance, :grace_days,
                        CAST(:features AS jsonb), :binding, :nonce,
                        :schema_version, :kid, 'dev-ingest', 'current'
                    )
                    ON CONFLICT (license_id) DO NOTHING
                    """
                ),
                {
                    "id": "00000000-0000-0000-0000-000000000400",
                    "license_id": DEV_LICENSE_ID,
                    "licensee_id": DEV_LICENSEE_ID,
                    "licensee_name": DEV_LICENSEE_NAME,
                    "tier": DEV_TIER,
                    "issued_at": now,
                    "valid_from": now,
                    "valid_until": None,  # perpetual dev license
                    "max_devices": DEV_MAX_DEVICES,
                    "overage_allowance": DEV_OVERAGE_ALLOWANCE,
                    "grace_days": DEV_GRACE_DAYS,
                    "features": json.dumps(DEV_FEATURES),
                    "binding": "dev-installation",
                    "nonce": None,
                    "schema_version": 1,
                    "kid": "dev-ingest-key",
                },
            )
        print(f"Dev-ingest license '{DEV_LICENSE_ID}' ensured (source=dev-ingest).")
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    return asyncio.run(_ingest())


if __name__ == "__main__":
    sys.exit(main())
