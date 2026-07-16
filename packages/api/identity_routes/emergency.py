"""
Identity API — Emergency Override (S-071).
"""

from fastapi import APIRouter, Depends, HTTPException

from packages.api.dependencies import get_db, require_permission, set_rls_context
from packages.domain import repository
from packages.domain.schemas import (
    EmergencyStatusOut,
    EmergencyActivateRequest,
    EmergencyDeactivateRequest,
)

router = APIRouter()


def _actor_from_claims(claims: dict) -> str:
    return claims.get("sub", "unknown")


# ---------------------------------------------------------------------------
# Emergency status
# ---------------------------------------------------------------------------


@router.get("/emergency/status", response_model=EmergencyStatusOut)
async def emergency_status(
    db=Depends(get_db),
    _claims: dict = Depends(require_permission("emergency.read")),
    _rls=Depends(set_rls_context),
):
    override = await repository.get_active_emergency_override(db)
    if override is None:
        return EmergencyStatusOut(active=False)
    return EmergencyStatusOut(
        active=True,
        reason=override.reason,
        activated_by=override.activated_by,
        activated_at=override.activated_at,
    )


@router.post("/emergency/activate", response_model=EmergencyStatusOut)
async def emergency_activate(
    body: EmergencyActivateRequest,
    db=Depends(get_db),
    claims: dict = Depends(require_permission("emergency.manage")),
    _rls=Depends(set_rls_context),
):
    try:
        override = await repository.activate_emergency_override(
            db,
            reason=body.reason,
            activated_by=_actor_from_claims(claims),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Audit event
    await repository.create_audit_event(
        db,
        actor_user_id=_actor_from_claims(claims),
        action="emergency.activated",
        target_type="emergency_override",
        target_id=override.id,
        details={"reason": body.reason},
    )
    return EmergencyStatusOut(
        active=True,
        reason=override.reason,
        activated_by=override.activated_by,
        activated_at=override.activated_at,
    )


@router.post("/emergency/deactivate", response_model=EmergencyStatusOut)
async def emergency_deactivate(
    body: EmergencyDeactivateRequest,
    db=Depends(get_db),
    claims: dict = Depends(require_permission("emergency.manage")),
    _rls=Depends(set_rls_context),
):
    try:
        override = await repository.deactivate_emergency_override(
            db,
            reason=body.reason,
            deactivated_by=_actor_from_claims(claims),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Audit event
    await repository.create_audit_event(
        db,
        actor_user_id=_actor_from_claims(claims),
        action="emergency.deactivated",
        target_type="emergency_override",
        target_id=override.id,
        details={"reason": body.reason},
    )
    return EmergencyStatusOut(active=False)
