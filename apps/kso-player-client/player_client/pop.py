"""KSO Player Client — PoP batch sender."""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .http import PlayerHttpClient
from .retry_backoff import BackoffPolicy, RetryBackoffManager, execute_with_retries


@dataclass
class PopSendResult:
    accepted_count: int = 0
    rejected_count: int = 0
    quarantined_count: int = 0
    duplicate_count: int = 0

    @property
    def accepted(self) -> bool:
        return self.accepted_count > 0


def send_pop_batch(
    http: PlayerHttpClient,
    manifest_id: str,
    device_id: str,
    campaign_id: str = "",
    surface_id: str = "",
    creative_asset_id: str = "",
    duration_ms: int = 10000,
    max_retries: int = 3,
) -> PopSendResult:
    now = datetime.now(timezone.utc).isoformat()
    event_id = str(uuid.uuid4())

    events = [{
        "event_id": event_id,
        "event_type": "proof",
        "schema_version": "1.0",
        "device_id": device_id,
        "manifest_id": manifest_id if manifest_id else None,
        "campaign_id": campaign_id if campaign_id else None,
        "creative_asset_id": creative_asset_id,
        "surface_id": surface_id,
        "duration_ms": duration_ms,
        "playback_result": "success",
        "rendered_at": now,
        "event_recorded_at": now,
    }]

    policy = BackoffPolicy(max_attempts=max_retries, base_delay_sec=1.0)
    manager = RetryBackoffManager(policy)

    data = execute_with_retries(
        lambda: http.post_json("/api/v1/pop/batch", {"events": events}),
        manager,
    )

    return PopSendResult(
        accepted_count=int(data.get("accepted_count", 0)),
        rejected_count=int(data.get("rejected_count", 0)),
        quarantined_count=int(data.get("quarantined_count", 0)),
        duplicate_count=int(data.get("duplicate_count", 0)),
    )
