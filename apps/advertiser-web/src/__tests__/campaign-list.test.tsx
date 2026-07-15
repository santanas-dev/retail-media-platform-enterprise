import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import CampaignListPage from "../pages/CampaignListPage";

// Mock the api client
const { mockGet, mockRefresh, mockGetMe } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockRefresh: vi.fn(),
  mockGetMe: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    getMe: (...args: unknown[]) => mockGetMe(...args),
    post: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
    refresh: (...args: unknown[]) => mockRefresh(...args),
  },
  setToken: vi.fn(),
  onUnauthorized: vi.fn(),
  ApiError: class extends Error {
    status: number;
    constructor(status: number, body?: unknown) {
      super(
        typeof body === "object" && body !== null && "detail" in body
          ? String((body as Record<string, unknown>).detail)
          : `HTTP ${status}`,
      );
      this.name = "ApiError";
      this.status = status;
    }
  },
}));

// Dynamic import to get the mocked ApiError (vi.mock hoists, import resolves to mock)
let _ApiError: typeof Error & { new (status: number, body?: unknown): Error & { status: number } };
beforeAll(async () => {
  const mod = await import("../api/client");
  _ApiError = mod.ApiError as any;
});

function makeApiError(status: number): Error & { status: number } {
  return new _ApiError(status) as Error & { status: number };
}

function renderCampaignList() {
  // S-035b: Session restore via api.refresh() — no localStorage
  mockRefresh.mockResolvedValue({ access_token: "refreshed-at", token_type: "Bearer", expires_in: 1800 });
  mockGetMe.mockResolvedValue({
    sub: "u1",
    auth_provider: "local_advertiser",
    username: "advertiser1",
    display_name: "Рекламодатель 1",
  });

  return render(
    <MemoryRouter>
      <AuthProvider>
        <CampaignListPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

const mockCampaigns = [
  {
    id: "c1",
    advertiser_organization_id: "org1",
    advertiser_brand_id: null,
    advertiser_contract_id: "contract1",
    code: "CAMP-001",
    name: "Новогодняя акция",
    description: null,
    status: "active",
    priority: 1,
    budget_limit_amount: 100000,
    budget_limit_currency: "RUB",
    start_at: "2025-12-01T00:00:00Z",
    end_at: "2026-01-15T00:00:00Z",
    timezone: "Europe/Moscow",
    created_by: null,
    created_at: "2025-11-01T10:00:00Z",
    updated_at: "2025-12-10T14:30:00Z",
  },
  {
    id: "c2",
    advertiser_organization_id: "org1",
    advertiser_brand_id: "brand1",
    advertiser_contract_id: "contract1",
    code: "CAMP-002",
    name: "Летняя распродажа",
    description: "Летняя кампания",
    status: "draft",
    priority: 2,
    budget_limit_amount: null,
    budget_limit_currency: "RUB",
    start_at: null,
    end_at: null,
    timezone: "Europe/Moscow",
    created_by: null,
    created_at: "2025-04-01T08:00:00Z",
    updated_at: "2025-04-10T09:00:00Z",
  },
];

describe("Campaign list — data rendering", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders campaign rows from API response", async () => {
    mockGet.mockResolvedValue({items: mockCampaigns, total: 2, limit: 50, offset: 0});

    renderCampaignList();

    await waitFor(() => {
      expect(screen.getByText("Новогодняя акция")).toBeInTheDocument();
      expect(screen.getByText("Летняя распродажа")).toBeInTheDocument();
    });

    // Check codes are shown
    expect(screen.getByText("CAMP-001")).toBeInTheDocument();
    expect(screen.getByText("CAMP-002")).toBeInTheDocument();
  });

  it("empty state shown when no campaigns", async () => {
    mockGet.mockResolvedValue({items: [], total: 0, limit: 50, offset: 0});

    renderCampaignList();

    await waitFor(() => {
      expect(screen.getByText("Нет кампаний")).toBeInTheDocument();
    });
  });

  it("403 shows access error", async () => {
    mockGet.mockRejectedValue(makeApiError(403));

    renderCampaignList();

    await waitFor(() => {
      expect(
        screen.getByText("Нет прав на просмотр кампаний"),
      ).toBeInTheDocument();
    });
  });

  it("401 clears session", async () => {
    mockGet.mockRejectedValue(makeApiError(401));

    renderCampaignList();

    await waitFor(() => {
      // Session should be cleared
      expect(localStorage.getItem("rmp_access_token")).toBeNull();
    });
  });
});
