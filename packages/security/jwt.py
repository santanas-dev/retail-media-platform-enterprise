"""
Retail Media Platform — JWT Helpers.

Phase 3.2b: Create and verify JWT access tokens.
No endpoint integration — pure crypto helpers.
"""

import time
import uuid

import jwt as pyjwt

from packages.security.config import get_security_config


def create_access_token(
    sub: str,
    auth_provider: str,
) -> str:
    """Create a signed JWT access token.

    Args:
        sub: Subject — user UUID.
        auth_provider: One of 'ad', 'local_advertiser', 'local_break_glass'.

    Returns:
        Encoded JWT string.
    """
    cfg = get_security_config()
    now = int(time.time())
    claims = {
        "sub": sub,
        "auth_provider": auth_provider,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + (cfg.jwt_access_token_ttl_minutes * 60),
        "iss": cfg.jwt_issuer,
    }
    return pyjwt.encode(claims, cfg.jwt_secret, algorithm=cfg.jwt_algorithm)


def verify_access_token(token: str) -> dict:
    """Verify and decode a JWT access token.

    Args:
        token: Encoded JWT string.

    Returns:
        Decoded claims dict.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidTokenError: Token is invalid (wrong signature, alg=none, etc.).
    """
    cfg = get_security_config()
    leeway = cfg.jwt_clock_skew_seconds

    claims = pyjwt.decode(
        token,
        cfg.jwt_secret,
        algorithms=[cfg.jwt_algorithm],
        options={
            "verify_exp": True,
            "verify_iat": True,
            "verify_signature": True,
            "require": ["sub", "auth_provider", "jti", "iat", "exp", "iss"],
        },
        issuer=cfg.jwt_issuer,
        leeway=leeway,
    )
    return claims
