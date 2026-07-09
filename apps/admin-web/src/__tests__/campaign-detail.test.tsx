import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import CampaignDetailPage from "../pages/CampaignDetailPage";

// ── Helpers ──

function createRouter(initialRoute: string) {
  return createMemoryRouter(
    [
      {
        path: "/login",
        element: <div>Login</div>,
      },
      {
        path: "/",
        element: (
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        ),
        children: [
          { path: "campaigns", element: <div>Campaign List</div> },
          { path: "campaigns/:id", element: <CampaignDetailPage /> },
        ],
      },
    ],
    { initialEntries: [initialRoute] },
  );
}

function mockAuthenticatedSession() {
  localStorage.setItem("rmp_access_token", "valid-token");
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(
      JSON.stringify({
        sub: "u1",
        auth_provider: "ad",
        username: "admin",
        display_name: "Admin",
      }),
      { status: 200 },
    ),
  );
}

const SEED_CAMPAIGN = {
  id: "c1",
  advertiser_organization_id: "org-1",
  advertiser_brand_id: "brand-1",
  advertiser_contract_id: "con-1",
  code: "CAMP-001",
  name: "Весенняя акция",
  description: "Тестовое описание",
  status: "draft",
  priority: 0,
  budget_limit_amount: 500000,
  budget_limit_currency: "RUB",
  start_at: "2026-04-01T00:00:00Z",
  end_at: "2026-05-31T00:00:00Z",
  timezone: "Europe/Moscow",
  created_by: "u1",
  created_at: "2026-03-15T10:00:00Z",
  updated_at: "2026-03-20T14:00:00Z",
};

const SEED_CAMPAIGNS = [SEED_CAMPAIGN];

const SEED_FLIGHTS = [
  {
    id: "f1",
    campaign_id: "c1",
    name: "Апрель",
    start_at: "2026-04-01T00:00:00Z",
    end_at: "2026-04-30T00:00:00Z",
    dayparting_json: null,
    days_of_week: null,
    priority: 0,
    created_at: "2026-03-15T10:00:00Z",
  },
  {
    id: "f2",
    campaign_id: "c1",
    name: "Май",
    start_at: "2026-05-01T00:00:00Z",
    end_at: "2026-05-31T00:00:00Z",
    dayparting_json: null,
    days_of_week: null,
    priority: 0,
    created_at: "2026-03-15T10:00:00Z",
  },
];

const SEED_PLACEMENTS = [
  {
    id: "p1",
    campaign_id: "c1",
    display_surface_id: "ds-1",
    store_id: "st-1",
    cluster_id: null,
    branch_id: null,
    share_of_voice_pct: 100,
    max_impressions: null,
    impressions_delivered: 0,
    status: "active",
    created_at: "2026-03-15T10:00:00Z",
  },
];

const SEED_CREATIVES = [
  {
    id: "cc1",
    campaign_id: "c1",
    creative_asset_id: "ca-1",
    sort_order: 0,
    duration_override_ms: null,
    created_at: "2026-03-15T10:00:00Z",
  },
];

const SEED_ASSETS = [
  {
    id: "ca-1",
    advertiser_organization_id: "org-1",
    code: "CR-001",
    name: "Баннер весна",
    media_type: "image/jpeg",
    sha256_checksum: "abc123",
    file_size_bytes: 102400,
    duration_ms: null,
    resolution_w: 1920,
    resolution_h: 1080,
    status: "active",
    moderation_status: "approved",
    created_at: "2026-03-10T08:00:00Z",
    updated_at: "2026-03-10T08:00:00Z",
  },
];

const SEED_ORGS = [
  { id: "org-1", code: "ADV-001", legal_name: "ООО Ромашка", display_name: "Ромашка", status: "active" },
];

const SEED_BRANDS = [
  { id: "brand-1", advertiser_organization_id: "org-1", code: "BR-001", name: "Чистая линия", status: "active" },
];

const SEED_CONTRACTS = [
  {
    id: "con-1",
    advertiser_organization_id: "org-1",
    code: "CON-001",
    name: "Договор №1",
    budget_limit_amount: 1000000,
    budget_limit_currency: "RUB",
    valid_from: "2026-01-01T00:00:00Z",
    valid_until: "2026-12-31T00:00:00Z",
    status: "active",
  },
];

// ── Tests ──

describe("CampaignDetailPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders campaign detail on successful fetch", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }
      // getCampaign → listCampaigns
      if (url.includes("/campaigns") && !url.includes("flights") && !url.includes("placements") && !url.includes("creatives")) {
        return new Response(JSON.stringify(SEED_CAMPAIGNS), { status: 200 });
      }
      if (url.includes("campaign-flights")) {
        return new Response(JSON.stringify(SEED_FLIGHTS), { status: 200 });
      }
      if (url.includes("campaign-placements")) {
        return new Response(JSON.stringify(SEED_PLACEMENTS), { status: 200 });
      }
      if (url.includes("campaign-creatives")) {
        return new Response(JSON.stringify(SEED_CREATIVES), { status: 200 });
      }
      if (url.includes("creative-assets")) {
        return new Response(JSON.stringify(SEED_ASSETS), { status: 200 });
      }
      if (url.includes("advertiser-organizations")) {
        return new Response(JSON.stringify(SEED_ORGS), { status: 200 });
      }
      if (url.includes("advertiser-brands")) {
        return new Response(JSON.stringify(SEED_BRANDS), { status: 200 });
      }
      if (url.includes("advertiser-contracts")) {
        return new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 });
      }
      if (url.includes("campaign-approvals")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter("/campaigns/c1");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    // Should show campaign name in heading + field value (2 occurrences)
    await waitFor(() => {
      const nameEls = screen.getAllByText("Весенняя акция");
      expect(nameEls.length).toBeGreaterThanOrEqual(1);
    });

    // Should show tabs
    expect(screen.getByText("Обзор")).toBeTruthy();
    expect(screen.getByText("Флайты")).toBeTruthy();
    expect(screen.getByText("Плейсменты")).toBeTruthy();
    expect(screen.getByText("Креативы")).toBeTruthy();
    expect(screen.getByText("Отчётность")).toBeTruthy();

    // Overview tab content
    const codeEls = screen.getAllByText("CAMP-001");
    expect(codeEls.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Черновик")).toBeTruthy();
    expect(screen.getByText("Ромашка")).toBeTruthy();
    expect(screen.getByText("Чистая линия")).toBeTruthy();
    expect(screen.getByText("Тестовое описание")).toBeTruthy();

    // Flights tab count badge
    const flightsTab = screen.getByText("Флайты").closest("button");
    expect(flightsTab).toBeTruthy();
    expect(flightsTab!.textContent).toContain("2");

    // Placements tab count badge
    const placementsTab = screen.getByText("Плейсменты").closest("button");
    expect(placementsTab).toBeTruthy();
    expect(placementsTab!.textContent).toContain("1");

    // Creatives tab count badge
    const creativesTab = screen.getByText("Креативы").closest("button");
    expect(creativesTab).toBeTruthy();
    expect(creativesTab!.textContent).toContain("1");
  });

  it("shows not found when campaign ID does not exist", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }
      // Return empty campaigns — ID won't match
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter("/campaigns/nonexistent");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Кампания не найдена")).toBeTruthy();
    });
  });

  it("shows error state on API failure", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({ detail: "Server error" }), { status: 500 });
    });

    const router = createRouter("/campaigns/c1");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ошибка")).toBeTruthy();
    });
  });

  it("401 clears session via existing client behavior", async () => {
    // Not authenticated — no token in localStorage
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unauthorized"));

    const router = createRouter("/campaigns/c1");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    // Should redirect to login
    await waitFor(() => {
      expect(screen.getByText("Login")).toBeTruthy();
    });
  });
});
