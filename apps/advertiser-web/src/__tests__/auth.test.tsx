import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "../auth/AuthContext";
import LoginPage from "../pages/LoginPage";

// Mock the api module
const mockLogin = vi.fn();
const mockLogout = vi.fn();
const mockGetMe = vi.fn();

vi.mock("../api/client", () => ({
  api: {
    login: (...args: unknown[]) => mockLogin(...args),
    logout: (...args: unknown[]) => mockLogout(...args),
    getMe: (...args: unknown[]) => mockGetMe(...args),
    get: vi.fn(),
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

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("Auth — login contract", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("calls /api/v1/auth/login with auth_provider=local_advertiser", async () => {
    mockLogin.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 1800,
      user: { sub: "u1", auth_provider: "local_advertiser" },
    });
    mockGetMe.mockResolvedValue({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "advertiser1",
      display_name: "Рекламодатель 1",
    });

    renderLogin();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Имя пользователя"), "advertiser1");
    await user.type(screen.getByLabelText("Пароль"), "password123");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledTimes(1);
    });

    const loginCall = mockLogin.mock.calls[0][0];
    expect(loginCall.username_or_email).toBe("advertiser1");
    expect(loginCall.password).toBe("password123");
    expect(loginCall.auth_provider).toBe("local_advertiser");
  });

  it("wrong provider user gets blocked", async () => {
    mockLogin.mockResolvedValue({
      access_token: "test-token",
      token_type: "Bearer",
      expires_in: 1800,
      user: { sub: "u1", auth_provider: "ad" },
    });
    mockGetMe.mockResolvedValue({
      sub: "u1",
      auth_provider: "ad",
      username: "admin",
      display_name: "Администратор",
    });

    renderLogin();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Имя пользователя"), "admin");
    await user.type(screen.getByLabelText("Пароль"), "password123");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    // Should show access error
    await waitFor(() => {
      expect(
        screen.getByText("Нет доступа к кабинету рекламодателя."),
      ).toBeInTheDocument();
    });

    // Token should not be stored
    expect(localStorage.getItem("rmp_access_token")).toBeNull();
  });
});

describe("Auth — logout", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("clears session on logout", async () => {
    // Set up a stored session
    localStorage.setItem("rmp_access_token", "stored-token");
    localStorage.setItem("rmp_auth_provider", "local_advertiser");

    mockGetMe.mockResolvedValue({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "advertiser1",
      display_name: "Рекламодатель 1",
    });
    mockLogout.mockResolvedValue({});

    // Render auth context with consumer
    function LogoutTest() {
      const auth = useAuth();
      return (
        <div>
          <span data-testid="user">{auth.user?.username || "no-user"}</span>
          <button data-testid="logout-btn" onClick={auth.logout}>
            Выйти
          </button>
        </div>
      );
    }

    render(
      <MemoryRouter>
        <AuthProvider>
          <LogoutTest />
        </AuthProvider>
      </MemoryRouter>,
    );

    // Wait for session restore
    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("advertiser1");
    });

    // Click logout
    fireEvent.click(screen.getByTestId("logout-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("user").textContent).toBe("no-user");
      expect(localStorage.getItem("rmp_access_token")).toBeNull();
      expect(localStorage.getItem("rmp_auth_provider")).toBeNull();
    });
  });
});

describe("Auth — 401 handling", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("401 triggers session clear", async () => {
    // Set up a stored session
    localStorage.setItem("rmp_access_token", "expired-token");
    localStorage.setItem("rmp_auth_provider", "local_advertiser");

    // getMe returns 401
    mockGetMe.mockRejectedValue(
      new (class extends Error {
        status = 401;
        constructor() {
          super("HTTP 401");
          this.name = "ApiError";
        }
      })(),
    );

    render(
      <MemoryRouter>
        <AuthProvider>
          <div data-testid="child">content</div>
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      screen.getByTestId("child");
    });

    // Session should be cleared after failed getMe
    expect(localStorage.getItem("rmp_access_token")).toBeNull();
  });
});

describe("ProtectedRoute — permission guard", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("local_advertiser with campaigns.read is allowed", async () => {
    localStorage.setItem("rmp_access_token", "valid-token");
    localStorage.setItem("rmp_auth_provider", "local_advertiser");

    mockGetMe.mockResolvedValue({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "advertiser1",
      display_name: "Рекламодатель 1",
      permissions: ["campaigns.read", "campaigns.manage", "creatives.read"],
    });

    const { default: ProtectedRoute } = await import("../components/ProtectedRoute");

    render(
      <MemoryRouter initialEntries={["/campaigns"]}>
        <AuthProvider>
          <ProtectedRoute>
            <div data-testid="child">content</div>
          </ProtectedRoute>
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("child")).toBeInTheDocument();
    });
  });

  it("local_advertiser without campaigns.read is blocked", async () => {
    localStorage.setItem("rmp_access_token", "valid-token");
    localStorage.setItem("rmp_auth_provider", "local_advertiser");

    mockGetMe.mockResolvedValue({
      sub: "u1",
      auth_provider: "local_advertiser",
      username: "advertiser1",
      display_name: "Рекламодатель 1",
      permissions: ["creatives.read"],
    });

    const { default: ProtectedRoute } = await import("../components/ProtectedRoute");

    render(
      <MemoryRouter initialEntries={["/campaigns"]}>
        <AuthProvider>
          <ProtectedRoute>
            <div data-testid="child">content</div>
          </ProtectedRoute>
        </AuthProvider>
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(
        screen.getByText("Нет прав на просмотр кампаний"),
      ).toBeInTheDocument();
    });

    // Child should NOT render
    expect(screen.queryByTestId("child")).toBeNull();
  });
});
