"""
Shared helpers for identity API route modules.

All helpers from the original packages/api/identity.py
moved here to avoid circular imports.
"""

from fastapi import HTTPException

from packages.api.dependencies import set_rls_context
from packages.domain import repository
from packages.domain.scopes import ScopeContext
from packages.domain.schemas import (
    CampaignOut,
    CreativeAssetOut,
)


def _serialize_campaign(c):
    """Safe serialization — strip storage_pii fields if any."""
    return CampaignOut.model_validate(c)


def _serialize_creative_asset(c):
    """Safe serialization — never expose storage_bucket/storage_key."""
    return CreativeAssetOut.model_validate(c)


def _scope_ids(scope) -> frozenset[str] | None:
    """Return advertiser scope IDs for scoped users, None for admins."""
    if scope.is_admin:
        return None
    ids = scope.advertiser_scope_ids if scope else set()
    return frozenset(ids) if ids else frozenset()


async def _require_draft_campaign(db, campaign_id: str, scope):
    """Load campaign, raise 404/409 if not found or not in draft.

    Returns the Campaign object so callers that need advertiser_organization_id
    can avoid a second lookup.
    """
    campaign = await repository.get_campaign(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND"})
    if campaign.status != "draft":
        raise HTTPException(status_code=409, detail="Campaign is not in draft status")
    if not scope.is_admin:
        org_str = str(campaign.advertiser_organization_id)
        if org_str not in (scope.advertiser_scope_ids or frozenset()):
            raise HTTPException(status_code=404, detail={"code": "CAMPAIGN_NOT_FOUND"})
    return campaign


async def _validate_flight_dates(db, campaign, start_at, end_at) -> str | None:
    """Validate flight start/end against contract window. Returns error string or None.

    Checks:
    - start_at < end_at
    - start_at >= contract.valid_from
    - end_at <= contract.valid_until (if not NULL)
    """
    if start_at >= end_at:
        return "Flight start_at must be before end_at"

    contract = await repository.get_advertiser_contract(
        db, str(campaign.advertiser_contract_id),
    )
    if contract is None:
        return "Campaign contract not found"

    if contract.valid_from and start_at < contract.valid_from:
        return "Flight start_at is before contract valid_from"

    if contract.valid_until is not None and end_at > contract.valid_until:
        return "Flight end_at is after contract valid_until"

    return None


async def _require_campaign_visible(db, campaign_id: str, scope: ScopeContext):
    """Return campaign if visible to caller, else raise 404.

    Checks both RLS (via get_campaign) and explicit org scope for defense-in-depth.
    Admin users bypass the org-id check.
    """
    campaign = await repository.get_campaign(db, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found"},
        )
    if not scope.is_admin:
        if str(campaign.advertiser_organization_id) not in scope.advertiser_scope_ids:
            raise HTTPException(
                status_code=404,
                detail={"code": "CAMPAIGN_NOT_FOUND", "message": "Campaign not found"},
            )
    return campaign
