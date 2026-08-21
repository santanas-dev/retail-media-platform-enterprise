"""
UI-smoke: campaign.activate — activate an approved campaign.
Pattern: full pipeline → primary creative upload → submit → approve → activate → verify.
Uses CREATIVE_AUTO_APPROVE_UPLOADS (CI default) — skips moderation.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL, login_as_break_glass_admin

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test-creative.png")


def test_uismoke__campaign__activate(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login ──
    login_as_break_glass_admin(page)

    # ── Create campaign ──
    page.click('[data-testid="campaign-create-open"]')
    page.wait_for_url("**/campaigns/new", timeout=10000)
    page.select_option("#c-org", index=1)
    page.select_option("#c-contract", index=1)
    campaign_code = f"SMOKE-ACT-{os.urandom(2).hex()}"
    page.fill("#c-code", campaign_code)
    page.fill("#c-name", f"Activate {campaign_code}")
    page.fill("#c-budget", "100000")
    page.click('button:has-text("Создать черновик")')
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── Navigate to content tab ──
    page.click('[data-testid="tab-content"]')
    page.wait_for_load_state("networkidle")

    # ── Primary creative upload ──
    creative_code = f"ACT-CR-{os.urandom(2).hex()}"
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
    page.fill('[data-testid="flight-start"]', "2027-06-01")
    page.fill('[data-testid="flight-end"]', "2027-06-30")
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

    # ── Back to overview (creative auto-approved via CREATIVE_AUTO_APPROVE_UPLOADS) ──
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

    # ── Approve ──
    approve_btn = page.locator('[data-testid="campaign-approve-btn"]')
    expect(approve_btn).to_be_visible(timeout=5000)
    approve_btn.click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="campaign-status-badge"]')).to_contain_text("Согласована", timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Approved")

    # ── Activate ──
    activate_btn = page.locator('[data-testid="campaign-activate-btn"]')
    expect(activate_btn).to_be_visible(timeout=5000)
    activate_btn.click()
    try:
        page.wait_for_selector('[data-testid="campaign-lifecycle-error"]', timeout=5000)
        err = page.locator('[data-testid="campaign-lifecycle-error"]').inner_text()
        raise AssertionError(f"Activate failed: {err}")
    except Exception as e:
        if "Activate failed" in str(e):
            raise
    expect(activate_btn).not_to_be_visible(timeout=10000)

    # ── Verify status "Активна" ──
    badge = page.locator('[data-testid="campaign-status-badge"]')
    expect(badge).to_contain_text("Активна", timeout=10000)

    # ── Reload: status persists ──
    page.reload()
    page.wait_for_load_state("networkidle")
    badge2 = page.locator('[data-testid="campaign-status-badge"]')
    expect(badge2).to_contain_text("Активна", timeout=10000)

    print(f"[{time.time()-t0:.1f}s] DONE — campaign.activate reachable")
