import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "../auth/AuthContext";

// Mock the API client to avoid real network calls
vi.mock("../api/client", () => {
  const actual = vi.importActual("../api/client");
  return {
    ...actual,
    api: {
      login: vi.fn(),
      refresh: vi.fn(),
      logout: vi.fn(),
      getMe: vi.fn(),
      get: vi.fn(),
      post: vi.fn(),
      patch: vi.fn(),
      del: vi.fn(),
    },
    setToken: vi.fn(),
    onUnauthorized: vi.fn(),
    ApiError: class MockApiError extends Error {
      status: number;
      body: unknown;
      constructor(status: number, body: unknown) {
        super(`HTTP ${status}`);
        this.name = "ApiError";
        this.status = status;
        this.body = body;
      }
    },
  };
});

function TestApp({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter initialEntries={["/"]}>
      <AuthProvider>
        {children}
      </AuthProvider>
    </MemoryRouter>
  );
}

function AuthConsumer() {
  const auth = useAuth();
  return (
    <div>
      <span data-testid="user">{auth.user ? auth.user.username : "no-user"}</span>
      <span data-testid="loading">{String(auth.loading)}</span>
    </div>
  );
}

describe("app smoke", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("renders without crashing", () => {
    render(
      <TestApp>
        <AuthConsumer />
      </TestApp>,
    );
    expect(screen.getByTestId("loading")).toBeInTheDocument();
  });

  it("shows no user when unauthenticated (no stored token)", async () => {
    render(
      <TestApp>
        <AuthConsumer />
      </TestApp>,
    );

    // After loading resolves, user should be null
    const loadingEl = await screen.findByTestId("loading");
    expect(loadingEl.textContent).toBe("false");

    const userEl = screen.getByTestId("user");
    expect(userEl.textContent).toBe("no-user");
  });
});
