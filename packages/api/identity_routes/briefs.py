"""
Identity API — Campaign Briefs / Placement Requests (BP-004).

Advertiser-scoped: list, detail, create draft, update draft, submit.
Status lifecycle: draft → submitted.
"""
from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import (
    get_current_active_user,
    get_db,
    require_scoped_permission,
    set_rls_context,
)
from packages.domain import repository
from packages.domain.schemas import (
    CampaignBriefOut,
    CampaignBriefCreateRequest,
    CampaignBriefUpdateRequest,
    PaginatedResponse,
)

from .common import _scope_ids

router = APIRouter()


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get("/campaign-briefs", response_model=PaginatedResponse[CampaignBriefOut])
async def list_briefs(
    db=Depends(get_db),
    _user=Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    scope_ids = _scope_ids(scope)
    items, total = await repository.list_campaign_briefs(
        db, scope_advertiser_ids=scope_ids,
    )
    return PaginatedResponse(
        items=[CampaignBriefOut.model_validate(b) for b in items],
        total=total,
        limit=50,
        offset=0,
    )


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------


@router.get("/campaign-briefs/{brief_id}", response_model=CampaignBriefOut)
async def get_brief(
    brief_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    scope_ids = _scope_ids(scope)
    brief = await repository.get_campaign_brief(
        db, brief_id, scope_advertiser_ids=scope_ids,
    )
    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    return CampaignBriefOut.model_validate(brief)


# ---------------------------------------------------------------------------
# Create draft
# ---------------------------------------------------------------------------


@router.post("/campaign-briefs", response_model=CampaignBriefOut, status_code=201)
async def create_brief(
    body: CampaignBriefCreateRequest,
    db=Depends(get_db),
    user=Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    scope_ids = _scope_ids(scope)
    if not scope_ids:
        raise HTTPException(status_code=403, detail="No advertiser scope")

    org_id = next(iter(scope_ids))
    brief_id = await repository.create_campaign_brief(
        db,
        advertiser_organization_id=org_id,
        title=body.title,
        created_by=user["sub"],
        objective=body.objective,
        product_category=body.product_category,
        target_period_from=body.target_period_from,
        target_period_to=body.target_period_to,
        budget_amount=body.budget_amount,
        budget_currency=body.budget_currency,
        preferred_channels=body.preferred_channels,
        comment=body.comment,
        scope_advertiser_ids=scope_ids,
    )
    await db.flush()
    brief = await repository.get_campaign_brief(db, brief_id)
    return CampaignBriefOut.model_validate(brief)


# ---------------------------------------------------------------------------
# Update draft
# ---------------------------------------------------------------------------


@router.patch("/campaign-briefs/{brief_id}", response_model=CampaignBriefOut)
async def update_brief(
    brief_id: str,
    body: CampaignBriefUpdateRequest,
    db=Depends(get_db),
    _user=Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    scope_ids = _scope_ids(scope)
    try:
        brief = await repository.update_campaign_brief(
            db,
            brief_id,
            scope_advertiser_ids=scope_ids,
            title=body.title,
            objective=body.objective,
            product_category=body.product_category,
            target_period_from=body.target_period_from,
            target_period_to=body.target_period_to,
            budget_amount=body.budget_amount,
            budget_currency=body.budget_currency,
            preferred_channels=body.preferred_channels,
            comment=body.comment,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    await db.flush()
    return CampaignBriefOut.model_validate(brief)


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


@router.post("/campaign-briefs/{brief_id}/submit", response_model=CampaignBriefOut)
async def submit_brief(
    brief_id: str,
    db=Depends(get_db),
    _user=Depends(get_current_active_user),
    scope=Depends(require_scoped_permission("campaigns.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    scope_ids = _scope_ids(scope)
    try:
        brief = await repository.submit_campaign_brief(
            db, brief_id, scope_advertiser_ids=scope_ids,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    if brief is None:
        raise HTTPException(status_code=404, detail="Brief not found")
    await db.flush()
    return CampaignBriefOut.model_validate(brief)
