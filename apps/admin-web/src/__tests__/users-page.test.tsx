import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import UsersPage from "../pages/UsersPage";
import { AuthProvider } from "../auth/AuthContext";

const SEED_USERS = [
  { id: "u1", code: "ADMIN", username: "admin", display_name: "Администратор", auth_provider: "ad", status: "active" },
  { id: "u2", code: "OPERATOR", username: "operator", display_name: "Оператор", auth_provider: "local_break_glass", status: "active" },
];

const SEED_DETAIL = {
  id: "u2",
  code: "OPERATOR",
  username: "operator",
  display_name: "Оператор",
  auth_provider: "local_break_glass",
  status: "active",
  is_break_glass: false,
  must_change_password: false,
  roles: [
    { id: "ur1", role_id: "r1", role_code: "operator", role_name: "Оператор", scope_type: null, scope_id: null },
  ],
};

const SEED_ROLES = [
  { id: "r1", code: "system_admin", name: "Системный администратор", description: "", is_system: true },
  { id: "r2", code: "operator", name: "Оператор", description: "", is_system: false },
  { id: "r3", code: "advertiser", name: "Рекламодатель", description: "", is_system: false },
];

function createRouter(path = "/users") {
  return createMemoryRouter(
    [{ path: "/users", element: <UsersPage /> }],
    { initialEntries: [path] },
  );
}

describe("UsersPage — role management RBAC", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hides Роли button when user lacks roles.manage", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        );
      }
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "reader", display_name: "Reader",
            permissions: ["users.read"] }),
          { status: 200 },
        );
      }
      if (url.includes("/users?")) {
        return new Response(JSON.stringify({ items: SEED_USERS, total: 2, limit: 50, offset: 0 }), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Администратор")).toBeTruthy();
    });

    // Button must NOT be visible
    expect(screen.queryByTestId("user-roles-open")).toBeNull();
  });

  it("shows Роли button when user has roles.manage", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        );
      }
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin",
            permissions: ["users.read", "users.manage", "roles.manage"] }),
          { status: 200 },
        );
      }
      if (url.includes("/users?")) {
        return new Response(JSON.stringify({ items: SEED_USERS, total: 2, limit: 50, offset: 0 }), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Администратор")).toBeTruthy();
    });

    // Button must be visible
    const buttons = screen.queryAllByTestId("user-roles-open");
    expect(buttons.length).toBeGreaterThan(0);
  });

  it("shows role management panel when Роли is clicked", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        );
      }
      if (url.endsWith("/me")) {
        return new Response(
          JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin",
            permissions: ["users.read", "users.manage", "roles.manage"] }),
          { status: 200 },
        );
      }
      if (url.includes("/users?")) {
        return new Response(JSON.stringify({ items: SEED_USERS, total: 2, limit: 50, offset: 0 }), { status: 200 });
      }
      if (url.match(/\/users\/u[12]$/)) {
        return new Response(JSON.stringify({ ...SEED_DETAIL, id: url.includes("u2") ? "u2" : "u1" }),
          { status: 200 });
      }
      if (url.endsWith("/roles")) {
        return new Response(JSON.stringify(SEED_ROLES), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Администратор")).toBeTruthy();
    });

    // Click Роли on first user
    const rolesBtn = screen.getAllByTestId("user-roles-open")[0];
    await user.click(rolesBtn);

    // Wait for panel and detail content
    await waitFor(() => {
      expect(screen.getByTestId("user-roles-panel")).toBeTruthy();
    });

    // Current role should be shown (may appear in panel title + role list)
    await waitFor(() => {
      const matches = screen.getAllByText(/Оператор/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });

    // Role dropdown and save button should be visible
    expect(screen.getByTestId("user-roles-role")).toBeTruthy();
    expect(screen.getByTestId("user-roles-save")).toBeTruthy();
  });
});
