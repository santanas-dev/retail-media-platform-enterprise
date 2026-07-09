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
import LoginPage from "../pages/LoginPage";
import CampaignListPage from "../pages/CampaignListPage";

// ── Helpers ──

function createAuthRouter(initialRoute: string) {
  return createMemoryRouter(
    [
      {
        path: "/login",
        element: <LoginPage />,
      },
      {
        path: "/",
        element: (
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <div>home</div> },
          { path: "campaigns", element: <CampaignListPage /> },
        ],
      },
    ],
    { initialEntries: [initialRoute] },
  );
}

function renderWithAuth(initialRoute = "/") {
  const router = createAuthRouter(initialRoute);
  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

// ── Auth Shell Tests ──

describe("auth shell", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  // ── Protected route redirect ──

  it("redirects to /login when not authenticated", async () => {
    // Mock /me to reject — no stored token
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Unauthorized"));

    renderWithAuth("/campaigns");

    await waitFor(() => {
      expect(screen.getByText("Центр управления рекламой")).toBeTruthy();
    });
  });

  // ── Login failure ──

  it("shows error on failed login", async () => {
    // Mock 401 response — LoginPage shows generic "Invalid username or password."
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          code: "INVALID_CREDENTIALS",
          message: "Invalid username/email or password",
        }),
        { status: 401 },
      ),
    );

    renderWithAuth("/login");

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Имя пользователя"),
      "baduser",
    );
    await user.type(screen.getByLabelText("Пароль"), "wrongpass");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    // LoginPage catches any login error and shows generic message
    await waitFor(() => {
      expect(
        screen.getByText("Invalid username or password."),
      ).toBeTruthy();
    });
  });

  // ── Login success ──

  it("navigates to /campaigns on successful login", async () => {
    // Order: login → /me
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            access_token: "at",
            token_type: "Bearer",
            expires_in: 1800,
            user: { sub: "u1", auth_provider: "ad" },
          }),
          { status: 200 },
        ),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            sub: "u1",
            auth_provider: "ad",
            username: "admin",
            display_name: "Admin",
          }),
          { status: 200 },
        ),
      );

    renderWithAuth("/login");

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Имя пользователя"),
      "admin",
    );
    await user.type(screen.getByLabelText("Пароль"), "secret");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    // Both sidebar link and page title say "Кампании"
    await waitFor(() => {
      const items = screen.getAllByText("Кампании");
      expect(items.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ── Logout clears session ──

  it("logout clears session and redirects to login", async () => {
    // 1. Simulate logged-in state: token in localStorage + /me succeeds
    localStorage.setItem("rmp_access_token", "valid-token");

    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            sub: "u1",
            auth_provider: "ad",
            username: "admin",
            display_name: "Admin",
          }),
          { status: 200 },
        ),
      )
      // logout call
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ message: "Logged out" }), { status: 200 }),
      );

    renderWithAuth("/campaigns");

    // Wait for session restore (sidebar + page title both say "Кампании")
    await waitFor(() => {
      const items = screen.getAllByText("Кампании");
      expect(items.length).toBeGreaterThanOrEqual(2);
    });

    // Find and click logout button
    const logoutBtn = screen.getByText("Выход");
    await userEvent.setup().click(logoutBtn);

    // Should redirect to login
    await waitFor(() => {
      expect(screen.getByText("Центр управления рекламой")).toBeTruthy();
      expect(localStorage.getItem("rmp_access_token")).toBeNull();
    });
  });
});
