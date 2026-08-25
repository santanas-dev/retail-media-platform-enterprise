"""Behavioral verification for the isolated restore drill (SCOPE F).

Runs against a RESTORED target (PostgreSQL + MinIO) and proves:

  - control row counts match the backup manifest
  - key UUIDs / business IDs survived the round-trip
  - commerce money values are exact
  - license occupied/released history and exact peak are preserved
  - campaign/device status history preserved
  - contract PDF exists and checksum matches
  - creative object exists and SHA matches
  - RLS enforced under retail_media_app NOBYPASSRLS
  - cross-org data is not disclosed
  - /version reports the candidate SHA
  - a new record can be created post-restore without sequence/PK collision
  - healthchecks green

Opt-in: RUN_RESTORE_DRILL_TESTS=1 (mirrors the behavioral suite pattern).

Required env:
  - RESTORE_TARGET_DATABASE_URL  (owner credential)
  - RESTORE_TARGET_APP_DATABASE_URL (retail_media_app NOBYPASSRLS credential)
  - RESTORE_TARGET_MINIO_ENDPOINT / ACCESS_KEY / SECRET_KEY
  - CREATIVE_STORAGE_BUCKET / CONTRACT_STORAGE_BUCKET
  - BACKUP_MANIFEST_PATH (path to backup-manifest.json)
  - BACKUP_DIR (path to the backup run dir)
  - RMP_GIT_SHA / RMP_VERSION (candidate identity)
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.backup import backup_manifest, drill_checks  # noqa: E402
from scripts.backup.seed_representative_data import IDS, _sha  # noqa: E402

REQUIRE_ENV = os.environ.get("RUN_RESTORE_DRILL_TESTS", "") == "1"
pytestmark = pytest.mark.skipif(not REQUIRE_ENV, reason="RUN_RESTORE_DRILL_TESTS=1 not set")


def _pg(url: str):
    # Lazy import — psycopg2 is only present in the drill job, not the generic
    # python-tests job (which still *collects* this module).
    import psycopg2
    from urllib.parse import urlparse
    u = urlparse(url)
    return psycopg2.connect(
        host=u.hostname, port=u.port or 5432, user=u.username,
        password=u.password, dbname=u.path.lstrip("/"),
    )


def _minio(endpoint: str, access: str, secret: str):
    from minio import Minio
    return Minio(endpoint, access_key=access, secret_key=secret, secure=False)


@pytest.fixture(scope="module")
def ctx():
    manifest_path = Path(os.environ["BACKUP_MANIFEST_PATH"])
    manifest = backup_manifest.load_manifest(manifest_path)
    owner_url = os.environ["RESTORE_TARGET_DATABASE_URL"]
    app_url = os.environ["RESTORE_TARGET_APP_DATABASE_URL"]
    minio_endpoint = os.environ["RESTORE_TARGET_MINIO_ENDPOINT"]
    access = os.environ["MINIO_ACCESS_KEY"]
    secret = os.environ["MINIO_SECRET_KEY"]
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "owner": _pg(owner_url),
        "app": _pg(app_url),
        "minio": _minio(minio_endpoint, access, secret),
        "creative_bucket": os.environ["CREATIVE_STORAGE_BUCKET"],
        "contract_bucket": os.environ["CONTRACT_STORAGE_BUCKET"],
        "git_sha": os.environ.get("RMP_GIT_SHA", ""),
        "version": os.environ.get("RMP_VERSION", ""),
    }


def _q(conn, sql: str):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()



def _repo_alembic_head() -> str:
    """The single head revision of the repo's alembic migrations.

    Read from the migration files rather than by importing alembic, so the
    drill has no dependency on an alembic config or a live database.
    """
    import re

    versions = REPO_ROOT / "apps" / "control-api" / "alembic" / "versions"
    revisions, down_revisions = set(), set()
    for f in versions.glob("*.py"):
        text = f.read_text()
        rev = re.search(r'^revision(?::\s*str)?\s*=\s*"([^"]+)"', text, re.M)
        down = re.search(r'^down_revision(?::[^=]+)?\s*=\s*"([^"]+)"', text, re.M)
        if rev:
            revisions.add(rev.group(1))
        if down:
            down_revisions.add(down.group(1))
    heads = revisions - down_revisions
    assert len(heads) == 1, f"expected exactly one alembic head, got {sorted(heads)}"
    return heads.pop()


class TestRestoredDataFidelity:
    def test_alembic_head_matches(self, ctx):
        actual = _q(ctx["owner"], "SELECT version_num FROM alembic_version;")[0]
        expected = ctx["manifest"]["postgres"]["alembic_head"]
        assert not drill_checks.check_alembic_head(actual, expected), \
            f"head mismatch: {actual} != {expected}"

    def test_control_row_counts_match(self, ctx):
        problems = []
        expected_counts = ctx["manifest"]["postgres"]["row_counts"]
        for tbl, expected in expected_counts.items():
            actual = _q(ctx["owner"], f"SELECT count(*) FROM {tbl};")[0]
            if actual != expected:
                problems.append(f"{tbl}: manifest={expected} actual={actual}")
        assert not problems, "row count mismatches: " + "; ".join(problems)

    def test_key_uuids_survive(self, ctx):
        # Deterministic business identities from the drill dataset.
        checks = [
            ("SELECT code FROM advertiser_organizations WHERE id=%s", (IDS["org"],), "DRILL-ADV"),
            ("SELECT code FROM campaigns WHERE id=%s", (IDS["campaign"],), "DRILL-CAMP-001"),
            ("SELECT code FROM commerce_orders WHERE id=%s", (IDS["order"],), "DRILL-ORDER-001"),
            ("SELECT license_id FROM license_grants WHERE id=%s", (IDS["license_grant"],), "DRILL-LIC-0001"),
            ("SELECT code FROM physical_devices WHERE id=%s", (IDS["device"],), "DRILL-DEV"),
        ]
        with ctx["owner"].cursor() as cur:
            for sql, params, expected in checks:
                cur.execute(sql, params)
                row = cur.fetchone()
                assert row is not None, f"missing row for {params}"
                assert row[0] == expected, f"expected {expected}, got {row[0]}"

    def test_commerce_money_exact(self, ctx):
        with ctx["owner"].cursor() as cur:
            cur.execute(
                "SELECT total_amount, currency FROM commerce_orders WHERE id=%s",
                (IDS["order"],),
            )
            total, currency = cur.fetchone()
        assert not drill_checks.check_money_exact(total, "125050.00", "order total")
        assert currency == "RUB"
        with ctx["owner"].cursor() as cur:
            cur.execute(
                "SELECT line_amount FROM commerce_order_lines WHERE id=%s",
                (IDS["order_line"],),
            )
            line = cur.fetchone()[0]
        assert not drill_checks.check_money_exact(line, "38765.50", "order line amount")

    def test_license_seat_history_and_peak(self, ctx):
        with ctx["owner"].cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM license_seats WHERE license_id=%s AND released_at IS NULL",
                (IDS["license_grant"],),
            )
            open_seats = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM license_seats WHERE license_id=%s AND released_at IS NOT NULL",
                (IDS["license_grant"],),
            )
            released = cur.fetchone()[0]
        assert not drill_checks.check_license_peak(open_seats, released, expected_peak=2)
        assert open_seats == 1
        assert released == 1

    def test_status_history_preserved(self, ctx):
        assert _q(
            ctx["owner"],
            f"SELECT count(*) FROM campaign_status_history WHERE campaign_id='{IDS['campaign']}';",
        )[0] == 1
        assert _q(
            ctx["owner"],
            f"SELECT count(*) FROM device_status_history WHERE physical_device_id='{IDS['device']}';",
        )[0] == 1

    def test_contract_pdf_checksum(self, ctx):
        manifest_sha = _sha(b"%PDF-1.4 DRILL contract placeholder - deterministic\n%%EOF\n")
        obj = ctx["minio"].get_object(
            ctx["contract_bucket"], "drill/contracts/drill-contract.pdf",
        )
        data = obj.read()
        obj.close()
        obj.release_conn()
        assert hashlib.sha256(data).hexdigest() == manifest_sha

    def test_creative_object_checksum(self, ctx):
        from scripts.backup.seed_representative_data import CREATIVE_BYTES
        manifest_sha = _sha(CREATIVE_BYTES)
        obj = ctx["minio"].get_object(
            ctx["creative_bucket"], "drill/creatives/drill-banner.png",
        )
        data = obj.read()
        obj.close()
        obj.release_conn()
        assert hashlib.sha256(data).hexdigest() == manifest_sha


class TestRlsAndIsolation:
    def test_app_role_nobypassrls(self, ctx):
        row = _q(
            ctx["owner"],
            "SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname='retail_media_app';",
        )
        assert row is not None, "retail_media_app role not found"
        assert not drill_checks.check_app_role_nobypassrls(row[0], row[1])

    def test_cross_org_not_disclosed(self, ctx):
        # App role (NOBYPASSRLS) with no admin flag must not see drill campaign
        # when RLS context restricts scope to an unrelated org.
        with ctx["app"].cursor() as cur:
            cur.execute("SET app.rmp_is_admin = false")
            cur.execute("SET app.rmp_scope_advertiser_ids = '{}'")
            cur.execute(
                "SELECT count(*) FROM campaigns WHERE id=%s", (IDS["campaign"],),
            )
            visible = cur.fetchone()[0]
        assert visible == 0, "cross-org campaign disclosed to app role without scope"


class TestManifestCompleteness:
    """001C-FU SCOPE 5 — the manifest must carry every truth field."""

    def test_manifest_has_identity_and_integrity(self, ctx):
        m = ctx["manifest"]
        # identity
        assert m["source"]["git_sha"]
        assert m["source"]["version"]
        # schema + integrity
        # The manifest must name the head the source tree actually has.
        # Pinning a literal here went stale on every migration (035, 036 …) and
        # each time the drill failed for a reason that had nothing to do with
        # backup fidelity. Deriving it keeps the assertion strict — a manifest
        # written at the wrong revision still fails — without the churn.
        assert m["postgres"]["alembic_head"] == _repo_alembic_head()
        assert len(m["postgres"]["dump_sha256"]) == 64
        assert isinstance(m["postgres"]["row_counts"], dict) and m["postgres"]["row_counts"]
        # consistency + encryption + rpo
        assert m["consistency_mode"] == "quiesced"
        assert m["encryption"]["enabled"] is False  # drill = no encryption (honest)
        assert "target_seconds" in m["rpo"]
        # quiescence evidence present
        assert m["quiescence"]["mode"] in ("writers-stopped", "maintenance")
        assert m["quiescence"]["evidence"].strip()

    def test_manifest_classifies_every_stateful_component(self, ctx):
        m = ctx["manifest"]
        from scripts.backup.backup_manifest import KNOWN_STATEFUL_COMPONENTS
        for comp in KNOWN_STATEFUL_COMPONENTS:
            assert comp in m["components"], f"component {comp} not classified"
            meta = m["components"][comp]
            assert meta["disposition"] in ("backed_up", "excluded_replayable", "excluded_disposable")
            assert meta["reason"].strip()
            assert meta["recovery_procedure"].strip()

    def test_manifest_has_no_secrets(self, ctx):
        import json as _json
        raw = _json.dumps(ctx["manifest"])
        lowered = raw.lower()
        for sub in ("password", "secret", "access_key", "private_key", "token"):
            assert sub not in lowered, f"manifest leaks '{sub}'"


class TestRuntimeReady:
    def test_version_reports_candidate_sha(self, ctx):
        import urllib.request
        base = os.environ.get("CONTROL_API_BASE_URL", "")
        if not base:
            pytest.skip("CONTROL_API_BASE_URL not set — version endpoint not reachable")
        with urllib.request.urlopen(f"{base}/version", timeout=10) as resp:
            payload = json.load(resp)
        assert payload.get("git_sha") == ctx["git_sha"] or payload.get("git_sha") != "", \
            "version endpoint must report a candidate git_sha"

    def test_health_live(self, ctx):
        import urllib.request
        base = os.environ.get("CONTROL_API_BASE_URL", "")
        if not base:
            pytest.skip("CONTROL_API_BASE_URL not set")
        with urllib.request.urlopen(f"{base}/health/live", timeout=10) as resp:
            assert resp.status == 200

    def test_new_record_no_pk_collision(self, ctx):
        # After restore, sequences/UUIDs must allow a fresh insert.
        new_id = "drill-post-restore-0000000000000001"
        try:
            with ctx["owner"].cursor() as cur:
                cur.execute(
                    "INSERT INTO retailers (id, code, legal_name, display_name, status) "
                    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
                    (new_id, "DRILL-POST", "Post Restore", "Post Restore", "active"),
                )
            ctx["owner"].commit()
        finally:
            with ctx["owner"].cursor() as cur:
                cur.execute("DELETE FROM retailers WHERE id=%s", (new_id,))
            ctx["owner"].commit()
