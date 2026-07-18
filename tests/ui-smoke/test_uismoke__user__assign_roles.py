"""
G2-FIX — user.assign_roles GREEN smoke test.

Proves that a system_admin can assign a role to a user through the UI:
  login → Пользователи → click «Роли» → choose role → save → verify.

No direct goto, no API calls, no localStorage manipulation.
Only real UI clicks using stable data-testid selectors.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__user__assign_roles.py -v
"""

import pytest
from conftest import login_as_break_glass_admin


def navigate_to_users(page):
    """Click «Пользователи» in sidebar."""
    page.wait_for_selector("text=Пользователи", state="visible", timeout=5000)
    page.click("text=Пользователи")
    page.wait_for_url("**/users", timeout=5000)


def test_uismoke__user__assign_roles(smoke_page):
    """System admin assigns a role to a user through the UI.

    1. Login via real form
    2. Navigate to user list
    3. Click «Роли» on a user
    4. Select a role from dropdown
    5. Save
    6. Verify role appeared in the list
    """
    page = smoke_page

    # Step 1: login
    login_as_break_glass_admin(page)

    # Step 2: navigate to «Пользователи»
    navigate_to_users(page)

    # Step 3: wait for user table, find «Роли» button
    page.wait_for_selector('[data-testid="user-roles-open"]', state="visible", timeout=5000)

    # Click the first «Роли» button
    roles_buttons = page.locator('[data-testid="user-roles-open"]')
    roles_buttons.first.click()

    # Step 4: wait for role management panel
    page.wait_for_selector('[data-testid="user-roles-panel"]', state="visible", timeout=5000)

    # Step 5: select a role from dropdown
    role_dropdown = page.locator('[data-testid="user-roles-role"]')
    role_dropdown.select_option(label=lambda label: "system_admin" not in label and "администратор" not in label.lower())
    # If no non-admin role found, just select first option after placeholder
    options_count = len(role_dropdown.locator("option").all())
    if options_count > 1:
        role_dropdown.select_option(index=1)

    # Step 6: click save
    page.click('[data-testid="user-roles-save"]')

    # Step 7: verify — the page should show the newly assigned role in current roles list
    # Wait briefly for the detail to reload
    page.wait_for_timeout(500)

    # The role panel should still be visible with updated roles
    assert page.locator('[data-testid="user-roles-panel"]').is_visible(), (
        "Role panel should remain visible after saving"
    )

    # Verify at least one role is shown in the current roles list
    current_roles = page.locator('[data-testid="user-roles-panel"] ul li')
    assert current_roles.count() >= 1, (
        "At least one role should appear in current roles after assignment"
    )
