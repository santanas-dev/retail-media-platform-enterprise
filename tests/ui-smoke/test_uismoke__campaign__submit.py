"""
UI-smoke: campaign.submit — creatives tab FIRST (upload works on fresh tab).
Then flights → placements → moderation → submit.
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "test-creative.png")


def test_uismoke__campaign__submit(smoke_page: Page) -> None:
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
    campaign_code = f"SMOKE-SUB-{os.urandom(2).hex()}"
    page.fill("#c-code", campaign_code)
    page.fill("#c-name", f"Submit {campaign_code}")
    page.fill("#c-budget", "100000")
    page.click('button:has-text("Создать черновик")')
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    # ── STEP 1: Creatives tab FIRST (BEFORE flights/placements) ──
    creative_code = f"SUB-CR-{os.urandom(2).hex()}"
    page.click('[data-testid="tab-creatives"]')
    page.wait_for_load_state("networkidle")

    # Create in library
    page.click('[data-testid="creative-add-library-btn"]')
    page.fill('[data-testid="creative-code"]', creative_code)
    page.fill('[data-testid="creative-name"]', "Submit CR")
    page.click('[data-testid="creative-add-submit"]')
    page.wait_for_load_state("networkidle")

    # Attach
    page.click('[data-testid="creative-attach-btn"]')
    opt = page.locator('[data-testid="creative-attach-select"] option').filter(has_text=creative_code)
    page.locator('[data-testid="creative-attach-select"]').select_option(value=opt.get_attribute("value"))
    page.click('[data-testid="creative-attach-submit"]')
    page.wait_for_load_state("networkidle")

    # Upload — WORKS when the tab was never navigated away from
    page.locator('[data-testid="creative-file-input"]').set_input_files(FIXTURE)
    expect(page.locator('[data-testid="creative-upload-done"]')).to_be_visible(timeout=20000)
    print(f"[{time.time()-t0:.1f}s] Creative uploaded")

    # ── STEP 2: Flights ──
    page.click('[data-testid="tab-flights"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="flight-add-btn"]')
    page.fill('[data-testid="flight-start"]', "2026-08-01")
    page.fill('[data-testid="flight-end"]', "2026-08-31")
    page.click('[data-testid="flight-submit"]')
    page.wait_for_load_state("networkidle")

    # ── STEP 3: Placements ──
    page.click('[data-testid="tab-placements"]')
    page.wait_for_load_state("networkidle")
    page.click('[data-testid="placement-add-btn"]')
    page.locator('[data-testid="placement-surface"]').select_option(index=1)
    page.click('[data-testid="placement-submit"]')
    page.wait_for_load_state("networkidle")

    # ── STEP 4: Submit (CREATIVE_AUTO_APPROVE_UPLOADS=true — creative already approved) ──
    # Submit button is on the Overview tab
    page.click('button:has-text("Обзор")')
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Submitting...")

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
    print(f"[{time.time()-t0:.1f}s] Submit done")

    # ── Verify ──
    status_badge = page.locator('[data-testid="campaign-status-badge"]')
    expect(status_badge).to_be_visible(timeout=10000)
    assert "На согласовании" in status_badge.inner_text()
    print(f"[{time.time()-t0:.1f}s] Status ✓")

    page.reload()
    page.wait_for_load_state("networkidle")
    assert "На согласовании" in page.locator('[data-testid="campaign-status-badge"]').inner_text()
    print(f"[{time.time()-t0:.1f}s] Reload ✓ — DONE")
