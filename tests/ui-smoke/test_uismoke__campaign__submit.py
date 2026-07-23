"""
UI-smoke: campaign.submit — CAMPAIGN-UX-001B readiness checklist progression.
Happy-path: Overview checklist → missing steps → flight → placement → creative ready → submit.
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

    # ── CAMPAIGN-UX-001B: Step 0 — Verify checklist on Overview ──
    checklist = page.locator('[data-testid="campaign-readiness-checklist"]')
    expect(checklist).to_be_visible(timeout=5000)
    # All three items should show missing
    assert page.locator('[data-testid="readiness-flight-status"]').inner_text() == "—"
    assert page.locator('[data-testid="readiness-placement-status"]').inner_text() == "—"
    assert page.locator('[data-testid="readiness-creative-status"]').inner_text() == "—"
    # Submit status shows what's missing
    submit_status = page.locator('[data-testid="readiness-submit-status"]').inner_text()
    assert "Осталось" in submit_status
    assert "рейс" in submit_status
    print(f"[{time.time()-t0:.1f}s] Checklist missing ✓")

    # ── Use checklist action: flight ──
    page.locator('[data-testid="readiness-flight-action"]').click()
    page.wait_for_load_state("networkidle")
    # Should now be on flights tab
    expect(page.locator('[data-testid="flight-add-btn"]')).to_be_visible(timeout=5000)
    page.click('[data-testid="flight-add-btn"]')
    page.fill('[data-testid="flight-start"]', "2026-08-01")
    page.fill('[data-testid="flight-end"]', "2026-08-31")
    page.click('[data-testid="flight-submit"]')
    page.wait_for_load_state("networkidle")

    # Return to Overview
    page.click('button:has-text("Обзор")')
    page.wait_for_load_state("networkidle")
    assert page.locator('[data-testid="readiness-flight-status"]').inner_text() == "✅"
    print(f"[{time.time()-t0:.1f}s] Flight ✓")

    # ── Use checklist action: placement ──
    page.locator('[data-testid="readiness-placement-action"]').click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="placement-add-btn"]')).to_be_visible(timeout=5000)
    page.click('[data-testid="placement-add-btn"]')
    page.locator('[data-testid="placement-surface"]').select_option(index=1)
    page.click('[data-testid="placement-submit"]')
    page.wait_for_load_state("networkidle")

    page.click('button:has-text("Обзор")')
    page.wait_for_load_state("networkidle")
    assert page.locator('[data-testid="readiness-placement-status"]').inner_text() == "✅"
    print(f"[{time.time()-t0:.1f}s] Placement ✓")

    # ── Use checklist action: creative ──
    creative_code = f"SUB-CR-{os.urandom(2).hex()}"
    page.locator('[data-testid="readiness-creative-action"]').click()
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="tab-creatives"]')).to_be_visible(timeout=5000)

    # Use primary upload path
    page.locator('[data-testid="creative-upload-select-file"]').click()
    page.locator('[data-testid="creative-upload-primary-file-input"]').set_input_files(FIXTURE)
    expect(page.locator('[data-testid="creative-upload-primary-code"]')).to_be_visible(timeout=5000)
    page.locator('[data-testid="creative-upload-primary-code"]').fill("")
    page.locator('[data-testid="creative-upload-primary-code"]').fill(creative_code)
    page.locator('[data-testid="creative-upload-metadata-submit"]').click()
    expect(page.locator('[data-testid="creative-upload-done"]')).to_be_visible(timeout=30000)

    # Return to Overview
    page.click('button:has-text("Обзор")')
    page.wait_for_load_state("networkidle")
    assert page.locator('[data-testid="readiness-creative-status"]').inner_text() == "✅"
    print(f"[{time.time()-t0:.1f}s] Creative ✓")

    # ── All three ready → submit possible ──
    submit_status = page.locator('[data-testid="readiness-submit-status"]').inner_text()
    assert "Можно отправить" in submit_status
    print(f"[{time.time()-t0:.1f}s] Ready to submit ✓")

    # ── Submit — button enabled ──
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
