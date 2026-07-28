import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import InventoryPage from "../pages/InventoryPage";

// ── Router ──

function createInventoryRouter() {
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
          { path: "inventory", element: <InventoryPage /> },
        ],
      },
    ],
    { initialEntries: ["/inventory"] },
  );
}

// ── Mock data ──

const MOCK_SURFACES = {
  items: [
    { id: "surf-1", code: "S01", store_id: "st-1", store_code: "STR01", store_name: "Магазин 1", resolution_w: 1920, resolution_h: 1080, is_active: true },
    { id: "surf-2", code: "S02", store_id: "st-2", store_code: "STR02", store_name: "Магазин 2", resolution_w: 1280, resolution_h: 720, is_active: true },
  ],
  total: 2,
  limit: 50,
  offset: 0,
};

const MOCK_STORES = {
  items: [
    { id: "st-1", code: "STR01", name: "Магазин 1", address: "ул. Ленина, 1", is_active: true, cluster_name: "Центр", branch_name: "Филиал А", surface_count: 3 },
  ],
  total: 1,
  limit: 50,
  offset: 0,
};

const MOCK_AVAILABILITY = {
  surface_id: "surf-1",
  starts_at: "2026-07-11T09:00:00Z",
  ends_at: "2026-07-11T18:00:00Z",
  all_available: true,
  total_requested: 20,
  total_available: 880,
  slots: [
    { slot_id: "slot-1", slot_date: "2026-07-11", slot_hour: 9, total_capacity: 100, booked_capacity: 0, reserved_capacity: 0, available_capacity: 100, requested_capacity: 10, available: true, sold_out: false, blocked: false },
    { slot_id: "slot-2", slot_date: "2026-07-11", slot_hour: 10, total_capacity: 100, booked_capacity: 0, reserved_capacity: 0, available_capacity: 100, requested_capacity: 10, available: true, sold_out: false, blocked: false },
  ],
  conflicts: [],
};

const MOCK_AVAILABILITY_CONFLICT = {
  surface_id: "surf-1",
  starts_at: "2026-07-11T09:00:00Z",
  ends_at: "2026-07-11T18:00:00Z",
  all_available: false,
  total_requested: 20,
  total_available: 880,
  slots: [
    { slot_id: "slot-1", slot_date: "2026-07-11", slot_hour: 9, total_capacity: 100, booked_capacity: 100, reserved_capacity: 0, available_capacity: 0, requested_capacity: 10, available: false, sold_out: true, blocked: false },
  ],
  conflicts: [
    { slot_id: "slot-1", slot_date: "2026-07-11", slot_hour: 9, total_capacity: 100, booked_capacity: 100, reserved_capacity: 0, available_capacity: 0, requested_capacity: 10, available: false, sold_out: true, blocked: false },
  ],
};

const MOCK_CONFLICTS_CLEAN = {
  has_conflicts: false,
  blocking: [],
  warnings: [],
};

const MOCK_CONFLICTS = {
  has_conflicts: true,
  blocking: [
    { conflict_type: "BLACKOUT_RULE", severity: "blocking", surface_id: "surf-1", message: "Blackout: ремонт", rule_type: "blackout", slot_date: "2026-07-11", slot_hour: 9, available_capacity: 0, requested_capacity: 10 },
  ],
  warnings: [
    { conflict_type: "SOV_OVER_100", severity: "warning", surface_id: "surf-1", message: "SOV > 100%", rule_type: null, slot_date: "2026-07-11", slot_hour: 10, available_capacity: 50, requested_capacity: 30 },
  ],
};

// ── Fetch setup ──

type FetchMock = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

function mockAuth(fetchImpl: FetchMock, perms: string[] = ["inventory.read", "inventory.manage"]) {
  // unused — the fetch mock routes by URL
}

function setupFetch(
  overrides: Partial<{
    surfaces: unknown;
    stores: unknown;
    availability: unknown;
    conflicts: unknown;
    rules: unknown;
    perms: string[];
    errorUrl: string;
    errorStatus: number;
    errorBody: unknown;
  }> = {},
) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init?) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);

    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(new Response(
        JSON.stringify({ access_token: "test-at", token_type: "Bearer", expires_in: 1800 }),
        { status: 200 },
      ));
    }

    if (url.endsWith("/auth/me")) {
      return Promise.resolve(new Response(
        JSON.stringify({
          sub: "u-admin",
          auth_provider: "local_break_glass",
          username: "admin",
          display_name: "Администратор",
          permissions: overrides.perms ?? ["inventory.read", "inventory.manage"],
          must_change_password: false,
        }),
        { status: 200 },
      ));
    }

    if (overrides.errorUrl && url.includes(overrides.errorUrl)) {
      return Promise.resolve(new Response(
        JSON.stringify(overrides.errorBody ?? { detail: "ошибка" }),
        { status: overrides.errorStatus ?? 500 },
      ));
    }

    if (url.includes("/inventory/surfaces")) {
      return Promise.resolve(new Response(JSON.stringify(overrides.surfaces ?? MOCK_SURFACES), { status: 200 }));
    }

    if (url.includes("/inventory/stores")) {
      return Promise.resolve(new Response(JSON.stringify(overrides.stores ?? MOCK_STORES), { status: 200 }));
    }

    if (url.includes("/inventory/availability")) {
      return Promise.resolve(new Response(JSON.stringify(overrides.availability ?? MOCK_AVAILABILITY), { status: 200 }));
    }

    if (url.includes("/inventory/conflicts/check")) {
      return Promise.resolve(new Response(JSON.stringify(overrides.conflicts ?? MOCK_CONFLICTS_CLEAN), { status: 200 }));
    }

    if (url.includes("/inventory/rules")) {
      return Promise.resolve(new Response(JSON.stringify(overrides.rules ?? []), { status: 200 }));
    }

    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

function renderInventory(overrides?: Parameters<typeof setupFetch>[0]) {
  setupFetch(overrides);
  const router = createInventoryRouter();
  return render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
}

beforeEach(() => { vi.restoreAllMocks(); });
afterEach(() => { vi.restoreAllMocks(); });

// ═══════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════

describe("InventoryPage — S-081 tabs", () => {
  it("renders all four tabs", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Каталог")).toBeDefined(); });
    expect(screen.getByText("Доступность")).toBeDefined();
    expect(screen.getByText("Конфликты")).toBeDefined();
    expect(screen.getByText("Правила")).toBeDefined();
  });

  it("shows catalog sub-tabs by default", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Магазины")).toBeDefined(); });
    expect(screen.getByText("Поверхности")).toBeDefined();
  });

  it("switches to availability tab on click", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Доступность")).toBeDefined(); });
    await userEvent.click(screen.getByText("Доступность"));
    expect(screen.getByText("Проверка доступности")).toBeDefined();
  });

  it("switches to conflicts tab on click", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Конфликты")).toBeDefined(); });
    await userEvent.click(screen.getByText("Конфликты"));
    expect(screen.getByText("Проверка конфликтов")).toBeDefined();
  });

  it("switches to rules tab and shows create button", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Правила")).toBeDefined(); });
    await userEvent.click(screen.getByText("Правила"));
    // Rules tab now loads from API — mock returns empty list
    await waitFor(() => { expect(screen.getByText(/Правил пока нет/)).toBeDefined(); });
    expect(screen.getByText("+ Создать")).toBeDefined();
  });

  it("hides create button without inventory.manage", async () => {
    renderInventory({ perms: ["inventory.read"] });
    await waitFor(() => { expect(screen.getByText("Правила")).toBeDefined(); });
    await userEvent.click(screen.getByText("Правила"));
    await waitFor(() => { expect(screen.getByText(/Правил пока нет/)).toBeDefined(); });
    expect(screen.queryByText("+ Создать")).toBeNull();
  });
});

describe("InventoryPage — Rules CRUD", () => {
  const MOCK_RULE = {
    id: "rule-1", scope_type: "global", scope_id: null, rule_type: "max_sov",
    priority: 17, value_json: { max_sov_percent: 35 }, is_active: true,
    starts_at: "2026-12-01T00:00:00Z", ends_at: "2026-12-31T00:00:00Z",
    created_at: "2026-07-27T00:00:00Z", updated_at: "2026-07-27T00:00:00Z",
  };

  it("shows create form with required fields", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Правила")).toBeDefined(); });
    await userEvent.click(screen.getByText("Правила"));
    await waitFor(() => { expect(screen.getByText("+ Создать")).toBeDefined(); });
    await userEvent.click(screen.getByText("+ Создать"));

    await waitFor(() => {
      expect(screen.getByTestId("inventory-rule-form")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-type")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-scope-type")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-priority")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-active")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-starts-at")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-ends-at")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-value")).toBeDefined();
      expect(screen.getByTestId("inventory-rule-submit")).toBeDefined();
    });
  });

  it("creates rule and shows success + row", async () => {
    // Use renderInventory with rules pre-populated (empty on load, then rule after create)
    let rulesCalled = 0;
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init?) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(JSON.stringify({
          sub: "u-admin", auth_provider: "local_break_glass", username: "admin", display_name: "Admin",
          permissions: ["inventory.read", "inventory.manage"], must_change_password: false,
        }), { status: 200 }));
      }
      if (url.includes("/inventory/stores")) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_STORES), { status: 200 }));
      }
      if (url.includes("/inventory/surfaces")) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_SURFACES), { status: 200 }));
      }
      if (url.includes("/inventory/rules") && init?.method === "POST") {
        return Promise.resolve(new Response(JSON.stringify(MOCK_RULE), { status: 201 }));
      }
      if (url.includes("/inventory/rules")) {
        rulesCalled++;
        const data = rulesCalled >= 2 ? [MOCK_RULE] : [];
        return Promise.resolve(new Response(JSON.stringify(data), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const router = createInventoryRouter();
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Правила")).toBeDefined(); });
    await userEvent.click(screen.getByText("Правила"));
    await waitFor(() => { expect(screen.getByText("+ Создать")).toBeDefined(); });
    await userEvent.click(screen.getByText("+ Создать"));

    // Select max_sov
    await userEvent.selectOptions(screen.getByTestId("inventory-rule-type"), "max_sov");
    // Fill value
    const valInput = screen.getByTestId("inventory-rule-value");
    await userEvent.clear(valInput);
    await userEvent.type(valInput, "35");
    // Set priority
    const priInput = screen.getByTestId("inventory-rule-priority");
    await userEvent.clear(priInput);
    await userEvent.type(priInput, "17");

    await userEvent.click(screen.getByTestId("inventory-rule-submit"));

    // Success banner
    await waitFor(() => {
      expect(screen.getByTestId("inventory-rule-success")).toBeDefined();
    });

    // Row created
    await waitFor(() => {
      const row = screen.getByTestId("inventory-rule-row-rule-1");
      expect(row).toBeDefined();
      expect(screen.getByTestId("inventory-rule-row-type-rule-1").textContent).toContain("Макс. доля показов");
      expect(screen.getByTestId("inventory-rule-row-value-rule-1").textContent).toContain("35%");
      expect(screen.getByTestId("inventory-rule-row-priority-rule-1").textContent).toContain("17");
    });
  });

  it("shows human-readable error on save failure", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input, init?) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(JSON.stringify({
          sub: "u-admin", auth_provider: "local_break_glass", username: "admin", display_name: "Admin",
          permissions: ["inventory.read", "inventory.manage"], must_change_password: false,
        }), { status: 200 }));
      }
      if (url.includes("/inventory/stores")) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_STORES), { status: 200 }));
      }
      if (url.includes("/inventory/surfaces")) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_SURFACES), { status: 200 }));
      }
      if (url.includes("/inventory/rules") && init?.method === "POST") {
        return Promise.resolve(new Response(JSON.stringify({ detail: "Duplicate rule" }), { status: 409 }));
      }
      if (url.includes("/inventory/rules")) {
        return Promise.resolve(new Response(JSON.stringify([]), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const router = createInventoryRouter();
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Правила")).toBeDefined(); });
    await userEvent.click(screen.getByText("Правила"));
    await waitFor(() => { expect(screen.getByText("+ Создать")).toBeDefined(); });
    await userEvent.click(screen.getByText("+ Создать"));

    await userEvent.click(screen.getByTestId("inventory-rule-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("inventory-rule-error")).toBeDefined();
    });

    const body = document.body.textContent || "";
    expect(body).not.toContain("[object Object]");
  });
});

describe("InventoryPage — Availability tab", () => {
  it("shows empty state before check", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Доступность")).toBeDefined(); });
    await userEvent.click(screen.getByText("Доступность"));
    await waitFor(() => {
      expect(screen.getByText(/нажмите «Проверить доступность»/)).toBeDefined();
    });
  });

  it("loads surface list into selector", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Доступность")).toBeDefined(); });
    await userEvent.click(screen.getByText("Доступность"));
    await waitFor(() => {
      expect(screen.getByText("S01 (Магазин 1)")).toBeDefined();
      expect(screen.getByText("S02 (Магазин 2)")).toBeDefined();
    });
  });

  it("shows availability result on successful check", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Доступность")).toBeDefined(); });
    await userEvent.click(screen.getByText("Доступность"));
    await waitFor(() => { expect(screen.getByText("S01 (Магазин 1)")).toBeDefined(); });

    // Select surface and submit
    const select = screen.getByLabelText("Поверхность");
    await userEvent.selectOptions(select, "surf-1");

    await userEvent.click(screen.getByRole("button", { name: /Проверить доступность/ }));

    await waitFor(() => {
      const availableEls = screen.getAllByText("Доступно");
      expect(availableEls.length).toBeGreaterThan(0);
      expect(screen.getByText("Слоты")).toBeDefined();
    });
  });

  it("shows slot grid with correct data", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Доступность")).toBeDefined(); });
    await userEvent.click(screen.getByText("Доступность"));
    await waitFor(() => { expect(screen.getByText("S01 (Магазин 1)")).toBeDefined(); });

    await userEvent.selectOptions(document.getElementById("av-surface")!, "surf-1");
    await userEvent.click(screen.getByRole("button", { name: /Проверить доступность/ }));

    await waitFor(() => {
      expect(screen.getByText("Слоты")).toBeDefined();
      expect(screen.getAllByText("2026-07-11").length).toBeGreaterThanOrEqual(1);
    });
  });

  it("shows conflict results when conflicts exist", async () => {
    renderInventory({ availability: MOCK_AVAILABILITY_CONFLICT });
    await waitFor(() => { expect(screen.getByText("Доступность")).toBeDefined(); });
    await userEvent.click(screen.getByText("Доступность"));
    await waitFor(() => { expect(screen.getByText("S01 (Магазин 1)")).toBeDefined(); });

    await userEvent.selectOptions(document.getElementById("av-surface")!, "surf-1");
    await userEvent.click(screen.getByRole("button", { name: /Проверить доступность/ }));

    await waitFor(() => {
      const conflictHeadings = screen.getAllByText(/^Конфликты/);
      expect(conflictHeadings.length).toBeGreaterThan(0);
      expect(screen.getByText("Недоступно")).toBeDefined();
    });
  });

  it("shows error on API failure", async () => {
    renderInventory({
      availability: {},
      errorUrl: "/inventory/availability",
      errorStatus: 500,
      errorBody: { detail: "внутренняя ошибка" },
    });
    await waitFor(() => { expect(screen.getByText("Доступность")).toBeDefined(); });
    await userEvent.click(screen.getByText("Доступность"));
    await waitFor(() => { expect(screen.getByText("S01 (Магазин 1)")).toBeDefined(); });

    await userEvent.selectOptions(document.getElementById("av-surface")!, "surf-1");
    await userEvent.click(screen.getByRole("button", { name: /Проверить доступность/ }));

    await waitFor(() => {
      expect(screen.getByText("внутренняя ошибка")).toBeDefined();
    });
  });
});

describe("InventoryPage — Conflicts tab", () => {
  it("shows no conflicts message when clean", async () => {
    renderInventory({ conflicts: MOCK_CONFLICTS_CLEAN });
    await waitFor(() => { expect(screen.getByText("Конфликты")).toBeDefined(); });
    await userEvent.click(screen.getByText("Конфликты"));
    await waitFor(() => { expect(screen.getByText("S01 (Магазин 1)")).toBeDefined(); });

    await userEvent.selectOptions(document.getElementById("cf-surface")!, "surf-1");
    await userEvent.click(screen.getByRole("button", { name: /Проверить конфликты/ }));

    await waitFor(() => {
      expect(screen.getByText("Конфликтов не обнаружено.")).toBeDefined();
    });
  });

  it("shows blocking conflicts when present", async () => {
    renderInventory({ conflicts: MOCK_CONFLICTS });
    await waitFor(() => { expect(screen.getByText("Конфликты")).toBeDefined(); });
    await userEvent.click(screen.getByText("Конфликты"));
    await waitFor(() => { expect(screen.getByText("S01 (Магазин 1)")).toBeDefined(); });

    await userEvent.selectOptions(document.getElementById("cf-surface")!, "surf-1");
    await userEvent.click(screen.getByRole("button", { name: /Проверить конфликты/ }));

    await waitFor(() => {
      expect(screen.getByText("Блокирующие конфликты")).toBeDefined();
      expect(screen.getByText("BLACKOUT_RULE")).toBeDefined();
      expect(screen.getByText(/ремонт/)).toBeDefined();
    });
  });

  it("shows warnings when present", async () => {
    renderInventory({ conflicts: MOCK_CONFLICTS });
    await waitFor(() => { expect(screen.getByText("Конфликты")).toBeDefined(); });
    await userEvent.click(screen.getByText("Конфликты"));
    await waitFor(() => { expect(screen.getByText("S01 (Магазин 1)")).toBeDefined(); });

    await userEvent.selectOptions(document.getElementById("cf-surface")!, "surf-1");
    await userEvent.click(screen.getByRole("button", { name: /Проверить конфликты/ }));

    await waitFor(() => {
      expect(screen.getByText("Предупреждения")).toBeDefined();
      expect(screen.getByText("SOV_OVER_100")).toBeDefined();
    });
  });
});

describe("InventoryPage — catalog", () => {
  it("renders stores table", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Каталог")).toBeDefined(); });
    // Default sub-tab is stores
    await waitFor(() => {
      expect(screen.getByText("STR01")).toBeDefined();
      expect(screen.getByText("Магазин 1")).toBeDefined();
    });
  });

  it("switches to surfaces sub-tab", async () => {
    renderInventory();
    await waitFor(() => { expect(screen.getByText("Поверхности")).toBeDefined(); });
    await userEvent.click(screen.getByText("Поверхности"));
    await waitFor(() => {
      expect(screen.getByText("S01")).toBeDefined();
      expect(screen.getByText("1920×1080")).toBeDefined();
    });
  });
});

describe("InventoryPage — permission-filtered menu", () => {
  it("shows inventory nav link with inventory.read permission", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "test-at", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(
          JSON.stringify({
            sub: "u-admin", auth_provider: "local_break_glass", username: "admin",
            display_name: "Администратор", permissions: ["inventory.read"],
            must_change_password: false,
          }),
          { status: 200 },
        ));
      }
      if (url.includes("/inventory/stores")) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_STORES), { status: 200 }));
      }
      if (url.includes("/inventory/surfaces")) {
        return Promise.resolve(new Response(JSON.stringify(MOCK_SURFACES), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const router = createInventoryRouter();
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => {
      const navLinks = screen.getAllByText("Инвентарь");
      expect(navLinks.length).toBeGreaterThan(0);
    });
  });

  it("does NOT show inventory link without permission (falls to login)", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(
          JSON.stringify({ access_token: "test-at", token_type: "Bearer", expires_in: 1800 }),
          { status: 200 },
        ));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(
          JSON.stringify({
            sub: "u-viewer", auth_provider: "local", username: "viewer",
            display_name: "Зритель", permissions: ["campaigns.read"],
            must_change_password: false,
          }),
          { status: 200 },
        ));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    const router = createMemoryRouter(
      [
        {
          path: "/",
          element: (<ProtectedRoute><Layout /></ProtectedRoute>),
          children: [{ index: true, element: <div>home</div> }],
        },
      ],
      { initialEntries: ["/"] },
    );
    render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("ЦУР")).toBeDefined(); });
    // "Инвентарь" should NOT be in the nav
    expect(screen.queryByText("Инвентарь")).toBeNull();
  });
});

describe("InventoryPage — no storage secrets", () => {
  it("does not render storage_bucket or storage_key in any output", async () => {
    setupFetch({});
    const router = createInventoryRouter();
    const { container } = render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);

    await waitFor(() => { expect(screen.getByText("Каталог")).toBeDefined(); });

    const html = container.innerHTML;
    expect(html).not.toContain("storage_bucket");
    expect(html).not.toContain("storage_key");
    expect(html).not.toContain("presigned_url");
    expect(html).not.toContain("access_token");
  });
});
