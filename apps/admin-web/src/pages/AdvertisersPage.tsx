import { useState, useEffect, useMemo, useRef } from "react";
import {
  listAdvertisers,
  listBrands,
  listContracts,
  getAdvertiserDetail,
  listBrandsByOrg,
  listContractsByOrg,
  listContactsByOrg,
  listMemberships,
  createAdvertiserOrganization,
  updateAdvertiserLegalRequisites,
  createAdvertiserBrand,
  updateAdvertiserBrand,
  createAdvertiserContract,
  updateAdvertiserContract,
  createContractUploadIntent,
  completeContractUpload,
  createAdvertiserContact,
  updateAdvertiserContact,
} from "../api/campaigns";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import type {
  AdvertiserOrganizationOut,
  AdvertiserOrganizationDetailOut,
  AdvertiserBrandOut,
  AdvertiserBrandCreate,
  AdvertiserBrandUpdate,
  AdvertiserContractCreate,
  AdvertiserContractUpdate,
  AdvertiserContractOut,
  AdvertiserContactOut,
  AdvertiserContactCreate,
  AdvertiserContactUpdate,
  AdvertiserUserMembershipOut,
  AdvertiserLegalRequisitesUpdate,
} from "../api/types";
import {
  statusLabel,
  statusColor,
  contactTypeLabel,
  authProviderLabel,
} from "../api/types";

// ── Types ──

interface OrgRow extends AdvertiserOrganizationOut {
  brandCount: number;
  contractCount: number;
  contactCount: number;
}

type PageState =
  | { stage: "loading" }
  | { stage: "error"; message: string }
  | { stage: "ready"; orgs: OrgRow[] };

type DetailData = {
  org: AdvertiserOrganizationDetailOut;
  brands: AdvertiserBrandOut[];
  contracts: AdvertiserContractOut[];
  contacts: AdvertiserContactOut[];
  users: AdvertiserUserMembershipOut[];
};

type DetailState =
  | { stage: "idle" }
  | { stage: "loading" }
  | { stage: "error"; message: string }
  | { stage: "ready"; data: DetailData };

// ── Inline Styles ──

const S = {
  header: {
    fontSize: "1.25rem",
    fontWeight: 600,
    margin: "0 0 1rem",
  } as React.CSSProperties,
  search: {
    width: "100%",
    maxWidth: 360,
    padding: "0.5rem 0.75rem",
    marginBottom: "1rem",
    border: "1px solid #e2e8f0",
    borderRadius: 6,
    fontSize: "0.875rem",
  } as React.CSSProperties,
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.875rem",
  },
  th: {
    textAlign: "left" as const,
    padding: "0.5rem 0.75rem",
    borderBottom: "2px solid #e2e8f0",
    color: "#64748b",
    fontWeight: 600,
    fontSize: "0.8rem",
    whiteSpace: "nowrap" as const,
  },
  td: {
    padding: "0.5rem 0.75rem",
    borderBottom: "1px solid #f1f5f9",
  },
  row: {
    cursor: "pointer",
  } as React.CSSProperties,
  badge: (color: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "0.1rem 0.5rem",
    borderRadius: 999,
    fontSize: "0.75rem",
    fontWeight: 500,
    color: "#fff",
    background: color,
  }),
  detailPanel: {
    marginTop: "1.5rem",
    border: "1px solid #e2e8f0",
    borderRadius: 8,
    background: "#fff",
    overflow: "hidden",
  } as React.CSSProperties,
  tabs: {
    display: "flex",
    borderBottom: "1px solid #e2e8f0",
    background: "#f8fafc",
  } as React.CSSProperties,
  tab: (active: boolean): React.CSSProperties => ({
    padding: "0.5rem 1rem",
    fontSize: "0.8125rem",
    fontWeight: active ? 600 : 400,
    color: active ? "#1e293b" : "#64748b",
    borderBottom: active ? "2px solid #2563eb" : "2px solid transparent",
    cursor: "pointer",
    background: active ? "#fff" : "transparent",
  }),
  tabContent: {
    padding: "1rem",
  } as React.CSSProperties,
  detailHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "0.75rem",
  } as React.CSSProperties,
  detailClose: {
    background: "none",
    border: "none",
    fontSize: "1.25rem",
    cursor: "pointer",
    color: "#64748b",
    padding: "0 0.25rem",
  } as React.CSSProperties,
  empty: {
    textAlign: "center" as const,
    color: "#64748b",
    padding: "2rem",
    fontSize: "0.875rem",
  },
  error: {
    color: "#dc2626",
    padding: "1rem",
    fontSize: "0.875rem",
  },
  loading: {
    color: "#64748b",
    padding: "1rem",
    fontSize: "0.875rem",
  },
  count: {
    display: "inline-block",
    background: "#f1f5f9",
    color: "#475569",
    borderRadius: 999,
    padding: "0.05rem 0.5rem",
    fontSize: "0.75rem",
    fontWeight: 500,
    minWidth: 24,
    textAlign: "center" as const,
  },
  fieldGroup: {
    marginBottom: "0.75rem",
  } as React.CSSProperties,
  fieldLabel: {
    fontSize: "0.75rem",
    color: "#64748b",
    fontWeight: 500,
    marginBottom: "0.15rem",
  } as React.CSSProperties,
  fieldValue: {
    fontSize: "0.875rem",
  } as React.CSSProperties,
  fieldError: {
    color: "#dc2626",
    fontSize: "0.8125rem",
    marginBottom: "0.5rem",
  } as React.CSSProperties,
  fieldSuccess: {
    color: "#16a34a",
    fontSize: "0.8125rem",
    marginBottom: "0.5rem",
  } as React.CSSProperties,
  btnPrimarySmall: {
    padding: "0.25rem 0.75rem",
    fontSize: "0.8125rem",
    fontWeight: 500,
    color: "#fff",
    background: "#2563eb",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
  } as React.CSSProperties,
  btnSecondarySmall: {
    padding: "0.25rem 0.75rem",
    fontSize: "0.8125rem",
    fontWeight: 500,
    color: "#475569",
    background: "#f1f5f9",
    border: "1px solid #e2e8f0",
    borderRadius: 4,
    cursor: "pointer",
  } as React.CSSProperties,
  btnEditSmall: {
    padding: "0.2rem 0.5rem",
    fontSize: "0.75rem",
    fontWeight: 500,
    color: "#2563eb",
    background: "#eff6ff",
    border: "1px solid #bfdbfe",
    borderRadius: 4,
    cursor: "pointer",
  } as React.CSSProperties,
  inputSmall: {
    padding: "0.2rem 0.4rem",
    fontSize: "0.8125rem",
    border: "1px solid #e2e8f0",
    borderRadius: 4,
    width: "100%",
  } as React.CSSProperties,
  selectSmall: {
    padding: "0.2rem 0.4rem",
    fontSize: "0.8125rem",
    border: "1px solid #e2e8f0",
    borderRadius: 4,
  } as React.CSSProperties,
  input: {
    padding: "0.4rem 0.6rem",
    fontSize: "0.875rem",
    border: "1px solid #e2e8f0",
    borderRadius: 4,
    width: "100%",
    marginBottom: "0.5rem",
    boxSizing: "border-box" as const,
  } as React.CSSProperties,
  select: {
    padding: "0.4rem 0.6rem",
    fontSize: "0.875rem",
    border: "1px solid #e2e8f0",
    borderRadius: 4,
    width: "100%",
    marginBottom: "0.5rem",
    background: "#fff",
  } as React.CSSProperties,
};

// ── Helpers ──

const TABS = ["Обзор", "Реквизиты", "Бренды", "Договоры", "Контакты", "Пользователи"] as const;
type Tab = (typeof TABS)[number];

// ── Component ──

export default function AdvertisersPage() {
  const { user } = useAuth();
  const canCreate = user?.permissions?.includes("advertisers.manage") ?? false;
  const [pageState, setPageState] = useState<PageState>({ stage: "loading" });
  const [detailState, setDetailState] = useState<DetailState>({ stage: "idle" });
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Обзор");
  const [search, setSearch] = useState("");
  // Create modal
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({ code: "", legal_name: "", display_name: "" });
  const [createError, setCreateError] = useState("");

  async function handleCreate() {
    setCreateError("");
    try {
      const org = await createAdvertiserOrganization(createForm);
      setCreateOpen(false);
      setCreateForm({ code: "", legal_name: "", display_name: "" });
      // Reload list
      const [orgs, brands, contracts] = await Promise.all([
        listAdvertisers(), listBrands(), listContracts(),
      ]);
      const brandMap = new Map<string, number>();
      for (const b of brands) brandMap.set(b.advertiser_organization_id, (brandMap.get(b.advertiser_organization_id) ?? 0) + 1);
      const contractMap = new Map<string, number>();
      for (const c of contracts) contractMap.set(c.advertiser_organization_id, (contractMap.get(c.advertiser_organization_id) ?? 0) + 1);
      const rows: OrgRow[] = orgs.map((o) => ({ ...o, brandCount: brandMap.get(o.id) ?? 0, contractCount: contractMap.get(o.id) ?? 0, contactCount: 0 }));
      setPageState({ stage: "ready", orgs: rows });
      setSelectedOrgId(org.id);
      setActiveTab("Обзор");
    } catch (e: unknown) {
      setCreateError(e instanceof ApiError ? e.message : "Ошибка создания организации");
    }
  }

  // ── Load org list + counts on mount ──

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [orgs, brands, contracts] = await Promise.all([
          listAdvertisers(),
          listBrands(),
          listContracts(),
        ]);

        if (cancelled) return;

        const brandMap = new Map<string, number>();
        for (const b of brands) {
          brandMap.set(b.advertiser_organization_id, (brandMap.get(b.advertiser_organization_id) ?? 0) + 1);
        }
        const contractMap = new Map<string, number>();
        for (const c of contracts) {
          contractMap.set(c.advertiser_organization_id, (contractMap.get(c.advertiser_organization_id) ?? 0) + 1);
        }

        const rows: OrgRow[] = orgs.map((o) => ({
          ...o,
          brandCount: brandMap.get(o.id) ?? 0,
          contractCount: contractMap.get(o.id) ?? 0,
          contactCount: 0, // loaded on demand in detail
        }));

        setPageState({ stage: "ready", orgs: rows });
      } catch (e: unknown) {
        if (cancelled) return;
        setPageState({
          stage: "error",
          message: e instanceof ApiError ? e.message : "Не удалось загрузить список рекламодателей",
        });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // ── Load detail when org selected ──
  const [detailVersion, setDetailVersion] = useState(0);

  useEffect(() => {
    if (!selectedOrgId) {
      setDetailState({ stage: "idle" });
      return;
    }

    let cancelled = false;
    async function load() {
      setDetailState({ stage: "loading" });
      try {
        const [org, brands, contracts, contacts, users] = await Promise.all([
          getAdvertiserDetail(selectedOrgId!),
          listBrandsByOrg(selectedOrgId!),
          listContractsByOrg(selectedOrgId!),
          listContactsByOrg(selectedOrgId!),
          listMemberships(selectedOrgId!).catch(() => [] as AdvertiserUserMembershipOut[]),
        ]);

        if (cancelled) return;
        setDetailState({ stage: "ready", data: { org, brands, contracts, contacts, users } });

        // Update contact count in pageState
        setPageState((prev) => {
          if (prev.stage !== "ready") return prev;
          return {
            ...prev,
            orgs: prev.orgs.map((o) =>
              o.id === selectedOrgId ? { ...o, contactCount: contacts.length } : o,
            ),
          };
        });
      } catch (e: unknown) {
        if (cancelled) return;
        setDetailState({
          stage: "error",
          message: e instanceof ApiError ? e.message : "Не удалось загрузить данные организации",
        });
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [selectedOrgId, detailVersion]);

  // ── Filter ──

  const filteredOrgs = useMemo(() => {
    if (pageState.stage !== "ready") return [];
    if (!search.trim()) return pageState.orgs;
    const q = search.toLowerCase();
    return pageState.orgs.filter(
      (o) =>
        o.code.toLowerCase().includes(q) ||
        o.display_name.toLowerCase().includes(q) ||
        o.legal_name.toLowerCase().includes(q),
    );
  }, [pageState, search]);

  // ── Render ──

  if (pageState.stage === "loading") {
    return <div style={S.loading}>Загрузка...</div>;
  }

  if (pageState.stage === "error") {
    return <div style={S.error}>{pageState.message}</div>;
  }

  return (
    <div>
      <h2 style={S.header}>Рекламодатели</h2>

      {canCreate && (
      <button
        data-testid="advertiser-create-open"
        onClick={() => setCreateOpen(true)}
        style={{ marginBottom: "1rem", padding: "0.5rem 1rem", cursor: "pointer" }}
      >
        + Создать организацию
      </button>
      )}

      {/* Search */}
      <input
        style={S.search}
        type="text"
        placeholder="Поиск по коду или названию..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {/* Orgs table */}
      {filteredOrgs.length === 0 ? (
        <div style={S.empty}>
          {search.trim() ? "Ничего не найдено" : "Нет рекламодателей"}
        </div>
      ) : (
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>Код</th>
              <th style={S.th}>Название</th>
              <th style={S.th}>Статус</th>
              <th style={S.th}>Бренды</th>
              <th style={S.th}>Договоры</th>
              <th style={S.th}>Контакты</th>
            </tr>
          </thead>
          <tbody>
            {filteredOrgs.map((org) => (
              <tr
                key={org.id}
                data-testid="advertiser-org-row"
                style={{
                  ...S.row,
                  background: selectedOrgId === org.id ? "#eff6ff" : undefined,
                }}
                onClick={() => {
                  setSelectedOrgId(org.id);
                  setActiveTab("Обзор");
                }}
              >
                <td style={S.td}>{org.code}</td>
                <td style={S.td}>{org.display_name}</td>
                <td style={S.td}>
                  <span style={S.badge(statusColor(org.status))}>{statusLabel(org.status)}</span>
                </td>
                <td style={S.td}><span style={S.count}>{org.brandCount}</span></td>
                <td style={S.td}><span style={S.count}>{org.contractCount}</span></td>
                <td style={S.td}><span style={S.count}>{org.contactCount}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {/* Detail panel */}
      {selectedOrgId && (
        <div style={S.detailPanel} data-testid="advertiser-detail-panel">
          <div style={S.tabs}>
            {TABS.map((t) => (
              <div key={t} style={S.tab(activeTab === t)} onClick={() => setActiveTab(t)} data-testid={`advertiser-tab-${t.toLowerCase()}`}>
                {t}
              </div>
            ))}
            <div style={{ flex: 1 }} />
            <button
              style={S.detailClose}
              onClick={() => setSelectedOrgId(null)}
              title="Закрыть"
            >
              ✕
            </button>
          </div>
          <div style={S.tabContent}>
            {detailState.stage === "loading" ? (
              <div style={S.loading}>Загрузка...</div>
            ) : detailState.stage === "error" ? (
              <div style={S.error}>{detailState.message}</div>
            ) : detailState.stage === "ready" ? (
              <RenderTab tab={activeTab} data={detailState.data} onRequisitesSaved={() => setDetailVersion((v) => v + 1)} onBrandChange={() => setDetailVersion((v) => v + 1)} />
            ) : null}
          </div>
        </div>
      )}

      {/* Create modal */}
      {createOpen && (
        <div style={{
          position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
          background: "rgba(0,0,0,0.4)", display: "flex",
          alignItems: "center", justifyContent: "center", zIndex: 1000,
        }} onClick={(e) => { if (e.target === e.currentTarget) setCreateOpen(false); }}>
          <div style={{ background: "#fff", borderRadius: 8, padding: "1.5rem", minWidth: 400, maxWidth: 500 }}>
            <h3 style={{ margin: "0 0 1rem" }}>Создать организацию</h3>
            {createError && <div style={{ color: "#dc2626", marginBottom: "0.75rem", fontSize: "0.875rem" }}>{createError}</div>}
            <div style={{ marginBottom: "0.75rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", marginBottom: "0.25rem", color: "#64748b" }}>Код</label>
              <input data-testid="advertiser-create-code" style={{ width: "100%", padding: "0.5rem", border: "1px solid #e2e8f0", borderRadius: 4 }} value={createForm.code} onChange={(e) => setCreateForm({ ...createForm, code: e.target.value })} />
            </div>
            <div style={{ marginBottom: "0.75rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", marginBottom: "0.25rem", color: "#64748b" }}>Юридическое название</label>
              <input data-testid="advertiser-create-legal-name" style={{ width: "100%", padding: "0.5rem", border: "1px solid #e2e8f0", borderRadius: 4 }} value={createForm.legal_name} onChange={(e) => setCreateForm({ ...createForm, legal_name: e.target.value })} />
            </div>
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", marginBottom: "0.25rem", color: "#64748b" }}>Отображаемое название</label>
              <input data-testid="advertiser-create-display-name" style={{ width: "100%", padding: "0.5rem", border: "1px solid #e2e8f0", borderRadius: 4 }} value={createForm.display_name} onChange={(e) => setCreateForm({ ...createForm, display_name: e.target.value })} />
            </div>
            <div style={{ display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
              <button onClick={() => setCreateOpen(false)} style={{ padding: "0.5rem 1rem", cursor: "pointer" }}>Отмена</button>
              <button data-testid="advertiser-create-save" onClick={handleCreate} style={{ padding: "0.5rem 1rem", cursor: "pointer", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4 }}>Сохранить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tab Renderers ──

function RenderTab({ tab, data, onRequisitesSaved, onBrandChange }: { tab: Tab; data: DetailData; onRequisitesSaved: () => void; onBrandChange: () => void }) {
  const onContractChange = onBrandChange;  // same refetch trigger for contracts
  const onContactChange = onBrandChange;   // same refetch trigger for contacts
  switch (tab) {
    case "Обзор":
      return <OverviewTab org={data.org} />;
    case "Реквизиты":
      return <LegalRequisitesTab org={data.org} onSaved={onRequisitesSaved} />;
    case "Бренды":
      return <BrandsTab brands={data.brands} orgId={data.org.id} onBrandChange={onBrandChange} />;
    case "Договоры":
      return <ContractsTab contracts={data.contracts} orgId={data.org.id} onContractChange={onContractChange} />;
    case "Контакты":
      return <ContactsTab contacts={data.contacts} users={data.users} orgId={data.org.id} onContactChange={onContactChange} />;
    case "Пользователи":
      return <UsersTab users={data.users} />;
  }
}

function OverviewTab({ org }: { org: AdvertiserOrganizationDetailOut }) {
  return (
    <div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Код</div>
        <div style={S.fieldValue} data-testid="advertiser-detail-code">{org.code}</div>
      </div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Название</div>
        <div style={S.fieldValue} data-testid="advertiser-detail-display-name">{org.display_name}</div>
      </div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Юридическое название</div>
        <div style={S.fieldValue} data-testid="advertiser-detail-legal-name">{org.legal_name}</div>
      </div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Статус</div>
        <div style={S.fieldValue} data-testid="advertiser-detail-status">
          <span style={S.badge(statusColor(org.status))}>{statusLabel(org.status)}</span>
        </div>
      </div>
      {org.created_at && (
        <div style={S.fieldGroup}>
          <div style={S.fieldLabel}>Создан</div>
          <div style={S.fieldValue}>{new Date(org.created_at).toLocaleString("ru-RU")}</div>
        </div>
      )}
      {org.updated_at && (
        <div style={S.fieldGroup}>
          <div style={S.fieldLabel}>Обновлён</div>
          <div style={S.fieldValue}>{new Date(org.updated_at).toLocaleString("ru-RU")}</div>
        </div>
      )}
    </div>
  );
}

// ── ADVERTISER-UX-001A2 — Legal requisites form ──

function LegalRequisitesTab({ org, onSaved }: { org: AdvertiserOrganizationDetailOut; onSaved: () => void }) {
  const { user } = useAuth();
  const canEdit = user?.permissions?.includes("advertisers.manage") ?? false;

  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState({
    legal_entity_type: org.legal_entity_type || "legal_entity",
    legal_form: org.legal_form || "ooo",
    legal_form_other: org.legal_form_other || "",
    legal_name: org.legal_name || "",
    inn: org.inn || "",
    legal_address: org.legal_address || "",
    settlement_account: org.settlement_account || "",
    correspondent_account: org.correspondent_account || "",
    bik: org.bik || "",
    bank_name: org.bank_name || "",
    kpp: org.kpp || "",
    ogrn: org.ogrn || "",
    ogrnip: org.ogrnip || "",
  });

  const isLE = form.legal_entity_type === "legal_entity";

  function updateField(field: string, value: string) {
    if (field === "legal_entity_type") {
      setForm((prev) => ({ ...prev, legal_entity_type: value, kpp: "", ogrn: "", ogrnip: "" }));
    } else {
      setForm((prev) => ({ ...prev, [field]: value }));
    }
  }

  async function handleSave() {
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const body: AdvertiserLegalRequisitesUpdate = {
        legal_entity_type: form.legal_entity_type,
        legal_form: form.legal_form,
        legal_name: form.legal_name,
        inn: form.inn,
        legal_address: form.legal_address,
        settlement_account: form.settlement_account,
        correspondent_account: form.correspondent_account,
        bik: form.bik,
        bank_name: form.bank_name,
      };
      if (form.legal_form === "other" && form.legal_form_other) {
        body.legal_form_other = form.legal_form_other;
      }
      if (isLE) {
        body.kpp = form.kpp || null;
        body.ogrn = form.ogrn || null;
      } else {
        body.ogrnip = form.ogrnip || null;
      }
      await updateAdvertiserLegalRequisites(org.id, body);
      setSuccess("Реквизиты сохранены");
      setEditing(false);
      onSaved();
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? typeof e.body === "object" && e.body !== null && "detail" in e.body
            ? String((e.body as Record<string, unknown>).detail)
            : e.message
          : "Ошибка сохранения реквизитов",
      );
    } finally {
      setSaving(false);
    }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "0.4rem 0.5rem", border: "1px solid #e2e8f0",
    borderRadius: 4, fontSize: "0.875rem", boxSizing: "border-box",
  };
  const labelStyle: React.CSSProperties = {
    display: "block", fontSize: "0.8rem", marginBottom: "0.2rem",
    color: "#64748b", fontWeight: 500,
  };
  const groupStyle: React.CSSProperties = { marginBottom: "0.75rem" };

  return (
    <div data-testid="advertiser-legal-section">
      {!editing && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <h4 style={{ margin: 0, fontSize: "0.9rem" }}>
              {org.inn ? "Юридические реквизиты" : "Юридические реквизиты не заполнены"}
            </h4>
            {canEdit && (
              <button
                data-testid="advertiser-legal-edit"
                onClick={() => setEditing(true)}
                style={{ padding: "0.35rem 0.75rem", cursor: "pointer", fontSize: "0.8125rem" }}
              >
                {org.inn ? "Редактировать" : "Заполнить"}
              </button>
            )}
          </div>
          {org.inn ? (
            <div>
              <div style={groupStyle}><div style={labelStyle}>Тип</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-entity-type">{org.legal_entity_type === "individual_entrepreneur" ? "ИП" : "Юрлицо"}</div></div>
              <div style={groupStyle}><div style={labelStyle}>Название</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-legal-name">{org.legal_name}</div></div>
              <div style={groupStyle}><div style={labelStyle}>ИНН</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-inn">{org.inn}</div></div>
              {org.kpp && <div style={groupStyle}><div style={labelStyle}>КПП</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-kpp">{org.kpp}</div></div>}
              {org.ogrn && <div style={groupStyle}><div style={labelStyle}>ОГРН</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-ogrn">{org.ogrn}</div></div>}
              {org.ogrnip && <div style={groupStyle}><div style={labelStyle}>ОГРНИП</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-ogrnip">{org.ogrnip}</div></div>}
              {org.legal_address && <div style={groupStyle}><div style={labelStyle}>Юридический адрес</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-legal-address">{org.legal_address}</div></div>}
              {org.settlement_account && <div style={groupStyle}><div style={labelStyle}>Расчётный счёт</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-settlement-account">{org.settlement_account}</div></div>}
              {org.correspondent_account && <div style={groupStyle}><div style={labelStyle}>Корр. счёт</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-correspondent-account">{org.correspondent_account}</div></div>}
              {org.bik && <div style={groupStyle}><div style={labelStyle}>БИК</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-bik">{org.bik}</div></div>}
              <div style={groupStyle}><div style={labelStyle}>Банк</div><div style={{ fontSize: "0.875rem" }} data-testid="advertiser-legal-display-bank-name">{org.bank_name}</div></div>
            </div>
          ) : (
            <div style={{ color: "#64748b", fontSize: "0.875rem" }}>
              {canEdit ? "Нажмите «Заполнить» чтобы добавить реквизиты." : "Нет данных."}
            </div>
          )}
        </div>
      )}

      {editing && (
        <div>
          <h4 style={{ margin: "0 0 1rem", fontSize: "0.9rem" }}>Редактирование реквизитов</h4>
          {error && <div data-testid="advertiser-legal-error" style={{ color: "#dc2626", marginBottom: "0.75rem", fontSize: "0.875rem" }}>{error}</div>}
          {success && <div data-testid="advertiser-legal-success" style={{ color: "#16a34a", marginBottom: "0.75rem", fontSize: "0.875rem" }}>{success}</div>}

          <div style={groupStyle}><div style={labelStyle}>Тип *</div>
            <select data-testid="advertiser-legal-entity-type" style={inputStyle} value={form.legal_entity_type}
              onChange={(e) => updateField("legal_entity_type", e.target.value)}>
              <option value="legal_entity">Юрлицо</option>
              <option value="individual_entrepreneur">ИП</option>
            </select></div>

          <div style={groupStyle}><div style={labelStyle}>Форма *</div>
            <select data-testid="advertiser-legal-form" style={inputStyle} value={form.legal_form}
              onChange={(e) => setForm({ ...form, legal_form: e.target.value })}>
              <option value="ooo">ООО</option><option value="ao">АО</option><option value="pao">ПАО</option>
              <option value="ip">ИП</option><option value="other">другое</option>
            </select></div>

          {form.legal_form === "other" && (
            <div style={groupStyle}><div style={labelStyle}>Другая форма *</div>
              <input data-testid="advertiser-legal-form-other" style={inputStyle} value={form.legal_form_other}
                onChange={(e) => setForm({ ...form, legal_form_other: e.target.value })} placeholder="Укажите форму" />
            </div>)}

          <div style={groupStyle}><div style={labelStyle}>Название *</div>
            <input data-testid="advertiser-legal-name" style={inputStyle} value={form.legal_name}
              onChange={(e) => setForm({ ...form, legal_name: e.target.value })} /></div>

          <div style={groupStyle}><div style={labelStyle}>ИНН * ({isLE ? "10" : "12"} цифр)</div>
            <input data-testid="advertiser-legal-inn" style={inputStyle} value={form.inn}
              onChange={(e) => setForm({ ...form, inn: e.target.value })} /></div>

          {isLE && <div style={groupStyle}><div style={labelStyle}>КПП * (9 цифр)</div>
            <input data-testid="advertiser-legal-kpp" style={inputStyle} value={form.kpp}
              onChange={(e) => setForm({ ...form, kpp: e.target.value })} /></div>}

          {isLE && <div style={groupStyle}><div style={labelStyle}>ОГРН * (13 цифр)</div>
            <input data-testid="advertiser-legal-ogrn" style={inputStyle} value={form.ogrn}
              onChange={(e) => setForm({ ...form, ogrn: e.target.value })} /></div>}

          {!isLE && <div style={groupStyle}><div style={labelStyle}>ОГРНИП * (15 цифр)</div>
            <input data-testid="advertiser-legal-ogrnip" style={inputStyle} value={form.ogrnip}
              onChange={(e) => setForm({ ...form, ogrnip: e.target.value })} /></div>}

          <div style={groupStyle}><div style={labelStyle}>Юридический адрес *</div>
            <input data-testid="advertiser-legal-address" style={inputStyle} value={form.legal_address}
              onChange={(e) => setForm({ ...form, legal_address: e.target.value })} /></div>

          <div style={groupStyle}><div style={labelStyle}>Расчётный счёт * (20 цифр)</div>
            <input data-testid="advertiser-legal-settlement-account" style={inputStyle} value={form.settlement_account}
              onChange={(e) => setForm({ ...form, settlement_account: e.target.value })} /></div>

          <div style={groupStyle}><div style={labelStyle}>Корреспондентский счёт * (20 цифр)</div>
            <input data-testid="advertiser-legal-correspondent-account" style={inputStyle} value={form.correspondent_account}
              onChange={(e) => setForm({ ...form, correspondent_account: e.target.value })} /></div>

          <div style={groupStyle}><div style={labelStyle}>БИК * (9 цифр)</div>
            <input data-testid="advertiser-legal-bik" style={inputStyle} value={form.bik}
              onChange={(e) => setForm({ ...form, bik: e.target.value })} /></div>

          <div style={groupStyle}><div style={labelStyle}>Банк *</div>
            <input data-testid="advertiser-legal-bank-name" style={inputStyle} value={form.bank_name}
              onChange={(e) => setForm({ ...form, bank_name: e.target.value })} /></div>

          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
            <button onClick={() => { setEditing(false); setError(""); setSuccess(""); }}
              style={{ padding: "0.5rem 1rem", cursor: "pointer" }}>Отмена</button>
            <button data-testid="advertiser-legal-submit" onClick={handleSave} disabled={saving}
              style={{ padding: "0.5rem 1rem", cursor: "pointer", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4, opacity: saving ? 0.6 : 1 }}>
              {saving ? "Сохранение..." : "Сохранить"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function BrandsTab({ brands, orgId, onBrandChange }: { brands: AdvertiserBrandOut[]; orgId: string; onBrandChange: () => void }) {
  const { user } = useAuth();
  const canEdit = user?.permissions?.includes("advertisers.manage") ?? false;

  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [form, setForm] = useState({ code: "", name: "", description: "" });

  function resetForm() {
    setForm({ code: "", name: "", description: "" });
    setCreating(false);
    setEditingId(null);
    setError("");
    setSuccess("");
  }

  async function handleCreate() {
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const body: AdvertiserBrandCreate = {
        advertiser_organization_id: orgId,
        code: form.code,
        name: form.name,
        description: form.description || null,
      };
      await createAdvertiserBrand(body);
      setSuccess(`Бренд «${form.name}» создан`);
      resetForm();
      onBrandChange();
    } catch (e: unknown) {
      setError(e instanceof ApiError ? (typeof e.body === "object" && e.body !== null && "detail" in e.body ? String((e.body as Record<string, unknown>).detail) : e.message) : "Ошибка создания бренда");
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(brandId: string) {
    setError("");
    setSuccess("");
    setSaving(true);
    try {
      const body: AdvertiserBrandUpdate = {
        code: form.code || undefined,
        name: form.name || undefined,
        description: form.description || undefined,
      };
      const updated = await updateAdvertiserBrand(brandId, orgId, body);
      setSuccess(`Бренд «${updated.name}» обновлён`);
      resetForm();
      onBrandChange();
    } catch (e: unknown) {
      setError(e instanceof ApiError ? (typeof e.body === "object" && e.body !== null && "detail" in e.body ? String((e.body as Record<string, unknown>).detail) : e.message) : "Ошибка обновления бренда");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(b: AdvertiserBrandOut) {
    setForm({ code: b.code, name: b.name, description: b.description ?? "" });
    setEditingId(b.id);
    setCreating(false);
    setError("");
    setSuccess("");
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "0.35rem 0.5rem", border: "1px solid #e2e8f0",
    borderRadius: 4, fontSize: "0.875rem", boxSizing: "border-box",
  };

  return (
    <div data-testid="advertiser-brands-section">
      {error && <div data-testid="advertiser-brand-error" style={{ color: "#dc2626", marginBottom: "0.5rem", fontSize: "0.875rem" }}>{error}</div>}
      {success && <div data-testid="advertiser-brand-success" style={{ color: "#16a34a", marginBottom: "0.5rem", fontSize: "0.875rem" }}>{success}</div>}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h4 style={{ margin: 0, fontSize: "0.9rem" }}>Бренды</h4>
        {canEdit && !creating && (
          <button data-testid="advertiser-brand-create-open" onClick={() => { setCreating(true); setEditingId(null); setForm({ code: "", name: "", description: "" }); setError(""); setSuccess(""); }}
            style={{ padding: "0.35rem 0.75rem", cursor: "pointer", fontSize: "0.8125rem" }}>Добавить бренд</button>
        )}
      </div>

      {creating && (
        <div style={{ border: "1px solid #e2e8f0", borderRadius: 6, padding: "0.75rem", marginBottom: "0.75rem", background: "#f8fafc" }}>
          <div style={{ marginBottom: "0.5rem" }}>
            <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Код *</div>
            <input data-testid="advertiser-brand-code" style={inputStyle} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Название *</div>
            <input data-testid="advertiser-brand-name" style={inputStyle} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div style={{ marginBottom: "0.5rem" }}>
            <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Описание</div>
            <input data-testid="advertiser-brand-description" style={inputStyle} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button onClick={resetForm} style={{ padding: "0.35rem 0.75rem", cursor: "pointer", fontSize: "0.8125rem" }}>Отмена</button>
            <button data-testid="advertiser-brand-submit" onClick={handleCreate} disabled={saving}
              style={{ padding: "0.35rem 0.75rem", cursor: "pointer", fontSize: "0.8125rem", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4 }}>Сохранить</button>
          </div>
        </div>
      )}

      {brands.length === 0 && !creating ? (
        <div data-testid="advertiser-brand-empty" style={S.empty}>Нет брендов</div>
      ) : (
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>Код</th>
              <th style={S.th}>Название</th>
              <th style={S.th}>Описание</th>
              <th style={S.th}>Статус</th>
              {canEdit && <th style={{ ...S.th, width: 60 }}></th>}
            </tr>
          </thead>
          <tbody>
            {brands.map((b) => (
              editingId === b.id ? (
                <tr key={b.id} data-testid={`advertiser-brand-row-${b.id}`}>
                  <td style={S.td}><input data-testid="advertiser-brand-code" style={inputStyle} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></td>
                  <td style={S.td}><input data-testid="advertiser-brand-name" style={inputStyle} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></td>
                  <td style={S.td}><input data-testid="advertiser-brand-description" style={inputStyle} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></td>
                  <td style={S.td}><span style={S.badge(statusColor(b.status))}>{statusLabel(b.status)}</span></td>
                  <td style={S.td}>
                    <div style={{ display: "flex", gap: "0.25rem" }}>
                      <button onClick={() => handleUpdate(b.id)} disabled={saving} style={{ padding: "0.2rem 0.4rem", cursor: "pointer", fontSize: "0.75rem" }}>✓</button>
                      <button onClick={resetForm} style={{ padding: "0.2rem 0.4rem", cursor: "pointer", fontSize: "0.75rem" }}>✕</button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={b.id} data-testid={`advertiser-brand-row-${b.id}`}>
                  <td style={S.td} data-testid={`advertiser-brand-display-code-${b.id}`}>{b.code}</td>
                  <td style={S.td} data-testid={`advertiser-brand-display-name-${b.id}`}>{b.name}</td>
                  <td style={S.td}>{b.description ?? "—"}</td>
                  <td style={S.td} data-testid={`advertiser-brand-display-status-${b.id}`}>
                    <span style={S.badge(statusColor(b.status))}>{statusLabel(b.status)}</span>
                  </td>
                  {canEdit && (
                    <td style={S.td}>
                      <button data-testid={`advertiser-brand-edit-${b.id}`} onClick={() => startEdit(b)}
                        style={{ padding: "0.2rem 0.4rem", cursor: "pointer", fontSize: "0.75rem" }}>Ред.</button>
                    </td>
                  )}
                </tr>
              )
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function ContractsTab({ contracts, orgId, onContractChange }: { contracts: AdvertiserContractOut[]; orgId: string; onContractChange: () => void }) {
  const { user } = useAuth();
  const canEdit = user?.permissions?.includes("advertisers.manage") ?? false;

  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState<string | null>(null); // contract id being uploaded
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pendingFile, setPendingFile] = useState<{ contractId: string; file: File } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pendingContractRef = useRef<string>("");

  const [form, setForm] = useState({
    code: "", name: "", contract_number: "",
    budget_limit_amount: "", budget_limit_currency: "RUB",
    valid_from: "", valid_until: "",
  });

  function resetForm() {
    setForm({ code: "", name: "", contract_number: "", budget_limit_amount: "", budget_limit_currency: "RUB", valid_from: "", valid_until: "" });
    setCreating(false);
    setEditingId(null);
    setError("");
    setSuccess("");
    setUploading(null);
  }

  function extractDetail(err: unknown): string {
    if (err instanceof ApiError && typeof err.body === "object" && err.body !== null && "detail" in err.body) {
      return String((err.body as Record<string, unknown>).detail);
    }
    if (err instanceof Error) return err.message;
    return String(err);
  }

  async function handleCreate() {
    setError(""); setSuccess(""); setSaving(true);
    try {
      const body: AdvertiserContractCreate = {
        advertiser_organization_id: orgId,
        code: form.code,
        name: form.name,
        contract_number: form.contract_number || undefined,
        budget_limit_amount: form.budget_limit_amount ? parseFloat(form.budget_limit_amount) : undefined,
        budget_limit_currency: form.budget_limit_currency,
        valid_from: form.valid_from ? new Date(form.valid_from).toISOString() : undefined,
        valid_until: form.valid_until ? new Date(form.valid_until).toISOString() : undefined,
      };
      await createAdvertiserContract(body);
      setSuccess("Договор создан");
      resetForm();
      onContractChange();
    } catch (e: unknown) {
      setError(extractDetail(e));
    } finally {
      setSaving(false);
    }
  }

  async function handleUpdate(contractId: string) {
    setError(""); setSuccess(""); setSaving(true);
    try {
      const body: AdvertiserContractUpdate = {
        code: form.code || undefined,
        name: form.name || undefined,
        contract_number: form.contract_number || undefined,
        budget_limit_amount: form.budget_limit_amount ? parseFloat(form.budget_limit_amount) : undefined,
        budget_limit_currency: form.budget_limit_currency || undefined,
        valid_from: form.valid_from ? new Date(form.valid_from).toISOString() : undefined,
        valid_until: form.valid_until ? new Date(form.valid_until).toISOString() : undefined,
      };
      const updated = await updateAdvertiserContract(contractId, orgId, body);
      setSuccess(`Договор «${updated.name}» обновлён`);
      resetForm();
      onContractChange();
    } catch (e: unknown) {
      setError(extractDetail(e));
    } finally {
      setSaving(false);
    }
  }

  function startEdit(c: AdvertiserContractOut) {
    setForm({
      code: c.code,
      name: c.name,
      contract_number: c.contract_number ?? "",
      budget_limit_amount: c.budget_limit_amount != null ? String(c.budget_limit_amount) : "",
      budget_limit_currency: c.budget_limit_currency,
      valid_from: c.valid_from ? new Date(c.valid_from).toISOString().slice(0, 10) : "",
      valid_until: c.valid_until ? new Date(c.valid_until).toISOString().slice(0, 10) : "",
    });
    setEditingId(c.id);
    setCreating(false);
    setError("");
    setSuccess("");
  }

  async function handleFileUpload(contractId: string, contractCode: string, file: File) {
    setError(""); setSuccess(""); setUploading(contractId);
    try {
      // Step 1: upload-intent
      const intent = await createContractUploadIntent(contractId, {
        filename: file.name,
        content_type: file.type || "application/pdf",
        content_length: file.size,
      });
      // Step 2: PUT to MinIO
      const putResp = await fetch(intent.upload_url, {
        method: "PUT",
        headers: intent.headers,
        body: file,
      });
      if (!putResp.ok) {
        throw new Error(`Upload failed: ${putResp.status} ${putResp.statusText}`);
      }
      // Step 3: complete-upload
      await completeContractUpload(contractId, { upload_id: intent.upload_id });
      setSuccess(`Файл «${file.name}» загружен для договора «${contractCode}»`);
      setUploading(null);
      onContractChange();
    } catch (e: unknown) {
      setError(extractDetail(e));
      setUploading(null);
    }
  }

  function handleFileTrigger(contractId: string) {
    // Click hidden file input — Playwright's filechooser can intercept this
    const input = document.getElementById(`contract-file-input-${contractId}`);
    if (input) {
      (input as HTMLInputElement).click();
    } else {
      // Fallback: show file dialog via programmatic input
      const tmp = document.createElement("input");
      tmp.type = "file";
      tmp.accept = ".pdf,application/pdf";
      tmp.onchange = (ev: Event) => {
        const target = ev.target as HTMLInputElement;
        if (target.files?.[0]) {
          const c = contracts.find((x) => x.id === contractId);
          handleFileUpload(contractId, c?.code ?? "", target.files[0]);
        }
      };
      tmp.click();
    }
  }

  function fmtDate(d: string | null | undefined): string {
    if (!d) return "—";
    try { return new Date(d).toLocaleDateString("ru-RU"); } catch { return "—"; }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "0.35rem 0.5rem", border: "1px solid #e2e8f0",
    borderRadius: 4, fontSize: "0.875rem", boxSizing: "border-box",
  };
  const narrowInput: React.CSSProperties = { ...inputStyle, width: "100%" };

  return (
    <div data-testid="advertiser-contracts-section">
      {error && <div data-testid="advertiser-contract-error" style={{ color: "#dc2626", marginBottom: "0.5rem", fontSize: "0.875rem" }}>{error}</div>}
      {success && <div data-testid="advertiser-contract-success" style={{ color: "#16a34a", marginBottom: "0.5rem", fontSize: "0.875rem" }}>{success}</div>}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
        <h4 style={{ margin: 0, fontSize: "0.9rem" }}>Договоры</h4>
        {canEdit && !creating && (
          <button data-testid="advertiser-contract-create-open" onClick={() => { setCreating(true); setEditingId(null); setForm({ code: "", name: "", contract_number: "", budget_limit_amount: "", budget_limit_currency: "RUB", valid_from: "", valid_until: "" }); setError(""); setSuccess(""); }}
            style={{ padding: "0.35rem 0.75rem", cursor: "pointer", fontSize: "0.8125rem" }}>Добавить договор</button>
        )}
      </div>

      {creating && (
        <div style={{ border: "1px solid #e2e8f0", borderRadius: 6, padding: "0.75rem", marginBottom: "0.75rem", background: "#f8fafc" }}>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", marginBottom: "0.5rem" }}>
            <div>
              <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Код *</div>
              <input data-testid="advertiser-contract-number" style={inputStyle} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Название *</div>
              <input data-testid="advertiser-contract-title" style={inputStyle} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>№ договора</div>
              <input data-testid="advertiser-contract-contract-number" style={inputStyle} value={form.contract_number} onChange={(e) => setForm({ ...form, contract_number: e.target.value })} />
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Бюджет</div>
              <input data-testid="advertiser-contract-budget" style={inputStyle} type="number" value={form.budget_limit_amount} onChange={(e) => setForm({ ...form, budget_limit_amount: e.target.value })} />
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Действует с</div>
              <input data-testid="advertiser-contract-starts-at" style={inputStyle} type="date" value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} />
            </div>
            <div>
              <div style={{ fontSize: "0.8rem", marginBottom: "0.2rem", color: "#64748b" }}>Действует по</div>
              <input data-testid="advertiser-contract-ends-at" style={inputStyle} type="date" value={form.valid_until} onChange={(e) => setForm({ ...form, valid_until: e.target.value })} />
            </div>
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button onClick={resetForm} style={{ padding: "0.35rem 0.75rem", cursor: "pointer", fontSize: "0.8125rem" }}>Отмена</button>
            <button data-testid="advertiser-contract-submit" onClick={handleCreate} disabled={saving}
              style={{ padding: "0.35rem 0.75rem", cursor: "pointer", fontSize: "0.8125rem", background: "#2563eb", color: "#fff", border: "none", borderRadius: 4 }}>Сохранить</button>
          </div>
        </div>
      )}

      {contracts.length === 0 && !creating ? (
        <div data-testid="advertiser-contract-empty" style={S.empty}>Нет договоров</div>
      ) : (
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>Код</th>
              <th style={S.th}>Название</th>
              <th style={S.th}>№ договора</th>
              <th style={S.th}>Бюджет</th>
              <th style={S.th}>Действует</th>
              <th style={S.th}>Статус</th>
              <th style={S.th}>Файл</th>
              {canEdit && <th style={{ ...S.th, width: 80 }}></th>}
            </tr>
          </thead>
          <tbody>
            {contracts.map((c) => (
              editingId === c.id ? (
                <tr key={c.id} data-testid={`advertiser-contract-row-${c.id}`}>
                  <td style={S.td}><input style={inputStyle} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} /></td>
                  <td style={S.td}><input style={inputStyle} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></td>
                  <td style={S.td}><input style={inputStyle} value={form.contract_number} onChange={(e) => setForm({ ...form, contract_number: e.target.value })} /></td>
                  <td style={S.td}><input style={narrowInput} type="number" value={form.budget_limit_amount} onChange={(e) => setForm({ ...form, budget_limit_amount: e.target.value })} /></td>
                  <td style={S.td}><input style={narrowInput} type="date" value={form.valid_from} onChange={(e) => setForm({ ...form, valid_from: e.target.value })} /></td>
                  <td style={S.td}><span style={S.badge(statusColor(c.status))}>{statusLabel(c.status)}</span></td>
                  <td style={S.td}>{c.file_name ?? "—"}</td>
                  <td style={S.td}>
                    <div style={{ display: "flex", gap: "0.25rem" }}>
                      <button onClick={() => handleUpdate(c.id)} disabled={saving} style={{ padding: "0.2rem 0.4rem", cursor: "pointer", fontSize: "0.75rem" }}>✓</button>
                      <button onClick={resetForm} style={{ padding: "0.2rem 0.4rem", cursor: "pointer", fontSize: "0.75rem" }}>✕</button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={c.id} data-testid={`advertiser-contract-row-${c.id}`}>
                  <td style={S.td} data-testid={`advertiser-contract-display-number-${c.id}`}>{c.code}</td>
                  <td style={S.td} data-testid={`advertiser-contract-display-title-${c.id}`}>{c.name}</td>
                  <td style={S.td}>{c.contract_number ?? "—"}</td>
                  <td style={S.td}>
                    {c.budget_limit_amount != null
                      ? `${c.budget_limit_amount.toLocaleString("ru-RU")} ${c.budget_limit_currency}`
                      : "—"}
                  </td>
                  <td style={S.td}>{fmtDate(c.valid_from)} – {fmtDate(c.valid_until)}</td>
                  <td style={S.td}>
                    <span style={S.badge(statusColor(c.status))}>{statusLabel(c.status)}</span>
                  </td>
                  <td style={S.td} data-testid={`advertiser-contract-display-file-${c.id}`}>
                    {c.file_name ? (
                      <span>{c.file_name}{c.file_size_bytes ? ` (${(c.file_size_bytes / 1024).toFixed(1)} KB)` : ""}</span>
                    ) : pendingFile && pendingFile.contractId === c.id ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
                        <span data-testid="advertiser-contract-selected-file" style={{ fontSize: "0.75rem", color: "#0c4a6e" }}>
                          📄 {pendingFile.file.name}
                        </span>
                        <button data-testid="advertiser-contract-upload-done"
                          style={{ padding: "0.15rem 0.4rem", cursor: "pointer", fontSize: "0.7rem", background: "#16a34a", color: "#fff", border: "none", borderRadius: 3 }}
                          onClick={() => {
                            handleFileUpload(c.id, c.code, pendingFile.file);
                            setPendingFile(null);
                          }}
                        >Загрузить</button>
                      </span>
                    ) : canEdit ? (
                      <button data-testid={`advertiser-contract-upload-${c.id}`}
                        style={{ padding: "0.2rem 0.4rem", cursor: "pointer", fontSize: "0.75rem", background: "#f1f5f9", border: "1px solid #e2e8f0", borderRadius: 3 }}
                        onClick={() => {
                          pendingContractRef.current = c.id;
                          fileInputRef.current?.click();
                        }}
                      >📎 Выбрать PDF</button>
                    ) : "—"}
                  </td>
                  {canEdit && (
                    <td style={S.td}>
                      <button data-testid={`advertiser-contract-edit-${c.id}`} onClick={() => startEdit(c)}
                        style={{ padding: "0.2rem 0.4rem", cursor: "pointer", fontSize: "0.75rem" }}>Ред.</button>
                    </td>
                  )}
                </tr>
              )
            ))}
          </tbody>
        </table>
      )}

      {/* Hidden file input for contract PDF upload — driven by visible button via ref */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        style={{ display: "none" }}
        data-testid="advertiser-contract-file-input"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          setPendingFile({ contractId: pendingContractRef.current, file: f });
          e.target.value = "";
        }}
      />
    </div>
  );
}

function ContactsTab({ contacts, users, orgId, onContactChange: _onContactChange }: { contacts: AdvertiserContactOut[]; users: AdvertiserUserMembershipOut[]; orgId: string; onContactChange: () => void }) {
  const { user } = useAuth();
  const canManage = user?.permissions?.includes("advertisers.manage") ?? false;
  // Local contacts list — avoids unmount on parent refetch (ADVERTISER-UX-001B3)
  const [localContacts, setLocalContacts] = useState<AdvertiserContactOut[]>(contacts);
  const contactsRef = useRef(contacts);
  // Sync from prop only when prop truly changes (not on our own writes)
  useEffect(() => {
    if (contacts !== contactsRef.current) {
      contactsRef.current = contacts;
      setLocalContacts(contacts);
    }
  }, [contacts]);
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState({ full_name: "", email: "", phone: "", title: "", user_id: "" });
  const [editForm, setEditForm] = useState({ full_name: "", email: "", phone: "", title: "", user_id: "" });

  // only advertiser (local_advertiser) users for link dropdown
  const advertiserUsers = useMemo(() => users.filter((u) => u.auth_provider === "local_advertiser"), [users]);

  function resetForm() {
    setForm({ full_name: "", email: "", phone: "", title: "", user_id: "" });
    setError("");
    setSuccess("");
  }

  function startCreate() { resetForm(); setCreating(true); setEditingId(null); }
  function cancelCreate() { setCreating(false); resetForm(); }

  function startEdit(c: AdvertiserContactOut) {
    setEditingId(c.id);
    setCreating(false);
    setEditForm({
      full_name: c.full_name,
      email: c.email,
      phone: c.phone ?? "",
      title: c.title ?? "",
      user_id: c.user_id ?? "",
    });
    setError("");
    setSuccess("");
  }

  function cancelEdit() { setEditingId(null); resetForm(); }

  async function handleCreate() {
    setError(""); setSuccess("");
    if (!form.full_name.trim()) { setError("Укажите имя контакта"); return; }
    if (!form.email.trim()) { setError("Укажите email"); return; }
    try {
      const created = await createAdvertiserContact({
        advertiser_organization_id: orgId,
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        phone: form.phone.trim() || null,
        title: form.title.trim() || null,
        user_id: form.user_id || null,
      });
      setSuccess("Контакт создан");
      setCreating(false);
      setForm({ full_name: "", email: "", phone: "", title: "", user_id: "" });
      // Optimistic local update — avoid unmount via parent refetch
      setLocalContacts((prev) => [...prev, created]);
      contactsRef.current = [...contactsRef.current, created];
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : "Ошибка создания контакта");
      setError(msg);
    }
  }

  async function handleUpdate(contactId: string) {
    setError(""); setSuccess("");
    try {
      const updated = await updateAdvertiserContact(contactId, orgId, {
        full_name: editForm.full_name.trim() || undefined,
        email: editForm.email.trim() || undefined,
        phone: editForm.phone.trim() || undefined,
        title: editForm.title.trim() || undefined,
        user_id: editForm.user_id || null,
      });
      setSuccess("Контакт обновлён");
      setEditingId(null);
      // Optimistic local update
      setLocalContacts((prev) => prev.map((c) => c.id === contactId ? updated : c));
      contactsRef.current = contactsRef.current.map((c) => c.id === contactId ? updated : c);
    } catch (e: unknown) {
      const msg = e instanceof ApiError ? e.message : (e instanceof Error ? e.message : "Ошибка обновления контакта");
      setError(msg);
    }
  }

  function getUserLinkInfo(userId: string | null) {
    if (!userId) return null;
    return users.find((u) => u.user_id === userId) ?? null;
  }

  const isEmpty = localContacts.length === 0 && !creating;

  return (
    <div data-testid="advertiser-contacts-section">
      {error && <div style={S.fieldError} data-testid="advertiser-contact-error">{error}</div>}
      {success && <div style={{ ...S.fieldSuccess }} data-testid="advertiser-contact-success">{success}</div>}

      {/* Create button */}
      {canManage && !creating && (
        <div style={{ marginBottom: 12 }}>
          <button style={S.btnPrimarySmall} onClick={startCreate} data-testid="advertiser-contact-create-open">
            + Добавить контакт
          </button>
        </div>
      )}

      {/* Create form */}
      {creating && (
        <div style={{ marginBottom: 16, padding: 12, background: "#f9fafb", borderRadius: 6 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Новый контакт</div>
          <input style={S.input} placeholder="ФИО" value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} data-testid="advertiser-contact-name" />
          <input style={S.input} placeholder="Email" value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} data-testid="advertiser-contact-email" />
          <input style={S.input} placeholder="Телефон" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} data-testid="advertiser-contact-phone" />
          <input style={S.input} placeholder="Должность" value={form.title} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} data-testid="advertiser-contact-title" />
          {advertiserUsers.length > 0 && (
            <select style={S.select} value={form.user_id} onChange={(e) => setForm((f) => ({ ...f, user_id: e.target.value }))} data-testid="advertiser-contact-user-link">
              <option value="">Без привязки к учётной записи</option>
              {advertiserUsers.map((u) => (
                <option key={u.user_id} value={u.user_id}>{u.username} ({u.display_name})</option>
              ))}
            </select>
          )}
          <div style={{ marginTop: 8, display: "flex", gap: 8 }}>
            <button style={S.btnPrimarySmall} onClick={handleCreate} data-testid="advertiser-contact-submit">Сохранить</button>
            <button style={S.btnSecondarySmall} onClick={cancelCreate}>Отмена</button>
          </div>
        </div>
      )}

      {/* Empty state */}
      {isEmpty && <div style={S.empty} data-testid="advertiser-contact-empty">Нет контактов</div>}

      {/* Contact list */}
      {localContacts.length > 0 && (
        <table style={S.table} data-testid="advertiser-contacts-table">
          <thead>
            <tr>
              <th style={S.th}>ФИО</th>
              <th style={S.th}>Email</th>
              <th style={S.th}>Телефон</th>
              <th style={S.th}>Должность</th>
              <th style={S.th}>Учётная запись</th>
              {canManage && <th style={S.th}></th>}
            </tr>
          </thead>
          <tbody>
            {localContacts.map((c) => {
              const isEditing = editingId === c.id;
              const linkedUser = getUserLinkInfo(c.user_id);
              return (
                <tr key={c.id} data-testid={`advertiser-contact-row-${c.id}`}>
                  {isEditing ? (
                    <>
                      <td style={S.td}><input style={S.inputSmall} value={editForm.full_name} onChange={(e) => setEditForm((f) => ({ ...f, full_name: e.target.value }))} data-testid="advertiser-contact-edit-name" /></td>
                      <td style={S.td}><input style={S.inputSmall} value={editForm.email} onChange={(e) => setEditForm((f) => ({ ...f, email: e.target.value }))} data-testid="advertiser-contact-edit-email" /></td>
                      <td style={S.td}><input style={S.inputSmall} value={editForm.phone} onChange={(e) => setEditForm((f) => ({ ...f, phone: e.target.value }))} /></td>
                      <td style={S.td}><input style={S.inputSmall} value={editForm.title} onChange={(e) => setEditForm((f) => ({ ...f, title: e.target.value }))} /></td>
                      <td style={S.td}>
                        {advertiserUsers.length > 0 && (
                          <select style={S.selectSmall} value={editForm.user_id} onChange={(e) => setEditForm((f) => ({ ...f, user_id: e.target.value }))}>
                            <option value="">—</option>
                            {advertiserUsers.map((u) => (<option key={u.user_id} value={u.user_id}>{u.username}</option>))}
                          </select>
                        )}
                      </td>
                      <td style={S.td}>
                        <button style={S.btnPrimarySmall} onClick={() => handleUpdate(c.id)}>✓</button>
                        <button style={{ ...S.btnSecondarySmall, marginLeft: 4 }} onClick={cancelEdit}>✕</button>
                      </td>
                    </>
                  ) : (
                    <>
                      <td style={S.td} data-testid={`advertiser-contact-display-name-${c.id}`}>{c.full_name}</td>
                      <td style={S.td} data-testid={`advertiser-contact-display-email-${c.id}`}>{c.email}</td>
                      <td style={S.td}>{c.phone ?? "—"}</td>
                      <td style={S.td}>{c.title ?? "—"}</td>
                      <td style={S.td} data-testid={`advertiser-contact-display-user-${c.id}`}>
                        {linkedUser ? `${linkedUser.username} (${linkedUser.display_name})` : "—"}
                      </td>
                      {canManage && (
                        <td style={S.td}>
                          <button style={S.btnEditSmall} onClick={() => startEdit(c)} data-testid={`advertiser-contact-edit-${c.id}`}>Ред.</button>
                        </td>
                      )}
                    </>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

function UsersTab({ users }: { users: AdvertiserUserMembershipOut[] }) {
  if (users.length === 0) return <div style={S.empty} data-testid="advertiser-detail-users-empty">Нет привязанных пользователей</div>;
  return (
    <div data-testid="advertiser-detail-users">
    <table style={S.table}>
      <thead>
        <tr>
          <th style={S.th}>Логин</th>
          <th style={S.th}>Имя</th>
          <th style={S.th}>Email</th>
          <th style={S.th}>Тип входа</th>
          <th style={S.th}>Смена пароля</th>
          <th style={S.th}>Статус</th>
          <th style={S.th}>Членство</th>
        </tr>
      </thead>
      <tbody>
        {users.map((u) => (
          <tr key={u.id}>
            <td style={S.td}>{u.username}</td>
            <td style={S.td}>{u.display_name}</td>
            <td style={S.td}>{u.email ?? "—"}</td>
            <td style={S.td}>{authProviderLabel(u.auth_provider)}</td>
            <td style={S.td}>{u.must_change_password ? "Требуется" : "—"}</td>
            <td style={S.td}>
              <span style={S.badge(statusColor(u.user_status))}>{statusLabel(u.user_status)}</span>
            </td>
            <td style={S.td}>
              <span style={S.badge(statusColor(u.membership_status))}>{statusLabel(u.membership_status)}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
    </div>
  );
}