"""
RM-STAB-022: the advertiser portal does not call ``require_permission`` routes.

Since RM-STAB-022 ``require_permission`` counts global roles only, so an
advertiser (scoped role) gets 403 on every route guarded by it - among them
GET /branches, /clusters, /stores and /display-surfaces, which the advertiser
role used to pass. That is safe only while advertiser-web never calls such a
route; this test pins it.

This is a static check: the guarded routes are read from the FastAPI app, the
portal calls from string literals in its sources. A path assembled from
variables is not seen. The 403 itself is proven in
tests/behavioral/test_rm_stab_022_role_escalation.py.
"""

import importlib.util
import os
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "apps" / "advertiser-web" / "src"
_PREFIX = "/api/v1/identity"
_REFERENCE_ROUTES = {"/branches", "/clusters", "/stores", "/display-surfaces"}
_LITERAL = re.compile(r"""(["'`])((?:(?!\1).)*)\1""")


def _app():
    os.environ.setdefault("ENVIRONMENT", "dev")
    path = _ROOT / "apps" / "control-api" / "main.py"
    spec = importlib.util.spec_from_file_location("control_api_main_rm022", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.app


def _uses_require_permission(dependant) -> bool:
    for dep in dependant.dependencies:
        qualname = getattr(dep.call, "__qualname__", "")
        if qualname.startswith("require_permission.<locals>"):
            return True
        if _uses_require_permission(dep):
            return True
    return False


def _leaf_routes(routes, prefix=""):
    """Yield (full path, dependant) for every endpoint, whether the installed
    FastAPI flattens included routers or keeps them as nested wrappers."""
    for route in routes:
        dependant = getattr(route, "dependant", None)
        if dependant is not None:
            yield prefix + route.path, dependant
            continue
        nested = getattr(route, "original_router", None)
        if nested is not None:
            context_prefix = getattr(route.include_context, "prefix", "") or ""
            yield from _leaf_routes(nested.routes, prefix + context_prefix)


def _guarded_paths() -> set[str]:
    """Paths of require_permission routes, relative to the identity prefix,
    with every path parameter written as ``{}``."""
    paths = set()
    for full_path, dependant in _leaf_routes(_app().routes):
        if not _uses_require_permission(dependant):
            continue
        assert full_path.startswith(_PREFIX), full_path
        paths.add(re.sub(r"\{[^}]*\}", "{}", full_path[len(_PREFIX):]))
    return paths


def _portal_paths() -> dict[str, str]:
    """Path-like string literals of advertiser-web -> where they were found."""
    found = {}
    for path in sorted(_SRC.rglob("*.ts*")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for match in _LITERAL.finditer(line):
                literal = match.group(2)
                if not literal.startswith("/"):
                    continue
                normalized = re.sub(r"\$\{[^}]*\}", "{}", literal.split("?")[0])
                found.setdefault(normalized, f"{path.relative_to(_SRC)}:{lineno}")
    return found


def test_guarded_routes_are_found_in_the_app():
    guarded = _guarded_paths()
    assert _REFERENCE_ROUTES <= guarded, sorted(guarded)
    assert "/users/{}/roles" in guarded
    assert len(guarded) >= 30, sorted(guarded)


def test_portal_literals_are_found():
    portal = _portal_paths()
    assert "/campaigns" in portal, sorted(portal)[:40]
    assert any("{}" in p for p in portal), "template literals with ${...} not parsed"


def test_advertiser_web_does_not_call_require_permission_routes():
    portal = _portal_paths()
    hits = sorted(f"{p}  ({portal[p]})" for p in _guarded_paths() & set(portal))
    assert hits == [], (
        "advertiser-web calls a route guarded by require_permission - its users "
        "hold scoped roles only and get 403 (RM-STAB-022):\n" + "\n".join(hits)
    )
