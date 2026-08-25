import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import Layout from "../components/Layout";
import RequirePermission from "../components/RequirePermission";
import CampaignListPage from "../pages/CampaignListPage";
import { CAMPAIGNS_MANAGE } from "../auth/permissions";
import { ApiError } from "../api/client";

/**
 * CAMPAIGN-PERMISSION-SPLIT-001 — the cabinet must not offer operator campaign
 * management to an advertiser, and a direct URL must not open the screen
 * either. The API and RLS remain the boundary; this is defence in depth.
 */

const ADVERTISER_PERMS = [
  "campaigns.read",
  "campaign_briefs.manage",
  "advertisers.read",
  "advertisers.contacts.read",
  "creatives.read",
  "organization.read",
];

const mockGet = vi.fn();

vi.mock("../api/client", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/client")>();
  return {
    ...actual,
    api: {
      get: (...args: unknown[]) => mockGet(...args),
      post: vi.fn(),
      patch: vi.fn(),
      del: vi.fn(),
      login: vi.fn(),
      logout: vi.fn().mockResolvedValue(undefined),
      refresh: vi.fn().mockResolvedValue({ access_token: "t", token_type: "Bearer", expires_in: 1800 }),
      getMe: vi.fn().mockImplementation(() => Promise.resolve(currentUser)),
    },
    setToken: vi.fn(),
    onUnauthorized: vi.fn(),
  };
});

let currentUser: Record<string, unknown>;

function advertiser() {
  currentUser = {
    sub: "u-adv",
    auth_provider: "local_advertiser",
    username: "advertiser_test",
    display_name: "Тестовый Рекламодатель",
    permissions: ADVERTISER_PERMS,
    advertiser_organization_id: "org-a",
  };
}

function operator() {
  currentUser = {
    sub: "u-op",
    auth_provider: "local_advertiser",
    username: "manager",
    display_name: "Менеджер",
    permissions: [...ADVERTISER_PERMS, CAMPAIGNS_MANAGE],
    advertiser_organization_id: "org-a",
  };
}

function renderAt(path: string, element: React.ReactNode) {
  const router = createMemoryRouter(
    [{ path: "/", element: <Layout />, children: [{ path: path.slice(1), element }] }],
    { initialEntries: [path] },
  );
  render(
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>,
  );
}

describe("CAMPAIGN-PERMISSION-SPLIT-001 — cabinet write surface", () => {
  afterEach(() => {
    mockGet.mockReset();
    vi.clearAllMocks();
  });

  it("hides campaign creation from an advertiser", async () => {
    advertiser();
    mockGet.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    renderAt("/campaigns", <CampaignListPage />);

    expect(await screen.findByTestId("self-campaign-empty")).toBeTruthy();
    expect(screen.queryByText("+ Создать кампанию")).toBeNull();
  });

  it("still offers campaign creation to an actor that may manage campaigns", async () => {
    operator();
    mockGet.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    renderAt("/campaigns", <CampaignListPage />);

    expect(await screen.findByTestId("self-campaign-empty")).toBeTruthy();
    expect(screen.getByText("+ Создать кампанию")).toBeTruthy();
  });

  it("points an advertiser at the brief flow instead of a hidden button", async () => {
    advertiser();
    mockGet.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    renderAt("/campaigns", <CampaignListPage />);

    expect(await screen.findByTestId("self-campaign-empty")).toBeTruthy();
    expect(screen.getByText(/подайте заявку/i)).toBeTruthy();
  });

  it("refuses an operator-only route opened by direct URL", async () => {
    advertiser();
    mockGet.mockResolvedValue([]);
    renderAt(
      "/campaigns/new",
      <RequirePermission permission={CAMPAIGNS_MANAGE}>
        <div>operator campaign form</div>
      </RequirePermission>,
    );

    expect(await screen.findByTestId("permission-denied")).toBeTruthy();
    expect(screen.queryByText("operator campaign form")).toBeNull();
  });

  it("keeps the brief journey reachable for an advertiser", async () => {
    advertiser();
    mockGet.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    renderAt("/campaigns", <CampaignListPage />);

    expect(await screen.findByTestId("nav-briefs")).toBeTruthy();
  });

  it("hides the operator-only creatives section from an advertiser", async () => {
    advertiser();
    mockGet.mockResolvedValue({ items: [], total: 0, limit: 50, offset: 0 });
    renderAt("/campaigns", <CampaignListPage />);

    await screen.findByTestId("nav-briefs");
    expect(screen.queryByText("Креативы")).toBeNull();
  });

  it("renders a structured 403 detail as text, not [object Object]", () => {
    const err = new ApiError(403, {
      detail: { code: "PERMISSION_DENIED", message: "Missing required permission: campaigns.manage" },
    });
    expect(err.message).toBe("Missing required permission: campaigns.manage");
    expect(err.message).not.toContain("[object Object]");
  });
});
