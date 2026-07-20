"""
Identity API — AD / LDAPS Settings (S-034, G4-FIX durable persistence).
"""

from fastapi import APIRouter, Depends

from packages.api.dependencies import (
    get_db,
    get_scope_context,
    require_permission,
    set_rls_context,
)
from packages.domain.scopes import ScopeContext
from packages.domain.schemas import ADSettingsOut, ADSettingsUpdate, ADTestResultOut

router = APIRouter()


@router.get("/auth/ad-settings", response_model=ADSettingsOut)
async def get_ad_settings(
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    """Return current AD/LDAPS settings — persisted in DB, secret-free."""
    from packages.security.config import get_security_config
    from packages.auth.ad_provider import get_ad_provider
    from packages.domain.repository import get_ad_settings

    cfg = get_security_config()
    ad = get_ad_provider()
    available = await ad.is_available()

    # Read from DB (durable); fall back to env defaults if row missing
    row = await get_ad_settings(db)

    enabled = row.enabled
    server_url = row.server_url
    mode, message = _derive_status(cfg, enabled, server_url, available)

    return ADSettingsOut(
        enabled=enabled,
        mode=mode,
        server_url=server_url if enabled else "",
        base_dn=row.base_dn,
        user_search_base=row.user_search_base,
        user_search_filter=row.user_search_filter,
        bind_dn=row.bind_dn,
        use_tls=row.use_tls,
        certificate_validation=row.certificate_validation,
        message=message,
    )


@router.put("/auth/ad-settings", response_model=ADSettingsOut)
async def update_ad_settings(
    body: ADSettingsUpdate,
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    """Update AD/LDAPS settings — persisted to DB. Bind password is NEVER accepted — env-only."""
    from packages.security.config import get_security_config
    from packages.auth.ad_provider import get_ad_provider
    from packages.domain.repository import create_audit_event, save_ad_settings

    cfg = get_security_config()

    # Validate certificate_validation
    if body.certificate_validation not in ("required", "optional", "none"):
        from fastapi import HTTPException
        raise HTTPException(
            status_code=422,
            detail="certificate_validation must be one of: required, optional, none",
        )

    # Persist to DB (durable — survives restart)
    row = await save_ad_settings(
        db,
        enabled=body.enabled,
        server_url=body.server_url,
        base_dn=body.base_dn,
        user_search_base=body.user_search_base,
        user_search_filter=body.user_search_filter,
        bind_dn=body.bind_dn,
        use_tls=body.use_tls,
        certificate_validation=body.certificate_validation,
    )

    # Also update runtime config for in-process consistency
    cfg.ad_enabled = body.enabled
    cfg.ad_server_url = body.server_url
    cfg.ad_base_dn = body.base_dn
    cfg.ad_user_search_base = body.user_search_base
    cfg.ad_user_search_filter = body.user_search_filter
    cfg.ad_bind_dn = body.bind_dn
    cfg.ad_use_tls = body.use_tls
    cfg.ad_certificate_validation = body.certificate_validation

    # Audit — no secrets in details
    await create_audit_event(
        db,
        actor_user_id=scope.user_id,
        action="ad_settings.updated",
        target_type="ad_settings",
        details={
            "enabled": body.enabled,
            "server_url": body.server_url,
            "base_dn": body.base_dn,
            "user_search_base": body.user_search_base,
            "bind_dn": body.bind_dn,
            "use_tls": body.use_tls,
            "certificate_validation": body.certificate_validation,
        },
    )

    ad = get_ad_provider()
    available = await ad.is_available()
    mode, message = _derive_status(cfg, body.enabled, body.server_url, available)

    return ADSettingsOut(
        enabled=body.enabled,
        mode=mode,
        server_url=body.server_url if body.enabled else "",
        base_dn=body.base_dn,
        user_search_base=body.user_search_base,
        user_search_filter=body.user_search_filter,
        bind_dn=body.bind_dn,
        use_tls=body.use_tls,
        certificate_validation=body.certificate_validation,
        message=message,
    )


@router.post("/auth/ad-settings/test", response_model=ADTestResultOut)
async def test_ad_connection(
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    """Test AD connection — honest stub until real LDAPS client exists."""
    from datetime import datetime, timezone
    from packages.security.config import get_security_config
    from packages.auth.ad_provider import get_ad_provider

    cfg = get_security_config()
    now = datetime.now(timezone.utc)

    if not cfg.ad_enabled:
        return ADTestResultOut(
            status="not_configured",
            message="AD integration is not configured. Employee AD login returns 503.",
            tested_at=now,
            error_code="ad_disabled",
        )

    if not cfg.ad_server_url:
        return ADTestResultOut(
            status="misconfigured",
            message="AD integration is enabled but AD_SERVER_URL is not set.",
            tested_at=now,
            error_code="ad_misconfigured",
        )

    ad = get_ad_provider()
    available = await ad.is_available()
    if not available:
        return ADTestResultOut(
            status="unavailable",
            message="AD server is not reachable. Check AD_SERVER_URL, network, and TLS configuration.",
            tested_at=now,
            error_code="ad_unavailable",
        )

    return ADTestResultOut(
        status="ok",
        message="AD connection test passed — server reachable.",
        tested_at=now,
    )


def _derive_status(cfg, enabled: bool, server_url: str, available: bool) -> tuple[str, str]:
    if not enabled:
        return "disabled", "AD integration is disabled. Employee AD login is not available."
    if not server_url:
        return "misconfigured", "AD integration is enabled but AD_SERVER_URL is not set."
    if not available:
        return "unavailable", "AD integration is configured but the server is not reachable."
    return "configured", "AD integration is configured."
