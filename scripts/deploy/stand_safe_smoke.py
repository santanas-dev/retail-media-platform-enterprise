#!/usr/bin/env python3
"""Stand-safe smoke for the local DEV/QA stand (LOCAL-DEV-STAND-001-FU-IDENTITY-SMOKE).

The CI UI-smoke suite is written for a throwaway phase1 compose. Run against
the shared stand it deletes accumulated accounts, can assign a role to a seed
user (it did: advertiser_test briefly gained `operator`), hard-codes dev
passwords and `http://localhost:8000`, and assumes creative auto-approval. This
runner exists so the stand can be checked without any of that.

What it is allowed to do:

  1. admin login + reload            6. creative upload
  2. advertiser login + reload       7. contract PDF upload
  3. /version, build-info, health    8. MinIO object existence / size / hash
  4. advertiser sees only its org    9. persistence across a reload
  5. operator endpoints -> 403

What it must never do: assign or remove roles, deactivate users, touch
emergency state, moderate shared creatives, clean up seed or non-owned records,
use a broad cleanup predicate, rely on dev credentials, or run against anything
other than the local stand.

Everything it creates carries a `standchk-<run-id>` marker, the exact ids are
written to a local run file, and cleanup only ever names those ids. Where the
API has no safe way to remove a record, the ids are reported and nothing is
deleted — a broad delete is never the fallback.

Passwords are read from the approved password files and never appear in argv,
the environment, the log or the report. The files are never modified.

Usage:
    python scripts/deploy/stand_safe_smoke.py --host 192.168.110.81 \\
        --admin-password-file ~/.config/rmp-local-stand/admin-password \\
        --advertiser-password-file ~/.config/rmp-local-stand/advertiser-password
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

STAND_PROJECT = "rmp-local-stand"
# The stand is the only environment this runner may touch.
ALLOWED_ENVIRONMENTS = {"staging"}
FORBIDDEN_ENVIRONMENTS = {"production", "prod", "pilot"}
STAND_VERSION_PREFIX = "stand-"

MARKER_PREFIX = "standchk"

# A 1x1 PNG and a minimal PDF — small, deterministic, and obviously synthetic.
PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000d49444154789c6360000002000100ffff03000006"
    "0005574bd0e10000000049454e44ae426082"
)
PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


class SmokeError(RuntimeError):
    pass


# --- reporting ---------------------------------------------------------------

class Report:
    def __init__(self) -> None:
        self.results: list[tuple[str, bool, str]] = []
        self.created: list[dict] = []

    def check(self, name: str, ok: bool, detail: str = "") -> bool:
        self.results.append((name, ok, detail))
        print(("  PASS  " if ok else "  FAIL  ") + name + (f"   [{detail}]" if detail else ""))
        return ok

    def record(self, kind: str, ident: str, cleanup: str) -> None:
        self.created.append({"kind": kind, "id": ident, "cleanup": cleanup})

    @property
    def failures(self) -> list[str]:
        return [n for n, ok, _ in self.results if not ok]


# --- credentials -------------------------------------------------------------

def read_password(path: Path) -> str:
    """Read a password from an approved file. The value is never printed.

    Fail-closed on anything that is not a private regular file: a symlink or a
    group-readable file is a different secret than the one that was approved.
    """
    if not path.exists():
        raise SmokeError(f"password file not found: {path}")
    if path.is_symlink():
        raise SmokeError(f"password file is a symlink: {path}")
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise SmokeError(f"password file is not a regular file: {path}")
    if st.st_mode & 0o077:
        raise SmokeError(f"password file is group/world accessible: {path} "
                         f"(mode {oct(st.st_mode & 0o777)})")
    if st.st_uid != os.getuid():
        raise SmokeError(f"password file is not owned by the current user: {path}")
    value = path.read_text().strip()
    if not value:
        raise SmokeError(f"password file is empty: {path}")
    return value


_SECRET_RE = re.compile(r"(password|secret|token|authorization)", re.IGNORECASE)


def redact(payload: dict) -> dict:
    """Never let a credential reach the log or the run file."""
    out = {}
    for k, v in payload.items():
        out[k] = "***" if _SECRET_RE.search(k) else v
    return out


# --- http --------------------------------------------------------------------

def call(base: str, method: str, path: str, token: str | None = None,
         body: dict | None = None, timeout: int = 30):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw or "null")
        except json.JSONDecodeError:
            return e.code, raw[:200]


def get_json(url: str, timeout: int = 20) -> dict:
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


def put_bytes(url: str, payload: bytes, headers: dict[str, str], timeout: int = 60) -> int:
    req = urllib.request.Request(url, data=payload, method="PUT")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status


def login(base: str, username: str, password: str, provider: str) -> str:
    st, res = call(base, "POST", "/auth/login",
                   body={"username_or_email": username, "password": password,
                         "auth_provider": provider})
    del password
    if st != 200:
        raise SmokeError(f"login failed for {username}: HTTP {st}")
    return res["access_token"]


# --- guards ------------------------------------------------------------------

def assert_target_is_the_stand(host: str, report: Report) -> dict:
    """Refuse to run anywhere but the local stand.

    Checked from what the target itself reports, not from a flag the caller
    passes, so pointing this at the pilot by mistake stops here.
    """
    version = get_json(f"http://{host}:8000/version")
    env = (version.get("environment") or "").lower()
    tag = version.get("version") or ""
    if env in FORBIDDEN_ENVIRONMENTS:
        raise SmokeError(f"refusing to run against environment={env!r}")
    if env not in ALLOWED_ENVIRONMENTS:
        raise SmokeError(f"unexpected environment={env!r}; the stand reports "
                         f"one of {sorted(ALLOWED_ENVIRONMENTS)}")
    if not tag.startswith(STAND_VERSION_PREFIX):
        raise SmokeError(f"version {tag!r} is not a stand bundle "
                         f"(expected a {STAND_VERSION_PREFIX}* tag)")
    report.check("target is the local stand, not the pilot", True,
                 f"{tag} env={env}")
    return version


# --- journeys ----------------------------------------------------------------

def journey_identity(host: str, report: Report, version: dict) -> None:
    for name, url in (("control-api /version", f"http://{host}:8000/version"),
                      ("admin-web build-info", f"http://{host}:3000/build-info.json"),
                      ("advertiser-web build-info", f"http://{host}:3001/build-info.json")):
        try:
            d = get_json(url)
        except Exception as e:
            report.check(f"{name} reachable", False, str(e)[:80])
            continue
        report.check(f"{name} reports the deployed SHA", d.get("git_sha") == version["git_sha"],
                     f"git_sha={str(d.get('git_sha'))[:12]}…")
    for name, url in (("live", f"http://{host}:8000/health/live"),
                      ("ready", f"http://{host}:8000/health/ready")):
        try:
            d = get_json(url)
            report.check(f"health/{name} ok", d.get("status") in ("ok", "alive", "live"),
                         str(d.get("status")))
        except Exception as e:
            report.check(f"health/{name} ok", False, str(e)[:80])


def journey_api_sessions(base: str, admin_token: str, adv_token: str,
                         report: Report) -> str:
    st, me = call(base, "GET", "/auth/me", adv_token)
    org = me.get("advertiser_organization_id") if st == 200 else None
    report.check("advertiser session resolves its own organisation", bool(org),
                 (me.get("advertiser_organization") or {}).get("display_name") if st == 200 else f"HTTP {st}")

    st, camps = call(base, "GET", "/identity/campaigns?limit=500", adv_token)
    orgs = {c["advertiser_organization_id"] for c in camps["items"]} if st == 200 else set()
    report.check("advertiser sees only its own organisation", st == 200 and orgs == {org},
                 f"orgs={orgs}")

    for path in ("/identity/users", "/identity/audit-events", "/identity/devices"):
        st, _ = call(base, "GET", path, adv_token)
        report.check(f"operator endpoint refused for advertiser: {path}",
                     st in (401, 403), f"HTTP {st}")
    for method, path in (("POST", "/identity/campaigns"),
                         ("POST", "/identity/creative-assets")):
        st, _ = call(base, method, path, adv_token, {})
        report.check(f"operator write refused for advertiser: {method} {path}",
                     st == 403, f"HTTP {st}")

    st, admin_me = call(base, "GET", "/auth/me", admin_token)
    report.check("operator session has no advertiser organisation",
                 st == 200 and admin_me.get("advertiser_organization_id") is None)
    return org


def journey_creative_upload(base: str, admin_token: str, org: str, run_id: str,
                            report: Report) -> None:
    code = f"{MARKER_PREFIX}-{run_id}-cr"
    st, asset = call(base, "POST", "/identity/creative-assets", admin_token, {
        "code": code, "name": f"{MARKER_PREFIX} creative {run_id}",
        "media_type": "image/png", "advertiser_organization_id": org,
    })
    if not report.check("creative asset created", st == 201, f"HTTP {st}"):
        return
    asset_id = asset["id"]
    report.record("creative_asset", asset_id, "no DELETE endpoint — retained, reported")

    st, intent = call(base, "POST", f"/identity/creative-assets/{asset_id}/upload-intent",
                      admin_token, {"filename": f"{code}.png", "content_type": "image/png",
                                    "content_length": len(PNG_BYTES)})
    if not report.check("creative upload intent issued", st == 200, f"HTTP {st}"):
        return
    try:
        code_put = put_bytes(intent["upload_url"], PNG_BYTES, intent.get("headers") or {})
    except Exception as e:
        report.check("creative object uploaded to MinIO", False, str(e)[:100])
        return
    report.check("creative object uploaded to MinIO", code_put in (200, 204), f"HTTP {code_put}")

    st, done = call(base, "POST", f"/identity/creative-assets/{asset_id}/complete-upload",
                    admin_token, {"upload_id": intent["upload_id"]})
    if not report.check("creative upload completed", st == 200, f"HTTP {st}"):
        return
    expected = hashlib.sha256(PNG_BYTES).hexdigest()
    report.check("MinIO object hash matches what was uploaded",
                 done.get("sha256_checksum") == expected, f"{str(done.get('sha256_checksum'))[:16]}…")
    report.check("MinIO object size matches what was uploaded",
                 done.get("file_size_bytes") == len(PNG_BYTES),
                 f"{done.get('file_size_bytes')} bytes")


def journey_contract_upload(base: str, admin_token: str, org: str, run_id: str,
                            report: Report) -> None:
    code = f"{MARKER_PREFIX}-{run_id}-ctr"
    st, contract = call(base, "POST", "/identity/advertiser-contracts", admin_token, {
        "advertiser_organization_id": org, "code": code,
        "name": f"{MARKER_PREFIX} contract {run_id}", "status": "active",
    })
    if not report.check("own contract created (shared contracts untouched)",
                        st == 201, f"HTTP {st}"):
        return
    contract_id = contract["id"]
    report.record("advertiser_contract", contract_id, "no DELETE endpoint — retained, reported")

    st, intent = call(base, "POST", f"/identity/advertiser-contracts/{contract_id}/upload-intent",
                      admin_token, {"filename": f"{code}.pdf", "content_type": "application/pdf",
                                    "content_length": len(PDF_BYTES)})
    if not report.check("contract upload intent issued", st == 200, f"HTTP {st}"):
        return
    try:
        code_put = put_bytes(intent["upload_url"], PDF_BYTES, intent.get("headers") or {})
    except Exception as e:
        report.check("contract PDF uploaded to MinIO", False, str(e)[:100])
        return
    report.check("contract PDF uploaded to MinIO", code_put in (200, 204), f"HTTP {code_put}")

    st, done = call(base, "POST", f"/identity/advertiser-contracts/{contract_id}/complete-upload",
                    admin_token, {"upload_id": intent["upload_id"]})
    if not report.check("contract upload completed", st == 200, f"HTTP {st}"):
        return
    expected = hashlib.sha256(PDF_BYTES).hexdigest()
    got = done.get("sha256_checksum") or done.get("file_sha256")
    report.check("contract object hash matches what was uploaded", got == expected,
                 f"{str(got)[:16]}…")


def journey_persistence(base: str, admin_token: str, run_id: str, report: Report) -> None:
    """A fresh session must still see what the previous one created."""
    st, assets = call(base, "GET", "/identity/creative-assets", admin_token)
    codes = {a.get("code") for a in assets} if isinstance(assets, list) else set()
    report.check("created creative survives a new session",
                 f"{MARKER_PREFIX}-{run_id}-cr" in codes, f"{len(codes)} assets visible")
    st, contracts = call(base, "GET", "/identity/advertiser-contracts", admin_token)
    ccodes = {c.get("code") for c in contracts} if isinstance(contracts, list) else set()
    report.check("created contract survives a new session",
                 f"{MARKER_PREFIX}-{run_id}-ctr" in ccodes, f"{len(ccodes)} contracts visible")


# --- main --------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", required=True, help="stand address (no scheme)")
    parser.add_argument("--admin-password-file", required=True, type=Path)
    parser.add_argument("--advertiser-password-file", required=True, type=Path)
    parser.add_argument("--admin-username", default="break_glass_admin")
    parser.add_argument("--advertiser-username", default="advertiser_test")
    parser.add_argument("--run-file", type=Path, default=None,
                        help="where to write the created-id record (default: cwd)")
    parser.add_argument("--browser", action="store_true",
                        help="also run the two browser login/reload journeys")
    args = parser.parse_args(argv)

    run_id = uuid.uuid4().hex[:8]
    base = f"http://{args.host}:8000/api/v1"
    report = Report()
    print(f"=== stand-safe smoke, run {MARKER_PREFIX}-{run_id} ===")

    try:
        version = assert_target_is_the_stand(args.host, report)
        admin_pw = read_password(args.admin_password_file)
        adv_pw = read_password(args.advertiser_password_file)
        report.check("credentials read from approved password files", True,
                     "values never printed")

        admin_token = login(base, args.admin_username, admin_pw, "local_break_glass")
        adv_token = login(base, args.advertiser_username, adv_pw, "local_advertiser")
        del admin_pw, adv_pw
        report.check("admin API session established", True)
        report.check("advertiser API session established", True)

        journey_identity(args.host, report, version)
        org = journey_api_sessions(base, admin_token, adv_token, report)
        if org:
            journey_creative_upload(base, admin_token, org, run_id, report)
            journey_contract_upload(base, admin_token, org, run_id, report)
        # A brand new token is the API-level equivalent of a reload: nothing
        # is cached client-side, so what comes back is what was committed.
        fresh_admin = login(base, args.admin_username,
                            read_password(args.admin_password_file), "local_break_glass")
        journey_persistence(base, fresh_admin, run_id, report)

        if args.browser:
            run_browser_journeys(args, report)
    except SmokeError as e:
        print(f"\nSMOKE ABORTED: {e}", file=sys.stderr)
        return 2

    run_file = args.run_file or Path(f"stand-safe-smoke-{run_id}.json")
    run_file.write_text(json.dumps({
        "run_id": run_id,
        "marker": f"{MARKER_PREFIX}-{run_id}",
        "host": args.host,
        "finished_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created": report.created,
        "results": [{"check": n, "ok": ok, "detail": d} for n, ok, d in report.results],
    }, indent=2, ensure_ascii=False) + "\n")

    print()
    print(f"created records (exact ids, cleanup only ever names these): {len(report.created)}")
    for item in report.created:
        print(f"  {item['kind']}: {item['id']} — {item['cleanup']}")
    print(f"run file: {run_file}")
    print(f"FAILED CHECKS: {report.failures if report.failures else 'нет'}")
    return 1 if report.failures else 0


def run_browser_journeys(args, report: Report) -> None:
    """admin and advertiser login + reload, using state-based waits only."""
    from playwright.sync_api import sync_playwright

    adm = f"http://{args.host}:3000"
    adv = f"http://{args.host}:3001"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for base_url, user, pwfile, label in (
            (adm, args.admin_username, args.admin_password_file, "админ-портал"),
            (adv, args.advertiser_username, args.advertiser_password_file, "кабинет"),
        ):
            ctx = browser.new_context()
            page = ctx.new_page()
            page.goto(f"{base_url}/login", wait_until="domcontentloaded")
            page.wait_for_selector("#login-username", state="visible")
            page.fill("#login-username", user)
            page.fill("#login-password", read_password(pwfile))
            page.click("button[type=submit]")
            page.wait_for_url(f"{base_url}/campaigns", timeout=30000)
            page.wait_for_selector("table, [data-testid]", state="visible", timeout=30000)
            report.check(f"{label}: вход", page.url.startswith(f"{base_url}/campaigns"), page.url)
            page.reload(wait_until="domcontentloaded")
            page.wait_for_selector("table, [data-testid]", state="visible", timeout=30000)
            report.check(f"{label}: сессия переживает reload",
                         page.url.startswith(f"{base_url}/campaigns"), page.url)
            ctx.close()
        browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
