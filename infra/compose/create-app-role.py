#!/usr/bin/env python3
"""Create + grant the app runtime role (NOBYPASSRLS) for the PILOT stack.

IMAGE-REGISTRY-001 — STAGED FIX (not yet wired into the compose).

The dev stack creates ``retail_media_app`` via ``init-db.sql`` (bind-mounted
into the postgres container). The pilot compose forbids source bind mounts, so
there is no init-db mount — which means the v0.11.1-pilot-packaging compose
does NOT create the app role (a discovered gap).

This script is the proper fix: it creates the role as part of the migration
one-shot under the owner credential. It is STAGED for the next patch release —
wiring it into db-migrate requires a new image (the script must be baked via
``COPY infra/compose/``), which is out of scope for IMAGE-REGISTRY-001 (no new
tag/release). Until then, the verify workflow provisions the role manually.

Idempotent — safe to re-run. Password is taken from ``POSTGRES_APP_PASSWORD``
(env).
"""

import asyncio
import os
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.domain.database import create_engine  # noqa: E402

APP_USER = os.environ.get("POSTGRES_APP_USER", "retail_media_app").strip()
APP_PASSWORD = os.environ.get("POSTGRES_APP_PASSWORD", "").strip()

# Identifiers/password are interpolated (CREATE ROLE has no bind params).
# Escape single quotes defensively; passwords are generated hex so this is a
# safety net, not the primary control.
_APP_USER_Q = APP_USER.replace("'", "''")
_APP_PASSWORD_Q = APP_PASSWORD.replace("'", "''")


async def _main() -> None:
    if not APP_USER:
        print("ERROR: POSTGRES_APP_USER is empty", file=sys.stderr)
        sys.exit(1)
    if not APP_PASSWORD:
        print("ERROR: POSTGRES_APP_PASSWORD is required to create the app role", file=sys.stderr)
        sys.exit(1)

    engine = create_engine()
    try:
        async with engine.begin() as conn:
            exists = await conn.execute(
                text("SELECT 1 FROM pg_roles WHERE rolname = :u"), {"u": APP_USER}
            )
            if exists.fetchone() is None:
                await conn.execute(text(
                    f"CREATE ROLE {_APP_USER_Q} LOGIN PASSWORD '{_APP_PASSWORD_Q}' "
                    f"NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
                ))
                print(f"create-app-role: created role {APP_USER} (NOBYPASSRLS)")
            else:
                print(f"create-app-role: role {APP_USER} already exists")

            db_name = (await conn.execute(text("SELECT current_database()"))).scalar()
            await conn.execute(text(f"GRANT CONNECT ON DATABASE {db_name} TO {_APP_USER_Q}"))
            await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {_APP_USER_Q}"))
            await conn.execute(text(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {_APP_USER_Q}"
            ))
            await conn.execute(text(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                f"GRANT USAGE, SELECT ON SEQUENCES TO {_APP_USER_Q}"
            ))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
