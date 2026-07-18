"""
Retail Media Platform — Headless Runtime Simulator.

Phase 4.2e: ADR-013 safety proofs.
No real player UI, no device OS, no production runtime daemon.
Pure in-memory state simulation for behavioral proof tests.

ADR-013 references:
  §1 Fail-Safe — no campaign content on invalid state
  §2 Kill-Switch — fail-closed for stale/unknown
  §3 Manifest Update Safety — atomic apply, last-known-good, monotonic guard
  §5 Offline Behavior — offline TTL enforcement
  §6 PoP Integrity — emit only after successful render, dedup
"""

import hashlib
import time
import uuid
from dataclasses import dataclass, field

from packages.contracts.manifest_signing import verify_manifest_signature


# ── Required manifest fields (per manifest_v1.schema.json + ADR-016) ──
REQUIRED_MANIFEST_FIELDS = {
    "manifest_id", "device_id", "store_id", "channel_type",
}

FORBIDDEN_MANIFEST_TERMS = [
    "storage_bucket", "storage_key", "access_key",
    "secret_key", "presigned_url", "token",
    "email", "phone", "password",
]


# ── Result types ──

@dataclass
class ApplyResult:
    success: bool
    failure_reason: str = ""
    manifest_id: str = ""
    manifest_version: int = 0


@dataclass
class RenderResult:
    played: bool
    failure_reason: str = ""
    event_id: str = ""
    surface_id: str = ""
    creative_asset_id: str = ""
    duration_ms: int = 0


# ── Simulator ──

class RuntimeSimulator:
    """Headless ADR-013 safety simulator for a single device.

    Simulates: manifest apply, kill-switch evaluation, render slot,
    PoP emission with dedup, offline TTL enforcement.

    No filesystem I/O, no network, no real media playback.
    """

    def __init__(
        self,
        device_id: str = "",
        device_code: str = "DEV-001",
        store_id: str = "",
        signing_key: str = "",
    ):
        self.device_id = device_id
        self.device_code = device_code
        self.store_id = store_id
        self.signing_key = signing_key  # MANIFEST_SIGNING_KEY for verification

        # Manifest state
        self._current_manifest: dict | None = None
        self._last_known_good: dict | None = None

        # Kill-switch (ADR-013 §2)
        self._kill_switch: dict = {
            "global": False,
            "store": False,
            "device": False,
            "campaign": {},  # campaign_id → bool
        }
        self._kill_switch_stale: bool = True  # fail-closed at boot

        # PoP event queue (ADR-013 §7: local buffer simulation)
        self._event_queue: list[dict] = []
        self._event_ids: set[str] = set()

        # Offline tracking (ADR-013 §5: monotonic clock)
        self._offline_start_monotonic: float | None = None
        self._offline_duration_s: float = 0.0

    # ── Manifest Apply (ADR-013 §3) ──────────────────────────────

    def apply_manifest(self, manifest: dict) -> ApplyResult:
        """Atomic manifest apply with validation and last-known-good retention.

        1. Validate shape + required fields
        2. Check for secrets/storage credentials
        3. Verify device_id match
        4. Monotonic version guard (unless emergency_flag)
        5. Atomic swap: temp verify → commit → discard old

        On any failure: keep last-known-good, return failure.
        """
        # Validate
        validation_errors = self.validate_manifest(manifest)
        if validation_errors:
            return ApplyResult(
                success=False,
                failure_reason="; ".join(validation_errors),
            )

        # Check for secrets
        import json
        manifest_str = json.dumps(manifest, default=str).lower()
        for term in FORBIDDEN_MANIFEST_TERMS:
            if term in manifest_str:
                return ApplyResult(
                    success=False,
                    failure_reason=f"Manifest contains forbidden term: {term}",
                )

        # Device ID match
        if manifest.get("device_id") != self.device_id:
            return ApplyResult(
                success=False,
                failure_reason="Manifest device_id does not match this device",
            )

        # Monotonic version guard (ADR-013 §3)
        if self._current_manifest is not None:
            new_version = manifest.get("manifest_version", 0)
            current_version = self._current_manifest.get("manifest_version", 0)
            is_emergency = manifest.get("emergency_flag", False)
            if new_version <= current_version and not is_emergency:
                return ApplyResult(
                    success=False,
                    failure_reason=(
                        f"Version {new_version} <= current {current_version} "
                        f"and emergency_flag is not set"
                    ),
                )

        # Signature verification (K2: real check, not placeholder)
        sig = manifest.get("signature", {})
        sig_value = sig.get("value", "")
        sig_algo = sig.get("algorithm", "")

        # Reject the old magic-string placeholder (security: never accept it)
        if sig_value == "INVALID":
            return ApplyResult(
                success=False,
                failure_reason="Manifest signature verification failed",
            )

        if self.signing_key:
            # Production mode: real signature required
            if not sig_value:
                return ApplyResult(
                    success=False,
                    failure_reason="Manifest signature is missing (signing key configured)",
                )
            if sig_algo != "HMAC-SHA256":
                return ApplyResult(
                    success=False,
                    failure_reason=f"Unsupported signature algorithm: {sig_algo}",
                )
            if not verify_manifest_signature(manifest, sig_value, self.signing_key):
                return ApplyResult(
                    success=False,
                    failure_reason="Manifest signature verification failed",
                )
        # When signing_key is not configured, accept unsigned manifests
        # (test/dev mode only; production MUST set MANIFEST_SIGNING_KEY)

        # Atomic swap: move current → last-known-good, set new
        self._last_known_good = self._current_manifest
        self._current_manifest = manifest
        return ApplyResult(
            success=True,
            manifest_id=manifest.get("manifest_id", ""),
            manifest_version=manifest.get("manifest_version", 0),
        )

    def validate_manifest(self, manifest: dict) -> list[str]:
        """Validate manifest shape and required fields. Returns error messages."""
        errors: list[str] = []
        for field in REQUIRED_MANIFEST_FIELDS:
            if field not in manifest or not manifest[field]:
                errors.append(f"Missing required field: {field}")
        if "manifest_version" not in manifest:
            errors.append("Missing manifest_version")
        if "display_surfaces" not in manifest:
            errors.append("Missing display_surfaces")
        return errors

    def rollback_to_last_known_good(self) -> None:
        """Roll back to the last-known-good manifest (ADR-013 §3)."""
        self._current_manifest = self._last_known_good

    # ── Kill-Switch (ADR-013 §2) ─────────────────────────────────

    def set_kill_switch(
        self, level: str, target_id: str = "", active: bool = True,
    ) -> None:
        """Set kill-switch state at any granularity level."""
        if level == "campaign":
            self._kill_switch["campaign"][target_id] = active
        elif level in ("global", "store", "device"):
            self._kill_switch[level] = active
        self._kill_switch_stale = False

    def clear_kill_switch_cache(self) -> None:
        """Simulate cache becoming stale (e.g., TTL expired, gateway unreachable)."""
        self._kill_switch_stale = True

    def refresh_kill_switch(self) -> None:
        """Simulate successful cache refresh from gateway."""
        self._kill_switch_stale = False

    def is_kill_switch_active(
        self, campaign_id: str = "", surface_id: str = "",
    ) -> bool:
        """Evaluate kill-switch state. Fail-closed for stale/unknown cache."""
        # ADR-013 §2: stale or unknown → fail closed (halt playback)
        if self._kill_switch_stale:
            return True

        # Check order: campaign → device → store → global
        if campaign_id and self._kill_switch["campaign"].get(campaign_id, False):
            return True
        if self._kill_switch["device"]:
            return True
        if self._kill_switch["store"]:
            return True
        if self._kill_switch["global"]:
            return True
        return False

    @property
    def kill_switch_stale(self) -> bool:
        return self._kill_switch_stale

    # ── Render (ADR-013 §1, §6) ──────────────────────────────────

    def render_slot(
        self,
        slot: dict | None = None,
        *,
        campaign_id: str = "",
        surface_id: str = "",
        creative_asset_id: str = "",
        duration_ms: int = 10000,
        is_fallback: bool = False,
    ) -> RenderResult:
        """Simulate rendering a playlist slot.

        Returns RenderResult with played=False if any safety gate blocks playback.

        Safety gates (in order):
        1. Kill-switch active → no play, no PoP
        2. Offline TTL expired → no play, no PoP
        3. No current manifest → no play
        4. Manifest expired (valid_to) → no play, follow fallback rules
        5. Manifest not yet valid (valid_from in future) → no play

        On successful render:
        - Emits PoP event with canonical fields
        - Deduplicates by event_id
        - Never emits PoP for fallback unless emit_pop=true
        """
        slot = slot or {}
        campaign_id = campaign_id or slot.get("campaign_id", "")
        surface_id = surface_id or slot.get("surface_id", "")
        creative_asset_id = creative_asset_id or slot.get("creative_asset_id", "")
        duration_ms = duration_ms or slot.get("duration_ms", 10000)

        # Gate 1: kill-switch (fail-closed for stale)
        if self.is_kill_switch_active(campaign_id=campaign_id):
            return RenderResult(
                played=False,
                failure_reason="kill_switch_active",
            )

        # Gate 2: offline TTL (ADR-013 §5)
        # Campaign content blocked. Fallback may play per fallback_rules.
        if self.is_offline_ttl_expired():
            if not is_fallback:
                return RenderResult(
                    played=False,
                    failure_reason="offline_ttl_expired",
                )
            # Fallback allowed — falls through to Gate 6 for no-PoP handling

        # Gate 3: no manifest
        manifest = self._current_manifest
        if manifest is None:
            return RenderResult(
                played=False,
                failure_reason="no_manifest_loaded",
            )

        # Gate 4: manifest expired
        valid_to = manifest.get("valid_to")
        if valid_to and self._is_past(valid_to):
            fallback = manifest.get("fallback_rules", {})
            on_expired = fallback.get("on_manifest_expired", "show_fallback")
            if is_fallback and on_expired != "show_fallback":
                return RenderResult(
                    played=False,
                    failure_reason="manifest_expired",
                )
            if not is_fallback:
                return RenderResult(
                    played=False,
                    failure_reason="manifest_expired",
                )

        # Gate 5: manifest not yet valid
        valid_from = manifest.get("valid_from")
        if valid_from and not self._is_past(valid_from):
            return RenderResult(
                played=False,
                failure_reason="manifest_not_yet_valid",
            )

        # Gate 6: no PoP for fallback unless emit_pop=true
        if is_fallback:
            fallback = manifest.get("fallback_rules", {})
            if not fallback.get("emit_pop", False):
                # Fallback plays but no billable PoP
                return RenderResult(
                    played=True,
                    event_id="",
                )

        # Successful render → emit PoP (ADR-013 §6)
        event = self._build_pop_event(
            manifest=manifest,
            campaign_id=campaign_id,
            surface_id=surface_id,
            creative_asset_id=creative_asset_id,
            duration_ms=duration_ms,
        )

        # Dedup by event_id
        if event["event_id"] in self._event_ids:
            # Idempotent — event already queued
            return RenderResult(
                played=True,
                event_id=event["event_id"],
            )

        self._event_ids.add(event["event_id"])
        self._event_queue.append(event)

        return RenderResult(
            played=True,
            event_id=event["event_id"],
            surface_id=surface_id,
            creative_asset_id=creative_asset_id,
            duration_ms=duration_ms,
        )

    def _build_pop_event(
        self,
        manifest: dict,
        campaign_id: str,
        surface_id: str,
        creative_asset_id: str,
        duration_ms: int,
        playback_result: str = "success",
    ) -> dict:
        """Build a PoP event with canonical fields (S-018 aligned)."""
        event_id = str(uuid.uuid4())
        now = _utcnow_iso()
        mid = manifest.get("manifest_id", "")
        return {
            "event_id": event_id,
            "event_type": "proof",
            "schema_version": "1.0",
            "device_id": self.device_id,
            "manifest_id": mid if mid else None,
            "campaign_id": campaign_id if campaign_id else None,
            "creative_asset_id": creative_asset_id,
            "surface_id": surface_id,
            "duration_ms": duration_ms,
            "playback_result": playback_result,
            "rendered_at": now,
            "event_recorded_at": now,
        }

    def _is_past(self, iso_str: str) -> bool:
        """Check if an ISO 8601 timestamp is in the past."""
        from datetime import datetime, timezone
        try:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
            return dt < datetime.now(timezone.utc)
        except (ValueError, TypeError):
            return False

    # ── Offline TTL (ADR-013 §5) ─────────────────────────────────

    def set_offline(self, offline: bool = True) -> None:
        """Simulate network state change."""
        if offline and self._offline_start_monotonic is None:
            self._offline_start_monotonic = time.monotonic()
        elif not offline:
            self._offline_start_monotonic = None

    def advance_offline_clock(self, hours: float) -> None:
        """Advance the simulated offline duration."""
        self._offline_duration_s += hours * 3600
        if self._offline_start_monotonic is not None:
            self._offline_start_monotonic = time.monotonic() - self._offline_duration_s

    def is_offline_ttl_expired(self) -> bool:
        """Check if offline TTL has been exceeded (ADR-013 §5)."""
        manifest = self._current_manifest
        if manifest is None:
            return False  # No manifest → no TTL to check
        ttl_hours = manifest.get("offline_ttl_hours", 168)
        if self._offline_start_monotonic is not None:
            elapsed = time.monotonic() - self._offline_start_monotonic
            total_s = self._offline_duration_s + elapsed
            return total_s >= (ttl_hours * 3600)
        return self._offline_duration_s >= (ttl_hours * 3600)

    # ── Properties ───────────────────────────────────────────────

    @property
    def current_manifest(self) -> dict | None:
        return self._current_manifest

    @property
    def last_known_good(self) -> dict | None:
        return self._last_known_good

    @property
    def event_queue(self) -> list[dict]:
        return list(self._event_queue)

    @property
    def playback_active(self) -> bool:
        """Is campaign playback currently allowed?"""
        if self._current_manifest is None:
            return False
        if self.is_kill_switch_active():
            return False
        if self.is_offline_ttl_expired():
            return False
        valid_to = self._current_manifest.get("valid_to")
        if valid_to and self._is_past(valid_to):
            return False
        return True

    def pop_events(self) -> list[dict]:
        """Get and clear the event queue (simulates batch delivery)."""
        events = list(self._event_queue)
        self._event_queue.clear()
        return events

    def reset(self) -> None:
        """Full reset to initial state."""
        self._current_manifest = None
        self._last_known_good = None
        self._kill_switch = {
            "global": False, "store": False, "device": False, "campaign": {},
        }
        self._kill_switch_stale = True
        self._event_queue.clear()
        self._event_ids.clear()
        self._offline_start_monotonic = None
        self._offline_duration_s = 0.0


# ── Helpers ──

def _utcnow_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def make_test_manifest(
    *,
    manifest_id: str = "",
    manifest_version: int = 1,
    device_id: str = "",
    device_code: str = "DEV-001",
    store_id: str = "store-1",
    store_code: str = "ST-001",
    channel_type: str = "KSO",
    device_type: str = "KSO-DEVICE",
    valid_from: str = "2026-01-01T00:00:00+00:00",
    valid_to: str = "2099-12-31T23:59:59+00:00",
    offline_ttl_hours: int = 168,
    display_surfaces: list[dict] | None = None,
    playlist: list[dict] | None = None,
    fallback_rules: dict | None = None,
    signature: dict | None = None,
    emergency_flag: bool = False,
    **extra,
) -> dict:
    """Build a valid skeleton manifest for simulator tests."""
    mid = manifest_id or str(uuid.uuid4())
    return {
        "manifest_id": mid,
        "manifest_version": manifest_version,
        "schema_version": "1.0",
        "device_id": device_id,
        "device_code": device_code,
        "store_id": store_id,
        "store_code": store_code,
        "channel_type": channel_type,
        "device_type": device_type,
        "display_surfaces": display_surfaces or [
            {"surface_id": str(uuid.uuid4()), "surface_code": "SURF-1"},
        ],
        "playlist": playlist or [],
        "media_files": [],
        "adapter_payload": {},
        "valid_from": valid_from,
        "valid_to": valid_to,
        "offline_ttl_hours": offline_ttl_hours,
        "fallback_rules": fallback_rules or {
            "on_manifest_expired": "show_fallback",
            "on_network_lost": "continue_last_valid",
            "filler_media_ids": [],
            "emit_pop": False,
        },
        "signature": signature or {
            "algorithm": "HMAC-SHA256",
            "value": "",
        },
        "emergency_flag": emergency_flag,
        **extra,
    }
