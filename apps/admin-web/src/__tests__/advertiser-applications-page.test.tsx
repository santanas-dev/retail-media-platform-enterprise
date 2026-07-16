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
      expect(screen.getByText("Одобрить")).toBeTruthy();
      expect(screen.getByText("Отклонить")).toBeTruthy();
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
