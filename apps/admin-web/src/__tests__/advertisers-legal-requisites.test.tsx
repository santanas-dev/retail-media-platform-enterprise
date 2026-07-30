/**
 * ADVERTISER-UX-001A2 — Legal requisites tab vitest tests.
 *
 * Display rendering tests. Full auth + edit/save flows tested in UI-smoke.
 */
import { describe, it, expect, vi, beforeEach, afterAll } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../auth/AuthContext";
import { api } from "../api/client";
import AdvertisersPage from "../pages/AdvertisersPage";

const ORG_ID = "00000000-0000-0000-0000-000000000300";

const filledOrg = {
  id: ORG_ID, code: "ADV-001", legal_name: "ООО Ромашка",
  display_name: "Ромашка", status: "active", created_at: null, updated_at: null,
  legal_entity_type: "legal_entity", legal_form: "ooo", legal_form_other: null,
  inn: "7707083893", legal_address: "г. Москва",
  settlement_account: "40702810500000000001", correspondent_account: "30101810200000000593",
  bik: "044525593", bank_name: "Сбербанк", kpp: "770701001", ogrn: "1027700132195", ogrnip: null,
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

async function openLegalTab() {
  const row = await screen.findByTestId("advertiser-org-row");
  await userEvent.click(row);
  await userEvent.click(await screen.findByText("Реквизиты"));
  await screen.findByTestId("advertiser-legal-section");
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/advertisers"]}>
      <AuthProvider><AdvertisersPage /></AuthProvider>
    </MemoryRouter>,
  );
}

function mockGet(org: Record<string, unknown>) {
  vi.spyOn(api, "getMe").mockResolvedValue(ADMIN_USER as never);
  vi.spyOn(api, "get").mockImplementation(async (p: unknown) => {
    const path = String(p);
    if (path.includes(`advertiser-organizations/${ORG_ID}`)) return org as never;
    if (path.includes("advertiser-organizations")) {
      return [{ id: org.id, code: org.code, legal_name: org.legal_name, display_name: org.display_name, status: "active" }] as never;
    }
    return [] as never;
  });
}

describe("LegalRequisitesTab", () => {
  it("renders tab with section for org without requisites", async () => {
    mockGet({ ...filledOrg, inn: null, kpp: null, ogrn: null, bank_name: null });
    renderPage();
    await openLegalTab();
    await screen.findByText("Юридические реквизиты не заполнены");
    // Section present — full edit/save flows tested in smoke
  });

  it("renders existing requisites in display mode", async () => {
    mockGet(filledOrg);
    renderPage();
    await openLegalTab();
    await screen.findByText("Юридические реквизиты");
    expect(screen.getByTestId("advertiser-legal-display-inn").textContent).toBe("7707083893");
    expect(screen.getByTestId("advertiser-legal-display-bank-name").textContent).toBe("Сбербанк");
    expect(screen.getByTestId("advertiser-legal-display-legal-name").textContent).toBe("ООО Ромашка");
  });
});
