"""
Retail Media Platform — Database Configuration.

Phase 2: SQLAlchemy async engine factory + lifecycle helpers.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import AsyncAdaptedQueuePool

# Read from environment; no default production credentials
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

# ---------------------------------------------------------------------------
# Connection pool configuration (S-068)
# ---------------------------------------------------------------------------
DB_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE_SECONDS = int(os.environ.get("DB_POOL_RECYCLE_SECONDS", "1800"))


def _validate_pool_config(env: str) -> None:
    """Raise ValueError if pool config is unsafe for the given environment."""
    if DB_POOL_SIZE < 1:
        raise ValueError(f"DB_POOL_SIZE must be >= 1, got {DB_POOL_SIZE}")
    if DB_MAX_OVERFLOW < 0:
        raise ValueError(f"DB_MAX_OVERFLOW must be >= 0, got {DB_MAX_OVERFLOW}")
    if DB_POOL_TIMEOUT < 1:
        raise ValueError(f"DB_POOL_TIMEOUT must be >= 1, got {DB_POOL_TIMEOUT}")
    if DB_POOL_RECYCLE_SECONDS < 60:
        raise ValueError(
            f"DB_POOL_RECYCLE_SECONDS must be >= 60, got {DB_POOL_RECYCLE_SECONDS}"
        )


def _pool_kwargs() -> dict:
    """Return the keyword arguments for create_async_engine pool config."""
    return {
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": DB_POOL_SIZE,
        "max_overflow": DB_MAX_OVERFLOW,
        "pool_timeout": DB_POOL_TIMEOUT,
        "pool_recycle": DB_POOL_RECYCLE_SECONDS,
    }

# ---------------------------------------------------------------------------
# Engine registry — modules import engine from here, not from control-api main
# ---------------------------------------------------------------------------
_global_engine = None


def set_global_engine(engine) -> None:
    global _global_engine
    _global_engine = engine


def get_global_engine():
    return _global_engine


def create_engine(url: str | None = None):
    """Create async SQLAlchemy engine with configurable pool (S-068)."""
    target = url or DATABASE_URL
    kwargs = _pool_kwargs() if _uses_queue_pool(target) else {}
    return create_async_engine(target, echo=False, **kwargs)


def _uses_queue_pool(url: str) -> bool:
    """Return True if the URL dialect supports QueuePool (PostgreSQL)."""
    return "postgresql" in url or "asyncpg" in url


def create_session_factory(engine=None):
    """Create async session factory."""
    eng = engine or create_engine()
    return async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)


async def check_db_health(engine, timeout: float = 2.0) -> tuple[bool, str | None]:
    """Run SELECT 1 to verify database connectivity.

    Returns (ok, error_code) tuple.
    Never includes DATABASE_URL in the returned error message.
    """
    if engine is None:
        return False, "no_engine"

    try:
        async with engine.connect() as conn:
            await asyncio.wait_for(
                conn.execute(text("SELECT 1")),
                timeout=timeout,
            )
        return True, None
    except asyncio.TimeoutError:
        return False, "timeout"
    except Exception:
        return False, "connection_failed"


async def check_db_role_safety(engine, dev_mode: bool = False) -> tuple[bool, dict]:
    """Verify the current DB role is safe for RLS enforcement.

    In production, the role MUST be non-superuser and NOBYPASSRLS.
    In dev mode, violations are reported but not fatal.

    Returns (ok, checks_dict).  Checks dict has:
        {"db_role": "ok" | "unsafe", "db_role_details": str}
    Never leaks DATABASE_URL or secrets.
    """
    if engine is None:
        return False, {
            "db_role": "unhealthy",
            "db_role_details": "no database engine",
        }

    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT rolsuper, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            )
            row = result.fetchone()
    except Exception:
        return False, {
            "db_role": "unhealthy",
            "db_role_details": "cannot query pg_roles",
        }

    if row is None:
        return False, {
            "db_role": "unhealthy",
            "db_role_details": "pg_roles row not found",
        }

    is_super = row[0]
    has_bypassrls = row[1]

    issues = []
    if is_super:
        issues.append("superuser")
    if has_bypassrls:
        issues.append("BYPASSRLS")

    if not issues:
        return True, {"db_role": "ok", "db_role_details": "non-superuser, NOBYPASSRLS"}

    detail = f"role has {', '.join(issues)}"
    if dev_mode:
        # Report but don't fail in dev
        return True, {"db_role": "ok", "db_role_details": f"dev: {detail}"}

    return False, {"db_role": "unsafe", "db_role_details": detail}


@asynccontextmanager
async def get_session(engine):
    """Yield an async session, auto-close on exit."""
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session


async def set_worker_admin_context(session) -> None:
    """Set admin RLS context for background workers.

    S-019: Workers (orchestrator, outbox relay, campaign consumer) do not
    go through FastAPI middleware and therefore have no ScopeContext.
    They operate system-wide — reading all tenants' outbox events and
    campaign data.  This helper sets app.rmp_is_admin=true on the
    current transaction so RLS policies grant full visibility.

    Call AFTER the transaction has begun (i.e. inside an async session
    context), before any RLS-protected queries.

    Deferred (ADR-009 §9): per-worker scope resolution from job payloads
    is Phase 3.6.  For the pilot, a single admin context suffices.
    """
    from sqlalchemy import text
    await session.execute(text("SET LOCAL app.rmp_is_admin = 'true'"))


async def grant_app_role_privileges(engine, dev_mode: bool = False) -> dict:
    """Grant DML privileges to retail_media_app after migrations/seed.

    S-019: Runs as part of db-setup to ensure the app runtime role has
    access to all tables created by Alembic migrations.  Must execute
    with the owner/migration role (which owns the tables).

    Returns a dict with counts: {granted_tables, granted_sequences, errors}.
    Never leaks connection strings or role passwords.
    """
    from sqlalchemy import text
    result = {"granted_tables": 0, "granted_sequences": 0, "errors": 0}

    try:
        async with engine.connect() as conn:
            # Grant on all existing tables
            await conn.execute(text(
                "GRANT SELECT, INSERT, UPDATE, DELETE "
                "ON ALL TABLES IN SCHEMA public TO retail_media_app"
            ))
            # Grant on all existing sequences
            await conn.execute(text(
                "GRANT USAGE, SELECT "
                "ON ALL SEQUENCES IN SCHEMA public TO retail_media_app"
            ))
            await conn.commit()

            # Count tables granted
            count_row = await conn.execute(text(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            ))
            result["granted_tables"] = count_row.scalar() or 0

            # Count sequences granted
            seq_row = await conn.execute(text(
                "SELECT count(*) FROM information_schema.sequences "
                "WHERE sequence_schema = 'public'"
            ))
            result["granted_sequences"] = seq_row.scalar() or 0

    except Exception:
        if dev_mode:
            result["errors"] += 1
            import logging
            logging.getLogger("rmp.database").warning(
                "grant_app_role_privileges failed — "
                "retail_media_app may not have table access. "
                "Re-run after migrations complete."
            )
        else:
            raise

    return result
