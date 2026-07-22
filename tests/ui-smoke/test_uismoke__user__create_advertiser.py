"""
JOURNEY-005 — user.create_advertiser HONEST smoke test.

Proves that a system_admin can create a local advertiser user through the UI:
  login → Пользователи → «+ Создать рекламодателя» → fill form → submit → see result.

This test is DETERMINISTIC:
- Uses seed advertiser organization (Рекламный Альянс, 00000000-0000-4000-a000-000000000002).
- Fills username/display_name fields, uses auto-generate password.
- Verifies success result block appears (auto-generated password).
- No API calls, no localStorage, no deep links.
- Only /login via page.goto() (in conftest fixture); all navigation via clicks.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__user__create_advertiser.py -v
"""

import secrets

from conftest import login_as_break_glass_admin

# Seed advertiser organization — must exist in seed (Рекламный Альянс)
TARGET_ORG_ID = "00000000-0000-4000-a000-000000000002"

# Dynamic username to avoid uniqueness conflicts across runs
SMOKE_USERNAME = f"smoke_adv_{secrets.token_hex(4)}"
SMOKE_DISPLAY_NAME = "Smoke Test Advertiser"


def navigate_to_users(page):
    """Click «Пользователи» in sidebar."""
    users_link = page.locator('aside nav a[href="/users"]')
    users_link.click(force=True)
    page.wait_for_url("**/users", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__user__create_advertiser(smoke_page):
    """System admin creates a local advertiser user.

    Deterministic flow:
    1. Login as break_glass_admin
    2. Navigate to «Пользователи»
    3. Click «+ Создать рекламодателя»
    4. Fill form: username, display_name, org ID
    5. Submit (auto-generate password checked by default)
    6. Verify success result appears with one-time password
    """
    page = smoke_page

    # Step 1: login
    login_as_break_glass_admin(page)

    # Step 2: navigate to «Пользователи»
    navigate_to_users(page)

    # Step 3: click «+ Создать рекламодателя»
    create_btn = page.locator('[data-testid="user-create-advertiser-open"]')
    create_btn.wait_for(state="visible", timeout=5000)
    create_btn.click()

    # Step 4: fill the create form
    username_input = page.locator('[data-testid="user-create-advertiser-username"]')
    username_input.wait_for(state="visible", timeout=3000)
    username_input.fill(SMOKE_USERNAME)

    display_input = page.locator(
        '[data-testid="user-create-advertiser-display-name"]'
    )
    display_input.fill(SMOKE_DISPLAY_NAME)

    org_input = page.locator('[data-testid="user-create-advertiser-org-id"]')
    org_input.fill(TARGET_ORG_ID)

    # Step 5: submit
    submit_btn = page.locator('[data-testid="user-create-advertiser-submit"]')
    submit_btn.click()

    # Step 6: verify success result appears with one-time password
    result_block = page.locator('[data-testid="user-create-advertiser-result"]')
    result_block.wait_for(state="visible", timeout=10000)

    result_text = result_block.inner_text()
    assert "⚠️ Одноразовый пароль" in result_text, (
        f"Expected one-time password block, got: {result_text}"
    )

    # Verify the one-time password is present (16 chars of alphanumeric)
    code_locator = result_block.locator("code")
    assert code_locator.is_visible(), "One-time password code not visible"
    otp = code_locator.inner_text()
    assert len(otp) > 8, f"Password too short: {otp}"
