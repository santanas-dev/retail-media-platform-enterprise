"""
UI-smoke: user.deactivate — admin deactivates a throwaway user and verifies blocked login.
Pattern: create throwaway → deactivate → verify blocked login.
Does NOT mutate shared seed credentials (break_glass_admin, advertiser_test).
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL, login_as_break_glass_admin


def test_uismoke__user__deactivate(smoke_page: Page) -> None:
    page = smoke_page
    import time, uuid; t0 = time.time()

    # ── Login as break_glass_admin ──
    login_as_break_glass_admin(page)
    print(f"[{time.time()-t0:.1f}s] Logged in")

    # ── Navigate to Users ──
    page.locator('aside nav a[href="/users"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # ── Create throwaway user ──
    unique_id = str(uuid.uuid4())[:8]
    smoke_username = f"smoke_deact_{unique_id}"  # matches the smoke% cleanup marker
    create_btn = page.locator('[data-testid="user-create-advertiser-open"]')
    expect(create_btn).to_be_visible(timeout=5000)
    create_btn.click()

    page.locator('[data-testid="user-create-advertiser-username"]').fill(smoke_username)
    page.locator('[data-testid="user-create-advertiser-display-name"]').fill("Smoke Deact Test")
    page.locator('[data-testid="user-create-advertiser-org-id"]').fill("00000000-0000-0000-0000-000000000200")
    page.locator('[data-testid="user-create-advertiser-submit"]').click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify creation and extract OTP from DOM
    result = page.locator('[data-testid="user-create-advertiser-result"]')
    result_text = result.inner_text() if result.count() > 0 else ""
    print(f"[{time.time()-t0:.1f}s] Create result: {result_text[:200]}")
    assert "500" not in result_text, f"Create failed: {result_text}"

    # Extract OTP from the result text (format: "Одноразовый пароль ...\n<otp>\n...")
    otp = None
    lines = result_text.split("\n")
    for line in lines:
        line = line.strip()
        # OTP is 12+ chars on its own line, with no spaces
        if len(line) >= 8 and " " not in line and "⚠" not in line and "пароль" not in line.lower():
            otp = line
            break
    assert otp is not None, f"Could not extract OTP from: {result_text[:200]}"
    print(f"[{time.time()-t0:.1f}s] Created: {smoke_username}, OTP: {otp[:4]}..." if len(otp) > 4 else f"OTP found")

    # ── Navigate away and back to refresh the list ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/users"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # ── Find the throwaway user row ──
    target_row = page.locator("tr", has=page.locator(f"text={smoke_username}"))
    expect(target_row).to_be_visible(timeout=10000)

    # Verify initial status is "Активен"
    status_cell = target_row.locator('[data-testid^="user-status-"]')
    assert "Активен" in status_cell.inner_text(), f"Expected Активен, got: {status_cell.inner_text()}"
    print(f"[{time.time()-t0:.1f}s] Found row, status: Активен")

    # ── Deactivate ──
    deact_btn = target_row.locator('[data-testid^="user-deactivate-open-"]')
    expect(deact_btn).to_be_visible(timeout=5000)
    deact_btn.click()
    page.wait_for_timeout(500)

    # Confirm deactivation
    confirm_btn = page.locator('[data-testid="user-deactivate-confirm"]')
    expect(confirm_btn).to_be_visible(timeout=5000)
    confirm_btn.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # Verify success
    success = page.locator('[data-testid="user-deactivate-success"]')
    expect(success).to_be_visible(timeout=5000)
    success_text = success.inner_text()
    assert "deactivated" in success_text.lower() or "деактив" in success_text.lower() or "revoked" in success_text.lower(), \
        f"Success message unexpected: {success_text}"
    assert "[object Object]" not in success_text
    print(f"[{time.time()-t0:.1f}s] Deactivate success: {success_text[:80]}")

    # ── Verify status changed to Неактивен ──
    status_cell = target_row.locator('[data-testid^="user-status-"]')
    assert "Неактивен" in status_cell.inner_text(), f"Expected Неактивен, got: {status_cell.inner_text()}"
    print(f"[{time.time()-t0:.1f}s] Status: Неактивен ✓")

    # ── Persistence: reload page, verify still inactive ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/users"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    target_row = page.locator("tr", has=page.locator(f"text={smoke_username}"))
    expect(target_row).to_be_visible(timeout=10000)
    status_cell = target_row.locator('[data-testid^="user-status-"]')
    assert "Неактивен" in status_cell.inner_text(), f"After reload, expected Неактивен, got: {status_cell.inner_text()}"
    print(f"[{time.time()-t0:.1f}s] Reload persistence: Неактивен ✓")

    # ── Verify blocked login ──
    # Logout first
    page.locator("button", has=page.locator("text=Выход")).click(force=True)
    page.wait_for_url("**/login", timeout=10000)
    page.wait_for_load_state("networkidle")

    # Attempt login as deactivated user
    page.select_option("#login-provider", "local_advertiser")
    page.fill("#login-username", smoke_username)
    page.fill("#login-password", otp)
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)

    # Should see error or stay on login page (not redirected to campaigns)
    current_url = page.url
    assert "/campaigns" not in current_url, \
        f"Deactivated user was allowed to login! URL: {current_url}"
    # Verify error is visible
    error_on_page = page.locator('[class*="error"], [class*="Error"], .text-red-500, .text-red-600').count() > 0 or \
        "ошибка" in page.inner_text("body").lower() or \
        "неверн" in page.inner_text("body").lower() or \
        "invalid" in page.inner_text("body").lower() or \
        "inactive" in page.inner_text("body").lower() or \
        "деактив" in page.inner_text("body").lower()
    assert error_on_page, f"No error visible after deactivated user login attempt. URL: {current_url}"
    print(f"[{time.time()-t0:.1f}s] Blocked login: ✓ (stayed on login, error visible)")

    # ── Verify admin can still login (no global break) ──
    login_as_break_glass_admin(page)
    print(f"[{time.time()-t0:.1f}s] Admin login verified — DONE")
