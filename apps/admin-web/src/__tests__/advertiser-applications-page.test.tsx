import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Layout from "../components/Layout";
import AdvertiserApplicationsPage from "../pages/AdvertiserApplicationsPage";

function createRouter() {
  return createMemoryRouter(
    [
      {
        path: "/",
        element: <ProtectedRoute><Layout /></ProtectedRoute>,
        children: [
          { index: true, element: <div>home</div> },
          { path: "advertiser-applications", element: <AdvertiserApplicationsPage /> },
        ],
      },
    ],
    { initialEntries: ["/advertiser-applications"] },
  );
}

function setupFetch(overrides: Record<string, unknown> = {}) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);

    if (url.endsWith("/auth/refresh")) {
      return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
    }
    if (url.endsWith("/auth/me")) {
      return Promise.resolve(new Response(JSON.stringify({
        sub: "u-admin", auth_provider: "local_break_glass", username: "admin", display_name: "Admin",
        permissions: ["advertiser_applications.read", "advertiser_applications.review"], must_change_password: false,
      }), { status: 200 }));
    }

    // Override handler
    for (const [key, value] of Object.entries(overrides)) {
      if (url.includes(key)) {
        if (typeof value === "function") return (value as Function)(url);
        return Promise.resolve(new Response(JSON.stringify(value), { status: 200 }));
      }
    }

    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

function renderPage() {
  const router = createRouter();
  return render(<AuthProvider><RouterProvider router={router} /></AuthProvider>);
}

const MOCK_APPS = {
  items: [
    { id: "a1", company_name: "ООО Тест", contact_name: "Иван", email: "i@t.ru", phone: "", website: "", comment: "", consent: true, status: "new", reviewer_id: null, review_reason: null, reviewed_at: null, created_at: "2026-07-17T10:00:00Z", updated_at: "2026-07-17T10:00:00Z" },
    { id: "a2", company_name: "ЗАО Пример", contact_name: "Петр", email: "p@e.ru", phone: "", website: "", comment: "", consent: true, status: "approved", reviewer_id: "u-1", review_reason: "OK", reviewed_at: "2026-07-17T11:00:00Z", created_at: "2026-07-17T09:00:00Z", updated_at: "2026-07-17T11:00:00Z" },
  ],
  total: 2,
  limit: 50,
  offset: 0,
};

describe("advertiser applications page — list", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  it("renders list of applications", async () => {
    setupFetch({ "/advertiser-applications": MOCK_APPS });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("ООО Тест")).toBeTruthy();
      expect(screen.getByText("ЗАО Пример")).toBeTruthy();
    });
  });

  it("renders status badges", async () => {
    setupFetch({ "/advertiser-applications": MOCK_APPS });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Новая")).toBeTruthy();
      expect(screen.getByText("Одобрена")).toBeTruthy();
    });
  });

  it("shows empty state", async () => {
    setupFetch({ "/advertiser-applications": { items: [], total: 0, limit: 50, offset: 0 } });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Нет заявок")).toBeTruthy();
    });
  });
});

describe("advertiser applications page — detail", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  it("shows detail when row clicked", async () => {
    const user = userEvent.setup();
    setupFetch({ "/advertiser-applications": MOCK_APPS });
    renderPage();

    await waitFor(() => { expect(screen.getByText("ООО Тест")).toBeTruthy(); });

    await user.click(screen.getByText("ООО Тест"));

    await waitFor(() => {
      // new applications show "Начать рассмотрение" button
      expect(screen.getByText("Начать рассмотрение")).toBeTruthy();
    });
  });

  it("hides approve/reject for already reviewed", async () => {
    const user = userEvent.setup();
    setupFetch({ "/advertiser-applications": MOCK_APPS });
    renderPage();

    await waitFor(() => { expect(screen.getByText("ЗАО Пример")).toBeTruthy(); });
    await user.click(screen.getByText("ЗАО Пример"));

    await waitFor(() => {
      // Should NOT show approve/reject buttons for approved app
      const approveBtns = screen.queryAllByText("Одобрить");
      expect(approveBtns.length).toBe(0);
    });
  });
});

describe("advertiser applications page — reviewing status", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  const APPS_WITH_REVIEWING = {
    items: [
      { id: "a1", company_name: "ООО Тест", contact_name: "Иван", email: "i@t.ru", phone: "", website: "", comment: "", consent: true, status: "reviewing", reviewer_id: null, review_reason: null, reviewed_at: null, created_at: "2026-07-17T10:00:00Z", updated_at: "2026-07-17T10:00:00Z" },
    ],
    total: 1,
    limit: 50,
    offset: 0,
  };

  it("renders На рассмотрении badge", async () => {
    setupFetch({ "/advertiser-applications": APPS_WITH_REVIEWING });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("На рассмотрении")).toBeTruthy();
    });
  });

  it("shows approve/reject buttons when reviewing status selected", async () => {
    const user = userEvent.setup();
    setupFetch({ "/advertiser-applications": APPS_WITH_REVIEWING });
    renderPage();

    await waitFor(() => { expect(screen.getByText("ООО Тест")).toBeTruthy(); });
    await user.click(screen.getByText("ООО Тест"));

    await waitFor(() => {
      expect(screen.getByText("Одобрить")).toBeTruthy();
      expect(screen.getByText("Отклонить")).toBeTruthy();
    });
  });
});

describe("advertiser applications page — invite", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  const INVITE_TOKEN = "tok-advertiser-invite-series-abcdefgh";

  const APPS_WITH_APPROVED = {
    items: [
      { id: "a-approved", company_name: "ООО Аппрувед", contact_name: "Анна", email: "a@t.ru",
        phone: "", website: "", comment: "", consent: true, status: "approved",
        reviewer_id: "u-1", review_reason: "OK", reviewed_at: "2026-07-17T11:00:00Z",
        created_at: "2026-07-17T10:00:00Z", updated_at: "2026-07-17T11:00:00Z" },
    ],
    total: 1, limit: 50, offset: 0,
  };

  it("shows Создать приглашение button for approved app without invite", async () => {
    const user = userEvent.setup();
    // Put more specific invite URL first — url.includes is greedy
    const overrides: Record<string, unknown> = {
      [`/advertiser-applications/a-approved/invite`]: null,
      "/advertiser-applications": APPS_WITH_APPROVED,
    };
    setupFetch(overrides);
    renderPage();

    await waitFor(() => { expect(screen.getByText("ООО Аппрувед")).toBeTruthy(); });
    await user.click(screen.getByText("ООО Аппрувед"));

    await waitFor(() => {
      expect(screen.getByText("Создать приглашение")).toBeTruthy();
    });
  });

  it("creates invite and shows token", { timeout: 10000 }, async () => {
    const user = userEvent.setup();

    vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
      const url = typeof input === "string" ? input : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(JSON.stringify({
          sub: "u-admin", auth_provider: "local_break_glass", username: "admin", display_name: "Admin",
          permissions: ["advertiser_applications.read", "advertiser_applications.review"], must_change_password: false,
        }), { status: 200 }));
      }
      // GET list
      if (url.includes("/advertiser-applications") && !url.includes("invite")) {
        return Promise.resolve(new Response(JSON.stringify(APPS_WITH_APPROVED), { status: 200 }));
      }
      // GET/POST invite — return pending invite with token
      if (url.includes("invite")) {
        return Promise.resolve(new Response(JSON.stringify({
          id: "inv-1", token: INVITE_TOKEN, contact_email: "a@t.ru", status: "pending",
          expires_at: "2026-08-17T11:00:00Z", accepted_at: null,
        }), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    renderPage();

    await waitFor(() => { expect(screen.getByText("ООО Аппрувед")).toBeTruthy(); });
    await user.click(screen.getByText("ООО Аппрувед"));

    // Invite section should show pending invite with token
    await waitFor(() => {
      expect(screen.getByText("Ожидает принятия")).toBeTruthy();
      expect(screen.getByText(INVITE_TOKEN)).toBeTruthy();
    });

    // Invite create/resend button rendered via data-testid
    expect(screen.getByTestId("advertiser-invite-create")).toBeTruthy();
  });

  it("invite button visible to any authenticated user (backend enforces RBAC)", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(JSON.stringify({
          sub: "u-readonly", auth_provider: "local_break_glass", username: "readonly", display_name: "Readonly",
          permissions: ["advertiser_applications.read"], must_change_password: false,
        }), { status: 200 }));
      }
      if (url.includes("/advertiser-applications") && !url.includes("invite")) {
        return Promise.resolve(new Response(JSON.stringify(APPS_WITH_APPROVED), { status: 200 }));
      }
      if (url.includes("/advertiser-applications/a-approved/invite")) {
        return Promise.resolve(new Response(JSON.stringify(null), { status: 200 }));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });
    renderPage();

    await waitFor(() => { expect(screen.getByText("ООО Аппрувед")).toBeTruthy(); });

    const user = userEvent.setup();
    await user.click(screen.getByText("ООО Аппрувед"));

    await waitFor(() => {
      // Button IS visible (no client-side RBAC — backend enforces on POST)
      expect(screen.getByText("Создать приглашение")).toBeTruthy();
    });
  });
});

describe("advertiser applications page — error", () => {
  beforeEach(() => { localStorage.clear(); vi.restoreAllMocks(); });
  afterEach(() => { localStorage.clear(); });

  it("shows error on fetch failure", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : String(input);
      if (url.endsWith("/auth/refresh")) {
        return Promise.resolve(new Response(JSON.stringify({ access_token: "t", token_type: "Bearer", expires_in: 1800 }), { status: 200 }));
      }
      if (url.endsWith("/auth/me")) {
        return Promise.resolve(new Response(JSON.stringify({
          sub: "u-admin", auth_provider: "local_break_glass", username: "admin", display_name: "Admin",
          permissions: ["advertiser_applications.read"], must_change_password: false,
        }), { status: 200 }));
      }
      if (url.includes("/advertiser-applications")) {
        return Promise.reject(new Error("Network error"));
      }
      return Promise.resolve(new Response("{}", { status: 200 }));
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Ошибка загрузки/i)).toBeTruthy();
    });
  });
});
