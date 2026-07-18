#!/usr/bin/env python3
"""
CLEAN-BOOT-001: Clean Docker Boot -> Login Smoke.

Usage:
  python3 scripts/smoke/clean-boot-login.py

Minimal stack: postgres + redis + control-api + db-setup.
NATS/MinIO not required for login smoke.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request
import urllib.error

REPO_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COMPOSE1 = os.path.join(REPO_DIR, "infra", "compose", "docker-compose.phase1.yml")
COMPOSE2 = os.path.join(REPO_DIR, "infra", "compose", "docker-compose.preview.yml")
API_URL = os.environ.get("API_URL", "http://localhost:8000")
TIMEOUT = int(os.environ.get("TIMEOUT", "60"))

GREEN = "\033[0;32m"
RED = "\033[0;31m"
NC = "\033[0m"
FAILED = False

def dc(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "compose", "-f", COMPOSE1, "-f", COMPOSE2, *args],
                          capture_output=True, text=True, cwd=REPO_DIR)

def http(method: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, dict]:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())
    except Exception as e:
        return 0, {"error": str(e)}

def ok(cond: bool, msg: str) -> None:
    global FAILED
    if cond:
        print(f"{GREEN}PASS{NC}: {msg}")
    else:
        print(f"{RED}FAIL{NC}: {msg}")
        FAILED = True

def main() -> None:
    print("=== CLEAN-BOOT-001: Clean Docker Boot -> Login Smoke ===\n")

    # Step 1: Clean state
    print("--- Step 1: docker compose down -v ---")
    dc("down", "-v", "--remove-orphans")
    print("")

    # Step 2: Build (no cache to ensure fresh Dockerfile)
    print("--- Step 2: Building control-api (no cache) ---")
    r = dc("build", "--no-cache", "control-api")
    ok(r.returncode == 0, "build control-api")
    print("")

    # Step 3: Start infra
    print("--- Step 3: Starting postgres + redis + control-api ---")
    r = dc("up", "-d", "postgres", "redis", "control-api")
    ok(r.returncode == 0, "compose up")
    print("")

    # Step 4: Wait for healthy
    print(f"--- Step 4: Waiting for control-api healthy (timeout {TIMEOUT}s) ---")
    start = time.time()
    while time.time() - start < TIMEOUT:
        try:
            code, _ = http("GET", "/api/v1/health")
            if code == 200:
                print(f"{GREEN}PASS{NC}: control-api healthy after {int(time.time()-start)}s")
                break
        except Exception:
            pass
        time.sleep(2)
    else:
        ok(False, f"control-api not healthy after {TIMEOUT}s")
    print("")

    # Step 5: db-setup
    print("--- Step 5: Running db-setup ---")
    r = dc("--profile", "setup", "run", "--rm", "db-setup")
    ok(r.returncode == 0, f"db-setup (exit {r.returncode})")
    if r.returncode != 0:
        print(r.stdout[-500:])
        print(r.stderr[-500:])
    print("")

    # Step 6: Login
    print("--- Step 6: POST /api/v1/auth/login ---")
    code, resp = http("POST", "/api/v1/auth/login", {
        "username_or_email": "advertiser_test",
        "password": "advertiser-dev-only",
        "auth_provider": "local_advertiser",
    })
    token = resp.get("access_token", "")
    ok(code == 200, f"Login HTTP {code}")
    ok(bool(token), "access_token present")
    print("")

    # Step 7: Campaigns
    print("--- Step 7: GET /api/v1/identity/campaigns ---")
    code, resp = http("GET", "/api/v1/identity/campaigns", token=token)
    total = resp.get("total", 0)
    ok(code == 200, f"Campaigns HTTP {code}")
    ok(total > 0, f"total={total} (non-empty)")
    print("")

    # Step 8: local_credentials
    print("--- Step 8: Verify local_credentials seeded ---")
    r = subprocess.run(
        ["docker", "compose", "-f", COMPOSE1, "-f", COMPOSE2,
         "exec", "-T", "postgres",
         "psql", "-U", "retail_media_owner", "-d", "retail_media_platform",
         "-t", "-c", "SELECT count(*) FROM local_credentials;"],
        capture_output=True, text=True, cwd=REPO_DIR,
    )
    cred_count = r.stdout.strip()
    ok(r.returncode == 0, f"local_credentials query (exit {r.returncode})")
    ok(cred_count is not None and cred_count != "0", f"count={cred_count}")
    print("")

    # Summary
    if FAILED:
        print(f"{RED}=== SOME CHECKS FAILED ==={NC}")
        sys.exit(1)
    print(f"{GREEN}=== ALL CHECKS PASSED ==={NC}")
    print(f"  login:        200 + token")
    print(f"  campaigns:    200 + {total} items")
    print(f"  credentials:  {cred_count} seeded")

if __name__ == "__main__":
    main()
