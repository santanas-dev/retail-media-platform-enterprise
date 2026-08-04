"""
DOMAIN-ENUM-001 — CampaignStatus transition guard unit tests.
"""
import pytest
from packages.domain import (
    CampaignStatus,
    ALLOWED_TRANSITIONS,
    validate_transition,
)


class TestCampaignStatusEnum:
    """Verify the enum has the real lifecycle values, no dead entries."""

    def test_real_values_present(self):
        assert CampaignStatus.DRAFT == "draft"
        assert CampaignStatus.PENDING_APPROVAL == "pending_approval"
        assert CampaignStatus.APPROVED == "approved"
        assert CampaignStatus.ACTIVE == "active"
        assert CampaignStatus.PAUSED == "paused"
        assert CampaignStatus.REJECTED == "rejected"

    def test_no_dead_values(self):
        """MODERATION, REVIEW, SCHEDULED, LIVE, ARCHIVED, CANCELLED removed.
        COMPLETED is now implemented (LIFECYCLE-COMPLETE-001)."""
        dead = {"moderation", "review", "scheduled", "live", "archived", "cancelled"}
        enum_values = {s.value for s in CampaignStatus}
        assert enum_values.isdisjoint(dead), f"Dead values still in enum: {enum_values & dead}"


class TestAllowedTransitions:
    """Verify ALLOWED_TRANSITIONS covers the real lifecycle."""

    def test_draft_to_pending_approval(self):
        assert CampaignStatus.PENDING_APPROVAL in ALLOWED_TRANSITIONS[CampaignStatus.DRAFT]

    def test_pending_approval_to_approved_rejected(self):
        allowed = ALLOWED_TRANSITIONS[CampaignStatus.PENDING_APPROVAL]
        assert CampaignStatus.APPROVED in allowed
        assert CampaignStatus.REJECTED in allowed

    def test_approved_to_active(self):
        assert CampaignStatus.ACTIVE in ALLOWED_TRANSITIONS[CampaignStatus.APPROVED]

    def test_active_to_paused(self):
        assert CampaignStatus.PAUSED in ALLOWED_TRANSITIONS[CampaignStatus.ACTIVE]

    def test_no_completed_yet(self):
        """COMPLETED is now implemented — LIFECYCLE-COMPLETE-001."""
        assert CampaignStatus.COMPLETED == "completed"
        assert CampaignStatus.COMPLETED in ALLOWED_TRANSITIONS[CampaignStatus.ACTIVE]

    def test_rejected_is_terminal(self):
        """Rejected has no outgoing transitions."""
        assert CampaignStatus.REJECTED not in ALLOWED_TRANSITIONS

    def test_completed_is_terminal(self):
        """Completed has no outgoing transitions."""
        assert CampaignStatus.COMPLETED not in ALLOWED_TRANSITIONS


class TestValidateTransition:
    """Validate transition guard function."""

    def test_valid_draft_to_pending_approval(self):
        result = validate_transition(CampaignStatus.DRAFT, CampaignStatus.PENDING_APPROVAL)
        assert result == CampaignStatus.DRAFT

    def test_valid_pending_to_approved(self):
        result = validate_transition(CampaignStatus.PENDING_APPROVAL, CampaignStatus.APPROVED)
        assert result == CampaignStatus.PENDING_APPROVAL

    def test_valid_pending_to_rejected(self):
        result = validate_transition(CampaignStatus.PENDING_APPROVAL, CampaignStatus.REJECTED)
        assert result == CampaignStatus.PENDING_APPROVAL

    def test_valid_approved_to_active(self):
        result = validate_transition(CampaignStatus.APPROVED, CampaignStatus.ACTIVE)
        assert result == CampaignStatus.APPROVED

    def test_valid_active_to_paused(self):
        result = validate_transition(CampaignStatus.ACTIVE, CampaignStatus.PAUSED)
        assert result == CampaignStatus.ACTIVE

    def test_valid_active_to_completed(self):
        result = validate_transition(CampaignStatus.ACTIVE, CampaignStatus.COMPLETED)
        assert result == CampaignStatus.ACTIVE

    def test_string_input_accepted(self):
        result = validate_transition("draft", CampaignStatus.PENDING_APPROVAL)
        assert result == CampaignStatus.DRAFT

    # ── Invalid transitions ──

    def test_draft_to_active_rejected(self):
        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.DRAFT, CampaignStatus.ACTIVE)

    def test_approved_to_rejected_rejected(self):
        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.APPROVED, CampaignStatus.REJECTED)

    def test_paused_to_active_rejected(self):
        """Resume not implemented — paused → active not allowed."""
        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.PAUSED, CampaignStatus.ACTIVE)

    def test_active_to_draft_rejected(self):
        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.ACTIVE, CampaignStatus.DRAFT)

    def test_unknown_status_raises(self):
        with pytest.raises(ValueError, match="Неизвестный статус"):
            validate_transition("garbage_status", CampaignStatus.ACTIVE)

    def test_completed_to_anything_rejected(self):
        """Completed is terminal — no outgoing transitions."""
        with pytest.raises(ValueError, match="Недопустимый переход"):
            validate_transition(CampaignStatus.COMPLETED, CampaignStatus.ACTIVE)
