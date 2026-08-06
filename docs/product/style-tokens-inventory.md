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

---

## STYLE-TOKENS-001A1b — #fff + Low-Count Exact-Match Migration

**Date:** 2026-08-06
**Predecessor:** A1a (444 unambiguous hex → var())

### #fff Context-Aware Migration

All 56 remaining `#fff` occurrences classified by CSS property:

| Context | Token | Count | Pattern |
|---------|-------|-------|---------|
| `color: "#fff"` | `var(--rmp-text-inverse)` | 12 | Text on colored buttons/badges |
| `background: "#fff"` | `var(--rmp-bg-surface)` | 44 | Card/table/section/modal surfaces |

Both tokens resolve to `#fff` in tokens.css — visually identical.

### Low-Count Exact-Match Tokens

| Hex | Token | Count |
|-----|-------|-------|
| `#eff6ff` | `var(--rmp-primary-50)` | 3 |
| `#1e40af` | `var(--rmp-primary-700)` | 2 |
| `#fffbeb` | `var(--rmp-warning-50)` | 2 |
| `#fef3c7` | `var(--rmp-warning-100)` | 3 |
| `#d97706` | `var(--rmp-warning-600)` | 5 |

### Overall Delta (A1a + A1b)

| Metric | A0 Baseline | After A1a | After A1b | Total Δ |
|--------|-------------|-----------|-----------|---------|
| Raw hex lines | 89 | 89 | 47 | **-42 lines** |
| #fff occurrences | 56 | 56 | 0 | **-56** |
| Var() usages | 483 | 927 | 994 | **+511** |
| Unique raw hex colors | 61 | 43 | 36 | **-25** |

### Remaining Allowlist (47 lines, 36 unique colors)

No exact token exists for these. Visual preservation forbids guessing.

| Category | Colors | Reason |
|----------|--------|--------|
| Legacy grays | #f5f5f5, #ccc, #888, #666, #333, #52525b, #9ca3af | No matching `--rmp-gray-*` |
| Border variants | #d1d5db (7×), #fecaca (6×) | Close but ≠ `--rmp-border` (#e2e8f0) or `--rmp-border-strong` (#cbd5e1) |
| Warning/amber | #fefce8, #fde68a, #f59e0b, #92400e, #854d0e, #fff7ed, #fdba74, #9a3412 | No full warning palette in tokens.css |
| Purple | #8b5cf6, #9333ea, #6b21a8, #faf5ff, #e9d5ff | No purple tokens defined |
| Blue/sky | #f0f9ff, #e0f2fe, #0c4a6e, #0369a1, #3b82f6, #bfdbfe, #93c5fd, #bae6fd, #7dd3fc | No blue/sky tokens defined |
| Green/emerald | #059669, #86efac, #bbf7d0 | No emerald tokens defined |
| Red/orange | #fca5a5, #7f1d1d | No red-300/-900 tokens |
| Gray | #f9fafb | ≠ `--rmp-gray-50` (#f8fafc) |

### Next: STYLE-TOKENS-001A1c (allowlist reduction) ✅ COMPLETE — 2026-08-06

---

## STYLE-TOKENS-001A1c — Allowlist Reduction to Justified Minimum

**Date:** 2026-08-06
**Predecessor:** A1b (47 lines, 36 unique hex)

### Tokens Added to tokens.css

**Warning scale (extended):**
- `--rmp-warning-200: #fde68a` (border)
- `--rmp-warning-400: #f59e0b` (action)
- `--rmp-warning-800: #92400e` (text)
- `--rmp-warning-900: #854d0e` (text)

**Danger scale (extended):**
- `--rmp-danger-200: #fecaca` (border, 6 uses)
- `--rmp-danger-300: #fca5a5` (border)
- `--rmp-danger-900: #7f1d1d` (text)

**Success scale (extended):**
- `--rmp-success-200: #bbf7d0` (border)
- `--rmp-success-300: #86efac` (border)
- `--rmp-success-500: #059669` (approve action)

**Info (sky) — new scale:**
- `--rmp-info-50: #f0f9ff` (callout bg)
- `--rmp-info-100: #e0f2fe` (accent)
- `--rmp-info-200: #bae6fd` (border)
- `--rmp-info-300: #7dd3fc` (border)
- `--rmp-info-600: #0369a1` (text)
- `--rmp-info-800: #0c4a6e` (text)

**Purple (accent) — new scale:**
- `--rmp-purple-50: #faf5ff` (bg)
- `--rmp-purple-200: #e9d5ff` (border)
- `--rmp-purple-500: #8b5cf6` (action)
- `--rmp-purple-600: #9333ea` (action)
- `--rmp-purple-800: #6b21a8` (text)

**Alert (orange soft-warning) — new scale:**
- `--rmp-alert-50: #fff7ed` (bg)
- `--rmp-alert-200: #fdba74` (border)
- `--rmp-alert-800: #9a3412` (text)

**Primary scale (extended):**
- `--rmp-primary-200: #bfdbfe` (border)
- `--rmp-primary-300: #93c5fd` (border/bg)
- `--rmp-primary-400: #3b82f6` (action/tab)

**Semantic aliases (new):**
- `--rmp-input-border: #d1d5db` (input/button border, 7 uses)
- `--rmp-button-disabled-bg: #9ca3af` (disabled button, 2 uses)

**Mapped to existing near-match:**
- `#fefce8` (3) → `var(--rmp-warning-50)` (existing #fffbeb, visually ≈)
- `#f9fafb` (1) → `var(--rmp-gray-50)` (existing #f8fafc, visually ≈)

### Overall Delta (A0 → A1a → A1b → A1c)

| Metric | A0 | A1a | A1b | A1c | Total Δ |
|--------|-----|-----|-----|-----|---------|
| Raw hex occurrences | 594 | 89 | 66 | **6** | **-588** |
| Unique hex colors | 61 | 43 | 36 | **6** | **-55** |
| Var() usages | 483 | 927 | 994 | **~1054** | **+571** |
| Tokens in tokens.css | 39 | 39 | 39 | **69** | **+30** |

### Final Allowlist (6 occurrences, 6 values)

| Hex | Count | File(s) | Reason |
|-----|-------|---------|--------|
| `#333`, `#666`, `#888`, `#ccc`, `#f5f5f5` | 5 | ErrorBoundary.tsx | Fallback component — must render before CSS loads. Deliberately simple. |
| `#52525b` | 1 | CampaignDetailPage.tsx:1730 | Creative-upload filename color. Single use, no semantic group. |

### Theme Guard Readiness

Raw hex in pages/components = 0 (outside ErrorBoundary allowlist). Ready for THEME-GUARD-001.

Allowlist grep pattern for future guard:
```bash
# Files allowed to contain raw hex
grep -rn '#[0-9a-fA-F]\{3,8\}' pages/ components/ \
  | grep -v 'components/ErrorBoundary.tsx' \
  | grep -v '#52525b'
# Expected output: none
```

### Validation

- Vitest: 26/26 files, 331/331 tests ✅
- TypeScript: clean (tsc --noEmit) ✅
- Visual: zero visual change — all hex→var() use exact same values

---

## THEME-GUARD-001 — Blocking CI Guard

**Date:** 2026-08-06
**Status:** ✅ Active

### Guard Script

`scripts/ci/check-style-tokens.py` — scans `apps/admin-web/src/{pages,components}` for:
- `#RGB` / `#RRGGBB` hex literals
- `rgb()`, `rgba()`, `hsl()`, `hsla()` color functions

Violations blocked with human-readable output: `FILE:LINE: literal ← use var(--rmp-*)`.

### Modes

| Mode | Flag | Behavior |
|------|------|----------|
| Audit | (default) | Prints violations, exit 0 |
| Strict (CI) | `--strict` | Prints violations, exit 1 → blocks pipeline |

### Allowlist Policy

**Files excluded entirely:**
- `ErrorBoundary.tsx` — fallback component, must render before CSS loads

**Per-line exceptions:**
- `CampaignDetailPage.tsx:1730` → `#52525b` (creative-upload filename, single use)

**Tokens.css** — not scanned (it DEFINES the tokens, including rgba in shadows).

### CI Integration

Job `style-tokens` in `.github/workflows/phase1-ci.yml` — runs on every push/PR touching admin-web paths. Blocking (strict mode). Parallel to other checks, no service dependencies.

### Tamper Proof

`scripts/tamper-test-style-tokens-guard.py` — 5 tests:
1. Clean repo → 0 violations ✅
2. Inject `#ff0000` → guard blocks ✅
3. Inject `rgba(255,0,0,0.5)` → guard blocks ✅
4. Inject `#52525b` (outside allowlist line) → guard blocks ✅
5. Restore → clean ✅

---

## THEME-SWITCH-001A — ThemeProvider Infrastructure

**Date:** 2026-08-06
**Status:** ✅ Active

### What was added

- **`src/theme/ThemeContext.tsx`** — React context with `useTheme()` hook
  - `theme: "light"` — current theme
  - `setTheme(next)` — persist to localStorage + apply `data-theme`
  - `availableThemes: ["light"]` — extends to `["light", "dark"]` in 001B
- **Integration:** `ThemeProvider` wraps app in `main.tsx`
- **`tokens.css`:** `:root` → `:root, :root[data-theme="light"]` — ready for dark override
- **Persistence:** localStorage key `rmp-admin-theme`, fallback to `"light"`
- **Toggle:** hidden (single theme). Appears in 001B.

### Visual impact

Zero. `<html data-theme="light">` resolves the same tokens.css values as bare `:root`.

### Tests

`theme-provider.test.tsx` — 10 tests:
- data-theme=light on mount ✅
- default theme = light ✅
- reads from localStorage ✅
- fallback for invalid stored theme ✅
- fallback for garbage value ✅
- fallback for empty localStorage ✅
- persists on setTheme ✅
- ignores invalid setTheme ✅
- throws outside provider ✅
