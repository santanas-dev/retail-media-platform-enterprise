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
from pydantic import BaseModel, Field
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
    record_device_heartbeat,
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
# Device RLS Context Dependency (EDGE-002-FU v4)
# ---------------------------------------------------------------------------


async def set_device_rls_context(
    device_id: str = Depends(get_device_id_from_token),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Bootstrap device RLS context on the request session.

    Production-safe bootstrap (no owner/bypass in request path):

    1. Set ``app.rmp_device_id = device_id`` — RLS policy on
       ``physical_devices`` allows SELECT when ``id`` matches this
       session variable (migration 023).

    2. Read ``retailer_id`` + ``status`` from ``physical_devices``
       — now visible because the bootstrap policy matches the row.

    3. Clear ``app.rmp_device_id`` — bootstrap served its purpose.

    4. Validate status (active/online).  Reject inactive/revoked.

    5. Set ``app.rmp_scope_retailer_ids = retailer_id`` so subsequent
       tenant-scoped queries (delivery_manifests, etc.) see only this
       retailer's data.

    Under NOBYPASSRLS (CI), the app role CANNOT bypass RLS, and no
    owner-role connection is used.  The bootstrap is a targeted,
    single-row-gated policy, not a general privilege elevation.
    """
    from sqlalchemy import text

    from packages.domain.repository import get_device_retailer_id_and_status

    # Step 1 — bootstrap: allow reading our own device row
    await session.execute(
        text("SELECT set_config('app.rmp_device_id', :id, true)"),
        {"id": device_id},
    )

    # Step 2 — read retailer_id + status (visible via bootstrap RLS)
    row = await get_device_retailer_id_and_status(session, device_id)

    # Step 3 — clear bootstrap
    await session.execute(
        text("SELECT set_config('app.rmp_device_id', '', true)"),
    )

    if row is None:
        raise HTTPException(status_code=404, detail="Device not found")

    retailer_id, device_status = row
    if device_status not in ("active", "online"):
        raise HTTPException(
            status_code=403,
            detail="Device not authorized",
        )

    # Step 4 — set permanent retailer scope for subsequent queries
    await session.execute(
        text(
            "SELECT set_config('app.rmp_scope_retailer_ids', :ids, true)"
        ),
        {"ids": retailer_id},
    )
    await session.execute(
        text("SELECT set_config('app.rmp_is_admin', 'false', true)"),
    )


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
    _rls: None = Depends(set_device_rls_context),
    session: AsyncSession = Depends(get_db),
):
    """Return the latest manifest for the authenticated device, or 404.

    200: manifest JSON with ETag header
    304: If-None-Match matches current content_hash (lightweight metadata check)
    404: no manifest or device not found
    401: invalid/expired/missing device token
    403: device not authorized
    429: rate limited

    RLS context is already set on the session by set_device_rls_context
    (EDGE-002-FU v4: production-safe device bootstrap via app.rmp_device_id).
    No owner/bypass session is used in the request path.

    Performance: uses lightweight metadata query first (1 SELECT).
    Full manifest assembly (6+ queries + HMAC) only runs when content_hash
    differs from If-None-Match.
    """

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

    # K1: runtime ETag includes emergency state so 304 doesn't serve stale
    # emergency.active=false after admin activation.
    runtime_etag = f'{meta["content_hash"]}:em:{meta["emergency_active"]}'

    if_none_match = request.headers.get("If-None-Match", "").strip('"')
    if if_none_match and runtime_etag == if_none_match:
        return Response(
            status_code=304,
            headers={"ETag": f'"{runtime_etag}"'},
        )

    # S-067: try Redis cache before full assembly.
    # K1: skip cache if emergency state differs from current — a cached
    # manifest would have stale emergency.active.
    cached = await get_manifest_cache(device_id)
    cache_emergency_ok = (
        cached is not None
        and cached.get("emergency", {}).get("active") == meta["emergency_active"]
    )
    if cache_emergency_ok and cached.get("content_hash") == meta["content_hash"]:
        response_obj = JSONResponse(content=cached)
        response_obj.headers["ETag"] = f'"{runtime_etag}"'
        return response_obj

    # Full manifest assembly (only when content changed + cache miss)
    manifest = await get_latest_manifest_for_device(session, device_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest available")

    # Cache for subsequent requests
    await set_manifest_cache(device_id, manifest)

    response_obj = JSONResponse(content=manifest)
    response_obj.headers["ETag"] = f'"{runtime_etag}"'
    return response_obj


# ---------------------------------------------------------------------------
# Device Heartbeat (EDGE-004)
# ---------------------------------------------------------------------------


class HeartbeatRequest(BaseModel):
    """Minimal device heartbeat payload.

    device_id is NEVER accepted from the client — it's extracted from the
    device JWT (sub claim) by get_device_id_from_token.
    """
    health_state: str = Field(default="healthy", max_length=32)
    runtime_version: str = Field(default="", max_length=64)
    player_version: str = Field(default="", max_length=128)


@app.post("/api/v1/device/heartbeat")
async def device_heartbeat(
    body: HeartbeatRequest,
    device_id: str = Depends(get_device_id_from_token),
    _rls: None = Depends(set_device_rls_context),
    session: AsyncSession = Depends(get_db),
):
    """Record a device heartbeat.

    Device JWT required; user/admin tokens rejected.
    device_id is extracted from JWT (not from payload).
    RLS context is set on the session by set_device_rls_context
    (EDGE-002-FU v4: production-safe device bootstrap).

    200: heartbeat recorded
    401: invalid/expired/missing/not-a-device token
    403: device not authorized (inactive/revoked)
    404: device not found
    """
    from datetime import datetime, timezone

    updated = await record_device_heartbeat(
        session,
        device_id,
        health_state=body.health_state,
        runtime_version=body.runtime_version,
        player_version=body.player_version,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Device not found")

    return {
        "status": "accepted",
        "server_time": datetime.now(tz=timezone.utc).isoformat(),
        "health_state": body.health_state,
    }


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
