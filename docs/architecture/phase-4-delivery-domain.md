# Phase 4.2–4.3 — Delivery Domain + PoP/Reporting

## Status: In Progress

- **4.2a** Architecture Lock (ADR-016) — 🔒 locked
- **4.2b** Delivery DB/Model Foundation — ✅ done (`46cfe71` + `137ae0b`)
- **4.2c** Manifest Generator Worker Skeleton — ✅ done (`e467543` + `e05b960` + `0154681`)
- **4.2d** Device Gateway Delivery Endpoint — ✅ done (`c34d5fa` + `c8a369e` + `08b099e`)
- **4.2e** Runtime Simulator Behavioral Tests — ✅ done (`52a50fc` + fix)
- **4.3a** PoP and Reporting Architecture Lock (ADR-017) — 🔒 locked
- **4.3b** PoP Persistence Schema — open
- **4.3c** PoP Ingestion Endpoint — open
- **4.3d** Reporting Read-Only Endpoints — open
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
| Behavioral proof | 9 required tests before 4.3c acceptance |

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
