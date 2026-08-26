#!/usr/bin/env python3
"""Resolve the single Alembic head revision from the migration files.

LOCAL-DEV-STAND-001-FU-IDENTITY-SMOKE.

The stand's declared schema head has to come from somewhere that cannot drift:
it used to be typed into ``.env.stand`` by hand and was wrong after two of the
last two updates. This resolver reads it out of the migration files, so the
build that produces a bundle also decides what schema that bundle expects.

Deliberately file-based rather than ``alembic heads``: it must work in a build
container with no alembic config and no database, and it must be able to refuse
a branched history rather than silently pick one head.

The value it returns is the **expected** head of a bundle. The **actual** head
of a running database is a different fact, read from ``alembic_version``; the
two are compared, never conflated.

Usage:
    python scripts/deploy/alembic_head.py [--versions-dir DIR]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_VERSIONS_DIR = (
    Path(__file__).resolve().parents[2] / "apps" / "control-api" / "alembic" / "versions"
)

_REVISION_RE = re.compile(r'^revision(?::\s*str)?\s*=\s*["\']([^"\']+)["\']', re.M)
_DOWN_RE = re.compile(r'^down_revision(?::[^=]+)?\s*=\s*["\']([^"\']+)["\']', re.M)

# A head that looks like a stand-in rather than a revision.
_PLACEHOLDER_RE = re.compile(r"REPLACE_WITH|TODO|EXAMPLE|PLACEHOLDER|^head$|^unknown$", re.IGNORECASE)


class HeadResolutionError(RuntimeError):
    """The migration history does not yield exactly one usable head."""


def read_revisions(versions_dir: Path) -> tuple[set[str], set[str]]:
    """Return (revisions, down_revisions) declared by the migration files."""
    if not versions_dir.is_dir():
        raise HeadResolutionError(f"migrations directory not found: {versions_dir}")

    revisions: set[str] = set()
    downs: set[str] = set()
    for path in sorted(versions_dir.glob("*.py")):
        if path.name.startswith("__"):
            continue
        text = path.read_text()
        rev = _REVISION_RE.search(text)
        down = _DOWN_RE.search(text)
        if rev:
            revisions.add(rev.group(1))
        if down:
            downs.add(down.group(1))
    if not revisions:
        raise HeadResolutionError(f"no alembic revisions found in {versions_dir}")
    return revisions, downs


def resolve_single_head(versions_dir: Path | str = DEFAULT_VERSIONS_DIR) -> str:
    """The one revision nothing else revises. Raises if that is not unique."""
    revisions, downs = read_revisions(Path(versions_dir))
    heads = sorted(revisions - downs)
    if len(heads) != 1:
        raise HeadResolutionError(
            f"expected exactly one alembic head, got {heads or '[]'} — "
            "a branched history cannot declare a single schema head"
        )
    head = heads[0]
    if _PLACEHOLDER_RE.search(head):
        raise HeadResolutionError(f"resolved head {head!r} looks like a placeholder")
    return head


def is_placeholder(value: str) -> bool:
    """True when a declared head is empty or a stand-in rather than a revision."""
    value = (value or "").strip()
    return not value or bool(_PLACEHOLDER_RE.search(value))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--versions-dir", default=str(DEFAULT_VERSIONS_DIR))
    args = parser.parse_args()
    try:
        print(resolve_single_head(args.versions_dir))
    except HeadResolutionError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
