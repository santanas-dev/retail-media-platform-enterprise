# PLAYER-001A — Player/KSO Import Audit & First Runnable Slice Plan

**Date:** 2026-07-27
**Status:** Audit complete — no blockers for PLAYER-001B.
**Scope:** Discovery/audit + docs only. No code import, no runtime implementation.
**Next:** R3 release to main (v0.10.0-preplayer-business-ready, stable baseline) → PLAYER-001B.

---

## 1. Existing Enterprise Contracts (all green)

### 1.1 Manifest Delivery

| What | Where | Status |
|------|-------|--------|
| Device gateway | `apps/device-gateway/main.py` (422 lines) | ✅ |
| GET /api/v1/device/manifest/latest | Lines 269–341 | ✅ Authenticated, rate-limited |
| Device auth | `get_device_id_from_token` (device JWT, `auth_provider="device"`) | ✅ |
| RLS bootstrap v4 | `set_device_rls_context` (production-safe, NOBYPASSRLS, no owner bypass) | ✅ |
| ETag 304 | Lightweight metadata query → content_hash + emergency state | ✅ |
| Redis cache | S-067 fast path, K1 emergency-aware skip | ✅ |
| Behavioral tests | `test_edge002_manifest_delivery.py` (5 tests) + `test_edge002fu_real_endpoint.py` | ✅ |
| Unit tests | `test_phase4_2c_delivery.py`, `test_phase4_2d_device_gateway.py` | ✅ |

### 1.2 Manifest Signature

| What | Where | Status |
|------|-------|--------|
| Signing/verification | `packages/contracts/manifest_signing.py` (49 lines) | ✅ |
| Algorithm | HMAC-SHA256 over canonical JSON (sorted keys, compact, excludes `signature`) | ✅ |
| Runtime verification | `packages/runtime/simulator.py` — `apply_manifest()` | ✅ K2 verified |
| K2 tests | `tests/test_k2_manifest_signing.py` (27 tests) | ✅ |
| Backward compat | `signing_key=""` → accepts unsigned (dev/test only) | ✅ |

### 1.3 Proof-of-Play (PoP) Ingestion

| What | Where | Status |
|------|-------|--------|
| API router | `packages/api/pop.py` (77 lines) — POST /api/v1/pop/batch | ✅ |
| Domain logic | `packages/domain/pop_ingestion.py` (386 lines) | ✅ |
| Validation gates | Schema version, device binding, dedup, duration bounds, playback result, manifest resolution, clock drift, cross-entity consistency | ✅ |
| Quarantine | Unknown manifests → 72h quarantine with dedup; clock drift → quarantine | ✅ |
| Dedup | `pop_dedup_index` unique constraint + savepoint retry pattern | ✅ |
| RLS proof | NOBYPASSRLS via `app.rmp_device_id` bootstrap (13 tests) | ✅ |
| Behavioral tests | `test_edge003_pop_ingestion.py` (6) + `test_edge003fu_nobypass_rls.py` (5) | ✅ |

### 1.4 Device Heartbeat

| What | Where | Status |
|------|-------|--------|
| POST /api/v1/device/heartbeat | `apps/device-gateway/main.py` lines 360–395 | ✅ |
| Fields | health_state, runtime_version, player_version (device_id from JWT) | ✅ |
| Behavioral tests | `test_edge004_heartbeat.py` (12 tests) | ✅ |

### 1.5 Emergency

| What | Where | Status |
|------|-------|--------|
| Backend state | K1: `emergency_overrides` table, admin endpoints | ✅ |
| Manifest propagation | `get_latest_manifest_metadata()` returns `emergency_active`, ETag includes it | ✅ |
| Player-side enforcement | **Deferred** — RuntimeSimulator has kill-switch (fail-closed, stale=fail) but no network emergency flag | ❌ Deferred |

### 1.6 Device Onboarding

| What | Where | Status |
|------|-------|--------|
| Admin creates code | `create_device_onboarding_code()` in repository | ✅ |
| Device uses code | `create_physical_device_onboard()` → device JWT | ✅ |
| Unit tests | `test_edge001_device_onboarding.py` (8 tests) | ✅ |
| Behavioral tests | `test_edge001_device_onboarding.py` (13 tests) | ✅ |
| Seed data | Seed has KSO-001 device, but `devices.manage` permission needed for admin | ⚠️ See §5 |

---

## 2. Existing Player/KSO Artifacts

### 2.1 In Enterprise Repo

| Component | File | Lines | What it does |
|-----------|------|-------|-------------|
| **RuntimeSimulator** | `packages/runtime/simulator.py` | 546 | Headless ADR-013 safety simulator: manifest apply (validate + sign verify + monotonic guard + atomic swap), kill-switch (fail-closed), render slot (6 safety gates), PoP emission (dedup + canonical fields), offline TTL |
| Manifest signing | `packages/contracts/manifest_signing.py` | 49 | HMAC-SHA256 canonical JSON sign/verify |
| Test helper | `make_test_manifest()` | ~45 | Factory for synthetically-signed manifests |

**No KSO/player/daemon/sidecar code in enterprise repo** — only the headless, in-memory RuntimeSimulator with no network, no I/O, no media playback.

### 2.2 In Old Repo (`santanas-dev/retail-media-platform`)

| Component | Files | Tests |
|-----------|-------|-------|
| **KSO Player** | 37 modules in `apps/kso_player/kso_player/` | 262 (all pass) |
| **KSO Sidecar** | 22+ modules in `apps/kso_sidecar_agent/kso_sidecar_agent/` | 327 (all pass) |
| Player shell | `player_shell/` (bootstrap.js, player.js, index.html) | N/A |

Key old-repo modules relevant to PLAYER-001B:

| Module | Function | Reusability |
|--------|----------|-------------|
| `manifest_client.py` | HTTP fetch manifest + parse JSON | **High** — pattern to follow |
| `manifest_store.py` | Filesystem cache with atomic write | Medium — may adapt |
| `heartbeat_client.py` | HTTP POST heartbeat to gateway | **High** — trivial |
| `pop_sender.py` | HTTP POST batch to /pop/batch | **High** — trivial |
| `pop_pickup.py` | Read local PoP events from filesystem | Medium |
| `device_auth_client.py` | Device registration + JWT acquisition | **High** — pattern to follow |
| `retry_backoff.py` | Retry with exponential backoff | **High** — copy-paste |
| `kill_switch.py` | File-flag kill-switch | Low — already in RuntimeSimulator |
| `runtime_daemon.py` | Main daemon loop | Low — not for first slice |
| `run_cycle.py` | Sidecar orchestration loop | Low — scope creep for first slice |

**Assessment:** Old repo has production-tested networking layer for manifest fetch, heartbeat, and PoP send. These are thin HTTP wrappers (few hundred lines total). The RuntimeSimulator in enterprise repo already has the safety logic but no network layer. The gap is small.

---

## 3. What's Missing (Gap Analysis)

| Layer | In Enterprise | In Old Repo | Gap |
|-------|--------------|------------|-----|
| Manifest fetch (HTTP) | ❌ | ✅ `manifest_client.py` | Need thin HTTP adapter |
| Manifest store (local) | ❌ | ✅ `manifest_store.py` (filesystem) | Can defer to in-memory for first slice |
| Heartbeat send (HTTP) | ❌ | ✅ `heartbeat_client.py` | Need thin HTTP adapter |
| PoP send (HTTP) | ❌ | ✅ `pop_sender.py` | Need thin HTTP adapter |
| Device auth (onboard → JWT) | ❌ (endpoint exists, client missing) | ✅ `device_auth_client.py` | Need thin HTTP adapter + seed onboarding code |
| Daemon loop | ❌ | ✅ `runtime_daemon.py` | Deferred — first slice is scripted, not daemon |
| Media sync | ❌ | ✅ `media_client.py`, `media_cache.py` | Deferred — no real media for first slice |
| Kill-switch fetch | ❌ | ❌ (local file-flag) | Deferred — RuntimeSimulator has in-memory kill-switch |
| Emergency fetch | ❌ | ❌ | Already in manifest (K1) — player reads from manifest |
| Runtime config | Minimal (signing_key) | ✅ `secret_store.py`, device_id persistence | Need minimal config layer |

**The gap is a thin HTTP adapter (~200-300 lines) connecting RuntimeSimulator to the three enterprise endpoints** (manifest/latest, heartbeat, pop/batch). The core safety logic is already proven.

---

## 4. PLAYER-001B — Minimal First Runnable Slice

### 4.1 Definition

**PLAYER-001B** is a local Python script that demonstrates the full device lifecycle against the enterprise backend:

```
1. Onboard device (acquire JWT from device-gateway)
2. Fetch signed manifest from device-gateway
3. Verify signature using manifest_signing
4. Apply manifest via RuntimeSimulator
5. Render one slot → emit PoP event
6. Send heartbeat
7. Send PoP batch to /pop/batch
8. Verify: backend reports PoP accepted
```

### 4.2 Architecture

```
┌─────────────────────────────┐
│     Enterprise Backend      │
│  - control-api (admin)      │
│  - device-gateway (8001)    │  ← HTTP
└──────────┬──────────────────┘
           │  JWT auth (Bearer)
┌──────────┴──────────────────┐
│     PLAYER-001B Client      │
│  - player_http.py (NEW)     │  HTTP adapter (~200 lines)
│  - RuntimeSimulator (EXIST) │  Safety + PoP + state
│  - manifest_signing (EXIST) │  Verify
│  - player_main.py (NEW)     │  Scripted flow (~100 lines)
└─────────────────────────────┘
```

### 4.3 New Files (100–300 lines total)

| File | Purpose | ~Lines | Depends on |
|------|---------|--------|------------|
| `apps/player/client/http.py` | HTTP adapter: manifest fetch, heartbeat send, PoP send, device onboard | 150 | `requests` |
| `apps/player/client/config.py` | ENV-based config: GATEWAY_URL, DEVICE_CODE/SECRET, SIGNING_KEY | 30 | — |
| `apps/player/main.py` | Scripted flow: onboard → fetch → verify → apply → render → heartbeat → PoP → verify | 80 | http.py, RuntimeSimulator, manifest_signing |
| `tests/test_player_client.py` | Contract test: integration with real device-gateway + control-api | 100 | pytest |

### 4.4 Explicitly NOT in PLAYER-001B

- Real media playback / rendering
- Kiosk UI / player shell
- Hardware control (X11, GPIO)
- Offline cache / filesystem persistence
- Command channel / WS
- Staged rollout
- Playlist engine beyond 1 slot
- Daemon loop / scheduler
- self.report_view UI
- Old repo import — written fresh against enterprise contracts

### 4.5 Why Not Import Old Repo Code

1. **Different contracts.** Old repo manifest schema, auth, and API paths differ from enterprise contracts (ADR-016, ADR-017, manifest_v1.schema.json).
2. **Different architecture.** Old repo is filesystem-heavy (state files, secret stores, rotation); enterprise RuntimeSimulator is in-memory, pure Python.
3. **Maintenance burden.** Adapting 5000+ lines of old code is riskier than writing 300 lines fresh against proven contracts.
4. **What IS reusable:** patterns (manifest fetch loop, retry/backoff), test structure, and the old repo's extensive test suite as reference.

---

## 5. Risk Review

| # | Risk | Severity | Mitigation in PLAYER-001B | Deferred |
|---|------|----------|--------------------------|----------|
| 1 | **Device JWT lifecycle** — tokens expire, need refresh | High | Use fresh JWT per test; document short-lived token pattern | Token refresh loop |
| 2 | **Manifest signing key config** — MUST match backend MANIFEST_SIGNING_KEY | High | ENV-based; contract test verifies signature round-trip | — |
| 3 | **Onboarding seed gap** — `devices.manage` permission not in seed | High | Pre-flight: add permission to seed OR use admin SQL bypass for test device | Seed fix in PLAYER-001B |
| 4 | **PoP idempotency** — duplicate events must be handled gracefully | Medium | RuntimeSimulator dedup works; HTTP retry must not double-send | — |
| 5 | **Offline/clock skew** — device clock ahead, stale timestamps | Medium | PoP ingestion handles clock drift (quarantine); manifest ETag prevents stale fetch | — |
| 6 | **Emergency enforcement** — player won't know about emergency unless manifest is re-fetched | Low | Manifest includes emergency flag (K1); ETag changes on emergency → refetch | Emergency polling |
| 7 | **Dev stack** — device-gateway must be running (port 8001), PostgreSQL required | Low | Docker compose; documented in runbook | — |
| 8 | **Python requests dependency** — new dependency for HTTP client | Low | Already in old repo; add to requirements.txt | — |

---

## 6. Decision: R3 Release First

**Recommendation:** R3 stable release to main BEFORE PLAYER-001B.

**Rationale:**
- Audit found **zero blockers** — all enterprise contracts are green, all gaps are well-understood.
- 35/40 reachable, pre-player business flow fully clickable — this is a coherent stable baseline.
- Tagging R3 (v0.10.0-preplayer-business-ready) before risky player work gives a rollback point.

**Sequence:**
1. ✅ PRODUCT-READINESS-001 (this audit)
2. → **R3** — merge develop → main, tag v0.10.0, CI green, docs update
3. → **PLAYER-001B** — first runnable KSO client (300 lines)

---

## 7. References

- `docs/architecture/contracts/universal-manifest-v1.md`
- `docs/architecture/contracts/proof-event-v1.md`
- `docs/architecture/adr/` — ADR-013 (safety), ADR-016 (manifest), ADR-017 (PoP), ADR-003 (device JWT)
- `PROJECT_STATE.md` — PLAYER-AUD-001 (old repo audit)
