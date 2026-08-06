# STYLE-TOKENS-001A0 — Inventory Baseline

**Date:** 2026-08-05
**Scope:** apps/admin-web/src/{pages,components}

## Raw Hex Inventory

| Metric | Count |
|--------|-------|
| Files scanned | 24 (.tsx/.ts) |
| Unique hex colors | 61 |
| Total hex occurrences | 594 |
| Total var() usages | 483 |
| Top file by raw hex | CampaignDetailPage.tsx (208) |

### Top 20 hex colors by usage

| Hex | Count | Maps to token | Files |
|-----|-------|---------------|-------|
| #64748b | 66 | `var(--rmp-gray-500)` → `var(--rmp-text-secondary)` | AdvertisersPage, ApprovalInboxPage, CampaignCreatePage, CampaignDetailPage, UsersPage, PublicApplicationForm |
| #e2e8f0 | 57 | `var(--rmp-gray-200)` → `var(--rmp-border)` | AdvertisersPage, CampaignDetailPage, EmergencyPage, UsersPage, DeviceHealthPage |
| #fff | 56 | `var(--rmp-bg-surface)` / `var(--rmp-text-inverse)` | Multiple — mostly backgrounds |
| #dc2626 | 47 | `var(--rmp-danger-600)` | AdvertisersPage, ApprovalInboxPage, CampaignDetailPage, EmergencyPage, UsersPage |
| #94a3b8 | 45 | `var(--rmp-gray-400)` → `var(--rmp-text-muted)` | AdvertiserApplicationsPage, CampaignDetailPage, DeviceHealthPage, UsersPage |
| #2563eb | 29 | `var(--rmp-primary-500)` | CampaignCreatePage, CampaignDetailPage, UsersPage |
| #475569 | 22 | `var(--rmp-gray-600)` | CampaignDetailPage, DeviceHealthPage, UsersPage |
| #f8fafc | 21 | `var(--rmp-gray-50)` → `var(--rmp-bg-page)` | AdvertisersPage, CampaignDetailPage, EmergencyPage |
| #991b1b | 21 | `var(--rmp-danger-800)` | CampaignDetailPage (error messages), EmergencyPage |
| #fef2f2 | 20 | `var(--rmp-danger-50)` | CampaignDetailPage (error cards), EmergencyPage |
| #166534 | 20 | `var(--rmp-success-800)` | CampaignDetailPage, EmergencyPage |
| #cbd5e1 | 19 | `var(--rmp-gray-300)` → `var(--rmp-border-strong)` | CampaignDetailPage, CampaignCreatePage |
| #16a34a | 19 | `var(--rmp-success-600)` | CampaignDetailPage, CampaignCreatePage, AdvertisersPage |
| #f1f5f9 | 16 | `var(--rmp-gray-100)` | Multiple (table rows, hover) |
| #f0fdf4 | 12 | `var(--rmp-success-50)` | CampaignCreatePage (success cards) |
| #334155 | 8 | `var(--rmp-gray-700)` | CampaignDetailPage, EmergencyPage |
| #1e293b | 7 | `var(--rmp-gray-800)` | Sidebar, headers |
| #0f172a | 4 | `var(--rmp-gray-900)` → `var(--rmp-text-primary)` | Headers, text |

### Files ordered by raw hex count

| File | Raw hex | var() |
|------|---------|-------|
| CampaignDetailPage.tsx | 208 | many |
| AdvertisersPage.tsx | 72 | many |
| UsersPage.tsx | 47 | many |
| CampaignCreatePage.tsx | 36 | some |
| DeviceHealthPage.tsx | 35 | some |
| ApprovalInboxPage.tsx | 34 | some |
| AdvertiserApplicationsPage.tsx | 33 | some |
| ADSettingsPage.tsx | 31 | some |
| EmergencyPage.tsx | 26 | some |
| AdvertiserWizard.tsx | 26 | some |
| AuditLogPage.tsx | 18 | few |
| PublicApplicationForm.tsx | 15 | few |
| InventoryPage.tsx | 6 | few |
| ErrorBoundary.tsx | 6 | few |
| CampaignListPage.tsx | 1 | few |

## Existing tokens.css Coverage

tokens.css already defines **all** hex values in the inventory as `--rmp-*` tokens.
The gap is NOT missing token definitions — it's that components use raw `#hex` literals
instead of `var(--rmp-*)`.

### Semantic aliases already defined

| Token | Value | Coverage |
|-------|-------|----------|
| `--rmp-bg-page` | var(--rmp-gray-50) | Partial — #f8fafc still raw in many files |
| `--rmp-bg-surface` | #fff | Partial — #fff still raw in most files |
| `--rmp-border` | var(--rmp-gray-200) | Low — #e2e8f0 used raw 57× |
| `--rmp-border-strong` | var(--rmp-gray-300) | Low — #cbd5e1 used raw 19× |
| `--rmp-text-primary` | var(--rmp-gray-900) | Partial — #0f172a still raw 4× |
| `--rmp-text-secondary` | var(--rmp-gray-500) | Low — #64748b used raw 66× |
| `--rmp-text-muted` | var(--rmp-gray-400) | Low — #94a3b8 used raw 45× |
| `--rmp-text-inverse` | #fff | Partial — #fff still raw 56× |
| `--rmp-danger-600` | #dc2626 | Low — used raw 47× |
| `--rmp-success-600` | #16a34a | Low — used raw 19× |
| `--rmp-primary-500` | #2563eb | Low — used raw 29× |
| `--rmp-sidebar-*` | Various | Good — already tokenized |

## Proposed Semantic Token Layer

No NEW tokens needed — reuse existing `--rmp-*` in components.
The mapping is 1:1 for 95%+ of occurrences.

### Mapping table (hex → semantic token)

```
#f8fafc → var(--rmp-bg-page)              [bg-page]
#f1f5f9 → var(--rmp-gray-100)              [hover, row-alt]
#e2e8f0 → var(--rmp-border)                [borders]
#cbd5e1 → var(--rmp-border-strong)         [strong borders]
#94a3b8 → var(--rmp-text-muted)            [muted text]
#64748b → var(--rmp-text-secondary)        [secondary text]
#475569 → var(--rmp-gray-600)              [dark text, headings]
#334155 → var(--rmp-gray-700)              [headings]
#1e293b → var(--rmp-gray-800)              [sidebar]
#0f172a → var(--rmp-text-primary)          [primary text]

#fff    → var(--rmp-bg-surface)            [surface bg]
       OR var(--rmp-text-inverse)          [inverse text]

#eff6ff → var(--rmp-primary-50)            [primary bg]
#2563eb → var(--rmp-primary-500)           [accent]
#1d4ed8 → var(--rmp-primary-600)           [accent-hover]
#1e40af → var(--rmp-primary-700)           [accent-active]

#f0fdf4 → var(--rmp-success-50)            [success bg]
#dcfce7 → var(--rmp-success-100)           [success bg light]
#16a34a → var(--rmp-success-600)           [success text]
#166534 → var(--rmp-success-800)           [success text dark]

#fffbeb → var(--rmp-warning-50)            [warning bg]
#fef3c7 → var(--rmp-warning-100)           [warning bg light]
#d97706 → var(--rmp-warning-600)           [warning text]

#fef2f2 → var(--rmp-danger-50)             [danger bg]
#fee2e2 → var(--rmp-danger-100)            [danger bg light]
#dc2626 → var(--rmp-danger-600)            [danger text]
#991b1b → var(--rmp-danger-800)            [danger text dark]
```

### Mapping coverage: **95%+** (all top-20 hexes directly mappable)

### Ambiguous/TODO (manual review)

| Hex | Count | Issue |
|-----|-------|-------|
| #fff | 56 | Ambiguous: sometimes bg-surface, sometimes text-inverse. Need context. |
| #475569 | 22 | Sometimes text, sometimes border in CampaignDetailPage. Check context. |
| #8b5cf6 | 3 | Purple — inventory? simulation? No token defined. Add if needed. |
| #7dd3fc, #bae6fd, #93c5fd, #bfdbfe | 1–2 each | Light blue variants — inventory? Check context before mapping. |
| #ccc, #888, #666, #333, #f5f5f5 | 1 each | Legacy grays — map to closest --rmp-gray-*. |
| #52525b | 1 | Zinc-600 — map to --rmp-gray-600. |

## Codemod Plan (A1)

### Safety: no visual change
All hex→var() mappings use the **exact same hex value** already defined in tokens.css.
The codemod is purely mechanical — replace literal `#64748b` with `var(--rmp-text-secondary)`.

### Phase order

1. **tokens.css addendum** (if needed): Add `--rmp-accent: var(--rmp-primary-500)` alias for clarity.
2. **Mechanical codemod**: `sed`-based replace for unambiguous hexes (top 50+ by count).
   - Safety: each replacement hex == the token's defined value. Verify with `rg` before commit.
3. **Manual review**: #fff (56×, ambiguous), #475569 (context-dependent), low-count outliers (purple, light blue).
4. **Vitest**: 331/331 must stay green.
5. **Build**: `npx vite build` must succeed.
6. **UI-smoke**: 35/35 must stay green.
7. **Visual diff**: playwright screenshot compare pre/post — must be pixel-identical.
8. **Merge**: single commit, clean git history.
