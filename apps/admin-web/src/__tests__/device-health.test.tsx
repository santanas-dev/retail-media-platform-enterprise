import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  createMemoryRouter,
  RouterProvider,
} from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { ThemeProvider } from "../theme/ThemeContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import DeviceHealthPage from "../pages/DeviceHealthPage";

// ── Helpers ──

function createDeviceRouter() {
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
          { path: "devices", element: <DeviceHealthPage /> },
        ],
      },
    ],
    { initialEntries: ["/devices"] },
  );
}

const MOCK_DEVICE = {
  id: "00000000-0000-0000-0000-000000000201",
  store_id: "00000000-0000-0000-0000-000000000100",
  device_type_id: "00000000-0000-0000-0000-000000000010",
  code: "KSO-001",
  serial_number: "SN-KSO-TEST-001",
  os_version: "Linux 6.8",
  ip_address: "10.0.0.5",
  status: "active",
  health_state: "healthy",
  last_seen_at: "2026-07-20T12:00:00+03:00",
  last_heartbeat_at: "2026-07-20T12:00:00+03:00",
  runtime_version: "rmp-runtime/1.2.3",
  player_version: "kso-player/4.5.6",
  current_manifest_id: "00000000-0000-0000-0000-000000000301",
  cache_size_bytes: 1048576,
  retailer_id: "00000000-0000-0000-0000-000000000001",
  created_at: "2026-01-01T00:00:00+03:00",
  updated_at: "2026-07-20T12:00:00+03:00",
};

function setupFetch(devices: unknown[] = [MOCK_DEVICE], summary = { total: 1, active: 1, inactive: 0, error: 0, unregistered: 0 }) {
  let refreshCalled = false;
  const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
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
            permissions: ["devices.read"],
            must_change_password: false,
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/devices/summary")) {
      return Promise.resolve(
        new Response(JSON.stringify(summary), { status: 200 }),
      );
    }
    if (url.includes("/devices")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({
            items: devices,
            total: devices.length,
            limit: 50,
            offset: 0,
          }),
          { status: 200 },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });
  return fetchSpy;
}

function setupFetchError(status: number, message: string) {
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
            permissions: ["devices.read"],
            must_change_password: false,
          }),
          { status: 200 },
        ),
      );
    }
    if (url.includes("/devices")) {
      return Promise.resolve(
        new Response(
          JSON.stringify({ detail: message }),
          { status },
        ),
      );
    }
    return Promise.resolve(new Response(JSON.stringify({}), { status: 200 }));
  });
}

function renderDevicePage() {
  const router = createDeviceRouter();
  return render(<RouterProvider router={router} />, {
    wrapper: ({ children }) => <ThemeProvider>
      <AuthProvider>{children}</AuthProvider>
    </ThemeProvider>,
  });
}

// ── Tests ──

describe("DeviceHealthPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the device table with health columns", async () => {
    setupFetch();
    renderDevicePage();

    await waitFor(() => {
      expect(screen.getByTestId("device-health-table")).toBeInTheDocument();
    });

    expect(screen.getByTestId("device-health-row-KSO-001")).toBeInTheDocument();
    expect(screen.getByTestId("device-health-state-KSO-001")).toHaveTextContent("Здоров");
  });

  it("shows health badge with correct label for degraded", async () => {
    setupFetch([{ ...MOCK_DEVICE, health_state: "degraded" }]);
    renderDevicePage();

    await waitFor(() => {
      expect(screen.getByTestId("device-health-state-KSO-001")).toHaveTextContent("Деградация");
    });
  });

  it("shows health badge for unhealthy", async () => {
    setupFetch([{ ...MOCK_DEVICE, health_state: "unhealthy" }]);
    renderDevicePage();

    await waitFor(() => {
      expect(screen.getByTestId("device-health-state-KSO-001")).toHaveTextContent("Нездоров");
    });
  });

  it("shows runtime and player versions", async () => {
    setupFetch();
    renderDevicePage();

    await waitFor(() => {
      expect(screen.getByTestId("device-health-runtime-version-KSO-001")).toHaveTextContent("rmp-runtime/1.2.3");
      expect(screen.getByTestId("device-health-player-version-KSO-001")).toHaveTextContent("kso-player/4.5.6");
    });
  });

  it("shows last heartbeat", async () => {
    setupFetch();
    renderDevicePage();

    await waitFor(() => {
      const hb = screen.getByTestId("device-health-last-heartbeat-KSO-001");
      expect(hb).toBeInTheDocument();
      expect(hb.textContent).toContain("2026");
    });
  });

  it("shows empty state when no devices", async () => {
    setupFetch([]);
    renderDevicePage();

    await waitFor(() => {
      expect(screen.getByTestId("device-health-empty")).toBeInTheDocument();
    });
  });

  it("shows loading state initially", async () => {
    // Defer response so loading state stays visible
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(
          new Response(JSON.stringify({ access_token: "test-at", token_type: "Bearer", expires_in: 1800 }), { status: 200 }),
        );
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(
          new Response(JSON.stringify({
            sub: "u-admin", auth_provider: "local_break_glass", username: "admin",
            display_name: "Администратор", permissions: ["devices.read"], must_change_password: false,
          }), { status: 200 }),
        );
      }
      // Never resolve — loading stays
      return new Promise(() => {});
    });

    renderDevicePage();

    const loading = await screen.findByTestId("device-health-loading");
    expect(loading).toBeInTheDocument();
  });

  it("shows error state with human-readable message", async () => {
    setupFetchError(500, "Internal server error");
    renderDevicePage();

    await waitFor(() => {
      const errorEl = screen.getByTestId("device-health-error");
      expect(errorEl).toBeInTheDocument();
      // Must NOT contain [object Object]
      expect(errorEl.textContent).not.toContain("[object Object]");
      expect(errorEl.textContent).not.toBe("");
    });
  });

  it("shows summary cards", async () => {
    setupFetch([MOCK_DEVICE], { total: 1, active: 1, inactive: 0, error: 0, unregistered: 0 });
    renderDevicePage();

    await waitFor(() => {
      expect(screen.getByText("Всего")).toBeInTheDocument();
    });
    // "1" appears in both "Всего" and "Активны" — multiple matches is expected
    const ones = screen.getAllByText("1");
    expect(ones.length).toBeGreaterThanOrEqual(2);
  });
});
