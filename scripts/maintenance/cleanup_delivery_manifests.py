"""
Clean up old delivery_manifests rows (S-068).

Keeps the latest N manifests per device and manifests newer than a
retention threshold.  Never deletes the single most-recent manifest
for any device.

Safety gates:
  - Dry-run by default (DRY_RUN=1).  Set DRY_RUN=0 to actually delete.
  - Requires RUN_MAINTENANCE=1 to prevent accidental execution.

Usage:
  DRY_RUN=0 RUN_MAINTENANCE=1 \\
  DATABASE_URL=postgresql+asyncpg://... \\
  python scripts/maintenance/cleanup_delivery_manifests.py

Environment:
  DATABASE_URL             — PostgreSQL connection string (required)
  MANIFEST_RETENTION_COUNT — keep at most this many manifests per device (default 5)
  MANIFEST_RETENTION_DAYS  — keep manifests newer than this many days (default 90)
  DRY_RUN                  — 1 (default): preview only; 0: delete
  RUN_MAINTENANCE          — must be 1 to run
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

DRY_RUN = os.environ.get("DRY_RUN", "1") not in ("0", "false", "no")
RUN_MAINTENANCE = os.environ.get("RUN_MAINTENANCE", "") == "1"
RETENTION_COUNT = int(os.environ.get("MANIFEST_RETENTION_COUNT", "5"))
RETENTION_DAYS = int(os.environ.get("MANIFEST_RETENTION_DAYS", "90"))

# ---------------------------------------------------------------------------
# Bootstrap — add repo root to path so packages.* imports work
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


def _build_engine():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("ERROR: DATABASE_URL is required", file=sys.stderr)
        sys.exit(1)
    return create_async_engine(url, echo=False)


async def _count_devices(session: AsyncSession) -> int:
    """Count distinct physical_device_ids in delivery_manifests."""
    row = await session.execute(
        text("SELECT COUNT(DISTINCT physical_device_id) FROM delivery_manifests")
    )
    return row.scalar() or 0


async def _count_candidates(
    session: AsyncSession, cutoff: datetime
) -> int:
    """Count rows that are NOT the latest per device and older than cutoff."""
    row = await session.execute(
        text("""
            SELECT COUNT(*) FROM delivery_manifests dm
            WHERE dm.id NOT IN (
                SELECT DISTINCT ON (physical_device_id) id
                FROM delivery_manifests
                WHERE status = 'generated'
                ORDER BY physical_device_id, generated_at DESC
            )
            AND dm.generated_at < :cutoff
        """),
        {"cutoff": cutoff},
    )
    return row.scalar() or 0


async def _delete_candidates(
    session: AsyncSession, cutoff: datetime
) -> int:
    """Delete old non-latest manifests. Returns row count."""
    result = await session.execute(
        text("""
            DELETE FROM delivery_manifests
            WHERE id IN (
                SELECT dm.id FROM delivery_manifests dm
                WHERE dm.id NOT IN (
                    SELECT DISTINCT ON (physical_device_id) id
                    FROM delivery_manifests
                    WHERE status = 'generated'
                    ORDER BY physical_device_id, generated_at DESC
                )
                AND dm.generated_at < :cutoff
                LIMIT 10000
            )
        """),
        {"cutoff": cutoff},
    )
    return result.rowcount


async def main():
    if not RUN_MAINTENANCE:
        print("Set RUN_MAINTENANCE=1 to execute. Exiting.")
        return

    engine = _build_engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    async with factory() as session:
        devices = await _count_devices(session)
        candidates = await _count_candidates(session, cutoff)
        total = candidates

        print(f"Devices with manifests: {devices}")
        print(f"Retention: keep latest {RETENTION_COUNT} per device, "
              f"manifests newer than {RETENTION_DAYS} days")
        print(f"Cutoff: {cutoff.isoformat()}")
        print(f"Candidates for cleanup: {total}")
        print(f"Mode: {'DRY-RUN' if DRY_RUN else 'DELETE'}")

        if DRY_RUN:
            print("Dry-run complete. No rows deleted. Set DRY_RUN=0 to delete.")
            return

        if total == 0:
            print("Nothing to delete.")
            return

        # Safety: require RUN_MAINTENANCE for delete
        deleted = await _delete_candidates(session, cutoff)
        await session.commit()
        print(f"Deleted {deleted} rows from delivery_manifests.")


if __name__ == "__main__":
    asyncio.run(main())
