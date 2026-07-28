"""
UI-smoke: user.reset_password — admin resets a local user's password.
Pattern: find or create throwaway user → reset password → verify OTP.
Does NOT mutate shared seed credentials (break_glass_admin, advertiser_test).
"""
import os, pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import BASE_URL


def test_uismoke__user__reset_password(smoke_page: Page) -> None:
    page = smoke_page
    import time, uuid; t0 = time.time()

    # ── Login as break_glass_admin ──
    page.select_option("#login-provider", "local_break_glass")
    page.fill("#login-username", "break_glass_admin")
    page.fill("#login-password", "break-glass-dev-only")
    page.click('button[type="submit"]')
    page.wait_for_url("**/campaigns", timeout=15000)
    page.wait_for_load_state("networkidle")
    print(f"[{time.time()-t0:.1f}s] Logged in")

    # ── Navigate to Users ──
    page.locator('aside nav a[href="/users"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1000)

    # ── Find an existing smoke-reset user or create one ──
    existing = page.locator("tr", has=page.locator("text=smoke-reset-"))
    count = existing.count()
    if count > 0:
        target_row = existing.first
        # Extract username from the row
        row_text = target_row.inner_text()
        lines = row_text.split("\n")
        for line in lines:
            if line.strip().startswith("smoke-reset-"):
                smoke_username = line.strip().split()[0]
                break
        else:
            smoke_username = "smoke-reset-existing"
        print(f"[{time.time()-t0:.1f}s] Found existing: {smoke_username}")
    else:
        # Create new throwaway user
        unique_id = str(uuid.uuid4())[:8]
        smoke_username = f"smoke-reset-{unique_id}"
        create_btn = page.locator('[data-testid="user-create-advertiser-open"]')
        expect(create_btn).to_be_visible(timeout=5000)
        create_btn.click()

        page.locator('[data-testid="user-create-advertiser-username"]').fill(smoke_username)
        page.locator('[data-testid="user-create-advertiser-display-name"]').fill("Smoke Reset Test")
        page.locator('[data-testid="user-create-advertiser-org-id"]').fill("00000000-0000-0000-0000-000000000200")
        page.locator('[data-testid="user-create-advertiser-submit"]').click()
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1000)

        # Verify creation didn't error out
        result = page.locator('[data-testid="user-create-advertiser-result"]')
        result_text = result.inner_text() if result.count() > 0 else ""
        assert "500" not in result_text, f"Create failed: {result_text}"
        print(f"[{time.time()-t0:.1f}s] Created: {smoke_username}")

        # Navigate away and back to refresh the list
        page.locator('aside nav a[href="/campaigns"]').click(force=True)
        page.wait_for_load_state("networkidle")
        page.locator('aside nav a[href="/users"]').click(force=True)
        page.wait_for_load_state("networkidle")
        target_row = page.locator("tr", has=page.locator(f"text={smoke_username}"))
        expect(target_row).to_be_visible(timeout=10000)

    # ── Find reset button in the target row ──
    reset_btn = target_row.locator('[data-testid^="user-reset-password-open-"]')
    expect(reset_btn).to_be_visible(timeout=5000)
    target_testid = reset_btn.get_attribute("data-testid") or ""
    print(f"[{time.time()-t0:.1f}s] Reset button: {target_testid}")

    # ── OTP capture ──
    captured_otp = []

    def capture_response(response):
        if "/reset-password" in response.url and response.status == 200:
            try:
                body = response.json()
                otp = body.get("one_time_password")
                if otp:
                    captured_otp.append(otp)
                    print(f"[{time.time()-t0:.1f}s] OTP: {otp}")
            except Exception:
                pass

    page.on("response", capture_response)

    # ── Reset ──
    reset_btn.click()
    confirm_btn = page.locator('[data-testid="user-reset-password-confirm"]')
    expect(confirm_btn).to_be_visible(timeout=5000)
    confirm_btn.click()
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(500)

    # ── Verify OTP ──
    assert len(captured_otp) > 0, "No OTP captured from reset-password response"
    otp = captured_otp[0]
    assert len(otp) >= 8, f"OTP too short: {otp}"
    assert "[object Object]" not in otp
    print(f"[{time.time()-t0:.1f}s] OTP: {otp[:4]}... ({len(otp)} chars) ✓")

    # ── Persistence: users page still loads ──
    page.locator('aside nav a[href="/campaigns"]').click(force=True)
    page.wait_for_load_state("networkidle")
    page.locator('aside nav a[href="/users"]').click(force=True)
    page.wait_for_load_state("networkidle")
    expect(page.locator("table")).to_be_visible(timeout=10000)
    print(f"[{time.time()-t0:.1f}s] Users persists ✓ — DONE")
