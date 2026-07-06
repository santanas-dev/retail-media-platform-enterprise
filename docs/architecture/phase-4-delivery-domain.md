# Phase 4.2 — Delivery Domain

## Status: In Progress

- **4.2a** Architecture Lock (ADR-016) — 🔒 locked
- **4.2b** Delivery DB/Model Foundation — ✅ done (`46cfe71` + `137ae0b`)
- **4.2c** Manifest Generator Worker Skeleton — ✅ done (`e467543` + `e05b960` + `0154681`)
- **4.2d** Device Gateway Delivery Endpoint — open
- **4.2e** Runtime Simulator Behavioral Tests — open

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

### Deferred to Phase 4.2d+

- Device-gateway `GET /device/v1/manifest` delivery endpoint
- Runtime/player implementation
- PoP ingestion and reporting
- NATS relay worker (actual JetStream publishing)
- Presigned URL generation (MinIO/S3)
- Manifest signature computation (real HMAC)
- Frontend campaign delivery status
