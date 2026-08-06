/**
 * COMMERCE-CONTUR2-001A3a — Vitest for CommerceTariffsPage.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../theme/ThemeContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import CommerceTariffsPage from "../pages/CommerceTariffsPage";

function createRouter() {
  return createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        ),
        children: [
          { index: true, element: <div>home</div> },
          { path: "commerce/tariffs", element: <CommerceTariffsPage /> },
        ],
      },
    ],
    { initialEntries: ["/commerce/tariffs"] },
  );
}

const MOCK_TARIFFS = [
  {
    id: "tv-1", code: "BASE-2026", name: "Базовый тариф 2026",
    status: "active", valid_from: "2026-01-01", valid_to: null,
    currency: "RUB", created_at: "2026-01-01T00:00:00Z", updated_at: null,
  },
];

const MOCK_PRICE_ITEMS = [
  {
    id: "pi-1", tariff_version_id: "tv-1",
    surface_id: "aaaa-bbbb-cccc-dddd-000000000001",
    billing_unit: "surface_day", unit_price_amount: 150.0,
    currency: "RUB", created_at: "2026-01-01T00:00:00Z",
  },
];

function setupFetch(perms?: string[]) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : String(input);

    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(new Response(JSON.stringify({
        access_token: "test-at", token_type: "Bearer", expires_in: 1800,
      }), { status: 200 }));
    }

    if (url.endsWith("/auth/me")) {
      return Promise.resolve(new Response(JSON.stringify({
        sub: "u-admin", auth_provider: "local_break_glass",
        username: "admin", display_name: "Администратор",
        permissions: perms ?? ["commerce.tariff_read", "commerce.tariff_manage"],
        must_change_password: false,
      }), { status: 200 }));
    }

    if (url.includes("/commerce/tariff-versions") && !url.includes("price-items")) {
      return Promise.resolve(new Response(JSON.stringify(MOCK_TARIFFS), { status: 200 }));
    }

    if (url.includes("/commerce/price-items")) {
      return Promise.resolve(new Response(JSON.stringify(MOCK_PRICE_ITEMS), { status: 200 }));
    }

    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

function renderPage(perms?: string[]) {
  setupFetch(perms);
  const router = createRouter();
  return render(
    <ThemeProvider>
      <AuthProvider><RouterProvider router={router} /></AuthProvider>
    </ThemeProvider>,
  );
}

beforeEach(() => { vi.restoreAllMocks(); });
afterEach(() => { vi.restoreAllMocks(); });

describe("CommerceTariffsPage", () => {
  it("renders page heading", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("commerce-tariffs-page")).toBeTruthy();
    });
  });

  it("shows tariffs after load", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("BASE-2026")).toBeTruthy();
    });
  });

  it("shows create button for manager", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("commerce-tariff-create-open")).toBeTruthy();
    });
  });

  it("hides create button for read-only", async () => {
    renderPage(["commerce.tariff_read"]);
    await waitFor(() => {
      expect(screen.getByTestId("commerce-tariffs-page")).toBeTruthy();
    });
    expect(screen.queryByTestId("commerce-tariff-create-open")).toBeNull();
  });

  it("opens create form", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("commerce-tariff-create-open")).toBeTruthy();
    });
    await userEvent.setup().click(screen.getByTestId("commerce-tariff-create-open"));
    await waitFor(() => {
      expect(screen.getByTestId("commerce-tariff-form")).toBeTruthy();
    });
  });

  it("switches to prices tab", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("commerce-tariffs-page")).toBeTruthy();
    });
    await userEvent.setup().click(screen.getByText("Прайс-листы"));
    await waitFor(() => {
      expect(screen.getByText(/Выберите тариф/)).toBeTruthy();
    });
  });

  it("shows price items after selecting tariff", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("commerce-tariff-row-tv-1")).toBeTruthy();
    });
    await userEvent.setup().click(screen.getByTestId("commerce-tariff-row-tv-1"));
    await userEvent.setup().click(screen.getByText("Прайс-листы"));
    await waitFor(() => {
      expect(screen.getByTestId("commerce-price-items-table")).toBeTruthy();
    });
  });
});
