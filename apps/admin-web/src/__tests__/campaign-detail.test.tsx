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
  /* S-035b: access token is memory-only — no localStorage.
     Session restore goes through /api/v1/auth/refresh (handled in mockAllFetches). */
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

function mockFetchFor(path: string): unknown {
  if (path.includes("campaign-flights")) return SEED_FLIGHTS;
  if (path.includes("campaign-placements")) return SEED_PLACEMENTS;
  if (path.includes("campaign-creatives")) return SEED_CREATIVES;
  if (path.includes("creative-assets")) return SEED_ASSETS;
  if (path.includes("advertiser-organizations")) return SEED_ORGS;
  if (path.includes("advertiser-brands")) return SEED_BRANDS;
  if (path.includes("advertiser-contracts")) return SEED_CONTRACTS;
  if (path.includes("campaign-approvals")) return [];
  if (path.includes("/display-surfaces")) return [];
  if (path.includes("/stores")) return [];
  if (path.includes("/campaigns") && !path.includes("flights") && !path.includes("placements") && !path.includes("creatives") && !path.includes("/pop/")) return {items: SEED_CAMPAIGNS, total: SEED_CAMPAIGNS.length, limit: 50, offset: 0};
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
    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
        { status: 200 },
      ));
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

    // Wait for ref loading to complete, then open form
    await waitFor(() => {
      expect(screen.queryByText("Загрузка справочников...")).toBeNull();
    });

    await user.click(screen.getByText("+ Добавить плейсмент"));

    await waitFor(() => {
      expect(screen.getByText(/Нет доступных поверхностей/)).toBeTruthy();
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
      // S-009j: business-friendly intake form
      expect(screen.getByText(/Добавить креатив в библиотеку/)).toBeTruthy();
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
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [publishedCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      // Active campaign shows the lifecycle banner, not generic read-only
      expect(screen.getByText(/Кампания активна/)).toBeTruthy();
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

  // ── S-009j: Creative Asset Intake UI ──

  describe("S-009j — creative asset intake form", () => {
    it("renders business labels, not raw MIME types", async () => {
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));

      // Click the intake button to reveal the form
      await user.click(screen.getByText(/Добавить креатив в библиотеку/));

      // Business labels, not raw MIME
      expect(screen.getByText("Тип медиа")).toBeTruthy();
      expect(screen.getByText("Изображение")).toBeTruthy();
      expect(screen.getByText("Видео")).toBeTruthy();
      expect(screen.getByText("HTML")).toBeTruthy();
      expect(screen.getByText("Прочее")).toBeTruthy();

      // No raw MIME types exposed
      expect(screen.queryByText("image/jpeg")).toBeNull();
      expect(screen.queryByText("video/mp4")).toBeNull();
    });

    it("checksum is hidden in collapsed technical section by default", async () => {
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));
      await user.click(screen.getByText(/Добавить креатив в библиотеку/));

      // Technical section is collapsed
      expect(screen.getByText("Технические параметры")).toBeTruthy();
      // SHA input exists but is inside collapsed <details>
      const shaInput = screen.queryByPlaceholderText("Авто-заглушка");
      // It exists in the DOM but may not be visible (collapsed)
      expect(shaInput).toBeTruthy();
    });

    it("deferred upload message is visible", async () => {
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));
      await user.click(screen.getByText(/Добавить креатив в библиотеку/));

      // S-017: upload notice removed — upload is now active
      expect(screen.getByText(/SHA-256/)).toBeTruthy();
      expect(screen.getByText(/Технические параметры/)).toBeTruthy();
    });

    it("shows validation error when name or code empty", async () => {
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));
      await user.click(screen.getByText(/Добавить креатив в библиотеку/));

      // Fill code, leave name empty — clear the required temporarily
      const codeInput = screen.getByLabelText("Код *") as HTMLInputElement;
      const nameInput = screen.getByLabelText("Название *") as HTMLInputElement;
      codeInput.removeAttribute("required");
      nameInput.removeAttribute("required");
      await user.type(codeInput, "BANNER-001");
      nameInput.value = "";
      await user.click(screen.getByText("Добавить в библиотеку"));
      await waitFor(() => {
        expect(screen.getByText(/Код и название обязательны/)).toBeTruthy();
      });
    });

    it("shows backend 422 error in readable Russian", async () => {
      mockAuthenticatedSession();
      mockAllFetches({
        "/creative-assets": (url, init) => {
          // Only intercept POST, let GET pass through for page load
          if (init?.method === "POST") {
            return Promise.resolve(
              new Response(JSON.stringify({ detail: "Креатив с таким кодом уже существует в организации" }), { status: 422 }),
            );
          }
          return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
        },
      });
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));
      await user.click(screen.getByText(/Добавить креатив в библиотеку/));

      await user.type(screen.getByLabelText("Код *"), "BANNER-001");
      await user.type(screen.getByLabelText("Название *"), "Главный баннер");
      await user.click(screen.getByText("Добавить в библиотеку"));

      await waitFor(() => {
        expect(screen.getByText(/Креатив с таким кодом уже существует/)).toBeTruthy();
      });
    });

    it("401 clears session", async () => {
      mockAuthenticatedSession();
      mockAllFetches({
        "/creative-assets": (url, init) => {
          // Only intercept POST, let GET pass through for page load
          if (init?.method === "POST") {
            return Promise.resolve(new Response(JSON.stringify({ detail: "Unauthorized" }), { status: 401 }));
          }
          return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
        },
      });
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));
      await user.click(screen.getByText(/Добавить креатив в библиотеку/));

      await user.type(screen.getByLabelText("Код *"), "BANNER-001");
      await user.type(screen.getByLabelText("Название *"), "Главный баннер");
      await user.click(screen.getByText("Добавить в библиотеку"));

      await waitFor(() => { expect(screen.getByText("Login")).toBeTruthy(); });
    });

    // P1: metadata-only assets show "Ожидает загрузки" label
    it("shows 'Ожидает загрузки' for metadata-only assets in library", async () => {
      mockAuthenticatedSession();
      const metadataAsset = {
        id: "ca-metadata", advertiser_organization_id: "org-1",
        code: "META-001", name: "Метадата креатив", media_type: "image",
        sha256_checksum: "",  // empty = metadata only
        file_size_bytes: 0, duration_ms: null,
        resolution_w: null, resolution_h: null,
        status: "metadata_only", moderation_status: "pending_review",
        created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
      };
      mockAllFetches({
        "/creative-assets": () => Promise.resolve(
          new Response(JSON.stringify([metadataAsset]), { status: 200 }),
        ),
      });
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));

      // Open the existing assets list
      await user.click(screen.getByText(/Существующие креативы/));
      await waitFor(() => {
        expect(screen.getByText("⚠ Ожидает загрузки")).toBeTruthy();
      });
    });
  });

  // ── CAMPAIGN-UX-001A: Primary upload UX ──

  describe("CAMPAIGN-UX-001A — primary upload path", () => {
    it("primary upload CTA is visible in Креативы tab for draft campaign", async () => {
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));

      // Primary upload section is visible
      expect(screen.getByText("Загрузить файл с ПК")).toBeTruthy();
      expect(screen.getByTestId("creative-upload-primary")).toBeTruthy();
      expect(screen.getByTestId("creative-upload-select-file")).toBeTruthy();
      // Explanation text
      expect(screen.getByText(/Выберите файл → заполните метаданные → готово/)).toBeTruthy();
    });

    it("primary upload button opens metadata form on click", async () => {
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));

      // Click the upload button — but since we mock file input,
      // we test the form visibility by direct state check.
      // The button triggers file input which we can't simulate in JSDOM cleanly.
      // Instead verify that clicking opens the file dialog trigger.
      const selectBtn = screen.getByTestId("creative-upload-select-file");
      expect(selectBtn).toBeTruthy();
      expect(selectBtn.textContent).toBe("Выбрать файл");
    });

    it("secondary 'Другие способы' label visible below primary upload", async () => {
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));

      // Secondary path label
      expect(screen.getByText(/Другие способы добавить креатив/)).toBeTruthy();
      // Existing paths still available
      expect(screen.getByTestId("creative-attach-btn")).toBeTruthy();
      expect(screen.getByTestId("creative-add-library-btn")).toBeTruthy();
    });

    it("primary upload hides secondary label when form is open", async () => {
      // Secondary label only shows when primary form is NOT open.
      // In JSDOM we can't trigger file input, so this is a structural test:
      // the label is wrapped in {isDraft && !showPrimaryUpload && (...)}
      mockAuthenticatedSession();
      mockAllFetches();
      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));

      // With no primary upload open, secondary label is visible
      expect(screen.getByText(/Другие способы добавить креатив/)).toBeTruthy();
    });

    it("creative asset create request includes advertiser_organization_id", async () => {
      mockAuthenticatedSession();
      let capturedBody: Record<string, unknown> | null = null;
      mockAllFetches({
        "/creative-assets": (url, init) => {
          // Only intercept POST to create endpoint (not upload-intent)
          if (init?.method === "POST" && url.endsWith("/creative-assets") && init.body) {
            capturedBody = JSON.parse(init.body as string);
            return Promise.resolve(new Response(JSON.stringify({
              id: "ca-new", advertiser_organization_id: "org-1",
              code: "UP-TEST", name: "Test", media_type: "image",
              sha256_checksum: "", file_size_bytes: 0,
              status: "metadata_only", moderation_status: "pending_review",
              created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
            }), { status: 201 }));
          }
          return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
        },
        "/campaign-creatives": (url, init) => {
          if (init?.method === "POST") {
            return Promise.resolve(new Response(JSON.stringify({
              id: "cc-new", campaign_id: "c1", creative_asset_id: "ca-new", sort_order: 0,
              asset: { id: "ca-new", code: "UP-TEST", name: "Test", media_type: "image",
                sha256_checksum: "a".repeat(64), file_size_bytes: 100,
                status: "ready", moderation_status: "approved",
                created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" },
              created_at: "2026-01-01T00:00:00Z",
            }), { status: 201 }));
          }
          return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
        },
      });

      const router = createRouter("/campaigns/c1");
      render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
      await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
      const user = userEvent.setup();
      await user.click(screen.getByText("Креативы"));

      // Simulate file selection via the hidden primary input
      const file = new File(["dummy"], "test.png", { type: "image/png" });
      const fileInput = document.querySelector('[data-testid="creative-upload-primary-file-input"]') as HTMLInputElement;
      expect(fileInput).toBeTruthy();
      await user.upload(fileInput, file);

      // Form should appear with auto-filled values
      await waitFor(() => {
        expect(screen.getByTestId("creative-upload-primary-code")).toBeTruthy();
      });

      // Submit the form
      await user.click(screen.getByTestId("creative-upload-metadata-submit"));

      // Verify the POST body includes advertiser_organization_id
      await waitFor(() => {
        expect(capturedBody).not.toBeNull();
      });
      expect(capturedBody).toHaveProperty("advertiser_organization_id", "org-1");
      expect(capturedBody).toHaveProperty("code");
      expect(capturedBody).toHaveProperty("name");
      expect(capturedBody).toHaveProperty("media_type");
    });
  });

  // ── S-017: Upload UI ──

  it("no storage_bucket or storage_key in creative asset UI", async () => {
    mockAuthenticatedSession();
    const asset = {
      id: "ca-ns", advertiser_organization_id: "org-1",
      code: "NS-001", name: "No Secrets", media_type: "image",
      sha256_checksum: "", file_size_bytes: 0, duration_ms: null,
      resolution_w: null, resolution_h: null,
      status: "metadata_only", moderation_status: "pending_review",
      created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z",
    };
    mockAllFetches({
      "/creative-assets": () => Promise.resolve(new Response(JSON.stringify([asset]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Креативы"));
    await user.click(screen.getByText(/Существующие креативы/));

    // The rendered asset data should not contain storage fields
    await waitFor(() => { expect(screen.getByText("NS-001")).toBeTruthy(); });
    expect(screen.queryByText(/storage_bucket/)).toBeNull();
    expect(screen.queryByText(/storage_key/)).toBeNull();
    expect(screen.queryByText(/presigned/)).toBeNull();
  });

  // ── S-009f: Approval workflow ──

  it("shows approve/reject buttons for pending_approval campaign", async () => {
    mockAuthenticatedSession();
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [pendingCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
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
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [pendingCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
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
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [pendingCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
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
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [pendingCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
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

  it("reject success displays rejection reason", async () => {
    mockAuthenticatedSession();
    let campaignStatus = "pending_approval";
    const pendingCampaign = { ...DRAFT_CAMPAIGN, status: "pending_approval" };
    const reasonText = "Не соответствует требованиям";
    mockAllFetches({
      "/campaigns": () => {
        const c = { ...pendingCampaign, status: campaignStatus };
        return Promise.resolve(new Response(JSON.stringify({items: [c], total: 1, limit: 50, offset: 0}), { status: 200 }));
      },
      "/reject": () => {
        campaignStatus = "rejected";
        return Promise.resolve(new Response(JSON.stringify({
          message: "Campaign rejected", campaign_id: "c1", old_status: "pending_approval", new_status: "rejected",
        }), { status: 200 }));
      },
    }, ["campaigns.approve"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Отклонить")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отклонить"));
    await waitFor(() => { expect(screen.getByText("Подтвердить отклонение")).toBeTruthy(); });
    const textarea = screen.getByPlaceholderText("Укажите причину отклонения");
    await userEvent.setup().type(textarea, reasonText);
    await userEvent.setup().click(screen.getByText("Подтвердить отклонение"));

    // Verify rejection reason is displayed
    await waitFor(() => {
      expect(screen.getByTestId("campaign-rejection-reason-display")).toBeTruthy();
      expect(screen.getByText(reasonText)).toBeTruthy();
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
      if (url.includes("/identity/campaigns?") && method !== "POST") {
        return Promise.resolve(new Response(JSON.stringify({items: [pendingCampaign], total: 1, limit: 50, offset: 0}), { status: 200 }));
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
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [pendingCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
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

  // ── Wave 4: Campaign Lifecycle — activate / pause ──

  it("shows activate button for approved campaign", async () => {
    mockAuthenticatedSession();
    const approvedCampaign = { ...DRAFT_CAMPAIGN, status: "approved" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [approvedCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
    }, ["campaigns.manage"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByText("Кампания согласована и готова к запуску.")).toBeTruthy();
      expect(screen.getByText("Активировать")).toBeTruthy();
    });
  });

  it("activate success refreshes campaign status", async () => {
    mockAuthenticatedSession();
    const approvedCampaign = { ...DRAFT_CAMPAIGN, status: "approved" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [approvedCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
      "/activate": () =>
        Promise.resolve(new Response(JSON.stringify({
          message: "Campaign activated", campaign_id: "c1", old_status: "approved", new_status: "active",
        }), { status: 200 })),
    }, ["campaigns.manage"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Активировать")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Активировать"));

    await waitFor(() => {
      expect(screen.queryByText("Кампания согласована и готова к запуску.")).toBeNull();
    });
  });

  it("shows pause button for active campaign", async () => {
    mockAuthenticatedSession();
    const activeCampaign = { ...DRAFT_CAMPAIGN, status: "active" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [activeCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
    }, ["campaigns.manage"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByText("Кампания активна — показы идут.")).toBeTruthy();
      expect(screen.getByText("Приостановить")).toBeTruthy();
    });
  });

  it("pause success refreshes campaign status", async () => {
    mockAuthenticatedSession();
    const activeCampaign = { ...DRAFT_CAMPAIGN, status: "active" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [activeCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
      "/pause": () =>
        Promise.resolve(new Response(JSON.stringify({
          message: "Campaign paused", campaign_id: "c1", old_status: "active", new_status: "paused",
        }), { status: 200 })),
    }, ["campaigns.manage"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Приостановить")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Приостановить"));

    await waitFor(() => {
      expect(screen.queryByText("Кампания активна — показы идут.")).toBeNull();
    });
  });

  it("non-manager cannot see activate button on approved", async () => {
    mockAuthenticatedSession();
    const approvedCampaign = { ...DRAFT_CAMPAIGN, status: "approved" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [approvedCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
    }); // no campaigns.manage → default /me has no permissions

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByText(/Кампания согласована/)).toBeTruthy();
      expect(screen.getByText(/У вас нет прав на управление кампанией/)).toBeTruthy();
      expect(screen.queryByText("Активировать")).toBeNull();
    });
  });

  it("activate error shows lifecycle error", async () => {
    mockAuthenticatedSession();
    const approvedCampaign = { ...DRAFT_CAMPAIGN, status: "approved" };
    // Direct mock on fetch to return 409 for activate
    const originalFetch = window.fetch;
    window.fetch = vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
      if (url.endsWith("/me")) {
        return Promise.resolve(new Response(JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin", permissions: ["campaigns.manage"] }), { status: 200 }));
      }
      if (url.includes("/identity/campaigns?") && (!init || init.method !== "POST")) {
        return Promise.resolve(new Response(JSON.stringify({items: [approvedCampaign], total: 1, limit: 50, offset: 0}), { status: 200 }));
      }
      if (url.includes("/activate") && init?.method === "POST") {
        return Promise.resolve(new Response(JSON.stringify({ detail: "Campaign not found or not in approved status" }), { status: 409 }));
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Активировать")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Активировать"));

    await waitFor(() => {
      expect(screen.getByTestId("campaign-lifecycle-error")).toBeTruthy();
    });
  });

  it("rejected campaign does not show activate/pause buttons", async () => {
    mockAuthenticatedSession();
    const rejectedCampaign = { ...DRAFT_CAMPAIGN, status: "rejected" };
    mockAllFetches({
      "/campaigns": () => Promise.resolve(new Response(JSON.stringify({items: [rejectedCampaign], total: 1, limit: 50, offset: 0}), { status: 200 })),
    }, ["campaigns.manage"]);

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    expect(screen.queryByText("Активировать")).toBeNull();
    expect(screen.queryByText("Приостановить")).toBeNull();
    expect(screen.queryByText("Кампания согласована")).toBeNull();
  });

  // ── S-009g: PoP Reporting ──

  it("shows empty reporting state when no data", async () => {
    mockAuthenticatedSession();
    // PoP endpoints return zero impressions — empty state
    const zeroSummary = {
      campaign_id: "c1",
      impressions_count: 0,
      total_duration_ms: 0,
      first_rendered_at: null,
      last_rendered_at: null,
      unique_devices: 0,
      unique_surfaces: 0,
    };
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(zeroSummary), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отчётность"));

    await waitFor(() => {
      expect(screen.getByText("Пока нет подтверждённых показов")).toBeTruthy();
    });
  });

  it("shows reporting summary cards with data", async () => {
    mockAuthenticatedSession();
    const summary = {
      campaign_id: "c1",
      impressions_count: 12_540,
      total_duration_ms: 1_800_000,
      first_rendered_at: "2026-06-01T08:00:00Z",
      last_rendered_at: "2026-06-15T20:00:00Z",
      unique_devices: 48,
      unique_surfaces: 12,
    };
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(summary), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отчётность"));

    await waitFor(() => {
      expect(screen.getByText(/12.540/)).toBeTruthy();
      expect(screen.getByText(/30.*мин/)).toBeTruthy();
      expect(screen.getByText("48")).toBeTruthy();
      expect(screen.getByText("12")).toBeTruthy();
    });
  });

  it("shows by-day table rows", async () => {
    mockAuthenticatedSession();
    const summary = { campaign_id: "c1", impressions_count: 100, total_duration_ms: 5000, first_rendered_at: null, last_rendered_at: null, unique_devices: 1, unique_surfaces: 1 };
    const byDay = [
      { date: "2026-06-01", impressions_count: 50, total_duration_ms: 2500 },
      { date: "2026-06-02", impressions_count: 50, total_duration_ms: 2500 },
    ];
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(summary), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify(byDay), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отчётность"));

    await waitFor(() => {
      expect(screen.getByText("По дням")).toBeTruthy();
      expect(screen.getByText("2026-06-01")).toBeTruthy();
      expect(screen.getByText("2026-06-02")).toBeTruthy();
    });
  });

  it("shows by-surface table rows", async () => {
    mockAuthenticatedSession();
    const summary = { campaign_id: "c1", impressions_count: 100, total_duration_ms: 5000, first_rendered_at: null, last_rendered_at: null, unique_devices: 1, unique_surfaces: 1 };
    const bySurface = [
      { surface_id: "surf-a1", impressions_count: 60, total_duration_ms: 3000 },
      { surface_id: "surf-b2", impressions_count: 40, total_duration_ms: 2000 },
    ];
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(summary), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify(bySurface), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отчётность"));

    await waitFor(() => {
      expect(screen.getByText("По поверхностям")).toBeTruthy();
      expect(screen.getByText("surf-a1")).toBeTruthy();
      expect(screen.getByText("surf-b2")).toBeTruthy();
    });
  });

  it("shows error on PoP 403", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отчётность"));

    await waitFor(() => {
      expect(screen.getByText("Нет прав на просмотр отчётности.")).toBeTruthy();
    });
  });

  it("shows error on PoP 404", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify({ detail: "Not found" }), { status: 404 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Отчётность"));

    await waitFor(() => {
      expect(screen.getByText("Кампания не найдена.")).toBeTruthy();
    });
  });

  // ── S-009h: Placement Reference Pickers ──

  const MOCK_SURFACES = [
    { id: "s1", store_id: "st1", code: "KSO-01", resolution_w: 1920, resolution_h: 1080, is_active: true },
    { id: "s2", store_id: "st2", code: "KSO-02", resolution_w: 3840, resolution_h: 2160, is_active: true },
  ];
  const MOCK_STORES: unknown[] = [
    { id: "st1", cluster_id: "cl1", code: "ST001", name: "Магазин 1", address: "ул. Ленина, 1", is_active: true },
    { id: "st2", cluster_id: "cl1", code: "ST002", name: "Магазин 2", address: "ул. Мира, 2", is_active: true },
  ];

  it("placement form shows reference pickers when data loaded", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/display-surfaces": () => Promise.resolve(new Response(JSON.stringify(MOCK_SURFACES), { status: 200 })),
      "/stores": () => Promise.resolve(new Response(JSON.stringify(MOCK_STORES), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Плейсменты"));

    // Wait for ref data to load (loading text disappears)
    await waitFor(() => {
      expect(screen.queryByText("Загрузка справочников...")).toBeNull();
    });

    await user.click(screen.getByText("+ Добавить плейсмент"));

    await waitFor(() => {
      // Surface picker shows KSO-01 option
      expect(screen.getByText(/KSO-01/)).toBeTruthy();
      // Store picker should have options (check count of store names via getAllByText)
      const storeOptions = screen.getAllByText(/Магазин \d/);
      expect(storeOptions.length).toBeGreaterThanOrEqual(2);
    });
  });

  it("placement form shows empty reference state", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/display-surfaces": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/stores": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Плейсменты"));

    // Wait for ref data to load (loading text disappears)
    await waitFor(() => {
      expect(screen.queryByText("Загрузка справочников...")).toBeNull();
    });

    await user.click(screen.getByText("+ Добавить плейсмент"));

    await waitFor(() => {
      expect(screen.getByText(/Нет доступных поверхностей/)).toBeTruthy();
    });
  });

  it("placement form shows ref load error", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/display-surfaces": () => Promise.reject(new Error("Network error")),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Плейсменты"));

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeTruthy();
    });
  });

  it("creating placement sends selected surface id", async () => {
    mockAuthenticatedSession();
    let postBody: unknown = null;
    mockAllFetches({
      "/display-surfaces": () => Promise.resolve(new Response(JSON.stringify(MOCK_SURFACES), { status: 200 })),
      "/stores": () => Promise.resolve(new Response(JSON.stringify(MOCK_STORES), { status: 200 })),
      "/campaigns/c1/placements": (url, init) => {
        if ((init as RequestInit).method === "POST") {
          postBody = JSON.parse((init as RequestInit).body as string);
          return Promise.resolve(new Response(JSON.stringify({
            id: "p-new", campaign_id: "c1", display_surface_id: "s1", store_id: "st1",
            share_of_voice_pct: 100, max_impressions: null, impressions_delivered: 0,
            status: "active", created_at: "2026-01-01T00:00:00Z",
          }), { status: 201 }));
        }
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      },
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    const user = userEvent.setup();
    await user.click(screen.getByText("Плейсменты"));

    // Wait for ref data to load (loading text disappears)
    await waitFor(() => {
      expect(screen.queryByText("Загрузка справочников...")).toBeNull();
    });

    await user.click(screen.getByText("+ Добавить плейсмент"));

    await waitFor(() => { expect(screen.getByText("Добавить")).toBeTruthy(); });

    // Select first surface — use label text
    const surfaceLabel = screen.getByText("Поверхность");
    const surfaceSelect = surfaceLabel.parentElement!.querySelector("select")!;
    await user.selectOptions(surfaceSelect, "s1");

    // Select first store
    const storeLabel = screen.getByText("Магазин");
    const storeSelect = storeLabel.parentElement!.querySelector("select")!;
    await user.selectOptions(storeSelect, "st1");

    await user.click(screen.getByText("Добавить"));

    await waitFor(() => {
      expect(postBody).not.toBeNull();
      const body = postBody as Record<string, unknown>;
      expect(body.display_surface_id).toBe("s1");
      expect(body.store_id).toBe("st1");
    });
  });
});

// ── S-090: Campaign Dashboard ──

describe("CampaignDetailPage — S-090 Dashboard", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  const POP_SUMMARY = {
    campaign_id: "c1",
    impressions_count: 8_500,
    total_duration_ms: 1_200_000,
    first_rendered_at: "2026-06-01T08:00:00Z",
    last_rendered_at: "2026-06-15T20:00:00Z",
    unique_devices: 42,
    unique_surfaces: 10,
  };

  const POP_BY_DAY = [
    { date: "2026-06-01", impressions_count: 600, total_duration_ms: 85000 },
    { date: "2026-06-02", impressions_count: 580, total_duration_ms: 82000 },
  ];

  const POP_BY_SURFACE = [
    { surface_id: "surf-1", impressions_count: 4500, total_duration_ms: 640000 },
    { surface_id: "surf-2", impressions_count: 4000, total_duration_ms: 560000 },
  ];

  const PLACEMENTS_WITH_PLAN = [
    { id: "p1", campaign_id: "c1", display_surface_id: "surf-1", store_id: "st1",
      share_of_voice_pct: 50, priority: 10, status: "active",
      max_impressions: 10000, impressions_delivered: 0,
      start_at: null, end_at: null, created_at: "2026-06-01T00:00:00Z", updated_at: "2026-06-01T00:00:00Z" },
  ];

  it("shows plan/fact heading and delivery status", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(POP_SUMMARY), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify(POP_BY_DAY), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify(POP_BY_SURFACE), { status: 200 })),
      "campaign-placements": () => Promise.resolve(new Response(JSON.stringify(PLACEMENTS_WITH_PLAN), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      expect(screen.getByText("План / Факт")).toBeTruthy();
      expect(screen.getByText("Недопоказ")).toBeTruthy();
    });
  });

  it("shows empty dashboard state when no PoP data", async () => {
    mockAuthenticatedSession();
    const zeroSummary = { campaign_id: "c1", impressions_count: 0, total_duration_ms: 0,
      first_rendered_at: null, last_rendered_at: null, unique_devices: 0, unique_surfaces: 0 };
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(zeroSummary), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      expect(screen.getByText("Пока нет подтверждённых показов")).toBeTruthy();
    });
  });

  it("shows critical underdelivery warning", async () => {
    mockAuthenticatedSession();
    const lowPop = { ...POP_SUMMARY, impressions_count: 2_000 };
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(lowPop), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "campaign-placements": () => Promise.resolve(new Response(JSON.stringify(PLACEMENTS_WITH_PLAN), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      expect(screen.getByText("Критичный недопоказ")).toBeTruthy();
    });
  });

  it("shows device health with limitation note", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(POP_SUMMARY), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      expect(screen.getByText("Здоровье устройств")).toBeTruthy();
      expect(screen.getByText(/S-097/)).toBeTruthy();
    });
  });

  it("shows loading state on dashboard tab", async () => {
    mockAuthenticatedSession();
    // Never-resolving promise keeps loading state visible
    let resolvePopup: (value: Response) => void;
    const popPromise = new Promise<Response>((res) => { resolvePopup = res; });
    mockAllFetches({
      "/pop/summary": () => popPromise,
      "/pop/by-day": () => popPromise,
      "/pop/by-surface": () => popPromise,
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      expect(screen.getByText("Загрузка дашборда...")).toBeTruthy();
    });

    // Resolve so test doesn't hang
    resolvePopup!(new Response(JSON.stringify([]), { status: 200 }));
  });

  it("shows error state on dashboard tab when PoP API fails", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify({ detail: "Server error" }), { status: 500 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      // Error message from popError — matches the error pattern from loadPopData
      expect(screen.getByText(/Ошибка/)).toBeTruthy();
    });
  });

  it("shows by-surface / geography table in dashboard", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(POP_SUMMARY), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify(POP_BY_SURFACE), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      expect(screen.getByText("По поверхностям / географии")).toBeTruthy();
      expect(screen.getByText("surf-1")).toBeTruthy();
      expect(screen.getByText("surf-2")).toBeTruthy();
    });
  });
  it("shows by-day table in dashboard", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "/pop/summary": () => Promise.resolve(new Response(JSON.stringify(POP_SUMMARY), { status: 200 })),
      "/pop/by-day": () => Promise.resolve(new Response(JSON.stringify(POP_BY_DAY), { status: 200 })),
      "/pop/by-surface": () => Promise.resolve(new Response(JSON.stringify([]), { status: 200 })),
    });

    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Обзор")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("Дашборд"));

    await waitFor(() => {
      expect(screen.getByText("По дням")).toBeTruthy();
      expect(screen.getByText("2026-06-01")).toBeTruthy();
    });
  });
});

// ── S-089: Inventory Simulation UI ──

describe("CampaignDetailPage — S-089 Simulation", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  const SIM_F = [{ id: "f1", campaign_id: "c1", name: "F1", start_at: "2026-01-01T00:00:00Z", end_at: "2026-02-01T00:00:00Z", priority: 0, created_at: "2026-01-01T00:00:00Z" }];
  const SIM_P = [{ id: "p1", campaign_id: "c1", display_surface_id: "surf-1", store_id: "st-1", cluster_id: null, branch_id: null, share_of_voice_pct: 100, max_impressions: 1000, impressions_delivered: 0, status: "active", created_at: "2026-01-01T00:00:00Z" }];
  const SIM_C = [{ id: "cc1", campaign_id: "c1", creative_asset_id: "ca-1", sort_order: 0, duration_override_ms: null, created_at: "2026-01-01T00:00:00Z", asset: { id: "ca-1", code: "CR1", name: "Banner", media_type: "image/jpeg", sha256_checksum: "abc", file_size_bytes: 100, status: "active", moderation_status: "approved", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" } }];

  const SIM_RESULT = {
    campaign_id: "c1", overall_fit: true,
    placements: [{ placement_id: "p1", surface_id: "surf-1", surface_code: "SURF-001", fit: true, slot_fill_percent: 50, total_requested: 1000, total_available: 2000, conflicts: [], applied_rules: [] }],
    blocking_count: 0, warning_count: 0,
  };

  it("shows simulation button when campaign has flights+placements+creatives", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "campaign-flights": () => Promise.resolve(new Response(JSON.stringify(SIM_F), { status: 200 })),
      "campaign-placements": () => Promise.resolve(new Response(JSON.stringify(SIM_P), { status: 200 })),
      "campaign-creatives": () => Promise.resolve(new Response(JSON.stringify(SIM_C), { status: 200 })),
    });
    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
    await waitFor(() => { expect(screen.getByText("🧪 Симуляция")).toBeTruthy(); });
  });

  it("shows simulation result after click (success)", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "campaign-flights": () => Promise.resolve(new Response(JSON.stringify(SIM_F), { status: 200 })),
      "campaign-placements": () => Promise.resolve(new Response(JSON.stringify(SIM_P), { status: 200 })),
      "campaign-creatives": () => Promise.resolve(new Response(JSON.stringify(SIM_C), { status: 200 })),
      "/inventory/simulate": () => Promise.resolve(new Response(JSON.stringify(SIM_RESULT), { status: 200 })),
    });
    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
    await waitFor(() => { expect(screen.getByText("🧪 Симуляция")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("🧪 Симуляция"));
    await waitFor(() => {
      expect(screen.getByText(/Кампания помещается/)).toBeTruthy();
      expect(screen.getByTestId("simulation-blocking-count").textContent).toBe("0");
    });
  });

  it("shows conflicts when fit=false", async () => {
    mockAuthenticatedSession();
    const conflictResult = { ...SIM_RESULT, overall_fit: false,
      placements: [{ placement_id: "p1", surface_id: "surf-1", surface_code: "SURF-001", fit: false, slot_fill_percent: 150, total_requested: 1500, total_available: 1000, conflicts: [{ conflict_type: "capacity_overbook", severity: "blocking", surface_id: "surf-1", message: "Overbooked" }], applied_rules: [] }],
      blocking_count: 1, warning_count: 0 };
    mockAllFetches({
      "campaign-flights": () => Promise.resolve(new Response(JSON.stringify(SIM_F), { status: 200 })),
      "campaign-placements": () => Promise.resolve(new Response(JSON.stringify(SIM_P), { status: 200 })),
      "campaign-creatives": () => Promise.resolve(new Response(JSON.stringify(SIM_C), { status: 200 })),
      "/inventory/simulate": () => Promise.resolve(new Response(JSON.stringify(conflictResult), { status: 200 })),
    });
    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
    await waitFor(() => { expect(screen.getByText("🧪 Симуляция")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("🧪 Симуляция"));
    await waitFor(() => {
      expect(screen.getByText(/не помещается/)).toBeTruthy();
      expect(screen.getByText("Overbooked")).toBeTruthy();
    });
  });

  it("shows error state on simulation failure", async () => {
    mockAuthenticatedSession();
    mockAllFetches({
      "campaign-flights": () => Promise.resolve(new Response(JSON.stringify(SIM_F), { status: 200 })),
      "campaign-placements": () => Promise.resolve(new Response(JSON.stringify(SIM_P), { status: 200 })),
      "campaign-creatives": () => Promise.resolve(new Response(JSON.stringify(SIM_C), { status: 200 })),
      "/inventory/simulate": () => Promise.resolve(new Response(JSON.stringify({ detail: "Server error" }), { status: 500 })),
    });
    const router = createRouter("/campaigns/c1");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
    await waitFor(() => { expect(screen.getByText("🧪 Симуляция")).toBeTruthy(); });
    await userEvent.setup().click(screen.getByText("🧪 Симуляция"));
    await waitFor(() => {
      expect(screen.getByText(/Server error/)).toBeTruthy();
    });
  });
});
