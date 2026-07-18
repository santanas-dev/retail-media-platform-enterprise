"""
G2-FIX-FU2 — user.assign_roles HONEST smoke test.

Proves that a system_admin can assign a specific role to a user through the UI:
  login → Пользователи → click «Роли» → select "operator" role → save → verify.

This test is DETERMINISTIC:
- Selects a specific role by its code ("operator").
- Asserts the exact role_code appears in the current roles after save.
- No lambda, no random index, no API calls, no localStorage.
- Only /login via page.goto() (in conftest fixture); all navigation via clicks.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__user__assign_roles.py -v
"""

import pytest
from conftest import login_as_break_glass_admin

# The role we assign — must exist in seed (operator role, code="operator")
TARGET_ROLE_CODE = "operator"
TARGET_ROLE_NAME = "Оператор"


def navigate_to_users(page):
    """Click «Пользователи» in sidebar."""
    users_link = page.locator('aside nav a[href="/users"]')
    users_link.click(force=True)
    page.wait_for_url("**/users", timeout=5000)
    page.wait_for_load_state("networkidle")


def test_uismoke__user__assign_roles(smoke_page):
    """System admin assigns the 'operator' role to the operator user.

    Deterministic flow:
    1. Login as break_glass_admin
    2. Navigate to «Пользователи»
    3. Click «Роли» on the operator user
    4. Select "operator" role from dropdown by VALUE (role code)
    5. Save
    6. Verify the operator role_code appears in the current roles list
    """
    page = smoke_page

    # Step 1: login (only page.goto(/login) is in conftest fixture)
    login_as_break_glass_admin(page)

    # Step 2: navigate to «Пользователи»
    navigate_to_users(page)

    # Step 3: wait for user table, click «Роли» on the operator user
    page.wait_for_selector('[data-testid="user-roles-open"]', state="visible", timeout=10000)

    # Find which row has "operator" username and click its «Роли» button
    rows = page.locator("table tbody tr")
    row_count = rows.count()
    assert row_count >= 2, f"Expected at least 2 users, got {row_count}"

    target_row_idx = -1
    for i in range(row_count):
        row_text = rows.nth(i).inner_text()
        if "operator" in row_text.lower():
            target_row_idx = i
            break

    assert target_row_idx >= 0, "Could not find 'operator' user in the table"

    # Click «Роли» on the operator user's row
    roles_btn = rows.nth(target_row_idx).locator('[data-testid="user-roles-open"]')
    roles_btn.click()

    # Step 4: wait for role management panel
    page.wait_for_selector('[data-testid="user-roles-panel"]', state="visible", timeout=5000)

    # Step 5: select "operator" role from dropdown by its value (role_code)
    role_dropdown = page.locator('[data-testid="user-roles-role"]')
    role_dropdown.wait_for(state="visible", timeout=5000)

    # Read all option values to verify TARGET_ROLE_CODE exists
    options = role_dropdown.locator("option")
    option_values = []
    for i in range(options.count()):
        val = options.nth(i).get_attribute("value")
        if val:
            option_values.append(val)

    assert TARGET_ROLE_CODE in option_values, (
        f"Role '{TARGET_ROLE_CODE}' not found in dropdown. Available: {option_values}"
    )

    # Select by value (role_code)
    role_dropdown.select_option(value=TARGET_ROLE_CODE)

    # Step 6: click save
    save_btn = page.locator('[data-testid="user-roles-save"]')
    assert save_btn.is_enabled(), "Save button should be enabled after selecting a role"
    save_btn.click()

    # Step 7: wait for detail to reload — verify the assigned role appears
    page.wait_for_timeout(800)

    # Verify the panel is still visible
    panel = page.locator('[data-testid="user-roles-panel"]')
    assert panel.is_visible(), "Role panel should remain visible after saving"

    # Verify the TARGET_ROLE_CODE appears in the current roles list
    role_items = panel.locator("ul li")
    role_count = role_items.count()
    assert role_count >= 1, f"Expected at least 1 role, got {role_count}"

    found = False
    for i in range(role_count):
        item_text = role_items.nth(i).inner_text()
        if TARGET_ROLE_CODE in item_text:
            found = True
            break

    assert found, (
        f"Role '{TARGET_ROLE_CODE}' ({TARGET_ROLE_NAME}) not found "
        f"in current roles after assignment"
    )
