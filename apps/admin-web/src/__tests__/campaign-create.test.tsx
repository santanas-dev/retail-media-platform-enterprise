import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import CampaignCreatePage from "../pages/CampaignCreatePage";
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
          { path: "campaigns/new", element: <CampaignCreatePage /> },
          { path: "campaigns/:id", element: <CampaignDetailPage /> },
        ],
      },
    ],
    { initialEntries: [initialRoute] },
  );
}

function mockAuthenticatedSession() {
  /* S-035b: access token is memory-only — no localStorage.
     Session restore goes through /api/v1/auth/refresh. */
}

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

describe("CampaignCreatePage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // ── 1. Unauthenticated redirect ──

  it("redirects to login when not authenticated", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unauthorized"));

    const router = createRouter("/campaigns/new");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Login")).toBeTruthy();
    });
  });

  // ── 2. Reference data loading renders selectors ──

  it("loads reference data and renders selectors", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
            { status: 200 },
          ),
        );
      }
      if (url.includes("advertiser-organizations")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_ORGS), { status: 200 }));
      }
      if (url.includes("advertiser-brands")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_BRANDS), { status: 200 }));
      }
      if (url.includes("advertiser-contracts")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/campaigns/new");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    // Wait for form to appear
    await waitFor(() => {
      expect(screen.getByText("Новая кампания")).toBeTruthy();
    });

    // Should show org selector with option
    const orgSelect = screen.getByLabelText(/Организация/) as HTMLSelectElement;
    expect(orgSelect).toBeTruthy();
    expect(orgSelect.options.length).toBeGreaterThan(1); // default + seed

    // Should have required field labels
    expect(screen.getByText("Название")).toBeTruthy();
    expect(screen.getByText("Код")).toBeTruthy();
    expect(screen.getByText("Создать черновик")).toBeTruthy();
  });

  // ── 3. Required-field validation blocks submit ──

  it("shows validation error when required fields empty", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
            { status: 200 },
          ),
        );
      }
      if (url.includes("advertiser-organizations")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_ORGS), { status: 200 }));
      }
      if (url.includes("advertiser-brands")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_BRANDS), { status: 200 }));
      }
      if (url.includes("advertiser-contracts")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/campaigns/new");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Новая кампания")).toBeTruthy();
    });

    // Click submit with empty form
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "Создать черновик" }));

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText("Название кампании обязательно")).toBeTruthy();
    });
  });

  // ── 4. Successful submit ──

  it("submits campaign and navigates to detail on success", async () => {
    mockAuthenticatedSession();

    const createdCampaign = {
      id: "new-c1",
      advertiser_organization_id: "org-1",
      advertiser_brand_id: "brand-1",
      advertiser_contract_id: "con-1",
      code: "SPRING-2026",
      name: "Весенняя акция",
      description: "Тест",
      status: "draft",
      priority: 1,
      budget_limit_amount: 500000,
      budget_limit_currency: "RUB",
      start_at: "2026-04-01T00:00:00.000Z",
      end_at: "2026-05-31T00:00:00.000Z",
      timezone: "Europe/Moscow",
      created_by: "u1",
      created_at: "2026-03-20T10:00:00Z",
      updated_at: "2026-03-20T10:00:00Z",
    };

    let postBody: unknown = null;

    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = (init as RequestInit)?.method;

      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
            { status: 200 },
          ),
        );
      }
      if (url.includes("advertiser-organizations")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_ORGS), { status: 200 }));
      }
      if (url.includes("advertiser-brands")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_BRANDS), { status: 200 }));
      }
      if (url.includes("advertiser-contracts")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 }));
      }
      // POST /campaigns — capture the body
      if (method === "POST" && url.includes("/campaigns") && !url.includes("flights") && !url.includes("placements")) {
        postBody = JSON.parse((init as RequestInit).body as string);
        return Promise.resolve(new Response(JSON.stringify(createdCampaign), { status: 201 }));
      }
      // Detail page data fetches after redirect
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/campaigns/new");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Новая кампания")).toBeTruthy();
    });

    const user = userEvent.setup();

    // Fill required fields
    await user.type(screen.getByLabelText(/Название/), "Весенняя акция");
    // Select org
    await user.selectOptions(screen.getByLabelText(/Организация/), "org-1");
    // Select contract (appears after org)
    await waitFor(async () => {
      const contractSelect = screen.getByLabelText("Договор *") as HTMLSelectElement;
      expect(contractSelect.options.length).toBeGreaterThan(1);
      await user.selectOptions(contractSelect, "con-1");
    });
    // Select brand
    await user.selectOptions(screen.getByLabelText("Бренд"), "brand-1");

    await user.click(screen.getByRole("button", { name: "Создать черновик" }));

    // Wait for submit and verify body
    await waitFor(() => {
      expect(postBody).not.toBeNull();
      expect((postBody as Record<string, unknown>).name).toBe("Весенняя акция");
      expect((postBody as Record<string, unknown>).advertiser_organization_id).toBe("org-1");
      expect((postBody as Record<string, unknown>).advertiser_contract_id).toBe("con-1");
    });

    // Should navigate to detail page
    await waitFor(() => {
      expect(screen.getByText("← К списку кампаний")).toBeTruthy();
    });
  });

  // ── 5. Backend 422 error ──

  it("shows error on backend 422", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = (init as RequestInit)?.method;

      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
            { status: 200 },
          ),
        );
      }
      if (url.includes("advertiser-organizations")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_ORGS), { status: 200 }));
      }
      if (url.includes("advertiser-brands")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_BRANDS), { status: 200 }));
      }
      if (url.includes("advertiser-contracts")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 }));
      }
      if (method === "POST" && url.includes("/campaigns")) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: "Cross-org reference error" }), { status: 422 }),
        );
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/campaigns/new");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Новая кампания")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Название/), "Test");
    await user.selectOptions(screen.getByLabelText(/Организация/), "org-1");
    await waitFor(async () => {
      const contractSelect = screen.getByLabelText("Договор *") as HTMLSelectElement;
      await user.selectOptions(contractSelect, "con-1");
    });

    await user.click(screen.getByRole("button", { name: "Создать черновик" }));

    await waitFor(() => {
      expect(screen.getByText(/Ошибка данных/)).toBeTruthy();
    });
  });

  // ── 6. Backend 403 error ──

  it("shows permission error on backend 403", async () => {
    mockAuthenticatedSession();

    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = (init as RequestInit)?.method;

      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" }),
            { status: 200 },
          ),
        );
      }
      if (url.includes("advertiser-organizations")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_ORGS), { status: 200 }));
      }
      if (url.includes("advertiser-brands")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_BRANDS), { status: 200 }));
      }
      if (url.includes("advertiser-contracts")) {
        return Promise.resolve(new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 }));
      }
      if (method === "POST" && url.includes("/campaigns")) {
        return Promise.resolve(
          new Response(JSON.stringify({ detail: "Scope error" }), { status: 403 }),
        );
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/campaigns/new");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Новая кампания")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/Название/), "Test");
    await user.selectOptions(screen.getByLabelText(/Организация/), "org-1");
    await waitFor(async () => {
      const contractSelect = screen.getByLabelText("Договор *") as HTMLSelectElement;
      await user.selectOptions(contractSelect, "con-1");
    });

    await user.click(screen.getByRole("button", { name: "Создать черновик" }));

    await waitFor(() => {
      expect(screen.getByText(/Нет прав на создание/)).toBeTruthy();
    });
  });

  // ── 7. 401 triggers session clear ──

  it("401 triggers session clear", async () => {
    // Not authenticated — no token, mock 401 on /me
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unauthorized"));

    const router = createRouter("/campaigns/new");
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Login")).toBeTruthy();
    });
  });

  // ── S-086: Availability forecast on create page ──

  it("shows availability forecast section", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
      if (url.endsWith("/me")) return Promise.resolve(new Response(JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin", permissions: ["campaigns.read", "campaigns.write", "inventory.read"] }), { status: 200 }));
      if (url.includes("advertiser-organizations")) return Promise.resolve(new Response(JSON.stringify(SEED_ORGS), { status: 200 }));
      if (url.includes("advertiser-brands")) return Promise.resolve(new Response(JSON.stringify(SEED_BRANDS), { status: 200 }));
      if (url.includes("advertiser-contracts")) return Promise.resolve(new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 }));
      if (url.includes("/display-surfaces")) return Promise.resolve(new Response(JSON.stringify([{ id: "s1", store_id: "st1", code: "S01", resolution_w: 1920, resolution_h: 1080, is_active: true }]), { status: 200 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const router = createRouter("/campaigns/new");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Доступность инвентаря")).toBeTruthy(); });
    expect(screen.getByText("Проверить")).toBeTruthy();
  });

  it("shows availability result on check", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
      if (url.endsWith("/me")) return Promise.resolve(new Response(JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin", permissions: ["campaigns.read", "campaigns.write", "inventory.read"] }), { status: 200 }));
      if (url.includes("advertiser-organizations")) return Promise.resolve(new Response(JSON.stringify(SEED_ORGS), { status: 200 }));
      if (url.includes("advertiser-brands")) return Promise.resolve(new Response(JSON.stringify(SEED_BRANDS), { status: 200 }));
      if (url.includes("advertiser-contracts")) return Promise.resolve(new Response(JSON.stringify(SEED_CONTRACTS), { status: 200 }));
      if (url.includes("/display-surfaces")) return Promise.resolve(new Response(JSON.stringify([{ id: "s1", store_id: "st1", code: "S01", resolution_w: 1920, resolution_h: 1080, is_active: true }]), { status: 200 }));
      if (url.includes("/inventory/availability")) return Promise.resolve(new Response(JSON.stringify({ surface_id: "s1", starts_at: "2026-01-01T00:00:00Z", ends_at: "2026-02-01T00:00:00Z", all_available: true, total_requested: 0, total_available: 100, slots: [], conflicts: [] }), { status: 200 }));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const router = createRouter("/campaigns/new");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Доступность инвентаря")).toBeTruthy(); });
    // Select surface and fill dates
    const surfaceSelect = document.getElementById("fc-surface") as HTMLSelectElement;
    await userEvent.selectOptions(surfaceSelect, "s1");
    const startInput = document.getElementById("c-start") as HTMLInputElement;
    const endInput = document.getElementById("c-end") as HTMLInputElement;
    await userEvent.clear(startInput); await userEvent.type(startInput, "2026-01-01");
    await userEvent.clear(endInput); await userEvent.type(endInput, "2026-02-01");
    await userEvent.click(screen.getByText("Проверить"));

    await waitFor(() => { expect(screen.getByText("Доступно")).toBeTruthy(); });
  });
});
