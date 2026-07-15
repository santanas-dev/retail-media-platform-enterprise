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
    // refresh fails → unauthenticated → redirect to login
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("No cookie"));

    renderWithAuth("/campaigns");

    await waitFor(() => {
      expect(screen.getByText("Центр управления рекламой")).toBeTruthy();
    });
  });

  // ── Login failure ──

  it("shows error on failed login", async () => {
    // refresh fails → show login page. Then login attempt fails.
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("No cookie"));

    renderWithAuth("/login");

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Имя пользователя"),
      "baduser",
    );
    await user.type(screen.getByLabelText("Пароль"), "wrongpass");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      expect(
        screen.getByText("Неверное имя пользователя или пароль."),
      ).toBeTruthy();
    });
  });

  // ── Login success ──

  it("navigates to /campaigns on successful login", async () => {
    // refresh fails → login page shown
    // login succeeds → token set → redirect
    vi.spyOn(globalThis, "fetch")
      // refresh: fail (no cookie on first mount)
      .mockRejectedValueOnce(new Error("No cookie"))
      // login: success
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
      // getMe: success
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            sub: "u1",
            auth_provider: "ad",
            username: "admin",
            display_name: "Admin",
            must_change_password: false,
          }),
          { status: 200 },
        ),
      );
    // CampaignListPage fetches
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.includes("/campaigns") && !url.includes("flights") && !url.includes("placements") && !url.includes("creatives")) {
        return Promise.resolve(new Response(JSON.stringify({items: [], total: 0, limit: 50, offset: 0}), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    renderWithAuth("/login");

    const user = userEvent.setup();
    await user.type(
      screen.getByLabelText("Имя пользователя"),
      "admin",
    );
    await user.type(screen.getByLabelText("Пароль"), "secret");
    await user.click(screen.getByRole("button", { name: "Войти" }));

    await waitFor(() => {
      const items = screen.getAllByText("Кампании");
      expect(items.length).toBeGreaterThanOrEqual(2);
    });
  });

  // ── Logout clears session ──
  // S-035b: no localStorage token — session restore via refresh cookie

  it("logout clears session and redirects to login", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ access_token: "refreshed-at", token_type: "Bearer", expires_in: 1800 }),
            { status: 200 },
          ),
        );
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              sub: "u1", auth_provider: "ad", username: "admin",
              display_name: "Admin", permissions: [], must_change_password: false,
            }),
            { status: 200 },
          ),
        );
      }
      if (url.endsWith("/auth/logout")) {
        return Promise.resolve(
          new Response(JSON.stringify({ message: "Logged out" }), { status: 200 }),
        );
      }
      // Non-campaign endpoints return bare arrays
      if (url.includes("campaign-flights") || url.includes("advertiser-organizations") || url.includes("advertiser-brands")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
      // Campaign data: paginated empty
      return Promise.resolve(new Response(JSON.stringify({items: [], total: 0, limit: 50, offset: 0}), { status: 200 }));
    });

    renderWithAuth("/campaigns");

    // Wait for session restore
    await waitFor(() => {
      const items = screen.getAllByText("Кампании");
      expect(items.length).toBeGreaterThanOrEqual(2);
    });

    // S-035b proof: no localStorage token after restore
    expect(localStorage.getItem("rmp_access_token")).toBeNull();

    // Click logout
    const logoutBtn = screen.getByText("Выход");
    await userEvent.setup().click(logoutBtn);

    await waitFor(() => {
      expect(screen.getByText("Центр управления рекламой")).toBeTruthy();
    });

    // S-035b proof: still no localStorage token after logout
    expect(localStorage.getItem("rmp_access_token")).toBeNull();
  });
});
