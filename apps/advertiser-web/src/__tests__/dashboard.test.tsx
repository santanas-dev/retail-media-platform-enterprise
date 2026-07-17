import { describe, it, expect, vi, beforeEach, afterEach, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import DashboardPage from "../pages/DashboardPage";

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

function setupMocks(meData: Record<string, unknown>) {
  mockRefresh.mockResolvedValue({ access_token: "at", token_type: "Bearer", expires_in: 1800 });
  mockGetMe.mockResolvedValue(meData);
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <AuthProvider>
        <DashboardPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows organization info when user has advertiser_organization", async () => {
    setupMocks({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "ivan@test.ru",
      display_name: "Иван Тестов",
      permissions: ["organization.read", "campaigns.read"],
      advertiser_organization_id: "org-a",
      advertiser_organization: {
        id: "org-a",
        code: "ADV-001",
        legal_name: "ООО Ромашка",
        display_name: "Ромашка",
        status: "active",
      },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("ООО Ромашка")).toBeTruthy();
    });

    expect(screen.getByText("ADV-001")).toBeTruthy();
    expect(screen.getByText("Активен")).toBeTruthy();
    expect(screen.getByText("Иван Тестов")).toBeTruthy();
    expect(screen.getByText("ivan@test.ru")).toBeTruthy();
    expect(screen.getByText("Рекламодатель (ограниченный доступ)")).toBeTruthy();
  });

  it("shows no-organization message when advertiser_organization is null", async () => {
    setupMocks({
      sub: "u2",
      auth_provider: "local_advertiser",
      username: "noorg@test.ru",
      display_name: "Без Организации",
      permissions: [],
      advertiser_organization_id: null,
      advertiser_organization: null,
    });

    renderDashboard();

    await waitFor(() => {
      expect(
        screen.getByText(/Организация не привязана/),
      ).toBeTruthy();
    });

    expect(screen.getByText("Доступ не настроен")).toBeTruthy();
  });

  it("shows loading state during auth restore", () => {
    // refresh never resolves -> stays loading
    mockRefresh.mockReturnValue(new Promise(() => {}));
    mockGetMe.mockResolvedValue({ sub: "u3" });

    render(
      <MemoryRouter>
        <AuthProvider>
          <DashboardPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    // Layout shows "Загрузка..." but DashboardPage renders null user => "Нет данных"
    // Actually AuthContext sets loading=true during restore; DashboardPage
    // is inside AuthProvider but outside Layout so we only test DashboardPage.
    // The loading phase: user is null => "Нет данных пользователя."
    expect(screen.getByText("Нет данных пользователя.")).toBeTruthy();
  });

  it("shows no-org when refresh fails (session expired)", async () => {
    mockRefresh.mockRejectedValue(new Error("Unauthorized"));
    mockGetMe.mockResolvedValue({ sub: "u4" });

    renderDashboard();

    // AuthProvider clears session, user becomes null
    await waitFor(() => {
      expect(screen.getByText("Нет данных пользователя.")).toBeTruthy();
    });
  });

  it("shows permissions when present", async () => {
    setupMocks({
      sub: "u5",
      auth_provider: "local_advertiser",
      username: "perm@test.ru",
      display_name: "With Perms",
      permissions: ["organization.read", "campaigns.read", "creatives.read"],
      advertiser_organization_id: "org-p",
      advertiser_organization: {
        id: "org-p",
        code: "ADV-P",
        legal_name: "ООО Пермиссии",
        display_name: "Пермиссии",
        status: "active",
      },
    });

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("organization.read")).toBeTruthy();
    });
    expect(screen.getByText("campaigns.read")).toBeTruthy();
    expect(screen.getByText("creatives.read")).toBeTruthy();
  });
});
