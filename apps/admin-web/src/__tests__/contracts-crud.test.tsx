/**
 * ADVERTISER-UX-001B2 — Contract CRUD + PDF upload vitest tests.
 *
 * Display/rendering tests. Auth-dependent visibility + create/edit/upload flows
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
const CONTRACT_ID = "00000000-0000-0000-0000-000000000500";

const seedOrg = {
  id: ORG_ID, code: "ADV-001", legal_name: "ООО Ромашка",
  display_name: "Ромашка", status: "active", created_at: null, updated_at: null,
  inn: null, kpp: null, ogrn: null, bank_name: null,
  legal_entity_type: null, legal_form: null, legal_form_other: null,
  legal_address: null, settlement_account: null, correspondent_account: null,
  bik: null, ogrnip: null,
};

const seedContract = {
  id: CONTRACT_ID, advertiser_organization_id: ORG_ID,
  code: "CTR-001", name: "Тестовый договор", contract_number: null,
  budget_limit_amount: null, budget_limit_currency: "RUB",
  valid_from: "2026-01-01T00:00:00Z", valid_until: null,
  status: "draft", terms_url: null,
  file_storage_key: null, file_name: null, file_size_bytes: null,
  file_sha256: null, file_content_type: null, file_uploaded_at: null,
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

async function openContractsTab() {
  const row = await screen.findByTestId("advertiser-org-row");
  await userEvent.click(row);
  await screen.findByTestId("advertiser-detail-panel");
  const tabs = screen.getAllByText("Договоры");
  const tabEl = tabs.find((el) => el.tagName === "DIV" && !el.closest("th"));
  if (!tabEl) throw new Error("Contracts tab not found");
  await userEvent.click(tabEl);
  await screen.findByTestId("advertiser-contracts-section");
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/advertisers"]}>
      <AuthProvider><AdvertisersPage /></AuthProvider>
    </MemoryRouter>,
  );
}

function mockAPI(user: typeof ADMIN_USER, contracts: Record<string, unknown>[] = []) {
  vi.spyOn(api, "getMe").mockResolvedValue(user as never);
  vi.spyOn(api, "get").mockImplementation(async (p: unknown) => {
    const path = String(p);
    if (path.includes(`advertiser-organizations/${ORG_ID}`)) return seedOrg as never;
    if (path.includes("advertiser-contracts-by-org")) return contracts as never;
    if (path.includes("advertiser-organizations")) {
      return [{ id: seedOrg.id, code: seedOrg.code, legal_name: seedOrg.legal_name, display_name: seedOrg.display_name, status: "active" }] as never;
    }
    return [] as never;
  });
}

describe("ContractsTab", () => {
  it("renders existing contract row with code and name", async () => {
    mockAPI(ADMIN_USER, [seedContract]);
    renderPage();
    await openContractsTab();
    await screen.findByTestId(`advertiser-contract-display-number-${CONTRACT_ID}`);
    expect(screen.getByTestId(`advertiser-contract-display-number-${CONTRACT_ID}`).textContent).toBe("CTR-001");
    expect(screen.getByTestId(`advertiser-contract-display-title-${CONTRACT_ID}`).textContent).toBe("Тестовый договор");
  });

  it("shows empty state when no contracts", async () => {
    mockAPI(ADMIN_USER, []);
    renderPage();
    await openContractsTab();
    await screen.findByTestId("advertiser-contract-empty");
    expect(screen.getByText("Нет договоров")).toBeTruthy();
  });

  it("renders section with contracts-section data-testid", async () => {
    mockAPI(ADMIN_USER, [seedContract]);
    renderPage();
    await openContractsTab();
    expect(screen.getByTestId("advertiser-contracts-section")).toBeTruthy();
  });

  it("shows file name and size for contract with uploaded file", async () => {
    const withFile = { ...seedContract, file_name: "contract-2026.pdf", file_size_bytes: 51200 };
    mockAPI(ADMIN_USER, [withFile]);
    renderPage();
    await openContractsTab();
    await screen.findByTestId(`advertiser-contract-display-file-${CONTRACT_ID}`);
    const cell = screen.getByTestId(`advertiser-contract-display-file-${CONTRACT_ID}`);
    expect(cell.textContent).toContain("contract-2026.pdf");
    expect(cell.textContent).toContain("50.0 KB");
  });
});
