/**
 * ADVERTISER-UX-001B1 — Brand CRUD vitest tests.
 *
 * Display/rendering tests. Auth-dependent visibility + create/edit flows
 * tested in UI-smoke (Playwright).
 */
import { describe, it, expect, vi, beforeEach, afterAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { api } from "../api/client";
import AdvertisersPage from "../pages/AdvertisersPage";

const ORG_ID = "00000000-0000-0000-0000-000000000300";
const BRAND_ID = "00000000-0000-0000-0000-000000000400";

const seedOrg = {
  id: ORG_ID, code: "ADV-001", legal_name: "ООО Ромашка",
  display_name: "Ромашка", status: "active", created_at: null, updated_at: null,
  inn: null, kpp: null, ogrn: null, bank_name: null,
};

const seedBrand = {
  id: BRAND_ID, advertiser_organization_id: ORG_ID,
  code: "BR-001", name: "Seed Brand", description: null, status: "active",
};

const ADMIN_USER = {
  sub: "a", code: "a", username: "admin", display_name: "Admin",
  auth_provider: "local_advertiser", permissions: ["advertisers.manage", "advertisers.read"],
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(Storage.prototype, "getItem").mockReturnValue("fake-token");
});

afterAll(() => vi.restoreAllMocks());

async function openBrandsTab() {
  const row = await screen.findByTestId("advertiser-org-row");
  await userEvent.click(row);
  await screen.findByTestId("advertiser-detail-panel");
  const tabs = screen.getAllByText("Бренды");
  const tabEl = tabs.find((el) => el.tagName === "DIV" && !el.closest("th"));
  if (!tabEl) throw new Error("Brands tab not found");
  await userEvent.click(tabEl);
  await screen.findByTestId("advertiser-brands-section");
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/advertisers"]}>
      <AuthProvider><AdvertisersPage /></AuthProvider>
    </MemoryRouter>,
  );
}

function mockAPI(user: typeof ADMIN_USER, brands: Record<string, unknown>[] = []) {
  vi.spyOn(api, "getMe").mockResolvedValue(user as never);
  vi.spyOn(api, "get").mockImplementation(async (p: unknown) => {
    const path = String(p);
    if (path.includes(`advertiser-organizations/${ORG_ID}`)) return seedOrg as never;
    if (path.includes("advertiser-brands-by-org")) return brands as never;
    if (path.includes("advertiser-organizations")) {
      return [{ id: seedOrg.id, code: seedOrg.code, legal_name: seedOrg.legal_name, display_name: seedOrg.display_name, status: "active" }] as never;
    }
    return [] as never;
  });
}

describe("BrandsTab", () => {
  it("renders existing brand row with name and code", async () => {
    mockAPI(ADMIN_USER, [seedBrand]);
    renderPage();
    await openBrandsTab();
    await screen.findByTestId(`advertiser-brand-display-name-${BRAND_ID}`);
    expect(screen.getByTestId(`advertiser-brand-display-code-${BRAND_ID}`).textContent).toBe("BR-001");
    expect(screen.getByTestId(`advertiser-brand-display-status-${BRAND_ID}`).textContent).toBe("Активна");
  });

  it("shows empty state when no brands", async () => {
    mockAPI(ADMIN_USER, []);
    renderPage();
    await openBrandsTab();
    await screen.findByTestId("advertiser-brand-empty");
    expect(screen.getByText("Нет брендов")).toBeTruthy();
  });

  it("renders section with brands-section data-testid", async () => {
    mockAPI(ADMIN_USER, [seedBrand]);
    renderPage();
    await openBrandsTab();
    // Section must exist
    expect(screen.getByTestId("advertiser-brands-section")).toBeTruthy();
  });
});
