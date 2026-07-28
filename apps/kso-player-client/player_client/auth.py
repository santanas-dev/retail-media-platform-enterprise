"""KSO Player Client — device authentication."""

import time
from dataclasses import dataclass, field
from typing import Optional

from .http import PlayerHttpClient
from .retry_backoff import BackoffPolicy, RetryBackoffManager, execute_with_retries


@dataclass
class TokenState:
    access_token: str = field(default="", repr=False)
    expires_at: float = 0.0

    @classmethod
    def from_auth_response(cls, data: dict, now: Optional[float] = None) -> "TokenState":
        now = now or time.time()
        token = data.get("access_token", "")
        if not token:
            raise ValueError("auth response missing access_token")
        expires_in = int(data.get("expires_in", 3600))
        return cls(access_token=token, expires_at=now + expires_in)

    def is_valid(self, now: Optional[float] = None, safety_window: int = 30) -> bool:
        now = now or time.time()
        return bool(self.access_token) and self.expires_at > now + safety_window


def authenticate(http: PlayerHttpClient, max_retries: int = 3) -> TokenState:
    """Acquire device JWT via POST /auth/token or return configured JWT."""
    return _do_auth(http, max_retries)


def _do_auth(http: PlayerHttpClient, max_retries: int) -> TokenState:
    policy = BackoffPolicy(max_attempts=max_retries, base_delay_sec=1.0)
    manager = RetryBackoffManager(policy)

    def _op() -> TokenState:
        data = http.post_json("/api/v1/auth/token", {
            "device_code": http.token,  # placeholder - actual auth endpoint
        })
        return TokenState.from_auth_response(data)

    return execute_with_retries(_op, manager, sleep_fn=time.sleep)
