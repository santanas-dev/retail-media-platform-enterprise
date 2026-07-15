"""
Identity API — Creative Assets: standalone, upload, moderation.
"""

from datetime import datetime, timezone as _tz

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.api.dependencies import (
    get_current_active_user,
    get_db,
    require_permission,
    require_scoped_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.scopes import ScopeContext
from packages.domain.schemas import (
    CompleteUploadRequest,
    CompleteUploadResponse,
    CreativeAssetCreateRequest,
    CreativeAssetOut,
    CreativeModerationQueueItem,
    CreativeModerationResponse,
    CreativeRejectRequest,
    UploadIntentRequest,
    UploadIntentResponse,
)
from packages.security.config import get_security_config

from .common import _scope_ids, _serialize_creative_asset

router = APIRouter()


# ---------------------------------------------------------------------------
# Standalone Creative Asset
# ---------------------------------------------------------------------------


@router.post("/creative-assets",
             response_model=CreativeAssetOut, status_code=201)
async def create_creative_asset_endpoint(
    body: CreativeAssetCreateRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    scope_ids = _scope_ids(scope)
    org_id = body.advertiser_organization_id

    if org_id:
        if scope_ids is not None and org_id not in scope_ids:
            raise HTTPException(status_code=422, detail="Advertiser organization not in scope")
    elif scope_ids is not None:
        if not scope_ids:
            raise HTTPException(status_code=403, detail="No advertiser scope")
        org_id = next(iter(scope_ids))
    else:
        raise HTTPException(status_code=422, detail="Advertiser organization required for admin users")

    try:
        asset_id = await repository.create_creative_asset_metadata(
            db,
            advertiser_organization_id=org_id,
            code=body.code,
            name=body.name,
            media_type=body.media_type,
            sha256_checksum=body.sha256_checksum,
            file_size_bytes=body.file_size_bytes,
            resolution_w=body.resolution_w,
            resolution_h=body.resolution_h,
            duration_ms=body.duration_ms,
            scope_advertiser_ids=scope_ids,
            created_by=claims["sub"],
        )
    except Exception as e:
        from packages.domain.exceptions import CrossOrgReferenceError
        if isinstance(e, CrossOrgReferenceError):
            raise HTTPException(status_code=422, detail=str(e))
        raise

    await repository.enqueue_outbox_event(
        db,
        event_type="creative_asset.created",
        aggregate_type="creative_asset",
        aggregate_id=asset_id,
        payload={"creative_asset_id": asset_id},
        headers={"source_service": "control-api"},
    )
    asset = await repository.get_creative_asset(db, asset_id)
    return _serialize_creative_asset(asset)


# ---------------------------------------------------------------------------
# S-017 — Creative Upload Endpoints (presigned URL flow)
# ---------------------------------------------------------------------------


@router.post("/creative-assets/{asset_id}/upload-intent",
             response_model=UploadIntentResponse)
async def upload_intent_endpoint(
    asset_id: str,
    body: UploadIntentRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope: ScopeContext = Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    cfg = get_security_config()
    if body.content_type not in cfg.creative_allowed_mime_types:
        raise HTTPException(status_code=422, detail=f"Unsupported media type: {body.content_type}")
    if body.content_length > cfg.creative_max_file_size_bytes:
        raise HTTPException(status_code=422, detail=f"File too large: {body.content_length} bytes")

    asset = await repository.get_creative_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Creative asset not found")
    if asset.status != "metadata_only":
        raise HTTPException(status_code=409, detail="Asset already has a file uploaded")

    org_id = str(asset.advertiser_organization_id)
    if not scope.is_admin and scope.advertiser_scope_ids and org_id not in scope.advertiser_scope_ids:
        raise HTTPException(status_code=403, detail="Not in your organisation scope")

    storage_key = f"{org_id}/{asset_id}/{body.filename}"
    bucket = cfg.creative_storage_bucket

    from packages.services.storage import get_storage_service
    storage = get_storage_service()
    upload_url, expires_at = await storage.async_generate_presigned_put(storage_key, body.content_type)

    session_id = await repository.create_upload_session(
        db,
        creative_asset_id=asset_id,
        advertiser_organization_id=org_id,
        storage_bucket=bucket,
        storage_key=storage_key,
        filename=body.filename,
        content_type=body.content_type,
        content_length=body.content_length,
        created_by=claims["sub"],
        ttl_seconds=cfg.creative_upload_url_ttl_seconds,
    )

    return UploadIntentResponse(
        upload_id=session_id,
        upload_url=upload_url,
        method="PUT",
        headers={"Content-Type": body.content_type},
        expires_at=expires_at.isoformat(),
    )


@router.post("/creative-assets/{asset_id}/complete-upload",
             response_model=CompleteUploadResponse)
async def complete_upload_endpoint(
    asset_id: str,
    body: CompleteUploadRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    scope: ScopeContext = Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    upload = await repository.get_upload_session(db, body.upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if upload["creative_asset_id"] != asset_id:
        raise HTTPException(status_code=422, detail="Upload session does not match this asset")
    if upload["completed_at"] is not None:
        raise HTTPException(status_code=409, detail="Upload already completed")

    if upload["expires_at"] < datetime.now(_tz.utc):
        raise HTTPException(status_code=410, detail="Upload session expired")

    org_id = upload["advertiser_organization_id"]
    if not scope.is_admin and scope.advertiser_scope_ids and org_id not in scope.advertiser_scope_ids:
        raise HTTPException(status_code=403, detail="Not in your organisation scope")

    from packages.services.storage import get_storage_service
    storage = get_storage_service()
    if not await storage.async_object_exists(upload["storage_key"]):
        raise HTTPException(status_code=404, detail="File not found in storage")

    actual_size = await storage.async_get_object_size(upload["storage_key"])
    if actual_size != upload["content_length"]:
        raise HTTPException(status_code=422, detail=f"Size mismatch: expected {upload['content_length']}, got {actual_size}")

    checksum = await storage.async_compute_sha256(upload["storage_key"])
    if checksum is None:
        raise HTTPException(status_code=500, detail="Failed to compute checksum")

    cfg = get_security_config()
    moderation = "approved" if cfg.creative_auto_approve_uploads else "pending_review"

    ok = await repository.mark_asset_uploaded(
        db, asset_id=asset_id,
        storage_bucket=upload["storage_bucket"],
        storage_key=upload["storage_key"],
        sha256_checksum=checksum,
        file_size_bytes=actual_size,
        moderation_status=moderation,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Asset is not in metadata_only status")

    await repository.mark_upload_complete(db, body.upload_id)

    return CompleteUploadResponse(
        asset_id=asset_id,
        sha256_checksum=checksum,
        file_size_bytes=actual_size,
        status="ready",
        moderation_status=moderation,
    )


# ---------------------------------------------------------------------------
# S-036 — Creative Moderation Queue
# ---------------------------------------------------------------------------


@router.get("/creative-assets/moderation-queue",
            response_model=list[CreativeModerationQueueItem])
async def moderation_queue_endpoint(
    status_filter: str = Query("pending_review", alias="moderation_status"),
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("creatives.moderate")),
    _rls=Depends(set_rls_context),
):
    valid = {"pending_review", "approved", "rejected", "all"}
    if status_filter not in valid:
        raise HTTPException(status_code=422, detail=f"Invalid status_filter: {status_filter}")

    items = await repository.list_moderation_queue(db, status_filter=status_filter)
    return [CreativeModerationQueueItem(**item) for item in items]


@router.post("/creative-assets/{asset_id}/approve",
             response_model=CreativeModerationResponse)
async def approve_creative_endpoint(
    asset_id: str,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    _perm: dict = Depends(require_permission("creatives.moderate")),
    _rls=Depends(set_rls_context),
):
    asset = await repository.get_creative_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Creative asset not found")

    ok = await repository.approve_creative_asset(db, asset_id=asset_id)
    if not ok:
        raise HTTPException(status_code=409, detail="Failed to approve creative asset")

    # Audit (S-052)
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=claims["sub"],
        action="creative.approved",
        target_type="creative_asset",
        target_id=asset_id,
        details={
            "previous_moderation_status": asset.moderation_status,
            "new_moderation_status": "approved",
        },
    )

    return CreativeModerationResponse(
        asset_id=asset_id,
        moderation_status="approved",
        message="Креатив одобрен",
    )


@router.post("/creative-assets/{asset_id}/reject",
             response_model=CreativeModerationResponse)
async def reject_creative_endpoint(
    asset_id: str,
    body: CreativeRejectRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    _perm: dict = Depends(require_permission("creatives.moderate")),
    _rls=Depends(set_rls_context),
):
    asset = await repository.get_creative_asset(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Creative asset not found")

    ok = await repository.reject_creative_asset(
        db, asset_id=asset_id, reason=body.reason,
    )
    if not ok:
        raise HTTPException(status_code=409, detail="Failed to reject creative asset")

    # Audit (S-052)
    from packages.domain.repository import create_audit_event
    await create_audit_event(
        db,
        actor_user_id=claims["sub"],
        action="creative.rejected",
        target_type="creative_asset",
        target_id=asset_id,
        details={
            "previous_moderation_status": asset.moderation_status,
            "new_moderation_status": "rejected",
            "rejection_reason": body.reason[:200],
        },
    )

    return CreativeModerationResponse(
        asset_id=asset_id,
        moderation_status="rejected",
        message="Креатив отклонён",
    )
