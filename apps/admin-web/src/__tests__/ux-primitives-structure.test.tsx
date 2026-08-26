import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../theme/ThemeContext";
import Layout from "../components/Layout";
import { setViewportWidth, DESKTOP_WIDTH, MOBILE_WIDTH } from "./testMatchMedia";

/**
 * PORTAL-UX-002 — the shell may change how it behaves, not where the console's
 * furniture is. The UI-smoke suite navigates through `aside nav a[href=…]`, so
 * the desktop landmark has to stay an <aside>; the drawer is a dialog only in
 * narrow mode, where the smoke never runs.
 */

const OPERATOR = {
  sub: "u-op",
  auth_provider: "local_break_glass",
  username: "operator",
  display_name: "Оператор",
  permissions: ["campaigns.read", "audit.read"],
};

function mockSession() {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : String(input);
    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }),
        { status: 200 }));
    }
    if (url.endsWith("/auth/me")) {
      return Promise.resolve(new Response(JSON.stringify(OPERATOR), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0 }), { status: 200 }));
  });
}

function renderShell() {
  const router = createMemoryRouter(
    [{ path: "/", element: <Layout />, children: [{ path: "campaigns", element: <div>ok</div> }] }],
    { initialEntries: ["/campaigns"] },
  );
  return render(
    <ThemeProvider>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ThemeProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("shell structure the UI-smoke suite depends on", () => {
  beforeEach(() => setViewportWidth(DESKTOP_WIDTH));

  it("keeps `aside nav a[href]` navigable on desktop", async () => {
    mockSession();
    const { container } = renderShell();
    await screen.findByRole("link", { name: "Кампании" });
    expect(container.querySelector('aside nav a[href="/campaigns"]')).not.toBeNull();
    expect(container.querySelector('aside nav a[href="/audit"]')).not.toBeNull();
  });
});

describe("shell structure in drawer mode", () => {
  beforeEach(() => setViewportWidth(MOBILE_WIDTH));

  it("is a dialog rather than a complementary landmark", async () => {
    mockSession();
    const { container } = renderShell();
    await screen.findByTestId("nav-menu-toggle");
    expect(container.querySelector("aside")).toBeNull();
    expect(screen.getByTestId("nav-sidebar").tagName).toBe("DIV");
  });
});
