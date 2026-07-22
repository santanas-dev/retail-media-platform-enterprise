import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";
import userEvent from "@testing-library/user-event";
import AdvertisersPage from "../pages/AdvertisersPage";
import { AuthProvider } from "../auth/AuthContext";

const SEED_ORGS = [
  { id: "org-1", code: "ADV-001", display_name: "Рекламный Альянс", legal_name: "ООО «Рекламный Альянс»", retailer_id: "r-1", status: "active", created_at: "2026-01-01T00:00:00Z", updated_at: null, retailers: null },
];
const SEED_ORGS_EMPTY: typeof SEED_ORGS = [];

const SEED_DETAIL = {
  id: "org-1", code: "ADV-001", display_name: "Рекламный Альянс", legal_name: "ООО «Рекламный Альянс»", retailer_id: "r-1", status: "active", created_at: "2026-01-01T00:00:00Z", updated_at: null, retailers: null,
};

function createRouter(path = "/advertisers") {
  return createMemoryRouter(
    [{ path: "/advertisers", element: <AdvertisersPage /> }],
    { initialEntries: [path] },
  );
}

describe("AdvertisersPage — view flow", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("clicking org row loads detail panel with code and name", async () => {
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
            permissions: ["advertisers.read", "advertisers.manage"] }),
          { status: 200 },
        );
      }
      if (url.includes("/advertiser-organizations?") || url.endsWith("/advertiser-organizations")) {
        // Distinguish list vs detail
        if (url.includes("org-1") && !url.includes("advertiser-organizations/org-1") === false) {
          // List
          return new Response(JSON.stringify(SEED_ORGS), { status: 200 });
        }
      }
      if (url.endsWith("/advertiser-organizations")) {
        return new Response(JSON.stringify(SEED_ORGS), { status: 200 });
      }
      if (url.includes("/advertiser-organizations/org-1")) {
        return new Response(JSON.stringify(SEED_DETAIL), { status: 200 });
      }
      if (url.includes("/advertiser-brands-by-org")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-contracts-by-org")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-contacts-by-org")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-brands?") || url.endsWith("/advertiser-brands")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-contracts?") || url.endsWith("/advertiser-contracts")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("memberships")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      return new Response(JSON.stringify([]), { status: 200 });
    });

    const router = createRouter();
    render(
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>,
    );

    // Wait for org list to load
    await waitFor(() => {
      expect(screen.getByTestId("advertiser-org-row")).toBeTruthy();
    });

    // Click the row
    await user.click(screen.getByTestId("advertiser-org-row"));

    // Detail panel should appear
    await waitFor(() => {
      expect(screen.getByTestId("advertiser-detail-panel")).toBeTruthy();
    });

    // Code and name should be visible
    await waitFor(() => {
      expect(screen.getByTestId("advertiser-detail-code")).toBeTruthy();
      expect(screen.getByTestId("advertiser-detail-display-name")).toBeTruthy();
    });

    expect(screen.getByTestId("advertiser-detail-code").textContent).toBe("ADV-001");
    expect(screen.getByTestId("advertiser-detail-display-name").textContent).toBe("Рекламный Альянс");
  });

  it("users tab shows empty state for org with no users", async () => {
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
            permissions: ["advertisers.read"] }),
          { status: 200 },
        );
      }
      if (url.endsWith("/advertiser-organizations")) {
        return new Response(JSON.stringify(SEED_ORGS), { status: 200 });
      }
      if (url.includes("/advertiser-organizations/org-1")) {
        return new Response(JSON.stringify(SEED_DETAIL), { status: 200 });
      }
      if (url.includes("/advertiser-brands-by-org")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-contracts-by-org")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-contacts-by-org")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-brands?") || url.endsWith("/advertiser-brands")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-contracts?") || url.endsWith("/advertiser-contracts")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("memberships")) {
        return new Response(JSON.stringify([]), { status: 200 });
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
      expect(screen.getByTestId("advertiser-org-row")).toBeTruthy();
    });

    await user.click(screen.getByTestId("advertiser-org-row"));

    await waitFor(() => {
      expect(screen.getByTestId("advertiser-detail-panel")).toBeTruthy();
    });

    // Click Пользователи tab
    const usersTab = screen.getByText("Пользователи");
    await user.click(usersTab);

    // Empty state should appear
    await waitFor(() => {
      expect(screen.getByTestId("advertiser-detail-users-empty")).toBeTruthy();
    });
  });

  it("shows empty state when no orgs exist", async () => {
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
            permissions: ["advertisers.read"] }),
          { status: 200 },
        );
      }
      if (url.endsWith("/advertiser-organizations")) {
        return new Response(JSON.stringify(SEED_ORGS_EMPTY), { status: 200 });
      }
      if (url.includes("/advertiser-brands?") || url.endsWith("/advertiser-brands")) {
        return new Response(JSON.stringify([]), { status: 200 });
      }
      if (url.includes("/advertiser-contracts?") || url.endsWith("/advertiser-contracts")) {
        return new Response(JSON.stringify([]), { status: 200 });
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
      expect(screen.getByText("Нет рекламодателей")).toBeTruthy();
    });
  });
});
