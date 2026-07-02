"""
Retail Media Platform — API Dependencies.

Phase 3.0: Database session dependency.

TODO(auth): Add JWT/SSO auth dependency when identity is implemented.
All endpoints are currently unprotected — open for development.
"""

from packages.domain.database import get_global_engine, get_session


async def get_db():
    """Yield an async SQLAlchemy session, auto-close on exit."""
    engine = get_global_engine()
    async with get_session(engine) as session:
        yield session
