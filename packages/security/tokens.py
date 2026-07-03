"""
Retail Media Platform — Token Helpers.

Phase 3.2b: Secure random token generation and SHA-256 hashing.
No raw token persistence — only token_hash is stored.
"""

import hashlib
import hmac
import secrets

from packages.security.config import get_security_config


def generate_token(byte_length: int | None = None) -> str:
    """Generate a cryptographically secure random token.

    Args:
        byte_length: Number of random bytes (default: from config, 32 bytes).

    Returns:
        URL-safe hex string (2x byte_length characters).
    """
    if byte_length is None:
        cfg = get_security_config()
        byte_length = cfg.refresh_token_bytes
    return secrets.token_hex(byte_length)


def hash_token(raw_token: str) -> str:
    """Hash a raw token using SHA-256.

    Used for storing refresh tokens and password reset tokens —
    only the hash is persisted, never the raw token.

    Args:
        raw_token: The raw token string to hash.

    Returns:
        SHA-256 hex digest of the token.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def constant_time_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time.

    Prevents timing attacks when comparing token hashes or secrets.

    Args:
        a: First string.
        b: Second string.

    Returns:
        True if strings are equal.
    """
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def verify_token_hash(raw_token: str, token_hash: str) -> bool:
    """Verify a raw token against its stored SHA-256 hash.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        raw_token: The raw token to verify.
        token_hash: The stored SHA-256 hash.

    Returns:
        True if raw_token hashes to token_hash.
    """
    computed = hash_token(raw_token)
    return constant_time_compare(computed, token_hash)
