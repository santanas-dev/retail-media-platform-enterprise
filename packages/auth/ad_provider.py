"""Active Directory / LDAPS authentication provider.

Phase 3.2c: Abstract interface + stub + real LDAPS implementation.

Implementations:
- StubADAuthProvider: always returns unavailable (honest 503)
- RealLDAPAuthProvider: real LDAPS bind/search via ldap3
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ADVerifyResult:
    """Result of an AD credential verification."""

    success: bool
    error_code: str | None = None
    display_name: str | None = None
    email: str | None = None
    groups: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class ADAuthProvider(ABC):
    """Abstract interface for Active Directory authentication."""

    @abstractmethod
    async def verify_credentials(
        self, username: str, password: str,
    ) -> ADVerifyResult:
        """Verify username/password against AD. Never stores password."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Quick connectivity test — does not require user credentials."""
        ...


# ---------------------------------------------------------------------------
# Stub — honest 503 during development
# ---------------------------------------------------------------------------


class StubADAuthProvider(ADAuthProvider):
    """Stub AD provider — always returns unavailable.

    Used in development and testing until LDAPS client is implemented.
    """

    async def verify_credentials(
        self, username: str, password: str,
    ) -> ADVerifyResult:
        return ADVerifyResult(
            success=False,
            error_code="ldap_unavailable",
        )

    async def is_available(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Real LDAPS implementation
# ---------------------------------------------------------------------------


class RealLDAPAuthProvider(ADAuthProvider):
    """Real Active Directory / LDAPS authentication via ldap3.

    Config from SecurityConfig env vars:
    - AD_ENABLED=true
    - AD_SERVER_URL (ldaps://host:636 or ldap://host:389)
    - AD_BASE_DN
    - AD_USER_SEARCH_BASE
    - AD_USER_SEARCH_FILTER (default: (sAMAccountName={username}))
    - AD_BIND_DN (service account; optional)
    - AD_BIND_PASSWORD (service account password)
    - AD_USE_TLS (default: true)
    - AD_CERTIFICATE_VALIDATION: required|optional|none

    Security:
    - Never logs passwords or bind credentials.
    - Uses ldap3 safe filter escaping against injection.
    - Timeout on all socket operations (10s receive, 5s connect).
    - Connection errors → safe 503 response, no LDAP internals exposed.
    """

    def __init__(self) -> None:
        from packages.security.config import get_security_config

        self._cfg = get_security_config()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def is_available(self) -> bool:
        """Quick check — bind service account or anonymous, then unbind."""
        try:
            conn = self._connect()
            self._bind_service(conn)
            conn.unbind()
            return True
        except Exception:
            return False

    async def verify_credentials(
        self, username: str, password: str,
    ) -> ADVerifyResult:
        """Full bind + search + user bind flow."""
        import logging

        _log = logging.getLogger("rmp.ad")

        if not self._cfg.ad_enabled:
            return ADVerifyResult(success=False, error_code="ad_disabled")

        if not self._cfg.ad_server_url:
            return ADVerifyResult(success=False, error_code="ad_misconfigured")

        conn = None
        try:
            conn = self._connect()
            self._bind_service(conn)

            user_dn = self._search_user(conn, username)
            if user_dn is None:
                _log.info("AD user not found: %s", username)
                return ADVerifyResult(
                    success=False, error_code="invalid_credentials",
                )

            if not self._bind_user(conn, user_dn, password):
                _log.info("AD bind failed: %s", username)
                return ADVerifyResult(
                    success=False, error_code="invalid_credentials",
                )

            display_name = self._read_display_name(conn, user_dn)
            _log.info("AD auth success: %s", username)
            return ADVerifyResult(
                success=True,
                display_name=display_name,
            )

        except _AdConnectionError:
            _log.warning("AD unavailable for user: %s", username)
            return ADVerifyResult(success=False, error_code="ad_unavailable")
        except Exception:
            _log.exception("AD auth error: %s", username)
            return ADVerifyResult(success=False, error_code="ad_unavailable")
        finally:
            if conn:
                try:
                    conn.unbind()
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _connect(self):
        import ldap3
        import ssl

        url = self._cfg.ad_server_url
        use_ssl = url.startswith("ldaps://")

        tls = None
        if self._cfg.ad_use_tls:
            tls_kwargs = {}
            cert_val = self._cfg.ad_certificate_validation
            if cert_val == "required":
                tls_kwargs["validate"] = ssl.CERT_REQUIRED
            elif cert_val == "optional":
                tls_kwargs["validate"] = getattr(ssl, "CERT_OPTIONAL", ssl.CERT_NONE)
            elif cert_val == "none":
                tls_kwargs["validate"] = ssl.CERT_NONE
            # Agnostically pass CA cert file if configured (applies to
            # required/optional — ignored by ldap3 for CERT_NONE).
            if self._cfg.ad_ca_cert_file:
                tls_kwargs["ca_certs_file"] = self._cfg.ad_ca_cert_file
            tls = ldap3.Tls(**tls_kwargs) if tls_kwargs else None

        host = url
        for prefix in ("ldaps://", "ldap://"):
            if host.startswith(prefix):
                host = host[len(prefix):]
        port = 636 if use_ssl else 389
        if ":" in host:
            host, port_str = host.rsplit(":", 1)
            port = int(port_str)

        server = ldap3.Server(
            host, port=port, use_ssl=use_ssl, tls=tls, connect_timeout=5,
        )
        conn = ldap3.Connection(
            server,
            receive_timeout=10,
            auto_bind=False,
            raise_exceptions=False,
        )
        return conn

    def _bind_service(self, conn) -> None:
        ok = conn.bind()
        if ok:
            return

        # Try service account if anonymous failed
        bind_dn = self._cfg.ad_bind_dn
        bind_pw = self._cfg.ad_bind_password
        if bind_dn and bind_pw:
            ok = conn.rebind(user=bind_dn, password=bind_pw)
            if ok:
                return

        desc = conn.result.get("description", "unknown")
        raise _AdConnectionError(f"bind failed: {desc}")

    def _search_user(self, conn, username: str) -> str | None:
        import ldap3

        search_base = self._cfg.ad_user_search_base or self._cfg.ad_base_dn
        if not search_base:
            return None

        safe_username = ldap3.utils.conv.escape_filter_chars(username)
        filter_str = self._cfg.ad_user_search_filter.replace(
            "{username}", safe_username,
        )

        conn.search(
            search_base=search_base,
            search_filter=filter_str,
            search_scope=ldap3.SUBTREE,
            attributes=["distinguishedName", "displayName"],
            size_limit=2,
            time_limit=8,
        )

        entries = conn.entries
        if len(entries) != 1:
            return None
        return str(entries[0].entry_dn)

    def _bind_user(self, conn, user_dn: str, password: str) -> bool:
        import ldap3

        try:
            # Don't modify original connection — use a fresh bind
            from ldap3 import Connection as LdapConnection

            conn2 = LdapConnection(
                conn.server,
                user=user_dn,
                password=password,
                receive_timeout=10,
                auto_bind=False,
                raise_exceptions=False,
            )
            conn2.open()
            ok = conn2.bind()
            try:
                conn2.unbind()
            except Exception:
                pass
            return bool(ok)
        except ldap3.core.exceptions.LDAPException:
            return False

    def _read_display_name(self, conn, user_dn: str) -> str | None:
        import ldap3

        conn.search(
            search_base=user_dn,
            search_filter="(objectClass=*)",
            search_scope=ldap3.BASE,
            attributes=["displayName"],
            size_limit=1,
            time_limit=5,
        )
        if conn.entries:
            val = conn.entries[0].displayName
            return str(val) if val else None
        return None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _AdConnectionError(Exception):
    """AD/LDAP connection error — safe to expose as 503."""


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_ad_provider() -> ADAuthProvider:
    """Return the appropriate AD auth provider based on config."""
    from packages.security.config import get_security_config

    cfg = get_security_config()
    if cfg.ad_enabled and cfg.ad_server_url:
        return RealLDAPAuthProvider()
    return StubADAuthProvider()
