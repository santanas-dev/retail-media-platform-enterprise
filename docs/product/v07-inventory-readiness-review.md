# v0.7 Inventory Foundation — Readiness Review

**Document:** docs/product/v07-inventory-readiness-review.md
**Created:** 2026-07-17
**Branch:** docs/S-082-v07-inventory-readiness-review
**Review type:** S-082 — v0.7 Inventory Foundation readiness gate
**Scope:** read-only, docs-only, no code changes, no tag

---

## 1. Overall Verdict

**GO** — develop at `f993541` is ready for v0.7 Inventory Foundation release candidate.
Minimum inventory contract fully delivered across 5 S-tickets (S-077–S-081).
KSO/player preparation can begin after v0.7. No code blockers.

---

## 2. Git / CI Truth

| Показатель | Значение | Статус |
|-----------|---------|--------|
| origin/main | `aca1fb0` | ✅ stable |
| origin/develop | `f993541` | ✅ HEAD (S-081 merge) |
| Ahead/behind | develop +18 ahead of main | ✅ |
| Working tree | clean | ✅ |
| Unmerged inventory branches | none | ✅ |
| Latest develop CI | [#29493671897](https://github.com/santanas-dev/retail-media-platform-enterprise/actions/runs/29493671897) | ✅ success |
| Python Unit Tests | all passed | ✅ |
| Behavioural PostgreSQL | all passed | ✅ |
| Frontend admin-web | all passed (120 tests) | ✅ |
| Frontend advertiser-web | all passed | ✅ |
| Import Boundaries (ADR-014) | all passed | ✅ |
| JSON Schema Validation | all passed | ✅ |
| Docker Compose Config | all passed | ✅ |
| Production Config Gate | all passed | ✅ |

---

## 3. Minimum Inventory Contract Matrix

| Capability | S-ticket | Status | Files | Tests | Limitations |
|-----------|---------|--------|-------|-------|------------|
| **Availability check** | S-078 | ✅ | `packages/domain/repository.py` `compute_inventory_availability`, `packages/api/identity_routes/inventory.py` `check_availability`, `packages/domain/schemas.py` `InventoryAvailabilityRequest/Response/SlotAvailability` | 23 unit (test_s078) | Capacity uses `INVENTORY_DEFAULT_SLOT_CAPACITY` env var (default 100) — production needs per-surface capacity config |
| **Booking/reservation lifecycle** | S-079 | ✅ | `packages/domain/repository.py` `reserve_inventory_for_placement`, `commit_inventory_for_campaign`, `release_inventory_for_campaign`, `expire_inventory_reservations`, `get_inventory_reservations_for_campaign` | 24 unit (test_s079) | UNIQUE constraint uses released-row reuse pattern. TTL=24h via env. No global reservations list endpoint (campaign-scoped only). |
| **Campaign integration** | S-079 | ✅ | `packages/api/identity_routes/campaigns.py` `list_campaign_inventory_reservations`, `packages/api/identity_routes/inventory.py` `get_campaign_inventory_conflicts`, auto-reserve on `request_approval`, commit on `approve`, release on `reject` | 24 unit (test_s079) | Approval flow integration = backend only. No UI reservation visibility in CampaignDetailPage yet. |
| **Conflict detection + rules** | S-080 | ✅ | `packages/domain/repository.py` `detect_inventory_conflicts`, `apply_inventory_rules_to_slot`, `get_inventory_conflicts_for_campaign`. 6 conflict types: SURFACE_INACTIVE, CAPACITY_OVERBOOKED, BLACKOUT_RULE, INTERNAL_BLOCK, MAX_SOV_RULE, SOV_OVER_100. Scope precedence: surface > store > global. | 18 unit (test_s080) | No rule CRUD API. Rules must be created via DB seed or migrations. Rule management UI = placeholder in S-081. |
| **Inventory calendar/checker UI** | S-081 | ✅ | `apps/admin-web/src/pages/InventoryPage.tsx` — 4 tabs (Каталог/Доступность/Конфликты/Правила). Availability checker form + slot grid + conflict list. Conflict checker with blocking/warnings tables. Rules placeholder. `apps/admin-web/src/api/types.ts` + `campaigns.ts` — TS types + API client methods. | 19 vitest (inventory-page.test.tsx) | Rules tab = placeholder (backend rule engine exists, management UI deferred). No advertiser-facing availability hints. No booking visibility in CampaignDetailPage. |

---

## 4. Remaining Inventory Limitations

### P1 — Planned for S-082+

- **❌ No rule create/edit UI:** backend rule engine works (S-080), but rules can only be created via DB. UI placeholder in admin-web.
- **❌ No sold-out alternatives UI:** when inventory is fully booked, no alternative suggestions.
- **❌ No SLA/inventory reports:** no reports showing free/busy inventory over time.
- **❌ No real forecast engine:** availability check uses static capacity (default 100). No machine learning from PoP history.
- **❌ No emergency/device-health impact on availability:** emergency mode and offline devices don't reduce available capacity yet.

### P2 — Awareness

- **❌ No advertiser-facing availability hints:** advertiser portal shows campaign status but no "this surface is likely available" indicators.
- **❌ No pricing/rate card/billing/programmatic:** inventory has no cost model.
- **❌ No competitor separation:** same-surface ads from competing brands. No category data exists yet.

---

## 5. KSO / Player Readiness Decision

### Verdict: ✅ KSO/player preparation can begin after v0.7 release

**Why now (not earlier):**

The minimum inventory contract guarantees that:
1. Availability is checked before reservation (S-078)
2. Reservations prevent double-booking of the same slot (S-079)
3. Campaign approval automatically reserves → commits inventory (S-079)
4. Blocking rules (blackout, internal block, max SOV) prevent invalid placements (S-080)
5. Operators can verify availability and conflicts visually (S-081)

Before S-077–S-081, a player could receive conflicting placements for the same surface/hour slot. Now the backend guarantees slot-level exclusivity.

### What KSO/player preparation can start:

- Device identity/registration architecture design
- Manifest verification path (existing device-gateway GET /manifest/latest)
- Player runtime architecture (rendering engine, slot management)
- Rollout/rollback planning (kill-switch integration)
- Device diagnostics and telemetry design
- Integration test harness for real KSO devices

### What should NOT be claimed:

- ❌ Real player NOT built (runtime simulator only — 41 unit tests, safety gates)
- ❌ Hardware NOT integrated (KSO terminals, Android, Intel NUC)
- ❌ Production rollout NOT ready
- ❌ Device management at scale NOT tested
- ❌ PoP ingestion from real devices NOT validated in production

---

## 6. Release Recommendation

### Verdict: GO — v0.7-inventory-foundation

**⏳ Not yet published.** Tag not created. Main not updated. Ready for S-083 publish step.

| Field | Value |
|-------|-------|
| **Tag name** | `v0.7-inventory-foundation` |
| **Tag target** | `f993541` (develop HEAD after S-081 merge) |
| **Tag type** | annotated (`git tag -a`) |
| **Tag scope** | code baseline — inventory foundation |
| **When to tag** | S-083 publish step (separate release-prep branch) |
| **Release notes** | 5 S-tickets: availability (23 tests), reservation (24 tests), conflicts (18 tests, 6 types), UI calendar (19 vitest), plus schema (S-077) |

### Post-release next:

- **S-083:** sold-out detection + alternatives
- **S-084:** inventory reports (free/busy, plan/fact, SLA)
- **KSO prep sprint** (device identity, manifest verification, player architecture)
- **Emergency/device-health impact** on inventory availability

---

## 7. Security / Compliance Checklist

| Gate | Status | Evidence |
|------|--------|----------|
| No localStorage tokens in admin-web | ✅ | AuthContext uses in-memory `_token`, HttpOnly refresh cookie |
| No storage_bucket/key/presigned_url in admin-web UI | ✅ | inventory-page test: `expect(html).not.toContain("storage_bucket")` |
| Inventories endpoint requires inventory.read permission | ✅ | `require_permission("inventory.read")` on all inventory endpoints |
| Inventory manage requires inventory.manage | ✅ | `PATCH /inventory/surfaces` requires `inventory.manage` |
| RLS context on conflict endpoints | ✅ | `set_rls_context` on `check_inventory_conflicts` and `get_campaign_inventory_conflicts` |
| No secrets in API responses | ✅ | Inventory response schemas: no storage paths, no presigned URLs, no password hashes |
| Access token never in localStorage | ✅ | Verified by behavioral gate in CI |
| Advertiser cannot access inventory management | ✅ | `inventory.read` permission not assigned to advertiser roles |

---

## 8. Documentation Truth

| Document | Status | Notes |
|----------|--------|-------|
| Roadmap (xlsx, 2 sheets) | ✅ | Both sheets have exactly 2 sheets: Технический (88×5) + Бизнес-функции (38×8). S-081 marked done. KSO "можно начинать подготовку после v0.7". |
| Stabilization tracker | ✅ | Header: "v0.7 inventory: S-076–S-081 done. S-082 next." All S-076–S-081 ✅ done. No dual-table drift. |
| Inventory gap analysis | ✅ | S-077–S-081 ✅ done. Remaining limitations documented honestly. |
| Release versioning | ✅ | v0.7-inventory-foundation section added with status, capabilities, limitations. |
| This review document | ✅ | Full v0.7 readiness review with contract matrix + KSO decision. |

---

## 9. Files Changed (docs-only)

| File | Action |
|------|--------|
| `docs/product/v07-inventory-readiness-review.md` | created — this document |
| `docs/architecture/stabilization-tracker.md` | updated — added S-082 |
| `docs/architecture/release-versioning.md` | updated — added v0.7 section |
| `docs/product/inventory-domain-gap-analysis.md` | updated — S-077–S-081 done, remaining limitations |
| `docs/product/roadmap-s020-2026-07-10.xlsx` | updated — v0.7 release candidate, KSO prep status |

---

## 10. Confirmation

- ✅ Read-only — no code changes
- ✅ No tag created
- ✅ main untouched (`aca1fb0`)
- ✅ No KSO/player implementation
- ✅ Docs-only branch: `docs/S-082-v07-inventory-readiness-review`
