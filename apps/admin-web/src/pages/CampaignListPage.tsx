import { useEffect, useState } from "react";
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
import { statusLabel, statusColor } from "../api/types";

export default function CampaignListPage() {
  const navigate = useNavigate();
  const [campaigns, setCampaigns] = useState<CampaignOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Lookup maps for advertiser names
  const [orgs, setOrgs] = useState<Map<string, AdvertiserOrganizationOut>>(new Map());
  const [brands, setBrands] = useState<Map<string, AdvertiserBrandOut>>(new Map());
  const [flights, setFlights] = useState<CampaignFlightOut[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [camps, flts, orgList, brandList] = await Promise.all([
          listCampaigns(),
          listFlights(),
          listAdvertisers(),
          listBrands(),
        ]);

        if (cancelled) return;

        setCampaigns(camps);
        setFlights(flts);
        setOrgs(new Map(orgList.map((o) => [o.id, o])));
        setBrands(new Map(brandList.map((b) => [b.id, b])));
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
  }, []);

  // ── Render states ──

  if (loading) {
    return (
      <div style={styles.centered}>
        <p style={styles.muted}>Загрузка кампаний...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.centered}>
        <div style={styles.errorBox}>
          <p style={{ margin: 0, fontWeight: 600 }}>Ошибка</p>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem" }}>{error}</p>
        </div>
      </div>
    );
  }

  if (campaigns.length === 0) {
    return (
      <div>
        <h2 style={styles.heading}>Кампании</h2>
        <div style={styles.emptyBox}>
          <p style={{ margin: 0, fontWeight: 500 }}>Нет кампаний</p>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "#94a3b8" }}>
            Создайте первую кампанию, чтобы она появилась здесь.
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
    const b = brands.get(c.advertiser_brand_id);
    return b?.name ?? null;
  }

  function flightSummary(c: CampaignOut): string {
    const campaignFlights = flights
      .filter((f) => f.campaign_id === c.id)
      .sort((a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime());

    if (campaignFlights.length === 0) return "—";

    const first = new Date(campaignFlights[0].start_at);
    const last = new Date(campaignFlights[campaignFlights.length - 1].end_at);

    const fmt = (d: Date) =>
      d.toLocaleDateString("ru-RU", { day: "numeric", month: "short" });

    if (campaignFlights.length === 1) {
      return `${fmt(first)} – ${fmt(last)}`;
    }
    return `${campaignFlights.length} пер., ${fmt(first)} – ${fmt(last)}`;
  }

  function formatDate(iso: string): string {
    return new Date(iso).toLocaleDateString("ru-RU", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  }

  // ── Render ──

  return (
    <div>
      <h2 style={styles.heading}>Кампании</h2>
      <table style={styles.table}>
        <thead>
          <tr>
            <th style={styles.th}>Название</th>
            <th style={styles.th}>Статус</th>
            <th style={styles.th}>Рекламодатель</th>
            <th style={styles.th}>Период</th>
            <th style={styles.th}>Обновлено</th>
          </tr>
        </thead>
        <tbody>
          {campaigns.map((c) => (
            <tr
              key={c.id}
              style={{ ...styles.row, cursor: "pointer" }}
              onClick={() => navigate(`/campaigns/${c.id}`)}
              onKeyDown={(e) => {
                if (e.key === "Enter") navigate(`/campaigns/${c.id}`);
              }}
              tabIndex={0}
              role="link"
              aria-label={`Перейти к кампании ${c.name}`}
            >
              <td style={styles.td}>
                <div style={{ fontWeight: 500 }}>{c.name}</div>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                  {c.code}
                  {brandName(c) ? ` · ${brandName(c)}` : ""}
                </div>
              </td>
              <td style={styles.td}>
                <span
                  style={{
                    ...styles.badge,
                    background: statusColor(c.status),
                  }}
                >
                  {statusLabel(c.status)}
                </span>
              </td>
              <td style={styles.td}>{orgName(c)}</td>
              <td style={styles.td}>{flightSummary(c)}</td>
              <td style={{ ...styles.td, fontSize: "0.8rem", color: "#64748b" }}>
                {formatDate(c.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ marginTop: "0.75rem", fontSize: "0.75rem", color: "#94a3b8" }}>
        Всего: {campaigns.length}
      </div>
    </div>
  );
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  heading: {
    margin: "0 0 1rem",
    fontSize: "1.25rem",
    fontWeight: 600,
  },
  centered: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 200,
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
  emptyBox: {
    background: "#f8fafc",
    border: "1px dashed #cbd5e1",
    borderRadius: 6,
    padding: "2rem",
    textAlign: "center" as const,
    color: "#64748b",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.875rem",
    background: "#fff",
    borderRadius: 6,
    overflow: "hidden",
    boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
  },
  th: {
    textAlign: "left" as const,
    padding: "0.5rem 0.75rem",
    fontWeight: 600,
    color: "#475569",
    borderBottom: "1px solid #e2e8f0",
    fontSize: "0.75rem",
    textTransform: "uppercase" as const,
    letterSpacing: "0.05em",
  },
  td: {
    padding: "0.6rem 0.75rem",
    borderBottom: "1px solid #f1f5f9",
    verticalAlign: "middle" as const,
  },
  row: {
    transition: "background 0.1s",
  },
  badge: {
    display: "inline-block",
    padding: "0.15rem 0.5rem",
    borderRadius: 999,
    fontSize: "0.75rem",
    fontWeight: 500,
    color: "#fff",
    lineHeight: "1.4",
  },
};
