"""Contract proof for the wait_settled barrier (UI-SMOKE-STABILITY-005).

These do not touch the product. They drive a synthetic page whose API response
and React-style render are deliberately delayed, and prove the barrier does not
return early - which is exactly the failure mode that made the UI-smoke set
flake with "locator not visible" on a different test every attempt.

Lives in tests/ui-contract/ so the roadmap guard does not count it as a
journey smoke, and so it needs no database or product stack.
"""

import os
import time

import pytest

if not os.environ.get("UI_SMOKE_RUN"):
    pytest.skip("UI_SMOKE_RUN not set", allow_module_level=True)

from _settle import SettleTimeout, wait_settled
from playwright.sync_api import Page, expect

# Served from a fake origin that is fulfilled entirely by Playwright routing -
# no network, no server. A real origin is required so the page's relative
# fetch('/slow-api') resolves (it does not on about:blank).
ORIGIN = "http://ui-contract.test"

DELAYED_RENDER_PAGE = """
<!doctype html><html><body>
<button id="go">go</button><div id="out"></div>
<script>
  window.fetchDone = false;
  document.getElementById('go').addEventListener('click', () => {
    fetch('/slow-api').then(r => r.text()).then(() => {
      window.fetchDone = true;
      setTimeout(() => {
        const el = document.createElement('span');
        el.setAttribute('data-testid', 'late-marker');
        el.textContent = 'rendered';
        document.getElementById('out').appendChild(el);
      }, RENDER_MS);
    });
  });
</script></body></html>
"""

# Contract boundary, stated honestly: the barrier waits for in-flight requests,
# two painted frames and a quiet DOM. It cannot predict a render scheduled far
# in the future with no network activity and no DOM change in between - nothing
# observable distinguishes that from "finished". React commits within a frame of
# the response, so the render delays exercised here stay inside the quiet window.
RENDER_DELAY_MS = 120


def _serve(page: Page, html: str, api_ms: int) -> None:
    def api(route):
        time.sleep(api_ms / 1000)
        route.fulfill(status=200, content_type="text/plain", body="ok")

    def index(route):
        route.fulfill(status=200, content_type="text/html", body=html)

    page.route(f"{ORIGIN}/slow-api", api)
    page.route(f"{ORIGIN}/", index)
    page.goto(f"{ORIGIN}/")


def _page_with(page: Page, api_ms: int, render_ms: int = RENDER_DELAY_MS) -> Page:
    _serve(page, DELAYED_RENDER_PAGE.replace("RENDER_MS", str(render_ms)), api_ms)
    return page


def _static(page: Page, body: str) -> Page:
    """A page on the fake origin with no API at all."""
    page.route(f"{ORIGIN}/", lambda r: r.fulfill(
        status=200, content_type="text/html", body=f"<!doctype html><html><body>{body}</body></html>"))
    page.goto(f"{ORIGIN}/")
    return page


def test_settles_on_a_quiet_page(page: Page):
    _static(page, "<p>static</p>")
    started = time.time()
    wait_settled(page, timeout=10000)
    assert time.time() - started < 5, "a quiet page must settle quickly"


def test_does_not_return_before_delayed_render_lands(page: Page):
    """The core regression: a slow API response, then the render it triggers.

    networkidle would have returned during the request gap; if the barrier did
    the same, the marker would still be missing the instant it returns.
    """
    _page_with(page, api_ms=800)
    page.click("#go")
    wait_settled(page, timeout=20000)
    # No waiting here on purpose - the marker must already be present.
    assert page.locator('[data-testid="late-marker"]').count() == 1, (
        "wait_settled returned before the delayed render landed"
    )


def test_waits_at_least_as_long_as_the_delay(page: Page):
    _page_with(page, api_ms=900)
    # Timed from the click: the sync route handler can be serviced inside
    # click(), so starting the clock after it would not measure the wait.
    started = time.time()
    page.click("#go")
    wait_settled(page, timeout=20000)
    elapsed_ms = (time.time() - started) * 1000
    assert elapsed_ms >= 900, (
        f"click+settle finished in {elapsed_ms:.0f}ms; the request alone takes ~900ms"
    )
    assert page.locator('[data-testid="late-marker"]').count() == 1


def test_does_not_return_while_a_request_is_in_flight(page: Page):
    _page_with(page, api_ms=1200)
    page.click("#go")
    wait_settled(page, timeout=20000)
    assert page.evaluate("window.fetchDone === true"), (
        "wait_settled returned while a request was still in flight"
    )
    assert page.evaluate("window.__rmpInflight") == 0


def test_fail_closed_when_the_dom_never_goes_quiet(page: Page):
    """A permanently churning DOM must fail loudly, not be swallowed."""
    _static(page, """<div id="x"></div>
    <script>setInterval(() => {
        document.getElementById('x').textContent = String(Math.random());
    }, 30);</script>""")
    with pytest.raises(SettleTimeout) as excinfo:
        wait_settled(page, timeout=2500)
    message = str(excinfo.value)
    assert "never settled" in message
    assert "in-flight requests" in message and "url:" in message


def test_timeout_message_carries_diagnostics(page: Page):
    _static(page, """<div id="y"></div>
    <script>setInterval(() => {
        const d = document.createElement('i'); d.textContent = 'x';
        document.getElementById('y').appendChild(d);
    }, 25);</script>""")
    with pytest.raises(SettleTimeout) as excinfo:
        wait_settled(page, timeout=2000)
    assert "readyState" in str(excinfo.value)


def test_inflight_counter_is_installed(page: Page):
    _static(page, "")
    assert page.evaluate("window.__rmpInflightInstalled === true"), (
        "the in-flight counter init script did not run"
    )


# --- static guard over the smoke suite ---------------------------------------
#
# The mass migration off networkidle rewrote 37 files; one of them ended up
# calling wait_settled without importing it, which only surfaced as a runtime
# NameError in a full run. This catches that class of mistake statically.

import ast
from pathlib import Path

_SMOKE_DIR = Path(__file__).resolve().parents[1] / "ui-smoke"


def _smoke_files():
    return sorted(_SMOKE_DIR.glob("test_uismoke__*.py"))


def test_every_smoke_file_that_uses_the_barrier_imports_it():
    offenders = []
    for path in _smoke_files():
        tree = ast.parse(path.read_text())
        used = any(
            isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            and n.func.id == "wait_settled"
            for n in ast.walk(tree)
        )
        if not used:
            continue
        imported = any(
            isinstance(n, ast.ImportFrom)
            and any(a.name == "wait_settled" for a in n.names)
            for n in ast.walk(tree)
        )
        if not imported:
            offenders.append(path.name)
    assert not offenders, f"wait_settled used without importing it: {offenders}"


def test_no_smoke_file_still_uses_networkidle():
    offenders = [
        p.name for p in _smoke_files()
        if "wait_for_load_state(\"networkidle\")" in p.read_text()
        or "wait_for_load_state('networkidle')" in p.read_text()
    ]
    assert not offenders, f"networkidle is a false readiness barrier: {offenders}"


def test_no_smoke_file_uses_arbitrary_sleeps():
    offenders = [p.name for p in _smoke_files() if ".wait_for_timeout(" in p.read_text()]
    assert not offenders, f"arbitrary sleeps left in: {offenders}"
