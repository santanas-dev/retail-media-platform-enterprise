import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  getCampaign,
  getFlightsByCampaign,
  getPlacementsByCampaign,
  getCreativesByCampaign,
  listAdvertisers,
  listBrands,
  listContracts,
  getApprovalsByCampaign,
} from "../api/campaigns";
import type {
  CampaignOut,
  CampaignFlightOut,
  CampaignPlacementOut,
  CampaignCreativeOut,
  CreativeAssetOut,
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  CampaignApprovalOut,
} from "../api/types";
import { statusLabel, statusColor, STATUS_LABELS } from "../api/types";

type Tab = "overview" | "flights" | "placements" | "creatives" | "reporting";

interface DetailData {
  campaign: CampaignOut;
  flights: CampaignFlightOut[];
  placements: CampaignPlacementOut[];
  creatives: Array<CampaignCreativeOut & { asset: CreativeAssetOut | null }>;
  org: AdvertiserOrganizationOut | null;
  brand: AdvertiserBrandOut | null;
  contract: AdvertiserContractOut | null;
  approvals: CampaignApprovalOut[];
}

export default function CampaignDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<DetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("overview");

  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    async function load() {
      try {
        const campaign = await getCampaign(id!);

        if (cancelled) return;

        if (!campaign) {
          setError("Кампания не найдена");
          setLoading(false);
          return;
        }

        const [
          flights,
          placements,
          creatives,
          orgs,
          brands,
          contracts,
          approvals,
        ] = await Promise.all([
          getFlightsByCampaign(campaign.id),
          getPlacementsByCampaign(campaign.id),
          getCreativesByCampaign(campaign.id),
          listAdvertisers(),
          listBrands(),
          listContracts(),
          getApprovalsByCampaign(campaign.id),
        ]);

        if (cancelled) return;

        const orgMap = new Map(orgs.map((o) => [o.id, o]));
        const brandMap = new Map(brands.map((b) => [b.id, b]));
        const contractMap = new Map(contracts.map((c) => [c.id, c]));

        setData({
          campaign,
          flights,
          placements,
          creatives: creatives.sort(
            (a, b) => a.sort_order - b.sort_order,
          ),
          org: orgMap.get(campaign.advertiser_organization_id) ?? null,
          brand: campaign.advertiser_brand_id
            ? brandMap.get(campaign.advertiser_brand_id) ?? null
            : null,
          contract: contractMap.get(campaign.advertiser_contract_id) ?? null,
          approvals,
        });
      } catch (e: unknown) {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Ошибка загрузки");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [id]);

  // ── Render states ──

  if (loading) {
    return (
      <div style={css.centered}>
        <p style={css.muted}>Загрузка...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={css.centered}>
        <div style={css.errorBox}>
          <p style={{ margin: 0, fontWeight: 600 }}>Ошибка</p>
          <p style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.875rem" }}>{error}</p>
          <button
            type="button"
            style={css.linkBtn}
            onClick={() => navigate("/campaigns")}
          >
            ← К списку кампаний
          </button>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={css.centered}>
        <div style={css.errorBox}>
          <p style={{ margin: 0, fontWeight: 600 }}>Кампания не найдена</p>
          <p style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.875rem", color: "#64748b" }}>
            ID: {id}
          </p>
          <button
            type="button"
            style={css.linkBtn}
            onClick={() => navigate("/campaigns")}
          >
            ← К списку кампаний
          </button>
        </div>
      </div>
    );
  }

  const { campaign, flights, placements, creatives, org, brand, contract, approvals } = data;

  // ── Helpers ──

  function fmtDate(iso: string | null): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });
  }

  function fmtDateTime(iso: string): string {
    return new Date(iso).toLocaleString("ru-RU", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function fmtAmount(amount: number | null, currency: string): string {
    if (amount == null) return "—";
    return new Intl.NumberFormat("ru-RU", {
      style: "currency",
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  }

  // ── Tab content ──

  function renderOverview() {
    return (
      <div style={css.section}>
        <div style={css.fieldGrid}>
          <Field label="Код" value={campaign.code} />
          <Field label="Название" value={campaign.name} />
          <Field
            label="Статус"
            value={
              <span
                style={{
                  ...css.badge,
                  background: statusColor(campaign.status),
                  display: "inline-block",
                  padding: "0.15rem 0.5rem",
                  borderRadius: 999,
                  fontSize: "0.8rem",
                  fontWeight: 500,
                  color: "#fff",
                }}
              >
                {statusLabel(campaign.status)}
              </span>
            }
          />
          <Field label="Приоритет" value={String(campaign.priority)} />
          <Field
            label="Бюджет"
            value={fmtAmount(campaign.budget_limit_amount, campaign.budget_limit_currency)}
          />
          <Field
            label="Период кампании"
            value={`${fmtDate(campaign.start_at)} – ${fmtDate(campaign.end_at)}`}
          />
          <Field label="Часовой пояс" value={campaign.timezone} />
          {campaign.description && (
            <FieldSpan label="Описание" value={campaign.description} />
          )}
        </div>

        <h3 style={css.subheading}>Рекламодатель</h3>
        <div style={css.fieldGrid}>
          <Field label="Организация" value={org?.display_name ?? org?.legal_name ?? campaign.advertiser_organization_id} />
          <Field label="Бренд" value={brand?.name ?? "—"} />
          <Field label="Договор" value={contract?.code ?? campaign.advertiser_contract_id} />
          <Field label="Статус договора" value={contract?.status ? statusLabel(contract.status) : "—"} />
          {contract?.valid_from && (
            <Field
              label="Действие договора"
              value={`${fmtDate(contract.valid_from)} – ${fmtDate(contract.valid_until)}`}
            />
          )}
        </div>

        <h3 style={css.subheading}>Метаданные</h3>
        <div style={css.fieldGrid}>
          <Field label="Создан" value={fmtDateTime(campaign.created_at)} />
          <Field label="Обновлён" value={fmtDateTime(campaign.updated_at)} />
          <Field label="Кем создан" value={campaign.created_by ?? "—"} />
        </div>

        {approvals.length > 0 && (
          <>
            <h3 style={css.subheading}>История согласований</h3>
            <div style={{ fontSize: "0.8rem" }}>
              {approvals.map((a) => (
                <div key={a.id} style={{ padding: "0.25rem 0", borderBottom: "1px solid #f1f5f9" }}>
                  <strong>{a.action}</strong> — {fmtDateTime(a.created_at)}
                  {a.reason ? ` — ${a.reason}` : ""}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    );
  }

  function renderFlights() {
    if (flights.length === 0) {
      return (
        <div style={css.section}>
          <p style={css.muted}>У этой кампании пока нет флайтов.</p>
        </div>
      );
    }

    return (
      <div style={css.section}>
        <table style={css.miniTable}>
          <thead>
            <tr>
              <th style={css.miniTh}>Название</th>
              <th style={css.miniTh}>Начало</th>
              <th style={css.miniTh}>Конец</th>
              <th style={css.miniTh}>Приоритет</th>
            </tr>
          </thead>
          <tbody>
            {flights
              .sort(
                (a, b) =>
                  new Date(a.start_at).getTime() - new Date(b.start_at).getTime(),
              )
              .map((f) => (
                <tr key={f.id}>
                  <td style={css.miniTd}>{f.name ?? "—"}</td>
                  <td style={css.miniTd}>{fmtDate(f.start_at)}</td>
                  <td style={css.miniTd}>{fmtDate(f.end_at)}</td>
                  <td style={css.miniTd}>{f.priority}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    );
  }

  function renderPlacements() {
    if (placements.length === 0) {
      return (
        <div style={css.section}>
          <p style={css.muted}>У этой кампании пока нет плейсментов.</p>
        </div>
      );
    }

    return (
      <div style={css.section}>
        <table style={css.miniTable}>
          <thead>
            <tr>
              <th style={css.miniTh}>ID</th>
              <th style={css.miniTh}>Surface</th>
              <th style={css.miniTh}>Store</th>
              <th style={css.miniTh}>SOV %</th>
              <th style={css.miniTh}>Показы</th>
              <th style={css.miniTh}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {placements.map((p) => (
              <tr key={p.id}>
                <td style={{ ...css.miniTd, fontSize: "0.75rem", fontFamily: "monospace" }}>
                  {p.id.slice(0, 8)}...
                </td>
                <td style={{ ...css.miniTd, fontSize: "0.75rem", fontFamily: "monospace" }}>
                  {p.display_surface_id?.slice(0, 8) ?? "—"}
                </td>
                <td style={{ ...css.miniTd, fontSize: "0.75rem", fontFamily: "monospace" }}>
                  {p.store_id?.slice(0, 8) ?? "—"}
                </td>
                <td style={css.miniTd}>{p.share_of_voice_pct}%</td>
                <td style={css.miniTd}>
                  {p.impressions_delivered}
                  {p.max_impressions ? ` / ${p.max_impressions}` : ""}
                </td>
                <td style={css.miniTd}>
                  <span
                    style={{
                      ...css.badge,
                      background: statusColor(p.status),
                      display: "inline-block",
                      padding: "0.1rem 0.4rem",
                      borderRadius: 999,
                      fontSize: "0.7rem",
                      fontWeight: 500,
                      color: "#fff",
                    }}
                  >
                    {statusLabel(p.status)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  function renderCreatives() {
    if (creatives.length === 0) {
      return (
        <div style={css.section}>
          <p style={css.muted}>У этой кампании пока нет креативов.</p>
        </div>
      );
    }

    return (
      <div style={css.section}>
        <table style={css.miniTable}>
          <thead>
            <tr>
              <th style={css.miniTh}>#</th>
              <th style={css.miniTh}>Ассет</th>
              <th style={css.miniTh}>Тип</th>
              <th style={css.miniTh}>Разрешение</th>
              <th style={css.miniTh}>Длит.</th>
              <th style={css.miniTh}>Статус</th>
            </tr>
          </thead>
          <tbody>
            {creatives.map((cc, i) => (
              <tr key={cc.id}>
                <td style={css.miniTd}>{i + 1}</td>
                <td style={css.miniTd}>
                  {cc.asset ? cc.asset.name : cc.creative_asset_id}
                </td>
                <td style={css.miniTd}>{cc.asset?.media_type ?? "—"}</td>
                <td style={css.miniTd}>
                  {cc.asset?.resolution_w && cc.asset?.resolution_h
                    ? `${cc.asset.resolution_w}×${cc.asset.resolution_h}`
                    : "—"}
                </td>
                <td style={css.miniTd}>
                  {cc.asset?.duration_ms != null
                    ? `${(cc.asset.duration_ms / 1000).toFixed(1)}с`
                    : "—"}
                </td>
                <td style={css.miniTd}>
                  {cc.asset
                    ? statusLabel(cc.asset.status)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  function renderReporting() {
    return (
      <div style={css.section}>
        <p style={css.muted}>
          Отчётность PoP пока недоступна — эндпоинты в разработке (Phase 4.3b).
        </p>
      </div>
    );
  }

  // ── Main render ──

  const tabNames: Record<Tab, string> = {
    overview: "Обзор",
    flights: "Флайты",
    placements: "Плейсменты",
    creatives: "Креативы",
    reporting: "Отчётность",
  };

  const tabs: Tab[] = ["overview", "flights", "placements", "creatives", "reporting"];

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <button
          type="button"
          style={css.linkBtn}
          onClick={() => navigate("/campaigns")}
        >
          ← К списку кампаний
        </button>
      </div>

      <h2 style={css.heading}>
        {campaign.name}
        <span style={{ fontSize: "0.7rem", color: "#94a3b8", marginLeft: "0.5rem", fontWeight: 400 }}>
          {campaign.code}
        </span>
      </h2>

      {/* Tabs */}
      <div style={css.tabBar}>
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            style={{
              ...css.tab,
              ...(activeTab === t ? css.tabActive : {}),
            }}
            onClick={() => setActiveTab(t)}
          >
            {tabNames[t]}
            {t === "flights" && flights.length > 0 && (
              <span style={css.tabCount}>{flights.length}</span>
            )}
            {t === "placements" && placements.length > 0 && (
              <span style={css.tabCount}>{placements.length}</span>
            )}
            {t === "creatives" && creatives.length > 0 && (
              <span style={css.tabCount}>{creatives.length}</span>
            )}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "overview" && renderOverview()}
      {activeTab === "flights" && renderFlights()}
      {activeTab === "placements" && renderPlacements()}
      {activeTab === "creatives" && renderCreatives()}
      {activeTab === "reporting" && renderReporting()}
    </div>
  );
}

// ── Small helper components ──

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div style={css.fieldLabel}>{label}</div>
      <div style={css.fieldValue}>{value}</div>
    </div>
  );
}

function FieldSpan({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ gridColumn: "1 / -1" }}>
      <div style={css.fieldLabel}>{label}</div>
      <div style={{ ...css.fieldValue, whiteSpace: "pre-wrap" }}>{value}</div>
    </div>
  );
}

// ── Styles ──

const css: Record<string, React.CSSProperties> = {
  heading: {
    margin: "0 0 1rem",
    fontSize: "1.25rem",
    fontWeight: 600,
  },
  subheading: {
    margin: "1.25rem 0 0.5rem",
    fontSize: "0.9rem",
    fontWeight: 600,
    color: "#334155",
    borderBottom: "1px solid #e2e8f0",
    paddingBottom: "0.25rem",
  },
  centered: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 200,
    flexDirection: "column" as const,
  },
  muted: {
    color: "#64748b",
    fontSize: "0.875rem",
  },
  errorBox: {
    background: "#fef2f2",
    color: "#991b1b",
    padding: "1rem",
    borderRadius: 6,
    maxWidth: 480,
  },
  linkBtn: {
    background: "none",
    border: "none",
    color: "#2563eb",
    cursor: "pointer",
    padding: 0,
    fontSize: "0.875rem",
    textDecoration: "underline" as const,
  },
  tabBar: {
    display: "flex",
    gap: 0,
    borderBottom: "2px solid #e2e8f0",
    marginBottom: "1rem",
  },
  tab: {
    padding: "0.5rem 0.75rem",
    background: "none",
    border: "none",
    borderBottom: "2px solid transparent",
    marginBottom: -2,
    cursor: "pointer",
    fontSize: "0.825rem",
    color: "#64748b",
    fontWeight: 500,
    display: "flex",
    alignItems: "center",
    gap: "0.35rem",
  },
  tabActive: {
    color: "#1e293b",
    borderBottomColor: "#2563eb",
  },
  tabCount: {
    background: "#e2e8f0",
    color: "#475569",
    borderRadius: 999,
    padding: "0 0.4rem",
    fontSize: "0.7rem",
    fontWeight: 600,
    lineHeight: "1.4",
  },
  section: {
    background: "#fff",
    borderRadius: 6,
    padding: "1rem",
    boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
  },
  fieldGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fill, minmax(240px, 1fr))",
    gap: "0.75rem",
  },
  fieldLabel: {
    fontSize: "0.7rem",
    fontWeight: 600,
    color: "#94a3b8",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
    marginBottom: "0.15rem",
  },
  fieldValue: {
    fontSize: "0.875rem",
    color: "#1e293b",
  },
  badge: {},
  miniTable: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.825rem",
  },
  miniTh: {
    textAlign: "left" as const,
    padding: "0.4rem 0.5rem",
    fontWeight: 600,
    color: "#475569",
    borderBottom: "1px solid #e2e8f0",
    fontSize: "0.7rem",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  },
  miniTd: {
    padding: "0.4rem 0.5rem",
    borderBottom: "1px solid #f1f5f9",
    verticalAlign: "middle" as const,
  },
};
