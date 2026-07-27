"""
UI-smoke: adsettings.test — test AD connection from admin settings page.
Pattern: login → AD settings → click test → verify result.
In dev mode, AD is disabled → expect controlled failure "not_configured".
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL


def test_uismoke__adsettings__test(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login as break_glass_admin ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Logged in")

    # ── Navigate to AD Settings ──
    page.locator('aside nav a[href="/settings/ad"]').click(force=True)
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="adsettings-page"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] AD settings page visible")

    # ── Click test button ──
    test_btn = page.locator('[data-testid="adsettings-test-btn"]')
    expect(test_btn).to_be_visible(timeout=5000)
    test_btn.click()

    # ── Verify result appears ──
    # In dev mode with default disabled AD, expect "not_configured" → error testid
    result = page.locator('[data-testid="adsettings-test-error"]')
    expect(result).to_be_visible(timeout=15000)

    # Verify human-readable message, no [object Object]
    result_text = result.inner_text()
    assert "AD integration is not configured" in result_text or "Не настроено" in result_text, \
        f"Expected controlled failure message, got: {result_text}"
    assert "[object Object]" not in result_text, f"Result contains [object Object]: {result_text}"
    print(f"[{time.time()-t0:.1f}s] Test result visible: {result_text[:80]}...")

    # ── Verify no bind_password exposure ──
    page_text = result_text
    assert "bind_password" not in page_text.lower(), "bind_password leaked in test result"
    assert "AD_BIND_PASSWORD" not in page_text, "AD_BIND_PASSWORD leaked in test result"
    print(f"[{time.time()-t0:.1f}s] No secret exposure ✓")

    # ── Persistence: navigate away and back ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/settings/ad"]').click(force=True)
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="adsettings-page"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Page persists after re-navigation ✓ — DONE")
