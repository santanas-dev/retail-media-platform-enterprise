import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import {
  listCampaigns,
  listFlights,
  listAdvertisers,
  listBrands,
} from "../api/campaigns";
import type {
  CampaignOut,
  CampaignFlightOut,
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
} from "../api/types";
import { statusLabel } from "../api/types";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import type { StatusBadgeVariant } from "../components/StatusBadge";

const PAGE_SIZE = 50;

/** Map campaign status → StatusBadge variant */
function statusVariant(status: string): StatusBadgeVariant {
  switch (status) {
    case "active":            return "active";
    case "draft":             return "draft";
    case "pending_approval":  return "review";
    case "approved":          return "active";
    case "rejected":          return "rejected";
    case "paused":            return "neutral";
    default:                  return "neutral";
  }
}

export default function CampaignListPage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<CampaignOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [orgs, setOrgs] = useState<Map<string, AdvertiserOrganizationOut>>(new Map());
  const [brands, setBrands] = useState<Map<string, AdvertiserBrandOut>>(new Map());
  const [flights, setFlights] = useState<CampaignFlightOut[]>([]);

  const [statusFilter, setStatusFilter] = useState<string>("all");
  const filteredCampaigns = statusFilter === "all"
    ? campaigns
    : campaigns.filter((c) => c.status === statusFilter);

  const load = useCallback(async (pageOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const [campsPage, flts, orgList, brandList] = await Promise.all([
        listCampaigns(PAGE_SIZE, pageOffset),
        listFlights(),
        listAdvertisers(),
        listBrands(),
      ]);
      setCampaigns(campsPage.items);
      setTotal(campsPage.total);
      setOffset(pageOffset);
      setFlights(flts);
      setOrgs(new Map(orgList.map((o) => [o.id, o])));
      setBrands(new Map(brandList.map((b) => [b.id, b])));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(0); }, [load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  // ── Render states ──

  if (loading) {
    return (
      <div style={centered}>
        <p style={{ color: "var(--rmp-text-secondary)", fontSize: "var(--rmp-font-size-base)" }}>Загрузка кампаний...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={centered}>
        <div style={{ background: "var(--rmp-danger-50)", color: "var(--rmp-danger-800)", padding: "var(--rmp-space-4)", borderRadius: "var(--rmp-radius-md)", maxWidth: 480 }}>
          <p style={{ margin: 0, fontWeight: 600 }}>Ошибка</p>
          <p style={{ margin: "var(--rmp-space-1) 0 0", fontSize: "var(--rmp-font-size-base)" }}>{error}</p>
        </div>
      </div>
    );
  }

  if (filteredCampaigns.length === 0) {
    return (
      <div>
        <PageHeader title="Кампании" />
        <FilterChips current={statusFilter} onChange={setStatusFilter} />
        <div style={{ background: "var(--rmp-gray-50)", border: "1px dashed var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-md)", padding: "var(--rmp-space-8)", textAlign: "center", color: "var(--rmp-text-secondary)" }}>
          <p style={{ margin: 0, fontWeight: 500 }}>
            {statusFilter === "all" ? "Нет кампаний" : "Нет кампаний с этим статусом"}
          </p>
          <p style={{ margin: "var(--rmp-space-1) 0 0", fontSize: "var(--rmp-font-size-base)", color: "var(--rmp-text-muted)" }}>
            {statusFilter === "all" ? "Создайте первую кампанию." : "Измените фильтр или создайте новую кампанию."}
          </p>
        </div>
      </div>
    );
  }

  // ── Helpers ──

  function orgName(c: CampaignOut): string {
    const org = orgs.get(c.advertiser_organization_id);
    return org?.display_name || org?.legal_name || c.advertiser_organization_id;
  }

  function brandName(c: CampaignOut): string | null {
    if (!c.advertiser_brand_id) return null;
    return brands.get(c.advertiser_brand_id)?.name ?? null;
  }

  function flightSummary(c: CampaignOut): string {
    const campaignFlights = flights.filter((f) => f.campaign_id === c.id).sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime());
    if (campaignFlights.length === 0) return "—";
    const first = new Date(campaignFlights[0].start_at);
    const last = new Date(campaignFlights[campaignFlights.length - 1].end_at);
    const fmt = (d: Date) => d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });
    if (campaignFlights.length === 1) return `${fmt(first)} – ${fmt(last)}`;
    return `${campaignFlights.length} пер., ${fmt(first)} – ${fmt(last)}`;
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" });
  }

  return (
    <div>
      <PageHeader title="Кампании" />
      <FilterChips current={statusFilter} onChange={setStatusFilter} />
      <table className="rmp-table">
        <thead>
          <tr>
            <th>Название</th>
            <th>Статус</th>
            <th>Рекламодатель</th>
            <th>Период</th>
            <th>Обновлено</th>
          </tr>
        </thead>
        <tbody>
          {filteredCampaigns.map((c) => (
            <tr
              key={c.id}
              style={{ cursor: "pointer" }}
              onClick={() => navigate(`/campaigns/${c.id}`)}
              onKeyDown={(e) => { if (e.key === "Enter") navigate(`/campaigns/${c.id}`); }}
              tabIndex={0}
              role="link"
              aria-label={`Перейти к кампании ${c.name}`}
            >
              <td>
                <div style={{ fontWeight: 500 }}>{c.name}</div>
                <div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-muted)" }}>
                  {c.code}{brandName(c) ? ` · ${brandName(c)}` : ""}
                </div>
              </td>
              <td>
                <StatusBadge variant={statusVariant(c.status)}>
                  {statusLabel(c.status)}
                </StatusBadge>
              </td>
              <td>{orgName(c)}</td>
              <td>{flightSummary(c)}</td>
              <td style={{ fontSize: "var(--rmp-font-size-sm)", color: "var(--rmp-text-secondary)" }}>
                {formatDate(c.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Pagination
        total={total} offset={offset} limit={PAGE_SIZE}
        hasPrev={hasPrev} hasNext={hasNext}
        onPrev={() => load(offset - PAGE_SIZE)}
        onNext={() => load(offset + PAGE_SIZE)}
      />
    </div>
  );
}

// ── Pagination ──

function Pagination({ total, offset, limit, hasPrev, hasNext, onPrev, onNext }: {
  total: number; offset: number; limit: number; hasPrev: boolean; hasNext: boolean;
  onPrev: () => void; onNext: () => void;
}) {
  if (total <= limit) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "var(--rmp-space-3)", fontSize: "var(--rmp-font-size-sm)" }}>
      <span style={{ color: "var(--rmp-text-secondary)" }}>{from}–{to} из {total}</span>
      <div style={{ display: "flex", gap: "var(--rmp-space-1)" }}>
        <button onClick={onPrev} disabled={!hasPrev} style={pgnBtn(hasPrev)}>← Назад</button>
        <button onClick={onNext} disabled={!hasNext} style={pgnBtn(hasNext)}>Вперёд →</button>
      </div>
    </div>
  );
}

function pgnBtn(enabled: boolean): React.CSSProperties {
  return {
    padding: "0.15rem 0.5rem", fontSize: "var(--rmp-font-size-xs)",
    border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)",
    background: enabled ? "var(--rmp-bg-surface)" : "var(--rmp-gray-100)",
    color: enabled ? "var(--rmp-text-primary)" : "var(--rmp-text-muted)",
    cursor: enabled ? "pointer" : "default",
  };
}

// ── Filter chips ──

const FILTER_OPTIONS = [
  { value: "all", label: "Все" },
  { value: "draft", label: "Черновики" },
  { value: "pending_approval", label: "На согласовании" },
  { value: "active", label: "Активные" },
  { value: "approved", label: "Согласованные" },
];

function FilterChips({ current, onChange }: { current: string; onChange: (v: string) => void }) {
  return (
    <div style={{ display: "flex", gap: "0.35rem", marginBottom: "var(--rmp-space-3)", flexWrap: "wrap" }}>
      {FILTER_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          style={{
            padding: "0.2rem 0.6rem", borderRadius: 999,
            border: current === opt.value ? "1px solid var(--rmp-primary-500)" : "1px solid var(--rmp-border-strong)",
            background: current === opt.value ? "var(--rmp-primary-50)" : "var(--rmp-bg-surface)",
            color: current === opt.value ? "var(--rmp-primary-700)" : "var(--rmp-text-secondary)",
            fontSize: "var(--rmp-font-size-xs)", fontWeight: current === opt.value ? 600 : 400,
            cursor: "pointer", lineHeight: "1.5",
          }}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

// ── Shared ──

const centered: React.CSSProperties = {
  display: "flex", alignItems: "center", justifyContent: "center", minHeight: 200,
};
