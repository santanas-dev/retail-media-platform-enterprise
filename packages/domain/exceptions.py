"""
Retail Media Platform — Domain Exceptions.

Application-agnostic error types raised by domain/services layer.
No FastAPI, no HTTP status codes — routers translate to HTTP.
"""


class DomainError(Exception):
    """Base domain error."""


class ScopeError(DomainError):
    """Caller is outside the required tenant scope."""


class CrossOrgReferenceError(DomainError):
    """Cross-organization reference detected (brand/contract belongs to a
    different organization than the request)."""


class EntityNotFoundError(DomainError):
    """Referenced entity does not exist."""
