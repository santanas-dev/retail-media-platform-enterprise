"""
EPIC-L — Grandfather seat reconciliation (Layer 1, task 001A2).

Idempotent dev/ops helper: for every active ``physical_devices`` row that has
no open seat, create one. Existing active devices are seated even if the fleet
already exceeds the current capacity (that overage is reported and only blocks
NEW enrollment). Inactive/unregistered devices are never seated.

This is NOT a production endpoint and NOT part of enrollment enforcement — it
is a data-integrity backfill for a fleet that predates the seat ledger. It is
not an implementation of license.upload.

Fail-closed contract (mirrors scripts/dev/license-dev-ingest.py):
- Runs ONLY when BOTH:
    * ENVIRONMENT is dev/development/local/test, AND
    * LICENSE_DEV_INGEST_ENABLED is true/1/yes
  otherwise it exits non-zero WITHOUT touching the database.

Usage:
    ENVIRONMENT=dev LICENSE_DEV_INGEST_ENABLED=true \\
        python3 scripts/dev/license-reconcile-seats.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime, timezone  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.domain.licensing_service import reconcile_existing_fleet  # noqa: E402


def _env_allowed() -> bool:
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env not in ("dev", "development", "local", "test"):
        return False
    flag = os.environ.get("LICENSE_DEV_INGEST_ENABLED", "").lower()
    return flag in ("true", "1", "yes")


async def _reconcile() -> int:
    if not _env_allowed():
        print(
            "ERROR: seat reconciliation refused. "
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
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                # Owner/admin context: this is a fixture/backfill path, not an
                # app request. Set admin GUC so RLS admits the writes.
                await session.execute(
                    text("SELECT set_config('app.rmp_is_admin', 'true', true)")
                )
                now = datetime.now(timezone.utc)
                result = await reconcile_existing_fleet(session, now=now)

        print(
            f"Reconciliation: scanned {result.scanned_active} active device(s), "
            f"created {result.created_seats} seat(s), "
            f"overage={'yes' if result.overage else 'no'}."
        )
        return 0
    finally:
        await engine.dispose()


def main() -> int:
    return asyncio.run(_reconcile())


if __name__ == "__main__":
    sys.exit(main())
