"""
UI-smoke: inventory.simulate — proves simulation result with specific fields.

Journey: inventory.simulate (managed-first)
Role: campaign_manager
Path: /login → campaign → flights → placement → creatives → overview → simulate → assert fields
"""
import os
import pathlib
import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from playwright.sync_api import Page, expect
from conftest import (
    BASE_URL,
    login_as_break_glass_admin,
    click_create_campaign_button,
    choose_first_contract,
)


def _create_draft_campaign(page: Page) -> str:
    """Create a draft campaign via UI and return its ID from the URL."""
    login_as_break_glass_admin(page)
    click_create_campaign_button(page)

    page.select_option("#c-org", index=1)
    choose_first_contract(page)

    page.fill("#c-code", f"SMOKE-SIM-{os.urandom(2).hex()}")
    page.fill("#c-name", "Smoke Sim Test")
    page.fill("#c-budget", "100000")

    page.click('button:has-text("Создать черновик")')
    page.wait_for_url(lambda url: url != BASE_URL + "/campaigns/new", timeout=15000)
    page.wait_for_load_state("networkidle")

    url = page.url
    return url.rstrip("/").split("/")[-1]


def _add_flight(page: Page, start: str, end: str) -> None:
    """Add a flight via the Flights tab (name/budget optional)."""
    tab = page.locator('[data-testid="tab-flights"]')
    expect(tab).to_be_visible(timeout=5000)
    tab.click()
    page.wait_for_load_state("networkidle")

    add_btn = page.locator('[data-testid="flight-add-btn"]')
    expect(add_btn).to_be_visible(timeout=3000)
    add_btn.click()

    page.fill('[data-testid="flight-start"]', start)
    page.fill('[data-testid="flight-end"]', end)
    page.click('[data-testid="flight-submit"]')
    page.wait_for_load_state("networkidle")


def _add_placement(page: Page) -> None:
    """Add a placement via the Placements tab — selects first surface."""
    tab = page.locator('[data-testid="tab-placements"]')
    expect(tab).to_be_visible(timeout=5000)
    tab.click()
    page.wait_for_load_state("networkidle")

    add_btn = page.locator('[data-testid="placement-add-btn"]')
    expect(add_btn).to_be_visible(timeout=3000)
    add_btn.click()

    # Select first surface option (skip placeholder)
    surface_select = page.locator('[data-testid="placement-surface"]')
    surface_select.select_option(index=1)

    page.click('[data-testid="placement-submit"]')
    page.wait_for_load_state("networkidle")


def _add_creative_to_library(page: Page, code: str) -> None:
    """Add a creative to the library and attach it to the campaign."""
    tab = page.locator('[data-testid="tab-creatives"]')
    expect(tab).to_be_visible(timeout=5000)
    tab.click()
    page.wait_for_load_state("networkidle")

    add_lib = page.locator('[data-testid="creative-add-library-btn"]')
    expect(add_lib).to_be_visible(timeout=3000)
    add_lib.click()

    page.fill('[data-testid="creative-code"]', code)
    page.fill('[data-testid="creative-name"]', "Sim Creative")
    page.click('[data-testid="creative-add-submit"]')
    page.wait_for_load_state("networkidle")

    attach_btn = page.locator('[data-testid="creative-attach-btn"]')
    expect(attach_btn).to_be_visible(timeout=3000)
    attach_btn.click()

    option_locator = page.locator(
        '[data-testid="creative-attach-select"] option'
    ).filter(has_text=code)
    expect(option_locator).to_have_count(1, timeout=5000)
    option_value = option_locator.get_attribute("value")
    page.locator('[data-testid="creative-attach-select"]').select_option(value=option_value)

    page.click('[data-testid="creative-attach-submit"]')
    page.wait_for_load_state("networkidle")


def test_uismoke__inventory__simulate(smoke_page: Page) -> None:
    """Run inventory simulation and verify specific result fields."""
    page = smoke_page
    _create_draft_campaign(page)

    creative_code = f"SIM-CR-{os.urandom(2).hex()}"

    # ── Add flight, placement, creative ──
    _add_flight(page, "2026-08-01", "2026-08-31")
    _add_placement(page)
    _add_creative_to_library(page, creative_code)

    # ── Navigate to Overview tab ──
    overview_tab = page.locator('[data-testid="tab-overview"]')
    expect(overview_tab).to_be_visible(timeout=5000)
    overview_tab.click()
    page.wait_for_load_state("networkidle")

    # ── Click "🧪 Симуляция" ──
    simulate_btn = page.locator('[data-testid="simulate-btn"]')
    expect(simulate_btn).to_be_visible(timeout=5000)
    simulate_btn.click()

    # ── Wait for results ──
    result_container = page.locator('[data-testid="simulation-result"]')
    expect(result_container).to_be_visible(timeout=15000)

    # ── Assert specific result fields ──
    verdict = page.locator('[data-testid="simulation-verdict"]')
    expect(verdict).to_be_visible()
    verdict_text = verdict.inner_text()
    assert "помещается" in verdict_text.lower() or "не помещается" in verdict_text.lower(), \
        f"Verdict missing expected text: {verdict_text}"

    blocking = page.locator('[data-testid="simulation-blocking-count"]')
    expect(blocking).to_be_visible()
    assert blocking.inner_text().isdigit(), f"blocking_count not a number: {blocking.inner_text()}"

    warning = page.locator('[data-testid="simulation-warning-count"]')
    expect(warning).to_be_visible()
    assert warning.inner_text().isdigit(), f"warning_count not a number: {warning.inner_text()}"

    # ── At least one placement row ──
    placement_0 = page.locator('[data-testid="simulation-placement-0"]')
    expect(placement_0).to_be_visible(timeout=5000)

    # slot_fill_percent
    fill = page.locator('[data-testid="simulation-slot-fill-0"]')
    expect(fill).to_be_visible()
    fill_text = fill.inner_text()
    assert fill_text.replace(".", "").replace("-", "").isdigit(), \
        f"slot_fill_percent not numeric: {fill_text}"

    # total_requested
    requested = page.locator('[data-testid="simulation-total-requested-0"]')
    expect(requested).to_be_visible()
    assert requested.inner_text().isdigit(), f"total_requested not numeric"

    # total_available
    available = page.locator('[data-testid="simulation-total-available-0"]')
    expect(available).to_be_visible()
    assert available.inner_text().isdigit(), f"total_available not numeric"
