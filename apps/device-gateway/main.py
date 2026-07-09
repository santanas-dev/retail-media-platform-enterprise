"""
Retail Media Platform — Device Gateway.

Phase 4.2d: Device manifest delivery endpoint.
Serves manifest JSON to authenticated devices.
No generation, no PoP, no runtime logic.
"""

import os
import sys
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.database import (
    create_engine,
    get_global_engine,
    get_session,
    set_global_engine,
)
from packages.domain.repository import get_latest_manifest_for_device, get_physical_device_for_manifest_delivery
from packages.observability import setup_logging, log_request_middleware
from packages.security.config import get_security_config
from packages.security.jwt import verify_access_token

SERVICE_NAME = "device-gateway"
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
        logger.exception(
            "Failed to create database engine — service will start degraded"
        )
        _engine = None
    yield
    if _engine:
        await _engine.dispose()
        logger.info("Database engine disposed")


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_db():
    """FastAPI dependency — yield an async session."""
    engine = get_global_engine()
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="Database not available",
        )
    async with get_session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Device Authentication Dependency
# ---------------------------------------------------------------------------


async def get_device_id_from_token(request: Request) -> str:
    """Extract physical_device_id from Authorization: Bearer <JWT>.

    ADR-003: device JWT has sub=<device_id>, auth_provider="device".
    Rejects user tokens (auth_provider != "device"), expired/invalid tokens.
    Returns physical_device_id (UUID string).
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header[7:]  # strip "Bearer "
    try:
        claims = verify_access_token(token)
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired device token",
        )

    # ADR-003: device JWT has auth_provider="device"
    if claims.get("auth_provider") != "device":
        raise HTTPException(
            status_code=401,
            detail="Token is not a device token",
        )

    device_id = claims.get("sub")
    if not device_id:
        raise HTTPException(
            status_code=401,
            detail="Device token missing sub claim",
        )

    return device_id


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RMP Device Gateway",
    version="0.2.0",
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
# Health
# ---------------------------------------------------------------------------


@app.get("/health/live")
async def health_live():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/health/ready")
async def health_ready():
    engine = get_global_engine()
    db_ok = engine is not None
    return {
        "status": "ok" if db_ok else "degraded",
        "service": SERVICE_NAME,
        "checks": {
            "database": "ok" if db_ok else "no_engine",
            "redis": "not_configured",
            "event_bus": "not_configured",
        },
    }


# ---------------------------------------------------------------------------
# Manifest Delivery
# ---------------------------------------------------------------------------


@app.get("/api/v1/device/manifest/latest")
async def get_latest_manifest(
    request: Request,
    device_id: str = Depends(get_device_id_from_token),
    session: AsyncSession = Depends(get_db),
):
    """Return the latest manifest for the authenticated device, or 404.

    200: manifest JSON with ETag header
    304: If-None-Match matches current content_hash
    404: no manifest or device not found
    401: invalid/expired/missing device token
    403: device not active
    """
    device_status = await get_physical_device_for_manifest_delivery(session, device_id)
    if device_status is None:
        raise HTTPException(status_code=404, detail="Device not found")
    if device_status not in ("active", "online"):
        raise HTTPException(
            status_code=403,
            detail=f"Device is {device_status}",
        )

    manifest = await get_latest_manifest_for_device(session, device_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest available")

    # If-None-Match → 304 Not Modified
    if_none_match = request.headers.get("If-None-Match", "")
    if if_none_match and manifest.get("content_hash") == if_none_match:
        return Response(
            status_code=304,
            headers={"ETag": if_none_match},
        )

    response_obj = JSONResponse(content=manifest)
    if manifest.get("content_hash"):
        response_obj.headers["ETag"] = manifest["content_hash"]
    return response_obj


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DEVICE_GATEWAY_PORT", "8001"))
    logger.info("Starting %s on port %s", SERVICE_NAME, port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
