"""
UI-smoke: campaign.reject — reject a pending campaign with reason.
Pattern: create draft → creative upload → flights → placements → moderate → submit → reject → verify reason.
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

    # ── Creative ──
    creative_code = f"RJ-CR-{os.urandom(2).hex()}"
    page.click('[data-testid="tab-creatives"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="creative-add-library-btn"]')
    page.fill('[data-testid="creative-code"]', creative_code)
    page.fill('[data-testid="creative-name"]', "Reject CR")
    page.click('[data-testid="creative-add-submit"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="creative-attach-btn"]')
    opt = page.locator('[data-testid="creative-attach-select"] option').filter(has_text=creative_code)
    page.locator('[data-testid="creative-attach-select"]').select_option(value=opt.get_attribute("value"))
    page.click('[data-testid="creative-attach-submit"]')
    page.wait_for_load_state("networkidle")
    page.locator('[data-testid="creative-file-input"]').set_input_files(FIXTURE)
    expect(page.locator('[data-testid="creative-upload-done"]')).to_be_visible(timeout=20000)
    print(f"[{time.time()-t0:.1f}s] Creative uploaded")

    # ── Flights ──
    page.click('[data-testid="tab-flights"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="flight-add-btn"]')
    page.fill('[data-testid="flight-start"]', "2026-12-01")
    page.fill('[data-testid="flight-end"]', "2026-12-31")
    page.click('[data-testid="flight-submit"]')
    page.wait_for_load_state("networkidle")

    # ── Placements ──
    page.click('[data-testid="tab-placements"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="placement-add-btn"]')
    page.locator('[data-testid="placement-surface"]').select_option(index=1)
    page.click('[data-testid="placement-submit"]')
    page.wait_for_load_state("networkidle")

    # ── Moderate approve creative ──
    page.locator('aside nav a[href="/creatives/moderation"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.wait_for_selector('[data-testid^="moderation-row-"]', timeout=15000)
    row = page.locator(f'[data-testid="moderation-row-{creative_code}"]')
    expect(row).to_be_visible(timeout=5000)
    page.locator(f'[data-testid="moderation-approve-{creative_code}"]').click()
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Creative approved")

    # ── Go back + submit ──
    page.go_back()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)
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
    badge_text = status_badge.inner_text()
    assert "Отклонена" == badge_text, f"Expected Отклонена, got: {badge_text}"
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
