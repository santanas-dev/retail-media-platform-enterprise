"""
Retail Media Platform — Device Gateway.

Phase 4.2d: Device manifest delivery endpoint.
Serves manifest JSON to authenticated devices.
No generation, no PoP, no runtime logic.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain.database import get_session
from packages.domain.repository import get_latest_manifest_for_device
from packages.observability import setup_logging, log_request_middleware
from packages.security.jwt import verify_access_token

SERVICE_NAME = "device-gateway"
logger = setup_logging(SERVICE_NAME)

app = FastAPI(
    title="RMP Device Gateway",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)
app.middleware("http")(log_request_middleware)


# ---------------------------------------------------------------------------
# Device Authentication Dependency
# ---------------------------------------------------------------------------


async def get_device_id_from_token(request: Request) -> str:
    """Extract physical_device_id from Authorization: Bearer <device JWT>.

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
# Health
# ---------------------------------------------------------------------------


@app.get("/health/live")
async def health_live():
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/health/ready")
async def health_ready():
    return {
        "status": "ok",
        "service": SERVICE_NAME,
        "checks": {
            "redis": "not_configured",
            "event_bus": "not_configured",
        },
    }


# ---------------------------------------------------------------------------
# Manifest Delivery
# ---------------------------------------------------------------------------


@app.get("/api/v1/device/manifest/latest")
async def get_latest_manifest(
    device_id: str = Depends(get_device_id_from_token),
    session: AsyncSession = Depends(get_session),
):
    """Return the latest generated manifest for the authenticated device.

    200: manifest JSON
    404: no manifest generated yet for this device
    401: invalid/expired/missing device token
    """
    # Check device exists and is active
    from packages.domain.models import PhysicalDevice
    device = (
        await session.execute(
            sa_select(PhysicalDevice).where(
                PhysicalDevice.id == device_id,
            )
        )
    ).scalar_one_or_none()

    if device is None:
        raise HTTPException(status_code=404, detail="Device not found")

    if device.status not in ("active", "online"):
        raise HTTPException(
            status_code=403,
            detail=f"Device is {device.status}",
        )

    manifest = await get_latest_manifest_for_device(session, device_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail="No manifest available")

    return manifest


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DEVICE_GATEWAY_PORT", "8001"))
    logger.info("Starting %s on port %s", SERVICE_NAME, port)
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
