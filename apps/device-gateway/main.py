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

from packages.observability.metrics import record_http_request, render_metrics
from packages.observability.rate_limit import check_rate_limit, get_rate_limit_key, DEVICE_MANIFEST_RATE_LIMIT
from packages.domain.database import (
    create_engine,
    get_global_engine,
    get_session,
    set_global_engine,
)
from packages.domain.repository import (
    get_latest_manifest_for_device,
    get_latest_manifest_metadata,
    get_physical_device_for_manifest_delivery,
)
from packages.infrastructure.redis_cache import get_manifest_cache, set_manifest_cache
from packages.observability import setup_logging, log_request_middleware
from packages.security.config import get_security_config, verify_metrics_auth
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
# Device RLS Context Dependency (EDGE-002-FU)
# ---------------------------------------------------------------------------


async def set_device_rls_context(
    device_id: str = Depends(get_device_id_from_token),
) -> str:
    """Set PostgreSQL RLS context for the device's retailer scope.

    Opens a short-lived owner session to resolve the device's
    retailer_id, then returns it so the endpoint can apply
    ``set_config('app.rmp_scope_retailer_ids', ...)`` on the
    request-scoped session BEFORE any tenant-scoped queries.

    Under NOBYPASSRLS (behavioural CI), this is required for the
    device to see its own rows in physical_devices and
    delivery_manifests — both tables are under FORCE RLS.

    Returns the retailer_id so it can be passed through to
    get_latest_manifest_for_device for the manifest payload.
    """
    from packages.domain.repository import get_device_retailer_id_and_status

    engine = get_global_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="Database not available")

    async with get_session(engine) as owner_session:
        row = await get_device_retailer_id_and_status(owner_session, device_id)

    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    retailer_id, device_status = row

    if device_status not in ("active", "online"):
        raise HTTPException(
            status_code=403,
            detail="Device not authorized",
        )

    return retailer_id


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
# HTTP metrics middleware — record every request
# ---------------------------------------------------------------------------
@app.middleware("http")
async def _metrics_middleware(request, call_next):
    response = await call_next(request)
    record_http_request(response.status_code)
    return response


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
    retailer_id: str = Depends(set_device_rls_context),
    session: AsyncSession = Depends(get_db),
):
    """Return the latest manifest for the authenticated device, or 404.

    200: manifest JSON with ETag header
    304: If-None-Match matches current content_hash (lightweight metadata check)
    404: no manifest or device not found
    401: invalid/expired/missing device token
    403: device not authorized
    429: rate limited

    Performance: uses lightweight metadata query first (1 SELECT).
    Full manifest assembly (6+ queries + HMAC) only runs when content_hash
    differs from If-None-Match.
    """
    # EDGE-002-FU: Apply device RLS context on the session.
    # Under NOBYPASSRLS (behavioural CI), physical_devices and
    # delivery_manifests are under FORCE RLS.  The device's
    # retailer_id was already resolved by set_device_rls_context
    # via an owner-role session — we now set the scope on this
    # request session so subsequent queries can see the device's
    # own rows.
    from sqlalchemy import text
    await session.execute(
        text("SELECT set_config('app.rmp_scope_retailer_ids', :ids, true)"),
        {"ids": retailer_id},
    )
    await session.execute(
        text("SELECT set_config('app.rmp_is_admin', 'false', true)"),
    )

    # S-065: rate limit per device before any DB work
    rate_key = get_rate_limit_key(request, device_id)
    if not check_rate_limit(rate_key, DEVICE_MANIFEST_RATE_LIMIT):
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
        )

    # S-067: fast ETag path — lightweight metadata query (1 SELECT)
    meta = await get_latest_manifest_metadata(session, device_id)
    if meta is None:
        raise HTTPException(status_code=404, detail="No manifest available")

    if_none_match = request.headers.get("If-None-Match", "").strip('"')
    if if_none_match and meta["content_hash"] == if_none_match:
        return Response(
            status_code=304,
            headers={"ETag": f'"{meta["content_hash"]}"'},
        )

    # S-067: try Redis cache before full assembly
    cached = await get_manifest_cache(device_id)
    if cached is not None and cached.get("content_hash") == meta["content_hash"]:
        response_obj = JSONResponse(content=cached)
        response_obj.headers["ETag"] = f'"{cached["content_hash"]}"'
        return response_obj

    # Full manifest assembly (only when content changed + cache miss)
    manifest = await get_latest_manifest_for_device(session, device_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest available")

    # Cache for subsequent requests
    await set_manifest_cache(device_id, manifest)

    response_obj = JSONResponse(content=manifest)
    if manifest.get("content_hash"):
        response_obj.headers["ETag"] = f'"{manifest["content_hash"]}"'
    return response_obj


# ---------------------------------------------------------------------------
# Metrics Endpoint (Prometheus)
# ---------------------------------------------------------------------------


@app.get("/metrics")
async def metrics(request: Request, _auth=Depends(verify_metrics_auth)):
    """Prometheus-compatible metrics endpoint.  Requires metrics auth token
    in production; open in dev mode (dev_mode=True)."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(content=render_metrics(), media_type="text/plain; version=0.0.4")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DEVICE_GATEWAY_PORT", "8001"))
    logger.info("Starting %s on port %s", SERVICE_NAME, port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
