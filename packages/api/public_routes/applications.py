"""
BP-001 — Public advertiser application endpoint.
No authentication required. Submits a lead for admin review.
"""

from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import get_db
from packages.domain import repository
from packages.domain.schemas import AdvertiserApplicationCreate, AdvertiserApplicationOut

router = APIRouter()


@router.post(
    "/advertiser-applications",
    response_model=AdvertiserApplicationOut,
    status_code=201,
)
async def submit_application(
    body: AdvertiserApplicationCreate,
    db=Depends(get_db),
):
    # Server-side consent validation
    if not body.consent:
        raise HTTPException(
            status_code=422,
            detail="Требуется согласие на обработку данных",
        )

    application = await repository.create_advertiser_application(
        db,
        company_name=body.company_name.strip(),
        contact_name=body.contact_name.strip(),
        email=body.email.strip(),
        phone=body.phone.strip(),
        website=body.website.strip(),
        comment=body.comment.strip(),
        consent=body.consent,
    )

    # Audit event
    await repository.create_audit_event(
        db,
        actor_user_id="public",
        action="advertiser_application.created",
        target_type="advertiser_application",
        target_id=application.id,
        details={
            "company_name": application.company_name,
            "email": application.email,
        },
    )

    return application
