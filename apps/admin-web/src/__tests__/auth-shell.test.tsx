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

function createAuthRouter(initialRoute: string) {
  return createMemoryRouter(
    [
      { path: "/login", element: <LoginPage /> },
      {
        path: "/",
        element: <ProtectedRoute><Layout /></ProtectedRoute>,
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
  return render(
    <AuthProvider>
      <RouterProvider router={createAuthRouter(initialRoute)} />
    </AuthProvider>,
  );
}

describe("auth shell", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("redirects to /login when not authenticated", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) return Promise.reject(new Error("No cookie"));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    renderWithAuth("/campaigns");
    await waitFor(() => {
      expect(screen.getByText("Центр управления рекламой")).toBeTruthy();
    });
  });

  it("login form defaults provider to AD for admin portal", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) return Promise.reject(new Error("No cookie"));
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    renderWithAuth("/login");
    await waitFor(() => {
      expect(screen.getByText("Центр управления рекламой")).toBeTruthy();
    });
    const select = screen.getByLabelText("Тип учётной записи") as HTMLSelectElement;
    expect(select.value).toBe("ad");
  });

  it("logout clears session and redirects to login", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "refreshed-at", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(JSON.stringify({
          sub: "u1", auth_provider: "ad", username: "admin",
          display_name: "Admin", permissions: ["campaigns.read"], must_change_password: false,
        }), { status: 200 }));
      }
      if (url.endsWith("/auth/logout")) {
        return Promise.resolve(new Response(JSON.stringify({ message: "Logged out" }), { status: 200 }));
      }
      if (url.includes("campaign-flights") || url.includes("advertiser-organizations") || url.includes("advertiser-brands")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }));
    });

    renderWithAuth("/campaigns");

    await waitFor(() => {
      expect(screen.getAllByText("Кампании").length).toBeGreaterThanOrEqual(2);
    });

    expect(localStorage.getItem("rmp_access_token")).toBeNull();

    const logoutBtn = screen.getByText("Выход");
    await userEvent.setup().click(logoutBtn);

    await waitFor(() => {
      expect(screen.getByText("Центр управления рекламой")).toBeTruthy();
    });

    expect(localStorage.getItem("rmp_access_token")).toBeNull();
  });
});
