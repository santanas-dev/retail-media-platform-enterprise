"""
Manifest Generation Worker Skeleton (ADR-016, Phase 4.2c).

Business logic for delivery planning / manifest generation.
Runs inside a caller-owned async transaction. Does NOT commit —
caller owns the transaction boundary. Does NOT publish NATS.

Layer: packages/domain/ — no api/auth/fastapi imports.
"""

from __future__ import annotations

import hashlib
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone as tz
from typing import Any

from sqlalchemy import select, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class EligibilityResult:
    eligible: bool
    reason: str | None = None


@dataclass
class TargetResolutionResult:
    """Resolved campaign targets: surface → device grouping."""
    # surface_id -> physical_device_id mapping
    surface_device_map: dict[str, str] = field(default_factory=dict)
    # device_id -> list of display_surface_ids
    device_surfaces: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class ManifestGenerationResult:
    """Structured result from generate_manifests_for_campaign."""
    campaign_id: str
    eligible: bool
    skip_reason: str | None = None
    device_count: int = 0
    surface_count: int = 0
    manifest_count: int = 0
    failure_count: int = 0
    manifest_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


async def check_eligibility(
    session: AsyncSession,
    campaign_id: str,
) -> EligibilityResult:
    """Check if a campaign is eligible for manifest generation (ADR-016 §2).

    Conditions:
    - campaign status >= 'approved'
    - at least one flight with valid window (start_at <= now, end_at > now)
    - contract valid (valid_from <= now, valid_until IS NULL OR > now)
    - at least one placement resolving to a display_surface
    - at least one linked creative asset with status='ready' AND moderation approved
    """
    from packages.domain.models import (
        Campaign,
        CampaignCreative,
        CampaignFlight,
        CampaignPlacement,
        CreativeAsset,
        AdvertiserContract,
        DisplaySurface,
        LogicalCarrier,
        PhysicalDevice,
        Store,
        Cluster,
        Branch,
    )

    # Load campaign
    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
    ).scalar_one_or_none()
    if campaign is None:
        return EligibilityResult(False, "Campaign not found")

    # 1. Status check: >= 'approved', excluding terminal/revoker states.
    # Per ADR-016 §1: completed/archived/paused go to Manifest revoker, NOT generator.
    eligible_statuses = {"approved", "scheduled", "active"}
    if campaign.status not in eligible_statuses:
        return EligibilityResult(
            False,
            f"Campaign status is '{campaign.status}', not in {sorted(eligible_statuses)}",
        )

    # 2. Contract validity
    now = datetime.now(tz.utc)
    if campaign.advertiser_contract_id:
        contract = (
            await session.execute(
                select(AdvertiserContract).where(
                    AdvertiserContract.id == campaign.advertiser_contract_id,
                )
            )
        ).scalar_one_or_none()
        if contract is None:
            return EligibilityResult(False, "Contract not found")
        if contract.valid_from and contract.valid_from > now:
            return EligibilityResult(False, "Contract not yet valid")
        if contract.valid_until and contract.valid_until <= now:
            return EligibilityResult(False, "Contract has expired")

    # 3. At least one valid flight
    flights_result = await session.execute(
        select(CampaignFlight).where(CampaignFlight.campaign_id == campaign_id)
    )
    flights = flights_result.scalars().all()
    valid_flights = [f for f in flights if f.start_at <= now and f.end_at > now]
    if not valid_flights:
        return EligibilityResult(False, "No valid flight window (started and not yet ended)")

    # 4. At least one placement exists
    placements_result = await session.execute(
        select(CampaignPlacement).where(CampaignPlacement.campaign_id == campaign_id)
    )
    placements = placements_result.scalars().all()
    if not placements:
        return EligibilityResult(False, "No placements")

    # 5. At least one linked creative asset with status='ready' and moderation approved
    creatives_result = await session.execute(
        select(CampaignCreative)
        .join(CreativeAsset, CampaignCreative.creative_asset_id == CreativeAsset.id)
        .where(
            CampaignCreative.campaign_id == campaign_id,
            CreativeAsset.status == "ready",
            CreativeAsset.moderation_status == "approved",
        )
    )
    valid_creatives = creatives_result.scalars().all()
    if not valid_creatives:
        return EligibilityResult(
            False, "No linked creative assets with status=ready and moderation=approved"
        )

    return EligibilityResult(True)


async def resolve_targets(
    session: AsyncSession,
    campaign_id: str,
) -> TargetResolutionResult:
    """Resolve campaign placements to display_surfaces → physical_devices (ADR-016 §3).

    Resolution chain:
      display_surface_id → direct
      store_id → all active surfaces in that store
      cluster_id → all active surfaces in stores in that cluster
      branch_id → all active surfaces in stores whose clusters belong to that branch

    Only active surfaces on active devices are included.
    Returns surface_device_map and device_surfaces grouping.
    """
    from packages.domain.models import (
        CampaignPlacement,
        DisplaySurface,
        LogicalCarrier,
        PhysicalDevice,
        Store,
        Cluster,
    )

    placements_result = await session.execute(
        select(CampaignPlacement).where(CampaignPlacement.campaign_id == campaign_id)
    )
    placements = placements_result.scalars().all()

    if not placements:
        return TargetResolutionResult()

    surface_ids: set[str] = set()
    store_ids: set[str] = set()
    cluster_ids: set[str] = set()
    branch_ids: set[str] = set()

    for p in placements:
        if p.display_surface_id:
            surface_ids.add(p.display_surface_id)
        elif p.store_id:
            store_ids.add(p.store_id)
        elif p.cluster_id:
            cluster_ids.add(p.cluster_id)
        elif p.branch_id:
            branch_ids.add(p.branch_id)

    # Map: surface_id → physical_device_id
    surface_device_map: dict[str, str] = {}

    async def _resolve_surfaces(where_clause):
        """Query display surfaces → logical_carrier → physical_device."""
        result = await session.execute(
            select(
                DisplaySurface.id,
                PhysicalDevice.id,
            )
            .select_from(DisplaySurface)
            .join(LogicalCarrier, DisplaySurface.logical_carrier_id == LogicalCarrier.id)
            .join(PhysicalDevice, LogicalCarrier.physical_device_id == PhysicalDevice.id)
            .where(
                DisplaySurface.is_active.is_(True),
                PhysicalDevice.status == "active",
                where_clause,
            )
        )
        for row in result.all():
            surface_device_map[row[0]] = row[1]

    if surface_ids:
        await _resolve_surfaces(DisplaySurface.id.in_(surface_ids))

    if store_ids:
        await _resolve_surfaces(DisplaySurface.store_id.in_(store_ids))

    if cluster_ids:
        StoreAlias = aliased(Store)
        result = await session.execute(
            select(
                DisplaySurface.id,
                PhysicalDevice.id,
            )
            .select_from(DisplaySurface)
            .join(LogicalCarrier, DisplaySurface.logical_carrier_id == LogicalCarrier.id)
            .join(PhysicalDevice, LogicalCarrier.physical_device_id == PhysicalDevice.id)
            .join(StoreAlias, DisplaySurface.store_id == StoreAlias.id, isouter=True)
            .where(
                DisplaySurface.is_active.is_(True),
                PhysicalDevice.status == "active",
                StoreAlias.cluster_id.in_(cluster_ids),
            )
        )
        for row in result.all():
            surface_device_map[row[0]] = row[1]

    if branch_ids:
        StoreAlias = aliased(Store)
        ClusterAlias = aliased(Cluster)
        result = await session.execute(
            select(
                DisplaySurface.id,
                PhysicalDevice.id,
            )
            .select_from(DisplaySurface)
            .join(LogicalCarrier, DisplaySurface.logical_carrier_id == LogicalCarrier.id)
            .join(PhysicalDevice, LogicalCarrier.physical_device_id == PhysicalDevice.id)
            .join(StoreAlias, DisplaySurface.store_id == StoreAlias.id, isouter=True)
            .join(ClusterAlias, StoreAlias.cluster_id == ClusterAlias.id, isouter=True)
            .where(
                DisplaySurface.is_active.is_(True),
                PhysicalDevice.status == "active",
                ClusterAlias.branch_id.in_(branch_ids),
            )
        )
        for row in result.all():
            surface_device_map[row[0]] = row[1]

    # Group by physical_device_id
    device_surfaces: dict[str, list[str]] = defaultdict(list)
    for surface_id, device_id in surface_device_map.items():
        device_surfaces[device_id].append(surface_id)

    return TargetResolutionResult(
        surface_device_map=surface_device_map,
        device_surfaces=dict(device_surfaces),
    )


# ---------------------------------------------------------------------------
# Manifest ID computation (ADR-016 §5)
# ---------------------------------------------------------------------------


_SEP = "\u2016"  # U+2016 DOUBLE VERTICAL LINE


def compute_manifest_id(
    campaign_id: str,
    campaign_status: str,
    campaign_updated_at: str,
    creative_asset_ids: list[str],
    creative_checksums: list[str],
    flight_ids: list[str],
    flight_data: list[str],
    placement_ids: list[str],
    surface_ids: list[str],
    device_id: str,
) -> str:
    """Compute deterministic manifest_id per ADR-016 §5.

    SHA-256 of: campaign.id ‖ campaign.status ‖ campaign.updated_at
    ‖ sorted(creative_asset.id) ‖ sorted(creative_asset.sha256_checksum)
    ‖ sorted(flight.id) ‖ sorted(flight.start_at‖end_at‖dayparting_json‖days_of_week)
    ‖ sorted(placement.id) ‖ sorted(resolved surface.id) ‖ device_id

    All fields concatenated as UTF-8 bytes with ‖ separator.
    Lists sorted lexicographically before concatenation.
    """
    parts: list[str] = [
        campaign_id,
        campaign_status,
        campaign_updated_at,
    ]
    parts.extend(sorted(creative_asset_ids))
    parts.extend(sorted(creative_checksums))
    parts.extend(sorted(flight_ids))
    parts.extend(sorted(flight_data))
    parts.extend(sorted(placement_ids))
    parts.extend(sorted(surface_ids))
    parts.append(device_id)

    input_bytes = _SEP.join(parts).encode("utf-8")
    return "sha256:" + hashlib.sha256(input_bytes).hexdigest()


# ---------------------------------------------------------------------------
# Manifest JSON generation
# ---------------------------------------------------------------------------


def generate_manifest_json(
    *,
    manifest_id: str,
    manifest_version: int,
    device_id: str,
    device_code: str = "",
    store_id: str = "",
    store_code: str = "",
    channel_type: str = "",
    device_type: str = "",
    surface_ids: list[str],
    surface_codes: dict[str, str] | None = None,
    playlist_items: list[dict[str, Any]] | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    offline_ttl_hours: int = 168,
) -> dict[str, Any]:
    """Generate manifest JSON compatible with universal-manifest-v1 schema.

    No presigned URLs in skeleton — uses object references.
    No storage credentials, no contact PII.
    Schema matches packages/contracts/manifest_v1.schema.json required fields.
    """
    surface_codes = surface_codes or {}

    manifest: dict[str, Any] = {
        "manifest_id": manifest_id,
        "manifest_version": manifest_version,
        "schema_version": "1.0",
        "device_id": device_id,
        "device_code": device_code,
        "store_id": store_id,
        "store_code": store_code,
        "channel_type": channel_type,
        "device_type": device_type,
        "display_surfaces": [
            {
                "surface_id": sid,
                "surface_code": surface_codes.get(sid, ""),
            }
            for sid in sorted(surface_ids)
        ],
        "playlist": playlist_items or [],
        "media_files": [],
        "adapter_payload": {},
        "valid_from": valid_from,
        "valid_to": valid_to,
        "offline_ttl_hours": offline_ttl_hours,
        "fallback_rules": {
            "on_manifest_expired": "show_fallback",
            "on_network_lost": "continue_last_valid",
            "filler_media_ids": [],
            "emit_pop": False,
        },
        "signature": {
            "algorithm": "HMAC-SHA256",
            "value": "",
        },
    }
    return manifest


# ---------------------------------------------------------------------------
# Main generation entry point
# ---------------------------------------------------------------------------


async def generate_manifests_for_campaign(
    session: AsyncSession,
    campaign_id: str,
) -> ManifestGenerationResult:
    """Generate delivery manifests for an eligible campaign (ADR-016).

    Steps:
    1. Check eligibility → return if not eligible
    2. Resolve targets → surface → device grouping
    3. For each device, compute manifest_id, check idempotency
    4. Create delivery_plan, delivery_manifest records, manifest surfaces/assets
    5. Enqueue outbox event (delivery.manifest.generated or .failed)
    6. Return structured result

    Does NOT commit — caller owns the transaction boundary.
    Does NOT publish NATS.
    """
    from packages.domain.models import (
        Campaign,
        CampaignCreative,
        CampaignFlight,
        CampaignPlacement,
        CreativeAsset,
        DeliveryManifest,
        DisplaySurface,
        LogicalCarrier,
        PhysicalDevice,
        Store,
    )
    from packages.domain.repository import (
        create_delivery_plan,
        create_delivery_manifest_record,
        mark_manifest_generated,
        mark_manifest_failed,
        enqueue_outbox_event,
    )

    # ── 1. Eligibility ──
    eligibility = await check_eligibility(session, campaign_id)
    if not eligibility.eligible:
        return ManifestGenerationResult(
            campaign_id=campaign_id,
            eligible=False,
            skip_reason=eligibility.reason,
        )

    # ── 2. Target resolution ──
    targets = await resolve_targets(session, campaign_id)
    if not targets.device_surfaces:
        await enqueue_outbox_event(
            session,
            event_type="delivery.manifest.failed",
            aggregate_type="campaign",
            aggregate_id=campaign_id,
            payload={
                "campaign_id": campaign_id,
                "reason": "No targets resolved to active surfaces/devices",
            },
        )
        return ManifestGenerationResult(
            campaign_id=campaign_id,
            eligible=True,
            skip_reason="No targets resolved",
        )

    # ── 3. Load campaign data for manifest computation ──
    campaign = (
        await session.execute(
            select(Campaign).where(Campaign.id == campaign_id)
        )
    ).scalar_one()

    # Flights
    flights_result = await session.execute(
        select(CampaignFlight).where(CampaignFlight.campaign_id == campaign_id)
    )
    flights = flights_result.scalars().all()

    # Placements
    placements_result = await session.execute(
        select(CampaignPlacement).where(CampaignPlacement.campaign_id == campaign_id)
    )
    placements = placements_result.scalars().all()

    # Creatives (ready + approved only)
    creatives_result = await session.execute(
        select(CampaignCreative, CreativeAsset)
        .join(CreativeAsset, CampaignCreative.creative_asset_id == CreativeAsset.id)
        .where(
            CampaignCreative.campaign_id == campaign_id,
            CreativeAsset.status == "ready",
            CreativeAsset.moderation_status == "approved",
        )
    )
    creative_asset_rows = creatives_result.all()

    # Load surface details for codes
    all_surface_ids: set[str] = set()
    for surfaces in targets.device_surfaces.values():
        all_surface_ids.update(surfaces)

    surface_code_map: dict[str, str] = {}
    surface_store_rows: list[Any] = []
    if all_surface_ids:
        surface_store_rows = (
            await session.execute(
                select(DisplaySurface.id, DisplaySurface.code, DisplaySurface.store_id)
                .where(DisplaySurface.id.in_(all_surface_ids))
            )
        ).all()
        for row in surface_store_rows:
            surface_code_map[row[0]] = row[1]

    # Load store details
    store_ids: set[str] = {row[2] for row in surface_store_rows if row[2]}
    store_code_map: dict[str, str] = {}
    if store_ids:
        store_rows = (
            await session.execute(
                select(Store.id, Store.code).where(Store.id.in_(store_ids))
            )
        ).all()
        for row in store_rows:
            store_code_map[row[0]] = row[1]

    # Load device details
    device_rows = (
        await session.execute(
            select(PhysicalDevice.id, PhysicalDevice.code, PhysicalDevice.store_id)
            .where(PhysicalDevice.id.in_(list(targets.device_surfaces.keys())))
        )
    ).all()
    device_store_map: dict[str, str] = {r[0]: r[2] for r in device_rows}
    device_code_map: dict[str, str] = {r[0]: r[1] for r in device_rows}

    # Prepare manifest_id inputs
    creative_asset_ids = sorted([ca.id for cc, ca in creative_asset_rows])
    creative_checksums = sorted([ca.sha256_checksum for cc, ca in creative_asset_rows])
    flight_ids = sorted([f.id for f in flights])
    flight_data_parts: list[str] = []
    for f in sorted(flights, key=lambda x: x.id):
        parts = [
            f.start_at.isoformat() if f.start_at else "",
            f.end_at.isoformat() if f.end_at else "",
            str(f.dayparting_json) if f.dayparting_json else "",
            ",".join(str(d) for d in sorted(f.days_of_week)) if f.days_of_week else "",
        ]
        flight_data_parts.append(_SEP.join(parts))
    placement_ids = sorted([p.id for p in placements])

    campaign_updated_at = (
        campaign.updated_at.isoformat()
        if campaign.updated_at else ""
    )

    # Compute campaign version hash for idempotency
    version_hash_input = _SEP.join([
        campaign_id,
        campaign.status,
        campaign_updated_at,
        *creative_asset_ids,
        *creative_checksums,
        *flight_ids,
        *flight_data_parts,
        *placement_ids,
    ]).encode("utf-8")
    campaign_version_hash = "sha256:" + hashlib.sha256(version_hash_input).hexdigest()

    # Flight windows for valid_from/valid_to
    flight_starts = [f.start_at for f in flights if f.start_at]
    flight_ends = [f.end_at for f in flights if f.end_at]
    valid_from = min(flight_starts).isoformat() if flight_starts else None
    valid_to = max(flight_ends).isoformat() if flight_ends else None

    # ── 4. Generate manifests per device ──
    device_count = len(targets.device_surfaces)
    manifest_count = 0
    failure_count = 0
    manifest_ids: list[str] = []

    for device_id, surfaces in targets.device_surfaces.items():
        device_surface_ids = sorted(surfaces)
        store_id = device_store_map.get(device_id, "")
        device_code = device_code_map.get(device_id, "")

        manifest_id = compute_manifest_id(
            campaign_id=campaign_id,
            campaign_status=campaign.status,
            campaign_updated_at=campaign_updated_at,
            creative_asset_ids=creative_asset_ids,
            creative_checksums=creative_checksums,
            flight_ids=flight_ids,
            flight_data=flight_data_parts,
            placement_ids=placement_ids,
            surface_ids=device_surface_ids,
            device_id=device_id,
        )

        # Idempotency: skip if manifest with same manifest_id already exists
        existing = (
            await session.execute(
                select(DeliveryManifest).where(
                    DeliveryManifest.manifest_id == manifest_id,
                )
            )
        ).scalar_one_or_none()

        if existing is not None:
            # Already generated — skip (idempotent)
            continue

        try:
            # Build playlist items
            playlist: list[dict[str, Any]] = []
            for cc, ca in creative_asset_rows:
                playlist.append({
                    "order": cc.sort_order,
                    "weight": cc.sort_order or 1,
                    "priority": campaign.priority,
                    "creative_asset_id": ca.id,
                    "media_type": ca.media_type,
                    "sha256_checksum": ca.sha256_checksum,
                    "duration_ms": cc.duration_override_ms or ca.duration_ms,
                    "start_time": None,
                    "days_of_week": None,
                })

            # Generate manifest JSON
            manifest_json = generate_manifest_json(
                manifest_id=manifest_id,
                manifest_version=1,
                device_id=device_id,
                device_code=device_code,
                store_id=store_id,
                store_code=store_code_map.get(store_id, ""),
                surface_ids=device_surface_ids,
                surface_codes=surface_code_map,
                playlist_items=playlist,
                valid_from=valid_from,
                valid_to=valid_to,
            )

            # Compute content hash for the manifest
            content_hash = "sha256:" + hashlib.sha256(
                str(manifest_json).encode("utf-8")
            ).hexdigest()

            # Persist: create manifest record with surfaces and assets
            asset_records = []
            for cc, ca in creative_asset_rows:
                asset_records.append({
                    "creative_asset_id": ca.id,
                    "sha256_checksum": ca.sha256_checksum,
                    "duration_ms": cc.duration_override_ms or ca.duration_ms,
                    "media_type": ca.media_type,
                })

            await create_delivery_manifest_record(
                session,
                manifest_id_external=manifest_id,
                campaign_id=campaign_id,
                physical_device_id=device_id,
                content_hash=content_hash,
                surface_ids=device_surface_ids,
                asset_records=asset_records,
            )

            # Mark as generated
            await mark_manifest_generated(
                session,
                manifest_id,
                content_hash=content_hash,
            )

            # Outbox: delivery.manifest.generated
            await enqueue_outbox_event(
                session,
                event_type="delivery.manifest.generated",
                aggregate_type="campaign",
                aggregate_id=campaign_id,
                payload={
                    "manifest_id": manifest_id,
                    "device_id": device_id,
                    "manifest_version": 1,
                    "campaign_ids": [campaign_id],
                },
                partition_key=campaign_id,
            )

            manifest_count += 1
            manifest_ids.append(manifest_id)

        except Exception:
            # Mark the manifest as failed
            await mark_manifest_failed(
                session,
                manifest_id,
                last_error="Manifest generation failed",
            )
            await enqueue_outbox_event(
                session,
                event_type="delivery.manifest.failed",
                aggregate_type="campaign",
                aggregate_id=campaign_id,
                payload={
                    "campaign_id": campaign_id,
                    "device_id": device_id,
                    "reason": "Manifest generation failed",
                },
            )
            failure_count += 1

    # Create delivery plan only if work was produced (idempotent: no duplicates on re-run)
    if manifest_count > 0:
        await create_delivery_plan(
            session,
            campaign_id=campaign_id,
            campaign_version_hash=campaign_version_hash,
            reason=f"Auto-planned: {device_count} device(s), {len(all_surface_ids)} surface(s), "
                   f"{manifest_count} manifest(s) generated",
        )

    return ManifestGenerationResult(
        campaign_id=campaign_id,
        eligible=True,
        device_count=device_count,
        surface_count=len(all_surface_ids),
        manifest_count=manifest_count,
        failure_count=failure_count,
        manifest_ids=manifest_ids,
    )
