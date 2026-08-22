/**
 * ADVERTISER-UX-001B3 — Advertiser contact CRUD vitest tests.
 *
 * Display/rendering tests. Auth-dependent + create/edit flows tested in UI-smoke.
 */
import { describe, it, expect, vi, beforeEach, afterAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { api } from "../api/client";
import AdvertisersPage from "../pages/AdvertisersPage";

const ORG_ID = "00000000-0000-0000-0000-000000000300";
const CONTACT_ID = "00000000-0000-0000-0000-000000000600";

const seedOrg = {
  id: ORG_ID, code: "ADV-001", legal_name: "ООО Ромашка",
  display_name: "Ромашка", status: "active", created_at: null, updated_at: null,
  inn: null, kpp: null, ogrn: null, bank_name: null,
  legal_entity_type: null, legal_form: null, legal_form_other: null,
  legal_address: null, settlement_account: null, correspondent_account: null,
  bik: null, ogrnip: null,
};

const seedContact = {
  id: CONTACT_ID, advertiser_organization_id: ORG_ID,
  user_id: null, contact_type: "primary",
  full_name: "Иван Петров", email: "ivan@test.ru",
  phone: "+7-999-123-45-67", title: "Менеджер",
  is_primary: true, status: "active",
};

const seedUser = {
  id: "mem-u1", user_id: "u-1", username: "ivan_p",
  display_name: "Иван Петров", email: "ivan@test.ru",
  auth_provider: "local_advertiser", user_status: "active",
  must_change_password: false, membership_status: "active",
  membership_created_at: "2026-07-01T00:00:00Z",
};

const ADMIN_USER = {
  sub: "a", code: "a", username: "admin", display_name: "Admin",
  auth_provider: "local_advertiser",
  permissions: ["advertisers.manage", "advertisers.read", "advertisers.contacts.read"],
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(Storage.prototype, "getItem").mockReturnValue("fake-token");
});

afterAll(() => vi.restoreAllMocks());

async function openContactsTab() {
  const row = await screen.findByTestId("advertiser-org-row");
  await userEvent.click(row);
  await screen.findByTestId("advertiser-detail-panel");
  const tabs = screen.getAllByText("Контакты");
  const tabEl = tabs.find((el) => el.tagName === "DIV" && !el.closest("th"));
  if (!tabEl) throw new Error("Contacts tab not found");
  await userEvent.click(tabEl);
  await screen.findByTestId("advertiser-contacts-section");
}

function renderPage() {
  vi.spyOn(api, "getMe").mockResolvedValue(ADMIN_USER as never);
  render(
    <MemoryRouter initialEntries={["/advertisers"]}>
      <AuthProvider>
        <AdvertisersPage />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("ContactsTab", () => {
  it("renders existing contact row with name and email", async () => {
    vi.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/advertiser-organizations")) return Promise.resolve([seedOrg]);
      if (url.includes("/advertiser-brands")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts")) return Promise.resolve([]);
      if (url.includes("/advertiser-organizations/")) return Promise.resolve(seedOrg);
      if (url.includes("/advertiser-brands-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contacts-by-org")) return Promise.resolve([seedContact]);
      if (url.includes("/advertiser-user-memberships")) return Promise.resolve([seedUser]);
      return Promise.resolve([]);
    });

    renderPage();
    await openContactsTab();

    expect(await screen.findByText("Иван Петров")).toBeTruthy();
    expect(screen.getByText("ivan@test.ru")).toBeTruthy();
  });

  it("shows empty state when no contacts", async () => {
    vi.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/advertiser-organizations")) return Promise.resolve([seedOrg]);
      if (url.includes("/advertiser-brands")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts")) return Promise.resolve([]);
      if (url.includes("/advertiser-organizations/")) return Promise.resolve(seedOrg);
      if (url.includes("/advertiser-brands-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contacts-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-user-memberships")) return Promise.resolve([]);
      return Promise.resolve([]);
    });

    renderPage();
    await openContactsTab();

    expect(await screen.findByText("Нет контактов")).toBeTruthy();
  });

  it("renders section with contacts-section data-testid", async () => {
    vi.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/advertiser-organizations")) return Promise.resolve([seedOrg]);
      if (url.includes("/advertiser-brands")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts")) return Promise.resolve([]);
      if (url.includes("/advertiser-organizations/")) return Promise.resolve(seedOrg);
      if (url.includes("/advertiser-brands-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contacts-by-org")) return Promise.resolve([seedContact]);
      if (url.includes("/advertiser-user-memberships")) return Promise.resolve([seedUser]);
      return Promise.resolve([]);
    });

    renderPage();
    await openContactsTab();

    expect(await screen.findByTestId("advertiser-contacts-section")).toBeTruthy();
  });

  it("shows linked user info when contact has user_id", async () => {
    const contactWithLink = { ...seedContact, user_id: "u-1" };

    vi.spyOn(api, "get").mockImplementation((url: string) => {
      if (url.includes("/advertiser-organizations")) return Promise.resolve([seedOrg]);
      if (url.includes("/advertiser-brands")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts")) return Promise.resolve([]);
      if (url.includes("/advertiser-organizations/")) return Promise.resolve(seedOrg);
      if (url.includes("/advertiser-brands-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contracts-by-org")) return Promise.resolve([]);
      if (url.includes("/advertiser-contacts-by-org")) return Promise.resolve([contactWithLink]);
      if (url.includes("/advertiser-user-memberships")) return Promise.resolve([seedUser]);
      return Promise.resolve([]);
    });

    renderPage();
    await openContactsTab();

    expect(await screen.findByText(/ivan_p/)).toBeTruthy();
  });
});
