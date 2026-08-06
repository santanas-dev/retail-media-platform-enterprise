import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { listApprovalQueue, approveCampaign, rejectCampaign } from "../api/campaigns";
import { ApiError } from "../api/client";
import type { CampaignApprovalQueueItem } from "../api/types";
import { statusLabel } from "../api/types";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric", month: "short", year: "numeric",
  });
}

const READY = "✅";
const NOT_READY = "❌";
const PAGE_SIZE = 50;

function Pagination({
  total, offset, limit, hasPrev, hasNext, onPrev, onNext,
}: {
  total: number; offset: number; limit: number;
  hasPrev: boolean; hasNext: boolean;
  onPrev: () => void; onNext: () => void;
}) {
  if (total <= limit) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "0.75rem", fontSize: "0.8125rem" }}>
      <span style={{ color: "var(--rmp-text-secondary)" }}>{from}–{to} из {total}</span>
      <div style={{ display: "flex", gap: "0.25rem" }}>
        <button onClick={onPrev} disabled={!hasPrev} style={pgnBtn(hasPrev)}>← Назад</button>
        <button onClick={onNext} disabled={!hasNext} style={pgnBtn(hasNext)}>Вперёд →</button>
      </div>
    </div>
  );
}

function pgnBtn(enabled: boolean): React.CSSProperties {
  return {
    padding: "0.2rem 0.6rem", fontSize: "0.75rem", border: "1px solid var(--rmp-border-strong)",
    borderRadius: 4, background: enabled ? "var(--rmp-bg-surface)" : "var(--rmp-gray-100)",
    color: enabled ? "var(--rmp-gray-700)" : "var(--rmp-text-muted)", cursor: enabled ? "pointer" : "default",
  };
}

export default function ApprovalInboxPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<CampaignApprovalQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("pending_approval");
  const [actionError, setActionError] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const load = useCallback(async (statusFilter: string, pageOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await listApprovalQueue(statusFilter, PAGE_SIZE, pageOffset);
      setItems(data.items);
      setTotal(data.total);
      setOffset(pageOffset);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setError("Нет доступа к согласованию кампаний");
      } else {
        setError("Ошибка загрузки");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(filter, 0); }, [filter, load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  const handleApprove = async (campaignId: string) => {
    setActionError(null);
    try {
      await approveCampaign(campaignId);
      await load(filter, offset);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Ошибка при согласовании");
    }
  };

  const handleReject = async (campaignId: string) => {
    if (!rejectReason.trim()) return;
    setActionError(null);
    try {
      await rejectCampaign(campaignId, { reason: rejectReason.trim() });
      setRejectingId(null);
      setRejectReason("");
      await load(filter, offset);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Ошибка при отклонении");
    }
  };

  const FILTERS = [
    { value: "pending_approval", label: "На согласовании" },
    { value: "approved", label: "Согласованные" },
    { value: "rejected", label: "Отклонённые" },
    { value: "all", label: "Все" },
  ];

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
        Согласование кампаний
      </h1>
      {actionError && (
        <div style={{ padding: "0.5rem 1rem", marginBottom: "0.5rem", background: "var(--rmp-danger-50)", color: "var(--rmp-danger-600)", borderRadius: 4, fontSize: "0.875rem" }}>
          {actionError}
        </div>
      )}
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            style={{
              padding: "0.25rem 0.75rem",
              borderRadius: 4,
              border: "1px solid var(--rmp-border-strong)",
              background: filter === f.value ? "var(--rmp-gray-800)" : "var(--rmp-bg-surface)",
              color: filter === f.value ? "var(--rmp-text-inverse)" : "var(--rmp-gray-700)",
              cursor: "pointer",
              fontSize: "0.8125rem",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>
      {loading && <p style={{ color: "var(--rmp-text-secondary)" }}>Загрузка...</p>}
      {error && !loading && <p style={{ color: "var(--rmp-danger-600)" }}>{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p style={{ color: "var(--rmp-text-secondary)" }}>Нет кампаний на согласовании</p>
      )}
      {!loading && items.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ background: "var(--rmp-gray-100)", textAlign: "left" }}>
              <th style={thStyle}>Кампания</th>
              <th style={thStyle}>Рекламодатель</th>
              <th style={thStyle}>Готовность</th>
              <th style={thStyle}>Статус</th>
              <th style={thStyle}>Подана</th>
              <th style={thStyle}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const canApprove = item.has_flight && item.has_placement && item.has_creative && item.all_creatives_ready && item.all_creatives_approved;
              return (
                <tr key={item.campaign_id} style={{ borderBottom: "1px solid var(--rmp-border)" }}>
                  <td style={tdStyle}>
                    <div style={{ fontWeight: 600, cursor: "pointer", color: "var(--rmp-primary-500)" }}
                         onClick={() => navigate(`/campaigns/${item.campaign_id}`)}>
                      {item.campaign_name}
                    </div>
                    <div style={{ color: "var(--rmp-text-secondary)", fontSize: "0.75rem" }}>{item.campaign_code}</div>
                  </td>
                  <td style={tdStyle}>
                    {item.advertiser_org_name ?? item.advertiser_org_id ?? "—"}
                    {item.advertiser_brand_name && <><br /><span style={{ color: "var(--rmp-text-secondary)", fontSize: "0.75rem" }}>{item.advertiser_brand_name}</span></>}
                  </td>
                  <td style={tdStyle}>
                    <div style={{ fontSize: "0.75rem", lineHeight: 1.6 }}>
                      <div>{item.has_flight ? READY : NOT_READY} Пролёты</div>
                      <div>{item.has_placement ? READY : NOT_READY} Размещения</div>
                      <div>{item.has_creative ? READY : NOT_READY} Креативы</div>
                      <div>{item.all_creatives_ready ? READY : NOT_READY} Файлы загружены</div>
                      <div>{item.all_creatives_approved ? READY : NOT_READY} Модерация пройдена</div>
                    </div>
                  </td>
                  <td style={tdStyle}>
                    <span style={{
                      color: item.campaign_status === "pending_approval" ? "var(--rmp-warning-600)"
                           : item.campaign_status === "approved" ? "var(--rmp-success-500)"
                           : "var(--rmp-danger-600)",
                      fontWeight: 500,
                    }}>
                      {statusLabel(item.campaign_status)}
                    </span>
                    {item.rejection_reason && (
                      <div style={{ color: "var(--rmp-danger-600)", fontSize: "0.75rem", maxWidth: 200, marginTop: 2 }}>
                        {item.rejection_reason}
                      </div>
                    )}
                  </td>
                  <td style={tdStyle}>{fmtDate(item.requested_at)}</td>
                  <td style={tdStyle}>
                    {item.campaign_status === "pending_approval" && (
                      rejectingId === item.campaign_id ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                          <input type="text" placeholder="Причина отказа" value={rejectReason}
                            onChange={(e) => setRejectReason(e.target.value)}
                            style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem", border: "1px solid var(--rmp-border-strong)", borderRadius: 4, width: 140 }} />
                          <div style={{ display: "flex", gap: 4 }}>
                            <button onClick={() => handleReject(item.campaign_id)} disabled={!rejectReason.trim()}
                              style={actionBtn("var(--rmp-danger-600)", !rejectReason.trim())}>Отклонить</button>
                            <button onClick={() => setRejectingId(null)}
                              style={actionBtn("var(--rmp-text-secondary)")}>Отмена</button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: "flex", gap: 4 }}>
                          <button onClick={() => handleApprove(item.campaign_id)}
                            disabled={!canApprove}
                            style={actionBtn("var(--rmp-success-500)", !canApprove)}
                            title={!canApprove ? "Кампания не готова к согласованию" : ""}>
                            Согласовать
                          </button>
                          <button onClick={() => { setRejectingId(item.campaign_id); setRejectReason(""); }}
                            style={actionBtn("var(--rmp-danger-600)")}>Отклонить</button>
                        </div>
                      )
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
      {!loading && items.length > 0 && (
        <Pagination
          total={total} offset={offset} limit={PAGE_SIZE}
          hasPrev={hasPrev} hasNext={hasNext}
          onPrev={() => load(filter, offset - PAGE_SIZE)}
          onNext={() => load(filter, offset + PAGE_SIZE)}
        />
      )}
    </div>
  );
}

const thStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem", fontWeight: 600, color: "var(--rmp-gray-600)", fontSize: "0.75rem",
};
const tdStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem", verticalAlign: "top",
};
function actionBtn(color: string, disabled = false): React.CSSProperties {
  return {
    padding: "0.15rem 0.5rem", fontSize: "0.75rem", border: `1px solid ${color}`,
    borderRadius: 4, background: disabled ? "var(--rmp-border)" : "var(--rmp-bg-surface)",
    color: disabled ? "var(--rmp-text-muted)" : color, cursor: disabled ? "default" : "pointer",
  };
}
