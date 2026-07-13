"""
Integration test: MinIO backup → restore drill (S-049).

Proves the full backup/restore cycle:
  upload test objects → backup → verify manifest → restore to target bucket →
  verify object count, content, and checksums.

Requires:
  - RUN_MINIO_INTEGRATION_TESTS=1
  - Local MinIO at MINIO_INTERNAL_ENDPOINT
  - Backup scripts (scripts/backup/minio_backup.py, scripts/restore/minio_restore.py)

Usage:
  RUN_MINIO_INTEGRATION_TESTS=1 python -m pytest tests/integration/test_minio_backup_restore.py -v

Skips silently when env is not set.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REQUIRE_ENV = os.environ.get("RUN_MINIO_INTEGRATION_TESTS", "") == "1"
SKIP_REASON = "RUN_MINIO_INTEGRATION_TESTS=1 not set."

REPO_ROOT = Path(os.path.dirname(__file__)).parent.parent.resolve()

BACKUP_SCRIPT = str(REPO_ROOT / "scripts" / "backup" / "minio_backup.py")
RESTORE_SCRIPT = str(REPO_ROOT / "scripts" / "restore" / "minio_restore.py")

SOURCE_BUCKET = "rmp-backup-test-source"
TARGET_BUCKET = "rmp-backup-test-target"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _minio_env() -> dict[str, str]:
    """Build env dict for MinIO SDK access using test credentials."""
    endpoint = os.environ.get("MINIO_INTERNAL_ENDPOINT", "localhost:9000")
    access = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    return {
        "MINIO_ENDPOINT": endpoint,
        "MINIO_ACCESS_KEY": access,
        "MINIO_SECRET_KEY": secret,
        "MINIO_INTERNAL_ENDPOINT": endpoint,
        "CREATIVE_STORAGE_BUCKET": SOURCE_BUCKET,
    }


def _create_test_key() -> tuple[str, str]:
    """Create a dedicated test access key for integration tests via mc."""
    endpoint = os.environ.get("MINIO_INTERNAL_ENDPOINT", "localhost:9000")
    access = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
    secret = os.environ.get("MINIO_SECRET_KEY", "minioadmin")
    test_access = "minio-backup-test"
    test_secret = "minio-backup-test-secret"

    # Check if mc is available
    mc_path = shutil.which("mc") or "/tmp/mc"
    if not Path(mc_path).exists():
        return access, secret  # fall back to root credentials

    try:
        subprocess.run(
            [mc_path, "alias", "set", "myminio", f"http://{endpoint}", access, secret],
            capture_output=True, timeout=10, check=False,
        )
        subprocess.run(
            [
                mc_path, "admin", "accesskey", "create", "myminio",
                "--access-key", test_access,
                "--secret-key", test_secret,
            ],
            capture_output=True, timeout=10, check=False,
        )
    except Exception:
        pass  # key may already exist

    return test_access, test_secret


def _minio_client(endpoint: str, access_key: str, secret_key: str):
    """Create a MinIO client."""
    from minio import Minio
    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def minio_env():
    """Check MinIO availability and set up test buckets. Skip if not available."""
    if not REQUIRE_ENV:
        pytest.skip(SKIP_REASON)

    endpoint = os.environ.get("MINIO_INTERNAL_ENDPOINT", "localhost:9000")

    # Get working credentials
    test_access, test_secret = _create_test_key()

    # Verify connectivity
    from minio import Minio
    try:
        client = Minio(endpoint, access_key=test_access, secret_key=test_secret, secure=False)
        # Quick health check
        client.list_buckets()
    except Exception as exc:
        pytest.skip(f"MinIO not reachable at {endpoint}: {exc}")

    env = {
        "MINIO_INTERNAL_ENDPOINT": endpoint,
        "MINIO_ACCESS_KEY": test_access,
        "MINIO_SECRET_KEY": test_secret,
        "CREATIVE_STORAGE_BUCKET": SOURCE_BUCKET,
    }

    # Create source bucket
    try:
        if not client.bucket_exists(SOURCE_BUCKET):
            client.make_bucket(SOURCE_BUCKET)
    except Exception:
        pass

    # Ensure target bucket doesn't exist (clean state)
    try:
        if client.bucket_exists(TARGET_BUCKET):
            # Remove all objects first
            objs = list(client.list_objects(TARGET_BUCKET, recursive=True))
            for obj in objs:
                client.remove_object(TARGET_BUCKET, obj.object_name)
            client.remove_bucket(TARGET_BUCKET)
    except Exception:
        pass

    yield env

    # Cleanup: remove both test buckets
    try:
        for bucket in (SOURCE_BUCKET, TARGET_BUCKET):
            if client.bucket_exists(bucket):
                objs = list(client.list_objects(bucket, recursive=True))
                for obj in objs:
                    client.remove_object(bucket, obj.object_name)
                client.remove_bucket(bucket)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMinioBackupRestore:
    """End-to-end backup → manifest verify → restore drill."""

    def test_skip_without_env(self, minio_env):
        """Clean skip when RUN_MINIO_INTEGRATION_TESTS is not set."""
        assert REQUIRE_ENV  # already skipped by fixture if not set

    def test_full_backup_restore_cycle(self, minio_env):
        """Upload test objects → backup → restore to target → verify."""

        endpoint = minio_env["MINIO_INTERNAL_ENDPOINT"]
        access = minio_env["MINIO_ACCESS_KEY"]
        secret = minio_env["MINIO_SECRET_KEY"]

        client = _minio_client(endpoint, access, secret)

        # 1. Upload 3 test objects with different keys and sizes
        test_objects: dict[str, bytes] = {
            "org-a/asset-1/banner.png": b"A" * 500,
            "org-b/asset-2/video.mp4": b"B" * 2048,
            "org-c/asset-3/icon.webp": b"C" * 100,
        }

        for key, data in test_objects.items():
            import io
            client.put_object(
                SOURCE_BUCKET, key,
                io.BytesIO(data), len(data),
            )

        # Verify they exist
        source_objects = list(client.list_objects(SOURCE_BUCKET, recursive=True))
        assert len(source_objects) == 3, f"Expected 3 test objects, got {len(source_objects)}"

        # 2. Run backup script
        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "minio-backups"
            backup_env = {
                **os.environ,
                "MINIO_ENDPOINT": endpoint,
                "MINIO_ACCESS_KEY": access,
                "MINIO_SECRET_KEY": secret,
                "MINIO_BUCKET": SOURCE_BUCKET,
                "BACKUP_DIR": str(backup_dir),
            }
            result = subprocess.run(
                [sys.executable, BACKUP_SCRIPT],
                env=backup_env, capture_output=True, text=True, timeout=60,
            )
            assert result.returncode == 0, f"Backup failed:\n{result.stderr}\n{result.stdout}"

            # Verify no secrets in output
            assert secret not in result.stdout, "Secret key leaked in backup stdout"
            assert access not in result.stdout, "Access key leaked in backup stdout"

            # Find backup subdirectory
            backup_dirs = sorted(backup_dir.iterdir())
            assert len(backup_dirs) >= 1, "No backup directory created"
            bdir = backup_dirs[0]

            # 3. Verify manifest
            manifest_path = bdir / "manifest.json"
            assert manifest_path.exists(), "manifest.json not found"

            with open(manifest_path) as f:
                manifest = json.load(f)

            assert manifest["bucket"] == SOURCE_BUCKET
            assert manifest["object_count"] == 3
            assert manifest["total_size_bytes"] == sum(len(d) for d in test_objects.values())
            assert len(manifest["objects"]) == 3
            assert "generated_at" in manifest
            assert "backup_timestamp" in manifest

            # Each object has key, size, sha256
            manifest_keys = {obj["key"] for obj in manifest["objects"]}
            assert manifest_keys == set(test_objects.keys())

            for mobj in manifest["objects"]:
                expected_data = test_objects[mobj["key"]]
                assert mobj["size"] == len(expected_data)
                assert mobj["sha256"] == hashlib.sha256(expected_data).hexdigest()

            # 4. Verify data files exist with correct content
            data_dir = bdir / "data"
            for key, expected_data in test_objects.items():
                data_file = data_dir / key
                assert data_file.exists(), f"Data file missing: {data_file}"
                actual = data_file.read_bytes()
                assert actual == expected_data, f"Content mismatch for {key}"

            # 5. Check mode
            check_result = subprocess.run(
                [sys.executable, RESTORE_SCRIPT, str(bdir), "--check"],
                env={**os.environ, "MINIO_ENDPOINT": endpoint,
                     "MINIO_ACCESS_KEY": access, "MINIO_SECRET_KEY": secret,
                     "MINIO_BUCKET": TARGET_BUCKET},
                capture_output=True, text=True, timeout=60,
            )
            assert check_result.returncode == 0, f"Check failed:\n{check_result.stderr}\n{check_result.stdout}"
            assert "VALID" in check_result.stdout

            # 6. Dry-run
            dry_result = subprocess.run(
                [sys.executable, RESTORE_SCRIPT, str(bdir), "--dry-run", "--verbose"],
                env={**os.environ, "MINIO_ENDPOINT": endpoint,
                     "MINIO_ACCESS_KEY": access, "MINIO_SECRET_KEY": secret,
                     "MINIO_BUCKET": TARGET_BUCKET},
                capture_output=True, text=True, timeout=60,
            )
            assert dry_result.returncode == 0, f"Dry-run failed:\n{dry_result.stderr}\n{dry_result.stdout}"

            # 7. Restore to target bucket
            restore_result = subprocess.run(
                [sys.executable, RESTORE_SCRIPT, str(bdir)],
                env={**os.environ,
                     "MINIO_ENDPOINT": endpoint,
                     "MINIO_ACCESS_KEY": access, "MINIO_SECRET_KEY": secret,
                     "MINIO_BUCKET": TARGET_BUCKET,
                     "REQUIRE_RESTORE_CONFIRMATION": "yes"},
                capture_output=True, text=True, timeout=60,
            )
            assert restore_result.returncode == 0, (
                f"Restore failed:\n{restore_result.stderr}\n{restore_result.stdout}"
            )

            # Verify no secrets in restore output
            assert secret not in restore_result.stdout, "Secret key leaked in restore stdout"

            # 8. Verify target bucket has all objects with correct content
            target_objects = list(client.list_objects(TARGET_BUCKET, recursive=True))
            assert len(target_objects) == 3, f"Expected 3 objects in target, got {len(target_objects)}"

            for key, expected_data in test_objects.items():
                response = client.get_object(TARGET_BUCKET, key)
                actual = response.read()
                response.close()
                response.release_conn()
                assert actual == expected_data, f"Content mismatch for {key} in target"

            # Verify restore summary contains SUCCESS
            assert "SUCCESS" in restore_result.stdout

    def test_backup_empty_bucket(self, minio_env):
        """Backup of an empty bucket should succeed with 0 objects."""
        endpoint = minio_env["MINIO_INTERNAL_ENDPOINT"]
        access = minio_env["MINIO_ACCESS_KEY"]
        secret = minio_env["MINIO_SECRET_KEY"]

        empty_bucket = "rmp-backup-test-empty"
        client = _minio_client(endpoint, access, secret)

        try:
            if not client.bucket_exists(empty_bucket):
                client.make_bucket(empty_bucket)

            with tempfile.TemporaryDirectory() as tmpdir:
                backup_dir = Path(tmpdir) / "minio-empty"
                result = subprocess.run(
                    [sys.executable, BACKUP_SCRIPT],
                    env={**os.environ,
                         "MINIO_ENDPOINT": endpoint,
                         "MINIO_ACCESS_KEY": access,
                         "MINIO_SECRET_KEY": secret,
                         "MINIO_BUCKET": empty_bucket,
                         "BACKUP_DIR": str(backup_dir)},
                    capture_output=True, text=True, timeout=60,
                )
                assert result.returncode == 0, f"Empty backup failed:\n{result.stderr}"

                # Verify manifest
                backup_dirs = sorted(backup_dir.iterdir())
                assert len(backup_dirs) >= 1
                with open(backup_dirs[0] / "manifest.json") as f:
                    manifest = json.load(f)
                assert manifest["object_count"] == 0
                assert manifest["total_size_bytes"] == 0
                assert manifest["objects"] == []

        finally:
            try:
                if client.bucket_exists(empty_bucket):
                    client.remove_bucket(empty_bucket)
            except Exception:
                pass

    def test_restore_requires_confirmation(self, minio_env):
        """Restore without REQUIRE_RESTORE_CONFIRMATION should fail."""
        endpoint = minio_env["MINIO_INTERNAL_ENDPOINT"]
        access = minio_env["MINIO_ACCESS_KEY"]
        secret = minio_env["MINIO_SECRET_KEY"]

        # Create a minimal backup
        client = _minio_client(endpoint, access, secret)
        import io
        client.put_object(SOURCE_BUCKET, "test/key.dat", io.BytesIO(b"hello"), 5)

        with tempfile.TemporaryDirectory() as tmpdir:
            backup_dir = Path(tmpdir) / "minio-confirm"
            subprocess.run(
                [sys.executable, BACKUP_SCRIPT],
                env={**os.environ,
                     "MINIO_ENDPOINT": endpoint,
                     "MINIO_ACCESS_KEY": access,
                     "MINIO_SECRET_KEY": secret,
                     "MINIO_BUCKET": SOURCE_BUCKET,
                     "BACKUP_DIR": str(backup_dir)},
                capture_output=True, timeout=60,
            )
            backup_dirs = sorted(backup_dir.iterdir())
            assert len(backup_dirs) >= 1

            # Attempt restore WITHOUT confirmation
            result = subprocess.run(
                [sys.executable, RESTORE_SCRIPT, str(backup_dirs[0])],
                env={**os.environ,
                     "MINIO_ENDPOINT": endpoint,
                     "MINIO_ACCESS_KEY": access,
                     "MINIO_SECRET_KEY": secret,
                     "MINIO_BUCKET": TARGET_BUCKET},
                capture_output=True, text=True, timeout=60,
            )
            assert result.returncode == 1
            assert "REQUIRE_RESTORE_CONFIRMATION" in result.stdout
