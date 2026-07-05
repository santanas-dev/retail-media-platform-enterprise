# ADR-014: Layering and Import Boundaries

**Status:** Accepted
**Date:** 2026-07-04
**Phase:** 4.0a+ (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

The platform is growing from a single FastAPI service (`control-api`)
into a multi-service architecture (ADR-001: Device Gateway, PoP
Ingestor, Orchestrator Worker, Adapter Workers).  `packages/` is the
shared library layer.  Without explicit layering rules, the codebase
risks:

- **Cyclic imports** — `api` imports `domain`, `domain` accidentally
  imports `api` → import loop at startup.
- **God objects** — a single service module that handles auth,
  advertiser, device, and campaign logic, with no clear boundaries.
- **Router bloat** — SQL queries, business rules, and validation all
  crammed into FastAPI route handlers.
- **Hidden dependencies** — a security module that depends on FastAPI's
  `Request` object, making it impossible to reuse outside HTTP context.

This ADR defines the layer hierarchy, dependency direction, and import
rules that every package and service must follow.  It also mandates
future CI enforcement via import-linter.

## Decision

### 1. Layer Hierarchy

```
┌──────────────────────────────────────────────┐
│ apps/                                        │  ← service entrypoints
│  control-api, device-gateway, orchestrator,  │
│  pop-ingestor, adapter-workers               │
├──────────────────────────────────────────────┤
│ packages/api/                                │  ← HTTP glue
│  routers, dependencies, request/response DTO │
├──────────────────────────────────────────────┤
│ packages/auth/                               │  ← business services
│  auth service, ad_provider                   │
│ (future: advertiser service, campaign srv)   │
├──────────────────────────────────────────────┤
│ packages/domain/                             │  ← core domain
│  models, repository, scopes, schemas,        │
│  database session helpers                    │
├──────────────────────────────────────────────┤
│ packages/security/    packages/observability/│  ← cross-cutting
│  jwt, crypto, config   logging, metrics,     │
│  sanitization          correlation           │
├──────────────────────────────────────────────┤
│ packages/contracts/                          │  ← zero-runtime schemas
│  manifest_v1, proof_event_v1, event types    │
└──────────────────────────────────────────────┘
```

| Layer | Purpose | Examples |
|-------|---------|----------|
| `apps/*` | Service entrypoints | `apps/control-api/main.py`, `apps/device-gateway/main.py` |
| `packages/api/` | HTTP routers, FastAPI dependencies, request/response DTOs | `packages/api/identity.py`, `packages/api/dependencies.py` |
| `packages/auth/` + future `packages/services/` | Business use-cases, orchestration, domain services | `packages/auth/service.py`, future `packages/services/advertiser.py` |
| `packages/domain/` | ORM models, repository queries, scope resolution, domain rules | `packages/domain/models.py`, `packages/domain/repository.py` |
| `packages/security/` | Auth crypto, config loading, JWT, password hashing, sanitization | `packages/security/jwt.py`, `packages/security/config.py` |
| `packages/observability/` | Structured logging, metrics primitives, correlation ID helpers | `packages/observability/__init__.py` |
| `packages/contracts/` | JSON schemas, event type definitions — no runtime imports | `packages/contracts/manifest_v1.schema.json` |

### 2. Allowed Dependency Direction

Dependencies flow **downward**.  A layer may only import from layers
below it or from cross-cutting layers at the bottom.

```
apps/*          ──may import──►  packages/api, packages/auth,
                                 packages/domain, packages/security,
                                 packages/observability, packages/contracts

packages/api/   ──may import──►  packages/auth, packages/domain,
                                 packages/security, packages/observability

packages/auth/  ──may import──►  packages/domain, packages/security,
                                 packages/observability

packages/domain/ ──may import──► packages/security (config only),
                                 packages/observability (logger only)
                                 ──MUST NOT──► packages/api, packages/auth,
                                                fastapi

packages/security/ ──may import──► (stdlib only, no packages.*)
                    ──MUST NOT──►  packages/api, packages/auth,
                                   packages/domain (except simple enums)

packages/observability/ ──may import──► (stdlib only, no packages.*)
                         ──MUST NOT──►  any business/domain/api package

packages/contracts/ ──may import──► (nothing at runtime)
                    ──MUST NOT──►  any runtime package
```

**Rationale for domain → security (config only):** Domain modules that need
`DATABASE_URL` or other environment-driven settings read them from `os.environ`
directly.  They must not import `jwt`, `password`,
`sanitize`, or `tokens` — those are auth-layer concerns.

### 3. Explicitly Forbidden Imports

| Forbidden import | Reason |
|-----------------|--------|
| `from packages.api import ...` in `packages/domain/` | Domain is the foundation; must not depend on HTTP layer |
| `from fastapi import ...` in `packages/domain/` | Domain objects must be HTTP-framework-agnostic |
| `from packages.api import ...` in `packages/security/` | Security primitives must be reusable outside HTTP context |
| `from packages.api.routers import ...` in `packages/auth/` | Services must not know about route registration |
| `from apps.control_api import ...` in `apps/device_gateway/` | Cross-service imports are forbidden |
| `from backend import ...` in `apps/*` or `packages/*` | Direct legacy imports are forbidden |
| `from apps.* import ...` in `packages/*` | Shared packages must not depend on specific apps |

**Additionally:**
- No module may import `*` from another package (`from packages.domain import *`).
- No circular imports between any two packages.
- No import of a concrete implementation where an interface/ABC is defined
  (e.g., `packages/auth/ad_provider.py` defines `ADAuthProvider` ABC;
  concrete implementations live in the same file or `infrastructure/`).

### 4. Anti-God-Object Rules

A "god object" is a module or class that mixes unrelated concerns —
auth + advertiser + device + campaign logic in one file.

| Rule | Example violation | Correct |
|------|-------------------|---------|
| One bounded context per service module | `services/platform.py` handling auth AND campaigns | `services/advertiser.py`, `services/campaign.py` |
| One reason to change per module | Adding a campaign field requires changing the auth module | Campaign changes only touch `services/campaign.py` |
| No mega-routers | Single `routers.py` with 50 endpoints across 5 domains | `api/identity.py`, `api/advertiser.py`, `api/campaigns.py` |
| Maximum file size guideline | > 500 lines → consider splitting | Most current files are 100–350 lines ✅ |

### 5. Repository / Query Rules

**DB queries live in repository modules, not in routers.**

```python
# ❌  SQL in router — untestable without HTTP, mixed concerns
@router.get("/users")
async def list_users(db=Depends(get_db)):
    result = await db.execute(select(User).limit(10))  # raw SQL in router
    return result.scalars().all()

# ✅  query in repository, router does glue only
# packages/domain/repository.py
async def list_users(db, limit, offset):
    result = await db.execute(select(User).limit(limit).offset(offset))
    return result.scalars().all(), await _count(db, User)

# packages/api/identity.py
@router.get("/users")
async def list_users(db=Depends(get_db), _perm=Depends(require_permission("users.read"))):
    items, total = await repository.list_users(db, limit, offset)
    return PaginatedUsers(items=[UserOut.model_validate(u) for u in items], ...)
```

**Router responsibilities:** validation, authorization (dependency
injection), request/response DTO mapping, HTTP status codes.

**Repository responsibilities:** query construction, pagination,
filtering, data access.

**Separation enforced:** routers never call `db.execute()` directly.

### 6. Dependency Injection

External clients (NATS, S3/MinIO, LDAP, Redis) are injected via
interfaces or factory functions — never global singletons accessed
through `import`.

```python
# ❌  hidden global singleton
from somewhere import nats_client
nats_client.publish(...)

# ✅  injected via FastAPI dependency or constructor
async def publish_manifest(manifest, nats: NATSClient = Depends(get_nats)):
    await nats.publish("manifest.generated", manifest)
```

**Exceptions:** `get_security_config()` (reads env vars, no I/O) and
`get_global_engine()` (SQLAlchemy engine registry) are acceptable
module-level accessors because they are configuration, not external
clients.

### 7. Future Import-Linter Enforcement

When CI infrastructure matures (Phase 4.1+), an import-linter check
MUST be added:

```
# .importlinter or pyproject.toml [tool.importlinter]
[[packages]]
name = "packages.domain"
forbidden_imports = ["packages.api", "packages.auth", "fastapi"]

[[packages]]
name = "packages.security"
forbidden_imports = ["packages.api", "packages.auth"]

[[packages]]
name = "packages.observability"
forbidden_imports = ["packages.api", "packages.auth", "packages.domain"]
```

**Until CI is implemented:** code review must manually verify that no
new import violates these rules.  Source-inspection is acceptable for
import hygiene until automated checks are in place.

**When CI is implemented:** import-linter runs as a blocking gate.
PRs with forbidden imports are rejected.

### 8. Current State (Baseline)

As of Phase 4.0a, the existing codebase complies with these rules:

| Package | Imports from | Compliant? |
|---------|-------------|:----------:|
| `packages/domain/` | `packages.domain.models` only (self) | ✅ |
| `packages/security/` | stdlib + approved crypto/JWT libraries only | ✅ |
| `packages/observability/` | stdlib only | ✅ |
| `packages/auth/` | `domain.*` models, `security.*`, `auth.*` | ✅ |
| `packages/api/` | `domain.*` (repository), `security.*`, `auth.*`, `fastapi` | ✅ |
| `apps/control-api/` | `packages.*`, `fastapi` | ✅ |

No forbidden imports exist.  Router endpoints delegate all DB queries
to `packages/domain/repository.py` — no `db.execute()` calls in route
handlers.  This ADR codifies the current compliance as the permanent rule.

## Consequences

- **Positive:** Clear mental model for every developer — "where does
  this code belong?" answered by layer purpose.  No cyclic imports
  can sneak in.  Domain logic is testable without HTTP fixtures.
  Security primitives are reusable outside web context.

- **Negative:** Strict layering can feel bureaucratic for small
  changes.  A developer adding a two-line helper may need to decide
  which package it belongs to.  Import-linter adds CI latency (future).

- **Risk:** The rule allowing domain modules to read environment settings
  directly could be misunderstood as permission for broader domain →
  security imports.  Mitigation: any new domain import from
  `packages.security` (beyond what's already prohibited) requires explicit
  approval and an ADR amendment.

## References

- ADR-001 — Service boundaries (no cross-service imports)
- ADR-008 — Testing strategy (repository separation enables unit tests
  without HTTP)
- ADR-011 — Transactional outbox (outbox relay is a separate worker,
  not a router)
- ADR-012 — Async I/O (infrastructure clients injected, not global)
- `apps/control-api/main.py` — current service entrypoint
- `packages/` — current shared library layout
