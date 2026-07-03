"""
Retail Media Platform — Password Helpers.

Phase 3.2b: bcrypt-based password hashing and verification via the bcrypt library.
Never logs passwords.
"""

import bcrypt

from packages.security.config import get_security_config


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        plain: Plaintext password.

    Returns:
        bcrypt hash string (decoded UTF-8).

    Raises:
        ValueError: If password is empty or too short.
    """
    _validate_password(plain)
    cfg = get_security_config()
    return bcrypt.hashpw(
        plain.encode("utf-8"),
        bcrypt.gensalt(rounds=cfg.password_bcrypt_rounds),
    ).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain: Plaintext password to check.
        hashed: bcrypt hash string.

    Returns:
        True if password matches hash.
    """
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(
            plain.encode("utf-8"),
            hashed.encode("utf-8"),
        )
    except (ValueError, TypeError):
        # Malformed hash or encoding issue
        return False


def _validate_password(plain: str) -> None:
    """Validate password meets minimum requirements."""
    if not plain:
        raise ValueError("Password must not be empty")
    cfg = get_security_config()
    if len(plain) < cfg.password_min_length:
        raise ValueError(
            f"Password must be at least {cfg.password_min_length} characters"
        )
