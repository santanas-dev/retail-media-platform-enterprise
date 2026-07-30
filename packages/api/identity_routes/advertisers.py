"""
Identity API — Advertiser Organizations, Brands, Contracts, Contacts, Memberships.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from packages.api.dependencies import (
    get_db,
    require_scoped_permission,
    set_rls_context,
    get_current_active_user,
)
from packages.domain import repository
from packages.domain.schemas import (
    AdvertiserBrandCreate,
    AdvertiserBrandOut,
    AdvertiserBrandUpdate,
    AdvertiserContactOut,
    AdvertiserContractOut,
    AdvertiserLegalRequisitesUpdate,
    AdvertiserOrganizationCreate,
    AdvertiserOrganizationDetailOut,
    AdvertiserOrganizationOut,
    AdvertiserUserMembershipOut,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Advertiser Organizations (Phase 3.5b — RLS pilot)
# ---------------------------------------------------------------------------


@router.get("/advertiser-organizations", response_model=list[AdvertiserOrganizationOut])
async def list_advertiser_organizations(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("organization.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_organizations(db)
    return [AdvertiserOrganizationOut.model_validate(o) for o in items]


@router.post("/advertiser-organizations", response_model=AdvertiserOrganizationOut, status_code=201)
async def create_advertiser_organization(
    body: AdvertiserOrganizationCreate,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new advertiser organization (admin-only)."""
    from packages.domain.repository import create_audit_event
    org = await repository.create_advertiser_organization(
        db, code=body.code, legal_name=body.legal_name, display_name=body.display_name,
    )
    await create_audit_event(
        db,
        actor_user_id=current_user["sub"],
        action="advertiser_organization.created",
        target_type="advertiser_organization",
        target_id=org.id,
    )
    return AdvertiserOrganizationOut.model_validate(org)


# ---------------------------------------------------------------------------
# Advertiser Brands (Phase 4.0b)
# ---------------------------------------------------------------------------


@router.get("/advertiser-brands", response_model=list[AdvertiserBrandOut])
async def list_advertiser_brands(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_brands(db)
    return [AdvertiserBrandOut.model_validate(b) for b in items]


# ---------------------------------------------------------------------------
# Advertiser Contracts (Phase 4.0b)
# ---------------------------------------------------------------------------


@router.get("/advertiser-contracts", response_model=list[AdvertiserContractOut])
async def list_advertiser_contracts(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_contracts(db)
    return [AdvertiserContractOut.model_validate(c) for c in items]


# ---------------------------------------------------------------------------
# Advertiser Contacts (Phase 4.0b)
# ---------------------------------------------------------------------------


@router.get("/advertiser-contacts", response_model=list[AdvertiserContactOut])
async def list_advertiser_contacts(
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.contacts.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_contacts(db)
    return [AdvertiserContactOut.model_validate(c) for c in items]


# ---------------------------------------------------------------------------
# S-039 — Advertiser detail + memberships
# ---------------------------------------------------------------------------


@router.get("/advertiser-organizations/{org_id}", response_model=AdvertiserOrganizationDetailOut)
async def get_advertiser_organization_detail(
    org_id: str,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    org = await repository.get_advertiser_organization(db, org_id)
    if org is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Organization not found"},
        )
    return AdvertiserOrganizationDetailOut.model_validate(org)


@router.put("/advertiser-organizations/{org_id}/legal-requisites", response_model=AdvertiserOrganizationDetailOut)
async def update_advertiser_organization_legal_requisites(
    org_id: str,
    body: AdvertiserLegalRequisitesUpdate,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
    current_user: dict = Depends(get_current_active_user),
):
    """Update legal requisites for an advertiser organization (ADVERTISER-UX-001A1)."""
    from packages.domain.repository import create_audit_event

    org = await repository.update_advertiser_organization_requisites(
        db, org_id,
        legal_entity_type=body.legal_entity_type,
        legal_form=body.legal_form,
        legal_form_other=body.legal_form_other,
        legal_name=body.legal_name,
        inn=body.inn,
        legal_address=body.legal_address,
        settlement_account=body.settlement_account,
        correspondent_account=body.correspondent_account,
        bik=body.bik,
        bank_name=body.bank_name,
        kpp=body.kpp,
        ogrn=body.ogrn,
        ogrnip=body.ogrnip,
    )
    if org is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "NOT_FOUND", "message": "Organization not found"},
        )
    await create_audit_event(
        db,
        actor_user_id=current_user["sub"],
        action="advertiser_organization.legal_requisites_updated",
        target_type="advertiser_organization",
        target_id=org_id,
    )
    return AdvertiserOrganizationDetailOut.model_validate(org)


@router.get("/advertiser-brands-by-org", response_model=list[AdvertiserBrandOut])
async def list_advertiser_brands_by_org(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_brands_by_org(db, advertiser_organization_id)
    return [AdvertiserBrandOut.model_validate(b) for b in items]


@router.post("/advertiser-brands", response_model=AdvertiserBrandOut, status_code=201)
async def create_advertiser_brand(
    body: AdvertiserBrandCreate,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Create a new brand for an advertiser organization."""
    brand = await repository.create_advertiser_brand(
        db,
        advertiser_organization_id=body.advertiser_organization_id,
        code=body.code,
        name=body.name,
        description=body.description,
    )
    return AdvertiserBrandOut.model_validate(brand)


@router.patch("/advertiser-brands/{brand_id}", response_model=AdvertiserBrandOut)
async def update_advertiser_brand(
    brand_id: str,
    body: AdvertiserBrandUpdate,
    advertiser_organization_id: str = Query(..., description="Scope guard: org ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Update an existing brand. Brand must belong to the given org."""
    brand = await repository.update_advertiser_brand(
        db,
        brand_id=brand_id,
        advertiser_organization_id=advertiser_organization_id,
        code=body.code,
        name=body.name,
        description=body.description,
    )
    if not brand:
        raise HTTPException(status_code=404, detail="Brand not found")
    return AdvertiserBrandOut.model_validate(brand)


@router.get("/advertiser-contracts-by-org", response_model=list[AdvertiserContractOut])
async def list_advertiser_contracts_by_org(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_contracts_by_org(db, advertiser_organization_id)
    return [AdvertiserContractOut.model_validate(c) for c in items]


@router.get("/advertiser-contacts-by-org", response_model=list[AdvertiserContactOut])
async def list_advertiser_contacts_by_org(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.contacts.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_contacts_by_org(db, advertiser_organization_id)
    return [AdvertiserContactOut.model_validate(c) for c in items]


@router.get("/advertiser-user-memberships", response_model=list[AdvertiserUserMembershipOut])
async def list_advertiser_user_memberships(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_user_memberships(db, advertiser_organization_id)
    return [AdvertiserUserMembershipOut(**row) for row in items]
