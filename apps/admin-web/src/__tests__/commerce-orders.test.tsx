/**
 * COMMERCE-CONTUR2-001A3b+A3c — Vitest for CommerceOrdersTab.
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

const MOCK_ORDERS = [
  {
    id: "ord-1", advertiser_organization_id: "00000000-0000-0000-0000-000000000200",
    code: "ORD-2026-0001", status: "draft", payment_status: "unpaid",
    tariff_version_id: "tv-1", total_amount: 1050.0, currency: "RUB",
    created_at: "2026-08-01T00:00:00Z", updated_at: null,
    lines: [{ id: "ln-1", order_id: "ord-1", surface_id: "00000000-0000-0000-0000-000000000031",
      date_from: "2026-08-01", date_to: "2026-08-07", quantity_days: 7,
      unit_price_amount: 150.0, line_amount: 1050.0 }],
  },
  {
    id: "ord-2", advertiser_organization_id: "00000000-0000-0000-0000-000000000200",
    code: "ORD-2026-0002", status: "confirmed", payment_status: "paid",
    tariff_version_id: "tv-1", total_amount: 2100.0, currency: "RUB",
    created_at: "2026-08-02T00:00:00Z", updated_at: "2026-08-02T12:00:00Z",
    lines: [{ id: "ln-2", order_id: "ord-2", surface_id: "00000000-0000-0000-0000-000000000031",
      date_from: "2026-08-01", date_to: "2026-08-14", quantity_days: 14,
      unit_price_amount: 150.0, line_amount: 2100.0 }],
  },
];

const CLOSED_ORDER = {
  id: "ord-3", advertiser_organization_id: "00000000-0000-0000-0000-000000000200",
  code: "ORD-2026-0003", status: "closed", payment_status: "paid",
  tariff_version_id: "tv-1", total_amount: 3150.0, currency: "RUB",
  created_at: "2026-08-03T00:00:00Z", updated_at: "2026-08-03T14:00:00Z",
  lines: [{ id: "ln-3", order_id: "ord-3", surface_id: "00000000-0000-0000-0000-000000000031",
    date_from: "2026-08-01", date_to: "2026-08-21", quantity_days: 21,
    unit_price_amount: 150.0, line_amount: 3150.0 }],
};

function mockDefault(perms?: string[]) {
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
        permissions: perms ?? ["commerce.order_read", "commerce.order_manage"],
        must_change_password: false,
      }), { status: 200 }));
    }
    if (url.includes("/commerce/tariff-versions")) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.includes("/commerce/orders")) {
      return Promise.resolve(new Response(JSON.stringify(MOCK_ORDERS), { status: 200 }));
    }
    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

function mockOrdersWithClosed() {
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
        permissions: ["commerce.order_read", "commerce.order_manage"],
        must_change_password: false,
      }), { status: 200 }));
    }
    if (url.includes("/commerce/tariff-versions")) {
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    }
    if (url.includes("/commerce/orders")) {
      const resp = [MOCK_ORDERS[0], MOCK_ORDERS[1], CLOSED_ORDER];
      return Promise.resolve(new Response(JSON.stringify(resp), { status: 200 }));
    }
    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

function renderPage() {
  const router = createRouter();
  return render(
    <ThemeProvider>
      <AuthProvider><RouterProvider router={router} /></AuthProvider>
    </ThemeProvider>,
  );
}

async function navigateToOrders() {
  await waitFor(() => screen.getByTestId("commerce-tariffs-page"));
  await userEvent.setup().click(screen.getByText("Заказы"));
  await waitFor(() => screen.getByText("ORD-2026-0001"));
}

beforeEach(() => { vi.restoreAllMocks(); });
afterEach(() => { vi.restoreAllMocks(); });

describe("CommerceOrdersTab", () => {
  // ── Basic tests ──

  it("switches to orders tab", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
  });

  it("shows order list with status and total", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
    expect(screen.getByText("Черновик")).toBeTruthy();
    expect(screen.getByText(/1.?050/)).toBeTruthy();
  });

  it("shows create button for order_manage", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
    expect(screen.getByTestId("commerce-order-create-open")).toBeTruthy();
  });

  it("hides create button without order_manage", async () => {
    mockDefault(["commerce.order_read"]); renderPage(); await navigateToOrders();
    expect(screen.queryByTestId("commerce-order-create-open")).toBeNull();
  });

  it("opens create form", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
    await userEvent.setup().click(screen.getByTestId("commerce-order-create-open"));
    await waitFor(() => expect(screen.getByTestId("commerce-order-create-form")).toBeTruthy());
  });

  it("shows order detail with lines on row click", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
    await userEvent.setup().click(screen.getByTestId("commerce-order-row-ord-1"));
    await waitFor(() => {
      expect(screen.getByTestId("commerce-order-detail")).toBeTruthy();
      expect(screen.getByTestId("commerce-order-lines-table")).toBeTruthy();
    });
  });

  it("shows status transition buttons for draft order", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
    await userEvent.setup().click(screen.getByTestId("commerce-order-row-ord-1"));
    await waitFor(() => {
      expect(screen.getByTestId("commerce-order-transition-offered")).toBeTruthy();
      expect(screen.getByTestId("commerce-order-transition-cancelled")).toBeTruthy();
    });
  });

  it("shows payment status selector", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
    await userEvent.setup().click(screen.getByTestId("commerce-order-row-ord-1"));
    await waitFor(() => expect(screen.getByTestId("commerce-order-payment-select")).toBeTruthy());
  });

  // ── A3c: Close order tests ──

  it("shows close button for confirmed order", async () => {
    mockDefault(); renderPage(); await navigateToOrders();
    await userEvent.setup().click(screen.getByTestId("commerce-order-row-ord-2"));
    await waitFor(() => {
      expect(screen.getByTestId("commerce-order-transition-closed")).toBeTruthy();
      expect(screen.getByTestId("commerce-order-transition-cancelled")).toBeTruthy();
    });
  });

  it("closed order shows Закрыт status in list", async () => {
    mockOrdersWithClosed(); renderPage(); await navigateToOrders();
    await waitFor(() => expect(screen.getByText("ORD-2026-0003")).toBeTruthy());
    expect(screen.getByText("Закрыт")).toBeTruthy();
    expect(screen.getByText(/3.?150/)).toBeTruthy();
  });
});
