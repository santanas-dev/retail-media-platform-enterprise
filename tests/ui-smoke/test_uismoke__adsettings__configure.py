"""
G4-FIX — adsettings.configure HONEST smoke test.

Proves that a system_admin can save AD settings through the UI:
  login → Настройки AD → fill form → Сохранить → success → reload → verify.

DETERMINISTIC:
- Fills all editable fields with test values.
- Asserts success message appears after save.
- Reloads page and verifies values persisted.
- Only /login via page.goto() (in conftest fixture); all navigation via clicks.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__adsettings__configure.py -v
"""

import pytest
from conftest import login_as_break_glass_admin


def navigate_to_ad_settings(page):
    """Click «Настройки AD» in sidebar."""
    link = page.locator('aside nav a[href="/ad-settings"]')
    link.click(force=True)
    page.wait_for_url("**/ad-settings", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__adsettings__configure(smoke_page):
    """System admin saves AD settings and verifies persistence.

    Deterministic flow:
    1. Login as break_glass_admin
    2. Navigate to «Настройки AD»
    3. Fill in test values for server_url, base_dn, bind_dn
    4. Uncheck TLS, set cert validation to "optional"
    5. Click «Сохранить»
    6. Verify success message
    7. Reload page
    8. Verify saved values are still present
    """
    page = smoke_page

    # Step 1: login
    login_as_break_glass_admin(page)

    # Step 2: navigate to «Настройки AD»
    navigate_to_ad_settings(page)

    # Step 3: fill form fields
    server_input = page.locator('[data-testid="adsettings-field-server-url"]')
    server_input.fill("ldaps://ad-smoke.test.local")

    base_dn_input = page.locator('[data-testid="adsettings-field-base-dn"]')
    base_dn_input.fill("dc=smoke,dc=test,dc=local")

    bind_dn_input = page.locator('[data-testid="adsettings-field-bind-dn"]')
    bind_dn_input.fill("cn=smokebind,dc=smoke,dc=test,dc=local")

    # Step 4: uncheck TLS, set cert validation to optional
    tls_checkbox = page.locator('[data-testid="adsettings-field-use-tls"]')
    if tls_checkbox.is_checked():
        tls_checkbox.uncheck()

    cert_select = page.locator('[data-testid="adsettings-field-cert-validation"]')
    cert_select.select_option("optional")

    # Step 5: save
    save_btn = page.locator('[data-testid="adsettings-save-btn"]')
    save_btn.click()

    # Step 6: success message
    success = page.locator('[data-testid="adsettings-save-success"]')
    success.wait_for(state="visible", timeout=5000)
    assert success.is_visible(), "Success banner not visible after save"

    # Step 7: reload page and verify persistence
    page.reload()
    page.wait_for_load_state("networkidle")

    # Step 8: verify saved values
    # Check details card shows saved server_url
    detail_server = page.locator('[data-testid="adsettings-detail-server-url"]')
    detail_server.wait_for(state="visible", timeout=5000)
    assert "ldaps://ad-smoke.test.local" in detail_server.text_content(), \
        f"Expected server URL in details, got: {detail_server.text_content()}"

    # Check TLS detail shows off
    detail_tls = page.locator('[data-testid="adsettings-detail-tls"]')
    assert "Выключен" in detail_tls.text_content(), \
        f"Expected TLS off, got: {detail_tls.text_content()}"

    # Check cert validation detail
    detail_cert = page.locator('[data-testid="adsettings-detail-cert"]')
    assert "Опциональна" in detail_cert.text_content(), \
        f"Expected cert optional, got: {detail_cert.text_content()}"
