"""
EPIC-L — License seat-ledger reconciliation (Layer 1, tasks 001A2 + 001A4).

DRY RUN (default): detect drift in the seat ledger and print findings. Performs
NO writes. Exit 0 when consistent, 1 when drift is found.

--apply: grandfather repair — create one open seat for every active device that
lacks one (idempotent). Runs ONLY when ENVIRONMENT ∈ dev/development/local/test
AND LICENSE_DEV_INGEST_ENABLED=true; otherwise exits 2 without touching the DB.
--apply never releases a seat of an active device and never deactivates devices.

Exit codes:
  0 — consistent (DRY RUN) / apply succeeded
  1 — drift found (DRY RUN)
  2 — configuration or runtime error (or --apply refused outside dev)

Usage:
    python3 scripts/dev/license-reconcile-seats.py            # DRY RUN
    ENVIRONMENT=dev LICENSE_DEV_INGEST_ENABLED=true \\
        python3 scripts/dev/license-reconcile-seats.py --apply
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import datetime, timezone  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.domain.licensing_service import (  # noqa: E402
    get_reconciliation_report,
    reconcile_existing_fleet,
)


def _env_allowed() -> bool:
    env = os.environ.get("ENVIRONMENT", "").lower()
    if env not in ("dev", "development", "local", "test"):
        return False
    flag = os.environ.get("LICENSE_DEV_INGEST_ENABLED", "").lower()
    return flag in ("true", "1", "yes")


def _db_url() -> str:
    db_url = os.environ.get("DATABASE_URL", "").strip()
    if not db_url:
        db_url = (
            "postgresql+asyncpg://retail_media:retail_media_dev"
            "@localhost:5432/retail_media_platform"
        )
    return db_url


async def _run(apply: bool) -> int:
    # Fail-closed: --apply must be refused BEFORE any DB connection in
    # non-dev environments.
    if apply and not _env_allowed():
        print(
            "ERROR: --apply refused. Requires ENVIRONMENT in "
            "(dev,development,local,test) AND "
            "LICENSE_DEV_INGEST_ENABLED=true.",
            file=sys.stderr,
        )
        return 2

    engine = create_async_engine(_db_url(), echo=False)
    try:
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            async with session.begin():
                now = datetime.now(timezone.utc)

                if not apply:
                    report = await get_reconciliation_report(session, now=now)
                    print(f"Reconciliation DRY RUN — consistent={report.consistent}")
                    print(f"  counts={report.counts}")
                    for finding in report.findings:
                        loc = ""
                        if finding.device_id:
                            loc += f" device={finding.device_id}"
                        if finding.seat_id:
                            loc += f" seat={finding.seat_id}"
                        print(
                            f"  [{finding.severity}] {finding.code}: "
                            f"{finding.message}{loc}"
                        )
                    return 0 if report.consistent else 1

                result = await reconcile_existing_fleet(session, now=now)
                print(
                    f"Reconciliation --apply: scanned {result.scanned_active} "
                    f"active device(s), created {result.created_seats} seat(s), "
                    f"overage={'yes' if result.overage else 'no'}."
                )
                return 0
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="License seat-ledger reconciliation (DRY RUN by default).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply grandfather repair (seat active devices without a seat).",
    )
    args = parser.parse_args()
    try:
        return asyncio.run(_run(apply=args.apply))
    except Exception as exc:  # noqa: BLE001 — surface a clean runtime code
        print(f"ERROR: reconciliation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
