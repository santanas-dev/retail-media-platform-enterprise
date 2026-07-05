# ADR-013: Edge Runtime Safety

**Status:** Accepted
**Date:** 2026-07-04
**Phase:** 4.0a+ (Architecture Lock)
**Deciders:** Sergey Paschenko (project owner), Hermes Agent

## Context

ADR-003 defines device identity, JWT sessions, and onboarding.  The
universal manifest v1 contract specifies `fallback_rules`, validity
windows, offline TTL, and signature verification.  Proof-of-play events
define idempotent `event_id`-based deduplication with device signatures.

What remains undefined: **the safety contract between the edge runtime
(player/sidecar) and the platform.**  A device running in a store is
unattended.  It has no human operator to intervene when a manifest is
corrupt, a kill-switch fires, or the network drops.  Every failure mode
must be handled by the runtime without human intervention.

This ADR defines the edge runtime safety invariants that every
device-facing component (player, sidecar, gateway) must enforce.

## Decision

### 1. Fail-Safe: No Campaign Content on Invalid State

The runtime must refuse to play campaign content in any of these states:

| Condition | Runtime behavior |
|-----------|-----------------|
| Manifest signature verification fails | Reject manifest, retain last-known-good, report error |
| Manifest `valid_from` is in the future | Reject manifest, wait until `valid_from` |
| Manifest `valid_to` has passed (expired) | Cease playback, follow `fallback_rules.on_manifest_expired` |
| Manifest `schema_version` unsupported | Reject, report version mismatch |
| Manifest references unknown `device_id` | Reject, mismatched target |
| Media file SHA-256 mismatch after download | Skip that item in playlist, log error, do NOT play |
| No `fallback_rules` configured and manifest invalid | Blank/black screen — never default to unknown content |

**Fallback content is allowed only if explicitly configured in the
manifest's `fallback_rules`.**  The runtime must never invent fallback
content (no hardcoded default ads, no local filesystem pick).  If
`fallback_rules.filler_media_ids` is empty or missing, the runtime
shows nothing (black screen or idle screen per channel defaults).

**Proof-of-play for fallback:** emitted only if the platform explicitly
sets `fallback_rules.emit_pop = true` in the manifest.  Default: no PoP
for fallback playback.

### 2. Kill-Switch

The platform can halt playback at four granularity levels:

| Level | Scope | Cleared by |
|-------|-------|-----------|
| **Global** | All devices, all campaigns | Admin action |
| **Store** | All devices in `store_id` | Admin action |
| **Device** | Specific `device_id` | Admin action |
| **Campaign** | Specific `campaign_id` across all devices | Admin action |

**Check order in render path** (before playing any slot):

```
is kill-switch active for this campaign?
  → YES: skip this playlist item, log, do NOT play
is kill-switch active for this device?
  → YES: halt all playback, show fallback or blank
is kill-switch active for this store?
  → YES: halt all playback, show fallback or blank
is global kill-switch active?
  → YES: halt all playback, show fallback or blank
```

**Local caching:**

- Kill-switch state is fetched from Device Gateway on heartbeat/manifest
  pull and cached locally.
- Cache TTL: 60 seconds default (configurable).
- **Stale cache (TTL expired, cannot reach gateway):** fail closed —
  halt campaign playback, show fallback or blank.  Never continue
  playing because «haven't checked lately.»
- Unknown kill-switch state (device just booted, no cache yet): same
  as stale — fail closed.

**Kill-switch is NOT a pause.**  It is an active stop.  Resuming
requires explicit admin action to clear the kill-switch, followed by
a new manifest pull.

### 3. Manifest Update Safety

Applying a new manifest is a multi-step atomic operation:

```
1. Download manifest to <cachedir>/manifests/incoming/<manifest_id>.json.tmp
2. Verify signature (Ed25519 or HMAC-SHA256 per manifest.signature)
3. Verify manifest_version > current version (monotonic check)
4. Verify device_id matches this device
5. Parse JSON, validate schema_version is supported
6. Download referenced media files (parallel, with retry)
7. Verify each media SHA-256
8. Atomic rename: <incoming>/ → <cachedir>/manifests/active/
9. Update current_manifest_id pointer
10. Discard previous manifest files not referenced by new manifest
```

**At any step before step 8, if an error occurs:**
- Delete `incoming/` directory entirely (partial downloads).
- Log error with reason.
- Retry on next poll cycle (backoff: 30s, 60s, 120s, 300s).
- **Never partially apply a manifest.**  A playlist with 3 of 5 media
  files downloaded is NOT playable.

**Last-known-good manifest:** the runtime always retains the
previously-applied manifest until a new one is fully verified and
atomically swapped.  If the new manifest fails at step 8 or earlier,
the runtime continues with the last-known-good manifest unchanged.

**Rollback on invalid update after apply:** if a manifest was applied
successfully (step 8 completed) but subsequent operations reveal it is
broken (e.g., all media URLs return 403 on first play attempt), the
runtime rolls back to the last-known-good manifest and reports the
failure.

**Monotonic version guard:** if `manifest_version <= current_version`,
reject unless `emergency_flag = true` (emergency manifests may
downgrade).

### 4. Locking

Only one manifest apply operation at a time per device:

```
if lockfile exists and age < max_lock_age_seconds (300s):
    skip this poll cycle (another apply in progress)
if lockfile exists and age >= max_lock_age_seconds:
    log "stale lock recovered", remove lockfile, continue
acquire lockfile (write PID + timestamp)
    ... apply manifest (steps 1–10 from §3) ...
release lockfile (delete)
```

**Stale lock recovery** (≥ 300s) means the previous apply process
crashed or hung.  Recovery is logged and reported in the next
heartbeat as `manifest.apply.stale_lock_recovered`.

**No parallel apply operations.**  The lock is process-local (filesystem
lockfile in the cache directory).  No distributed lock needed — one
process per device.

### 5. Offline Behavior

Devices operate in stores with unreliable network.  The runtime must
handle extended offline periods:

| Condition | Behavior |
|-----------|----------|
| Network lost, manifest still valid | Continue playlist from last-known-good manifest |
| Network lost, manifest `valid_to` passed | Stop campaign content, show `fallback_rules.on_manifest_expired` |
| Network lost for > `offline_ttl_hours` | Stop campaign content, show `fallback_rules.on_network_lost` (default: `continue_last_valid`) |
| Device clock is wrong (NTP unreachable) | Use monotonic clock for durations, last-known-good wall clock for schedule. If clock drift > 1 hour, stop time-gated content (dayparting), play only non-scheduled items |

**`offline_ttl_hours`** is set in the manifest (default 168 = 7 days).
After expiry, the device must NOT play campaign content.  This prevents
a disconnected device from playing stale ads indefinitely.

**Clock drift tolerance:** if the device cannot reach NTP and its
wall clock differs from last sync by > 1 hour, time-of-day
constraints (`start_time`, `days_of_week`) are suspended — only
non-scheduled playlist items play.  Prevents «10 AM ad at 3 AM.»
Monotonic clock (`time.monotonic()`) is always trusted for durations.

### 6. Proof-of-Play Integrity

PoP events must be truthful and complete:

| Rule | Rationale |
|------|-----------|
| Emit PoP **only after actual render** | Never emit for skipped, failed, or pre-fetched content |
| PoP includes `manifest_id`, `surface_id`, `media_id`, `creative_version_id`, `rendered_at`, `duration_ms`, `device_id` | Full trace from manifest to render |
| PoP includes `pop_mode` per contract | `real_playback`, `screen_render`, etc. |
| No PoP for fallback unless `fallback_rules.emit_pop = true` | Distinguish real campaign delivery from filler |
| Dedup key: `event_id` (UUID) | Backend deduplicates; retried PoP events are harmless |
| PoP emitted even if offline | Queued in local buffer (§7); delivered when connectivity returns |

**Anti-patterns:**
- Emitting PoP on file download (not yet rendered)
- Emitting PoP with `duration_ms=0` (skipped/template-not-rendered)
- Emitting PoP for content that was in playlist but never reached the
  renderer (preempted, overlapped, hidden by touch)
- Batched PoP with the same `event_id` for different renderings

### 7. Local Event Buffer

PoP events, heartbeats, errors, and status changes are queued locally
before transmission:

```
[Event] → append to local SQLite / log-structured buffer
        → transmission worker picks up events
        → POST to Device Gateway (batch or single)
        → on 200: mark as sent, GC eligible
        → on failure (4xx/5xx/network): retry with backoff
```

**Durability:** events are written to disk before acknowledged to the
caller.  If the process crashes, buffered events survive restart.

**Retention:**
- Max buffer size: 100 MB or 100 000 events, whichever comes first.
- When buffer is full: drop oldest events (FIFO), emit
  `device.error.buffer_overflow` event.
- Normal GC: delete events older than 7 days that have been
  successfully delivered.

**At-least-once delivery:** the transmission worker retries until the
backend returns 200.  The backend deduplicates by `event_id`.

**Backoff:** [1s, 2s, 4s, 8s, 16s, 32s, 64s] with jitter, reset on
success.

**No unbounded disk growth.**  Buffer limits are hard — exceeding them
drops events rather than filling the disk.

### 8. Observability

Every device emits these signals:

| Signal | Frequency | Contents |
|--------|-----------|----------|
| **Heartbeat** | Every 30s | device_id, status (online/degraded/error), current_manifest_id, manifest_version, cache_size_bytes, cache_free_bytes, uptime_seconds, last_error_code, ip_address, player_version, chromium_version |
| **Manifest apply** | On each apply attempt | success/failure, manifest_id, manifest_version, failure_reason, duration_ms |
| **Kill-switch active** | On state change | level (global/store/device/campaign), target_id, active_since |
| **Offline duration** | On heartbeat | seconds_since_last_gateway_contact |
| **Local queue depth** | On heartbeat | buffered_events_count, oldest_buffered_event_age_seconds |
| **Render failure** | On each failure | media_id, failure_reason (sha256_mismatch, file_missing, decode_error, timeout), surface_id |

All signals include `correlation_id` where applicable (manifest pull
correlation, campaign publish correlation).

**When offline:** all signals are buffered in the local event queue (§7)
and delivered when connectivity returns.  Heartbeats are NOT generated
while offline — the first heartbeat after reconnection carries the
offline duration.

### 9. Security

**No secrets on device:**

| What | Where | Rule |
|------|-------|------|
| Device secret / HMAC key | Memory only, encrypted at rest | Never written to app logs, manifest files, or PoP events |
| JWT access token | Memory only, short-lived (15 min) | Never in URLs, never in PoP/heartbeat payloads |
| Device certificate | Encrypted file, memory when active | Private key never leaves device |
| Manifest `adapter_payload` | Cached as-is | Must not contain secrets (enforced server-side by manifest schema) |
| Media URLs | In manifest | `presigned_url` only — no permanent credentials |

**Sanitization rules for device logs:**
- Tokens, secrets, signatures → `REDACTED`
- `presigned_url` query parameters → `REDACTED`
- Device IP / MAC in verbose logs → truncated (`10.x.x.0/24`)

### 10. Testing Requirements

Before accepting any device-facing runtime code, the following
behavioral/simulation tests must pass:

| Test | What it proves |
|------|---------------|
| **Invalid manifest does not play** | Corrupt signature → rejected, last-known-good retained, error reported |
| **Kill-switch stops playback** | Active kill-switch → render path returns before play, PoP NOT emitted |
| **Manifest atomic update** | Partial download → rolled back, last-known-good active, no partial playlist in render |
| **Rollback to last-known-good** | New manifest applies but media URLs all 403 → runtime rolls back, continues with previous |
| **Stale lock recovery** | Lockfile from crashed process (age > 300s) → recovered, new apply proceeds, recovery logged |
| **PoP only after render** | Pre-fetched media, skipped slot, sha256 mismatch → no PoP emitted; successfully rendered → PoP emitted with correct manifest_id/surface_id |
| **Offline TTL enforcement** | Clock advances past `offline_ttl_hours` → campaign content stops, fallback or blank |
| **Local buffer survives restart** | Events written to disk, process killed, restarted → pending events still in buffer and delivered |
| **No secrets in logs** | Device log inspection after auth + playback → no tokens, secrets, or raw signatures |

**Source-inspection alone is not sufficient for runtime safety.**  A
simulated device environment that actually runs the player/sidecar
against a mock gateway and manifests is required.

## Consequences

- **Positive:** Unattended devices handle every failure mode without
  operator intervention.  Kill-switch provides emergency stop at any
  granularity.  Manifest updates are atomic — no corrupt state.
  Proof-of-play integrity ensures billing/analytics accuracy.  Local
  buffer survives crashes and network outages.

- **Negative:** Atomic manifest update adds latency (download all media
  before switching).  Kill-switch fail-closed means network problems
  halt playback — intentionally, but operators must understand this.
  Local event buffer adds disk I/O on the device.

- **Risk:** A device with a corrupt clock and no NTP could enter a
  state where it incorrectly believes `offline_ttl_hours` has expired.
  Mitigation: clock drift > 1 hour → suspend time-gated content but
  continue non-scheduled items (not a full stop).  A device with
  full disk (buffer overflow) drops events silently — operations must
  monitor `device.error.buffer_overflow` events.

## References

- ADR-003 — Device identity (JWT, onboarding, no tokens in URLs)
- ADR-005 — Observability (heartbeat, metrics, correlation IDs)
- ADR-011 — Transactional outbox (at-least-once + idempotent pattern
  mirrored in local event buffer)
- ADR-012 — Async I/O (streaming for media downloads)
- `docs/architecture/contracts/universal-manifest-v1.md` — Manifest schema
- `docs/architecture/contracts/proof-event-v1.md` — PoP schema
- `docs/architecture/events/event-contracts-v1.md` — Device events
