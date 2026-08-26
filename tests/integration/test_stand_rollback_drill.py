"""
LOCAL-DEV-STAND-001-FU-IDENTITY-SMOKE — migration-aware rollback drill.

Proves, in a disposable environment that never touches the running stand, the
claim the rollback design rests on:

  * the previous release's image cannot migrate a database that has already
    moved to the new revision — ``alembic upgrade head`` fails with
    "Can't locate revision identified by <head>", so putting the old images
    back is NOT a rollback;
  * therefore a schema-changing update must take a verified dump first, and the
    rollback must restore it — after which the old schema head and the row
    counts are back.

Both halves run the real ``local_stand.dump_database`` / ``restore_database``
functions against a throwaway postgres named for a throwaway project, so the
drill exercises the shipped code rather than a copy of it.

Opt-in: RUN_STAND_ROLLBACK_DRILL=1 (needs docker and the repo's alembic).
"""

from __future__ import annotations

import importlib.util
import os
import stat
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "scripts" / "deploy" / "local_stand.py"

RUN = os.environ.get("RUN_STAND_ROLLBACK_DRILL") == "1"
pytestmark = pytest.mark.skipif(
    not RUN, reason="RUN_STAND_ROLLBACK_DRILL=1 not set (needs docker)")

DRILL_PROJECT = "rmp-rollback-drill"
CONTAINER = f"{DRILL_PROJECT}-postgres-1"
OWNER = "retail_media_owner"
OWNER_PW = "retail_media_owner_pass"
DB = "retail_media_platform"
PORT = "55432"
OLD_HEAD = "035"
NEW_HEAD = "036"


def _sh(cmd: list[str], check: bool = True, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, check=check, **kw)


def _psql(sql: str) -> str:
    p = _sh(["docker", "exec", CONTAINER, "psql", "-U", OWNER, "-d", DB, "-tA", "-c", sql],
            check=False)
    return (p.stdout or "").strip()


def _alembic(revision: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DATABASE_URL"] = f"postgresql://{OWNER}:{OWNER_PW}@localhost:{PORT}/{DB}"
    return subprocess.run(
        ["alembic", "upgrade", revision] if revision != "downgrade"
        else ["alembic", "downgrade", "-1"],
        cwd=REPO_ROOT / "apps" / "control-api",
        capture_output=True, text=True, env=env, check=False,
    )


@pytest.fixture(scope="module")
def stand_module():
    spec = importlib.util.spec_from_file_location("local_stand_drill", TOOL)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["local_stand_drill"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def drill_db(tmp_path_factory, stand_module):
    """A throwaway postgres, migrated to the OLD head with data in it."""
    _sh(["docker", "rm", "-f", CONTAINER], check=False)
    _sh(["docker", "run", "-d", "--name", CONTAINER,
         "-e", f"POSTGRES_USER={OWNER}", "-e", f"POSTGRES_PASSWORD={OWNER_PW}",
         "-e", f"POSTGRES_DB={DB}", "-p", f"127.0.0.1:{PORT}:5432",
         "postgres:16-alpine"])
    for _ in range(60):
        if _sh(["docker", "exec", CONTAINER, "pg_isready", "-U", OWNER, "-d", DB],
               check=False).returncode == 0:
            break
        time.sleep(1)
    else:
        pytest.fail("drill postgres never became ready")

    assert _alembic(OLD_HEAD).returncode == 0, "could not migrate the drill db to 035"
    seed = subprocess.run(
        [sys.executable, "apps/control-api/seed.py"],
        cwd=REPO_ROOT, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT),
             "DATABASE_URL": f"postgresql+asyncpg://{OWNER}:{OWNER_PW}@localhost:{PORT}/{DB}"},
    )
    assert seed.returncode == 0, seed.stderr[-500:]

    # Point the real tooling at the throwaway project.
    stand_module.PROJECT = DRILL_PROJECT
    state = tmp_path_factory.mktemp("drill-state")
    stand_module.STATE_DIR = state
    def _drill_compose(*args, **kw):
        """Translate the tool's compose calls into the drill container.

        Only the two shapes the rollback path uses are supported: bringing
        postgres up (already up here) and running a command inside it. Anything
        else fails loudly rather than silently succeeding.
        """
        args = list(args)
        if args[:3] == ["up", "-d", "postgres"]:
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[:3] == ["exec", "-T", "postgres"]:
            return subprocess.run(["docker", "exec", CONTAINER, *args[3:]],
                                  capture_output=True, text=True, check=False)
        raise AssertionError(f"unexpected compose call in the drill: {args}")

    stand_module.compose = _drill_compose
    stand_module.wait_postgres_healthy = lambda timeout=180: None

    yield {"env": {"POSTGRES_OWNER_USER": OWNER, "POSTGRES_DB": DB}}

    _sh(["docker", "rm", "-f", CONTAINER], check=False)


class TestMigrationAwareRollbackDrill:

    def test_old_image_cannot_migrate_a_database_that_moved_on(self, drill_db):
        """The reason an image-only rollback is not a rollback."""
        assert _psql("SELECT version_num FROM alembic_version") == OLD_HEAD
        _psql(f"UPDATE alembic_version SET version_num='{NEW_HEAD}'")
        # 'the previous release' = the migration set without the new revision.
        new_file = REPO_ROOT / "apps" / "control-api" / "alembic" / "versions" / \
            "036_campaign_permission_split.py"
        hidden = new_file.with_suffix(".py.hidden")
        new_file.rename(hidden)
        try:
            result = _alembic("head")
            combined = (result.stdout or "") + (result.stderr or "")
            assert result.returncode != 0, "the old migration set should not accept head 036"
            assert f"Can't locate revision identified by '{NEW_HEAD}'" in combined, combined[-400:]
        finally:
            hidden.rename(new_file)
        _psql(f"UPDATE alembic_version SET version_num='{OLD_HEAD}'")

    def test_dump_is_private_checksummed_and_restores_schema_and_data(self, drill_db, stand_module):
        env = drill_db["env"]
        counts_before = stand_module.baseline_counts(env)
        assert counts_before, "baseline counts must be readable before an update"
        assert stand_module.db_schema_head(env) == OLD_HEAD

        dump_path, checksum = stand_module.dump_database(env, f"{OLD_HEAD}-to-{NEW_HEAD}")
        assert dump_path.exists() and dump_path.stat().st_size > 0
        assert stat.S_IMODE(dump_path.stat().st_mode) == 0o600, "dump must be 0600"
        sums = dump_path.with_name(dump_path.name + ".sha256")
        assert sums.exists() and checksum in sums.read_text()
        assert stat.S_IMODE(sums.stat().st_mode) == 0o600

        # The update happens: schema moves and data changes.
        assert _alembic(NEW_HEAD).returncode == 0
        assert stand_module.db_schema_head(env) == NEW_HEAD
        _psql("DELETE FROM campaign_status_history")
        _psql("DELETE FROM campaign_placements")
        _psql("DELETE FROM campaign_creatives")
        _psql("DELETE FROM campaign_flights")
        _psql("DELETE FROM campaigns")
        assert stand_module.baseline_counts(env)["campaigns"] == 0

        # The rollback the tool performs.
        stand_module.restore_database(env, dump_path, checksum)
        assert stand_module.db_schema_head(env) == OLD_HEAD, \
            "restoring the pre-update dump must bring the old schema head back"
        counts_after = stand_module.baseline_counts(env)
        assert counts_after == counts_before, \
            f"row counts differ after restore: {counts_before} != {counts_after}"

    def test_restore_refuses_a_tampered_dump(self, drill_db, stand_module):
        env = drill_db["env"]
        dump_path, checksum = stand_module.dump_database(env, "tamper")
        dump_path.write_bytes(dump_path.read_bytes() + b"tampered")
        with pytest.raises(SystemExit):
            stand_module.restore_database(env, dump_path, checksum)
