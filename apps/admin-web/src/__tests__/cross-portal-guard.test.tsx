import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../theme/ThemeContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";

/**
 * AUTHZ-CROSS-PORTAL-001 — cookies are not isolated by port, so the refresh
 * cookie issued to the advertiser cabinet (:3001) is also sent to the
 * operator console (:3000) and restores a session here.  The operator shell
 * must not mount for an advertiser-cabinet identity.
 */

function operatorRouter() {
  return createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        ),
        children: [{ path: "campaigns", element: <div>operator campaigns</div> }],
      },
    ],
    { initialEntries: ["/campaigns"] },
  );
}

function mockSession(me: Record<string, unknown>) {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url =
      typeof input === "string"
        ? input
        : input instanceof URL
          ? input.toString()
          : String(input);
    calls.push(url);
    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/auth/me")) {
      return Promise.resolve(new Response(JSON.stringify(me), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }));
  });
  return calls;
}

function renderApp() {
  render(
    <ThemeProvider>
      <AuthProvider>
        <RouterProvider router={operatorRouter()} />
      </AuthProvider>
    </ThemeProvider>,
  );
}

const ADVERTISER_ME = {
  sub: "u-adv",
  auth_provider: "local_advertiser",
  username: "advertiser_test",
  display_name: "Тестовый Рекламодатель",
  permissions: ["campaigns.read", "campaigns.manage", "advertisers.read"],
  must_change_password: false,
  advertiser_organization_id: "00000000-0000-0000-0000-000000000200",
};

const OPERATOR_ME = {
  sub: "u-admin",
  auth_provider: "local_break_glass",
  username: "break_glass_admin",
  display_name: "Администратор",
  permissions: ["campaigns.read", "campaigns.manage"],
  must_change_password: false,
  advertiser_organization_id: null,
};

describe("AUTHZ-CROSS-PORTAL-001 — operator console rejects a cabinet session", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the wrong-portal notice instead of the operator shell", async () => {
    mockSession(ADVERTISER_ME);
    renderApp();

    expect(await screen.findByTestId("wrong-portal-notice")).toBeTruthy();
    expect(screen.queryByText("operator campaigns")).toBeNull();
  });

  it("does not render any operator action for a cabinet session", async () => {
    mockSession(ADVERTISER_ME);
    renderApp();

    await screen.findByTestId("wrong-portal-notice");
    expect(screen.queryByTestId("campaign-create-open")).toBeNull();
    expect(screen.queryByTestId("theme-toggle")).toBeNull();
  });

  it("issues no operator API request on behalf of a cabinet session", async () => {
    const calls = mockSession(ADVERTISER_ME);
    renderApp();

    await screen.findByTestId("wrong-portal-notice");
    const operatorCalls = calls.filter(
      (u) => !u.endsWith("/auth/refresh") && !u.endsWith("/auth/me"),
    );
    expect(operatorCalls).toEqual([]);
  });

  it("still mounts the operator shell for an operator session", async () => {
    mockSession(OPERATOR_ME);
    renderApp();

    expect(await screen.findByText("operator campaigns")).toBeTruthy();
    expect(screen.queryByTestId("wrong-portal-notice")).toBeNull();
  });
});
