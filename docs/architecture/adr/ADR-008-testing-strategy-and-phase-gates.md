# ADR-008: Testing Strategy and Phase Gates

**Status:** Accepted
**Date:** 2026-07-03
**Phase:** 3.2e (External Audit Alignment)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

The current test suite (230 tests, 40 CI checks) includes a mix of behavioral tests (login flow, JWT validation, cookie attributes) and static/source-inspection tests (model column counts, FK relationships, seed script content checks). An external architecture audit raised the question of whether static inspection tests are sufficient for security-critical paths like authentication, RBAC, and tenant isolation.

## Decision

### Test Classification

| Category | Examples | Phase Gate Required? | Notes |
|----------|----------|---------------------|-------|
| **Behavioral** | Login returns 401, wrong audience rejected, cookie has HttpOnly, logout clears cookie | **Yes — mandatory** | Exercise the actual runtime (or mocked runtime with real routing). Prove the system *does the right thing*. |
| **Negative behavioral** | AD unavailable → 503, unknown provider → 422, invalid JWT → 401, replay attack → 401 | **Yes — mandatory for security paths** | Prove the system *prevents the wrong thing*. |
| **Static / source inspection** | Model has 25 tables, column `code` exists, seed has no passwords | **Allowed as lint/supplementary, NOT sufficient as gate** | Prove the code *looks right*. Does NOT prove it *works*. |
| **Structural / lint** | `py_compile`, JSON schema validation, compose config check, TypeScript `tsc --noEmit` | **Allowed as CI gating, but never a replacement for behavioral tests** | Syntax and structure checks. |

### Phase Gate Rules

1. **Every phase that touches auth, RBAC, RLS, or tenant isolation MUST include negative behavioral tests.** A PR that adds a new permission check without a test proving denial is rejected.
2. **Static inspection tests (model columns, FK counts, seed content) are allowed** as supplementary checks but do not count toward phase acceptance for security-critical paths.
3. **Future phases (3.3 RBAC, 3.4 behavioral tests, 4.x analytics) must not be accepted on static tests alone.** Each phase must demonstrate a behavioral test proving the new behavior works (or fails correctly for negative cases).
4. **Existing static tests are preserved** — they provide value as regression guards for schema changes and CI lint gates.

### Specific Requirements by Domain

| Domain | Minimum Behavioral Tests |
|--------|-------------------------|
| Auth (login/refresh/logout) | ✅ Phase 3.2d: 26 behavioral tests (mocked AuthService + TestClient) |
| /auth/me | ✅ Phase 3.2d: valid token, expired, wrong audience, garbage token, missing token |
| RBAC enforcement | Phase 3.3: must include negative test (no permission → 403, wrong role → 403) |
| RLS / tenant isolation | Phase 3.3+: must include cross-tenant access denial test |
| Rate limiting | Phase 3.3+: must include 429 after N attempts |
| Identity endpoints (protected) | Phase 3.3: must include 401 without JWT, 403 without permission |
| Audit integrity | Phase 3.4: must verify audit events are actually written to DB |

### What Phase 3.4 Adds

Phase 3.4 will introduce **real PostgreSQL behavioral tests** for auth and RBAC:
- Spin up a test PostgreSQL (or use testcontainers)
- Run migrations
- Seed test data
- Execute login → get JWT → call protected endpoint → verify 403/200
- Verify audit events written to `audit_events_operational`
- These tests will replace or supplement the current mocked-AuthService tests

## Consequences

- **Positive:** Security-critical paths are validated by behavior, not just structure. Negative tests prove the system rejects what it should.
- **Negative:** Behavioral tests require more setup (test DB, fixtures). Phase 3.4 will add this infrastructure.
- **Risk:** Mocked tests (Phase 3.2d) may miss DB-level issues (e.g., constraint violations, FK errors). Mitigation: Phase 3.4 adds real-DB tests before production gate.

## References

- `tests/test_phase3_auth_api.py` — 26 behavioral tests (Phase 3.2d)
- `tests/test_phase2_models.py` — 61 static inspection tests (Phase 2.0-2.1)
- `tests/test_phase3_security.py` — Mixed: some behavioral (JWT roundtrip), some static (config defaults)
- `scripts/ci/phase1-checks.sh` — CI lint gate
- `.github/workflows/phase1-ci.yml` — CI pipeline
