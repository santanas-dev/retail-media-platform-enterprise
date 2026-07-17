import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import BriefDetailPage from "../pages/BriefDetailPage";

const { mockGet, mockRefresh, mockGetMe, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockRefresh: vi.fn(),
  mockGetMe: vi.fn(),
  mockPost: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    login: vi.fn(),
    logout: vi.fn().mockResolvedValue(undefined),
    getMe: (...args: unknown[]) => mockGetMe(...args),
    post: (...args: unknown[]) => mockPost(...args),
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

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...(actual as object),
    useParams: () => ({ id: "brief-001" }),
  };
});

const briefData: Record<string, unknown> = {
  id: "brief-001",
  advertiser_organization_id: "org-a",
  title: "Продвижение молока",
  objective: "Повысить продажи",
  product_category: "Молочная продукция",
  target_period_from: "2026-08-01",
  target_period_to: "2026-09-30",
  budget_amount: 150000,
  budget_currency: "RUB",
  preferred_channels: "LED-экраны",
  comment: "Пилот",
  status: "draft",
  created_by: "u1",
  created_at: "2026-07-17T10:00:00Z",
  updated_at: "2026-07-17T10:00:00Z",
};

function setupMocks(meData: Record<string, unknown>) {
  mockRefresh.mockResolvedValue({ access_token: "at", token_type: "Bearer", expires_in: 1800 });
  mockGetMe.mockResolvedValue(meData);
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/briefs/brief-001"]}>
      <AuthProvider>
        <BriefDetailPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("BriefDetailPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows brief detail", async () => {
    setupMocks({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "ivan@test.ru",
      display_name: "Иван",
      permissions: ["campaigns.read"],
      advertiser_organization_id: "org-a",
      advertiser_organization: null,
    });
    mockGet.mockResolvedValue(briefData);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Продвижение молока")).toBeTruthy();
    });
    expect(screen.getByText("Повысить продажи")).toBeTruthy();
    expect(screen.getByText("Молочная продукция")).toBeTruthy();
    const rubText = screen.getByText((content) => content.includes("150") && content.includes("RUB"));
    expect(rubText).toBeTruthy();
    expect(screen.getByText("Черновик")).toBeTruthy();
  });

  it("shows submit button for draft", async () => {
    setupMocks({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "ivan@test.ru",
      display_name: "Иван",
      permissions: ["campaigns.read", "campaigns.manage"],
      advertiser_organization_id: "org-a",
      advertiser_organization: null,
    });
    mockGet.mockResolvedValue(briefData);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Отправить на рассмотрение")).toBeTruthy();
    });
    expect(screen.getByText("Редактировать")).toBeTruthy();
  });

  it("shows readonly message for submitted brief", async () => {
    setupMocks({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "ivan@test.ru",
      display_name: "Иван",
      permissions: ["campaigns.read"],
      advertiser_organization_id: "org-a",
      advertiser_organization: null,
    });
    mockGet.mockResolvedValue({ ...briefData, status: "submitted" });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("На рассмотрении")).toBeTruthy();
    });
    expect(screen.getByText(/Заявка отправлена на рассмотрение/)).toBeTruthy();
  });
});
