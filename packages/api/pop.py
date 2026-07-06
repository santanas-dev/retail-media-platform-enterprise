"""
Retail Media Platform — PoP Ingestion API Router (Phase 4.3c).

POST /api/v1/pop/batch — device-submitted proof-of-play events.
Thin router — all business logic in packages/domain/pop_ingestion.py.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from packages.api.dependencies import get_db, get_device_id_from_token
from packages.domain import pop_ingestion
from packages.domain.schemas import (
    POP_MAX_BATCH_SIZE,
    PopBatchRequest,
    PopBatchResponse,
    PopEventResult,
)

router = APIRouter(prefix="/api/v1/pop", tags=["pop"])


@router.post("/batch", response_model=PopBatchResponse)
async def ingest_batch(
    request: PopBatchRequest,
    device_id: str = Depends(get_device_id_from_token),
    db = Depends(get_db),
) -> PopBatchResponse:
    """Ingest a batch of PoP events from a device.

    Device JWT required (auth_provider=device).  User/admin tokens rejected.
    Max 500 events per batch.  Partial success allowed.

    Validation per ADR-017:
    - schema_version must be \"1.0\"
    - event_id dedup prevents double-counting
    - device_id must match JWT sub
    - unknown manifest → quarantine 72h, campaign_verified=false
    - known manifest → cross-entity consistency checks
    - contradictions → reject per event
    """
    if not request.events:
        raise HTTPException(status_code=422, detail="Batch must contain at least one event")

    batch_id = str(uuid.uuid4())

    # db is an active session+transaction from get_db dependency
    result = await pop_ingestion.ingest_pop_batch(
        db,
        request.events,
        jwt_device_id=device_id,
        batch_id=batch_id,
    )

    return PopBatchResponse(
        accepted_count=result["accepted_count"],
        rejected_count=result["rejected_count"],
        quarantined_count=result["quarantined_count"],
        duplicate_count=result["duplicate_count"],
        results=[
            PopEventResult(
                event_id=r["event_id"],
                status=r["status"],
                reason=r["reason"],
            )
            for r in result["results"]
        ],
    )
