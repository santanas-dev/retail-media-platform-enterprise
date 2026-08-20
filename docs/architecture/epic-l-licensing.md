# EPIC-L — Platform/Device Licensing Architecture

**Date:** 2026-07-30 (updated 2026-08-20 — Layer 1 design freeze, 001A0)
**Status:** Canon intake + Layer 1 design freeze. No implementation.
**Owner gate §08:** Approved 2026-07-30.

---

## Layer 1 — Seat Ledger Design Freeze (EPIC-L-SEAT-LEDGER-001A0)

**Status:** Discovery + decisions recorded. No migrations/models/API/UI.

This section freezes the eight Layer 1 decisions that the seat-ledger schema
MUST be compatible with. It is the source of truth for tasks 001A1–001A4 and
for the Layer 2 signed-license work. Any Layer 1 implementation that contradicts
these decisions is out of contract.

### Repo discovery (actual code, current `origin/develop`)

Anchors in the auditor document may be stale; the following was verified against
the current tree (commit `1b0452c`).

**A. `POST /device/onboard` flow** — `packages/api/device_routes/onboard.py` +
`packages/domain/repository.py` (EDGE-001 section).

- Transaction boundary: `get_db` (`packages/api/dependencies.py:21`) opens
  `async with session.begin():` — a single transaction per request, committed
  on context exit. No explicit `commit()` in the handler; the async context
  manager commits on success.
- Claim: `claim_onboarding_code` runs `UPDATE device_onboarding_codes SET
  status='claimed' WHERE code=:code AND status='active' AND expires_at > now
  RETURNING id` (atomic CAS, raw SQL for asyncpg). Two racing requests → one wins.
- `physical_devices` row creation: `create_physical_device_onboard` (`repository.py:6328`)
  builds `PhysicalDevice(status="active")` and `session.add()` — the row is
  inserted with `status='active'` at onboard time, in the same transaction.
- Code→device bind: `bind_code_to_device` (`repository.py:6411`) sets
  `status='used'`, `hardware_fingerprint_bound`, `physical_device_id`, `used_at`.
- Repeat request (idempotency): on `CODE_ALREADY_USED`, `get_device_by_fingerprint`
  is consulted; if the same fingerprint already owns the device, the existing
  identity + a fresh token is returned (no new device). A NEW code with a
  fingerprint that belongs to a DIFFERENT device → `revert_claim` then
  `FINGERPRINT_CONFLICT` 403.
- Atomic device + seat reserve: NOT currently possible — there is no seat
  concept. The existing transaction is atomic for device+code, so the seat
  reservation can be added inside the same `session.begin()` block at the
  enrollment choke-point (decision #4 below).

**B. `physical_devices.status` mutation paths.**

- The ONLY production write path that sets status is onboard
  (`create_physical_device_onboard` → `status='active'`).
- There is NO active→inactive/decommission endpoint or repository function, and
  NO re-activation path. `devices.py` (`identity_routes`) exposes read-only
  endpoints (`GET /devices`, `/devices/summary`, `/devices/{id}`) — no PATCH.
- Heartbeat (`record_device_heartbeat`, `repository.py:3110`) updates
  `last_heartbeat_at`, `health_state`, runtime/player versions — it does NOT
  touch `status`.
- `PhysicalDevice.status` is documented in `models.py:216` as a
  "Current state CACHE. See device_status_history for authoritative transitions."
  `DeviceStatusHistory` exists but no code writes to it yet.
- **Divergence found:** `apps/control-api/seed.py:206` inserts a `physical_devices`
  row directly with `status='unregistered'` (seed fixture `KSO-001`), bypassing
  onboard entirely. This is a third status path (seed-only, not API). The
  `unregistered` value is also the model default but is never produced by the
  API. Layer 1 must not assume the only statuses are the ones onboard writes.

**C. RLS / role posture.**

- `retail_media_app` is created NOBYPASSRLS in CI
  (`.github/workflows/phase1-ci.yml:292-323`) with an assert on
  `rolsuper=false` and `rolbypassrls=false`. control-api and UI-smoke run under
  this role.
- `physical_devices` is in `HIERARCHY_TABLES` (`020_multitenancy_retailer_id.py:84`)
  → `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` with `RETAILER_ONLY`
  policies (admin OR `retailer_id = ANY(app.rmp_scope_retailer_ids)`).
- Migration `023` adds a device bootstrap to the SELECT policy:
  `id = app.rmp_device_id` allows the device-gateway to read its own row before
  the retailer scope is known.
- `set_rls_context` (`packages/api/dependencies.py:153`) sets `app.rmp_user_id`,
  `app.rmp_is_admin`, `app.rmp_scope_retailer_ids`, `app.rmp_scope_advertiser_ids`.
  device-gateway uses its own `set_device_rls_context` bootstrap
  (`apps/device-gateway/main.py:135`).
- Behavioral tests: `tests/behavioral/conftest.py` points `DATABASE_URL` at
  `postgresql+asyncpg://retail_media_app:retail_media_app@...` (NOBYPASSRLS); a
  separate owner-role `_run_sql` does setup/cleanup with
  `set_config('app.rmp_is_admin','true')` to bypass RLS for fixtures only.

**D. license.* registry + CI/guard/import-boundaries.**

- `docs/product/feature-registry.yaml`: `license.view`, `license.upload`,
  `license.seat_release`, `license.report`, `license.enforce` — all `status:
  blocked`, `gap: "EPIC-L canon intake only. No implementation."`. Roles `[service]`.
- `user-journeys.md` §EPIC-L mirrors the same blocked list and non-goals.
- CI quality gates (from `phase1-ci.yml`): Python unit tests, import-boundaries
  (ADR-014), roadmap-consistency-audit (blocking, `--strict`), style-tokens,
  JSON-schema, production-config gate, behavioral PostgreSQL (ADR-008),
  UI-smoke (P0 subset, NOBYPASSRLS).
- `scripts/ci/check-import-boundaries.py` + `import-boundaries.toml` enforce
  layering (domain/auth/security/observability/contracts + cross-app + legacy).
  There is currently NO rule forbidding licensing↔commerce imports — decision #8
  makes that a required rule for 001A4.

### Layer 1 frozen decisions

1. **Single effective grant.** One installation has exactly one effective
   license grant. Limits from multiple grants are NOT summed; a second grant
   supersedes/replaces, never adds.

2. **Seat ↔ device identity.** A seat belongs to a device identity. Layer 2
   grant replacement MUST atomically transfer/re-bind occupied seats — the
   existing fleet must not lose seats or be shut off. In 001A0 we only describe
   a compatible data model; renewal/upload is NOT implemented here.

3. **Enrollment enforcement.** When enforcement blocks onboarding:
   HTTP **409**, body carries a stable `code` + Russian `message`.
   Codes: `LICENSE_MISSING`, `LICENSE_SEAT_LIMIT`, `LICENSE_EXPIRED`.
   Missing license blocks ONLY new enrollment (never an already-active device).
   DEV runs through an explicit dev-ingest license/fixture — no hidden bypass.

4. **Atomic capacity + create + reserve.** Capacity check, `physical_devices`
   insert, and seat reserve happen in ONE transaction. Concurrent enrollments
   use a row lock on the effective grant (or equivalent DB serialization).
   A bare `COUNT(*)` before INSERT is insufficient.

5. **Active device always holds a seat.** Release is allowed ONLY as part of a
   confirmed `active → inactive/decommission` transition. There is no manual
   "free a seat from a still-playing active device" operation.

6. **Peak seat-month.** The monthly peak is the exact maximum of concurrently
   open intervals `reserved_at <= t < released_at` over the calendar month, UTC.
   Daily snapshots are forbidden (they can miss an intraday peak).

7. **Effective state is computed.** `active` / `grace` / `expired` are derived
   from `valid_from`, `valid_until`, `grace_days` at check time. The `status`
   column is NOT the sole source of truth; `revoked` remains an explicit state.

8. **Contour isolation.** Licensing may read device/enrollment domain, but NOT
   `commerce_*` or advertiser-commercial. Контур 1 and Контур 2 must not mix.

### Task slicing

- **001A1 ✅** — schema/migration + dev-ingest fixture + repository read model.
- **001A2** — transactional enrollment choke-point + concurrency proof. ← NEXT
- **001A3** — decommission/release + exact monthly peak.
- **001A4** — report API + registry/import-boundaries + full behavioral matrix.
- **EPIC-L-SIGNED-LICENSE-002** — only after full Layer 1 closure.

### 001A1 implementation notes (as-built)

- Migration `034_license_seat_ledger.py` (`apps/control-api/alembic/versions/`).
  Tables `license_grants` + `license_seats`; ENABLE+FORCE RLS (admin-only context);
  partial unique indexes `uq_license_grants_single_current` (single current grant)
  and `uq_license_seats_open_per_device` (single open seat per device); CHECK
  constraints for non-negative limits/grace, valid window, release-after-reserve,
  Layer-1 source restriction (`dev-ingest` only); FK ondelete RESTRICT preserves
  license history (no cascade wipe of seat intervals).
- ORM models in `packages/domain/licensing.py` (`LicenseGrant`, `LicenseSeat`),
  registered on `Base.metadata` via a tail import in `models.py`. No FK/import to
  `commerce_*` or advertiser-commercial.
- Read model in `packages/domain/licensing_repository.py`:
  `get_effective_license`, `compute_effective_state` (active/grace/expired/
  revoked/missing from dates, not status), `count_occupied_seats` (open seats on
  active devices only), `capacity_of`, `free_of`. No GUC-setting; works under
  NOBYPASSRLS when the caller has set service/admin context.
- Dev-ingest: `scripts/dev/license-dev-ingest.py` — fail-closed (requires
  ENVIRONMENT ∈ {dev,development,local,test} AND LICENSE_DEV_INGEST_ENABLED=true),
  idempotent, deterministic `dev-ingest-0001` grant with source=dev-ingest.
  Not wired into the universal production seed and NOT an implementation of
  license.upload.
- Behavioral proof: `tests/behavioral/test_license_seat_ledger.py` (18 tests)
  under `retail_media_app` NOBYPASSRLS — no-context hides/blocks, admin context
  reads/writes, constraint proof, read-model proof, dev-ingest idempotency +
  production refusal.

### Layer 1 non-goals (unchanged from intake)

- No license issuer implementation; no `.lic` upload; no player/KSO changes;
  no advertiser billing; no feature statuses reachable in registry.
- A1 does NOT: reserve seats in device_onboard, enforce limits, decommission/
  release, peak_seats_for_month, report endpoint/UI, signed upload/JWS/CRL,
  or change feature-registry statuses. Manual release of an active seat is
  not added.

---

## Money Contours

Two independent money flows. Do not mix in tables, services, or UI.

| # | Контур | Стороны | Статус |
|---|--------|---------|--------|
| 1 | Лицензирование платформы/устройств | Оператор/licensee → вендор | EPIC-L |
| 2 | Коммерческий учёт размещений | Рекламодатель → оператор | v2.6 (deferred) |

**Shared touchpoint:** device identity / enrollment only.

---

## MVP Layer — What Must Exist Before Pilot

- **License entity:** license_id, licensee{id,name}, tier, issued_at, valid_from, valid_until (nullable)
- **Seat counting:** seat-month unit; active = device holds seat; metric = monthly peak occupied seats
- **Enforcement (soft):**
  - Playing screen never blanks (no kill switch)
  - Blocks only new enrollment over limit / after expiry
  - Expired / over-cap → alert + status (no screen blackout)
- **Format:** signed `.lic` file, JWS/JWT, EdDSA/ed25519
  - Public key in platform
  - Private key vendor-side only
  - Offline verification on device side

---

## Next Layer — Not in MVP

- License upload/management UI
- License report dashboard
- Seat release on decommission
- License audit log

---

## Later Layer (v2.6+)

- Advertiser commercial billing (Контур 2)
- Per-campaign placement accounting
- Invoice generation

---

## License Payload Matrix (Approved Fields)

```
┌────────────────────────┬──────────┬──────────────────────────────┐
│ Field                  │ Type     │ Notes                        │
├────────────────────────┼──────────┼──────────────────────────────┤
│ license_id             │ string   │ Unique license identifier    │
│ licensee.id            │ string   │ Operator ID                  │
│ licensee.name          │ string   │ Operator name                │
│ tier                   │ string   │ License tier                 │
│ issued_at              │ datetime │                              │
│ valid_from             │ datetime │                              │
│ valid_until            │ datetime │ Nullable = perpetual         │
│ max_devices            │ int      │ Max concurrent devices       │
│ overage_allowance      │ int      │ Extra seats before block     │
│ grace_days             │ int      │ Days before enforcement      │
│ features[]             │ [string] │ Enabled feature flags        │
│ installation_binding   │ string   │ Ties license to install      │
│ nonce                  │ string   │ Anti-replay                  │
│ schema_version         │ int      │ Payload schema version       │
│ kid (JWS header)       │ string   │ Key ID for verification      │
└────────────────────────┴──────────┴──────────────────────────────┘
```

---

## Seat-Hook Requirement (LICENSE-001)

Future real device enrollment MUST:

1. **Mint stable device identity** (if not already present)
2. **Reserve a license seat** — call seat allocation at enrollment boundary

Retrofit after deployed fleet is expensive. PLAYER/KSO implementation must not create enrollable devices without this hook.

Counting/enforcement may come later, but the identity/seat reservation boundary is required at enrollment.

---

## Explicit Non-Goals

- No license issuer implementation (vendor-side)
- No license models, migrations, or API endpoints
- No UI for license management
- No player/KSO code changes
- No advertiser billing (Контур 2)
- No feature statuses reachable in registry

---

## References

- `docs/product/user-journeys.md` §EPIC-L — full canon decisions
- `PROJECT_STATE.md` — EPIC-L-000 ✅ status
- `docs/product/feature-registry.yaml` — license.* feature IDs (blocked)
- `docs/architecture/player-001a-source-import-audit.md` — seat-hook note
- `docs/runbook/kso-player-client.md` — seat-hook note
