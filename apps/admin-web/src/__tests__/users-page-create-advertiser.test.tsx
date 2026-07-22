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

function createRouter(path = "/users") {
  return createMemoryRouter(
    [{ path: "/users", element: <UsersPage /> }],
    { initialEntries: [path] },
  );
}

describe("UsersPage — create advertiser flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hides + Создать рекламодателя button when user lacks users.manage", async () => {
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

    // Create button must NOT be visible
    expect(screen.queryByTestId("user-create-advertiser-open")).toBeNull();
  });

  it("shows + Создать рекламодателя button when user has users.manage", async () => {
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

    expect(screen.getByTestId("user-create-advertiser-open")).toBeTruthy();
  });

  it("opens create form when + Создать рекламодателя is clicked", async () => {
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
            permissions: ["users.read", "users.manage"] }),
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

    // Click create button
    await user.click(screen.getByTestId("user-create-advertiser-open"));

    // Form fields should appear
    expect(screen.getByTestId("user-create-advertiser-username")).toBeTruthy();
    expect(screen.getByTestId("user-create-advertiser-display-name")).toBeTruthy();
    expect(screen.getByTestId("user-create-advertiser-org-id")).toBeTruthy();
    expect(screen.getByTestId("user-create-advertiser-submit")).toBeTruthy();
  });

  it("shows success result after successful create", async () => {
    const user = userEvent.setup();
    let createCalled = false;

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
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
            permissions: ["users.read", "users.manage"] }),
          { status: 200 },
        );
      }
      if (url.endsWith("/users/local-advertiser")) {
        createCalled = true;
        const body = JSON.parse(String(init?.body || "{}"));
        return new Response(
          JSON.stringify({
            user_id: "new-u3",
            username: body.username,
            display_name: body.display_name,
            one_time_password: "ABCD1234EFGH5678",
            message: "User created",
          }),
          { status: 201 },
        );
      }
      if (url.includes("/users?")) {
        // After create, list is re-fetched — return updated list
        const users = createCalled
          ? [...SEED_USERS, { id: "u3", code: "SMOKE", username: "smoke_adv_1", display_name: "Smoke Adv", auth_provider: "local_advertiser", status: "active" }]
          : SEED_USERS;
        return new Response(JSON.stringify({ items: users, total: users.length, limit: 50, offset: 0 }), { status: 200 });
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

    // Open create form
    await user.click(screen.getByTestId("user-create-advertiser-open"));

    // Fill form
    await user.type(screen.getByTestId("user-create-advertiser-username"), "smoke_adv_1");
    await user.type(screen.getByTestId("user-create-advertiser-display-name"), "Smoke Adv");
    await user.type(
      screen.getByTestId("user-create-advertiser-org-id"),
      "00000000-0000-4000-a000-000000000002",
    );

    // Submit
    await user.click(screen.getByTestId("user-create-advertiser-submit"));

    // Wait for success result
    await waitFor(() => {
      expect(screen.getByTestId("user-create-advertiser-result")).toBeTruthy();
    });

    // Result should contain the one-time password
    expect(screen.getByText(/ABCD1234EFGH5678/)).toBeTruthy();
    expect(createCalled).toBe(true);
  });

  it("shows error state on create failure", async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
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
            permissions: ["users.read", "users.manage"] }),
          { status: 200 },
        );
      }
      if (url.endsWith("/users/local-advertiser")) {
        return new Response(
          JSON.stringify({ detail: "Username already taken" }),
          { status: 409 },
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

    // Open create form
    await user.click(screen.getByTestId("user-create-advertiser-open"));

    // Fill and submit
    await user.type(screen.getByTestId("user-create-advertiser-username"), "admin");
    await user.type(screen.getByTestId("user-create-advertiser-display-name"), "X");
    await user.type(
      screen.getByTestId("user-create-advertiser-org-id"),
      "00000000-0000-4000-a000-000000000002",
    );
    await user.click(screen.getByTestId("user-create-advertiser-submit"));

    // Wait for error result
    await waitFor(() => {
      expect(screen.getByTestId("user-create-advertiser-result")).toBeTruthy();
    });

    // Result should show the error (no one-time password styling)
    expect(screen.getByText(/Username already taken/)).toBeTruthy();
  });
});
