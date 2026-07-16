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
import EmergencyPage from "../pages/EmergencyPage";

// ── Router factory ──

function createEmergencyRouter() {
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
          { path: "emergency", element: <EmergencyPage /> },
        ],
      },
    ],
    { initialEntries: ["/emergency"] },
  );
}

// ── Mock helpers ──

type FetchMock = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

function mockSession(mockFn: FetchMock, perms: string[] = ["emergency.read", "emergency.manage"]) {
  // /auth/refresh
  mockFn; // unused — setup via global fetch mock below
}

function renderEmergencyPage(statusResponse: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init?) => {
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
        new Response(
          JSON.stringify({
            sub: "u-admin",
            auth_provider: "local_break_glass",
            username: "admin",
            display_name: "Администратор",
            permissions: ["emergency.read", "emergency.manage"],
            must_change_password: false,
          }),
          { status: 200 },
        ),
      );
    }

    if (url.includes("/emergency/status")) {
      return Promise.resolve(
        new Response(JSON.stringify(statusResponse), { status: 200 }),
      );
    }

    if (url.includes("/emergency/activate")) {
      return Promise.resolve(
        new Response(JSON.stringify({ active: true, reason: "OK", activated_by: "u-admin", activated_at: "2026-07-16T12:00:00Z" }), { status: 200 }),
      );
    }

    if (url.includes("/emergency/deactivate")) {
      return Promise.resolve(
        new Response(JSON.stringify({ active: false }), { status: 200 }),
      );
    }

    return Promise.resolve(new Response("{}", { status: 200 }));
  });

  const router = createEmergencyRouter();
  return render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

// ── Inactive status helper ──

const INACTIVE_STATUS = { active: false };

// ── Active status helper ──

const ACTIVE_STATUS = {
  active: true,
  reason: "Технические работы",
  activated_by: "u-1",
  activated_at: "2026-07-16T12:00:00Z",
};

// ── Tests ──

describe("emergency page — inactive", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders inactive status badge", async () => {
    renderEmergencyPage(INACTIVE_STATUS);

    await waitFor(() => {
      expect(screen.getByText("НЕ АКТИВЕН")).toBeTruthy();
    });
  });

  it("renders activate button with reason textarea", async () => {
    renderEmergencyPage(INACTIVE_STATUS);

    await waitFor(() => {
      expect(screen.getByText("Активировать аварийный режим")).toBeTruthy();
    });

    // textarea for reason
    const textarea = screen.getByPlaceholderText("Опишите причину включения аварийного режима");
    expect(textarea).toBeTruthy();
  });

  it("activate button disabled when reason is empty", async () => {
    renderEmergencyPage(INACTIVE_STATUS);

    await waitFor(() => {
      const btn = screen.getByText("Активировать аварийный режим");
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    });
  });

  it("does not show active warning when inactive", async () => {
    renderEmergencyPage(INACTIVE_STATUS);

    await waitFor(() => {
      expect(screen.getByText("НЕ АКТИВЕН")).toBeTruthy();
    });

    // The warning about active mode should not be present
    const warnings = screen.queryAllByText(/аварийный режим активен/i);
    expect(warnings.length).toBe(0);
  });
});

describe("emergency page — active", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("renders active status badge with reason and activator", async () => {
    renderEmergencyPage(ACTIVE_STATUS);

    await waitFor(() => {
      expect(screen.getByText("АКТИВЕН")).toBeTruthy();
      expect(screen.getByText("Технические работы")).toBeTruthy();
      expect(screen.getByText("u-1")).toBeTruthy();
    });
  });

  it("renders active warning", async () => {
    renderEmergencyPage(ACTIVE_STATUS);

    await waitFor(() => {
      const warning = screen.getByText(/аварийный режим активен/i);
      expect(warning).toBeTruthy();
    });
  });

  it("renders deactivate button", async () => {
    renderEmergencyPage(ACTIVE_STATUS);

    await waitFor(() => {
      expect(screen.getByText("Деактивировать аварийный режим")).toBeTruthy();
    });
  });

  it("deactivate button disabled when reason is empty", async () => {
    renderEmergencyPage(ACTIVE_STATUS);

    await waitFor(() => {
      const btn = screen.getByText("Деактивировать аварийный режим");
      expect((btn as HTMLButtonElement).disabled).toBe(true);
    });
  });

  it("does not show activate form when active", async () => {
    renderEmergencyPage(ACTIVE_STATUS);

    await waitFor(() => {
      expect(screen.getByText("АКТИВЕН")).toBeTruthy();
    });

    // The activate button should not be present
    const activateBtns = screen.queryAllByText("Активировать аварийный режим");
    expect(activateBtns.length).toBe(0);
  });
});

describe("emergency page — confirmation flow", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("shows confirmation step when activate button is clicked", async () => {
    const user = userEvent.setup();
    renderEmergencyPage(INACTIVE_STATUS);

    await waitFor(() => {
      expect(screen.getByText("Активировать аварийный режим")).toBeTruthy();
    });

    // Type reason first
    const textarea = screen.getByPlaceholderText("Опишите причину включения аварийного режима");
    await user.type(textarea, "Тестовая причина");

    // Click activate
    const btn = screen.getByText("Активировать аварийный режим");
    await user.click(btn);

    // Confirmation should appear
    await waitFor(() => {
      expect(screen.getByText("Подтвердите активацию:")).toBeTruthy();
      expect(screen.getByText("Да, активировать")).toBeTruthy();
      expect(screen.getByText("Отмена")).toBeTruthy();
    });
  });

  it("shows player-side limitation notice", async () => {
    renderEmergencyPage(INACTIVE_STATUS);

    await waitFor(() => {
      const notice = screen.getByText(/Player-side enforcement/i);
      expect(notice).toBeTruthy();
    });
  });
});

describe("emergency page — error handling", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    localStorage.clear();
  });

  it("shows error message on fetch failure", async () => {
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
          new Response(
            JSON.stringify({
              sub: "u-admin",
              auth_provider: "local_break_glass",
              username: "admin",
              display_name: "Администратор",
              permissions: ["emergency.read", "emergency.manage"],
              must_change_password: false,
            }),
            { status: 200 },
          ),
        );
      }

      if (url.includes("/emergency/status")) {
        return Promise.reject(new Error("Network error"));
      }

      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const router = createEmergencyRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    await waitFor(() => {
      // EmergencyPage uses e.message for Error instances, "Ошибка загрузки" for non-Error
      const errorEl = screen.getByText(/Network error/i);
      expect(errorEl).toBeTruthy();
    });
  });
});
