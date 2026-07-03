"""
Retail Media Platform — Audit/Mask Sanitization Helpers.

Phase 3.2b: Remove/mask secrets from dicts before logging or audit storage.
"""

import copy

# Exact sensitive keys to mask (after normalization: lowercase, _ → -, strip -).
# These match the FULL key name, not substrings — to avoid false positives
# like authorization_id or tokenizer_config.
#
# Two categories: passwords/secrets → "***", tokens/headers → "***MASKED***"
_SENSITIVE_SHORT: frozenset[str] = frozenset({
    "password",
    "passwd",
    "pwd",
    "secret",
})
_SENSITIVE_TOKEN: frozenset[str] = frozenset({
    "token",
    "access-token",
    "access_token",
    "refresh-token",
    "refresh_token",
    "reset-token",
    "reset_token",
    "id-token",
    "id_token",
    "jwt",
    "api-key",
    "api_key",
    "authorization",
    "cookie",
    "set-cookie",
    "set_cookie",
})


def sanitize_auth_details(data: dict | None) -> dict:
    """Recursively sanitize a dict by masking sensitive fields.

    Returns a deep copy with sensitive values replaced by '***'.
    Handles nested dicts and lists of dicts.
    Only masks EXACT key matches — no substring matching.

    Args:
        data: Raw dict (may contain secrets). None returns {}.

    Returns:
        Sanitized dict safe for logging and audit storage.
    """
    if data is None:
        return {}

    result = copy.deepcopy(data)
    _sanitize_recursive(result)
    return result


def _normalize(key: str) -> str:
    """Normalize a key for lookup: lowercase, _ → -, strip leading/trailing -."""
    return key.lower().replace("_", "-").strip("-")


def _sanitize_recursive(obj: dict | list) -> None:
    """Mutate obj in-place, masking sensitive fields."""
    if isinstance(obj, dict):
        keys_to_mask = []
        keys_to_mask_token = []
        for key in obj:
            norm = _normalize(key)
            if norm in _SENSITIVE_SHORT:
                keys_to_mask.append(key)
            elif norm in _SENSITIVE_TOKEN:
                keys_to_mask_token.append(key)

        for key in keys_to_mask:
            obj[key] = "***"
        for key in keys_to_mask_token:
            obj[key] = "***MASKED***"

        # Recurse into nested values
        for value in obj.values():
            _sanitize_recursive(value)

    elif isinstance(obj, list):
        for item in obj:
            _sanitize_recursive(item)
