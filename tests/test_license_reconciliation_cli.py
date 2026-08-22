"""EPIC-L-SEAT-LEDGER-001A4 — CLI reconciliation fail-closed proof.

The --apply path must refuse (exit 2) in a non-dev environment BEFORE touching
the database. DRY RUN is always allowed (read-only).
"""

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "dev" / "license-reconcile-seats.py"


def _run_cli(*args, environment: str, flag: str = "") -> subprocess.CompletedProcess:
    env = {**os.environ, "ENVIRONMENT": environment}
    if flag:
        env["LICENSE_DEV_INGEST_ENABLED"] = flag
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        env=env,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )


def test_apply_refused_in_production():
    result = _run_cli("--apply", environment="production")
    assert result.returncode == 2, result.stderr
    assert "refused" in result.stderr


def test_apply_refused_in_dev_without_flag():
    result = _run_cli("--apply", environment="dev", flag="")
    assert result.returncode == 2, result.stderr
    assert "refused" in result.stderr


def test_apply_allowed_in_dev_with_flag():
    # Should get past the env gate (may fail later on DB, but NOT with code 2
    # for env refusal). Without a reachable DB the runtime error path also
    # returns 2 — so assert it did not print the "refused" message.
    result = _run_cli("--apply", environment="dev", flag="true")
    assert "refused" not in result.stderr
