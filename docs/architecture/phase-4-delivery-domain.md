# Phase 4.2–4.3 — Delivery Domain + PoP/Reporting

## Status: In Progress

- **4.2a** Architecture Lock (ADR-016) — 🔒 locked
- **4.2b** Delivery DB/Model Foundation — ✅ done (`46cfe71` + `137ae0b`)
- **4.2c** Manifest Generator Worker Skeleton — ✅ done (`e467543` + `e05b960` + `0154681`)
- **4.2d** Device Gateway Delivery Endpoint — ✅ done (`c34d5fa` + `c8a369e` + `08b099e`)
- **4.2e** Runtime Simulator Behavioral Tests — ✅ done (`52a50fc` + fix)
- **4.3a** PoP and Reporting Architecture Lock (ADR-017) — 🔒 locked
- **4.3b** PoP Persistence Schema — ✅ done
- **4.3c** PoP Ingestion Endpoint — ✅ done
- **4.3d** Reporting Read-Only Endpoints — ✅ done
- **4.3e** Materialized Views / Exports — open

## Phase 4.3a: Proof-of-Play and Reporting Architecture (locked)

### Decision

ADR-017 locks the PoP pipeline architecture:

| Decision | Detail |
|----------|--------|
| PoP source | Device runtime only — after successful render |
| Ingestion endpoint | `POST /api/v1/pop/batch`, device JWT, idempotent by `event_id` |
| Validation | manifest_id known or quarantined, device_id = JWT sub, clock drift ±5min, duration bounds |
| Storage | PostgreSQL `pop_events_raw` + `pop_dedup_index`. ClickHouse deferred (ADR-007) |
| Reporting | Only `status=accepted` + `playback_result=success`. No fallback, no duplicates, no synthesized |
| Outbox | All ingestion events via outbox (ADR-011). No direct NATS |
| Audit | Ingestion attempts, quarantine reasons, dedup hits — all audit-logged |
| Phase split | 4.3b (schema) → 4.3c (ingestion) → 4.3d (reporting) → 4.3e (views/exports) |
| Behavioral proof | 12 required tests before 4.3c acceptance |

## Phase 4.3b: PoP Persistence Schema (done)

### Deliverable

Migration 009 — `pop_events_raw`, `pop_dedup_index`, `pop_ingestion_batches`.

| Asset | Details |
|-------|---------|
| Migration | `apps/control-api/alembic/versions/009_pop_persistence_schema.py` |
| Models | `PopEventRaw`, `PopDedupIndex`, `PopIngestionBatch` in `packages/domain/models.py` |
| Repository | 6 helpers in `packages/domain/repository.py`: `record_pop_raw_event`, `insert_pop_dedup_key`, `is_pop_event_duplicate`, `accept_pop_event`, `quarantine_pop_event`, `expire_pop_quarantine_events` |
| Constraints | `duration_ms` [1, 86400000], `status` ∈ {accepted,quarantined,rejected}, `playback_result` ∈ {success,fallback,interrupted,failed}, `event_id` UNIQUE |
| Indexes | 7 on raw table + 2 on batches |
| No RLS | Device-owned events, internal service ingestion |
| No FK on campaign_id/manifest_id | Quarantine path — events arrive before manifest |

### Key Decisions

- **No RLS** — events ingested by internal service, reporting APIs enforce scoping via JOINs.
- **campaign_id/manifest_id soft links** — no FK constraints to allow quarantine (unknown manifest).
- **campaign_verified defaults FALSE** — only `accept_pop_event` sets TRUE.
- **Caller-owned transactions** — no commit inside helpers. Rollback → no partial state.
- **No ClickHouse, no NATS, no FastAPI** in domain layer.
- **accepted = billing-grade** — `status='accepted'` AND `campaign_verified=true` AND `playback_result='success'`.

### Test Coverage

| Suite | Count | What |
|-------|-------|------|
| Unit (models) | 15 | Columns, constraints, secrets/PII, nullable rules, FKs, REQUIRED_TABLES, table count=44 |
| Unit (repo) | 6 | Helper signatures, import boundaries — no NATS/FastAPI/ClickHouse |
| Behavioral | 10 | Commit/rollback, dedup detection, quarantine (campaign_verified=false), duration constraints, status constraints, expire, accepted=playback_result success |

### Behavioral Proofs

| # | Test | What it proves |
|---|------|---------------|
| 1 | `test_accept_commit_stores_raw_and_dedup` | Accepted event creates raw + dedup entries, campaign_verified=true |
| 2 | `test_rollback_creates_nothing` | Rollback produces zero rows in both tables |
| 3 | `test_duplicate_detected` | `is_pop_event_duplicate` returns True after insert |
| 4 | `test_new_event_id_not_duplicate` | Unknown event_id returns False |
| 5 | `test_quarantine_sets_campaign_verified_false` | Quarantine stores campaign_verified=false, expires_at, null campaign/manifest |
| 6 | `test_quarantine_with_campaign_from_payload` | campaign_id from device payload stored but unverified |
| 7 | `test_expire_quarantine_events` | Expired quarantine → status=rejected, reason=quarantine_expired |
| 8 | `test_duration_too_small_rejected` | duration_ms=0 violates DB CHECK |
| 9 | `test_duration_too_large_rejected` | duration_ms=86400001 violates DB CHECK |
| 10 | `test_accepted_event_must_be_success` | accept_pop_event forces playback_result='success' |

## Phase 4.3c: PoP Ingestion Endpoint (done)

### Deliverable

`POST /api/v1/pop/batch` on control-api — device-submitted proof-of-play events.

| Property | Detail |
|----------|--------|
| Endpoint | `POST /api/v1/pop/batch` on `apps/control-api` |
| Auth | Device JWT only (`auth_provider=device`). User/admin tokens → 403 |
| Router | `packages/api/pop.py` — thin, no `db.execute`, delegates to domain |
| Service | `packages/domain/pop_ingestion.py` — pure domain, no FastAPI/NATS/ClickHouse |
| Batch max | 500 events (Pydantic `min_length=1, max_length=500`) |
| Batch semantics | Partial success per event. Response includes counts + per-event `(status, reason)` |
| Empty batch | Pydantic `min_length=1` → single 422 path (no redundant API guard) |

### Validation Pipeline (11-step per ADR-017)

| Step | Check | Failure |
|------|-------|---------|
| 1 | `schema_version` == `"1.0"` | reject: `unsupported_schema_version` |
| 2 | `event.device_id` == JWT `sub` | reject: `device_mismatch` |
| 3 | Dedup: `is_pop_event_duplicate` | duplicate (no insert) |
| 4 | `duration_ms` ∈ [1, 86400000] | reject: `invalid_duration` |
| 5 | `playback_result` == `"success"` | reject: `non_success_playback` |
| 6 | `rendered_at` ≥ `now - 30 days` | reject: `stale_event` |
| 7 | Clock drift: `rendered_at` ≤ `now + 5 min` | quarantine: `clock_drift` |
| 8 | Manifest resolution: lookup by `manifest_id` | unknown → quarantine: `unknown_manifest` (72h, `campaign_verified=false`) |
| 9 | Known manifest → cross-entity consistency: `campaign_id`, `device_id` vs `physical_device_id`, `surface_id` ∈ manifest surfaces, `creative_asset_id` ∈ manifest assets | reject: `campaign_mismatch` / `device_manifest_mismatch` / `surface_not_in_manifest` / `asset_not_in_manifest` |
| 10 | Accept: `accept_pop_event` with resolved `campaign_id` from manifest (trusted), `campaign_verified=true` | — |
| 11 | Dedup key: `insert_pop_dedup_key` + `session.flush()` before outbox | prevents same-tx race |

### Persistence

| Table | Role |
|-------|------|
| `pop_events_raw` | Accepted + quarantined events. `campaign_verified=true` only for accepted billing-grade events |
| `pop_dedup_index` | Dedup by `event_id` (UNIQUE PK). Same-tx flush ensures visibility |
| `pop_ingestion_batches` | Batch audit trail |
| `outbox_events` | Transactional outbox (ADR-011). No direct NATS |

### Outbox Events

| Event | When |
|-------|------|
| `pop.event.accepted` | Event passes all validation + cross-entity checks |
| `pop.event.quarantined` | Unknown manifest or clock drift (72h TTL, `campaign_verified=false`) |
| `pop.batch.ingested` | Per-batch summary with counts |

### Fixes Included

| Fix | Commit | What |
|-----|--------|------|
| Dedup flush | `59060ad` | `session.flush()` after `insert_pop_dedup_key` in all 3 paths — prevents same-tx/batch UniqueViolation |
| Fixture hardening | `d1d7bb5` | 4 behavioral proofs (clock_drift, device_manifest_mismatch, stale_event, duration_out_of_range), redundant API guard removed, outbox cleanup broadened, event_id overflow fixed |
| Cleanup time fence | `d97be76` | `AND created_at > NOW() - INTERVAL '10 minutes'` on PoP outbox cleanup |

### Test Coverage

| Suite | Count | What |
|-------|-------|------|
| Unit | 29 | Schemas (13), batch request (3), batch response (2), import boundaries (6), constants (5) |
| Behavioral | 27 | Accept, reject ×6 (schema, device, playback, campaign, surface, asset), device_manifest_mismatch, stale_event, duration_out_of_range, quarantine ×2 (unknown_manifest, clock_drift), dedup (same-tx), batch (mixed + dedup) |

### Deferred

- Reporting API (4.3d): read-only endpoints, aggregation queries, billing-grade reports
- Materialized views / exports (4.3e)
- ClickHouse analytics pipeline
- Frontend analytics dashboards

## Phase 4.3d: PoP Reporting Read Models (done)

### Deliverable

Read-only reporting queries over accepted PoP events. PostgreSQL only — no ClickHouse, no billing invoice logic, no frontend.

| Property | Detail |
|----------|--------|
| Router | `packages/api/identity.py` — under `/api/v1/identity/campaigns/{id}/pop/...` |
| Domain | `packages/domain/repository.py` — 3 reporting helpers |
| Auth | JWT required. `require_scoped_permission("campaigns.read", "advertiser")` + `set_rls_context` |
| Filters | `status='accepted' AND campaign_verified=true AND playback_result='success'` — no quarantined, rejected, duplicate, or fallback events |
| No ClickHouse | ADR-007 — PostgreSQL only, ClickHouse deferred |

### Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/identity/campaigns/{id}/pop/summary` | impressions_count, total_duration_ms, first/last_rendered_at, unique_devices, unique_surfaces |
| `GET /api/v1/identity/campaigns/{id}/pop/by-day` | Daily breakdown: date, impressions_count, total_duration_ms |
| `GET /api/v1/identity/campaigns/{id}/pop/by-surface` | Per-surface breakdown: surface_id, impressions_count, total_duration_ms |

### Repository Helpers

| Helper | Query |
|--------|-------|
| `get_campaign_pop_summary(session, campaign_id)` | Aggregate: COUNT, SUM, MIN, MAX, COUNT DISTINCT |
| `list_campaign_pop_by_day(session, campaign_id)` | GROUP BY cast(rendered_at, Date), ORDER BY date ASC |
| `list_campaign_pop_by_surface(session, campaign_id)` | GROUP BY surface_id, ORDER BY count DESC |

### Schemas

| Schema | Fields |
|--------|--------|
| `CampaignPopSummaryOut` | campaign_id, impressions_count, total_duration_ms, first_rendered_at, last_rendered_at, unique_devices, unique_surfaces |
| `CampaignPopByDayOut` | date (YYYY-MM-DD), impressions_count, total_duration_ms |
| `CampaignPopBySurfaceOut` | surface_id, impressions_count, total_duration_ms |

No PII, no secrets, no storage URLs, no contact info exposed.

### Test Coverage

| Suite | Count | What |
|-------|-------|------|
| Unit | 13 | Schemas (8), import boundaries (5) — no FastAPI/NATS/ClickHouse, no db.execute in router |
| Behavioral | 8 | Empty campaign → zeros, accepted counted, quarantined excluded, campaign_verified=false excluded, playback_result≠success excluded, different campaign isolation, by-day grouping, by-surface grouping |

### Deferred

- RLS cross-tenant behavioral tests (requires advertiser user + token for second org)
- Auth negative tests (401/403) via HTTP layer
- Materialized views / exports (4.3e)
- Frontend analytics dashboards

## Phase 4.2c: Manifest Generator Worker Skeleton (closed)

### Deliverable

`packages/domain/delivery.py` (776 lines) — business logic for campaign-to-manifest
pipeline.

| Function | Role |
|----------|------|
| `check_eligibility(session, campaign_id)` | ADR-016 §2: status ∈ {approved, scheduled, active}, valid flights, valid contract, ≥1 placement, ≥1 ready+approved creative |
| `resolve_targets(session, campaign_id)` | ADR-016 §3: placements → display_surfaces → physical_devices via branch/cluster/store/surface hierarchy. Only active surfaces on active devices. |
| `compute_manifest_id(...)` | ADR-016 §5: deterministic SHA-256 over campaign + creatives + flights + placements + resolved surfaces + device. Excludes `generated_at` per ADR-016. |
| `compute_campaign_version_hash(...)` | Deterministic SHA-256 over campaign-level inputs only (excludes surfaces/device) — used for delivery plan idempotency. |
| `generate_manifest_json(...)` | ADR-016 §4: manifest JSON compatible with `packages/contracts/manifest_v1.schema.json`. No presigned URLs, no secrets, no PII. |
| `generate_manifests_for_campaign(session, campaign_id)` | Orchestrator: eligibility → resolution → per-device manifest generation → persistence → outbox. Caller-owned transaction. |

### Key Decisions

- **Eligibility:** `approved`, `scheduled`, `active` only. `completed`/`archived`/`paused` → Manifest revoker (future), NOT generator. Creative must be `status=ready` AND `moderation=approved`.
- **Target resolution:** branch → cluster → store → display_surface → logical_carrier → physical_device. One manifest per device; multi-surface devices get one manifest with multiple `display_surfaces[]` entries.
- **Deterministic hashes:** `manifest_id` covers full content including resolution; `campaign_version_hash` covers campaign content only. Both SHA-256 with `‖` (U+2016) separators, sorted lists.
- **Manifest JSON:** schema_version `1.0`, no presigned URLs (skeleton only), no `storage_bucket`/`storage_key`, no PII. Signature structure placeholder (HMAC-SHA256 with empty value).
- **Idempotency:** `manifest_id` collision check before insert. Plan created only when `manifest_count > 0`. Re-run produces zero new rows and zero new outbox events.
- **Outbox:** `delivery.manifest.generated` on success, `delivery.manifest.failed` on no-targets or per-device failure. Both in caller-owned transaction. No direct NATS publish.
- **Caller-owned transaction:** no commit inside helpers. Rollback → no partial state.

### Test Coverage

| Suite | Count | What |
|-------|-------|------|
| Unit (Phase 4.2c) | 25 | Eligibility helpers, `manifest_id` determinism (7 cases), `campaign_version_hash` determinism (5 cases), manifest JSON structure (6 fields), no secrets, no NATS, public API |
| Behavioral (Phase 4.2c) | 12 | Approved campaign → manifest + outbox, unapproved/draft → no-op, completed → blocked, live/unknown → blocked, idempotency (manifest + plan), rollback no partial state, store_id placement resolution, one device = one manifest, no targets → failed outbox |
| CI | clean | Import boundaries, no NATS/fastapi in delivery.py |

### Behavioral Proofs

| Proof | Test |
|-------|------|
| Unapproved campaign → no manifest | `test_unapproved_campaign_no_manifest` |
| Completed campaign → blocked (ADR-016 §1 revoker) | `test_completed_status_no_manifest` |
| Noncanonical status → blocked | `test_live_status_no_manifest` |
| Approved campaign → manifest rows + outbox | `test_generates_manifest_for_approved_campaign` |
| One device = one manifest with surfaces | `test_one_device_one_manifest` |
| Store-level placement resolves | `test_store_placement_resolves` |
| No targets → `delivery.manifest.failed` | `test_no_targets_produces_failed_outbox` |
| Rollback → no partial state | `test_rollback_creates_no_partial_state` |
| Idempotent re-run (manifest dedup) | `test_idempotent_generation` |
| Idempotent re-run (plan/outbox dedup) | `test_plan_idempotent_on_rerun` |

### Outbox Events

| Event | When |
|-------|------|
| `delivery.manifest.generated` | Manifest created and marked generated for a device |
| `delivery.manifest.failed` | No targets resolved, or per-device generation failure |

## Phase 4.2d: Device Gateway Delivery Endpoint (closed)

### Deliverable

`apps/device-gateway/main.py` — `GET /api/v1/device/manifest/latest`

| Property | Implementation |
|----------|---------------|
| Auth | Device JWT only (`auth_provider=device`). User/admin tokens → 401 |
| Device ID | From token `sub` claim only. No query/path param |
| Status gate | `active` or `online` only. Offline/revoked/unregistered → 403 |
| Orphan detection | INNER JOIN Store — devices assigned to deleted stores → 404 |
| Manifest source | `get_latest_manifest_for_device(session, device_id)` in repository |
| Manifest filter | `physical_device_id` + `status=generated`, `generated_at DESC LIMIT 1` |
| Response shape | All 18 fields from `generate_manifest_json()` + `generated_at`/`content_hash` metadata |
| Schema validation | Response validates against `manifest_v1.schema.json` via `jsonschema.validate()` |
| `channel_type` | Resolved from device → device_type → channel (real DB chain, not hardcoded) |
| `offline_ttl_hours` | 168 (ADR-013 default) |
| Secrets/PII | No `storage_bucket`, `storage_key`, `presigned_url`, tokens, passwords, contact PII |
| ETag | `ETag` header = `content_hash` on 200 |
| If-None-Match | Match → `304 Not Modified` with empty body + ETag header |
| Direct SQL | Zero `session.execute`/`select` calls in router — all delegated to repository |
| No generation | No import/call of `check_eligibility`, `resolve_targets`, `compute_manifest_id`, `generate_manifest_json`, `generate_manifests_for_campaign` |
| No NATS/PoP | No NATS imports, no outbox/attempt/runtime/player code |

### Behavioral Proofs

| Proof | Test |
|-------|------|
| Valid device fetches manifest with required fields | `test_valid_device_fetches_manifest` |
| Cross-device isolation (non-existent device → 404) | `test_another_device_manifest_isolation` |
| No manifest → 404 | `test_no_manifest_returns_404` |
| Inactive device → 403 | `test_inactive_device_rejected` |
| ETag → 304 round-trip | `test_if_none_match_returns_304` |
| Missing auth → 401 | `test_no_auth_returns_401` |
| User token rejected → 401 | `test_user_token_rejected` |
| Response has zero secrets/storage/PII | `test_valid_device_fetches_manifest` (inline assertion) |

### Test Coverage

| Suite | Count | What |
|-------|-------|------|
| Unit (Phase 4.2d) | 10 | Auth dependency (5), response shape + schema validation (3), no-generation-in-endpoint (2) |
| Behavioral (Phase 4.2d) | 7 | Real PostgreSQL: valid fetch, 304 ETag, 401 no-auth, 401 user token, isolation, inactive 403, no manifest 404 |

### Deferred to Phase 4.3b+

- Runtime/player implementation
- PoP ingestion and reporting (4.3c–4.3e)
- NATS relay worker (actual JetStream publishing)
- Presigned URL generation (MinIO/S3)
- Manifest signature computation (real HMAC)
- Frontend campaign delivery status
