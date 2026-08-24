"""Contract tests for the readiness barrier — browser only, no product stack.

Deliberately independent of tests/ui-smoke/conftest.py and of pytest-playwright:
these tests must prove the barrier's behaviour without a database, control-api,
a built frontend, or the smoke plugin stack. They drive Chromium directly.
"""

import os
import sys
from pathlib import Path

import pytest

_RUN = bool(os.environ.get("UI_SMOKE_RUN", ""))

if not _RUN:
    def pytest_ignore_collect(collection_path, config):
        return True
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ui-smoke"))
    from _settle import INFLIGHT_INIT_JS
    from playwright.sync_api import sync_playwright

    @pytest.fixture(scope="session")
    def _browser():
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            yield browser
            browser.close()

    @pytest.fixture
    def page(_browser):
        """Own page fixture — overrides pytest-playwright's when it is present."""
        context = _browser.new_context()
        context.add_init_script(INFLIGHT_INIT_JS)
        pg = context.new_page()
        yield pg
        context.close()
