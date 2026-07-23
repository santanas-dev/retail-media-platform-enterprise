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
import CreativeModerationPage from "../pages/CreativeModerationPage";

// ── Helpers ──

function createRouter(initialRoute: string) {
  return createMemoryRouter(
    [
      {
        path: "/login",
        element: <div>Login</div>,
      },
      {
        path: "/",
        element: (
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        ),
        children: [
          { path: "creatives/moderation", element: <CreativeModerationPage /> },
        ],
      },
    ],
    { initialEntries: [initialRoute] },
  );
}

const SEED_QUEUE = {
  items: [
    {
      id: "ca-1",
      advertiser_organization_id: "org-1",
      code: "CR-001",
      name: "Баннер 1200x628",
      media_type: "image/jpeg",
      file_size_bytes: 245760,
      duration_ms: null,
      resolution_w: 1200,
      resolution_h: 628,
      status: "ready",
      moderation_status: "pending_review",
      moderation_notes: null,
      created_at: "2026-07-01T10:00:00Z",
      updated_at: "2026-07-01T10:00:00Z",
      advertiser_name: "ООО Ромашка",
      advertiser_code: "ADV-001",
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const EMPTY_QUEUE = { items: [], total: 0, limit: 50, offset: 0 };

function mockAllFetches(
  overrides?: Record<string, (input: string, init?: RequestInit) => Promise<Response>>,
  userPerms?: string[],
) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (overrides) {
      for (const [key, fn] of Object.entries(overrides)) {
        if (url.includes(key)) return fn(url, init);
      }
    }
    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
        { status: 200 },
      ));
    }
    if (url.endsWith("/me")) {
      const userData: Record<string, unknown> = { sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin" };
      if (userPerms) userData.permissions = userPerms;
      return Promise.resolve(new Response(JSON.stringify(userData), { status: 200 }));
    }
    if (url.includes("moderation-queue")) {
      return Promise.resolve(new Response(JSON.stringify(SEED_QUEUE), { status: 200 }));
    }
    return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
  });
}

// ── Tests ──

describe("CreativeModerationPage — S-036", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  // ── Render states ──

  it("renders page with title and filters", async () => {
    mockAllFetches();
    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByText("Модерация креативов")).toBeTruthy();
    });
    // All filter buttons visible
    expect(screen.getByTestId("moderation-filter-pending_review")).toBeTruthy();
    expect(screen.getByTestId("moderation-filter-approved")).toBeTruthy();
    expect(screen.getByTestId("moderation-filter-rejected")).toBeTruthy();
    expect(screen.getByTestId("moderation-filter-all")).toBeTruthy();
  });

  it("renders queue with a pending item", async () => {
    mockAllFetches();
    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-row-CR-001")).toBeTruthy();
    });
    // Status is pending
    expect(screen.getByTestId("moderation-status-CR-001").textContent).toContain("На проверке");
    // Approve + Reject buttons visible
    expect(screen.getByTestId("moderation-approve-CR-001")).toBeTruthy();
    expect(screen.getByTestId("moderation-reject-CR-001")).toBeTruthy();
  });

  it("shows empty state when queue is empty", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/me")) {
        return Promise.resolve(new Response(JSON.stringify({ sub: "u1", auth_provider: "ad", username: "admin", display_name: "Admin", permissions: ["creatives.moderate"] }), { status: 200 }));
      }
      if (url.includes("moderation-queue")) {
        return Promise.resolve(new Response(JSON.stringify(EMPTY_QUEUE), { status: 200 }));
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-empty")).toBeTruthy();
    });
    expect(screen.getByTestId("moderation-empty").textContent).toContain("Очередь пуста");
  });

  // ── Approve flow ──

  it("approves a creative and refreshes list", async () => {
    let approveCalled = false;

    mockAllFetches(
      {
        "/creative-assets/ca-1/approve": () => {
          approveCalled = true;
          return Promise.resolve(new Response(
            JSON.stringify({ asset_id: "ca-1", moderation_status: "approved", message: "Креатив одобрен" }),
            { status: 200 },
          ));
        },
      },
      ["creatives.moderate"],
    );

    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-approve-CR-001")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("moderation-approve-CR-001"));

    await waitFor(() => {
      expect(approveCalled).toBe(true);
    });
  });

  // ── Reject flow: open modal, type reason, confirm ──

  it("opens reject input and shows cancel/confirm buttons", async () => {
    mockAllFetches(undefined, ["creatives.moderate"]);
    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-reject-CR-001")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("moderation-reject-CR-001"));

    await waitFor(() => {
      expect(screen.getByTestId("moderation-reject-reason-CR-001")).toBeTruthy();
    });
    expect(screen.getByTestId("moderation-reject-confirm-CR-001")).toBeTruthy();
    expect(screen.getByTestId("moderation-reject-cancel-CR-001")).toBeTruthy();
    // Confirm button should be disabled without reason text
    expect((screen.getByTestId("moderation-reject-confirm-CR-001") as HTMLButtonElement).disabled).toBe(true);
  });

  it("rejects a creative with reason", async () => {
    let rejectCalled = false;
    let rejectBody: unknown = null;

    mockAllFetches(
      {
        "/creative-assets/ca-1/reject": (_url, init) => {
          rejectCalled = true;
          rejectBody = JSON.parse(init?.body as string);
          return Promise.resolve(new Response(
            JSON.stringify({ asset_id: "ca-1", moderation_status: "rejected", message: "Креатив отклонён" }),
            { status: 200 },
          ));
        },
      },
      ["creatives.moderate"],
    );

    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-reject-CR-001")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("moderation-reject-CR-001"));

    await waitFor(() => {
      expect(screen.getByTestId("moderation-reject-reason-CR-001")).toBeTruthy();
    });

    // Type reason
    await user.type(screen.getByTestId("moderation-reject-reason-CR-001"), "Не соответствует брендбуку");

    // Confirm button should now be enabled
    await waitFor(() => {
      expect((screen.getByTestId("moderation-reject-confirm-CR-001") as HTMLButtonElement).disabled).toBe(false);
    });

    await user.click(screen.getByTestId("moderation-reject-confirm-CR-001"));

    await waitFor(() => {
      expect(rejectCalled).toBe(true);
      expect((rejectBody as Record<string, string>).reason).toBe("Не соответствует брендбуку");
    });
  });

  it("cancels reject and returns to approve/reject buttons", async () => {
    mockAllFetches(undefined, ["creatives.moderate"]);
    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-reject-CR-001")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("moderation-reject-CR-001"));

    await waitFor(() => {
      expect(screen.getByTestId("moderation-reject-reason-CR-001")).toBeTruthy();
    });

    // Click cancel
    await user.click(screen.getByTestId("moderation-reject-cancel-CR-001"));

    // Back to approve/reject buttons
    await waitFor(() => {
      expect(screen.getByTestId("moderation-approve-CR-001")).toBeTruthy();
    });
    // Reject reason input should be gone
    expect(screen.queryByTestId("moderation-reject-reason-CR-001")).toBeNull();
  });

  // ── Error states ──

  it("shows error when approve fails", async () => {
    mockAllFetches(
      {
        "/creative-assets/ca-1/approve": () => {
          return Promise.resolve(new Response(
            JSON.stringify({ detail: "Failed to approve creative asset" }),
            { status: 409 },
          ));
        },
      },
      ["creatives.moderate"],
    );

    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-approve-CR-001")).toBeTruthy();
    });

    const user = userEvent.setup();
    await user.click(screen.getByTestId("moderation-approve-CR-001"));

    await waitFor(() => {
      expect(screen.getByTestId("moderation-action-error")).toBeTruthy();
    });
  });

  it("shows 403 message when missing permission", async () => {
    // Mock without creatives.moderate permission
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "valid-token", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/me")) {
        // No creatives.moderate in permissions
        return Promise.resolve(new Response(JSON.stringify({ sub: "u1", auth_provider: "ad", username: "operator", display_name: "Operator", permissions: ["campaigns.read"] }), { status: 200 }));
      }
      if (url.includes("moderation-queue")) {
        return Promise.resolve(new Response(
          JSON.stringify({ detail: "Нет доступа к модерации креативов" }),
          { status: 403 },
        ));
      }
      return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
    });

    const router = createRouter("/creatives/moderation");
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      expect(screen.getByTestId("moderation-error")).toBeTruthy();
    });
    expect(screen.getByTestId("moderation-error").textContent).toContain("Нет доступа");
  });
});
