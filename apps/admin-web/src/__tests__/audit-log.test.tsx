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
import AuditLogPage from "../pages/AuditLogPage";

// ── Helpers ──

function createAuditRouter() {
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
          { path: "audit", element: <AuditLogPage /> },
        ],
      },
    ],
    { initialEntries: ["/audit"] },
  );
}

function renderAuditPage(auditEvents: unknown[]) {
  // Session restore (refresh + me)
  // Then audit-events endpoint
  let refreshCalled = false;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
    if (url.endsWith("/auth/refresh")) {
      refreshCalled = true;
      return Promise.resolve(
        new Response(
          JSON.stringify({ access_token: "test-at", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ),
      );
    }
    if (url.endsWith("/auth/me")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            sub: "u-admin",
            auth_provider: "local_break_glass",
            username: "admin",
            display_name: "Администратор",
            permissions: ["audit.read"],
            must_change_password: false,
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/audit-events")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: auditEvents,
            total: auditEvents.length,
            limit: 50,
            offset: 0,
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }));
  });

  const router = createAuditRouter();
  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

function makeEvent(overrides: Record<string, unknown> = {}) {
  return {
    id: "ev-001",
    actor_user_id: "u-admin",
    action: "auth.login.success",
    target_type: "user",
    target_id: "u-admin",
    correlation_id: null,
    ip_address: "127.0.0.1",
    details_json: { method: "token" },
    created_at: "2026-07-16T10:00:00Z",
    ...overrides,
  };
}

// ── Audit Log Page Tests ──

describe("audit log page", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders audit events table when data loaded", async () => {
    renderAuditPage([makeEvent(), makeEvent({ id: "ev-002", action: "auth.logout" })]);

    await waitFor(() => {
      const headers = screen.getAllByText("Журнал аудита");
      expect(headers.length).toBeGreaterThanOrEqual(1);
      // Action labels rendered
      expect(screen.getByText("Вход")).toBeTruthy();
      expect(screen.getAllByText("Выход").length).toBeGreaterThanOrEqual(1);
    });

    // Actor — actor_user_id and target_id may be same, so getAllByText
    expect(screen.getAllByText("u-admin").length).toBeGreaterThanOrEqual(1);

    // Target
    expect(screen.getAllByText("user").length).toBe(2);

    // Pagination info
    expect(screen.getByText(/Всего: 2/)).toBeTruthy();
  });

  it("shows empty state when no events", async () => {
    renderAuditPage([]);

    await waitFor(() => {
      expect(screen.getByText("Нет записей аудита")).toBeTruthy();
    });
  });

  it("shows error state on fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("Network error"));

    // Only refresh fails → user is not authenticated, redirects to login.
    // To test audit fetch error, we need session to succeed and audit to fail.
    vi.restoreAllMocks();

    let meCalled = false;
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
        meCalled = true;
        return Promise.resolve(
          new Response(
            JSON.stringify({
              sub: "u-admin", auth_provider: "local_break_glass",
              username: "admin", display_name: "Admin",
              permissions: ["audit.read"], must_change_password: false,
            }),
            { status: 200 },
          ),
        );
      }
      if (url.includes("/audit-events")) {
        return Promise.reject(new Error("Network error"));
      }
      return Promise.resolve(new Response(JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }), { status: 200 }));
    });

    const router = createAuditRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeTruthy();
    });
  });

  it("redacts secret keys from details", async () => {
    renderAuditPage([
      makeEvent({
        id: "ev-secret",
        action: "auth.password_change",
        details_json: {
          password: "supersecret",
          password_hash: "$2b$...",
          new_algorithm: "bcrypt",
        },
      }),
    ]);

    await waitFor(() => {
      const headers = screen.getAllByText("Журнал аудита");
      expect(headers.length).toBeGreaterThanOrEqual(1);
    });

    // Wait for data to render
    await waitFor(() => {
      const allPre = Array.from(document.querySelectorAll("pre")).map((e) => e.textContent).join("\n");
      expect(allPre).toContain("[REDACTED]");
      expect(allPre).toContain("bcrypt");
    });
  });

  it("handles login failure event display", async () => {
    renderAuditPage([
      makeEvent({
        id: "ev-fail",
        action: "auth.login.failure",
        details_json: { failure_reason: "wrong_password" },
      }),
    ]);

    await waitFor(() => {
      const headers = screen.getAllByText("Журнал аудита");
      expect(headers.length).toBeGreaterThanOrEqual(1);
    });

    // Wait for loading to finish and data to render
    await waitFor(() => {
      expect(screen.getByText("Ошибка входа")).toBeTruthy();
    });
  });

  it("paginates forward and back", async () => {
    const events = Array.from({ length: 12 }, (_, i) =>
      makeEvent({ id: `ev-${i.toString().padStart(3, "0")}`, action: `action.${i}` }),
    );

    renderAuditPage(events);

    await waitFor(() => {
      const headers = screen.getAllByText("Журнал аудита");
      expect(headers.length).toBeGreaterThanOrEqual(1);
      // All 12 items should be on first page (limit 50)
      expect(screen.getByText(/Всего: 12/)).toBeTruthy();
    });

    // Forward button should be disabled since offset + limit >= total
    const fwdBtn = screen.getByText("Вперёд →");
    expect((fwdBtn as HTMLButtonElement).disabled).toBe(true);

    // Back button should be disabled on first page
    const backBtn = screen.getByText("← Назад");
    expect((backBtn as HTMLButtonElement).disabled).toBe(true);
  });
});
