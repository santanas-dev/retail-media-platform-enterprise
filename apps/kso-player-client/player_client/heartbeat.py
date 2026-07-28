"""KSO Player Client — heartbeat sender."""

from dataclasses import dataclass

from .http import PlayerHttpClient
from .retry_backoff import BackoffPolicy, RetryBackoffManager, execute_with_retries


@dataclass
class HeartbeatResult:
    accepted: bool
    server_time: str = ""


def send_heartbeat(
    http: PlayerHttpClient,
    health_state: str = "healthy",
    runtime_version: str = "0.1.0",
    player_version: str = "0.1.0",
    max_retries: int = 3,
) -> HeartbeatResult:
    policy = BackoffPolicy(max_attempts=max_retries, base_delay_sec=1.0)
    manager = RetryBackoffManager(policy)

    data = execute_with_retries(
        lambda: http.post_json("/api/v1/device/heartbeat", {
            "health_state": health_state,
            "runtime_version": runtime_version,
            "player_version": player_version,
        }),
        manager,
    )

    return HeartbeatResult(
        accepted=(data.get("status") == "accepted"),
        server_time=str(data.get("server_time", "")),
    )
