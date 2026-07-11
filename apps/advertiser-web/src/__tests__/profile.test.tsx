import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import ProfilePage from "../pages/ProfilePage";

// Mock the api module
const mockGet = vi.fn();
const mockGetMe = vi.fn();
const mockChangePassword = vi.fn();
const mockLogout = vi.fn();
const mockLogin = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    get: (...args: unknown[]) => mockGet(...args),
    getMe: (...args: unknown[]) => mockGetMe(...args),
    changePassword: (...args: unknown[]) => mockChangePassword(...args),
    login: (...args: unknown[]) => mockLogin(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
    post: vi.fn(),
    patch: vi.fn(),
    del: vi.fn(),
    refresh: vi.fn(),
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

function setupProfile(overrides?: { must_change_password?: boolean }) {
  localStorage.setItem("rmp_access_token", "valid-token");
  localStorage.setItem("rmp_auth_provider", "local_advertiser");

  mockGetMe.mockResolvedValue({
    sub: "u1",
    auth_provider: "local_advertiser",
    username: "advertiser_test",
    display_name: "Рекламодатель Тест",
    permissions: ["campaigns.read", "creatives.read"],
    must_change_password: overrides?.must_change_password ?? false,
  });

  // Organizations
  mockGet.mockImplementation((path: string) => {
    if (path === "/advertiser-organizations") {
      return Promise.resolve([
        {
          id: "ADV-001",
          code: "ADV-001",
          legal_name: "ООО «Тестовый Рекламодатель»",
          display_name: "Тестовый Рекламодатель",
          status: "active",
        },
      ]);
    }
    if (path === "/advertiser-brands") {
      return Promise.resolve([
        { id: "b1", advertiser_organization_id: "ADV-001", code: "BRAND-A", name: "Бренд А", status: "active" },
      ]);
    }
    if (path === "/advertiser-contracts") {
      return Promise.resolve([
        {
          id: "c1",
          advertiser_organization_id: "ADV-001",
          code: "CONTRACT-1",
          name: "Договор №1",
          budget_limit_amount: 500000,
          budget_limit_currency: "RUB",
          valid_from: "2026-01-01",
          valid_until: null,
          status: "active",
        },
      ]);
    }
    if (path === "/advertiser-contacts") {
      return Promise.reject(new (class extends Error { status = 403; constructor() { super("Forbidden"); } })());
    }
    return Promise.resolve([]);
  });

  render(
    <MemoryRouter initialEntries={["/profile"]}>
      <AuthProvider>
        <ProfilePage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

function setupProfileWithContacts() {
  localStorage.setItem("rmp_access_token", "valid-token");
  localStorage.setItem("rmp_auth_provider", "local_advertiser");

  mockGetMe.mockResolvedValue({
    sub: "u1",
    auth_provider: "local_advertiser",
    username: "advertiser_test",
    display_name: "Рекламодатель Тест",
    permissions: ["campaigns.read", "creatives.read", "advertisers.contacts.read"],
    must_change_password: false,
  });

  mockGet.mockImplementation((path: string) => {
    if (path === "/advertiser-organizations") {
      return Promise.resolve([{ id: "ADV-001", code: "ADV-001", legal_name: "ООО «Тест»", display_name: "Тест", status: "active" }]);
    }
    if (path === "/advertiser-brands") return Promise.resolve([]);
    if (path === "/advertiser-contracts") return Promise.resolve([]);
    if (path === "/advertiser-contacts") {
      return Promise.resolve([
        { id: "cnt-1", advertiser_organization_id: "ADV-001", contact_type: "primary", full_name: "Иван Иванов", email: "ivan@test.ru", phone: "+79991234567", is_primary: true, status: "active" },
      ]);
    }
    return Promise.resolve([]);
  });

  render(
    <MemoryRouter initialEntries={["/profile"]}>
      <AuthProvider>
        <ProfilePage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ProfilePage — rendering", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("renders user info from /me", async () => {
    setupProfile();
    await waitFor(() => {
      expect(screen.getByText("advertiser_test")).toBeInTheDocument();
      expect(screen.getByText("Рекламодатель Тест")).toBeInTheDocument();
    });
  });

  it("renders organization info", async () => {
    setupProfile();
    await waitFor(() => {
      expect(screen.getByText("Тестовый Рекламодатель")).toBeInTheDocument();
      expect(screen.getByText("ООО «Тестовый Рекламодатель»")).toBeInTheDocument();
    });
  });

  it("renders brands table", async () => {
    setupProfile();
    await waitFor(() => {
      expect(screen.getByText("Бренд А")).toBeInTheDocument();
    });
  });

  it("renders contracts table with budget", async () => {
    setupProfile();
    await waitFor(() => {
      expect(screen.getByText("Договор №1")).toBeInTheDocument();
      expect(screen.getByText("500,000 RUB")).toBeInTheDocument();
    });
  });

  it("shows contacts access warning on 403", async () => {
    setupProfile();
    await waitFor(() => {
      expect(screen.getByText("Нет доступа к контактам")).toBeInTheDocument();
    });
  });

  it("renders contacts table when permitted", async () => {
    setupProfileWithContacts();
    await waitFor(() => {
      expect(screen.getByText("Иван Иванов")).toBeInTheDocument();
      expect(screen.getByText("ivan@test.ru")).toBeInTheDocument();
    });
  });
});

describe("ProfilePage — must_change_password banner", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("shows banner when must_change_password is true", async () => {
    setupProfile({ must_change_password: true });
    await waitFor(() => {
      expect(screen.getByText(/Необходимо сменить пароль/)).toBeInTheDocument();
    });
  });

  it("does not show banner when must_change_password is false", async () => {
    setupProfile({ must_change_password: false });
    await waitFor(() => {
      expect(screen.getByText("advertiser_test")).toBeInTheDocument();
    });
    expect(screen.queryByText(/Необходимо сменить пароль/)).toBeNull();
  });
});

describe("ProfilePage — password change", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("calls changePassword with correct values", async () => {
    mockChangePassword.mockResolvedValue({ message: "Password changed" });
    setupProfile();

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Текущий пароль")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Текущий пароль"), "oldpass");
    await user.type(screen.getByPlaceholderText(/Новый пароль.*минимум/), "new-password-123");
    await user.type(screen.getByPlaceholderText("Подтвердите новый пароль"), "new-password-123");
    await user.click(screen.getByRole("button", { name: "Сменить пароль" }));

    await waitFor(() => {
      expect(mockChangePassword).toHaveBeenCalledWith("oldpass", "new-password-123");
    });
  });

  it("shows success message and refreshes me", async () => {
    mockChangePassword.mockResolvedValue({ message: "Password changed" });
    setupProfile({ must_change_password: true });

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Текущий пароль")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Текущий пароль"), "oldpass");
    await user.type(screen.getByPlaceholderText(/Новый пароль.*минимум/), "new-password-123");
    await user.type(screen.getByPlaceholderText("Подтвердите новый пароль"), "new-password-123");
    await user.click(screen.getByRole("button", { name: "Сменить пароль" }));

    await waitFor(() => {
      expect(screen.getByText("Пароль изменён")).toBeInTheDocument();
      // refreshMe should have been called
      expect(mockGetMe).toHaveBeenCalled();
    });
  });

  it("shows error when passwords don't match", async () => {
    setupProfile();
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Текущий пароль")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Текущий пароль"), "oldpass");
    await user.type(screen.getByPlaceholderText(/Новый пароль.*минимум/), "new-password-123");
    await user.type(screen.getByPlaceholderText("Подтвердите новый пароль"), "different");
    await user.click(screen.getByRole("button", { name: "Сменить пароль" }));

    await waitFor(() => {
      expect(screen.getByText("Пароли не совпадают")).toBeInTheDocument();
    });
  });

  it("shows error when password too short", async () => {
    setupProfile();
    await waitFor(() => {
      expect(screen.getByPlaceholderText("Текущий пароль")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Текущий пароль"), "oldpass");
    await user.type(screen.getByPlaceholderText(/Новый пароль.*минимум/), "short");
    await user.type(screen.getByPlaceholderText("Подтвердите новый пароль"), "short");
    await user.click(screen.getByRole("button", { name: "Сменить пароль" }));

    await waitFor(() => {
      expect(screen.getByText("Пароль должен быть не менее 8 символов")).toBeInTheDocument();
    });
  });

  it("shows backend error on 400", async () => {
    mockChangePassword.mockRejectedValue(
      new (class extends Error {
        status = 400;
        constructor() {
          super("Current password is incorrect");
          this.name = "ApiError";
        }
      })(),
    );
    setupProfile();

    await waitFor(() => {
      expect(screen.getByPlaceholderText("Текущий пароль")).toBeInTheDocument();
    });

    const user = userEvent.setup();
    await user.type(screen.getByPlaceholderText("Текущий пароль"), "wrong");
    await user.type(screen.getByPlaceholderText(/Новый пароль.*минимум/), "new-password-123");
    await user.type(screen.getByPlaceholderText("Подтвердите новый пароль"), "new-password-123");
    await user.click(screen.getByRole("button", { name: "Сменить пароль" }));

    await waitFor(() => {
      expect(screen.getByText("Current password is incorrect")).toBeInTheDocument();
    });
  });
});
