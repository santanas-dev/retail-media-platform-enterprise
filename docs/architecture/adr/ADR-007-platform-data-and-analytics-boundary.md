# ADR-007: Platform Data and Analytics Boundary

**Status:** Accepted
**Date:** 2026-07-03
**Phase:** 3.2e (External Audit Alignment)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

The platform stack includes both PostgreSQL (operational) and ClickHouse (analytics) in the Phase 1 Docker Compose. An external architecture audit raised the question of whether ClickHouse is part of the current platform runtime or a future concern, and whether the data boundary between OLTP and OLAP is correctly defined for the current phase.

## Decision

### PostgreSQL → OLTP Source of Truth

PostgreSQL is the **sole operational data store** for the current platform runtime. All transactional data — organizations, channels, devices, campaigns, placements, inventory, users, roles, permissions, audit events — lives in PostgreSQL. Every mutation goes through PostgreSQL first.

### Operational Reports → PostgreSQL

Operational reports that serve the admin dashboard and advertiser cabinet **may query PostgreSQL directly**, using:
- Appropriate indexes on frequently-filtered columns
- Pre-aggregated materialized views for KPI dashboards (store occupancy, campaign performance)
- Separate read-replica if query load becomes a concern

PostgreSQL's query planner, combined with targeted indexes and `MATERIALIZED VIEW`, is sufficient for operational reporting at the scale of a retail network (hundreds of stores, tens of thousands of devices).

### ClickHouse → Downstream / Deferred

ClickHouse is **deferred** — it is not part of the current platform runtime. It will be introduced when:
- PoP (Proof of Play) events reach volume requiring columnar storage (>10M events/day)
- Multi-dimensional analytics queries exceed PostgreSQL's capability
- Long-term historical analysis and ad-hoc BI queries are needed

**Until then**, ClickHouse remains in `docker-compose.phase1.yml` as an infrastructure placeholder, marked as `# Deferred — not part of current runtime`. It is **not started** by default in development or CI. No application code depends on it.

### Transition Path (Phase 4+)

When ClickHouse is activated:
- PoP ingestor writes to both PostgreSQL (recent window, 30 days) and ClickHouse (full history)
- Analytics API reads from ClickHouse for historical queries, PostgreSQL for real-time dashboards
- Migration script backfills historical PoP data from PostgreSQL to ClickHouse
- This transition will be gated by its own ADR (ADR-0XX: Analytics Pipeline Activation)

## Consequences

- **Positive:** Clear operational boundary. No distributed transactions in current phase. Developers don't need ClickHouse running locally. Reduced infrastructure complexity.
- **Negative:** When ClickHouse is eventually needed, there will be a migration cost (backfill script, dual-write period, API routing logic). This is accepted as the price of deferring complexity.
- **Risk:** Operational reports on PostgreSQL may become slow if query patterns are not optimized. Mitigation: indexes and materialized views are explicitly allowed; read-replica is a documented option.

## References

- `infra/compose/docker-compose.phase1.yml` — ClickHouse service (deferred)
- `docs/architecture/phase-2-foundation.md` — Current foundation phase
- TZ v2.5 §23 (Data Flows and Storage), §24.10 (Database Requirements)
