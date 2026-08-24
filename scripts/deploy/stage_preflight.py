#!/usr/bin/env python3
"""Stage the pilot host preflight with its repository-relative layout (001D-FU1).

``pilot_host_preflight.py`` resolves ``REPO_ROOT`` from its own location
(``parents[2]``) in order to find the pilot compose file and the two validators
it reuses. Copying those files *flat* into a staging directory therefore breaks
path resolution: the compose file is looked up outside the staging tree, the
compose check reports ``pilot compose missing``, and the run ends in a **false
FAIL** rather than an honest verdict.

This helper is the single source of truth for the staging layout, so the runbook
and the actual copy can no longer drift apart. It only creates directories and
copies files - it never runs the preflight, and never mutates a deployment.

Usage:
    python3 scripts/deploy/stage_preflight.py --dest /tmp/rmp-preflight
    python3 scripts/deploy/stage_preflight.py --dest /tmp/rmp-preflight \\
        --requirements infra/deploy/host-requirements.json
    python3 scripts/deploy/stage_preflight.py --remote rmp-pilot
    python3 scripts/deploy/stage_preflight.py --list
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Repository-relative paths that MUST keep their layout inside the staging tree.
# pilot_host_preflight.py derives REPO_ROOT as parents[2] of its own path, so it
# must land at <stage>/scripts/deploy/ for <stage> to become its REPO_ROOT.
STAGE_FILES: tuple[str, ...] = (
    "scripts/deploy/pilot_host_preflight.py",
    "scripts/deploy/validate-image-lock.py",
    "scripts/deploy/validate-pilot-env.py",
    "infra/compose/docker-compose.pilot.yml",
)

# Where an owner-supplied requirements file is placed inside the staging tree.
REQUIREMENTS_TARGET = "infra/deploy/host-requirements.json"

# Default staging root on the target host.
DEFAULT_REMOTE_DEST = "/tmp/rmp-preflight"

# The entrypoint, relative to the staging root.
ENTRYPOINT = "scripts/deploy/pilot_host_preflight.py"


def stage(dest: Path, requirements: Path | None = None) -> list[Path]:
    """Copy the preflight set into ``dest`` preserving repository-relative paths."""
    written: list[Path] = []
    for rel in STAGE_FILES:
        src = REPO_ROOT / rel
        if not src.exists():
            raise FileNotFoundError(f"missing repository file: {rel}")
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
        written.append(target)

    if requirements is not None:
        if not requirements.exists():
            raise FileNotFoundError(f"requirements file not found: {requirements}")
        target = dest / REQUIREMENTS_TARGET
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(requirements, target)
        written.append(target)

    return written


def _run(cmd: list[str]) -> int:
    print("+ " + " ".join(cmd))
    return subprocess.run(cmd).returncode


def stage_remote(host: str, dest: str, requirements: Path | None) -> int:
    """Stage onto a remote host over ssh/scp. Creates directories and copies only."""
    dirs = sorted({str(Path(dest) / Path(rel).parent) for rel in STAGE_FILES})
    if requirements is not None:
        dirs.append(str(Path(dest) / Path(REQUIREMENTS_TARGET).parent))
    rc = _run(["ssh", "-o", "BatchMode=yes", host, "mkdir -p " + " ".join(sorted(set(dirs)))])
    if rc != 0:
        return rc

    for rel in STAGE_FILES:
        rc = _run(["scp", "-q", "-o", "BatchMode=yes",
                   str(REPO_ROOT / rel), f"{host}:{Path(dest) / rel}"])
        if rc != 0:
            return rc

    if requirements is not None:
        rc = _run(["scp", "-q", "-o", "BatchMode=yes",
                   str(requirements), f"{host}:{Path(dest) / REQUIREMENTS_TARGET}"])
        if rc != 0:
            return rc

    print()
    print("Staged. Run the read-only preflight with:")
    print(f"  ssh {host} 'python3 {Path(dest) / ENTRYPOINT} --json'")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dest", help="local staging directory")
    parser.add_argument("--remote", help="ssh host/alias to stage onto")
    parser.add_argument("--remote-dest", default=DEFAULT_REMOTE_DEST,
                        help=f"staging directory on the remote host (default: {DEFAULT_REMOTE_DEST})")
    parser.add_argument("--requirements", help="owner-supplied host-requirements.json to include")
    parser.add_argument("--list", action="store_true",
                        help="print the staging layout and exit")
    args = parser.parse_args(argv)

    if args.list:
        for rel in STAGE_FILES:
            print(rel)
        return 0

    requirements = Path(args.requirements).resolve() if args.requirements else None

    if args.remote:
        return stage_remote(args.remote, args.remote_dest, requirements)

    if not args.dest:
        parser.error("one of --dest, --remote or --list is required")

    dest = Path(args.dest).resolve()
    written = stage(dest, requirements)
    for p in written:
        print(f"  {p.relative_to(dest)}")
    print()
    print("Staged. Run the read-only preflight with:")
    print(f"  python3 {dest / ENTRYPOINT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
