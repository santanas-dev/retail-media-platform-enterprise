"""KSO Player Client — retry/backoff manager (imported from retail-media-platform).

Source: santanas-dev/retail-media-platform, apps/kso_sidecar_agent/kso_sidecar_agent/retry_backoff.py
License: internal.
Adapted for enterprise: HttpClientError replaced with local PlayerHttpError.
"""

import random as _random
import time as _time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Tuple


class PlayerHttpError(Exception):
    """HTTP-level error with retryable classification."""

    def __init__(self, status_code: int, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


FORBIDDEN_REASON_SUBSTRINGS = [
    "token", "jwt", "password", "secret", "api_key",
    "private_key", "payment_card", "receipt",
    "device_secret", "access_token",
]


def _redact_reason(reason: str) -> str:
    result = reason
    lower = result.lower()
    for forbidden in FORBIDDEN_REASON_SUBSTRINGS:
        if forbidden in lower:
            result = result.replace(forbidden, "[REDACTED]")
            result = result.replace(forbidden.title(), "[REDACTED]")
            result = result.replace(forbidden.upper(), "[REDACTED]")
    return result


@dataclass
class BackoffPolicy:
    max_attempts: int = 3
    base_delay_sec: float = 2.0
    max_delay_sec: float = 60.0
    multiplier: float = 2.0
    jitter_ratio: float = 0.25

    def __post_init__(self) -> None:
        if not isinstance(self.max_attempts, int) or self.max_attempts < 1 or self.max_attempts > 10:
            raise ValueError(f"max_attempts must be 1–10, got {self.max_attempts!r}")
        if not isinstance(self.base_delay_sec, (int, float)) or self.base_delay_sec <= 0:
            raise ValueError(f"base_delay_sec must be > 0, got {self.base_delay_sec!r}")
        if not isinstance(self.max_delay_sec, (int, float)) or self.max_delay_sec < self.base_delay_sec:
            raise ValueError(f"max_delay_sec must be >= base_delay_sec ({self.base_delay_sec}), got {self.max_delay_sec!r}")
        if not isinstance(self.multiplier, (int, float)) or self.multiplier < 1.0:
            raise ValueError(f"multiplier must be >= 1.0, got {self.multiplier!r}")
        if not isinstance(self.jitter_ratio, (int, float)) or self.jitter_ratio < 0.0 or self.jitter_ratio > 1.0:
            raise ValueError(f"jitter_ratio must be 0.0–1.0, got {self.jitter_ratio!r}")


@dataclass
class RetryDecision:
    attempt: int
    max_attempts: int
    retryable: bool
    should_retry: bool
    delay_sec: float
    reason: str

    def __post_init__(self) -> None:
        self.reason = _redact_reason(self.reason)


class RetryBackoffManager:
    def __init__(self, policy: BackoffPolicy, random_fn: Optional[Callable[[], float]] = None) -> None:
        self._policy = policy
        self._random = random_fn or _random.random

    @property
    def policy(self) -> BackoffPolicy:
        return self._policy

    def classify_error(self, error: Exception) -> Tuple[bool, str]:
        if isinstance(error, PlayerHttpError):
            return error.retryable, _redact_reason(str(error))
        if isinstance(error, (TimeoutError, ConnectionError, OSError)):
            return True, _redact_reason(str(error))
        if isinstance(error, (ValueError, RuntimeError)):
            return False, _redact_reason(str(error))
        return False, _redact_reason(str(error))

    def compute_delay(self, attempt: int) -> float:
        if attempt < 1:
            raise ValueError(f"attempt must be >= 1, got {attempt}")
        base = self._policy.base_delay_sec
        exp = attempt - 1
        delay = base * (self._policy.multiplier ** exp)
        if self._policy.jitter_ratio > 0:
            jitter_range = delay * self._policy.jitter_ratio
            jitter = (self._random() - 0.5) * 2 * jitter_range
            delay += jitter
        delay = max(delay, 0.0)
        delay = min(delay, self._policy.max_delay_sec)
        return delay

    def next_decision(self, attempt: int, error: Exception) -> RetryDecision:
        retryable, reason = self.classify_error(error)
        should_retry = retryable and (attempt < self._policy.max_attempts)
        delay_sec = self.compute_delay(attempt + 1) if should_retry else 0.0
        return RetryDecision(
            attempt=attempt,
            max_attempts=self._policy.max_attempts,
            retryable=retryable,
            should_retry=should_retry,
            delay_sec=delay_sec,
            reason=reason,
        )


def execute_with_retries(
    operation: Callable[[], Any],
    manager: RetryBackoffManager,
    sleep_fn: Optional[Callable[[float], None]] = None,
) -> Any:
    _sleep = sleep_fn or _time.sleep
    last_error: Optional[Exception] = None
    for attempt in range(1, manager.policy.max_attempts + 1):
        try:
            return operation()
        except Exception as e:
            last_error = e
            decision = manager.next_decision(attempt, e)
            if not decision.should_retry:
                raise
            _sleep(decision.delay_sec)
    assert last_error is not None
    raise last_error
