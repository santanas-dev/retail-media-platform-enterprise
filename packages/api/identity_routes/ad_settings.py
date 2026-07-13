"""
Identity API — AD / LDAPS Settings (S-034).
"""

from fastapi import APIRouter, Depends

from packages.api.dependencies import (
    get_db,
    get_scope_context,
    require_permission,
    set_rls_context,
)
from packages.domain.scopes import ScopeContext
from packages.domain.schemas import ADSettingsOut, ADTestResultOut

router = APIRouter()


@router.get("/auth/ad-settings", response_model=ADSettingsOut)
async def get_ad_settings(
    db=Depends(get_db),
    scope: ScopeContext = Depends(get_scope_context),
    _rls=Depends(set_rls_context),
    _claims: dict = Depends(require_permission("users.manage")),
):
    """Return current AD/LDAPS connection status and config."""
    from packages.security.config import get_security_config
    from packages.auth.ad_provider import get_ad_provider

    cfg = get_security_config()
    ad = get_ad_provider()
    available = await ad.is_available()

    if not cfg.ad_enabled:
        mode = "disabled"
        message = "AD integration is disabled. Employee AD login is not available."
    elif not cfg.ad_server_url:
        mode = "misconfigured"
        message = "AD integration is enabled but AD_SERVER_URL is not set."
    elif available:
        mode = "configured"
        message = "AD integration is configured and reachable."
    else:
        mode = "unavailable"
        message = "AD integration is configured but the server is not reachable."

    return ADSettingsOut(
        enabled=cfg.ad_enabled,
        mode=mode,
        server_url=cfg.ad_server_url if cfg.ad_enabled else "",
        base_dn=cfg.ad_base_dn,
        user_search_base=cfg.ad_user_search_base,
        user_search_filter=cfg.ad_user_search_filter,
        bind_dn=cfg.ad_bind_dn,
        use_tls=cfg.ad_use_tls,
        certificate_validation=cfg.ad_certificate_validation,
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
