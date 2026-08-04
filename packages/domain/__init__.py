"""
Retail Media Platform — Shared Domain Enums and Constants.

Phase 1: Placeholders only. No ORM, no DB dependencies.
"""
from enum import StrEnum


class ChannelType(StrEnum):
    KSO = "KSO"
    ANDROID_TV = "ANDROID_TV"
    PRICE_CHECKER = "PRICE_CHECKER"
    ESL = "ESL"
    LED = "LED"
    MOCK = "MOCK"


class DeviceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    ERROR = "error"
    MAINTENANCE = "maintenance"
    REVOKED = "revoked"
    UNREGISTERED = "unregistered"


class ProofMode(StrEnum):
    REAL_PLAYBACK = "real_playback"
    SCREEN_RENDER = "screen_render"
    IDLE_SCREEN = "idle_screen"
    TEMPLATE_APPLIED = "template_applied"
    GATEWAY_ACK = "gateway_ack"
    LABEL_ACK = "label_ack"
    CONTROLLER_ACK = "controller_ack"


class CertificateType(StrEnum):
    RSA = "rsa"
    ED25519 = "ed25519"
    HSM = "hsm"


class ManifestStatus(StrEnum):
    GENERATED = "generated"
    DELIVERED = "delivered"
    APPLIED = "applied"
    EXPIRED = "expired"
    ERROR = "error"


class PlaybackResult(StrEnum):
    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class CampaignStatus(StrEnum):
    """Campaign lifecycle status — single source of truth.

    Realised transitions (guarded by ALLOWED_TRANSITIONS):
        draft → pending_approval → approved → active → paused
        pending_approval → rejected
        active → completed  (LIFECYCLE-COMPLETE-001)
    """
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ACTIVE = "active"
    PAUSED = "paused"
    REJECTED = "rejected"
    COMPLETED = "completed"


# ── Campaign lifecycle transition guard ──
# Only these transitions are valid.  A transition NOT listed here raises
# ValueError, which callers translate into a 409/422 domain error.
ALLOWED_TRANSITIONS: dict[CampaignStatus, set[CampaignStatus]] = {
    CampaignStatus.DRAFT: {CampaignStatus.PENDING_APPROVAL},
    CampaignStatus.PENDING_APPROVAL: {CampaignStatus.APPROVED, CampaignStatus.REJECTED},
    CampaignStatus.APPROVED: {CampaignStatus.ACTIVE},
    CampaignStatus.ACTIVE: {CampaignStatus.PAUSED, CampaignStatus.COMPLETED},
}


def validate_transition(
    current: CampaignStatus | str,
    target: CampaignStatus,
) -> CampaignStatus:
    """Validate a campaign status transition.

    Raises ValueError with a Russian message if the transition is not allowed.
    Returns the current status coerced to CampaignStatus on success.
    """
    if isinstance(current, str):
        try:
            current = CampaignStatus(current)
        except ValueError:
            raise ValueError(
                f"Неизвестный статус кампании: {current}. "
                f"Допустимые: {[s.value for s in CampaignStatus]}"
            )
    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise ValueError(
            f"Недопустимый переход: {current.value} → {target.value}. "
            f"Разрешённые переходы из {current.value}: "
            f"{[s.value for s in sorted(allowed)]}"
        )
    return current


# Service identifiers for logging/metrics
SERVICE_CONTROL_API = "control-api"
SERVICE_DEVICE_GATEWAY = "device-gateway"
SERVICE_POP_INGESTOR = "pop-ingestor"
SERVICE_ORCHESTRATOR = "orchestrator-worker"
SERVICE_ADAPTER_MOCK = "adapter-mock"
SERVICE_ADAPTER_KSO = "adapter-kso"

# Defaults
DEFAULT_CORRELATION_ID_HEADER = "X-Correlation-ID"
DEVICE_CORRELATION_ID_HEADER = "X-Device-Correlation-ID"
