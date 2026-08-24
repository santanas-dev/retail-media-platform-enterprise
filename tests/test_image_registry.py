"""Negative/tamper matrix for the image registry release lock (IMAGE-REGISTRY-001, SCOPE F).

Covers the publish preflight (tag/SHA) and the release-lock verifier/generator
invariants. These run in CI (python-tests) as the permanent regression guard for
the GHCR publication path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# scripts/deploy is not a package — expose its modules for import.
_DEPLOY = str(Path(__file__).resolve().parent.parent / "scripts" / "deploy")
sys.path.insert(0, _DEPLOY)

import generate_release_lock as gen  # noqa: E402
import release_preflight as preflight  # noqa: E402
import verify_release_lock as verifier  # noqa: E402

RELEASE_TAG = "v0.11.1-pilot-packaging"
RELEASE_SHA = "90c4bb1a9c7d1b2d5dbf6bef180d942dd5336275"
REGISTRY = "ghcr.io/santanas-dev/retail-media-platform-enterprise"

GOOD_DIGESTS = {
    "control-api": "sha256:" + "a" * 64,
    "device-gateway": "sha256:" + "b" * 64,
    "orchestrator-worker": "sha256:" + "c" * 64,
    "admin-web": "sha256:" + "d" * 64,
    "advertiser-web": "sha256:" + "e" * 64,
}


def _build_lock(digests=None, sha=RELEASE_SHA, tag=RELEASE_TAG, **kw):
    return gen.build_lock(tag, sha, "linux/amd64", REGISTRY, digests or dict(GOOD_DIGESTS), **kw)


# ---------------------------------------------------------------------------
# Publish preflight (SCOPE A / SCOPE F)
# ---------------------------------------------------------------------------

def test_preflight_wrong_expected_sha_refused():
    errs = preflight.validate_release_ref(
        tag_object_sha="x" * 40, peeled_sha=RELEASE_SHA,
        expected_sha="f" * 40, is_tag_ref=True,
    )
    assert any("expected_sha mismatch" in e for e in errs)


def test_preflight_branch_not_tag_refused():
    errs = preflight.validate_release_ref(
        tag_object_sha="", peeled_sha=RELEASE_SHA,
        expected_sha=RELEASE_SHA, is_tag_ref=False,
    )
    assert any("not a tag" in e for e in errs)


def test_preflight_lightweight_tag_refused():
    errs = preflight.validate_release_ref(
        tag_object_sha=RELEASE_SHA, peeled_sha=RELEASE_SHA,
        expected_sha=RELEASE_SHA, is_tag_ref=True,
    )
    assert any("lightweight" in e for e in errs)


def test_preflight_ok():
    errs = preflight.validate_release_ref(
        tag_object_sha="a" * 40, peeled_sha=RELEASE_SHA,
        expected_sha=RELEASE_SHA, is_tag_ref=True,
    )
    assert errs == []


# ---------------------------------------------------------------------------
# Release-lock generator (SCOPE D)
# ---------------------------------------------------------------------------

def test_generator_missing_service_refused():
    with pytest.raises(ValueError):
        _build_lock(digests={k: v for k, v in GOOD_DIGESTS.items() if k != "admin-web"})


def test_generator_extra_service_refused():
    d = dict(GOOD_DIGESTS)
    d["rogue-service"] = "sha256:" + "f" * 64
    with pytest.raises(ValueError):
        _build_lock(digests=d)


def test_generator_non_sha256_digest_refused():
    d = dict(GOOD_DIGESTS)
    d["control-api"] = "not-a-digest"
    with pytest.raises(ValueError):
        _build_lock(digests=d)


def test_generator_bad_sha_length_refused():
    with pytest.raises(ValueError):
        _build_lock(sha="90c4bb1")


def test_generator_lock_has_all_extended_fields():
    lock = _build_lock()
    assert lock["schema_version"] == "1.1"
    assert lock["platform"] == "linux/amd64"
    assert lock["compose_service_mapping"] == {"db-migrate": "control-api"}
    assert lock["release"]["tag"] == RELEASE_TAG
    for img in lock["images"]:
        assert img["oci"]["revision"] == RELEASE_SHA
        assert img["sbom"] == "attested"
        assert img["provenance"] == "attested"


# ---------------------------------------------------------------------------
# Release-lock verifier (SCOPE D / SCOPE F)
# ---------------------------------------------------------------------------

def test_verify_good_lock_passes():
    lock = _build_lock()
    assert verifier.verify(lock) == []


def test_verify_placeholder_digest_refused():
    lock = _build_lock()
    lock["images"][0]["image_digest"] = "sha256:REPLACE_WITH_REAL_DIGEST"
    assert any("placeholder" in e for e in verifier.verify(lock))


def test_verify_empty_digest_refused():
    lock = _build_lock()
    lock["images"][0]["image_digest"] = ""
    assert any("empty" in e or "not a valid" in e for e in verifier.verify(lock))


def test_verify_latest_tag_refused():
    lock = _build_lock()
    lock["images"][0]["source_tag"] = "latest"
    assert any("mutable" in e for e in verifier.verify(lock))


def test_verify_mixed_sha_refused():
    lock = _build_lock()
    lock["images"][1]["git_sha"] = "f" * 40
    assert any("mixed" in e for e in verifier.verify(lock))


def test_verify_missing_service_refused():
    lock = _build_lock()
    lock["images"] = lock["images"][:-1]  # drop advertiser-web
    assert any("missing" in e for e in verifier.verify(lock))


def test_verify_unsupported_platform_refused():
    lock = _build_lock()
    lock["platform"] = "linux/arm64"
    assert any("platform" in e for e in verifier.verify(lock))


def test_verify_tampered_digest_format_refused():
    # A tampered digest that is no longer a valid sha256:<hex> is caught by the verifier.
    lock = _build_lock()
    lock["images"][0]["image_digest"] = "sha256:deadbeef"
    assert any("not a valid sha256" in e for e in verifier.verify(lock))


def test_verify_wrong_digest_value_is_valid_format_but_mismatches():
    # A wrong digest that IS a valid sha256:<hex> format passes the static
    # verifier (by design) — it is caught at *pull* time in the verify workflow.
    lock = _build_lock()
    lock["images"][0]["image_digest"] = "sha256:" + "f" * 64
    assert verifier.verify(lock) == []
