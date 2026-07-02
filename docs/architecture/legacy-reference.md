# Legacy Reference

**Original repository:** [retail-media-platform](https://github.com/santanas-dev/retail-media-platform)

The legacy repository contains the initial platform implementation.
It is **reference-only** for this enterprise rewrite.

## What May Be Reused as Knowledge

| Area | File/Section | How to Reuse |
|------|-------------|--------------|
| Business requirements | `docs/00-source-of-truth/TZ_Retail_Media_Platform_v2_5_Final_Hermes.extracted.md` | Source of truth for domain model, workflows, constraints |
| Architecture decisions | `docs/00-source-of-truth/rmp_rewrite_starting_decisions.md` | Starting decisions that informed ADR-001…005 |
| Enterprise review | `docs/00-source-of-truth/rmp_enterprise_architecture_review.md` | Risk assessment, deployment model critique |
| Backend domain logic | `backend/app/routers/`, `backend/app/services/` | Business rules for campaigns, placements, inventory, manifests |
| Portal UX patterns | `apps/portal-web/` | Admin UI workflows, form layouts, RBAC patterns |
| KSO runtime | `apps/kso_player/`, `apps/kso_sidecar_agent/` | Device lifecycle, manifest delivery, PoP proof generation |
| API contracts | `backend/app/schemas/` | Request/response shapes for reference when designing new APIs |
| Database schema | `backend/app/models/` | Legacy SQLAlchemy models — reference for domain entities, NOT to copy |

## What Must NOT Be Copied Directly

| Area | Reason |
|------|--------|
| `backend/` — entire directory | Tightly coupled to SQLAlchemy sync, Jinja2, old auth. Rewritten from scratch in `apps/control-api/` |
| `apps/portal-web/` — entire directory | Jinja2 server-side templates. New frontend is React 19 + TypeScript in `apps/admin-web/` |
| `apps/kso_player/`, `apps/kso_sidecar_agent/`, `apps/kso_state_adapter/` | KSO runtime prototypes. New adapters go into `apps/adapter-workers/` |
| Legacy `.env.example` | Contains old variable names and defaults. New `.env` schema coming in Phase 3 |
| `backend/alembic/` — legacy migrations | Start fresh with `apps/control-api/alembic/versions/001_init_channel_model.py` |
| Legacy `docker-compose.yml` | Replaced by `infra/compose/docker-compose.phase1.yml` |
| `tools/`, `players/`, `docs-site/` | Dev tooling and docs-site — not part of the rewrite |

## Review Process

When designing a new feature in the enterprise rewrite:

1. Read the relevant section of `TZ_Retail_Media_Platform_v2_5_Final_Hermes.extracted.md`.
2. Study the legacy implementation in `backend/` and `apps/portal-web/` for domain understanding.
3. Write a mini-design and get approval.
4. Implement in the enterprise repo from scratch — do not copy-paste legacy code.

## Key Architectural Differences

| Concern | Legacy | Enterprise Rewrite |
|---------|--------|-------------------|
| Core model | KSO-first (tight coupling) | Channel-agnostic foundation (ADR-001) |
| API framework | FastAPI sync + Jinja2 templates | FastAPI async + React SPA |
| Database | SQLAlchemy sync, one connection pool | SQLAlchemy async, `check_db_health`, connection lifecycle in lifespan |
| Auth | Local password hash + JWT | AD/SSO-ready identity foundation (Phase 2.1), no auth implementation yet |
| Device identity | HMAC device_secret inline | `device_certificates` table, mTLS-ready (ADR-003) |
| Monitoring | Basic logging | Structured JSON logs, correlation IDs, health/readiness probes (ADR-005) |
| Migration | Legacy Alembic in `backend/` | Fresh Alembic in `apps/control-api/alembic/` starting at `001` |
