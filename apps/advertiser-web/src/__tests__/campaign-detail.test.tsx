import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import CampaignDetailPage from "../pages/CampaignDetailPage";

const mockGet = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    login: vi.fn(), logout: vi.fn().mockResolvedValue(undefined),
    getMe: vi.fn().mockResolvedValue({ sub: "u1", auth_provider: "local_advertiser", username: "a", display_name: "A" }),
    post: vi.fn(), patch: vi.fn(), del: vi.fn(), refresh: vi.fn(),
  },
  setToken: vi.fn(), onUnauthorized: vi.fn(),
  ApiError: class extends Error { status: number; constructor(s: number) { super(`HTTP ${s}`); this.status = s; } },
}));

let makeApiError: (s: number) => Error & { status: number };
beforeAll(async () => {
  const AE = (await import("../api/client")).ApiError as any;
  makeApiError = (s) => new AE(s);
});

const camp = { id: "c1", advertiser_organization_id: "o1", advertiser_brand_id: null, advertiser_contract_id: "c1", code: "C-001", name: "Тестовая кампания", description: "Описание", status: "active", priority: 1, budget_limit_amount: 50000, budget_limit_currency: "RUB", start_at: "2025-01-01T00:00:00Z", end_at: "2025-06-01T00:00:00Z", timezone: "UTC", created_by: null, created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z" };

const flight = { id: "f1", campaign_id: "c1", name: "Январь", start_at: "2025-01-01T00:00:00Z", end_at: "2025-01-31T23:59:59Z", dayparting_json: null, days_of_week: null, priority: 1, created_at: "2025-01-01T00:00:00Z" };
const placement = { id: "p1", campaign_id: "c1", display_surface_id: "s-01", store_id: null, cluster_id: null, branch_id: null, share_of_voice_pct: 50, max_impressions: null, impressions_delivered: 500, status: "active", created_at: "2025-01-01T00:00:00Z" };
const ccLink = { id: "cc1", campaign_id: "c1", creative_asset_id: "ca1", sort_order: 1, duration_override_ms: null, created_at: "2025-01-01T00:00:00Z" };
const asset = { id: "ca1", advertiser_organization_id: "o1", code: "CR-1", name: "Баннер", media_type: "image/png", sha256_checksum: "abc", file_size_bytes: 1000, duration_ms: null, resolution_w: 100, resolution_h: 100, status: "ready", moderation_status: "approved", created_at: "2025-01-01T00:00:00Z", updated_at: "2025-01-01T00:00:00Z" };
const approval = { id: "a1", campaign_id: "c1", requested_by: "u1", requested_at: "2025-01-01T00:00:00Z", reviewed_by: "u2", reviewed_at: "2025-01-02T00:00:00Z", decision: "approved", rejection_reason: null, created_at: "2025-01-01T00:00:00Z" };

const popSummary = { campaign_id: "c1", impressions_count: 1500, total_duration_ms: 45000, first_rendered_at: "2025-01-01T08:00:00Z", last_rendered_at: "2025-01-05T20:00:00Z", unique_devices: 3, unique_surfaces: 2 };
const popByDay = [
  { date: "2025-01-01", impressions_count: 300, total_duration_ms: 9000 },
  { date: "2025-01-02", impressions_count: 500, total_duration_ms: 15000 },
];
const popBySurface = [
  { surface_id: "surface-01", impressions_count: 900, total_duration_ms: 27000 },
  { surface_id: "surface-02", impressions_count: 600, total_duration_ms: 18000 },
];

function setupFull() {
  mockGet.mockImplementation((path: string) => {
    const m: Record<string, unknown> = {
      "/campaigns": [camp], "/campaign-flights": [flight],
      "/campaign-placements": [placement], "/campaign-creatives": [ccLink],
      "/creative-assets": [asset], "/campaign-approvals": [approval],
      "/campaign-status-history": [],
      "/campaigns/c1/pop/summary": popSummary,
      "/campaigns/c1/pop/by-day": popByDay,
      "/campaigns/c1/pop/by-surface": popBySurface,
    };
    return m[path] ? Promise.resolve(m[path]) : Promise.resolve([]);
  });
}

function renderPage() {
  localStorage.setItem("rmp_access_token", "t");
  localStorage.setItem("rmp_auth_provider", "local_advertiser");
  const router = createMemoryRouter(
    [{ path: "/campaigns/:id", element: <AuthProvider><CampaignDetailPage /></AuthProvider> }],
    { initialEntries: ["/campaigns/c1"] },
  );
  return render(<RouterProvider router={router} />);
}

describe("CampaignDetailPage", () => {
  beforeEach(() => { localStorage.clear(); vi.clearAllMocks(); });
  afterEach(() => localStorage.clear());

  it("renders without crashing", () => {
    setupFull();
    const { container } = renderPage();
    expect(container).toBeTruthy();
  });

  it("calls all required API endpoints", async () => {
    setupFull();
    renderPage();
    await waitFor(() => {
      expect(mockGet.mock.calls.length).toBeGreaterThanOrEqual(7);
    }, { timeout: 3000 });
    const paths = mockGet.mock.calls.map(c => c[0]);
    expect(paths).toContain("/campaigns");
    expect(paths).toContain("/campaign-flights");
    expect(paths).toContain("/campaign-placements");
    expect(paths).toContain("/campaign-creatives");
    expect(paths).toContain("/creative-assets");
    expect(paths).toContain("/campaign-approvals");
    expect(paths).toContain("/campaign-status-history");
  });

  it("shows inaccessible message on 403", async () => {
    mockGet.mockRejectedValue(makeApiError(403));
    renderPage();
    await screen.findByText("Кампания не найдена или недоступна", {}, { timeout: 3000 });
    expect(screen.queryByText(/approve|reject/i)).toBeNull();
  });

  it("clears session on 401", async () => {
    mockGet.mockRejectedValue(makeApiError(401));
    renderPage();
    await waitFor(() => {
      expect(localStorage.getItem("rmp_access_token")).toBeNull();
    }, { timeout: 3000 });
  });

  it("has no storage fields in 403 state", async () => {
    mockGet.mockRejectedValue(makeApiError(403));
    renderPage();
    await screen.findByText("Кампания не найдена или недоступна", {}, { timeout: 3000 });
    expect(document.body.textContent).not.toMatch(/storage_bucket|storage_key|presigned_url/i);
  });

  // ── PoP Reporting tests ──

  it("shows PoP summary cards", async () => {
    setupFull();
    renderPage();
    await screen.findByText("Отчётность", {}, { timeout: 3000 });
    // Wait for summary data — "1 500" formatted with locale
    await waitFor(() => {
      expect(document.body.textContent).toMatch(/1.?500/);
    }, { timeout: 3000 });
  });

  it("shows PoP by-day table", async () => {
    setupFull();
    renderPage();
    await screen.findByText("По дням", {}, { timeout: 3000 });
  });

  it("shows PoP by-surface table", async () => {
    setupFull();
    renderPage();
    await screen.findByText("По поверхностям", {}, { timeout: 3000 });
    expect(screen.getByText("surface-01")).toBeInTheDocument();
  });

  it("shows empty state when no PoP data", async () => {
    mockGet.mockImplementation((path: string) => {
      const m: Record<string, unknown> = {
        "/campaigns": [camp], "/campaign-flights": [],
        "/campaign-placements": [], "/campaign-creatives": [],
        "/creative-assets": [], "/campaign-approvals": [],
        "/campaign-status-history": [],
        "/campaigns/c1/pop/summary": { ...popSummary, impressions_count: 0 },
        "/campaigns/c1/pop/by-day": [],
        "/campaigns/c1/pop/by-surface": [],
      };
      return m[path] ? Promise.resolve(m[path]) : Promise.resolve([]);
    });
    renderPage();
    await screen.findByText("Пока нет подтверждённых показов", {}, { timeout: 3000 });
  });

  it("has no sales lift/attribution wording", async () => {
    setupFull();
    renderPage();
    // Wait for PoP section to load fully
    await screen.findByText("По дням", {}, { timeout: 3000 });
    const body = document.body.textContent ?? "";
    expect(body).not.toMatch(/sales.lift|роста продаж|воронк/i);
    expect(body).toMatch(/не является отчётом по продажам/i); // disclaimer IS present
  });

  it("no storage fields in PoP section", async () => {
    setupFull();
    renderPage();
    await screen.findByText("По дням", {}, { timeout: 3000 });
    expect(document.body.textContent).not.toMatch(/storage_bucket|storage_key|presigned_url/i);
  });
});

// ── Edit flow (draft-only) ──

describe("CampaignDetailPage — edit", () => {
  const draftCamp = { ...camp, status: "draft" };
  const activeCamp = { ...camp, status: "active" };

  it("draft campaign shows edit button", async () => {
    mockGet.mockImplementation((path: string) => {
      const m: Record<string, unknown> = {
        "/campaigns": [draftCamp], "/campaign-flights": [],
        "/campaign-placements": [], "/campaign-creatives": [],
        "/creative-assets": [], "/campaign-approvals": [],
        "/campaign-status-history": [],
        [`/campaigns/${camp.id}/pop/summary`]: { campaign_id: "c1", impressions_count: 0, total_duration_ms: 0, first_rendered_at: null, last_rendered_at: null, unique_devices: 0, unique_surfaces: 0 },
        [`/campaigns/${camp.id}/pop/by-day`]: [], [`/campaigns/${camp.id}/pop/by-surface`]: [],
      };
      return Promise.resolve(m[path] ?? []);
    });
    renderPage();
    await waitFor(() => screen.getByText("Редактировать"));
    expect(screen.getByText("Редактировать")).toBeInTheDocument();
  });

  it("non-draft campaign does not show edit button", async () => {
    mockGet.mockImplementation((path: string) => {
      const m: Record<string, unknown> = {
        "/campaigns": [activeCamp], "/campaign-flights": [],
        "/campaign-placements": [], "/campaign-creatives": [],
        "/creative-assets": [], "/campaign-approvals": [],
        "/campaign-status-history": [],
        [`/campaigns/${camp.id}/pop/summary`]: { campaign_id: "c1", impressions_count: 0, total_duration_ms: 0, first_rendered_at: null, last_rendered_at: null, unique_devices: 0, unique_surfaces: 0 },
        [`/campaigns/${camp.id}/pop/by-day`]: [], [`/campaigns/${camp.id}/pop/by-surface`]: [],
      };
      return Promise.resolve(m[path] ?? []);
    });
    renderPage();
    // Wait for page to load — campaign name appears in the header
    await waitFor(() => expect(screen.getByRole("heading", { name: "Тестовая кампания" })).toBeInTheDocument());
    expect(screen.queryByText("Редактировать")).toBeNull();
  });
});
