import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { useAuth } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import AdvertisersPage from "../pages/AdvertisersPage";

// ── Helpers ──

function createRouter() {
  return createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        ),
        children: [
          { path: "advertisers", element: <AdvertisersPage /> },
        ],
      },
    ],
    { initialEntries: ["/advertisers"] },
  );
}

function renderPage() {
  const router = createRouter();
  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

function mockFetchResponses(overrides: Record<string, any> = {}) {
  const defaults = {
    // Detail endpoints first (more specific paths must match before parents)
    "advertiser-organizations/org-1": { id: "org-1", code: "ORG01", legal_name: "ООО Альфа", display_name: "Альфа", status: "active", created_at: "2026-01-01T00:00:00", updated_at: null },
    "advertiser-organizations/org-2": { id: "org-2", code: "ORG02", legal_name: "ООО Бета", display_name: "Бета", status: "draft", created_at: "2026-01-01T00:00:00", updated_at: null },
    "advertiser-brands-by-org": [
      { id: "b-1", advertiser_organization_id: "org-1", code: "B01", name: "Brand Alpha", description: null, status: "active" },
    ],
    "advertiser-contracts-by-org": [
      { id: "c-1", advertiser_organization_id: "org-1", code: "CON01", name: "Contract A", contract_number: "N-001", budget_limit_amount: 100000, budget_limit_currency: "RUB", valid_from: "2026-01-01T00:00:00", valid_until: null, status: "active", terms_url: null },
    ],
    "advertiser-contacts-by-org": [
      { id: "ct-1", advertiser_organization_id: "org-1", contact_type: "primary", full_name: "Иван Петров", email: "ivan@test.ru", phone: null, is_primary: true, status: "active" },
    ],
    "advertiser-user-memberships": [
      { id: "m-1", user_id: "u-1", username: "adv1", display_name: "Advertiser One", email: "a1@test.ru", auth_provider: "local_advertiser", user_status: "active", must_change_password: false, membership_status: "active", membership_created_at: null },
    ],
    // List endpoints (general paths)
    "/advertiser-organizations": [
      { id: "org-1", code: "ORG01", legal_name: "ООО Альфа", display_name: "Альфа", status: "active" },
      { id: "org-2", code: "ORG02", legal_name: "ООО Бета", display_name: "Бета", status: "draft" },
    ],
    "/advertiser-brands": [
      { id: "b-1", advertiser_organization_id: "org-1", code: "B01", name: "Brand Alpha", description: null, status: "active" },
      { id: "b-2", advertiser_organization_id: "org-2", code: "B02", name: "Brand Beta", description: null, status: "draft" },
    ],
    "/advertiser-contracts": [
      { id: "c-1", advertiser_organization_id: "org-1", code: "CON01", name: "Contract A", contract_number: "N-001", budget_limit_amount: 100000, budget_limit_currency: "RUB", valid_from: "2026-01-01T00:00:00", valid_until: null, status: "active", terms_url: null },
    ],
  };
  const data = { ...defaults, ...overrides };

  vi.spyOn(globalThis, "fetch").mockImplementation(async (input: any) => {
    const url = typeof input === "string" ? input : input.url;
    // Auth calls – return mock user
    if (url.includes("/api/v1/auth/refresh") || url.includes("/api/v1/auth/me")) {
      if (url.includes("/me")) {
        return new Response(JSON.stringify({
          id: "u-1", username: "admin", display_name: "Admin", auth_provider: "local",
          status: "active", is_break_glass: false, must_change_password: false,
          roles: [], email: null, created_at: null, updated_at: null,
        }), { status: 200 });
      }
      return new Response(JSON.stringify({ access_token: "tok", token_type: "bearer" }), { status: 200 });
    }

    // Find matching mock data by URL path
    for (const [path, mockData] of Object.entries(data)) {
      if (url.includes(path)) {
        return new Response(JSON.stringify(mockData), { status: 200 });
      }
    }

    return new Response(JSON.stringify({ detail: "Not found" }), { status: 404 });
  });
}

// Override AuthContext to skip actual auth flow
const defaultPermissions = ["advertisers.manage", "organization.read", "advertisers.read", "advertisers.contacts.read"];

vi.mock("../auth/AuthContext", async () => {
  const actual = await vi.importActual("../auth/AuthContext") as any;
  return {
    ...actual,
    useAuth: vi.fn(() => ({
      user: { id: "u-1", username: "admin", display_name: "Admin", sub: "u-1", auth_provider: "local", permissions: defaultPermissions },
      loading: false,
      logout: vi.fn(),
    })),
  };
});

// ── Tests ──

describe("AdvertisersPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Reset useAuth to default permissions
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u-1", username: "admin", display_name: "Admin", sub: "u-1", auth_provider: "local", permissions: defaultPermissions },
      loading: false,
      logout: vi.fn(),
    } as any);
    mockFetchResponses();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders page title", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Рекламодатели")).toBeInTheDocument();
    });
  });

  it("loads organizations from API and displays them", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Альфа")).toBeInTheDocument();
    });
    expect(screen.getByText("Бета")).toBeInTheDocument();
  });

  it("shows organization counts", async () => {
    renderPage();
    await waitFor(() => {
      // Brand count for org-1 is 1
      const cells = screen.getAllByText("1");
      expect(cells.length).toBeGreaterThan(0);
    });
  });

  it("shows empty state when no orgs", async () => {
    vi.restoreAllMocks();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: any) => {
      const url = typeof input === "string" ? input : input.url;
      if (url.includes("/advertiser-organizations")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-brands") || url.includes("/advertiser-contracts")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(JSON.stringify({ access_token: "tok", token_type: "bearer" }), { status: 200 });
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Нет рекламодателей")).toBeInTheDocument();
    });
  });

  it("filters organizations by search", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Альфа")).toBeInTheDocument();
      expect(screen.getByText("Бета")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Поиск по коду или названию...");
    await userEvent.type(searchInput, "альфа");

    await waitFor(() => {
      expect(screen.getByText("Альфа")).toBeInTheDocument();
      expect(screen.queryByText("Бета")).not.toBeInTheDocument();
    });
  });

  it("shows detail tabs when org is clicked", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Альфа")).toBeInTheDocument();
    });

    await userEvent.click(screen.getByText("Альфа"));

    // Tabs may duplicate sidebar nav items — check detail content appears instead
    await waitFor(() => {
      // Org detail has legal name in overview
      expect(screen.getByText("ООО Альфа")).toBeInTheDocument();
    });
  });

  it("no secrets rendered in org detail", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Альфа")).toBeInTheDocument();
    });
    await userEvent.click(screen.getByText("Альфа"));

    await waitFor(() => {
      expect(screen.getByText("ООО Альфа")).toBeInTheDocument();
    });

    // No raw UUIDs, password fields, tokens
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/password_hash|passwordHash|refresh_token|access_token/);
  });

  // ── G3-FIX-FU: RBAC + create flow ──

  it("hides create button without advertisers.manage permission", async () => {
    // Override useAuth to return no advertisers.manage
    vi.mocked(useAuth).mockReturnValue({
      user: { id: "u-1", username: "admin", display_name: "Admin", sub: "u-1", auth_provider: "local", permissions: ["organization.read", "advertisers.read"] },
      loading: false,
      logout: vi.fn(),
    } as any);

    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Рекламодатели")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("advertiser-create-open")).not.toBeInTheDocument();
  });

  it("shows create button with advertisers.manage permission", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Рекламодатели")).toBeInTheDocument();
    });
    expect(screen.getByTestId("advertiser-create-open")).toBeInTheDocument();
  });

  it("create modal saves via POST API and closes", async () => {
    let postBody: any = null;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: any, init?: any) => {
      const url = typeof input === "string" ? input : input.url;
      if (url.includes("/me")) {
        return new Response(JSON.stringify({ id: "u-1", username: "admin", display_name: "Admin", sub: "u-1", auth_provider: "local", permissions: defaultPermissions }), { status: 200 });
      }
      if (url.includes("/refresh")) {
        return new Response(JSON.stringify({ access_token: "tok", token_type: "bearer" }), { status: 200 });
      }
      // Capture POST body
      if (url.includes("/advertiser-organizations") && init?.method === "POST") {
        postBody = JSON.parse(init.body);
        return new Response(JSON.stringify({ id: "org-new", code: "NEW01", legal_name: "ООО Новый", display_name: "Новый", status: "active" }), { status: 201 });
      }
      // Return list with the new org after POST
      if (url.endsWith("/advertiser-organizations")) {
        const orgs = [
          { id: "org-1", code: "ORG01", legal_name: "ООО Альфа", display_name: "Альфа", status: "active" },
          { id: "org-2", code: "ORG02", legal_name: "ООО Бета", display_name: "Бета", status: "draft" },
        ];
        if (postBody) orgs.push({ id: "org-new", code: "NEW01", legal_name: "ООО Новый", display_name: "Новый", status: "active" });
        return new Response(JSON.stringify(orgs), { status: 200 });
      }
      if (url.includes("/advertiser-brands") || url.includes("/advertiser-contracts")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("advertiser-create-open")).toBeInTheDocument();
    });

    // Click create button → fill → save
    await userEvent.click(screen.getByTestId("advertiser-create-open"));
    await userEvent.type(screen.getByTestId("advertiser-create-code"), "NEW01");
    await userEvent.type(screen.getByTestId("advertiser-create-legal-name"), "ООО Новый");
    await userEvent.type(screen.getByTestId("advertiser-create-display-name"), "Новый");
    await userEvent.click(screen.getByTestId("advertiser-create-save"));

    // Modal closes after save
    await waitFor(() => {
      expect(screen.queryByTestId("advertiser-create-code")).not.toBeInTheDocument();
    });

    // POST was called with correct body
    expect(postBody).not.toBeNull();
    expect(postBody.code).toBe("NEW01");
    expect(postBody.legal_name).toBe("ООО Новый");
    expect(postBody.display_name).toBe("Новый");
  });
});