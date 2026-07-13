import { useState, useEffect, useMemo } from "react";
import {
  listAdvertisers,
  listBrands,
  listContracts,
  getAdvertiserDetail,
  listBrandsByOrg,
  listContractsByOrg,
  listContactsByOrg,
  listMemberships,
} from "../api/campaigns";
import { ApiError } from "../api/client";
import type {
  AdvertiserOrganizationOut,
  AdvertiserOrganizationDetailOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  AdvertiserContactOut,
  AdvertiserUserMembershipOut,
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
};

// ── Helpers ──

const TABS = ["Обзор", "Бренды", "Договоры", "Контакты", "Пользователи"] as const;
type Tab = (typeof TABS)[number];

// ── Component ──

export default function AdvertisersPage() {
  const [pageState, setPageState] = useState<PageState>({ stage: "loading" });
  const [detailState, setDetailState] = useState<DetailState>({ stage: "idle" });
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("Обзор");
  const [search, setSearch] = useState("");

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
  }, [selectedOrgId]);

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
        <div style={S.detailPanel}>
          <div style={S.tabs}>
            {TABS.map((t) => (
              <div key={t} style={S.tab(activeTab === t)} onClick={() => setActiveTab(t)}>
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
              <RenderTab tab={activeTab} data={detailState.data} />
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Tab Renderers ──

function RenderTab({ tab, data }: { tab: Tab; data: DetailData }) {
  switch (tab) {
    case "Обзор":
      return <OverviewTab org={data.org} />;
    case "Бренды":
      return <BrandsTab brands={data.brands} />;
    case "Договоры":
      return <ContractsTab contracts={data.contracts} />;
    case "Контакты":
      return <ContactsTab contacts={data.contacts} />;
    case "Пользователи":
      return <UsersTab users={data.users} />;
  }
}

function OverviewTab({ org }: { org: AdvertiserOrganizationDetailOut }) {
  return (
    <div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Код</div>
        <div style={S.fieldValue}>{org.code}</div>
      </div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Название</div>
        <div style={S.fieldValue}>{org.display_name}</div>
      </div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Юридическое название</div>
        <div style={S.fieldValue}>{org.legal_name}</div>
      </div>
      <div style={S.fieldGroup}>
        <div style={S.fieldLabel}>Статус</div>
        <div style={S.fieldValue}>
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

function BrandsTab({ brands }: { brands: AdvertiserBrandOut[] }) {
  if (brands.length === 0) return <div style={S.empty}>Нет брендов</div>;
  return (
    <table style={S.table}>
      <thead>
        <tr>
          <th style={S.th}>Код</th>
          <th style={S.th}>Название</th>
          <th style={S.th}>Описание</th>
          <th style={S.th}>Статус</th>
        </tr>
      </thead>
      <tbody>
        {brands.map((b) => (
          <tr key={b.id}>
            <td style={S.td}>{b.code}</td>
            <td style={S.td}>{b.name}</td>
            <td style={S.td}>{b.description ?? "—"}</td>
            <td style={S.td}>
              <span style={S.badge(statusColor(b.status))}>{statusLabel(b.status)}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ContractsTab({ contracts }: { contracts: AdvertiserContractOut[] }) {
  if (contracts.length === 0) return <div style={S.empty}>Нет договоров</div>;
  return (
    <table style={S.table}>
      <thead>
        <tr>
          <th style={S.th}>Код</th>
          <th style={S.th}>Название</th>
          <th style={S.th}>№ договора</th>
          <th style={S.th}>Бюджет</th>
          <th style={S.th}>Действует с</th>
          <th style={S.th}>Действует по</th>
          <th style={S.th}>Статус</th>
        </tr>
      </thead>
      <tbody>
        {contracts.map((c) => (
          <tr key={c.id}>
            <td style={S.td}>{c.code}</td>
            <td style={S.td}>{c.name}</td>
            <td style={S.td}>{c.contract_number ?? "—"}</td>
            <td style={S.td}>
              {c.budget_limit_amount != null
                ? `${c.budget_limit_amount.toLocaleString("ru-RU")} ${c.budget_limit_currency}`
                : "—"}
            </td>
            <td style={S.td}>{c.valid_from ? new Date(c.valid_from).toLocaleDateString("ru-RU") : "—"}</td>
            <td style={S.td}>{c.valid_until ? new Date(c.valid_until).toLocaleDateString("ru-RU") : "—"}</td>
            <td style={S.td}>
              <span style={S.badge(statusColor(c.status))}>{statusLabel(c.status)}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ContactsTab({ contacts }: { contacts: AdvertiserContactOut[] }) {
  if (contacts.length === 0) return <div style={S.empty}>Нет контактов</div>;
  return (
    <table style={S.table}>
      <thead>
        <tr>
          <th style={S.th}>Тип</th>
          <th style={S.th}>ФИО</th>
          <th style={S.th}>Email</th>
          <th style={S.th}>Телефон</th>
          <th style={S.th}>Основной</th>
          <th style={S.th}>Статус</th>
        </tr>
      </thead>
      <tbody>
        {contacts.map((c) => (
          <tr key={c.id}>
            <td style={S.td}>{contactTypeLabel(c.contact_type)}</td>
            <td style={S.td}>{c.full_name}</td>
            <td style={S.td}>{c.email}</td>
            <td style={S.td}>{c.phone ?? "—"}</td>
            <td style={S.td}>{c.is_primary ? "✓" : ""}</td>
            <td style={S.td}>
              <span style={S.badge(statusColor(c.status))}>{statusLabel(c.status)}</span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function UsersTab({ users }: { users: AdvertiserUserMembershipOut[] }) {
  if (users.length === 0) return <div style={S.empty}>Нет привязанных пользователей</div>;
  return (
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
  );
}