"""
PoP Ingestion Service (Phase 4.3c — ADR-017).

Pure domain logic — no FastAPI, no NATS, no ClickHouse.
Caller owns the database transaction boundary.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from packages.domain import repository
from packages.domain.models import (
    DeliveryManifest,
    DeliveryManifestAsset,
    DeliveryManifestSurface,
)
from packages.domain.schemas import (
    POP_CLOCK_DRIFT_MINUTES,
    POP_MAX_DURATION_MS,
    POP_QUARANTINE_TTL_HOURS,
    POP_SCHEMA_VERSION,
    PopEventIn,
)

STALE_EVENT_DAYS = 30


def _is_pop_dedup_unique_violation(exc: IntegrityError) -> bool:
    """Return True if exc is a UniqueViolation on pop_dedup_index.

    Duck-types asyncpg's UniqueViolationError via .orig without a hard
    import, so the domain stays decoupled from the DB-API driver.

    Safety: only returns True when the constraint name contains
    "pop_dedup".  FK violations, check violations, and other unique
    constraints are not matched.
    """
    orig = getattr(exc, "orig", None)
    if orig is None:
        return False
    cls_name = type(orig).__name__
    if "UniqueViolation" not in cls_name:
        return False
    constraint_name = getattr(orig, "constraint_name", "") or ""
    return "pop_dedup" in constraint_name


async def _resolve_manifest(
    session: AsyncSession, manifest_id: str,
) -> DeliveryManifest | None:
    """Look up manifest by its string manifest_id."""
    stmt = select(DeliveryManifest).where(
        DeliveryManifest.manifest_id == manifest_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_manifest_surfaces(
    session: AsyncSession, manifest_pk: str,
) -> set[str]:
    """Return display_surface_ids for a manifest (by internal PK)."""
    stmt = select(DeliveryManifestSurface.display_surface_id).where(
        DeliveryManifestSurface.manifest_id == manifest_pk,
    )
    result = await session.execute(stmt)
    return {row[0] for row in result.fetchall()}


async def _get_manifest_assets(
    session: AsyncSession, manifest_pk: str,
) -> set[str]:
    """Return creative_asset_ids for a manifest (by internal PK)."""
    stmt = select(DeliveryManifestAsset.creative_asset_id).where(
        DeliveryManifestAsset.manifest_id == manifest_pk,
    )
    result = await session.execute(stmt)
    return {row[0] for row in result.fetchall()}


async def _write_pop_event(
    session: AsyncSession,
    *,
    write_fn,
    event_type: str,
    aggregate_id: str,
    outbox_payload: dict,
) -> dict[str, str] | None:
    """Execute a PoP write path inside a savepoint.

    If the dedup key insert raises IntegrityError (race condition
    with concurrent ingest), rolls back the savepoint and returns
    duplicate status so the batch can continue.
    """
    sp = await session.begin_nested()
    try:
        await write_fn()
        await repository.insert_pop_dedup_key(session, aggregate_id)
        await session.flush()
        await sp.commit()
        await repository.enqueue_outbox_event(
            session,
            event_type=event_type,
            aggregate_type="pop_event",
            aggregate_id=aggregate_id,
            payload=outbox_payload,
        )
        return None  # success — caller sets exact status
    except IntegrityError as exc:
        await sp.rollback()
        if _is_pop_dedup_unique_violation(exc):
            return {"status": "duplicate", "reason": "duplicate_event_id"}
        raise


async def ingest_pop_event(
    session: AsyncSession,
    event: PopEventIn,
    *,
    jwt_device_id: str,
    now: datetime | None = None,
    batch_id: str | None = None,
) -> dict:
    """Validate and ingest a single PoP event.

    Called inside a caller-owned transaction.  Returns a result dict
    with status and reason.  Does NOT commit — caller owns the boundary.

    Returns:
        {"status": "accepted"|"quarantined"|"rejected"|"duplicate",
         "reason": str|None}
    """
    if now is None:
        now = datetime.now(timezone.utc)

    # 1. Schema version
    if event.schema_version != POP_SCHEMA_VERSION:
        return {"status": "rejected", "reason": "unsupported_schema_version"}

    # 2. Device binding
    if event.device_id != jwt_device_id:
        return {"status": "rejected", "reason": "device_mismatch"}

    # 3. Dedup
    is_dup = await repository.is_pop_event_duplicate(session, event.event_id)
    if is_dup:
        return {"status": "duplicate", "reason": "duplicate_event_id"}

    # 4. Duration bounds (also enforced by DB CHECK, but reject early)
    if event.duration_ms < 1 or event.duration_ms > POP_MAX_DURATION_MS:
        return {"status": "rejected", "reason": "invalid_duration"}

    # 5. Playback result
    if event.playback_result != "success":
        return {"status": "rejected", "reason": "non_success_playback"}

    # 6. Resolve device retailer_id early — needed for RLS on pop_events_raw
    #    (both accepted and quarantined paths require it for NOBYPASSRLS).
    device_row = await repository.get_device_retailer_id_and_status(
        session, event.device_id,
    )
    device_retailer_id = device_row[0] if device_row else None

    if device_retailer_id is None:
        return {"status": "rejected", "reason": "device_not_found"}

    # 7. Stale event check
    stale_cutoff = now - timedelta(days=STALE_EVENT_DAYS)
    if event.rendered_at < stale_cutoff:
        return {"status": "rejected", "reason": "stale_event"}

    # 7. Clock drift (future)
    future_cutoff = now + timedelta(minutes=POP_CLOCK_DRIFT_MINUTES)
    clock_drift = event.rendered_at > future_cutoff

    # 8. Manifest resolution
    manifest = None
    if event.manifest_id:
        manifest = await _resolve_manifest(session, event.manifest_id)

    if manifest is None:
        # Unknown manifest → quarantine
        expires_at = now + timedelta(hours=POP_QUARANTINE_TTL_HOURS)

        async def _write():
            await repository.quarantine_pop_event(
                session,
                event_id=event.event_id,
                schema_version=event.schema_version,
                device_id=event.device_id,
                manifest_id=event.manifest_id,
                campaign_id=event.campaign_id,
                creative_asset_id=event.creative_asset_id,
                surface_id=event.surface_id,
                rendered_at=event.rendered_at,
                event_recorded_at=event.event_recorded_at,
                duration_ms=event.duration_ms,
                playback_result=event.playback_result,
                quarantine_reason="unknown_manifest",
                expires_at=expires_at,
                batch_id=batch_id,
                retailer_id=device_retailer_id,
            )

        dup = await _write_pop_event(
            session,
            write_fn=_write,
            event_type="pop.event.quarantined",
            aggregate_id=event.event_id,
            outbox_payload={
                "event_id": event.event_id,
                "manifest_id": event.manifest_id,
                "device_id": event.device_id,
                "reason": "unknown_manifest",
                "expires_at": expires_at.isoformat(),
            },
        )
        if dup is not None:
            return dup
        return {"status": "quarantined", "reason": "unknown_manifest"}

    # 9. Clock drift quarantine (manifest known but clock is ahead)
    if clock_drift:
        expires_at = now + timedelta(hours=POP_QUARANTINE_TTL_HOURS)

        async def _write():
            await repository.quarantine_pop_event(
                session,
                event_id=event.event_id,
                schema_version=event.schema_version,
                device_id=event.device_id,
                manifest_id=event.manifest_id,
                campaign_id=event.campaign_id,
                creative_asset_id=event.creative_asset_id,
                surface_id=event.surface_id,
                rendered_at=event.rendered_at,
                event_recorded_at=event.event_recorded_at,
                duration_ms=event.duration_ms,
                playback_result=event.playback_result,
                quarantine_reason="clock_drift",
                expires_at=expires_at,
                batch_id=batch_id,
                retailer_id=device_retailer_id,
            )

        dup = await _write_pop_event(
            session,
            write_fn=_write,
            event_type="pop.event.quarantined",
            aggregate_id=event.event_id,
            outbox_payload={
                "event_id": event.event_id,
                "manifest_id": event.manifest_id,
                "device_id": event.device_id,
                "reason": "clock_drift",
                "rendered_at": event.rendered_at.isoformat(),
            },
        )
        if dup is not None:
            return dup
        return {"status": "quarantined", "reason": "clock_drift"}

    # 10. Cross-entity consistency checks (manifest known, not clock-drifted)
    # campaign mismatch
    if event.campaign_id and event.campaign_id != manifest.campaign_id:
        return {"status": "rejected", "reason": "campaign_mismatch"}

    # device mismatch
    if event.device_id != manifest.physical_device_id:
        return {"status": "rejected", "reason": "device_manifest_mismatch"}

    # surface not in manifest
    manifest_pk: str = str(manifest.id)
    manifest_surfaces = await _get_manifest_surfaces(session, manifest_pk)
    if event.surface_id not in manifest_surfaces:
        return {"status": "rejected", "reason": "surface_not_in_manifest"}

    # creative not in manifest
    manifest_assets = await _get_manifest_assets(session, manifest_pk)
    if event.creative_asset_id not in manifest_assets:
        return {"status": "rejected", "reason": "asset_not_in_manifest"}

    # 11. Accept — billing-grade
    # manifest_id and campaign_id from the resolved manifest (trusted)
    manifest_id_str: str = str(manifest.manifest_id)
    campaign_id_str: str = str(manifest.campaign_id)

    async def _write():
        await repository.accept_pop_event(
            session,
            event_id=event.event_id,
            schema_version=event.schema_version,
            device_id=event.device_id,
            manifest_id=manifest_id_str,
            campaign_id=campaign_id_str,  # trusted from manifest
            creative_asset_id=event.creative_asset_id,
            surface_id=event.surface_id,
            rendered_at=event.rendered_at,
            event_recorded_at=event.event_recorded_at,
            duration_ms=event.duration_ms,
            batch_id=batch_id,
            retailer_id=manifest.retailer_id,
        )

    dup = await _write_pop_event(
        session,
        write_fn=_write,
        event_type="pop.event.accepted",
        aggregate_id=event.event_id,
        outbox_payload={
            "event_id": event.event_id,
            "manifest_id": manifest_id_str,
            "campaign_id": campaign_id_str,
            "device_id": event.device_id,
            "surface_id": event.surface_id,
            "creative_asset_id": event.creative_asset_id,
            "duration_ms": event.duration_ms,
        },
    )
    if dup is not None:
        return dup
    return {"status": "accepted", "reason": None}


async def ingest_pop_batch(
    session: AsyncSession,
    events: list[PopEventIn],
    *,
    jwt_device_id: str,
    now: datetime | None = None,
    batch_id: str | None = None,
) -> dict:
    """Ingest a batch of PoP events.

    Processes each event sequentially inside the caller-owned transaction.
    Returns summary dict compatible with PopBatchResponse.

    Does NOT commit — caller owns the transaction boundary.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    results = []
    counts = {"accepted": 0, "rejected": 0, "quarantined": 0, "duplicate": 0}

    for event in events:
        result = await ingest_pop_event(
            session, event,
            jwt_device_id=jwt_device_id,
            now=now,
            batch_id=batch_id,
        )
        results.append({
            "event_id": event.event_id,
            "status": result["status"],
            "reason": result["reason"],
        })
        counts[result["status"]] += 1

    # Batch-level outbox summary
    await repository.enqueue_outbox_event(
        session,
        event_type="pop.batch.ingested",
        aggregate_type="pop_batch",
        aggregate_id=batch_id or "unknown",
        payload={
            "batch_id": batch_id,
            "device_id": jwt_device_id,
            "event_count": len(events),
            "accepted_count": counts["accepted"],
            "rejected_count": counts["rejected"],
            "quarantined_count": counts["quarantined"],
            "duplicate_count": counts["duplicate"],
        },
    )

    return {
        "accepted_count": counts["accepted"],
        "rejected_count": counts["rejected"],
        "quarantined_count": counts["quarantined"],
        "duplicate_count": counts["duplicate"],
        "results": results,
    }
