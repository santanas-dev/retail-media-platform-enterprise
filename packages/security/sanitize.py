"""
Retail Media Platform — Audit/Mask Sanitization Helpers.

Phase 3.2b: Remove/mask secrets from dicts before logging or audit storage.
"""

import copy

# Fields to mask: key name → replacement value
_MASK_RULES: dict[str, str] = {
    "password": "***",
    "passwd": "***",
    "secret": "***",
    "token": "***MASKED***",
    "access_token": "***MASKED***",
    "refresh_token": "***MASKED***",
    "authorization": "***MASKED***",
    "cookie": "***MASKED***",
    "set-cookie": "***MASKED***",
    "set_cookie": "***MASKED***",
    "api_key": "***MASKED***",
    "jwt": "***MASKED***",
}


def sanitize_auth_details(data: dict | None) -> dict:
    """Recursively sanitize a dict by masking sensitive fields.

    Returns a deep copy with sensitive values replaced by '***'.
    Handles nested dicts and lists of dicts.

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


def _sanitize_recursive(obj: dict | list) -> None:
    """Mutate obj in-place, masking sensitive fields."""
    if isinstance(obj, dict):
        # Collect keys to mask (can't mutate during iteration)
        keys_to_mask = []
        for key in obj:
            key_lower = key.lower().replace("_", "-")
            for pattern, replacement in _MASK_RULES.items():
                if pattern in key_lower:
                    keys_to_mask.append((key, replacement))
                    break

        for key, replacement in keys_to_mask:
            obj[key] = replacement

        # Recurse into nested values
        for value in obj.values():
            _sanitize_recursive(value)

    elif isinstance(obj, list):
        for item in obj:
            _sanitize_recursive(item)
