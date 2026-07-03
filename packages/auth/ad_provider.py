"""
Retail Media Platform — AD Auth Provider Interface.

Phase 3.2c: Abstract interface for AD/LDAPS authentication.
Only stub implementation — no real LDAPS client yet.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ADVerifyResult:
    """Result of AD credential verification."""

    success: bool
    username: str | None = None
    display_name: str | None = None
    email: str | None = None
    external_subject: str | None = None  # objectSid
    error_code: str | None = None


class ADAuthProvider(ABC):
    """Abstract interface for Active Directory authentication.

    Implementations:
    - StubADAuthProvider: always returns unavailable (Phase 3.2c)
    - LDAPADAuthProvider: real LDAPS bind/search (Phase 3.2+)
    """

    @abstractmethod
    async def verify_credentials(
        self, username: str, password: str
    ) -> ADVerifyResult:
        """Verify username/password against AD.

        Args:
            username: sAMAccountName.
            password: Plaintext password (never stored, only used for bind).

        Returns:
            ADVerifyResult with success/failure and user attributes.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if AD is reachable."""
        ...


class StubADAuthProvider(ADAuthProvider):
    """Stub AD provider — always returns unavailable.

    Used in development and testing until LDAPS client is implemented (Phase 3.2+).
    """

    async def verify_credentials(
        self, username: str, password: str
    ) -> ADVerifyResult:
        return ADVerifyResult(
            success=False,
            error_code="ldap_unavailable",
        )

    async def is_available(self) -> bool:
        return False
