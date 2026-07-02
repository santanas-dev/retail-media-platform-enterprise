"""
Retail Media Platform — Database Configuration.

Phase 2: SQLAlchemy async engine factory + lifecycle helpers.
"""
import asyncio
import os
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Read from environment; no default production credentials
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://retail_media:retail_media_dev@localhost:5432/retail_media_platform",
)

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
    """Create async SQLAlchemy engine."""
    target = url or DATABASE_URL
    return create_async_engine(target, echo=False)


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


@asynccontextmanager
async def get_session(engine):
    """Yield an async session, auto-close on exit."""
    factory = create_session_factory(engine)
    async with factory() as session:
        yield session
