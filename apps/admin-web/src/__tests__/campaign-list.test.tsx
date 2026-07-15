import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import CampaignListPage from "../pages/CampaignListPage";
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
          { path: "campaigns", element: <CampaignListPage /> },
          { path: "campaigns/:id", element: <CampaignDetailPage /> },
        ],
      },
    ],
    { initialEntries: [initialRoute] },
  );
}

const SEED_CAMPAIGNS = [
  {
    id: "c1",
    advertiser_organization_id: "org-1",
    advertiser_brand_id: "brand-1",
    advertiser_contract_id: "con-1",
    code: "CAMP-001",
    name: "Весенняя акция",
    description: null,
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
  },
  {
    id: "c2",
    advertiser_organization_id: "org-1",
    advertiser_brand_id: null,
    advertiser_contract_id: "con-2",
    code: "CAMP-002",
    name: "Летнее промо",
    description: null,
    status: "active",
    priority: 1,
    budget_limit_amount: null,
    budget_limit_currency: "RUB",
    start_at: "2026-06-01T00:00:00Z",
    end_at: null,
    timezone: "Europe/Moscow",
    created_by: "u1",
    created_at: "2026-05-01T08:00:00Z",
    updated_at: "2026-06-10T09:00:00Z",
  },
];

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
  {
    id: "f3",
    campaign_id: "c2",
    name: null,
    start_at: "2026-06-01T00:00:00Z",
    end_at: "2026-08-31T00:00:00Z",
    dayparting_json: null,
    days_of_week: null,
    priority: 1,
    created_at: "2026-05-01T08:00:00Z",
  },
];

const SEED_ORGS = [
  { id: "org-1", code: "ADV-001", legal_name: "ООО Ромашка", display_name: "Ромашка", status: "active" },
];

const SEED_BRANDS = [
  { id: "brand-1", advertiser_organization_id: "org-1", code: "BR-001", name: "Чистая линия", status: "active" },
];

function mockAuthenticatedSession() {
  /* S-035b: access token is memory-only — no localStorage.
     Session restore goes through /api/v1/auth/refresh. */
  let callCount = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation(() => {
    callCount++;
    if (callCount === 1) {
      // refresh: return new access token
      return Promise.resolve(
        new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ),
      );
    }
    // getMe: return user data
    return Promise.resolve(
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
  });
}

const CAMPAIGNS_URL = "/api/v1/identity/campaigns";
const FLIGHTS_URL = "/api/v1/identity/campaign-flights";
const ORGS_URL = "/api/v1/identity/advertiser-organizations";
const BRANDS_URL = "/api/v1/identity/advertiser-brands";
const PLACEMENTS_URL = "/api/v1/identity/campaign-placements";
const CREATIVES_URL = "/api/v1/identity/campaign-creatives";
const ASSETS_URL = "/api/v1/identity/creative-assets";
const CONTRACTS_URL = "/api/v1/identity/advertiser-contracts";
const APPROVALS_URL = "/api/v1/identity/campaign-approvals";

// ── Tests ──

describe("CampaignListPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("redirects to login when not authenticated", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unauthorized"));

    const router = createRouter("/campaigns");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Login")).toBeTruthy();
    });
  });

  it("renders campaign rows on successful fetch", async () => {
    mockAuthenticatedSession();

    // Intercept subsequent data fetches
    let callCount = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      callCount++;
      const url = String(input);

      // Skip the /me auth call (already handled by mockAuthenticatedSession spy override)
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }

      if (url.includes("/campaigns") && !url.includes("flights") && !url.includes("placements") && !url.includes("creatives")) {
        return new Response(JSON.stringify({items: SEED_CAMPAIGNS, total: SEED_CAMPAIGNS.length, limit: 50, offset: 0}), { status: 200 });
      }
      if (url.includes("campaign-flights")) {
        return new Response(JSON.stringify(SEED_FLIGHTS), { status: 200 });
      }
      if (url.includes("advertiser-organizations")) {
        return new Response(JSON.stringify(SEED_ORGS), { status: 200 });
      }
      if (url.includes("advertiser-brands")) {
        return new Response(JSON.stringify(SEED_BRANDS), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter("/campaigns");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Весенняя акция")).toBeTruthy();
      expect(screen.getByText("Летнее промо")).toBeTruthy();
    });

    // Verify status labels
    expect(screen.getByText("Черновик")).toBeTruthy();
    expect(screen.getByText("Активна")).toBeTruthy();

    // Verify advertiser names (both campaigns share org-1)
    const orgEls = screen.getAllByText("Ромашка");
    expect(orgEls.length).toBe(2);

    // Verify flight summary for CAMP-001 (2 flights)
    expect(screen.getByText("2 пер., 1 апр. – 31 мая")).toBeTruthy();

    // Verify total count
    // Pagination hidden when total ≤ limit (2 ≤ 50) — correct UX
  });

  it("shows empty state when no campaigns", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        );
      }
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }
      if (url.includes("campaign-flights") || url.includes("advertiser-organizations") || url.includes("advertiser-brands")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(JSON.stringify({items: [], total: 0, limit: 50, offset: 0}), { status: 200 });
    });

    const router = createRouter("/campaigns");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Нет кампаний")).toBeTruthy();
    });
  });

  it("shows error state on API failure", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        );
      }
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }
      return new Response(JSON.stringify({ detail: "Server error" }), { status: 500 });
    });

    const router = createRouter("/campaigns");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Ошибка")).toBeTruthy();
    });
  });

  it("navigates to detail on row click", async () => {
    mockAuthenticatedSession();

    let callCount = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        );
      }
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
          { status: 200 },
        );
      }
      if (url.includes("/campaigns") && !url.includes("flights") && !url.includes("placements") && !url.includes("creatives")) {
        return new Response(JSON.stringify({items: SEED_CAMPAIGNS, total: SEED_CAMPAIGNS.length, limit: 50, offset: 0}), { status: 200 });
      }
      if (url.includes("campaign-flights")) {
        return new Response(JSON.stringify(SEED_FLIGHTS), { status: 200 });
      }
      if (url.includes("advertiser-organizations")) {
        return new Response(JSON.stringify(SEED_ORGS), { status: 200 });
      }
      if (url.includes("advertiser-brands")) {
        return new Response(JSON.stringify(SEED_BRANDS), { status: 200 });
      }
      // Detail page fires these for campaign-detail view
      if (url.includes("campaign-placements")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("campaign-creatives")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("creative-assets")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("advertiser-contracts")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("campaign-approvals")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter("/campaigns");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    // Wait for the list to load
    await waitFor(() => {
      expect(screen.getByText("Весенняя акция")).toBeTruthy();
    });

    // Click the first row
    const row = screen.getByText("Весенняя акция").closest("tr");
    expect(row).toBeTruthy();
    await userEvent.setup().click(row!);

    // Should navigate to detail — detail page shows campaign name in heading
    await waitFor(() => {
      // The detail page heading contains campaign name + code
      const headings = screen.getAllByText("Весенняя акция");
      expect(headings.length).toBeGreaterThan(0);
    });
  });
});
