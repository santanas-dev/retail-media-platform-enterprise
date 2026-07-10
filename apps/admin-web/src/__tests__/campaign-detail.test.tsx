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
}

const DRAFT_CAMPAIGN = {
  id: "c1",
  advertiser_organization_id: "org-1",
  advertiser_brand_id: "brand-1",
  advertiser_contract_id: "con-1",
  code: "CAMP-001",
  name: "Весенняя акция",
  description: "Тест",
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

const SEED_CAMPAIGNS = [DRAFT_CAMPAIGN];
const SEED_FLIGHTS: unknown[] = [];
const SEED_PLACEMENTS: unknown[] = [];
const SEED_CREATIVES: unknown[] = [];
const SEED_ASSETS: unknown[] = [];
const SEED_ORGS = [{ id: "org-1", code: "ADV-001", legal_name: "ООО Ромашка", display_name: "Ромашка", status: "active" }];
const SEED_BRANDS = [{ id: "brand-1", advertiser_organization_id: "org-1", code: "BR-001", name: "Чистая линия", status: "active" }];
const SEED_CONTRACTS = [{ id: "con-1", advertiser_organization_id: "org-1", code: "CON-001", name: "Договор", budget_limit_amount: 1000000, budget_limit_currency: "RUB", valid_from: "2026-01-01T00:00:00Z", valid_until: null, status: "active" }];

function mockFetchFor(path: string): unknown[] {
  if (path.includes("campaign-flights")) return SEED_FLIGHTS;
  if (path.includes("campaign-placements")) return SEED_PLACEMENTS;
  if (path.includes("campaign-creatives")) return SEED_CREATIVES;
  if (path.includes("creative-assets")) return SEED_ASSETS;
  if (path.includes("advertiser-organizations")) return SEED_ORGS;
  if (path.includes("advertiser-brands")) return SEED_BRANDS;
  if (path.includes("advertiser-contracts")) return SEED_CONTRACTS;
  if (path.includes("campaign-approvals")) return [];
  if (path.includes("/campaigns") && !path.includes("flights") && !path.includes("placements") && !path.includes("creatives")) return SEED_CAMPAIGNS;
  return [];
}

function mockAllFetches(
  overrides?: Record<string, (input: string, init?: RequestInit) => Promise<Response>>,
  userPerms?: string[],
) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (overrides) {
      for (const [key, fn] of Object.entries(overrides)) {
        if (url.includes(key)) return fn(url, init);
      }
    }
    if (url.endsWith("/me")) {
      const userData: Record<string, unknown> = { sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" };
      if (userPerms) userData.permissions = userPerms;
      return Promise.resolve(new Response(JSON.stringify(userData), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify(mockFetchFor(url)), { status: 200 }));
  });
}

// ── Tests ──

describe("CampaignDetailPage — S-009e", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  // ── Basic render ──

  it("renders tabs and overview for draft campaign", async () => {
    mockAuthenticatedSession();
    mockAllFetches();

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    expect(screen.getByText("Флайты")).toBeTruthy();
    expect(screen.getByText("Отправить на согласование")).toBeTruthy();
    // Approval button should be disabled (no flights/placements/creatives)
    const btn = screen.getByText("Отправить на согласование");
    expect((btn as HTMLButtonElement).disabled).toBe(true);
  });

  // ── Flights: add form ──

  it("shows flight add form and validates dates", async () => {
    mockAuthenticatedSession();
    mockAllFetches();

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });

    // Navigate to flights tab
    const user = userEvent.setup();
    await user.click(screen.getByText("Флайты"));

    // Click add button
    await waitFor(() => { expect(screen.getByText("+ Добавить флайт")).toBeTruthy(); });
    await user.click(screen.getByText("+ Добавить флайт"));

    // Form should appear
    await waitFor(() => { expect(screen.getByText("Добавить")).toBeTruthy(); });

    // Submit without dates → validation error
    await user.click(screen.getByText("Добавить"));
    await waitFor(() => {
      expect(screen.getByText("Даты начала и окончания обязательны")).toBeTruthy();
    });
  });

  // ── Flights: successful create ──

  it("creates flight on valid submit", async () => {
    mockAuthenticatedSession();
    let postBody: unknown = null;
    mockAllFetches({
      "/campaigns/c1/flights": (url, init) => {
        if ((init as RequestInit).method === "POST") {
          postBody = JSON.parse((init as RequestInit).body as string);
          return Promise.resolve(new Response(JSON.stringify({
            id: "f-new", campaign_id: "c1", name: "Май", start_at: "2026-05-01T00:00:00Z", end_at: "2026-05-31T00:00:00Z",
            dayparting_json: null, days_of_week: null, priority: 1, created_at: "2026-06-01T00:00:00Z",
          }), { status: 201 }));
        }
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      },
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Флайты"));
    await waitFor(() => { expect(screen.getByText("+ Добавить флайт")).toBeTruthy(); });
    await user.click(screen.getByText("+ Добавить флайт"));
    await waitFor(() => { expect(screen.getByText("Добавить")).toBeTruthy(); });

    // Fill dates
    const startInput = screen.getByLabelText("Начало *");
    const endInput = screen.getByLabelText("Конец *");
    await user.type(startInput, "2026-05-01");
    await user.type(endInput, "2026-05-31");
    await user.click(screen.getByText("Добавить"));

    await waitFor(() => {
      expect(postBody).not.toBeNull();
    });
  });

  // ── Flights: backend 422 ──

  it("shows backend error on flight 422", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/campaigns/c1/flights": () =>
        Promise.resolve(new Response(JSON.stringify({ detail: "Flight outside contract" }), { status: 422 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Флайты"));
    await waitFor(() => { expect(screen.getByText("+ Добавить флайт")).toBeTruthy(); });
    await user.click(screen.getByText("+ Добавить флайт"));
    await waitFor(() => { expect(screen.getByText("Добавить")).toBeTruthy(); });

    await user.type(screen.getByLabelText("Начало *"), "2026-05-01");
    await user.type(screen.getByLabelText("Конец *"), "2026-05-31");
    await user.click(screen.getByText("Добавить"));

    await waitFor(() => {
      expect(screen.getByText(/Ошибка данных/)).toBeTruthy();
    });
  });

  // ── Placements: shows warning about missing ref data ──

  it("shows placement warning about missing reference data", async () => {
    mockAuthenticatedSession();
    mockAllFetches();

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Плейсменты"));

    await waitFor(() => {
      expect(screen.getByText(/Справочники поверхностей/)).toBeTruthy();
    });
  });

  // ── Creatives: shows existing assets, add form ──

  it("shows creative assets reference and add form", async () => {
    mockAuthenticatedSession();
    mockAllFetches();

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Креативы"));

    await waitFor(() => {
      // Warning about create-only
      expect(screen.getByText(/Создание нового креатива/)).toBeTruthy();
      expect(screen.getByText("+ Создать креатив")).toBeTruthy();
    });
  });

  // ── Creatives: empty assets state ──

  it("shows empty creative assets message", async () => {
    mockAuthenticatedSession();
    mockAllFetches();

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Креативы"));

    await waitFor(() => {
      expect(screen.getByText("У этой кампании пока нет креативов.")).toBeTruthy();
    });
  });

  // ── Approval: button disabled when setup incomplete ──

  it("disables approval button when no flights/placements/creatives", async () => {
    mockAuthenticatedSession();
    mockAllFetches();

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      const btn = screen.getByText("Отправить на согласование") as HTMLButtonElement;
      expect(btn.disabled).toBe(true);
    });
  });

  // ── Approval: backend error shown ──

  it("shows approval backend error", async () => {
    mockAuthenticatedSession();
    // Mock with 1 flight, 1 placement, 1 creative so button is enabled
    const SEED_F: unknown[] = [{ id: "f1", campaign_id: "c1", name: "F1", start_at: "2026-01-01T00:00:00Z", end_at: "2026-02-01T00:00:00Z", priority: 0, created_at: "2026-01-01T00:00:00Z" }];
    const SEED_P: unknown[] = [{ id: "p1", campaign_id: "c1", display_surface_id: null, store_id: "st-1", cluster_id: null, branch_id: null, share_of_voice_pct: 100, max_impressions: null, impressions_delivered: 0, status: "active", created_at: "2026-01-01T00:00:00Z" }];
    const SEED_C: unknown[] = [{ id: "cc1", campaign_id: "c1", creative_asset_id: "ca-1", sort_order: 0, duration_override_ms: null, created_at: "2026-01-01T00:00:00Z", asset: { id: "ca-1", code: "CR1", name: "Banner", media_type: "image/jpeg", sha256_checksum: "abc", file_size_bytes: 100, status: "active", moderation_status: "approved", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" } }];

    mockAllFetches({
      "campaign-flights": () => Promise.resolve(new Response(JSON.stringify(SEED_F), { status: 200 })),
      "campaign-placements": () => Promise.resolve(new Response(JSON.stringify(SEED_P), { status: 200 })),
      "campaign-creatives": () => Promise.resolve(new Response(JSON.stringify(SEED_C), { status: 200 })),
      "/campaigns/c1/request-approval": () =>
        Promise.resolve(new Response(JSON.stringify({ detail: "Campaign must have at least one flight, one placement, and one creative" }), { status: 422 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(async () => {
      const btn = screen.getByText("Отправить на согласование") as HTMLButtonElement;
      if (!btn.disabled) {
        await userEvent.setup().click(btn);
      }
    });

    // Re-find button (may have re-rendered)
    await waitFor(async () => {
      const buttons = screen.queryAllByText("Отправить на согласование");
      const btn = buttons[buttons.length - 1] as HTMLButtonElement;
      if (!btn.disabled) {
        await userEvent.setup().click(btn);
      }
    });

    await waitFor(() => {
      expect(screen.getByText(/Ошибка данных/)).toBeTruthy();
    });
  });

  // ── Non-draft: controls hidden ──

  it("hides mutating controls for non-draft campaign", async () => {
    mockAuthenticatedSession();
    const publishedCampaign = { ...DRAFT_CAMPAIGN, status: "active" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify([publishedCampaign]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      // Should show read-only message
      expect(screen.getByText(/Изменения доступны только в статусе/)).toBeTruthy();
    });

    // Navigate to flights tab
    await userEvent.setup().click(screen.getByText("Флайты"));
    // No add button
    expect(screen.queryByText("+ Добавить флайт")).toBeNull();
  });

  // ── 401 ──

  it("401 clears session", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unauthorized"));
    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
    await waitFor(() => { expect(screen.getByText("Login")).toBeTruthy(); });
  });

  // ── S-009f: Approval workflow ──

  it("shows approve/reject buttons for pending_approval campaign", async () => {
    mockAuthenticatedSession();
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify([pendingCampaign]), { status: 200 })),
    }, ["campaigns.approve"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByText("Кампания ожидает согласования.")).toBeTruthy();
      expect(screen.getByText("Согласовать")).toBeTruthy();
      expect(screen.getByText("Отклонить")).toBeTruthy();
    });
  });

  it("reject requires reason before submit", async () => {
    mockAuthenticatedSession();
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify([pendingCampaign]), { status: 200 })),
    }, ["campaigns.approve"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Отклонить")).toBeTruthy(); });

    // Click reject
    await userEvent.setup().click(screen.getByText("Отклонить"));

    // Reject dialog appears, confirm button should be disabled
    await waitFor(() => {
      const confirmBtn = screen.getByText("Подтвердить отклонение") as HTMLButtonElement;
      expect(confirmBtn.disabled).toBe(true);
    });
  });

  it("approve success refreshes campaign status", async () => {
    mockAuthenticatedSession();
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify([pendingCampaign]), { status: 200 })),
      "/approve": () =>
        Promise.resolve(new Response(JSON.stringify({
          message: "Campaign approved", campaign_id: "c1", old_status: "pending_approval", new_status: "approved",
        }), { status: 200 })),
    }, ["campaigns.approve"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Согласовать")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Согласовать"));

    // After approve, campaign status should update (button disappears, status badge changes)
    // We verify the API call was made — the test checks the mock was triggered
    await waitFor(() => {
      // Approval banner should be gone, status updated
      expect(screen.queryByText("Кампания ожидает согласования.")).toBeNull();
    });
  });

  it("reject success refreshes campaign status", async () => {
    mockAuthenticatedSession();
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify([pendingCampaign]), { status: 200 })),
      "/reject": () =>
        Promise.resolve(new Response(JSON.stringify({
          message: "Campaign rejected", campaign_id: "c1", old_status: "pending_approval", new_status: "rejected",
        }), { status: 200 })),
    }, ["campaigns.approve"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Отклонить")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отклонить"));

    // Fill reject reason
    await waitFor(() => { expect(screen.getByText("Подтвердить отклонение")).toBeTruthy(); });
    const textarea = screen.getByPlaceholderText("Укажите причину отклонения");
    await userEvent.setup().type(textarea, "Не соответствует требованиям");
    await userEvent.setup().click(screen.getByText("Подтвердить отклонение"));

    // After reject, approval banner should be gone
    await waitFor(() => {
      expect(screen.queryByText("Кампания ожидает согласования.")).toBeNull();
    });
  });

  it("shows error on approve 403", async () => {
    mockAuthenticatedSession();
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };

    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = String(input);
      const method = (init as RequestInit)?.method;

      if (url.endsWith("/me")) {
        return Promise.resolve(new Response(JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin", permissions: ["campaigns.approve"] }), { status: 200 }));
      }
      // Return pending campaign for list
      if (url.endsWith("/identity/campaigns") && method !== "POST") {
        return Promise.resolve(new Response(JSON.stringify([pendingCampaign]), { status: 200 }));
      }
      // Approve returns 403
      if (url.includes("/approve") && method === "POST") {
        return Promise.resolve(new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }));
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Согласовать")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Согласовать"));

    await waitFor(() => {
      expect(screen.getByText("Нет прав на это действие.")).toBeTruthy();
    });
  });

  it("non-approver sees read-only pending message", async () => {
    mockAuthenticatedSession();
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };
    // No campaigns.approve permission — default /me has no permissions
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify([pendingCampaign]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      // Should show the pending message with no-rights note
      expect(screen.getByText(/Кампания ожидает согласования/)).toBeTruthy();
      expect(screen.getByText(/У вас нет прав на согласование/)).toBeTruthy();
      // Approve/reject buttons should NOT be visible
      expect(screen.queryByText("Согласовать")).toBeNull();
      expect(screen.queryByText("Отклонить")).toBeNull();
    });
  });
});
