# Pilot Host Preflight — Operator Runbook (001D)

| **Task:** PILOT-DEPLOYMENT-READINESS-001D |
| **Status:** TOOLING READY / HOST PROOF PENDING |
| **Scope:** read-only host preflight. **Not** a deployment. |

> No step in this runbook deploys anything. The preflight never runs
> `compose up`, migrations, restore, seed, or any application service, and never
> pulls an image. Registry checks use manifest inspection only.
>
> Pilot remains **NOT DEPLOYED**. Production remains **NO-GO**. Deployed SHA
> remains **UNKNOWN / NOT TRACKED**.

---

## 1. What the tool is

`scripts/deploy/pilot_host_preflight.py` — a single fail-closed preflight that
reports whether a candidate pilot host is fit to receive the pilot stack.

```bash
python3 scripts/deploy/pilot_host_preflight.py            # human-readable
python3 scripts/deploy/pilot_host_preflight.py --json     # machine-readable
```

| Exit | Verdict | Meaning |
|:----:|---------|---------|
| `0` | `GO` | every check passed |
| `2` | `NEEDS_OWNER_INPUT` | no failures, but owner-supplied facts are missing |
| `1` | `FAIL` | at least one check failed |

A failure always outranks a missing input, so an incomplete requirements file
can never mask a real defect.

Options: `--requirements`, `--env`, `--lock`, `--compose`, `--skip-registry`.

### Redaction

Every emitted detail passes through a redactor covering GitHub tokens
(`ghp_`/`gho_`/`github_pat_`), URL-embedded passwords, `password=`/`token=`/
`api_key=` assignments, JWTs, and private-key headers. Environment **values are
never read into the report** — only variable *names* are checked.

---

## 2. Requirement values are owner input, not invention

The repository documents these concretely, and the tool derives them itself —
they are **not** configurable:

| Fact | Value | Source |
|------|-------|--------|
| Platform | `linux` / `amd64` only | single-arch bundle; no arm64 published |
| Host ports | `8000`, `8001`, `3000`, `3001` | `docker-compose.pilot.yml` `ports:` |
| Services | control-api, device-gateway, orchestrator-worker, admin-web, advertiser-web | `validate-image-lock.py` |
| Registry | `ghcr.io/santanas-dev/rmp-pilot` (private) | IMAGE-REGISTRY-001-PRIVATE-REMEDIATION |
| Compose project | `rmp-pilot`; volumes `pg_data`, `minio_data`, `nats_jetstream` | `docker-compose.pilot.yml` |
| Required env names | 34 names | `.env.pilot.example` |

The repository documents **no** numeric CPU/RAM/disk thresholds and **no**
minimum Docker/Compose versions. Those, plus DNS/TLS/backup/monitoring facts,
come from an owner-supplied file:

```bash
cp infra/deploy/host-requirements.example.json infra/deploy/host-requirements.json
$EDITOR infra/deploy/host-requirements.json     # every null is owner input
```

Every `null` produces `NEEDS_OWNER_INPUT` — never an assumed threshold.

---

## 3. Owner-input gate (SCOPE B)

Status as of 001D. **No secrets in this table, ever** — record only the *name*
of a secret reference and how it will be delivered interactively.

| # | Input | Status | Notes |
|---|-------|:------:|-------|
| 1 | Host / IP, SSH user, access method | **MISSING** | blocks any real-host proof |
| 2 | OS + version | **MISSING** | tool verifies `linux`; distro/version is owner input |
| 3 | Architecture | **UNKNOWN** | must be `x86_64`; images are amd64-only |
| 4 | CPU / RAM / disk | **MISSING** | no thresholds documented in repo |
| 5 | DNS names (admin/advertiser/control-api/device-gateway) | **MISSING** | tool resolves them once supplied |
| 6 | TLS termination + certificate owner | **MISSING** | no proxy config exists in repo (001A finding 3) |
| 7 | Firewall / VPN / access policy | **MISSING** | who may reach control-api |
| 8 | Registry authentication | **PRESENT (CI)** / **MISSING (host)** | a read-only GHCR pull credential must exist on the host |
| 9 | Secret-storage mechanism | **MISSING** | env-file vs docker secrets vs vault |
| 10 | Persistent storage paths | **MISSING** | `persistent_data_root` for docker volumes |
| 11 | Backup destination | **MISSING** | existence + writability + free space checked once supplied |
| 12 | SMTP / AD-LDAPS / external integrations | **MISSING** | or an explicit "not needed for pilot" |
| 13 | Monitoring destination | **MISSING** | self-hosted vs external |
| 14 | Maintenance window | **MISSING** | required before 001E |
| 15 | Rollback operator | **MISSING** | named human |

**Secrets are never sent to chat and never committed.** The repository holds
templates with placeholders only; `infra/deploy/.env.pilot`,
`images.lock.json` and `host-requirements.json` are gitignored.

---

## 4. What the preflight checks

| Group | Checks |
|-------|--------|
| platform | OS is linux; architecture is x86_64/amd64 |
| docker | engine present + version; compose plugin + version; daemon responds; current user reaches the socket without elevation |
| resources | CPU cores, RAM, free disk at `persistent_data_root`, writability |
| clock | time sync observable via `timedatectl` / `chronyc` / `ntpq` |
| ports | 8000/8001/3000/3001 free — an occupied port is **classified** (pilot container = collision, foreign container, non-docker listener) |
| network | DNS + outbound HTTPS:443 to `github.com` and `ghcr.io` |
| compose | `docker compose config` validates; no `build:`, no source bind mounts, no mutable/`latest` tags, no dev credentials, no dev ingest |
| images | lock present; `validate-image-lock.py` passes; all 5 refs digest-only; checksum recorded |
| registry | authenticated manifest inspection succeeds; **anonymous access denied** (proves the package is private) |
| env | `.env.pilot` present on target only, not git-tracked, owner-only permissions (no group/other); all 34 required names present; `validate-pilot-env.py` finds no placeholder/dev/weak secrets |
| storage | backup destination exists, writable, has free space |
| collision | no existing `rmp-pilot` containers or volumes |
| owner | DNS/TLS/monitoring/secret-storage/window/rollback reported PASS / MISSING / FAIL |

---

## 5. Real-host proof gate (SCOPE E)

**Before any SSH to the pilot host, the owner must approve the exact command
plan.** The agent does not connect on its own initiative.

### 5.1 Proposed read-only plan

Copy the tool and the templates to the host, then run it. Nothing else.

```bash
# 1. copy tool + templates (no secrets leave the host)
scp scripts/deploy/pilot_host_preflight.py \
    scripts/deploy/validate-image-lock.py \
    scripts/deploy/validate-pilot-env.py \
    <user>@<host>:/tmp/rmp-preflight/

# 2. run read-only, machine-readable
ssh <user>@<host> 'python3 /tmp/rmp-preflight/pilot_host_preflight.py \
    --json \
    --requirements /etc/rmp/host-requirements.json \
    --env /etc/rmp/.env.pilot \
    --lock /etc/rmp/images.lock.json'
```

### 5.2 Metadata collected

OS name, architecture, CPU count, total RAM, free disk at the configured paths,
Docker/Compose version strings, time-sync boolean, listener state of four ports,
DNS resolution booleans, compose/lock validation verdicts, env variable **names**,
file permission bits, container/volume names in the `rmp-pilot` project.

**Not collected:** any environment *value*, any secret, any credential, any
customer data, any file contents beyond variable names.

### 5.3 Acceptance for a real-host GO

- preflight executed **on the target host** (not simulated);
- no secret present in output or artifacts;
- immutable private image bundle reachable by digest (manifest inspection);
- verdict `GO`, or an exact blocker list;
- **no service, volume, or network created** by the preflight.

Absent host access: verdict stays `TOOLING READY / HOST PROOF PENDING`. 001D is
**not** DONE, 001E does **not** start, and feature-registry statuses do not move.

---

## 6. CI enforcement

The blocking `packaging` job (a `release-gate` dependency) runs:

1. **Fail-closed contract** — the tool is invoked with the all-null example
   requirements; CI fails if it returns `GO` (exit 0) or any code other than
   1/2, and asserts the JSON payload reports `deployment_performed: false`.
2. **`tests/test_pilot_host_preflight.py`** — 48 deterministic tests over
   fixtures and stubbed probes: clean→GO, missing owner input→NEEDS_OWNER_INPUT,
   missing Docker/Compose, unsupported architecture, insufficient disk/RAM/CPU,
   occupied port, placeholder digest, mutable/`latest` image, service-set
   mismatch, weak/dev secret, unsafe env permissions, tracked env file, missing
   backup destination, redaction, and existing deployment/volume collision.
   An AST guard asserts the tool never invokes a deployment verb.

No real host, credential, or secret is present in GitHub Actions.
