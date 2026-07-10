# ADR-009: Fail-Closed Scopes and PostgreSQL RLS

**Status:** Accepted
**Date:** 2026-07-04
**Phase:** 3.5a (Scope/RLS Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ADR-006 §6 established RBAC with server-side deny-by-default and scope types
(`global`, `branch`, `cluster`, `store`, `advertiser`). Phase 3.3 implemented
permission-gated identity endpoints (`require_permission`). Phase 3.4 added
real-DB behavioral tests proving correct 403 on missing permission.

What is still unresolved: **how scopes interact with permissions, and whether
the DB itself enforces tenant isolation.** The current schema has
`access_scopes`, `user_roles.scope_type/scope_id`, and `user_access_scopes`
tables — but no code reads them. Every identity endpoint returns all rows
regardless of the caller's scope.

The risk: a single missing `WHERE scope_id = ?` in an app-layer query leaks
data across tenants. Without a second defense (PostgreSQL RLS), every
advertiser, campaign, and placement endpoint is a potential data leak.

## Decision

### 1. Scope is a lens, not an escalator

A scoped role **narrows** visibility; it never **widens** it. The rules:

| Rule | Rationale |
|------|-----------|
| Global permission requires explicit unscoped role (`scope_type IS NULL`) | Admin is a deliberate assignment, not an accident of missing scope |
| Scoped role never grants global access | `user_roles(role=system_admin, scope_type=branch, scope_id=BR-001)` → admin permissions **only** within BR-001, not globally |
| Empty scopes = deny-all, never admin fallback | A user with zero scopes sees nothing, even if they have a role with permissions |
| Admin = explicit `system_admin` / `security_admin` role only | `operator` with all permissions is still not admin — scope still applies |
| Scope hierarchy: `global` > `branch` > `cluster` > `store`; `advertiser` is orthogonal | Branch-scoped user sees their branch and all descendant clusters/stores. Advertiser scope is a separate dimension — see below. |
| Unresolved scope = deny/error, never pass | If `scope_type` is set but `scope_id` points to a deleted/missing resource, the lookup fails closed |

**Advertiser scope is orthogonal to org hierarchy.** An advertiser-scoped
user sees only their own advertiser organization's campaigns/placements/media.
They have zero visibility into branches/clusters/stores — the hierarchy is
an internal concern. Conversely, an internal user with `branch` scope does
not automatically see advertiser data — advertiser access is an explicit
`advertiser` scope assignment.

### 2. Two-layer defense: app, then database

```
Request → JWT → ScopeContext (app layer) → permission + scope check
                                      ↓
                              SET LOCAL app.rmp_* (per transaction)
                                      ↓
                              PostgreSQL RLS (second defense)
```

**Layer 1 — App: `ScopeContext` dependency**

A FastAPI dependency that resolves the authenticated user's effective scopes
from `user_roles` + `user_access_scopes` + `role_permissions`. Returns:

- `is_admin: bool` — `system_admin` or `security_admin`, unscoped
- `global_permissions: set[str]` — permission codes from unscoped roles
- `scoped_permissions: dict[ScopeKey, set[str]]` — `{(branch, BR-001): {devices.read, ...}, ...}`
- `effective_scopes: set[ScopeKey]` — all scope keys the user can access

`ScopeKey` is a composite: `(scope_type, scope_id)`. Hierarchy expansion
happens at resolution time: a branch-scoped user automatically inherits
all descendant clusters and stores.

`require_scoped_permission(perm, scope_type=None)` factory:

```
if is_admin AND perm ∈ global_permissions → pass (admin bypass)
elif perm ∈ scoped_permissions for any scope → pass
else → 403 PERMISSION_DENIED

if scope_type specified AND scope not in effective_scopes → 403 SCOPE_RESTRICTED
```

**Layer 2 — Database: PostgreSQL RLS**

Before every tenant-scoped query, the app layer executes:

```sql
SELECT set_config('app.rmp_user_id', :user_id, true);          -- local to transaction
SELECT set_config('app.rmp_is_admin', :is_admin::text, true);
SELECT set_config('app.rmp_scope_branch_ids', :branch_csv, true);
SELECT set_config('app.rmp_scope_cluster_ids', :cluster_csv, true);
SELECT set_config('app.rmp_scope_store_ids', :store_csv, true);
SELECT set_config('app.rmp_scope_advertiser_ids', :advertiser_csv, true);
```

RLS policies on tenant tables filter rows by these session variables.
Example for `advertiser_organizations`:

```sql
CREATE POLICY advertiser_scope_sel ON advertiser_organizations
    FOR SELECT
    USING (
        COALESCE(
            NULLIF(current_setting('app.rmp_is_admin', true), ''),
            'false'
        )::bool = true
        OR id = ANY(
            COALESCE(
                string_to_array(
                    NULLIF(current_setting('app.rmp_scope_advertiser_ids', true), ''),
                    ','
                ),
                '{}'::text[]
            )
        )
    );

ALTER TABLE advertiser_organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE advertiser_organizations FORCE ROW LEVEL SECURITY;
```

Key safety rules enforced by the policy:
- `current_setting(..., true)` — second argument `true` (PostgreSQL 16+
  `missing_ok`) returns NULL when the variable was never `SET`, instead
  of raising ``unrecognized configuration parameter``.
- `NULLIF(..., '')` — treats an empty string (explicit `SET TO ''`) as unset.
- `COALESCE(..., 'false')` — defaults to deny for the admin flag.
- `COALESCE(..., '{}'::text[])` — defaults to empty array for scope lists
  (empty array never matches any row → deny-all).

**Every RLS policy in the platform MUST use this pattern.**  A forgotten
`SET LOCAL` must result in zero rows, never a 500 error.

**Why both layers?** The app layer provides clear 403 errors with
`PERMISSION_DENIED` / `SCOPE_RESTRICTED` codes. PostgreSQL RLS is the
seatbelt: if a future developer forgets a `WHERE` clause, the DB silently
filters rows instead of leaking data. Defense in depth.

### 3. Tenant table classification

**Tables requiring RLS (tenant-scoped):**

| Table | Scope FK | RLS filter |
|-------|----------|------------|
| `advertiser_organizations` | `id` (PK, IS the advertiser) | `id` in advertiser scope |
| `advertiser_user_memberships` | derived from `advertiser_organization_id` | `advertiser_organization_id` via org |
| `campaigns` | `advertiser_id` | `advertiser_id` |
| `placements` | derived from `campaign_id` | `campaign.advertiser_id` |
| `media_assets` | `uploaded_by` → advertiser | `uploaded_by` / advertiser membership |
| `creative_versions` | derived from `media_asset_id` | `media_asset.uploaded_by` |
| `orders` | `advertiser_id` (implied via contract) | advertiser hierarchy |
| `contracts` | `advertiser_id` | `advertiser_id` |
| `branches` | `id` | `id` in branch hierarchy |
| `clusters` | `branch_id` | `branch_id` in hierarchy |
| `stores` | `cluster_id` | `cluster_id` in hierarchy |

**Tables that are global (no RLS, projection only):**

| Table | Reason |
|-------|--------|
| `channels`, `device_types`, `capability_profiles` | Platform-wide reference data |
| `permissions`, `roles`, `role_permissions` | RBAC metadata — read by all authenticated users |
| `users` | Identity table — projection restricts visible fields, not rows |
| `audit_events_operational` | All events exist; non-admin sees subset via app-layer filter, not RLS |
| `login_attempts`, `refresh_sessions`, `local_credentials` | Security tables — accessed only by auth service, never user-facing |

### 4. First RLS pilot: `advertiser_organizations` + `advertiser_user_memberships`

**Target:** Phase 3.5b.

**Why these tables:**

1. **Simplest FK structure** — single `advertiser_id` FK, no hierarchical
   scope chains. No branch→cluster→store parent lookups needed.
2. **Clear ownership boundary** — advertiser user sees only their own org.
   Internal staff with `advertisers.read` can see all, or scoped subset.
3. **Low blast radius** — no campaigns, placements, or media exist yet.
   FK cascade risk is limited to `advertiser_user_memberships`.
4. **Easy to test** — login as advertiser → `GET /api/v1/advertisers` →
   response contains only the user's own organization. Cross-tenant:
   try to access another org's ID → 403 at app layer, 0 rows from RLS.
5. **Proves the `SET LOCAL` pattern** — validates that `app.rmp_*` session
   variables work correctly with async SQLAlchemy + connection pooling.

**What the pilot does NOT cover:**
- Hierarchical scope expansion (branch→cluster→store) — deferred to 3.5c
- Cross-table RLS (campaigns filtered by `campaign.advertiser_id` joined
  through `advertiser_organizations`) — deferred to 3.5c
- RLS on INSERT/UPDATE/DELETE — Phase 3.5b is SELECT-only
- `FORCE ROW LEVEL SECURITY` on tables with existing data — only on new
  migration; existing data is dev seed, not production

### 5. Phase 3.5b implementation plan

**Migration (`004_rls_pilot.py`):**

1. Create helper function `app.set_rmp_session_vars(user_id, is_admin, branches, clusters, stores, advertisers)` — takes arrays, produces CSV
2. `ALTER TABLE advertiser_organizations ENABLE ROW LEVEL SECURITY`
3. `ALTER TABLE advertiser_organizations FORCE ROW LEVEL SECURITY`
4. `CREATE POLICY advertiser_scope_sel ON advertiser_organizations FOR SELECT USING (...)` — admin bypass OR advertiser_id in scope.  `FOR SELECT` (not `FOR ALL`) for the pilot; SELECT-only per the pilot scope.  `USING` filters existing rows; `WITH CHECK` (needed for INSERT/UPDATE/DELETE policies) is deferred to 3.5c.
5. Same for `advertiser_user_memberships` (inherits from `advertiser_organization_id`)
6. Index on `advertiser_organizations.id` (already PK) and `advertiser_user_memberships.advertiser_organization_id` (already FK)

**Code changes:**

1. `packages/domain/scopes.py` — `ScopeKey`, `ScopeContext`, `resolve_scope_context(session, user_id)` — queries `user_roles` + `role_permissions` + `access_scopes`
2. `packages/api/dependencies.py`:
   - `get_scope_context(db, current_user)` — resolves `ScopeContext` using the
     same DB session that `get_db()` opened.  Must be called after
     `get_current_active_user` (which loads the user record).
   - `require_scoped_permission(perm, scope_type=None)` — factory dependency
     that checks both permission AND scope.
   - `set_rls_context(db, scope)` — a separate dependency (or router-level
     `dependencies=[Depends(set_rls_context)]`) that calls `SET LOCAL` after
     both the transaction and the scope context are ready.  Depends on
     `get_db` + `get_scope_context`.
3. `packages/domain/database.py` — `set_rmp_session_vars(session, scope: ScopeContext)` — executes `SET LOCAL app.rmp_*` on the active connection
4. Existing `require_permission` endpoints continue to work; new scoped
   endpoints use `require_scoped_permission`

**Dependency ordering (no circular dependency):**

```
get_db()               → starts transaction, yields session
get_current_active_user → validates JWT, loads user row (uses session)
get_scope_context()     → loads roles/permissions/scopes (uses session)
set_rls_context()       → SET LOCAL app.rmp_* on session (side-effect only)
route handler           → tenant queries now filtered by RLS + app-layer
```

`set_rls_context` is wired as a router-level dependency on tenant-scoped
routers, so every route handler on that router automatically gets RLS
variables set before its queries run.  Individual handlers that need
explicit scope checks also use `Depends(require_scoped_permission(...))`.

**Behavioral tests (new file `tests/behavioral/test_scope_rls.py`):**

1. Advertiser user → `GET /api/v1/advertisers` → only own org (200)
2. Advertiser user → `GET /api/v1/advertisers/{other_org_id}` → 403 or 404
3. Internal user with `branch` scope → `GET /api/v1/advertisers` → 403 (no advertiser scope)
4. Admin (unscoped system_admin) → `GET /api/v1/advertisers` → all orgs (200)
5. RLS-only defense: app-layer scope filter intentionally removed → RLS still blocks (0 rows)
6. No scope user (role without any scope assignment) → 403 on all tenant endpoints

**Rollback strategy:**

RLS policies are additive and reversible:
- `DROP POLICY IF EXISTS ... ON advertiser_organizations`
- `ALTER TABLE advertiser_organizations DISABLE ROW LEVEL SECURITY`
- No data migration, no column changes — pure DDL
- `SET LOCAL` variables are transaction-scoped — no persistent state to clean up

### 6. Scope resolution algorithm

```python
async def resolve_scope_context(session, user_id: str) -> ScopeContext:
    user = await find_user_by_id(session, user_id)
    if not user or user.status != "active":
        return ScopeContext.empty()

    # Load all user_roles with their role's permissions
    user_roles = await get_user_roles_with_permissions(session, user_id)

    is_admin = False
    global_permissions: set[str] = set()
    scoped_permissions: dict[ScopeKey, set[str]] = {}
    effective_scopes: set[ScopeKey] = set()

    for ur in user_roles:
        perms = {p.code for p in ur.role.permissions}

        if ur.scope_type is None:
            # Unscoped → global
            global_permissions |= perms
            if ur.role.code in ("system_admin", "security_admin"):
                is_admin = True
        else:
            # Scoped → narrow
            key = ScopeKey(ur.scope_type, ur.scope_id)
            scoped_permissions.setdefault(key, set()).update(perms)
            effective_scopes.add(key)

    # Expand hierarchy: branch → all descendant clusters → all descendant stores
    expanded = expand_hierarchy_scopes(session, effective_scopes)
    effective_scopes |= expanded

    return ScopeContext(
        user_id=user_id,
        is_admin=is_admin,
        global_permissions=global_permissions,
        scoped_permissions=scoped_permissions,
        effective_scopes=effective_scopes,
    )
```

**Hierarchy expansion** (branch → clusters → stores) runs at scope resolution
time, not per-request. For `branch` scope `BR-001`:
- Query `SELECT id FROM clusters WHERE branch_id = 'BR-001'` → `{CL-001, CL-002}`
- Query `SELECT id FROM stores WHERE cluster_id IN (...)` → `{ST-001, ST-002, ST-003}`
- Result: `effective_scopes = {(branch, BR-001), (cluster, CL-001), (cluster, CL-002), (store, ST-001), (store, ST-002), (store, ST-003)}`

This expansion is cached per-request (the `ScopeContext` object). Hierarchy
changes between requests are picked up automatically.

### 7. Scoped projection for identity endpoints

Current identity endpoints (`/api/v1/identity/users`, `/roles`, `/permissions`,
`/audit-events`) are protected by permission only. After scope enforcement:

- `users.read` with `branch` scope → users with roles scoped to that branch
  (or unscoped). Does NOT list all users.
- `audit.read` with `store` scope → audit events for that store only.
- `roles.read` / `permissions.read` → unchanged (global metadata).

For non-admin callers, `UserOut` projection strips `auth_provider`,
`external_subject`, and `is_break_glass` — these are admin-only fields.

### 8. Advertiser scope is a separate dimension

Advertiser scope (`scope_type=advertiser`) operates independently of
org-hierarchy scope:

| User | Hierarchy scope | Advertiser scope | Sees |
|------|----------------|-----------------|------|
| Admin | global (unscoped) | — | Everything |
| Branch manager | branch BR-001 | — | Devices/stores in BR-001 branch; NO advertiser data |
| Advertiser user | — | advertiser ADV-001 | Only ADV-001 campaigns/placements/media; NO org hierarchy |
| Regional analyst | cluster CL-001 | advertiser ADV-001 | Devices in CL-001 cluster AND ADV-001 campaigns in those stores |

A user can have multiple scopes across both dimensions. The effective access
is the union of individually scoped permissions — never the intersection.

### 9. Database role privileges

RLS is only effective if the database role executing queries does not have
the `BYPASSRLS` attribute or superuser privileges.  The platform MUST enforce:

| Role | Purpose | `BYPASSRLS` | Superuser | Notes |
|------|---------|:-----------:|:---------:|-------|
| App runtime (`retail_media_app`) | FastAPI connection pool | **NO** | **NO** | Regular user with `CONNECT` + DML on schema. `FORCE ROW LEVEL SECURITY` ensures even table owner cannot bypass RLS. |
| Migration runner (`retail_media_admin`) | Alembic `upgrade head` | Temporarily YES | **NO** | Needs DDL rights (`CREATE TABLE`, `ALTER TABLE … FORCE RLS`). Revoke `BYPASSRLS` after migration completes. |
| Dev `docker-compose` user | Local development only | YES (dev convenience) | YES (dev convenience) | `POSTGRES_USER=retail_media` in `docker-compose.phase1.yml` — this is a **dev-only shortcut**. Production must use distinct, least-privilege roles. |
| seed runner | `python apps/control-api/seed.py` | NO | NO | `INSERT`/`UPDATE` on seed tables. Must respect RLS — if seed inserts tenant data, it must `SET LOCAL` first. |

**Production invariant:** the PostgreSQL role used by the FastAPI connection
pool MUST be `NOBYPASSRLS` and NOT a superuser.  This is validated at startup
by the readiness check (Phase 3.5b adds a `SELECT rolsuper, rolbypassrls FROM
pg_roles WHERE rolname = current_user` assertion to `/health/ready`).

**Background workers** (NATS-based orchestrator, pop-ingestor, adapter-workers)
do not go through FastAPI middleware.  They will need their own RLS context
mechanism — either a dedicated worker DB role with system-scoped privileges,
or a per-job `SET LOCAL` preamble that resolves scopes from the job payload.
This is deferred to Phase 3.6 (worker RLS).

> **S-019 (2026-07-10):** Compose now enforces the three-role architecture:
> `retail_media_owner` (DDL/migrations/seed) and `retail_media_app`
> (NOBYPASSRLS — control-api, device-gateway, orchestrator-worker).
> Background workers call `set_worker_admin_context()` to set
> `app.rmp_is_admin=true` before each transaction — a pilot-grade
> system-wide scope.  Per-worker payload-based scope resolution remains
> deferred to Phase 3.6.  See `docs/runbook/delivery-runtime.md`.

## Consequences

- **Positive:** Two-layer defense means a missing app-layer filter is caught
  by PostgreSQL RLS. Advertiser data is isolated from internal hierarchy, and
  vice versa. The `SET LOCAL` pattern is transaction-scoped — no connection
  state leakage between concurrent requests.
- **Negative:** Every tenant-scoped query now requires `SET LOCAL` preamble
  (adds ~1ms overhead). RLS policy maintenance grows with table count — each
  new tenant table needs a policy migration. `FORCE ROW LEVEL SECURITY`
  means even migration scripts must respect policies — may complicate seed
  and data migrations.
- **Risk:** If `SET LOCAL` is forgotten on a new endpoint, RLS returns zero
  rows (fail-closed) — the endpoint appears to "work" but returns empty.
  Mitigation: behavioral tests that assert non-zero row counts for scoped
  users. If RLS policy is misconfigured (wrong FK column), data leaks.
  Mitigation: cross-tenant behavioral tests (user A must not see user B's
  data) for every tenant table.

## References

- ADR-006 §6 — RBAC enforcement model, scope types
- ADR-008 — testing strategy, behavioral test requirements
- ERD v2.5 §§1.1–1.2 — access_scopes, user_roles, advertiser tables
- `packages/domain/models.py` — AccessScope, UserRole, UserAccessScope
- `packages/api/dependencies.py` — require_permission pattern
- `tests/behavioral/test_auth_rbac_behavior.py` — deny-by-default proven
- PostgreSQL docs: [CREATE POLICY](https://www.postgresql.org/docs/current/sql-createpolicy.html)
- PostgreSQL docs: [ALTER TABLE ... FORCE ROW LEVEL SECURITY](https://www.postgresql.org/docs/current/sql-altertable.html)
