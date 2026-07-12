import { describe, it, expect, vi, beforeEach, beforeAll } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import CampaignCreatePage from "../pages/CampaignCreatePage";

const mockGet = vi.fn();
const mockPost = vi.fn();
const mockGetMe = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
    getMe: (...args: unknown[]) => mockGetMe(...args),
    login: vi.fn(),
    logout: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
    refresh: vi.fn().mockResolvedValue({ access_token: "t", token_type: "Bearer", expires_in: 1800 }),
    changePassword: vi.fn(),
  },
  setToken: vi.fn(),
  onUnauthorized: vi.fn(),
  ApiError: class MockApiError extends Error {
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

let makeApiError: (status: number, msg?: string) => Error & { status: number };
beforeAll(async () => {
  const AE = (await import("../api/client")).ApiError as new (status: number, body?: unknown) => Error & { status: number };
  makeApiError = (status, msg) => new AE(status, { detail: msg || `HTTP ${status}` });
});

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...(actual as object),
    useNavigate: () => mockNavigate,
  };
});

function setup() {
  /* S-035b: session restore via refresh — no localStorage */

  mockGetMe.mockResolvedValue({
    sub: "u1",
    auth_provider: "local_advertiser",
    username: "advertiser1",
    display_name: "Рекламодатель 1",
    permissions: ["campaigns.manage", "campaigns.read"],
  });

  mockGet.mockImplementation((path: string) => {
    if (path === "/advertiser-organizations") {
      return Promise.resolve([
        { id: "ADV-001", code: "ADV-001", legal_name: "ООО «Тест»", display_name: "Тестовый", status: "active" },
      ]);
    }
    if (path === "/advertiser-brands") {
      return Promise.resolve([
        { id: "b1", advertiser_organization_id: "ADV-001", code: "BRAND-A", name: "Бренд А", status: "active" },
      ]);
    }
    if (path === "/advertiser-contracts") {
      return Promise.resolve([
        { id: "c1", code: "CONTRACT-1", name: "Договор №1", budget_limit_amount: 500000, budget_limit_currency: "RUB", valid_from: "2026-01-01", valid_until: null, status: "active", advertiser_organization_id: "ADV-001" },
      ]);
    }
    return Promise.resolve([]);
  });

  render(
    <MemoryRouter initialEntries={["/campaigns/new"]}>
      <AuthProvider>
        <CampaignCreatePage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("CampaignCreatePage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    mockGetMe.mockResolvedValue({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "advertiser1",
      display_name: "Рекламодатель 1",
      permissions: ["campaigns.manage", "campaigns.read"],
    });
  });

  it("loads and displays brand/contract options", async () => {
    setup();
    await waitFor(() => {
      expect(screen.getByText("Бренд А (BRAND-A)")).toBeInTheDocument();
      expect(screen.getByText(/CONTRACT-1/)).toBeInTheDocument();
    });
  });

  it("auto-generates code from name", async () => {
    setup();
    await waitFor(() => screen.getByPlaceholderText("Название кампании"));

    const nameInput = screen.getByPlaceholderText("Название кампании");
    await userEvent.setup().type(nameInput, "Моя первая кампания!");

    const codeInput = screen.getByPlaceholderText("Автоматически") as HTMLInputElement;
    expect(codeInput.value).toBe("МОЯ-ПЕРВАЯ-КАМПАНИЯ");
  });

  it("shows validation error when name is empty", async () => {
    setup();
    await waitFor(() => screen.getByPlaceholderText("Название кампании"));

    await userEvent.setup().click(screen.getByRole("button", { name: "Создать кампанию" }));

    await waitFor(() => {
      expect(screen.getByText("Название обязательно")).toBeInTheDocument();
    });
  });

  it("shows validation error when contract not selected", async () => {
    setup();
    await waitFor(() => screen.getByPlaceholderText("Название кампании"));

    const nameInput = screen.getByPlaceholderText("Название кампании");
    await userEvent.setup().type(nameInput, "Test");

    await userEvent.setup().click(screen.getByRole("button", { name: "Создать кампанию" }));

    await waitFor(() => {
      expect(screen.getByText("Договор обязателен")).toBeInTheDocument();
    });
  });

  it("POSTs correct payload and navigates on success", async () => {
    mockPost.mockResolvedValue({ id: "new-camp-123" });
    setup();

    await waitFor(() => screen.getByPlaceholderText("Название кампании"));

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Название кампании"), "Тестовая кампания");
    // Select contract
    await user.selectOptions(
      screen.getByLabelText("Договор *"),
      "c1",
    );
    await user.click(screen.getByRole("button", { name: "Создать кампанию" }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledTimes(1);
    });

    const [path, payload] = mockPost.mock.calls[0];
    expect(path).toBe("/campaigns");
    expect(payload.name).toBe("Тестовая кампания");
    expect(payload.advertiser_organization_id).toBe("ADV-001");
    expect(payload.advertiser_contract_id).toBe("c1");
    expect(mockNavigate).toHaveBeenCalledWith("/campaigns/new-camp-123");
  });

  it("shows friendly 403 error", async () => {
    mockPost.mockRejectedValue(makeApiError(403, "Forbidden"));
    setup();

    await waitFor(() => screen.getByPlaceholderText("Название кампании"));
    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Название кампании"), "Test");
    // Contract select — use value directly
    const contractSelect = document.querySelector("#field-contract") as HTMLSelectElement;
    if (contractSelect) {
      await user.selectOptions(contractSelect, "c1");
    }
    await user.click(screen.getByRole("button", { name: "Создать кампанию" }));

    await waitFor(() => {
      expect(screen.getByText("Нет прав на создание кампаний")).toBeInTheDocument();
    }, { timeout: 2000 });
  });
});
