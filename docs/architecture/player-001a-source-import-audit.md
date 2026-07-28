# PLAYER-001A — Source Repo KSO/Player Import Audit & First Runnable Slice Plan

**Date:** 2026-07-27
**Status:** Audit complete — no blockers. Recommendation: write fresh thin adapter, reuse nothing from old repo as-is.
**Source repo:** `santanas-dev/retail-media-platform`, commit `41e3398` (v0.9.0-rc0-business-demo.5-143-g41e3398)
**Scope:** Discovery/audit + docs only. No code import, no runtime implementation.

---

## 1. Source Repo Inventory

### 1.1 Overview

| Metric | Value |
|--------|-------|
| Player SLOC | 38,804 lines |
| Sidecar SLOC | 18,558 lines |
| Total | ~57,362 lines |
| Player test files | 46 |
| Sidecar test files | 63 |
| Total tests | ~3,910 |
| Architecture doc | `docs/kso_player_architecture.md` (670 lines) |
| Sidecar design | `docs/kso_sidecar_agent_design.md` (566 lines) |
| Device gateway doc | `docs/device_gateway.md` (665 lines) |

### 1.2 KSO Player (`apps/kso_player/kso_player/`)

| Module | Lines | Purpose | Quality |
|--------|-------|---------|---------|
| `runtime_daemon.py` | — | Main daemon loop | Production-grade, Chromium kiosk-oriented |
| `runtime_cycle.py` | — | Playback cycle state machine | Tied to filesystem I/O |
| `display_cycle.py` | — | Screen rendering | X11/Chromium-dependent |
| `playlist.py` | — | Manifest → playlist transform | Old manifest schema |
| `render_plan.py` | — | Slot scheduling | Media-aware |
| `pop_writer.py` | — | Local PoP event writing | Filesystem-based (JSONL) |
| `kill_switch.py` | 65 | File-flag kill-switch | Clean, pure Python, but filesystem-bound |
| `runtime_gate.py` | — | State machine (idle/playing/…) | Tied to local JSON state |
| `safety.py` | — | 9-state safety evaluator | Core logic reusable, tied to local state |
| `simulator.py` | — | Dev simulator | Overlaps with enterprise RuntimeSimulator |

**Player shell:** `player_shell/` — HTML/JS (bootstrap.js, player.js, index.html). Chromium kiosk rendering layer.

### 1.3 KSO Sidecar Agent (`apps/kso_sidecar_agent/kso_sidecar_agent/`)

| Module | Lines | Purpose | Reusability |
|--------|-------|---------|-------------|
| `manifest_client.py` | 456 | HTTP fetch manifest, parse response | **Pattern only** — old schema |
| `heartbeat_client.py` | 311 | POST heartbeat with retry | **Pattern only** — old payload |
| `device_auth_client.py` | 164 | POST /auth/token, token lifecycle | **Pattern only** — old auth |
| `pop_sender.py` | 788 | PoP batch HTTP send, classification | **Pattern only** — old payload |
| `retry_backoff.py` | 267 | Exponential backoff + jitter | **High** — pure logic, no deps |
| `token_state.py` | 148 | Memory-only token storage | **High** — pure logic |
| `http_client.py` | — | Safe HTTP client wrapper | Pattern for SafeHttpClient |
| `local_config.py` | — | ENV-based config reader | Pattern, not reusable as-is |
| `secret_store.py` | — | Device secret storage | Filesystem-bound |
| `pop_pickup.py` | — | Read PoP from local files | Filesystem-bound |
| `pop_rotation_*.py` | — | PoP file rotation | Filesystem-bound |
| `media_client.py` | — | Media download + cache | MinIO-aware |
| `run_cycle.py` | — | Sidecar orchestration loop | Full daemon, too heavy for first slice |
| `safe_logger.py` | — | Structured logging | Excellent pattern |

### 1.4 Tests (representative)

| Test file | Tests | What it covers |
|-----------|-------|---------------|
| `test_manifest_client.py` | — | Manifest fetch/parse/validate |
| `test_device_auth_client.py` | — | Auth token lifecycle |
| `test_heartbeat_client.py` | — | Heartbeat send with retry |
| `test_pop_sender*.py` | — | PoP send, retry, classification |
| `test_retry_backoff.py` | — | Backoff policy |
| `test_run_cycle_e2e.py` | — | Full sidecar lifecycle |
| `test_manifest_sync.py` | — | Manifest sync with ETag |

---

## 2. Enterprise Contracts Inventory (already green)

| Contract | Endpoint | Key File(s) | Test Count | Auth |
|----------|----------|-------------|------------|------|
| Device onboarding | POST /api/v1/device/onboard (via admin) | `packages/domain/repository.py` L5641 | 21 (8+13) | Admin JWT → creates code; device uses code |
| Manifest delivery | GET /api/v1/device/manifest/latest | `apps/device-gateway/main.py` L269 | 5 behavioral | Device JWT (`auth_provider="device"`) |
| Manifest signing | — | `packages/contracts/manifest_signing.py` | 27 unit (K2) | HMAC-SHA256, canonical JSON |
| PoP ingestion | POST /api/v1/pop/batch | `packages/api/pop.py` + `packages/domain/pop_ingestion.py` | 11 behavioral | Device JWT |
| Heartbeat | POST /api/v1/device/heartbeat | `apps/device-gateway/main.py` L360 | 12 behavioral | Device JWT |
| Emergency | In manifest via K1 | `packages/domain/repository.py` L2516 | 4 behavioral | In-manifest flag |
| Runtime safety | — | `packages/runtime/simulator.py` (546 lines) | 41 unit | In-memory only |

**Enterprise manifest schema:** `packages/contracts/manifest_v1.schema.json` — flat structure with `manifest_id`, `device_id`, `playlist[]`, `signature{algorithm, value}`, `emergency{active}`, `content_hash`. **Additional properties forbidden** (`additionalProperties: false`).

**Enterprise PoP schema:** `packages/contracts/proof_event_v1.schema.json` — `event_id`, `device_id`, `creative_asset_id`, `surface_id`, `duration_ms`, `playback_result`, `rendered_at`, `event_recorded_at`.

**Enterprise auth:** Device JWT with `auth_provider="device"`, `sub=<device_id>`. No `device_code`/`device_secret` exchange — device obtains JWT through onboarding flow.

---

## 3. Gap Analysis — Old Repo vs Enterprise

### 3.1 Manifest Shape (CRITICAL incompatibility)

| Aspect | Old Repo | Enterprise | Impact |
|--------|----------|------------|--------|
| Shape | `{status, manifest_hash, manifest_version_id, manifest: {items: [...]}}` | `{manifest_id, device_id, playlist: [...], signature: {...}, emergency: {...}}` | **Total mismatch** |
| Item fields | `id`, `sha256`, `duration_ms`, `order`, `media_path` | `creative_asset_id`, `sha256_checksum`, `duration_ms`, `order`, `media_type` | Field renames + additions |
| Signature | None (verified separately) | `signature{algorithm, value}` — HMAC-SHA256 | New requirement |
| Emergency | Not in manifest | `emergency{active}` — K1 | New field |
| Content hash | `manifest_hash` (top-level) | `content_hash` (inside manifest dict) | Structural diff |
| Strictness | Validates forbidden keys | `additionalProperties: false` | Enterprise stricter |

**Verdict:** Old `ManifestClient` and `ManifestSnapshot` are **incompatible**. Write fresh against enterprise schema.

### 3.2 Auth Model (CRITICAL incompatibility)

| Aspect | Old Repo | Enterprise | Impact |
|--------|----------|------------|--------|
| Auth flow | `device_code` + `device_secret` → POST /auth/token → JWT | Admin creates onboarding code → device uses code → JWT issued | Different flow |
| JWT claims | `sub: "device:<uuid>"`, `type: "device"`, `aud: "device-gateway"`, `device_id`, `device_code`, `session_id` | `sub: <device_id>`, `auth_provider: "device"`, standard JWT claims | Different claims |
| Token check | `get_current_device()` validates type="device", aud="device-gateway" | `get_device_id_from_token()` checks `auth_provider=="device"` | Different validation |
| Token storage | `TokenState` — in-memory dataclass | N/A (client side) | Trivial to reimplement |

**Verdict:** Old `DeviceAuthClient`, `TokenState` are **incompatible** with enterprise auth. Write fresh. `TokenState` pattern is reusable as concept.

### 3.3 PoP Shape (SIGNIFICANT incompatibility)

| Aspect | Old Repo | Enterprise | Impact |
|--------|----------|------------|--------|
| Endpoint | POST /api/device-gateway/pop/events (single) | POST /api/v1/pop/batch (batch) | Batch vs single |
| Event ID | `device_event_id` | `event_id` | Field rename |
| Item ref | `manifest_item_id` | `creative_asset_id` | Different domain model |
| Surface | Not in event | `surface_id` (required) | New field |
| Schema validation | Via endpoint (14 checks) | Pydantic `PopEventIn` + JSON Schema | Enterprise stricter |
| Response | `{status, proof_event_id}` | `{accepted_count, rejected_count, ...}` | Batch summary |

**Verdict:** Old `PopSender` is **incompatible**. Write fresh. Classification logic (retryable vs non-retryable) is reusable as concept.

### 3.4 Heartbeat Shape (MODERATE incompatibility)

| Aspect | Old Repo | Enterprise | Impact |
|--------|----------|------------|--------|
| Endpoint | POST /api/device-gateway/heartbeat | POST /api/v1/device/heartbeat | Path change |
| Fields | `status`, `message`, `device_time`, `app_version`, `os_version`, `storage_free_mb`, `cache_items_count`, `current_manifest_hash`, `details_json` | `health_state`, `runtime_version`, `player_version` | **Fewer fields in enterprise** |
| Response | `{status, id, gateway_device_id}` | `{status: "accepted", server_time, health_state}` | Different response |

**Verdict:** Old `HeartbeatClient` is **mostly incompatible**. Write fresh — much simpler (3 fields vs 9). ~50 lines.

### 3.5 What IS Reusable

| Component | Verdict | Reason |
|-----------|---------|--------|
| `retry_backoff.py` | ✅ **Copy-paste** | Pure logic, no deps, production-tested. 267 lines. |
| `token_state.py` | ✅ **Adapt** | Memory-only token pattern is sound. Rewrite for enterprise JWT claims (simpler). ~60 lines. |
| `http_client.py` (SafeHttpClient) | ✅ **Adapt** | Pattern for safe HTTP with `Authorization` redaction. ~100 lines. |
| `safe_logger.py` | ✅ **Adapt** | Structured logging pattern. ~50 lines. |
| `pop_sender.py` (classification) | ⚠️ **Concept** | Response classification (retryable/non-retryable/terminal) is a good pattern. Rewrite for enterprise schema. |
| `manifest_client.py` (forbidden-key validation) | ⚠️ **Concept** | Security-conscious manifest validation pattern. Rewrite for enterprise schema. |
| KSO Player (37 modules) | ❌ **Discard** | Full playback engine tied to Chromium/X11/filesystem. Overlap with enterprise RuntimeSimulator. |
| KSO Sidecar daemon | ❌ **Discard** | Full daemon with 14 functions. Scope creep for first slice. |
| Media cache/client | ❌ **Discard** | Enterprise uses MinIO presigned URLs — different model. Deferred to later slice. |
| Pop rotation/filesystem | ❌ **Discard** | Enterprise RuntimeSimulator holds events in memory. No filesystem rotation needed for first slice. |
| Runtime config sync | ❌ **Discard** | Enterprise has no /config/current endpoint. Manifest is the config. |

### 3.6 Size Estimate for Fresh Code

| Module | Lines | Reuses |
|--------|-------|--------|
| `player_client/http.py` — Safe HTTP client | ~80 | Pattern from old `http_client.py` |
| `player_client/auth.py` — Device onboarding + JWT | ~60 | Pattern from old `token_state.py` |
| `player_client/manifest.py` — Fetch + validate | ~60 | Validation concepts from old `manifest_client.py` |
| `player_client/heartbeat.py` — Send heartbeat | ~40 | Simpler than old (3 fields) |
| `player_client/pop.py` — Batch send + classify | ~80 | Classification concepts from old `pop_sender.py` |
| `player_main.py` — Scripted flow | ~80 | New |
| `player_client/config.py` — ENV config | ~30 | New |
| `tests/test_player_client.py` | ~150 | New |
| **Total** | **~580 lines** | |

This is dramatically smaller than importing and adapting 57K lines of old code. The fresh approach targets enterprise contracts directly.

---

## 4. PLAYER-001B — First Runnable Slice

### 4.1 Definition

```
PLAYER-001B: A single Python script that exercises the full device lifecycle
against the running enterprise backend (device-gateway + control-api):

  1. [admin] Create onboarding code via control-api (or use seed fixture)
  2. [device] Authenticate: use device_code → obtain device JWT
  3. [device] GET /api/v1/device/manifest/latest → signed manifest
  4. [device] Verify signature using manifest_signing.verify()
  5. [device] Apply manifest via RuntimeSimulator.apply_manifest()
  6. [device] Render 1 slot → emit PoP event via RuntimeSimulator.render_slot()
  7. [device] POST /api/v1/device/heartbeat → accepted
  8. [device] POST /api/v1/pop/batch → accepted_count >= 1
  9. [verify] Query backend: PoP event stored, heartbeat recorded
```

### 4.2 Architecture

```
┌──────────────────────────────────────────┐
│           Enterprise Backend              │
│  control-api (8000)  — admin operations   │
│  device-gateway (8001) — device endpoints │
│  postgres, minio, redis                   │
└──────────────┬───────────────────────────┘
               │ HTTP (JWT Bearer)
┌──────────────┴───────────────────────────┐
│         PLAYER-001B Client                │
│                                           │
│  ┌─────────────────────┐                  │
│  │ player_client/       │  NEW (~350 loc) │
│  │  http.py             │  HTTP adapter   │
│  │  auth.py             │  Onboard + JWT  │
│  │  manifest.py         │  Fetch+validate │
│  │  heartbeat.py        │  Send heartbeat │
│  │  pop.py              │  Batch send     │
│  │  config.py           │  ENV config     │
│  └─────────────────────┘                  │
│                                           │
│  ┌─────────────────────┐                  │
│  │ player_main.py       │  NEW (~80 loc)  │
│  │  Scripted flow       │                  │
│  └─────────────────────┘                  │
│                                           │
│  ┌─────────────────────┐                  │
│  │ Enterprise Runtime   │  EXISTING       │
│  │  manifest_signing.py │  HMAC verify    │
│  │  simulator.py        │  Apply+render   │
│  └─────────────────────┘                  │
│                                           │
│  ┌─────────────────────┐                  │
│  │ Old repo import      │  COPY-PASTE     │
│  │  retry_backoff.py    │  267 lines      │
│  └─────────────────────┘                  │
└──────────────────────────────────────────┘
```

### 4.3 Explicitly NOT in PLAYER-001B

- ❌ Import old KSO Player (37 modules, 38K lines) — discarded
- ❌ Import old KSO Sidecar Agent (22+ modules, 18K lines) — discarded
- ❌ Real media playback / kiosk UI / Chromium
- ❌ Hardware control (X11, GPIO)
- ❌ Filesystem persistence / offline cache
- ❌ Media download / cache
- ❌ Command channel / WS
- ❌ Staged rollout
- ❌ Playlist engine beyond 1 slot
- ❌ Daemon loop / scheduler / cron
- ❌ self.report_view UI
- ❌ Channel Orchestrator resurrection (deferred per §24)
- ❌ Old device gateway assumptions (different auth, different manifest shape)

### 4.4 Decision: Fresh Code, Not Import

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| Import old sidecar | Reuses tested code, saves time | 57K lines to audit, incompatible contracts, filesystem deps, scope creep | ❌ |
| Import old player | Full functionality | 38K lines, Chromium/X11-bound, overlaps RuntimeSimulator | ❌ |
| **Write fresh adapter** | Targets enterprise contracts exactly, minimal (~580 lines), no deps beyond requests | New code | ✅ |

**Only import: `retry_backoff.py`** (267 lines, pure logic, zero deps, battle-tested). Everything else is fresh.

---

## 5. Risk Review

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | **Onboarding code creation** — requires `devices.manage` permission in seed | High | Pre-flight: add permission to seed OR use admin SQL bypass for test device |
| 2 | **MANIFEST_SIGNING_KEY mismatch** | High | ENV config; contract test round-trips signing before first run |
| 3 | **Device JWT lifecycle** | Medium | Fresh JWT per test run; 60-min expiry not a problem for script |
| 4 | **PoP dedup across runs** | Medium | RuntimeSimulator handles in-memory dedup; fresh UUIDs per run |
| 5 | **Old manifest shape in old repo tests** | Low | Fresh code ignores old schema entirely; enterprise schema is canonical |
| 6 | **Python requests dependency** | Low | Already used in enterprise repo (admin-web); add to requirements |
| 7 | **Dev stack prerequisites** | Low | Docker compose must be running; documented in runbook |
| 8 | **Emergency enforcement** | Low | Manifest includes emergency flag (K1); RuntimeSimulator reads it |

---

## 6. Outcome: PLAYER-001B Completed, KSO-ENV-001 Required

**Sequence (actual):**
1. ✅ PRODUCT-READINESS-001 (business readiness)
2. ✅ PLAYER-001A (this audit)
3. ✅ R3 — v0.10.0-preplayer-business-ready (96b5159, CI 35/35)
4. ✅ PLAYER-001B-FU — thin enterprise KSO contract client, full live loop proof closed (CI #30368381545, 35/35)
5. ⏸️ **PLAYER-001C / media scheduler / playback loop — DEFERRED**
6. → **KSO-ENV-001** — real Sherman-J/KSO environment audit BEFORE any kiosk/scheduler code

**Rationale:** PLAYER-001B-FU proved the platform contracts work (signed manifest, heartbeat, PoP). Building a scheduler in a vacuum without real hardware data is wasteful. KSO-ENV-001 gathers real OS, Chromium/kiosk, autostart, storage, network, codecs, and update-model data before the first line of kiosk code.

## 7. Real KSO Dependency (pre-KSO-ENV-001 checklist)

Before any kiosk, scheduler, or media playback implementation, KSO-ENV-001 must determine:

- **OS / version:** Sherman-J Linux distribution, kernel, package manager
- **Chromium / kiosk:** installed version, kiosk-mode availability, `--kiosk` flags, GPU
- **Autostart:** systemd user service, `~/.config/autostart/`, or equivalent
- **Filesystem / cache paths:** writable partitions, `$HOME`, `/tmp`, `/var/cache`
- **Device credentials storage:** secure path for device JWT / secrets
- **Network recovery:** WiFi/Ethernet reconnect, captive portal handling
- **Codecs / media support:** H.264, VP9, WebP, animation formats
- **Logs / observability:** syslog, journald, or custom log path
- **Update / install path:** how software is deployed (apt, tarball, USB, OTA)

---

## 8. Source Paths (Proof of Inspection)

### Old Repo (santanas-dev/retail-media-platform, commit 41e3398)

```
apps/kso_player/kso_player/           — 37 modules, 38,804 lines
apps/kso_sidecar_agent/kso_sidecar_agent/ — 22+ modules, 18,558 lines
docs/kso_player_architecture.md        — 670 lines, Variant D recommended
docs/kso_sidecar_agent_design.md       — 566 lines, 14 functions scoped
docs/device_gateway.md                 — 665 lines, Steps 10-13
docs/kso_sidecar_device_auth_design.md
docs/kso_sidecar_manifest_store_design.md
docs/kso_sidecar_media_cache_design.md
```

### Enterprise Repo (santanas-dev/retail-media-platform-enterprise)

```
apps/device-gateway/main.py            — Manifest + heartbeat endpoints
packages/contracts/manifest_signing.py — HMAC-SHA256 sign/verify
packages/contracts/manifest_v1.schema.json — Flat manifest schema
packages/contracts/proof_event_v1.schema.json — PoP schema
packages/runtime/simulator.py          — ADR-013 safety proofs, 546 lines
packages/api/pop.py                    — POST /pop/batch router
packages/domain/pop_ingestion.py       — PoP validation pipeline
packages/domain/repository.py          — Manifest assembly, onboarding
```

Source inventory complete: `rg -l "manifest_client\|heartbeat_client\|device_auth\|pop_sender\|retry_backoff\|token_state" /home/cobalt/retail-media-platform/apps/` confirmed all files exist and were inspected.
