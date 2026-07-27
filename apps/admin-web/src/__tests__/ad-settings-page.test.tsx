import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import ADSettingsPage from "../pages/ADSettingsPage";
import { AuthProvider } from "../auth/AuthContext";

const SEED_SETTINGS = {
  enabled: false,
  mode: "disabled",
  server_url: "",
  base_dn: "",
  user_search_base: "",
  user_search_filter: "(sAMAccountName={username})",
  bind_dn: "",
  use_tls: true,
  certificate_validation: "required",
  message: "AD integration is disabled.",
};

function createRouter() {
  return createMemoryRouter(
    [{ path: "/", element: <ADSettingsPage /> }],
    { initialEntries: ["/"] },
  );
}

describe("ADSettingsPage — save form RBAC", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("hides edit form when user lacks users.manage", async () => {
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
      if (url.includes("/auth/ad-settings") && !url.includes("/test")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-page")).toBeTruthy();
    });

    // Edit form NOT visible
    expect(screen.queryByTestId("adsettings-edit-form")).toBeNull();
    // Save button NOT visible
    expect(screen.queryByTestId("adsettings-save-btn")).toBeNull();
  });

  it("shows edit form when user has users.manage", async () => {
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
      if (url.includes("/auth/ad-settings") && !url.includes("/test")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-page")).toBeTruthy();
    });

    // Edit form visible
    expect(screen.getByTestId("adsettings-edit-form")).toBeTruthy();
    // Save button visible
    expect(screen.getByTestId("adsettings-save-btn")).toBeTruthy();
  });

  it("shows success message after save", async () => {
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
      if (url.includes("/auth/ad-settings") && !url.includes("/test") && init?.method === "PUT") {
        // Return saved settings
        return new Response(JSON.stringify({
          ...SEED_SETTINGS,
          enabled: true,
          server_url: "ldaps://ad.test.com",
          mode: "configured",
          message: "AD integration is configured.",
        }), { status: 200 });
      }
      if (url.includes("/auth/ad-settings") && !url.includes("/test")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-save-btn")).toBeTruthy();
    });

    // Fill server_url field
    const serverInput = screen.getByTestId("adsettings-field-server-url");
    await user.clear(serverInput);
    await user.type(serverInput, "ldaps://ad.test.com");

    // Click save
    await user.click(screen.getByTestId("adsettings-save-btn"));

    // Success message appears
    await waitFor(() => {
      expect(screen.getByTestId("adsettings-save-success")).toBeTruthy();
    });
  });

  it("shows error banner on server error", async () => {
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
      if (url.includes("/auth/ad-settings") && !url.includes("/test") && init?.method === "PUT") {
        return new Response(
          JSON.stringify({ detail: "Server error" }),
          { status: 500 },
        );
      }
      if (url.includes("/auth/ad-settings") && !url.includes("/test")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-save-btn")).toBeTruthy();
    });

    await user.click(screen.getByTestId("adsettings-save-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-save-error")).toBeTruthy();
    });
  });

  it("does not render bind_password field in edit form", async () => {
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
      if (url.includes("/auth/ad-settings") && !url.includes("/test")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-edit-form")).toBeTruthy();
    });

    // No bind_password field in the edit form
    expect(screen.queryByTestId("adsettings-field-bind-password")).toBeNull();
    // The read-only details section mentions AD_BIND_PASSWORD as a note — that's fine
  });
});

// ── Test Connection Flow ──

describe("ADSettingsPage — test connection flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockSession(extra?: Record<string, unknown>) {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 });
      }
      if (url.endsWith("/me")) {
        return new Response(JSON.stringify({
          sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin",
          permissions: ["users.read", "users.manage"], ...extra,
        }), { status: 200 });
      }
      if (url.includes("/auth/ad-settings/test")) {
        return new Response(JSON.stringify({
          status: "not_configured",
          message: "AD integration is not configured.",
          tested_at: "2026-07-27T12:00:00Z",
          error_code: "ad_disabled",
        }), { status: 200 });
      }
      if (url.includes("/auth/ad-settings")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });
  }

  it("shows test result after clicking test button", async () => {
    const user = userEvent.setup();
    mockSession();

    const router = createRouter();
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-btn")).toBeTruthy();
    });

    await user.click(screen.getByTestId("adsettings-test-btn"));

    // Result should appear — not_configured maps to error testid
    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-error")).toBeTruthy();
    });

    // Message is human-readable
    expect(screen.getByText("AD integration is not configured.")).toBeTruthy();

    // No [object Object]
    const body = document.body.textContent || "";
    expect(body).not.toContain("[object Object]");
  });

  it("shows test success for ok status", async () => {
    const user = userEvent.setup();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 });
      }
      if (url.endsWith("/me")) {
        return new Response(JSON.stringify({
          sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin",
          permissions: ["users.read", "users.manage"],
        }), { status: 200 });
      }
      if (url.includes("/auth/ad-settings/test")) {
        return new Response(JSON.stringify({
          status: "ok",
          message: "AD connection test passed — server reachable.",
          tested_at: "2026-07-27T12:00:00Z",
          error_code: null,
        }), { status: 200 });
      }
      if (url.includes("/auth/ad-settings")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const router = createRouter();
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-btn")).toBeTruthy();
    });

    await user.click(screen.getByTestId("adsettings-test-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-success")).toBeTruthy();
    });

    expect(screen.getByText("AD connection test passed — server reachable.")).toBeTruthy();
  });

  it("does not render bind_password in test result", async () => {
    const user = userEvent.setup();
    mockSession();

    const router = createRouter();
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-btn")).toBeTruthy();
    });

    await user.click(screen.getByTestId("adsettings-test-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-error")).toBeTruthy();
    });

    // Check only the test result element — not the informational footnote in details
    const resultEl = screen.getByTestId("adsettings-test-error");
    const resultText = resultEl.textContent || "";
    expect(resultText).not.toContain("bind_password");
    expect(resultText).not.toContain("AD_BIND_PASSWORD");
  });

  it("shows loading state while testing", async () => {
    const user = userEvent.setup();
    let resolveTest: (v: Response) => void;
    const testPromise = new Promise<Response>((r) => { resolveTest = r; });

    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 });
      }
      if (url.endsWith("/me")) {
        return new Response(JSON.stringify({
          sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin",
          permissions: ["users.read", "users.manage"],
        }), { status: 200 });
      }
      if (url.includes("/auth/ad-settings/test")) {
        return testPromise;
      }
      if (url.includes("/auth/ad-settings")) {
        return new Response(JSON.stringify(SEED_SETTINGS), { status: 200 });
      }
      return new Response(JSON.stringify({}), { status: 200 });
    });

    const router = createRouter();
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-btn")).toBeTruthy();
    });

    await user.click(screen.getByTestId("adsettings-test-btn"));

    // Loading indicator visible
    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-loading")).toBeTruthy();
    });

    // Resolve the test
    resolveTest!(new Response(JSON.stringify({
      status: "ok", message: "OK", tested_at: "2026-07-27T12:00:00Z", error_code: null,
    }), { status: 200 }));

    // Loading disappears, result appears
    await waitFor(() => {
      expect(screen.getByTestId("adsettings-test-success")).toBeTruthy();
    });
  });
});
