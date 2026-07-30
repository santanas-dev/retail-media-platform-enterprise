# EPIC-L — Platform/Device Licensing Architecture

**Date:** 2026-07-30  
**Status:** Canon intake only. No implementation.  
**Owner gate §08:** Approved 2026-07-30.

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
