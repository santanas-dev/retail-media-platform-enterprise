import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import BriefListPage from "../pages/BriefListPage";

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

function setupMocks(meData: Record<string, unknown>) {
  mockRefresh.mockResolvedValue({ access_token: "at", token_type: "Bearer", expires_in: 1800 });
  mockGetMe.mockResolvedValue(meData);
}

function renderPage() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <BriefListPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("BriefListPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows empty state when no briefs", async () => {
    setupMocks({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "ivan@test.ru",
      display_name: "Иван",
      permissions: ["campaigns.read"],
      advertiser_organization_id: "org-a",
      advertiser_organization: {
        id: "org-a",
        code: "ADV-001",
        legal_name: "ООО Ромашка",
        display_name: "Ромашка",
        status: "active",
      },
    });
    mockGet.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Мои заявки")).toBeTruthy();
    });
    expect(screen.getByText(/У вас пока нет заявок/)).toBeTruthy();
    expect(screen.getByText("Создать заявку")).toBeTruthy();
  });

  it("shows list of briefs", async () => {
    setupMocks({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "ivan@test.ru",
      display_name: "Иван",
      permissions: ["campaigns.read"],
      advertiser_organization_id: "org-a",
      advertiser_organization: null,
    });
    mockGet.mockResolvedValue({
      items: [
        {
          id: "b1",
          advertiser_organization_id: "org-a",
          title: "Продвижение молока",
          objective: "Увеличить продажи",
          product_category: "Молочная продукция",
          target_period_from: "2026-08-01",
          target_period_to: "2026-09-30",
          budget_amount: 150000,
          budget_currency: "RUB",
          preferred_channels: null,
          comment: null,
          status: "draft",
          created_by: "u1",
          created_at: "2026-07-17T10:00:00Z",
          updated_at: "2026-07-17T10:00:00Z",
        },
        {
          id: "b2",
          advertiser_organization_id: "org-a",
          title: "Реклама сыров",
          objective: null,
          product_category: "Сыры",
          target_period_from: null,
          target_period_to: null,
          budget_amount: null,
          budget_currency: "RUB",
          preferred_channels: null,
          comment: null,
          status: "submitted",
          created_by: "u1",
          created_at: "2026-07-16T08:00:00Z",
          updated_at: "2026-07-17T09:00:00Z",
        },
      ],
      total: 2,
      limit: 50,
      offset: 0,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Продвижение молока")).toBeTruthy();
    });
    expect(screen.getByText("Реклама сыров")).toBeTruthy();
    expect(screen.getByText("Черновик")).toBeTruthy();
    expect(screen.getByText("На рассмотрении")).toBeTruthy();
  });

  it("shows loading state", () => {
    mockRefresh.mockReturnValue(new Promise(() => {}));
    mockGetMe.mockResolvedValue({ sub: "u3" });
    mockGet.mockReturnValue(new Promise(() => {}));

    const { container } = render(
      <MemoryRouter>
        <AuthProvider>
          <BriefListPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    expect(container.textContent).toContain("Загрузка...");
  });

  it("shows error on API failure", async () => {
    setupMocks({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "err@test.ru",
      display_name: "Err",
      permissions: ["campaigns.read"],
      advertiser_organization_id: "org-a",
      advertiser_organization: null,
    });
    mockGet.mockRejectedValue(new Error("Network error"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Не удалось загрузить заявки/)).toBeTruthy();
    });
  });
});
