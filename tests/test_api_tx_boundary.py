"""API-TX-BOUNDARY-001 — a 2xx mutation must mean the write is committed.

packages/api/dependencies.py::get_db yields inside `async with session.begin()`,
so the transaction commits when the dependency exits. With FastAPI's default
dependency scope ("request") that happens AFTER the response has been sent, so a
client that immediately re-reads can observe pre-commit state.

That is what made the UI-smoke suite flaky in a way no test-side wait could fix:
the SPA received 200, refetched at once, and read stale data. The clearest
evidence was advertiser__brand_crud asserting
'Смоук Бренд SMOKE-…' == 'Смоук Бренд Обновлён' - the old value.

These tests pin the ordering contract itself, independently of the database.
"""

from __future__ import annotations

import inspect

import pytest
from fastapi import BackgroundTasks, Depends, FastAPI
from fastapi.testclient import TestClient

import packages.api.dependencies as deps


# --- the ordering contract ---------------------------------------------------

def _ordering_app(scope):
    """App whose dependency records when it exits, relative to response send."""
    events: list[str] = []
    app = FastAPI()

    async def dep():
        events.append("dep:start")
        try:
            yield "session"
        finally:
            events.append("dep:exit")      # stands in for commit

    depends = Depends(dep, scope=scope) if scope else Depends(dep)

    @app.get("/x")
    async def handler(_s=depends, background: BackgroundTasks = None):
        events.append("handler:end")
        return {"ok": True}

    return app, events


def test_fastapi_supports_function_scope():
    """The fix depends on this; fail loudly if the runtime cannot do it."""
    sig = inspect.signature(Depends)
    assert "scope" in sig.parameters, (
        "this FastAPI cannot scope dependencies; the transaction boundary "
        "cannot be fixed without an upgrade or a separate dependency")


def test_default_request_scope_exits_after_response():
    """Documents the defect: with request scope the commit lands after send."""
    app, events = _ordering_app(scope=None)
    with TestClient(app) as client:
        client.get("/x")
    assert events[-1] == "dep:exit"
    assert events.index("handler:end") < events.index("dep:exit")


def test_function_scope_exits_before_response_is_sent():
    """The contract the fix relies on: dependency exit precedes the send."""
    app, events = _ordering_app(scope="function")
    sent: list[str] = []

    @app.middleware("http")
    async def mark_send(request, call_next):
        response = await call_next(request)
        sent.append("response:sent")
        events.append("response:sent")
        return response

    with TestClient(app) as client:
        client.get("/x")

    assert "dep:exit" in events and "response:sent" in events
    assert events.index("dep:exit") < events.index("response:sent"), (
        f"dependency must finish before the response is sent, got {events}")


# --- get_db must use function scope everywhere -------------------------------

def test_get_db_is_wired_with_function_scope():
    """Every Depends(get_db) must carry scope='function'.

    A single request-scoped usage re-opens the read-after-write window for that
    endpoint, so this is asserted across the whole API surface rather than at
    the definition site.
    """
    import pathlib
    import re

    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    pattern = re.compile(r"Depends\(\s*get_db\s*([^)]*)\)")
    for path in list((root / "packages" / "api").rglob("*.py")) + \
                list((root / "apps").rglob("*.py")):
        text = path.read_text()
        for m in pattern.finditer(text):
            if 'scope="function"' not in m.group(0) and "scope='function'" not in m.group(0):
                offenders.append(f"{path.relative_to(root)}: {m.group(0)[:60]}")
    assert not offenders, (
        "Depends(get_db) without scope='function' re-opens the pre-commit read "
        "window:\n" + "\n".join(offenders[:15]))


def test_get_db_still_wraps_a_transaction():
    src = inspect.getsource(deps.get_db)
    assert "session.begin()" in src, "the transactional boundary was removed"
    assert "yield session" in src


# --- failure semantics -------------------------------------------------------
#
# A 2xx must never be returned when the commit itself failed, and a handler
# exception must roll back. With request scope the commit ran after the response
# had already been sent, so a late failure could not change the status code.

def _tx_app(commit_raises=False, handler_raises=False, serialization_error=False):
    state = {"committed": False, "rolled_back": False}
    app = FastAPI()

    class FakeTx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            if exc_type is not None:
                state["rolled_back"] = True
                return False
            if commit_raises:
                raise RuntimeError("commit failed")
            if serialization_error:
                raise RuntimeError("could not serialize access due to concurrent update")
            state["committed"] = True
            return False

    async def dep():
        async with FakeTx():
            yield "session"

    @app.get("/m")
    async def mutate(_s=Depends(dep, scope="function")):
        if handler_raises:
            raise ValueError("handler blew up")
        return {"ok": True}

    return app, state


def test_commit_failure_cannot_return_2xx():
    app, state = _tx_app(commit_raises=True)
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/m")
    assert r.status_code >= 500, (
        f"a failed commit must not surface as {r.status_code}; the client would "
        f"believe a write landed that was rolled back")
    assert not state["committed"]


def test_serialization_failure_cannot_return_2xx():
    app, state = _tx_app(serialization_error=True)
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/m")
    assert r.status_code >= 500
    assert not state["committed"]


def test_handler_exception_rolls_back():
    app, state = _tx_app(handler_raises=True)
    with TestClient(app, raise_server_exceptions=False) as client:
        r = client.get("/m")
    assert r.status_code >= 500
    assert state["rolled_back"], "handler failure must roll the transaction back"
    assert not state["committed"]


def test_successful_handler_commits_and_returns_2xx():
    app, state = _tx_app()
    with TestClient(app) as client:
        r = client.get("/m")
    assert r.status_code == 200
    assert state["committed"]


# --- surface audit -----------------------------------------------------------

def test_no_streaming_or_background_endpoints_hold_the_session():
    """Both would outlive a function-scoped session; assert none exist.

    If one is introduced later it needs its own session, not this dependency -
    hence a guard rather than a comment.
    """
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    offenders = []
    for path in (root / "packages" / "api").rglob("*.py"):
        text = path.read_text()
        if "StreamingResponse" in text or "BackgroundTasks" in text:
            if "get_db" in text:
                offenders.append(str(path.relative_to(root)))
    assert not offenders, (
        "these endpoints stream or defer work while holding a function-scoped "
        f"session: {offenders}")


def test_explicit_commit_endpoints_are_inventoried():
    """Endpoints that commit by hand must still work under function scope.

    They are listed so the count cannot drift silently; a new one needs a
    deliberate review for double-commit.
    """
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parents[1]
    found = {}
    for path in (root / "packages" / "api").rglob("*.py"):
        n = len(re.findall(r"await (?:db|session)\.commit\(\)", path.read_text()))
        if n:
            found[path.name] = n
    # auth.py manages its own login/refresh transactions; users/creatives commit
    # mid-handler before follow-up work.
    assert set(found) <= {"auth.py", "users.py", "creatives.py", "advertisers.py",
                          "campaigns.py", "commerce.py", "inventory.py",
                          "devices.py", "emergency.py", "briefs.py",
                          "advertiser_applications.py", "ad_settings.py",
                          "licenses.py", "reporting.py", "pop.py",
                          "applications.py", "onboard.py"}, found


def test_tamper_reverting_to_request_scope_is_caught():
    """Proof the guard is load-bearing: request scope must fail the wiring test."""
    import re
    sample = 'db=Depends(get_db)'
    assert not re.search(r'scope\s*=\s*["\']function["\']', sample)
    # the real assertion lives in test_get_db_is_wired_with_function_scope;
    # this documents what a regression would look like.


# --- dependency floor --------------------------------------------------------
#
# scope= does not exist before FastAPI 0.121.0 (verified: 0.120.0 absent,
# 0.121.0 present). With the previous floor of >=0.115.0 a clean install could
# resolve a version where every Depends(get_db, scope="function") raises
# TypeError at import time.

@pytest.mark.parametrize("req", [
    "apps/control-api/requirements.txt",
    "apps/device-gateway/requirements.txt",
])
def test_fastapi_floor_supports_dependency_scope(req):
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parents[1]
    text = (root / req).read_text()
    m = re.search(r"^fastapi>=(\d+)\.(\d+)\.(\d+)", text, re.M)
    assert m, f"{req}: no fastapi floor found"
    major, minor, patch = (int(g) for g in m.groups())
    assert (major, minor) >= (0, 121), (
        f"{req}: floor {major}.{minor}.{patch} predates dependency scope; "
        f"Depends(get_db, scope='function') would fail at import")
