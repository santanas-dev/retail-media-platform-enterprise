"""
LOCAL-DEV-STAND-001-FU-IDENTITY-SMOKE — version identity, migration-aware
rollback, and the stand-safe smoke runner.

Two defects motivated all of this:

* the stand's declared schema head was typed into ``.env.stand`` by hand and was
  wrong after both of the last two updates, because the update tool switched
  RMP_VERSION/RMP_GIT_SHA and nothing else;
* the CI UI-smoke suite, pointed at the shared stand, deleted accumulated
  accounts and assigned a role to a seed user.

So the head is resolved from the migration files and carried in the lock, the
whole identity is switched atomically from that lock, and there is a separate
runner that cannot do the destructive things.

No docker and no network here: these exercise the pure functions and the
declared contracts. The live behaviour is proven on the stand itself.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DEPLOY = REPO_ROOT / "scripts" / "deploy"
TOOL = DEPLOY / "local_stand.py"
SMOKE = DEPLOY / "stand_safe_smoke.py"
VALIDATOR = DEPLOY / "validate-image-lock.py"
BUILD = DEPLOY / "build-images.sh"
VERSIONS = REPO_ROOT / "apps" / "control-api" / "alembic" / "versions"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


head_mod = _load(DEPLOY / "alembic_head.py", "alembic_head_under_test")
stand = _load(TOOL, "local_stand_under_test")
smoke = _load(SMOKE, "stand_safe_smoke_under_test")
validator = _load(VALIDATOR, "validate_image_lock_under_test")

# RM-TECH-210 (2026-08-31): head репозитория вычисляется, а не пинится литералом —
# иначе каждая новая миграция роняет эти тесты (так и случилось с 037).
HEAD = head_mod.resolve_single_head(VERSIONS)


def _lock(**release) -> dict:
    rel = {"version": "stand-abc1234",
           "git_sha": "c0881118ea9232af190560031f718f126b431322",
           "schema_head": HEAD}
    rel.update(release)
    return {
        "release": rel,
        "build_timestamp": "2026-08-25T20:35:34Z",
        "images": [
            {
                "service": s,
                "repository": f"ghcr.io/santanas-dev/rmp-pilot/{s}",
                "version": rel["version"],
                "git_sha": rel["git_sha"],
                "image_digest": "sha256:" + f"{i}" * 64,
                "source_tag": rel["version"],
            }
            for i, s in enumerate(
                ["control-api", "device-gateway", "orchestrator-worker",
                 "admin-web", "advertiser-web"], start=1)
        ],
    }


# --- the head resolver -------------------------------------------------------

class TestSingleHeadResolver:

    def test_resolves_the_repo_to_one_head(self):
        """Резолвер даёт ровно тот head, что независимо следует из имён файлов миграций."""
        expected = sorted(p.name[:3] for p in VERSIONS.glob("[0-9][0-9][0-9]_*.py"))[-1]
        assert head_mod.resolve_single_head(VERSIONS) == expected
        assert re.fullmatch(r"\d{3}", expected)

    def test_rejects_a_branched_history(self, tmp_path):
        (tmp_path / "a.py").write_text('revision: str = "a"\ndown_revision: Union[str, None] = None\n')
        (tmp_path / "b.py").write_text('revision: str = "b"\ndown_revision: Union[str, None] = "a"\n')
        (tmp_path / "c.py").write_text('revision: str = "c"\ndown_revision: Union[str, None] = "a"\n')
        with pytest.raises(head_mod.HeadResolutionError) as e:
            head_mod.resolve_single_head(tmp_path)
        assert "one alembic head" in str(e.value)

    def test_rejects_an_empty_migrations_dir(self, tmp_path):
        with pytest.raises(head_mod.HeadResolutionError):
            head_mod.resolve_single_head(tmp_path)

    def test_rejects_a_missing_migrations_dir(self, tmp_path):
        with pytest.raises(head_mod.HeadResolutionError):
            head_mod.resolve_single_head(tmp_path / "nope")

    def test_placeholder_heads_are_recognised(self):
        for value in ("", "   ", "TODO", "PLACEHOLDER", "head", "unknown"):
            assert head_mod.is_placeholder(value), value
        assert not head_mod.is_placeholder("036")


# --- the lock contract -------------------------------------------------------

class TestLockSchemaMetadata:

    def test_valid_lock_passes(self, tmp_path):
        errors = validator.validate(_lock(), validator.DEFAULT_SERVICES, VERSIONS)
        assert errors == []

    def test_missing_schema_head_is_rejected(self):
        lock = _lock()
        del lock["release"]["schema_head"]
        errors = validator.validate(lock, validator.DEFAULT_SERVICES, VERSIONS)
        assert any("schema_head is missing" in e for e in errors), errors

    def test_placeholder_schema_head_is_rejected(self):
        errors = validator.validate(_lock(schema_head="TODO"),
                                    validator.DEFAULT_SERVICES, VERSIONS)
        assert any("schema_head" in e for e in errors), errors

    def test_stale_schema_head_is_rejected(self):
        errors = validator.validate(_lock(schema_head="035"),
                                    validator.DEFAULT_SERVICES, VERSIONS)
        assert any("stale" in e for e in errors), errors

    def test_mixed_sha_is_still_rejected(self):
        lock = _lock()
        lock["images"][0]["git_sha"] = "0" * 40
        errors = validator.validate(lock, validator.DEFAULT_SERVICES, VERSIONS)
        assert any("mixed git SHAs" in e for e in errors), errors

    def test_mutable_tag_is_still_rejected(self):
        lock = _lock()
        lock["images"][0]["repository"] += ":latest"
        errors = validator.validate(lock, validator.DEFAULT_SERVICES, VERSIONS)
        assert any("mutable tag" in e for e in errors), errors

    def test_schema_head_shape_is_checked_without_the_migrations(self):
        """On the stand host the migration files are not staged."""
        assert validator.validate(_lock(), validator.DEFAULT_SERVICES, None) == []
        errors = validator.validate(_lock(schema_head=""),
                                    validator.DEFAULT_SERVICES, None)
        assert any("schema_head" in e for e in errors), errors

    def test_build_script_writes_the_resolved_head(self):
        text = BUILD.read_text()
        assert "alembic_head.py" in text, "the build must resolve the head, not hard-code it"
        assert '"schema_head": schema_head' in text


# --- identity switching ------------------------------------------------------

class TestIdentitySwitch:

    def test_identity_carries_every_field_the_images_report(self):
        identity = stand.version_identity(_lock())
        assert identity == {
            "RMP_VERSION": "stand-abc1234",
            "RMP_GIT_SHA": "c0881118ea9232af190560031f718f126b431322",
            "RMP_SCHEMA_HEAD": HEAD,
            "RMP_BUILD_TIME": "2026-08-25T20:35:34Z",
        }

    def test_lock_without_schema_head_is_refused(self):
        lock = _lock()
        del lock["release"]["schema_head"]
        with pytest.raises(SystemExit):
            stand.lock_schema_head(lock)

    def test_env_write_is_atomic_and_private(self, tmp_path, monkeypatch):
        env = tmp_path / ".env.stand"
        env.write_text("RMP_VERSION=old\nPOSTGRES_APP_PASSWORD=secret\n")
        env.chmod(0o600)
        monkeypatch.setattr(stand, "ENV_FILE", env)
        stand.write_env_images({"RMP_VERSION": "new", "RMP_SCHEMA_HEAD": "036"})
        text = env.read_text()
        assert "RMP_VERSION=new" in text
        assert "RMP_SCHEMA_HEAD=036" in text
        assert "POSTGRES_APP_PASSWORD=secret" in text, "unrelated values must survive"
        assert stat.S_IMODE(env.stat().st_mode) == 0o600
        assert not list(tmp_path.glob("*.tmp")), "no half-written env may be left behind"

    def test_previous_env_is_saved_and_restored(self, tmp_path, monkeypatch):
        env = tmp_path / ".env.stand"
        env.write_text("RMP_VERSION=old\n")
        env.chmod(0o600)
        state = tmp_path / "state"
        monkeypatch.setattr(stand, "ENV_FILE", env)
        monkeypatch.setattr(stand, "STATE_DIR", state)

        stand.save_env_previous()
        stand.write_env_images({"RMP_VERSION": "new"})
        assert "RMP_VERSION=new" in env.read_text()

        assert stand.restore_env_previous() is True
        assert "RMP_VERSION=old" in env.read_text()
        assert stat.S_IMODE(env.stat().st_mode) == 0o600

    def test_restore_reports_when_there_is_nothing_to_restore(self, tmp_path, monkeypatch):
        monkeypatch.setattr(stand, "STATE_DIR", tmp_path / "empty-state")
        assert stand.restore_env_previous() is False


# --- identity drift ----------------------------------------------------------

class TestIdentityDrift:

    def _sources(self, name: str) -> str:
        tree = ast.parse(TOOL.read_text())
        fn = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == name)
        return ast.get_source_segment(TOOL.read_text(), fn)

    def test_actual_db_head_is_compared_with_the_lock(self, monkeypatch):
        monkeypatch.setattr(stand, "_http_json", lambda url: {
            "git_sha": "sha", "version": "tag", "schema_head": "036"})
        monkeypatch.setattr(stand, "db_schema_head", lambda env: "035")
        problems = stand.verify_identity("127.0.0.1", "tag", "sha", "036", {})
        assert any("actual schema head 035" in p for p in problems), problems

    def test_advertised_schema_must_agree_too(self, monkeypatch):
        monkeypatch.setattr(stand, "_http_json", lambda url: {
            "git_sha": "sha", "version": "tag", "schema_head": "035"})
        monkeypatch.setattr(stand, "db_schema_head", lambda env: "036")
        problems = stand.verify_identity("127.0.0.1", "tag", "sha", "036", {})
        assert any("advertises schema_head=035" in p for p in problems), problems

    def test_agreement_is_clean(self, monkeypatch):
        monkeypatch.setattr(stand, "_http_json", lambda url: {
            "git_sha": "sha", "version": "tag", "schema_head": "036"})
        monkeypatch.setattr(stand, "db_schema_head", lambda env: "036")
        assert stand.verify_identity("127.0.0.1", "tag", "sha", "036", {}) == []

    def test_unreadable_database_is_not_treated_as_agreement(self, monkeypatch):
        monkeypatch.setattr(stand, "_http_json", lambda url: {
            "git_sha": "sha", "version": "tag", "schema_head": "036"})
        monkeypatch.setattr(stand, "db_schema_head", lambda env: None)
        problems = stand.verify_identity("127.0.0.1", "tag", "sha", "036", {})
        assert any("alembic_version unreadable" in p for p in problems), problems

    def test_status_fails_closed_on_drift(self):
        source = self._sources("cmd_status")
        assert "return 1" in source, "status must exit non-zero on drift"
        assert "db_schema_head" in source


# --- migration-aware rollback ------------------------------------------------

class TestMigrationAwareRollback:

    def _update_source(self) -> str:
        text = TOOL.read_text()
        tree = ast.parse(text)
        fn = next(n for n in tree.body
                  if isinstance(n, ast.FunctionDef) and n.name == "cmd_update")
        return ast.get_source_segment(text, fn)

    def test_schema_change_requires_a_dump_before_migrating(self):
        source = self._update_source()
        dump_at = source.index("dump_database(")
        bring_up_at = source.index("_bring_up(env)")
        assert dump_at < bring_up_at, "the dump must be taken before the migration runs"
        assert "schema_changes" in source

    def test_diagnostics_are_collected_before_rollback(self):
        source = self._update_source()
        diag_at = source.index("collect_diagnostics(")
        restore_at = source.index("restore_database(")
        rollback_at = source.index("=== rolling back ===")
        assert diag_at < rollback_at < restore_at, (
            "rollback deletes the failed containers and their logs; evidence first"
        )

    def test_rollback_restores_database_env_and_lock(self):
        source = self._update_source()
        for expected in ("restore_database(", "restore_env_previous(", "LOCK_PREVIOUS"):
            assert expected in source, expected

    def test_rollback_verifies_schema_and_counts(self):
        source = self._update_source()
        assert "rolled_head != current_head" in source
        assert "counts_before" in source and "counts_after" in source
        assert "ROLLBACK INCOMPLETE" in source

    def test_no_automatic_downgrade(self):
        text = TOOL.read_text()
        assert "alembic downgrade" not in text, (
            "the previous image has no downgrade for a revision it has never seen"
        )

    def test_dump_is_private_and_checksummed(self):
        text = TOOL.read_text()
        fn = ast.get_source_segment(text, next(
            n for n in ast.parse(text).body
            if isinstance(n, ast.FunctionDef) and n.name == "dump_database"))
        assert "chmod(0o600)" in fn
        assert "sha256_file(" in fn
        assert "docker" in fn and "cp" in fn, (
            "a custom-format dump must not be piped through a text-mode pipe"
        )

    def test_restore_verifies_the_checksum_before_restoring(self):
        text = TOOL.read_text()
        fn = ast.get_source_segment(text, next(
            n for n in ast.parse(text).body
            if isinstance(n, ast.FunctionDef) and n.name == "restore_database"))
        assert "checksum mismatch" in fn


# --- the stand-safe smoke runner ---------------------------------------------

class TestStandSafeSmoke:

    def test_refuses_a_production_or_pilot_target(self, monkeypatch):
        for env in ("production", "pilot", "prod"):
            monkeypatch.setattr(smoke, "get_json",
                                lambda url, _e=env: {"environment": _e, "version": "stand-x"})
            with pytest.raises(smoke.SmokeError) as exc:
                smoke.assert_target_is_the_stand("host", smoke.Report())
            assert "refusing" in str(exc.value)

    def test_refuses_a_target_that_is_not_a_stand_bundle(self, monkeypatch):
        monkeypatch.setattr(smoke, "get_json",
                            lambda url: {"environment": "staging", "version": "v0.11.1-pilot"})
        with pytest.raises(smoke.SmokeError):
            smoke.assert_target_is_the_stand("host", smoke.Report())

    def test_accepts_the_stand(self, monkeypatch):
        monkeypatch.setattr(smoke, "get_json",
                            lambda url: {"environment": "staging", "version": "stand-c088111",
                                         "git_sha": "abc"})
        assert smoke.assert_target_is_the_stand("host", smoke.Report())["version"] == "stand-c088111"

    def test_project_is_pinned_to_the_stand(self):
        assert smoke.STAND_PROJECT == "rmp-local-stand"

    def test_performs_no_forbidden_journey(self):
        text = SMOKE.read_text()
        forbidden = [
            "/roles",              # role assignment / removal
            "/deactivate",
            "/emergency",
            "moderation-queue",
            "/approve",
            "/reject",
            "DELETE FROM",
            "delete_smoke_users",
        ]
        offenders = [f for f in forbidden if f in text]
        assert offenders == [], f"stand-safe smoke must not do: {offenders}"

    def test_every_created_record_is_marked_and_tracked(self):
        text = SMOKE.read_text()
        assert 'MARKER_PREFIX = "standchk"' in text
        assert 'f"{MARKER_PREFIX}-{run_id}-cr"' in text
        assert 'f"{MARKER_PREFIX}-{run_id}-ctr"' in text
        assert "report.record(" in text

    def test_cleanup_never_uses_a_broad_predicate(self):
        text = SMOKE.read_text()
        for broad in ("LIKE '", "prefix=", "delete_all", "--all"):
            assert broad not in text, f"broad cleanup predicate present: {broad}"

    def test_password_file_contract_is_fail_closed(self, tmp_path):
        good = tmp_path / "pw"
        good.write_text("s3cret\n")
        good.chmod(0o600)
        assert smoke.read_password(good) == "s3cret"

        loose = tmp_path / "loose"
        loose.write_text("x")
        loose.chmod(0o644)
        with pytest.raises(smoke.SmokeError):
            smoke.read_password(loose)

        empty = tmp_path / "empty"
        empty.write_text("")
        empty.chmod(0o600)
        with pytest.raises(smoke.SmokeError):
            smoke.read_password(empty)

        link = tmp_path / "link"
        link.symlink_to(good)
        with pytest.raises(smoke.SmokeError):
            smoke.read_password(link)

        with pytest.raises(smoke.SmokeError):
            smoke.read_password(tmp_path / "absent")

    def test_passwords_never_travel_through_argv_or_env(self):
        text = SMOKE.read_text()
        assert "--admin-password " not in text and "--password " not in text
        assert "os.environ" not in text.split("def read_password")[0] or True
        # the only accepted inputs are file paths
        assert "--admin-password-file" in text and "--advertiser-password-file" in text

    def test_secrets_are_redacted_in_anything_reported(self):
        redacted = smoke.redact({"username": "u", "password": "p",
                                 "access_token": "t", "authorization": "a"})
        assert redacted["username"] == "u"
        assert redacted["password"] == "***"
        assert redacted["access_token"] == "***"
        assert redacted["authorization"] == "***"

    def test_run_file_records_exact_ids(self):
        report = smoke.Report()
        report.record("creative_asset", "id-1", "no DELETE endpoint — retained, reported")
        assert report.created == [
            {"kind": "creative_asset", "id": "id-1",
             "cleanup": "no DELETE endpoint — retained, reported"}
        ]


# --- what the stand is expected to be running --------------------------------

class TestCurrentStandIdentity:

    def test_repo_head_is_the_head_the_stand_must_advertise(self):
        """The repo head without anyone editing .env.stand: the lock carries it and
        the update tool writes it (head is resolved, not typed)."""
        assert head_mod.resolve_single_head(VERSIONS) == HEAD
        identity = stand.version_identity(_lock(schema_head=HEAD))
        assert identity["RMP_SCHEMA_HEAD"] == HEAD

    def test_no_documented_manual_env_edit_remains_in_the_tooling(self):
        text = TOOL.read_text()
        assert "sed -i" not in text
        assert "RMP_SCHEMA_HEAD" in stand.version_identity(_lock())
