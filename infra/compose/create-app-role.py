#!/usr/bin/env python3
"""Create + grant the app runtime role (NOBYPASSRLS) for the PILOT stack.

IMAGE-REGISTRY-001; wired into the pilot ``db-migrate`` one-shot by RF-05.

The dev stack creates ``retail_media_app`` via ``init-db.sql`` (bind-mounted
into the postgres container). The pilot compose forbids source bind mounts, so
there is no init-db mount: this script, baked into the image with
``COPY infra/compose/``, creates the role under the owner credential before
``grant-app-role.py`` runs.

Idempotent — safe to re-run. Password is taken from ``POSTGRES_APP_PASSWORD``
(env) and used only when the role does not exist yet; rotating it later is a
separate ALTER ROLE by the operator.
"""

import asyncio
import os
import re
import sys

from sqlalchemy import text

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from packages.domain.database import create_engine  # noqa: E402

APP_USER = os.environ.get("POSTGRES_APP_USER", "retail_media_app").strip()
APP_PASSWORD = os.environ.get("POSTGRES_APP_PASSWORD", "").strip()

# CREATE ROLE takes no bind parameters, so the role name must be a plain
# identifier and the password a quoted literal.
_IDENT = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def _literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


async def _main() -> None:
    if not _IDENT.match(APP_USER):
        print("ERROR: POSTGRES_APP_USER must be a plain lowercase identifier", file=sys.stderr)
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
                # The statement carries the password: keep PostgreSQL from
                # logging it if it fails (default log_min_error_statement=error).
                # Only a superuser may change that setting; a CREATEROLE owner
                # proceeds without it.
                is_super = (await conn.execute(text(
                    "SELECT rolsuper FROM pg_roles WHERE rolname = current_user"
                ))).scalar()
                if is_super:
                    await conn.exec_driver_sql("SET LOCAL log_min_error_statement = panic")
                await conn.exec_driver_sql(
                    f"CREATE ROLE {APP_USER} LOGIN PASSWORD {_literal(APP_PASSWORD)} "
                    f"NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS"
                )
                print(f"create-app-role: created role {APP_USER} (NOBYPASSRLS)")
            else:
                # The password of an existing role is NOT changed here.
                print(f"create-app-role: role {APP_USER} already exists (password unchanged)")

            db_name = (await conn.execute(text("SELECT current_database()"))).scalar()
            await conn.exec_driver_sql(f"GRANT CONNECT ON DATABASE {_ident(db_name)} TO {APP_USER}")
            await conn.exec_driver_sql(f"GRANT USAGE ON SCHEMA public TO {APP_USER}")
            await conn.exec_driver_sql(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_USER}"
            )
            await conn.exec_driver_sql(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
                f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_USER}"
            )
    except Exception as exc:
        # Never print the exception text: SQLAlchemy appends the failed
        # statement, which may contain the password.
        sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or "-"
        print(f"ERROR: create-app-role failed ({type(exc).__name__}, SQLSTATE {sqlstate})", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
