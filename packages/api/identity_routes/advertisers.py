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
from packages.security.config import get_security_config
from packages.domain.schemas import (
    AdvertiserBrandCreate,
    AdvertiserBrandOut,
    AdvertiserBrandUpdate,
    AdvertiserContactCreate,
    AdvertiserContactOut,
    AdvertiserContactUpdate,
    AdvertiserContractCreate,
    AdvertiserContractOut,
    AdvertiserContractUpdate,
    AdvertiserLegalRequisitesUpdate,
    AdvertiserOrganizationCreate,
    AdvertiserOrganizationDetailOut,
    AdvertiserOrganizationOut,
    AdvertiserUserMembershipOut,
    ContractUploadIntentRequest,
    ContractUploadIntentResponse,
    ContractUploadCompleteRequest,
    ContractUploadCompleteResponse,
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
    """Create a new advertiser organization (admin-only).

    Code is auto-generated when omitted. Duplicate explicit code → 409.
    """
    from packages.domain.repository import create_audit_event
    from sqlalchemy.exc import IntegrityError

    try:
        org = await repository.create_advertiser_organization(
            db, code=body.code, legal_name=body.legal_name,
            display_name=body.display_name,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Организация с кодом '{body.code}' уже существует",
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


@router.post("/advertiser-contacts", response_model=AdvertiserContactOut, status_code=201)
async def create_advertiser_contact(
    body: AdvertiserContactCreate,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
    current_user: dict = Depends(get_current_active_user),
):
    """Create a new advertiser contact (ADVERTISER-UX-001B3)."""
    from packages.domain.repository import create_audit_event

    try:
        contact = await repository.create_advertiser_contact(
            db,
            advertiser_organization_id=body.advertiser_organization_id,
            full_name=body.full_name,
            email=body.email,
            phone=body.phone,
            title=body.title,
            contact_type=body.contact_type,
            is_primary=body.is_primary,
            user_id=body.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    await create_audit_event(
        db,
        actor_user_id=current_user["sub"],
        action="advertiser_contact.created",
        target_type="advertiser_contact",
        target_id=contact.id,
    )
    return AdvertiserContactOut.model_validate(contact)


@router.patch("/advertiser-contacts/{contact_id}", response_model=AdvertiserContactOut)
async def update_advertiser_contact(
    contact_id: str,
    body: AdvertiserContactUpdate,
    advertiser_organization_id: str = Query(..., description="Scope guard: org ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
    current_user: dict = Depends(get_current_active_user),
):
    """Update an advertiser contact (ADVERTISER-UX-001B3)."""
    from packages.domain.repository import create_audit_event

    try:
        contact = await repository.update_advertiser_contact(
            db,
            contact_id=contact_id,
            advertiser_organization_id=advertiser_organization_id,
            full_name=body.full_name,
            email=body.email,
            phone=body.phone,
            title=body.title,
            contact_type=body.contact_type,
            is_primary=body.is_primary,
            status=body.status,
            user_id=body.user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    await create_audit_event(
        db,
        actor_user_id=current_user["sub"],
        action="advertiser_contact.updated",
        target_type="advertiser_contact",
        target_id=contact.id,
    )
    return AdvertiserContactOut.model_validate(contact)


@router.get("/advertiser-user-memberships", response_model=list[AdvertiserUserMembershipOut])
async def list_advertiser_user_memberships(
    advertiser_organization_id: str = Query(..., description="Filter by organization ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.read", "advertiser")),
    _rls=Depends(set_rls_context),
):
    items = await repository.list_advertiser_user_memberships(db, advertiser_organization_id)
    return [AdvertiserUserMembershipOut(**row) for row in items]


# ---------------------------------------------------------------------------
# ADVERTISER-UX-001B2 — Contract CRUD + PDF Upload
# ---------------------------------------------------------------------------


@router.post("/advertiser-contracts", response_model=AdvertiserContractOut, status_code=201)
async def create_advertiser_contract(
    body: AdvertiserContractCreate,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Create a new advertiser contract."""
    contract = await repository.create_advertiser_contract(
        db,
        advertiser_organization_id=body.advertiser_organization_id,
        code=body.code,
        name=body.name,
        contract_number=body.contract_number,
        budget_limit_amount=body.budget_limit_amount,
        budget_limit_currency=body.budget_limit_currency,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    return AdvertiserContractOut.model_validate(contract)


@router.patch("/advertiser-contracts/{contract_id}", response_model=AdvertiserContractOut)
async def update_advertiser_contract(
    contract_id: str,
    body: AdvertiserContractUpdate,
    advertiser_organization_id: str = Query(..., description="Scope guard: org ID"),
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Update an existing advertiser contract. Contract must belong to the given org."""
    contract = await repository.update_advertiser_contract(
        db,
        contract_id=contract_id,
        advertiser_organization_id=advertiser_organization_id,
        code=body.code,
        name=body.name,
        contract_number=body.contract_number,
        budget_limit_amount=body.budget_limit_amount,
        budget_limit_currency=body.budget_limit_currency,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return AdvertiserContractOut.model_validate(contract)


# ── Contract PDF upload (presigned URL flow, mirrors creative upload pattern) ──


@router.post("/advertiser-contracts/{contract_id}/upload-intent",
             response_model=ContractUploadIntentResponse)
async def contract_upload_intent(
    contract_id: str,
    body: ContractUploadIntentRequest,
    db=Depends(get_db),
    claims: dict = Depends(get_current_active_user),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Request a presigned upload URL for a contract PDF."""
    cfg = get_security_config()

    # PDF-only validation
    if body.content_type != "application/pdf":
        raise HTTPException(status_code=422, detail="Only PDF files are accepted")
    if body.content_length > cfg.contract_max_file_size_bytes:
        raise HTTPException(status_code=422,
                            detail=f"File too large: {body.content_length} bytes")

    contract = await repository.get_advertiser_contract(db, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    org_id = str(contract.advertiser_organization_id)

    storage_key = f"{org_id}/{contract_id}/{body.filename}"
    bucket = cfg.contract_storage_bucket

    from packages.services.storage import get_storage_service
    storage = get_storage_service()
    upload_url, expires_at = await storage.async_contract_generate_presigned_put(storage_key)

    session_id = await repository.create_contract_upload_session(
        db,
        contract_id=contract_id,
        advertiser_organization_id=org_id,
        storage_bucket=bucket,
        storage_key=storage_key,
        filename=body.filename,
        content_type=body.content_type,
        content_length=body.content_length,
        created_by=claims["sub"],
        ttl_seconds=cfg.contract_upload_url_ttl_seconds,
    )

    return ContractUploadIntentResponse(
        upload_id=session_id,
        upload_url=upload_url,
        method="PUT",
        headers={"Content-Type": body.content_type},
        expires_at=expires_at.isoformat(),
    )


@router.post("/advertiser-contracts/{contract_id}/complete-upload",
             response_model=ContractUploadCompleteResponse)
async def contract_complete_upload(
    contract_id: str,
    body: ContractUploadCompleteRequest,
    db=Depends(get_db),
    _perm=Depends(require_scoped_permission("advertisers.manage", "advertiser")),
    _rls=Depends(set_rls_context),
):
    """Verify and complete a contract PDF upload. Sets file metadata on the contract."""
    from datetime import datetime, timezone as _tz

    upload = await repository.get_contract_upload_session(db, body.upload_id)
    if upload is None:
        raise HTTPException(status_code=404, detail="Upload session not found")
    if upload["contract_id"] != contract_id:
        raise HTTPException(status_code=422, detail="Upload session does not match this contract")
    if upload["completed_at"] is not None:
        raise HTTPException(status_code=409, detail="Upload already completed")

    if upload["expires_at"] < datetime.now(_tz.utc):
        raise HTTPException(status_code=410, detail="Upload session expired")

    from packages.services.storage import get_storage_service
    storage = get_storage_service()
    if not await storage.async_contract_object_exists(upload["storage_key"]):
        raise HTTPException(status_code=404, detail="File not found in storage")

    actual_size = await storage.async_contract_get_object_size(upload["storage_key"])
    if actual_size != upload["content_length"]:
        raise HTTPException(status_code=422,
                            detail=f"Size mismatch: expected {upload['content_length']}, got {actual_size}")

    checksum = await storage.async_contract_compute_sha256(upload["storage_key"])
    if checksum is None:
        raise HTTPException(status_code=500, detail="Failed to compute checksum")

    contract = await repository.set_contract_file_metadata(
        db,
        contract_id=contract_id,
        storage_key=upload["storage_key"],
        filename=upload["filename"],
        content_type=upload["content_type"],
        file_size_bytes=actual_size,
        sha256=checksum,
    )
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    await repository.mark_contract_upload_complete(db, body.upload_id)

    return ContractUploadCompleteResponse(
        contract_id=contract_id,
        sha256_checksum=checksum,
        file_size_bytes=actual_size,
    )
