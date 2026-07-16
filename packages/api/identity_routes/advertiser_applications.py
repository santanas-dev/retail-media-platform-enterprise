"""
Identity API — Admin review of advertiser applications (BP-001).
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.api.dependencies import get_db, require_permission, set_rls_context
from packages.domain import repository
from packages.domain.schemas import (
    AdvertiserApplicationOut,
    AdvertiserApplicationReview,
    AdvertiserApplicationListOut,
)

router = APIRouter()


def _actor_from_claims(claims: dict) -> str:
    return claims.get("sub", "unknown")


# ── List applications ──


@router.get("/advertiser-applications", response_model=AdvertiserApplicationListOut)
async def list_applications(
    status: str | None = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("advertiser_applications.read")),
    _rls=Depends(set_rls_context),
):
    items, total = await repository.list_advertiser_applications(
        db,
        status_filter=status,
        offset=offset,
        limit=limit,
    )
    return AdvertiserApplicationListOut(items=items, total=total, limit=limit, offset=offset)


# ── Detail ──


@router.get("/advertiser-applications/{application_id}", response_model=AdvertiserApplicationOut)
async def get_application(
    application_id: str,
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("advertiser_applications.read")),
    _rls=Depends(set_rls_context),
):
    app = await repository.get_advertiser_application(db, application_id)
    if app is None:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    return app


# ── Review ──


@router.post("/advertiser-applications/{application_id}/review", response_model=AdvertiserApplicationOut)
async def review_application(
    application_id: str,
    body: AdvertiserApplicationReview,
    db=Depends(get_db),
    claims: dict = Depends(require_permission("advertiser_applications.review")),
    _rls=Depends(set_rls_context),
):
    actor = _actor_from_claims(claims)

    try:
        app = await repository.review_advertiser_application(
            db,
            application_id=application_id,
            action=body.action,
            reviewer_id=actor,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Audit
    await repository.create_audit_event(
        db,
        actor_user_id=actor,
        action=f"advertiser_application.{body.action}d",
        target_type="advertiser_application",
        target_id=application_id,
        details={"reason": body.reason},
    )

    # On approve — create AdvertiserOrganization
    if body.action == "approve":
        org_id = await repository.create_advertiser_from_application(
            db,
            application=app,
        )
        await repository.create_audit_event(
            db,
            actor_user_id=actor,
            action="advertiser_organization.created_from_application",
            target_type="advertiser_organization",
            target_id=org_id,
            details={
                "application_id": application_id,
                "company_name": app.company_name,
            },
        )

    return app
