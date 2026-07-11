import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type {
  CampaignOut,
  CampaignFlightOut,
  CampaignPlacementOut,
  CampaignCreativeOut,
  CreativeAssetOut,
  CampaignApprovalOut,
  CampaignStatusHistoryOut,
} from "../api/types";
import { statusLabel, statusColor } from "../api/types";
import { useAuth } from "../auth/AuthContext";

// ── Helpers ──

const APPROVAL_LABELS: Record<string, string> = {
  pending: "На рассмотрении",
  approved: "Согласовано",
  rejected: "Отклонено",
};

function approvalLabel(d: string | null): string {
  return d && APPROVAL_LABELS[d] ? APPROVAL_LABELS[d] : d ?? "—";
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function budgetLabel(amount: number | null, currency: string): string {
  if (amount == null) return "—";
  return `${amount.toLocaleString("ru-RU")} ${currency}`;
}

// ── Component ──

export default function CampaignDetailPage() {
  const { id: campaignId } = useParams<{ id: string }>();
  const { logout } = useAuth();
  const navigate = useNavigate();

  const [campaign, setCampaign] = useState<CampaignOut | null>(null);
  const [flights, setFlights] = useState<CampaignFlightOut[]>([]);
  const [placements, setPlacements] = useState<CampaignPlacementOut[]>([]);
  const [ccLinks, setCcLinks] = useState<CampaignCreativeOut[]>([]);
  const [creativeAssets, setCreativeAssets] = useState<CreativeAssetOut[]>([]);
  const [approvals, setApprovals] = useState<CampaignApprovalOut[]>([]);
  const [statusHistory, setStatusHistory] = useState<CampaignStatusHistoryOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [camps, flts, plcs, ccs, assets, apprs, hist] = await Promise.all([
          api.get<CampaignOut[]>("/campaigns"),
          api.get<CampaignFlightOut[]>("/campaign-flights"),
          api.get<CampaignPlacementOut[]>("/campaign-placements"),
          api.get<CampaignCreativeOut[]>("/campaign-creatives"),
          api.get<CreativeAssetOut[]>("/creative-assets"),
          api.get<CampaignApprovalOut[]>("/campaign-approvals"),
          api.get<CampaignStatusHistoryOut[]>("/campaign-status-history"),
        ]);
        if (cancelled) return;

        const found = camps.find((c) => c.id === campaignId);
        if (!found) {
          setNotFound(true);
          setLoading(false);
          return;
        }
        setCampaign(found);
        setFlights(flts.filter((f) => f.campaign_id === campaignId));
        setPlacements(plcs.filter((p) => p.campaign_id === campaignId));
        setCcLinks(ccs.filter((cc) => cc.campaign_id === campaignId));
        setCreativeAssets(assets);
        setApprovals(apprs.filter((a) => a.campaign_id === campaignId));
        setStatusHistory(hist.filter((h) => h.campaign_id === campaignId));
      } catch (e: unknown) {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) {
          logout();
          return;
        }
        if (e instanceof ApiError && (e.status === 403 || e.status === 404)) {
          setNotFound(true);
          setLoading(false);
          return;
        }
        setError(e instanceof Error ? e.message : "Ошибка загрузки");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [campaignId, logout]);

  // ── Render states ──

  if (loading) {
    return (
      <div style={styles.centered}>
        <p style={styles.muted}>Загрузка кампании...</p>
      </div>
    );
  }

  if (notFound || error) {
    return (
      <div style={styles.centered}>
        <div style={styles.inaccessibleBox}>
          <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>
            Кампания не найдена или недоступна
          </h3>
          <p style={{ margin: 0, fontSize: "0.85rem", color: "#64748b" }}>
            Возможно, у вас нет прав на просмотр этой кампании.
          </p>
          <button
            type="button"
            onClick={() => navigate("/campaigns", { replace: true })}
            style={styles.backBtn}
          >
            ← К списку кампаний
          </button>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return null;
  }

  // ── Derived data ──

  const assetById = new Map(creativeAssets.map((a) => [a.id, a]));

  return (
    <div>
      {/* ── Back ── */}
      <button
        type="button"
        onClick={() => navigate("/campaigns")}
        style={styles.backLink}
      >
        ← К списку кампаний
      </button>

      {/* ── Header ── */}
      <div style={styles.header}>
        <div>
          <h2 style={{ margin: "0 0 0.25rem", fontSize: "1.25rem" }}>
            {campaign.name}
          </h2>
          <span style={{ fontSize: "0.8rem", color: "#64748b" }}>
            {campaign.code}
          </span>
        </div>
        <span
          style={{
            ...styles.badge,
            background: statusColor(campaign.status),
          }}
        >
          {statusLabel(campaign.status)}
        </span>
      </div>

      {/* ── Sections ── */}
      <Section title="Обзор">
        <KvList
          items={[
            ["Код", campaign.code],
            ["Название", campaign.name],
            ["Статус", statusLabel(campaign.status)],
            [
              "Период",
              campaign.start_at
                ? `${formatDate(campaign.start_at)} — ${formatDate(campaign.end_at ?? "")}`
                : "—",
            ],
            ["Бюджет", budgetLabel(campaign.budget_limit_amount, campaign.budget_limit_currency)],
            ["Приоритет", String(campaign.priority)],
            ["Часовой пояс", campaign.timezone],
            ...(campaign.description
              ? [["Описание", campaign.description] as [string, string]]
              : []),
          ]}
        />
      </Section>

      <Section title="Периоды / Флайты">
        {flights.length === 0 ? (
          <EmptyState text="Флайты не заданы" />
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Название</th>
                <th style={styles.th}>Начало</th>
                <th style={styles.th}>Окончание</th>
                <th style={styles.th}>Приоритет</th>
              </tr>
            </thead>
            <tbody>
              {flights.map((f) => (
                <tr key={f.id} style={styles.row}>
                  <td style={styles.td}>{f.name || "—"}</td>
                  <td style={styles.td}>{formatDate(f.start_at)}</td>
                  <td style={styles.td}>{formatDate(f.end_at)}</td>
                  <td style={styles.td}>{f.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Размещения">
        {placements.length === 0 ? (
          <EmptyState text="Размещения не заданы" />
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Поверхность</th>
                <th style={styles.th}>SOV %</th>
                <th style={styles.th}>Показов</th>
                <th style={styles.th}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {placements.map((p) => (
                <tr key={p.id} style={styles.row}>
                  <td style={styles.td}>
                    {p.display_surface_id || p.store_id || p.cluster_id || p.branch_id || "—"}
                  </td>
                  <td style={styles.td}>{p.share_of_voice_pct}%</td>
                  <td style={styles.td}>
                    {p.impressions_delivered}
                    {p.max_impressions ? ` / ${p.max_impressions}` : ""}
                  </td>
                  <td style={styles.td}>{p.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Креативы">
        {ccLinks.length === 0 ? (
          <EmptyState text="Креативы не привязаны" />
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Название</th>
                <th style={styles.th}>Тип</th>
                <th style={styles.th}>Размер</th>
                <th style={styles.th}>Статус</th>
              </tr>
            </thead>
            <tbody>
              {ccLinks.map((cc) => {
                const asset = assetById.get(cc.creative_asset_id);
                return (
                  <tr key={cc.id} style={styles.row}>
                    <td style={styles.td}>
                      {asset?.name ?? cc.creative_asset_id}
                    </td>
                    <td style={styles.td}>{asset?.media_type ?? "—"}</td>
                    <td style={styles.td}>
                      {asset
                        ? `${(asset.file_size_bytes / 1024).toFixed(0)} KB`
                        : "—"}
                    </td>
                    <td style={styles.td}>
                      {asset ? (
                        <span
                          style={{
                            ...styles.smallBadge,
                            background:
                              asset.status === "ready"
                                ? "#059669"
                                : asset.status === "metadata_only"
                                  ? "#d97706"
                                  : "#64748b",
                          }}
                        >
                          {statusLabel(asset.status)}
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </Section>

      <Section title="Согласование">
        {approvals.length === 0 && statusHistory.length === 0 ? (
          <EmptyState text="Нет истории согласования" />
        ) : (
          <div>
            {approvals.length > 0 && (
              <div style={{ marginBottom: "1rem" }}>
                <h4 style={styles.subheading}>Заявки на согласование</h4>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Запрошено</th>
                      <th style={styles.th}>Рассмотрено</th>
                      <th style={styles.th}>Решение</th>
                      <th style={styles.th}>Комментарий</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvals.map((a) => (
                      <tr key={a.id} style={styles.row}>
                        <td style={styles.td}>
                          {formatDateTime(a.requested_at)}
                        </td>
                        <td style={styles.td}>
                          {a.reviewed_at ? formatDateTime(a.reviewed_at) : "—"}
                        </td>
                        <td style={styles.td}>
                          <span
                            style={{
                              ...styles.smallBadge,
                              background:
                                a.decision === "approved"
                                  ? "#059669"
                                  : a.decision === "rejected"
                                    ? "#dc2626"
                                    : "#64748b",
                            }}
                          >
                            {approvalLabel(a.decision)}
                          </span>
                        </td>
                        <td style={styles.td}>
                          {a.rejection_reason || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            {statusHistory.length > 0 && (
              <div>
                <h4 style={styles.subheading}>История статусов</h4>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>Дата</th>
                      <th style={styles.th}>Старый статус</th>
                      <th style={styles.th}>Новый статус</th>
                      <th style={styles.th}>Причина</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statusHistory.map((h) => (
                      <tr key={h.id} style={styles.row}>
                        <td style={styles.td}>
                          {formatDateTime(h.changed_at)}
                        </td>
                        <td style={styles.td}>
                          {h.old_status ? statusLabel(h.old_status) : "—"}
                        </td>
                        <td style={styles.td}>
                          {statusLabel(h.new_status)}
                        </td>
                        <td style={styles.td}>{h.reason || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </Section>
    </div>
  );
}

// ── Sub-components ──

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>{title}</h3>
      {children}
    </div>
  );
}

function KvList({ items }: { items: [string, string][] }) {
  return (
    <div style={styles.kvGrid}>
      {items.map(([k, v]) => (
        <div key={k} style={styles.kvRow}>
          <span style={styles.kvKey}>{k}</span>
          <span style={styles.kvValue}>{v}</span>
        </div>
      ))}
    </div>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div style={styles.emptyBox}>
      <p style={{ margin: 0, color: "#94a3b8", fontSize: "0.875rem" }}>
        {text}
      </p>
    </div>
  );
}

// ── Styles ──

const styles: Record<string, React.CSSProperties> = {
  centered: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 200,
  },
  muted: { color: "#64748b", fontSize: "0.875rem" },
  inaccessibleBox: {
    background: "#f8fafc",
    border: "1px dashed #cbd5e1",
    borderRadius: 6,
    padding: "2rem",
    maxWidth: 480,
    textAlign: "center" as const,
  },
  backBtn: {
    marginTop: "1rem",
    padding: "0.4rem 0.8rem",
    background: "#f1f5f9",
    border: "1px solid #e2e8f0",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: "0.85rem",
    color: "#475569",
  },
  backLink: {
    background: "none",
    border: "none",
    color: "#2563eb",
    cursor: "pointer",
    fontSize: "0.85rem",
    padding: 0,
    marginBottom: "0.75rem",
    textDecoration: "underline",
    textUnderlineOffset: 2,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "1.5rem",
  },
  badge: {
    display: "inline-block",
    padding: "0.2rem 0.6rem",
    borderRadius: 999,
    fontSize: "0.8rem",
    fontWeight: 500,
    color: "#fff",
    lineHeight: "1.4",
  },
  section: {
    marginBottom: "1.5rem",
  },
  sectionTitle: {
    margin: "0 0 0.75rem",
    fontSize: "1rem",
    fontWeight: 600,
    color: "#1e293b",
  },
  subheading: {
    margin: "0 0 0.5rem",
    fontSize: "0.85rem",
    fontWeight: 600,
    color: "#475569",
  },
  kvGrid: {
    display: "grid",
    gridTemplateColumns: "180px 1fr",
    gap: "0.4rem 0",
    fontSize: "0.875rem",
  },
  kvRow: {
    display: "contents" as "contents",
  },
  kvKey: {
    color: "#64748b",
    fontWeight: 500,
    padding: "0.25rem 0",
  },
  kvValue: {
    padding: "0.25rem 0",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse" as const,
    fontSize: "0.85rem",
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
    padding: "0.5rem 0.75rem",
    borderBottom: "1px solid #f1f5f9",
    verticalAlign: "middle" as const,
  },
  row: { transition: "background 0.1s" },
  smallBadge: {
    display: "inline-block",
    padding: "0.1rem 0.4rem",
    borderRadius: 999,
    fontSize: "0.7rem",
    fontWeight: 500,
    color: "#fff",
    lineHeight: "1.4",
  },
  emptyBox: {
    background: "#f8fafc",
    border: "1px dashed #cbd5e1",
    borderRadius: 6,
    padding: "1.5rem",
    textAlign: "center" as const,
  },
};
