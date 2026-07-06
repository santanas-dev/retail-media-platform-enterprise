# Phase 4.2 — Delivery Domain

## Status: In Progress

- **4.2a** Architecture Lock (ADR-016) — 🔒 locked
- **4.2b** Delivery DB/Model Foundation — ✅ done (46cfe71 + fix)
- **4.2c** Manifest Generator Worker Skeleton — ✅ done (this commit)
- **4.2d** Device Gateway Delivery Endpoint — open
- **4.2e** Runtime Simulator Behavioral Tests — open

## Phase 4.2c: Manifest Generator Worker Skeleton

### Deliverable

`packages/domain/delivery.py` — business logic for campaign-to-manifest pipeline:

| Function | Role |
|----------|------|
| `check_eligibility(session, campaign_id)` | ADR-016 §2: status >= approved, valid flights, valid contract, >=1 resolving placement, >=1 ready creative |
| `resolve_targets(session, campaign_id)` | ADR-016 §3: placements → display_surfaces → physical_devices via branch/cluster/store/surface hierarchy |
| `compute_manifest_id(...)` | ADR-016 §5: deterministic SHA-256 over campaign + creatives + flights + placements + surfaces + device |
| `generate_manifest_json(...)` | ADR-016 §4: manifest JSON compatible with `packages/contracts/manifest_v1.schema.json` |
| `generate_manifests_for_campaign(session, campaign_id)` | Orchestrator: eligibility → resolution → per-device manifest generation → persistence → outbox |

### Key Decisions

- **No presigned URLs** in skeleton — `playlist[]` carries `creative_asset_id`, `sha256_checksum`, `media_type` references. Presigned URL generation deferred to Phase 4.2d+.
- **No storage credentials, no PII** — manifest JSON free of `storage_bucket`, `storage_key`, `access_key`, `secret_key`, `advertiser_organization_id`, emails, phones.
- **Idempotency** — `manifest_id` collision check before insert. Same campaign/device content → same manifest_id → no duplicate records.
- **Outbox** — `delivery.manifest.generated` on success, `delivery.manifest.failed` on failure, both in caller-owned transaction. No direct NATS publish.
- **Caller-owned transaction** — no commit inside helpers. Rollback → no partial state.
- **Import boundaries** — lives in `packages/domain/`, no api/auth/fastapi/NATS imports. Clean per `check-import-boundaries.py`.

### Test Coverage

| Suite | Count | What |
|-------|-------|------|
| Unit | 20 | Eligibility helpers, manifest_id determinism (6 cases), manifest JSON structure (6 fields), no secrets, no NATS, public API |
| Behavioral | 8 | Approved campaign → manifest, unapproved → no-op, idempotency, rollback, outbox, one device = one manifest, no targets → failed outbox |

### Outbox Events

| Event | When |
|-------|------|
| `delivery.manifest.generated` | Manifest created and marked generated for a device |
| `delivery.manifest.failed` | No targets resolved, or per-device generation failure |
