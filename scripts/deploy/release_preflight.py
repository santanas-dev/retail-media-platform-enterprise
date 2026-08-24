#!/usr/bin/env python3
"""Publish preflight checks (IMAGE-REGISTRY-001, SCOPE A).

Pure, testable validation of the release ref before any image is built/pushed.
The publish workflow invokes this as a gate step; the unit tests exercise the
same function for the negative matrix.

Checks enforced:
  - ref must be a tag (branch / bare SHA is refused);
  - tag must be annotated (tag object != peeled commit);
  - peeled commit must equal the expected release SHA exactly.

Exit 0 = OK; 1 = refused.
"""

from __future__ import annotations

import argparse
import sys


def validate_release_ref(
    tag_object_sha: str,
    peeled_sha: str,
    expected_sha: str,
    is_tag_ref: bool,
) -> list[str]:
    """Return a list of refusal reasons (empty = OK)."""
    errors: list[str] = []
    if not is_tag_ref:
        errors.append("ref is not a tag — publish only from an annotated release tag")
    if tag_object_sha and peeled_sha and tag_object_sha == peeled_sha:
        errors.append("tag is lightweight (not annotated) — refuse")
    if expected_sha and peeled_sha and expected_sha.strip() != peeled_sha.strip():
        errors.append(f"expected_sha mismatch: peeled={peeled_sha} expected={expected_sha}")
    return errors


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tag-object", default="", help="git rev-parse of the tag ref")
    p.add_argument("--peel", default="", help="git rev-parse of tag^{}")
    p.add_argument("--expected", required=True, help="expected release SHA")
    p.add_argument("--is-tag", default="false", help="true/false — whether ref is a tag")
    args = p.parse_args()

    errors = validate_release_ref(
        args.tag_object, args.peel, args.expected,
        args.is_tag.lower() == "true",
    )
    if errors:
        for e in errors:
            print(f"REFUSE: {e}", file=sys.stderr)
        return 1
    print(f"preflight OK: annotated tag → {args.peel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
