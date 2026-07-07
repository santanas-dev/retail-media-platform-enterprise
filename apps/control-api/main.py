"""
Retail Media Platform — Control API.

Phase 2.2: FastAPI skeleton with database readiness check.
No auth, no business endpoints.
"""

import os
import sys
from contextlib import asynccontextmanager

# Ensure shared packages are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from packages.observability import log_request_middleware, setup_logging
from packages.domain.database import check_db_health, check_db_role_safety, create_engine, set_global_engine
from packages.security.config import get_security_config

SERVICE_NAME = "control-api"
logger = setup_logging(SERVICE_NAME)

# ---------------------------------------------------------------------------
# Engine lifecycle — created once, shared across requests
# ---------------------------------------------------------------------------
_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    try:
        _engine = create_engine()
        set_global_engine(_engine)
        logger.info("Database engine created")
    except Exception:
        logger.exception("Failed to create database engine — service will start degraded")
        _engine = None
    yield
    if _engine:
        await _engine.dispose()
        logger.info("Database engine disposed")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RMP Control API",
    version="0.3.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)
app.middleware("http")(log_request_middleware)

# ---------------------------------------------------------------------------
# CORS — must be configured before routers
# ---------------------------------------------------------------------------
_cors_cfg = get_security_config()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_cfg.cors_allowed_origins,
    allow_credentials=_cors_cfg.cors_allow_credentials,
    allow_methods=_cors_cfg.cors_allowed_methods,
    allow_headers=_cors_cfg.cors_allowed_headers,
)

# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------

from packages.api.identity import router as identity_router
from packages.api.auth import router as auth_router
from packages.api.pop import router as pop_router

app.include_router(identity_router)
app.include_router(auth_router)
app.include_router(pop_router)


# ---------------------------------------------------------------------------
# Health Endpoints
# ---------------------------------------------------------------------------


@app.get("/health/live")
async def health_live():
    """Liveness: process is alive. No external dependency checks."""
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/health/ready")
async def health_ready():
    """Readiness: can the service serve traffic?

    Checks:
    - database: SELECT 1 via async SQLAlchemy
    - db_role: non-superuser, NOBYPASSRLS (production only; dev reports but
      does not fail on superuser/BYPASSRLS)
    """
    dev_mode = os.environ.get("ENVIRONMENT", "production") != "production"
    checks = {"database": "unhealthy", "db_role": "unhealthy"}

    if _engine is None:
        logger.warning("Readiness check: no database engine")
        return JSONResponse(
            content={"status": "degraded", "service": SERVICE_NAME, "checks": checks},
            status_code=503,
        )

    # Database connectivity
    db_ok, db_reason = await check_db_health(_engine, timeout=2.0)

    if db_ok:
        checks["database"] = "ok"
    else:
        logger.error("Readiness check: database unavailable (reason=%s)", db_reason)
        return JSONResponse(
            content={
                "status": "degraded",
                "service": SERVICE_NAME,
                "checks": checks,
                "db_error": "database_unavailable",
            },
            status_code=503,
        )

    # DB role safety (RLS enforcement)
    role_ok, role_info = await check_db_role_safety(_engine, dev_mode=dev_mode)
    checks.update(role_info)

    if not role_ok:
        logger.error("Readiness check: unsafe db role (info=%s)", role_info)
        return JSONResponse(
            content={
                "status": "degraded",
                "service": SERVICE_NAME,
                "checks": checks,
                "db_error": "unsafe_db_role",
            },
            status_code=503,
        )

    return {"status": "ok", "service": SERVICE_NAME, "checks": checks}


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("CONTROL_API_PORT", "8000"))
    logger.info("Starting %s on port %s", SERVICE_NAME, port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
