import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";

// ── Helpers ──

interface TestUser {
  sub: string;
  auth_provider: string;
  username: string;
  display_name: string;
  permissions: string[];
  must_change_password: boolean;
}

function mockSession(user: TestUser) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({ access_token: "test-at", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/auth/me")) {
      return Promise.resolve(
        new Response(JSON.stringify(user), { status: 200 }),
      );
    }
    // Default: paginated empty
    return Promise.resolve(
      new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }),
    );
  });
}

function createLayoutRouter() {
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
          { path: "campaigns", element: <div>campaigns</div> },
          { path: "campaigns/approvals", element: <div>approvals</div> },
          { path: "creatives/moderation", element: <div>moderation</div> },
          { path: "inventory", element: <div>inventory</div> },
          { path: "advertisers", element: <div>advertisers</div> },
          { path: "users", element: <div>users</div> },
          { path: "settings/ad", element: <div>ad settings</div> },
          { path: "audit", element: <div>audit</div> },
        ],
      },
    ],
    { initialEntries: ["/"] },
  );
}

function renderLayout(user: TestUser) {
  mockSession(user);
  const router = createLayoutRouter();
  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

// ── Permission-filtered Menu Tests ──

describe("permission-filtered layout menu", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  const system_admin: TestUser = {
    sub: "u-admin",
    auth_provider: "local_break_glass",
    username: "admin",
    display_name: "Администратор",
    permissions: [
      "campaigns.read", "campaigns.approve", "creatives.moderate",
      "inventory.read", "advertisers.read",
      "users.read", "users.manage",
      "audit.read",
    ],
    must_change_password: false,
  };

  it("shows all nav items for system_admin with full permissions", async () => {
    renderLayout(system_admin);

    await waitFor(() => {
      expect(screen.getByText("Кампании")).toBeTruthy();
    });

    expect(screen.getByText("Согласование кампаний")).toBeTruthy();
    expect(screen.getByText("Модерация креативов")).toBeTruthy();
    expect(screen.getByText("Инвентарь")).toBeTruthy();
    expect(screen.getByText("Рекламодатели")).toBeTruthy();
    expect(screen.getByText("Пользователи")).toBeTruthy();
    expect(screen.getByText("Настройки AD")).toBeTruthy();
    expect(screen.getByText("Журнал аудита")).toBeTruthy();
  });

  it("hides creatives.moderate when user lacks permission", async () => {
    renderLayout({
      ...system_admin,
      permissions: system_admin.permissions.filter((p) => p !== "creatives.moderate"),
    });

    await waitFor(() => {
      expect(screen.getByText("Кампании")).toBeTruthy();
    });

    expect(screen.queryByText("Модерация креативов")).toBeNull();
    // Other items still visible
    expect(screen.getByText("Согласование кампаний")).toBeTruthy();
  });

  it("hides AD settings when user lacks users.manage", async () => {
    renderLayout({
      ...system_admin,
      permissions: ["campaigns.read", "users.read"], // no users.manage
    });

    await waitFor(() => {
      expect(screen.getByText("Кампании")).toBeTruthy();
    });

    expect(screen.queryByText("Настройки AD")).toBeNull();
    expect(screen.getByText("Пользователи")).toBeTruthy(); // users.read still grants
  });

  it("shows audit log when user has audit.read", async () => {
    renderLayout({
      ...system_admin,
      permissions: ["audit.read"],
    });

    await waitFor(() => {
      expect(screen.getByText("Журнал аудита")).toBeTruthy();
    });

    expect(screen.queryByText("Кампании")).toBeNull(); // no campaigns.read
  });

  it("hides audit log when user lacks audit.read", async () => {
    renderLayout({
      ...system_admin,
      permissions: system_admin.permissions.filter((p) => p !== "audit.read"),
    });

    await waitFor(() => {
      expect(screen.getByText("Кампании")).toBeTruthy();
    });

    expect(screen.queryByText("Журнал аудита")).toBeNull();
  });

  it("shows only permitted subset for operator-like user", async () => {
    renderLayout({
      sub: "u-op",
      auth_provider: "local_advertiser",
      username: "operator",
      display_name: "Оператор",
      permissions: ["campaigns.read", "inventory.read", "advertisers.read"],
      must_change_password: false,
    });

    await waitFor(() => {
      expect(screen.getByText("Кампании")).toBeTruthy();
    });

    expect(screen.getByText("Инвентарь")).toBeTruthy();
    expect(screen.getByText("Рекламодатели")).toBeTruthy();

    // Hidden
    expect(screen.queryByText("Согласование кампаний")).toBeNull();
    expect(screen.queryByText("Модерация креативов")).toBeNull();
    expect(screen.queryByText("Пользователи")).toBeNull();
    expect(screen.queryByText("Настройки AD")).toBeNull();
    expect(screen.queryByText("Журнал аудита")).toBeNull();
  });
});
