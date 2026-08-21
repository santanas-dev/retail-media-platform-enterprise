"""
UI-TRUTH-001A / G1-FIX — campaign.create GREEN smoke test.

Proves that a real user can create a campaign through the UI:
  login → sidebar → click «Создать кампанию» → select org → fill form → submit → verify.

No direct goto, no API calls, no localStorage manipulation.
Only real UI clicks using stable data-testid selectors.

Run with:  UI_SMOKE_RUN=1 pytest tests/ui-smoke/test_uismoke__campaign__create.py -v
"""

import pytest
from conftest import (
    login_as_break_glass_admin,
    navigate_to_campaigns,
    click_create_campaign_button,
    select_first_org,
    choose_first_contract,
    fill_campaign_code_and_name,
    submit_campaign_form,
    verify_campaign_created,
    unique_suffix,
)


def test_uismoke__campaign__create(smoke_page):
    """Break-glass admin creates a campaign through the UI.

    1. Login via real form
    2. Navigate to campaign list
    3. Click «Создать кампанию» button
    4. Select advertiser org (reveals contract field)
    5. Choose first contract
    6. Fill code + name + placement basis
    7. Submit
    8. Verify redirect to campaign detail page
    """
    page = smoke_page

    # Step 1: login
    login_as_break_glass_admin(page)

    # Step 2: click «Кампании» in sidebar (already on /campaigns after login)
    navigate_to_campaigns(page)

    # Step 3: click «Создать кампанию» (data-testid="campaign-create-open")
    click_create_campaign_button(page)

    # Step 4: select first advertiser org (makes contract select visible)
    select_first_org(page)

    # Step 5: choose first contract
    choose_first_contract(page)

    # Step 6: fill code + name (required fields) — unique code per run so a
    # re-run against a long-lived DB never collides on the campaign code.
    fill_campaign_code_and_name(page, f"SMOKE-{unique_suffix()}", "Smoke Test Campaign")

    # Step 7: select placement basis (default "commercial" is fine)
    page.select_option("#c-placement-basis", "commercial")

    # Step 8: submit
    submit_campaign_form(page)

    # Step 9: verify we're on the campaign detail page
    verify_campaign_created(page)
