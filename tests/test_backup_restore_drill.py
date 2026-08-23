"""Negative matrix for the backup/restore drill (SCOPE G).

Unit-level (no DB, no MinIO). Each item maps to a specific guard that must
fail-closed. These run in the normal python-tests job.

SCOPE G items:
  1. corrupted DB dump → refuse
  2. tampered manifest checksum → refuse
  3. missing MinIO object → verification red
  4. swapped object content → checksum mismatch
  5. source == target → refuse before mutation
  6. non-empty target → refuse
  7. wrong alembic head → refuse
  8. app role BYPASSRLS/superuser → refuse acceptance
  9. missing backup component → incomplete backup
  10. production mode without encryption → fail closed
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.backup import backup_manifest, drill_checks  # noqa: E402
from scripts.restore import isolated_restore  # noqa: E402


def _make_backup(tmp_path: Path) -> tuple[Path, dict]:
    """Build a minimal, valid on-disk backup + manifest for negative tests."""
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    dump = run_dir / "postgres" / "rmp.dump"
    dump.parent.mkdir(parents=True)
    dump.write_bytes(b"DUMP-BYTES-0001")
    dump_sha = backup_manifest.sha256_file(dump)

    obj_dir = run_dir / "minio" / "bucket-a"
    obj_dir.mkdir(parents=True)
    obj = obj_dir / "drill" / "creatives" / "banner.png"
    obj.parent.mkdir(parents=True)
    obj.write_bytes(b"OBJECT-BYTES-0001")
    obj_sha = backup_manifest.sha256_file(obj)

    manifest = backup_manifest.build_manifest(
        backup_dir=run_dir,
        git_sha="c" * 40,
        version="test",
        alembic_head="034",
        postgres_server_version="16",
        minio_server_version="RELEASE.test",
        dump_file=Path("postgres/rmp.dump"),
        dump_sha256=dump_sha,
        row_counts={"campaigns": 1},
        buckets={
            "bucket-a": {
                "object_count": 1,
                "total_size_bytes": len(b"OBJECT-BYTES-0001"),
                "objects": [
                    {"key": "drill/creatives/banner.png", "size": len(b"OBJECT-BYTES-0001"),
                     "sha256": obj_sha},
                ],
            }
        },
        backup_tool_version="test",
        environment="drill",
        quiesce_mode="writers-stopped",
        quiesce_evidence="test fixture: no writers by construction",
    )
    backup_manifest.write_manifest(manifest, run_dir / "backup-manifest.json")
    return run_dir, manifest


class TestNegativeMatrix:
    def test_1_corrupted_dump_refused(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        dump = run_dir / manifest["postgres"]["dump_file"]
        dump.write_bytes(b"CORRUPTED")
        problems = backup_manifest.verify_manifest_against_disk(manifest, run_dir)
        assert any("dump checksum mismatch" in p for p in problems)

    def test_2_tampered_manifest_checksum_refused(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        manifest["postgres"]["dump_sha256"] = "0" * 64
        problems = backup_manifest.verify_manifest_against_disk(manifest, run_dir)
        assert any("dump checksum mismatch" in p for p in problems)

    def test_3_missing_object_verification_red(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        obj = run_dir / "minio" / "bucket-a" / "drill" / "creatives" / "banner.png"
        obj.unlink()
        problems = backup_manifest.verify_manifest_against_disk(manifest, run_dir)
        assert any("object missing" in p for p in problems)

    def test_4_swapped_object_content_mismatch(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        obj = run_dir / "minio" / "bucket-a" / "drill" / "creatives" / "banner.png"
        obj.write_bytes(b"DIFFERENT-CONTENT")
        problems = backup_manifest.verify_manifest_against_disk(manifest, run_dir)
        assert any("object checksum mismatch" in p for p in problems)

    def test_5_source_equals_target_refused(self):
        problems = isolated_restore.guard_source_target_distinct(
            source_dsn="postgresql://u:p@db:5432/x",
            target_dsn="postgresql://u:p@db:5432/x",
            source_minio_endpoint="minio:9000",
            target_minio_endpoint="minio:9000",
        )
        assert len(problems) == 2

    def test_5b_source_equals_target_allowed_when_distinct(self):
        problems = isolated_restore.guard_source_target_distinct(
            source_dsn="postgresql://u:p@db:5432/x",
            target_dsn="postgresql://u:p@db2:5432/x",
            source_minio_endpoint="minio:9000",
            target_minio_endpoint="minio2:9000",
        )
        assert problems == []

    def test_6_nonempty_target_refused(self):
        problems = isolated_restore.guard_nonempty_target(target_is_empty=False, allow_nonempty=False)
        assert problems
        assert isolated_restore.guard_nonempty_target(True, False) == []
        assert isolated_restore.guard_nonempty_target(False, True) == []

    def test_7_wrong_alembic_head_refused(self):
        problems = drill_checks.check_alembic_head("033", "034")
        assert problems

    def test_8_app_role_bypassrls_refused(self):
        problems = drill_checks.check_app_role_nobypassrls(False, True)
        assert any("BYPASSRLS" in p for p in problems)
        problems = drill_checks.check_app_role_nobypassrls(True, False)
        assert any("superuser" in p for p in problems)

    def test_9_missing_component_incomplete(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        del manifest["minio"]
        with pytest.raises(ValueError):
            backup_manifest.validate_manifest(manifest)

    def test_9b_missing_postgres_incomplete(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        del manifest["postgres"]
        with pytest.raises(ValueError):
            backup_manifest.validate_manifest(manifest)

    def test_10_production_no_encryption_fail_closed(self):
        problems = drill_checks.check_production_encryption("production", False)
        assert problems
        assert drill_checks.check_production_encryption("production", True) == []
        assert drill_checks.check_production_encryption("pilot", False) == []


class TestManifestSecretSafety:
    def test_no_secrets_serialized(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        # Inject a credential-like value deep in the structure.
        manifest["postgres"]["row_counts"] = {"campaigns": 1, "password": 1}
        with pytest.raises(ValueError):
            backup_manifest.validate_manifest(manifest)

    def test_secret_value_rejected(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        # A DSN with an embedded password is credential material → must be rejected.
        manifest["minio"]["buckets"]["bucket-a"]["objects"][0]["key"] = (
            "postgresql://admin:x1y2z3@db.internal:5432/leak"
        )
        with pytest.raises(ValueError):
            backup_manifest.validate_manifest(manifest)

    def test_sensitive_key_rejected(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        manifest["minio"]["access_key"] = "AKIAEXAMPLE"
        with pytest.raises(ValueError):
            backup_manifest.validate_manifest(manifest)


class TestComponentClassification:
    """001C-FU SCOPE 1 — NATS and every stateful component must be classified."""

    def test_nats_classified_replayable(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        comps = manifest["components"]
        assert "nats" in comps, "NATS must be explicitly classified"
        nats = comps["nats"]
        assert nats["disposition"] == "excluded_replayable"
        assert nats["reason"].strip()
        assert nats["recovery_procedure"].strip()

    def test_redis_classified_disposable(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        assert manifest["components"]["redis"]["disposition"] == "excluded_disposable"

    def test_manifest_cannot_silently_forget_nats(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        del manifest["components"]["nats"]
        with pytest.raises(ValueError) as exc:
            backup_manifest.validate_manifest(manifest)
        assert "nats" in str(exc.value)

    def test_manifest_cannot_silently_forget_redis(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        del manifest["components"]["redis"]
        with pytest.raises(ValueError) as exc:
            backup_manifest.validate_manifest(manifest)
        assert "redis" in str(exc.value)

    def test_excluded_component_requires_recovery_procedure(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        manifest["components"]["nats"]["recovery_procedure"] = ""
        with pytest.raises(ValueError) as exc:
            backup_manifest.validate_manifest(manifest)
        assert "recovery_procedure" in str(exc.value)

    def test_invalid_disposition_rejected(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        manifest["components"]["nats"]["disposition"] = "backed_up_sometimes"
        with pytest.raises(ValueError):
            backup_manifest.validate_manifest(manifest)


class TestQuiescenceEnforcement:
    """001C-FU SCOPE 2 — quiesced backup must carry proven quiescence evidence."""

    def test_production_backup_without_quiescence_refused(self):
        problems = backup_manifest.check_quiescence_evidence(
            "production", "none", "",
        )
        assert problems

    def test_production_backup_with_maintenance_mode_ok(self):
        problems = backup_manifest.check_quiescence_evidence(
            "production", "maintenance", "maintenance flag set via ops API",
        )
        assert problems == []

    def test_production_backup_writers_stopped_with_evidence_ok(self):
        problems = backup_manifest.check_quiescence_evidence(
            "pilot", "writers-stopped", "docker compose stop control-api device-gateway",
        )
        assert problems == []

    def test_production_backup_empty_evidence_refused(self):
        problems = backup_manifest.check_quiescence_evidence(
            "production", "maintenance", "",
        )
        assert problems

    def test_manifest_without_quiescence_evidence_refused(self, tmp_path):
        run_dir, manifest = _make_backup(tmp_path)
        # Simulate a "pilot" manifest forged without quiescence evidence.
        manifest["source"]["environment"] = "pilot"
        manifest["quiescence"] = {"mode": "none", "evidence": ""}
        with pytest.raises(ValueError):
            backup_manifest.validate_manifest(manifest)

    def test_drill_environment_no_evidence_needed(self):
        # dev/drill is quiesced-by-construction — no evidence required.
        assert backup_manifest.check_quiescence_evidence("drill", "", "") == []
        assert backup_manifest.check_quiescence_evidence("dev", "", "") == []
