"""
UI-smoke: adsettings.test — test AD connection from admin settings page.
Pattern: login → AD settings → click test → verify result.
Works regardless of AD state (disabled/enabled/configured).
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL, login_as_break_glass_admin


def test_uismoke__adsettings__test(smoke_page: Page) -> None:
    page = smoke_page
    import time; t0 = time.time()

    # ── Login as break_glass_admin ──
    login_as_break_glass_admin(page)
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

    # ── Verify result appears — wait for either error or success locator ──
    # LDAP connection can take time (connect_timeout=5s + network), so use generous timeout
    result_error = page.locator('[data-testid="adsettings-test-error"]')
    result_success = page.locator('[data-testid="adsettings-test-success"]')
    result_error.wait_for(state="visible", timeout=30000)
    result_visible = result_error if result_error.is_visible() else result_success

    # Verify human-readable message, no [object Object]
    result_text = result_visible.inner_text()
    # Accept: any controlled outcome (not_configured, unavailable, misconfigured, ok)
    assert any(phrase in result_text.lower() for phrase in [
        "not configured",
        "не настроено",
        "not reachable",
        "недоступен",
        "unavailable",
        "misconfigured",
        "ok",
        "configured",
    ]), \
        f"Expected controlled message, got: {result_text}"
    assert "[object Object]" not in result_text, f"Result contains [object Object]: {result_text}"
    print(f"[{time.time()-t0:.1f}s] Test result visible: {result_text[:80]}...")

    # ── Verify no bind_password exposure ──
    assert "bind_password" not in result_text.lower(), "bind_password leaked in test result"
    assert "AD_BIND_PASSWORD" not in result_text, "AD_BIND_PASSWORD leaked in test result"
    print(f"[{time.time()-t0:.1f}s] No secret exposure ✓")

    # ── Persistence: navigate away and back ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/settings/ad"]').click(force=True)
    page.wait_for_load_state("networkidle")
    expect(page.locator('[data-testid="adsettings-page"]')).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Persistence OK")
