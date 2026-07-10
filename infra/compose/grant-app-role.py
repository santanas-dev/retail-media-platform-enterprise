#!/usr/bin/env python3
"""S-019: Grant table/sequence privileges to retail_media_app after migrations + seed.

Run by db-setup service with the owner/migration DATABASE_URL.
Must execute AFTER alembic upgrade head + seed.py.
Idempotent — safe to re-run.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.domain.database import create_engine, grant_app_role_privileges


async def _main() -> None:
    engine = create_engine()
    try:
        result = await grant_app_role_privileges(engine, dev_mode=True)
        print(
            f"S-019 grant: {result['granted_tables']} tables, "
            f"{result['granted_sequences']} sequences"
        )
        if result["errors"]:
            print("WARNING: grant_app_role_privileges had errors — "
                  "retail_media_app may not have table access", file=sys.stderr)
            sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
