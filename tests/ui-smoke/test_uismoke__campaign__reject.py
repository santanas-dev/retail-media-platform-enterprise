"""
UI-smoke: campaign.reject — reject a pending campaign with reason.
Pattern: create → primary creative upload → flights → placements → submit → reject → verify reason.
Uses CREATIVE_AUTO_APPROVE_UPLOADS (CI default) — creative pre-approved, no moderation needed.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test-creative.png")


def test_uismoke__campaign__reject(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── Create campaign ──
    page.click('[data-testid="campaign-create-open"]')
    page.wait_for_url("**/campaigns/new", timeout=10000)
    page.select_option("#c-org", index=1)
    page.select_option("#c-contract", index=1)
    campaign_code = f"SMOKE-RJ-{os.urandom(2).hex()}"
    page.fill("#c-code", campaign_code)
    page.fill("#c-name", f"Reject {campaign_code}")
    page.fill("#c-budget", "100000")
    page.click('button:has-text("Создать черновик")')
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── Navigate to content tab ──
    page.click('[data-testid="tab-content"]')
    page.wait_for_load_state("networkidle")

    # ── Primary creative upload ──
    creative_code = f"RJ-CR-{os.urandom(2).hex()}"
    page.locator('[data-testid="creative-upload-select-file"]').click()
    page.locator('[data-testid="creative-upload-primary-file-input"]').set_input_files(FIXTURE)
    expect(page.locator('[data-testid="creative-upload-primary-code"]')).to_be_visible(timeout=5000)
    page.locator('[data-testid="creative-upload-primary-code"]').fill(creative_code)
    page.locator('[data-testid="creative-upload-metadata-submit"]').click()
    expect(page.locator('[data-testid="creative-upload-done"]')).to_be_visible(timeout=30000)
    print(f"[{time.time()-t0:.1f}s] Creative uploaded")

    # ── Flights ──
    page.click('[data-testid="flight-add-btn"]')
    expect(page.locator('[data-testid="flight-start"]')).to_be_visible(timeout=5000)
    page.fill('[data-testid="flight-start"]', "2027-05-01")
    page.fill('[data-testid="flight-end"]', "2027-05-31")
    page.click('[data-testid="flight-submit"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Flight added")

    # ── Placements ──
    page.click('[data-testid="placement-add-btn"]')
    expect(page.locator('[data-testid="placement-surface"]')).to_be_visible(timeout=5000)
    page.locator('[data-testid="placement-surface"]').select_option(index=1)
    page.click('[data-testid="placement-submit"]')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Placement added")

    # ── Back to overview ──
    page.click('[data-testid="tab-overview"]')
    page.wait_for_load_state("networkidle")

    # ── Submit ──
    submit_btn = page.locator('[data-testid="campaign-submit-btn"]')
    expect(submit_btn).to_be_enabled(timeout=10000)
    submit_btn.click()
    try:
        page.wait_for_selector('[data-testid="campaign-submit-error"]', timeout=5000)
        err = page.locator('[data-testid="campaign-submit-error"]').inner_text()
        raise AssertionError(f"Submit failed: {err}")
    except Exception as e:
        if "Submit failed" in str(e):
            raise
    page.wait_for_load_state("networkidle")
    status_badge = page.locator('[data-testid="campaign-status-badge"]')
    expect(status_badge).to_be_visible(timeout=10000)
    assert "На согласовании" in status_badge.inner_text()
    print(f"[{time.time()-t0:.1f}s] Submitted")

    # ── Reject ──
    reject_btn = page.locator('[data-testid="campaign-reject-btn"]')
    expect(reject_btn).to_be_visible(timeout=5000)
    reject_btn.click()
    reason = "Недостаточный бюджет на Q3"
    reason_input = page.locator('[data-testid="campaign-reject-reason"]')
    expect(reason_input).to_be_visible(timeout=5000)
    reason_input.fill(reason)
    page.locator('[data-testid="campaign-reject-confirm"]').click()
    try:
        page.wait_for_selector('[data-testid="campaign-approval-error"]', timeout=5000)
        err = page.locator('[data-testid="campaign-approval-error"]').inner_text()
        raise AssertionError(f"Reject failed: {err}")
    except Exception as e:
        if "Reject failed" in str(e):
            raise
    page.wait_for_load_state("networkidle")

    # ── Verify ──
    status_badge = page.locator('[data-testid="campaign-status-badge"]')
    expect(status_badge).to_be_visible(timeout=10000)
    expect(status_badge).to_contain_text("Отклонена", timeout=5000)
    print(f"[{time.time()-t0:.1f}s] Rejected ✓")

    # Verify rejection reason is displayed
    reason_display = page.locator('[data-testid="campaign-rejection-reason-display"]')
    expect(reason_display).to_be_visible(timeout=5000)
    assert reason in reason_display.inner_text()
    print(f"[{time.time()-t0:.1f}s] Reason visible ✓")

    # ── Reload persistence ──
    page.reload()
    page.wait_for_load_state("networkidle")
    status_badge = page.locator('[data-testid="campaign-status-badge"]')
    assert "Отклонена" == status_badge.inner_text()
    print(f"[{time.time()-t0:.1f}s] Reload ✓ — DONE")
