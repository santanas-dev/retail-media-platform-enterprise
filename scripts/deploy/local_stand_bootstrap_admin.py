#!/usr/bin/env python3
"""Bootstrap or rotate the local DEV/QA stand admin credential (LOCAL-DEV-STAND-001).

Why this exists
---------------
``apps/control-api/seed.py`` creates the ``break_glass_admin`` user
unconditionally, but seeds ``local_credentials`` only when dev credentials are
enabled - and those carry the well-known dev password. The
env-injected-password-hash path documented in
``docs/runbook/clean-install-login.md`` is marked *future* and is not
implemented, so on a stand seeded with ``SEED_DEV_CREDENTIALS=false`` nobody can
log in at all.

This tool closes that gap for the local stand only. It takes the password from a
TTY prompt, hashes it with the SAME contract the product uses (bcrypt, 12
rounds, ``password_hash_algorithm='bcrypt'``), and creates or rotates the
credential row. The plaintext is never written to disk, never passed on a
command line, never echoed and never logged.

Fail-closed
-----------
It refuses to run unless the caller explicitly asks for local-stand mode AND the
running project really is the local stand. It will not touch a pilot or
production database.

Usage:
    python3 scripts/deploy/local_stand_bootstrap_admin.py --local-stand
    python3 scripts/deploy/local_stand_bootstrap_admin.py --local-stand --username break_glass_admin
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PILOT_COMPOSE = ROOT / "infra" / "compose" / "docker-compose.pilot.yml"
STAND_COMPOSE = ROOT / "infra" / "compose" / "docker-compose.local-stand.yml"
ENV_FILE = ROOT / "infra" / "deploy" / ".env.stand"
RECORD = ROOT / "state" / "deploy-record.json"

PROJECT = "rmp-local-stand"
STAND_KIND = "local-dev-stand"

DEFAULT_USERNAME = "break_glass_admin"
CREDENTIAL_TYPE = "local_break_glass"   # fallback when auth_provider is unset
HASH_ALGORITHM = "bcrypt"
BCRYPT_ROUNDS = 12                      # must match apps/control-api/seed.py
MIN_PASSWORD_LEN = 12

# Passwords the product ships as dev-only. Never acceptable on the stand.
FORBIDDEN_PASSWORDS = {
    "break-glass-dev-only", "advertiser-dev-only", "changeme", "change_me",
    "password", "secret", "admin", "test",
}


def fail(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run(cmd: list[str], stdin: str | None = None, check: bool = True, timeout: int = 120):
    p = subprocess.run(cmd, capture_output=True, text=True, input=stdin, timeout=timeout)
    if check and p.returncode != 0:
        fail(f"command failed ({p.returncode}): {' '.join(cmd[:6])}...\n{(p.stderr or '').strip()}")
    return p


def compose(*args: str, stdin: str | None = None, check: bool = True):
    return run(["docker", "compose", "-p", PROJECT,
                "-f", str(PILOT_COMPOSE), "-f", str(STAND_COMPOSE),
                "--env-file", str(ENV_FILE), *args], stdin=stdin, check=check)


def read_env() -> dict[str, str]:
    if not ENV_FILE.exists():
        fail(f"env file missing: {ENV_FILE}")
    env = {}
    for raw in ENV_FILE.read_text().splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def assert_local_stand(explicit: bool) -> None:
    """Fail closed unless this is unambiguously the local stand."""
    if not explicit:
        fail("refusing to run without --local-stand (this tool is stand-only)")
    if not STAND_COMPOSE.exists():
        fail(f"local-stand overlay not found: {STAND_COMPOSE}")
    if RECORD.exists():
        try:
            rec = json.loads(RECORD.read_text())
        except json.JSONDecodeError:
            fail(f"deploy record is not valid JSON: {RECORD}")
        if rec.get("stand") != STAND_KIND or rec.get("project") != PROJECT:
            fail(f"deploy record is not the local stand "
                 f"(stand={rec.get('stand')!r}, project={rec.get('project')!r})")
    p = run(["docker", "compose", "-p", PROJECT, "-f", str(PILOT_COMPOSE),
             "-f", str(STAND_COMPOSE), "--env-file", str(ENV_FILE),
             "ps", "--format", "json"], check=False)
    if p.returncode != 0 or not (p.stdout or "").strip():
        fail(f"project {PROJECT} is not running; start the stand first")


def read_password_file(path: Path) -> str:
    """Read the stand password from an owner-managed file outside the repo.

    Only the PATH ever travels through argv or the environment - never the
    value. The file must be a regular, owner-only file.
    """
    if not path.exists():
        fail(f"password file not found: {path}")
    if path.is_symlink():
        fail(f"password file must not be a symlink: {path}")
    if not path.is_file():
        fail(f"password file is not a regular file: {path}")
    mode = path.stat().st_mode
    if mode & (stat.S_IRWXG | stat.S_IRWXO):
        fail(f"password file {path} is group/other accessible "
             f"({stat.filemode(mode)}); expected 0600")
    value = path.read_text().strip("\n")
    if not value:
        fail(f"password file {path} is empty")
    return value


def read_password_stdin() -> str:
    """Read the password from stdin - used when driving this over ssh.

    Keeps the secret off the remote filesystem entirely: it exists only in this
    process's memory on the stand host.
    """
    value = sys.stdin.readline().strip("\n")
    if not value:
        fail("no password received on stdin")
    return value


def prompt_password() -> str:
    """Read the password twice from a TTY. Never echoed, never stored."""
    if not sys.stdin.isatty():
        fail("a TTY is required - run this interactively (ssh -t), "
             "the password is never accepted from a pipe or an argument")
    pw = getpass.getpass("Stand admin password: ")
    again = getpass.getpass("Repeat password: ")
    if pw != again:
        fail("passwords do not match")
    if len(pw) < MIN_PASSWORD_LEN:
        fail(f"password must be at least {MIN_PASSWORD_LEN} characters")
    if pw.lower() in FORBIDDEN_PASSWORDS:
        fail("password is a known dev/default value and is not allowed on the stand")
    return pw


def hash_password(plain: str) -> str:
    """Hash inside the control-api image, using the product's own bcrypt contract.

    The plaintext travels on stdin only - never argv, never a file.
    """
    script = (
        "import sys,bcrypt;"
        "pw=sys.stdin.buffer.read().rstrip(b'\\n');"
        f"print(bcrypt.hashpw(pw,bcrypt.gensalt(rounds={BCRYPT_ROUNDS})).decode())"
    )
    p = compose("exec", "-T", "control-api", "python", "-c", script, stdin=plain + "\n")
    digest = (p.stdout or "").strip().splitlines()[-1] if p.stdout else ""
    if not digest.startswith("$2"):
        fail("bcrypt hashing failed inside control-api")
    return digest


def _psql(env: dict, sql: str, tuples_only: bool = True) -> str:
    owner = env.get("POSTGRES_OWNER_USER", "retail_media_owner")
    db = env.get("POSTGRES_DB", "retail_media_platform")
    args = ["exec", "-T", "postgres", "psql", "-U", owner, "-d", db, "-v", "ON_ERROR_STOP=1"]
    if tuples_only:
        args += ["-tAc", sql]
        return (compose(*args).stdout or "").strip()
    return (compose(*args, stdin=sql).stdout or "").strip()


def bootstrap(env: dict, username: str, password_hash: str) -> str:
    """Create or rotate the credential. Idempotent: same end state either way."""
    user_id = _psql(env, f"SELECT id FROM users WHERE username='{username}'")
    if not user_id:
        fail(f"user {username!r} not found - run migrations and seed first")

    # Match the credential type to the user's own auth_provider. Seeding a
    # break-glass credential onto an advertiser would be wrong, and a mismatch
    # is what the login endpoint checks.
    provider = _psql(env, f"SELECT auth_provider FROM users WHERE id='{user_id}'")
    credential_type = provider if provider.startswith("local_") else CREDENTIAL_TYPE

    existing = _psql(
        env, f"SELECT 1 FROM local_credentials WHERE user_id='{user_id}'")

    if existing == "1":
        sql = (
            "UPDATE local_credentials SET "
            f"password_hash='{password_hash}', "
            f"password_hash_algorithm='{HASH_ALGORITHM}', "
            "must_change_password=false, status='active' "
            f"WHERE user_id='{user_id}';"
        )
        action = "rotated"
    else:
        sql = (
            "INSERT INTO local_credentials "
            "(id, user_id, credential_type, password_hash, "
            " password_hash_algorithm, must_change_password, status) "
            f"VALUES (gen_random_uuid(), '{user_id}', '{credential_type}', "
            f"'{password_hash}', '{HASH_ALGORITHM}', false, 'active');"
        )
        action = "created"

    _psql(env, sql, tuples_only=False)

    check = _psql(
        env,
        "SELECT status || '|' || password_hash_algorithm "
        f"FROM local_credentials WHERE user_id='{user_id}'")
    if check != f"active|{HASH_ALGORITHM}":
        fail(f"credential verification failed: {check!r}")
    return action


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--local-stand", action="store_true",
                        help="required: acknowledge this targets the local stand")
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument(
        "--password-file", default=os.environ.get("STAND_PASSWORD_FILE"),
        help="path to the owner-managed password file (the PATH, never the value)")
    parser.add_argument(
        "--password-stdin", action="store_true",
        help="read the password from stdin (for ssh); keeps it off the remote disk")
    parser.add_argument(
        "--random-password", action="store_true",
        help="generate a throwaway password instead of prompting. Only for "
             "service accounts nobody logs in as: the product returns None for "
             "must_change_password when a user has no credential row, which "
             "makes AdvertiserUserMembershipOut fail validation with a 500.")
    args = parser.parse_args(argv)

    assert_local_stand(args.local_stand)
    env = read_env()

    if args.random_password:
        import secrets as _secrets
        password = _secrets.token_urlsafe(24)
        print(f"generating a throwaway password for '{args.username}' "
              f"(not printed, not stored - nobody is expected to log in as it)")
    elif args.password_stdin:
        password = read_password_stdin()
    elif args.password_file:
        password = read_password_file(Path(args.password_file))
    else:
        password = prompt_password()
    try:
        digest = hash_password(password)
    finally:
        del password           # do not keep the plaintext around

    action = bootstrap(env, args.username, digest)
    print(f"\nstand admin credential {action} for '{args.username}' "
          f"(bcrypt, {BCRYPT_ROUNDS} rounds, must_change_password=false)")
    print("the password was never written to disk, argv or logs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
