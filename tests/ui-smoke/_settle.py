"""State-based readiness barrier for browser tests (UI-SMOKE-STABILITY-005).

Lives in its own module so the contract proof in tests/ui-contract/ can import
it without pulling in the smoke suite's database fixtures.
"""

from __future__ import annotations

import os

# Settle budget: how long a rendered result may take to appear after a
# mutation. This is a *state* wait - it returns as soon as the app is
# genuinely idle, so a healthy run pays only the real render time.
SETTLE_TIMEOUT_MS = int(os.environ.get("UI_SMOKE_SETTLE_TIMEOUT_MS", "20000"))
_SETTLE_QUIET_MS = 250

# Counts in-flight fetch/XHR so settling cannot start while a request the
# UI depends on is still outstanding.
_INFLIGHT_INIT_JS = """
(() => {
    if (window.__rmpInflightInstalled) return;
    window.__rmpInflightInstalled = true;
    window.__rmpInflight = 0;
    const origFetch = window.fetch;
    if (origFetch) {
        window.fetch = function (...args) {
            window.__rmpInflight++;
            return origFetch.apply(this, args).finally(() => { window.__rmpInflight--; });
        };
    }
    const origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function (...args) {
        window.__rmpInflight++;
        let done = false;
        const dec = () => { if (!done) { done = true; window.__rmpInflight--; } };
        this.addEventListener("loadend", dec);
        try { return origSend.apply(this, args); } catch (e) { dec(); throw e; }
    };
})()
"""

# Idle means: nothing in flight, at least two painted frames, and the DOM
# quiet for the quiet window. Returns a diagnostic object, never just false,
# so a timeout can explain itself.
_SETTLE_JS = """
(quietMs) => new Promise((resolve) => {
    let lastMutation = performance.now();
    let frames = 0;
    const obs = new MutationObserver(() => {
        lastMutation = performance.now();
        frames = 0;
    });
    obs.observe(document.documentElement, {
        childList: true, subtree: true, attributes: true, characterData: true,
    });
    const started = performance.now();
    const tick = () => {
        const inflight = window.__rmpInflight || 0;
        if (inflight > 0) {
            lastMutation = performance.now();
            frames = 0;
            return requestAnimationFrame(tick);
        }
        frames++;
        const quietFor = performance.now() - lastMutation;
        if (frames >= 2 && quietFor >= quietMs) {
            obs.disconnect();
            return resolve({ settled: true, waitedMs: Math.round(performance.now() - started) });
        }
        requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
})
"""

_SETTLE_PROBE_JS = """
() => ({
    inflight: window.__rmpInflight === undefined ? "n/a" : window.__rmpInflight,
    readyState: document.readyState,
    url: location.href,
})
"""

class SettleTimeout(AssertionError):
    """The app never went idle - a real failure, not something to swallow."""

def wait_settled(page: Page, timeout: int = None) -> None:
    """State-based replacement for ``wait_for_load_state("networkidle")``.

    ``networkidle`` returns after 500 ms of network silence. In this SPA
    that moment arrives *after* the API response but *before* React has
    mounted the result of the mutation. Tests then began a short visibility
    wait against a screen that had not rendered yet and lost the race
    whenever the runner was busy - which is why the failing set differed on
    every attempt while the error was always "locator not visible".

    Idle here means all three of: no in-flight fetch/XHR, at least two
    painted frames, and a DOM that has been quiet for the quiet window.

    It is fail-closed: if the app never goes idle within the budget this
    raises with diagnostics. The semantic ``expect`` that follows remains
    the proof of the result - this only removes a false readiness barrier.
    """
    budget = timeout or SETTLE_TIMEOUT_MS
    page.wait_for_load_state("domcontentloaded")
    try:
        page.wait_for_function(_SETTLE_JS, arg=_SETTLE_QUIET_MS, timeout=budget)
    except Exception as exc:
        try:
            probe = page.evaluate(_SETTLE_PROBE_JS)
        except Exception:
            probe = {"probe": "unavailable"}
        raise SettleTimeout(
            f"UI never settled within {budget}ms - "
            f"in-flight requests: {probe.get('inflight')}, "
            f"readyState: {probe.get('readyState')}, url: {probe.get('url')}. "
            f"The DOM kept changing or a request never completed "
            f"(original: {type(exc).__name__})"
        ) from exc



__all__ = ["wait_settled", "SettleTimeout", "INFLIGHT_INIT_JS",
           "SETTLE_TIMEOUT_MS"]

INFLIGHT_INIT_JS = _INFLIGHT_INIT_JS
