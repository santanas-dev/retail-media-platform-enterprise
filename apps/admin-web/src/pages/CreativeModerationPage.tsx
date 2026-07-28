import { useEffect, useState, useCallback } from "react";
import { listModerationQueue, approveCreative, rejectCreative } from "../api/campaigns";
import { ApiError } from "../api/client";
import type { CreativeModerationQueueItem } from "../api/types";
import { moderationStatusLabel, statusLabel } from "../api/types";
import PageHeader from "../components/PageHeader";
import StatusBadge from "../components/StatusBadge";
import type { StatusBadgeVariant } from "../components/StatusBadge";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "short", year: "numeric" });
}

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function fmtResolution(w: number | null, h: number | null): string {
  if (w && h) return `${w}×${h}`;
  if (w) return `${w}px`;
  return "—";
}

function fmtDuration(ms: number | null): string {
  if (!ms) return "—";
  const sec = Math.round(ms / 1000);
  if (sec < 60) return `${sec}с`;
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, "0")}`;
}

function modVariant(s: string): StatusBadgeVariant {
  switch (s) {
    case "approved": return "active";
    case "rejected": return "rejected";
    default: return "review";
  }
}

const PAGE_SIZE = 50;

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

export default function CreativeModerationPage() {
  const [items, setItems] = useState<CreativeModerationQueueItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("pending_review");
  const [actionError, setActionError] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState("");

  const load = useCallback(async (statusFilter: string, pageOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await listModerationQueue(statusFilter, PAGE_SIZE, pageOffset);
      setItems(data.items);
      setTotal(data.total);
      setOffset(pageOffset);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setError("Нет доступа к модерации креативов");
      } else {
        setError("Ошибка загрузки очереди");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(filter, 0); }, [filter, load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  const handleApprove = async (assetId: string) => {
    setActionError(null);
    try {
      await approveCreative(assetId);
      await load(filter, offset);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Ошибка при одобрении");
    }
  };

  const handleReject = async (assetId: string) => {
    if (!rejectReason.trim()) return;
    setActionError(null);
    try {
      await rejectCreative(assetId, { reason: rejectReason.trim() });
      setRejectingId(null); setRejectReason("");
      await load(filter, offset);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Ошибка при отклонении");
    }
  };

  const openReject = (id: string) => { setRejectingId(id); setRejectReason(""); setActionError(null); };

  const FILTERS = [
    { value: "pending_review", label: "На проверке" },
    { value: "approved", label: "Одобрены" },
    { value: "rejected", label: "Отклонены" },
    { value: "all", label: "Все" },
  ];

  return (
    <div data-testid="moderation-page">
      <PageHeader title="Модерация креативов" />
      {actionError && (
        <div data-testid="moderation-action-error" style={{ padding: "var(--rmp-space-2) var(--rmp-space-4)", marginBottom: "var(--rmp-space-2)", background: "var(--rmp-danger-50)", color: "var(--rmp-danger-600)", borderRadius: "var(--rmp-radius-sm)", fontSize: "var(--rmp-font-size-base)" }}>
          {actionError}
        </div>
      )}
      <div style={{ display: "flex", gap: "var(--rmp-space-2)", marginBottom: "var(--rmp-space-4)" }}>
        {FILTERS.map((f) => (
          <button
            key={f.value}
            data-testid={`moderation-filter-${f.value}`}
            onClick={() => setFilter(f.value)}
            style={{
              padding: "var(--rmp-space-1) var(--rmp-space-3)", borderRadius: "var(--rmp-radius-sm)",
              border: "1px solid var(--rmp-border-strong)",
              background: filter === f.value ? "var(--rmp-gray-800)" : "var(--rmp-bg-surface)",
              color: filter === f.value ? "var(--rmp-text-inverse)" : "var(--rmp-text-primary)",
              cursor: "pointer", fontSize: "var(--rmp-font-size-sm)",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>
      {loading && <p data-testid="moderation-loading" style={{ color: "var(--rmp-text-secondary)" }}>Загрузка...</p>}
      {error && !loading && <p data-testid="moderation-error" style={{ color: "var(--rmp-danger-600)" }}>{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p data-testid="moderation-empty" style={{ color: "var(--rmp-text-secondary)" }}>Очередь пуста</p>
      )}
      {!loading && items.length > 0 && (
        <table className="rmp-table">
          <thead>
            <tr>
              <th>Креатив</th>
              <th>Рекламодатель</th>
              <th>Тип</th>
              <th>Размер</th>
              <th>Статус</th>
              <th>Модерация</th>
              <th>Создан</th>
              <th>Действия</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} data-testid={`moderation-row-${item.code}`}>
                <td>
                  <div style={{ fontWeight: 600 }}>{item.name}</div>
                  <div style={{ color: "var(--rmp-text-secondary)", fontSize: "var(--rmp-font-size-xs)" }}>{item.code}</div>
                </td>
                <td>{item.advertiser_name ?? item.advertiser_code ?? "—"}</td>
                <td>{item.media_type}</td>
                <td>
                  {fmtSize(item.file_size_bytes)}
                  {item.resolution_w && <><br />{fmtResolution(item.resolution_w, item.resolution_h)}</>}
                  {item.duration_ms && <><br />{fmtDuration(item.duration_ms)}</>}
                </td>
                <td>{statusLabel(item.status)}</td>
                <td>
                  <span data-testid={`moderation-status-${item.code}`}>
                    <StatusBadge variant={modVariant(item.moderation_status)}>
                      {moderationStatusLabel(item.moderation_status)}
                    </StatusBadge>
                  </span>
                  {item.moderation_notes && item.moderation_status === "rejected" && (
                    <div style={{ color: "var(--rmp-text-secondary)", fontSize: "var(--rmp-font-size-xs)", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.moderation_notes}
                    </div>
                  )}
                </td>
                <td>{fmtDate(item.created_at)}</td>
                <td>
                  {rejectingId === item.id ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <input
                        type="text" placeholder="Причина отказа" data-testid={`moderation-reject-reason-${item.code}`}
                        value={rejectReason} onChange={(e) => setRejectReason(e.target.value)}
                        style={{ padding: "var(--rmp-space-1) var(--rmp-space-2)", fontSize: "var(--rmp-font-size-xs)", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", width: 140 }}
                      />
                      <div style={{ display: "flex", gap: 4 }}>
                        <button data-testid={`moderation-reject-confirm-${item.code}`} onClick={() => handleReject(item.id)} disabled={!rejectReason.trim()} style={actionBtn("var(--rmp-danger-600)", !rejectReason.trim())}>Отклонить</button>
                        <button data-testid={`moderation-reject-cancel-${item.code}`} onClick={() => setRejectingId(null)} style={actionBtn("var(--rmp-text-secondary)")}>Отмена</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: "flex", gap: 4 }}>
                      <button data-testid={`moderation-approve-${item.code}`} onClick={() => handleApprove(item.id)} style={actionBtn("var(--rmp-success-600)")}>Одобрить</button>
                      <button data-testid={`moderation-reject-${item.code}`} onClick={() => openReject(item.id)} style={actionBtn("var(--rmp-danger-600)")}>Отклонить</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {!loading && items.length > 0 && (
        <Pagination total={total} offset={offset} limit={PAGE_SIZE}
          hasPrev={hasPrev} hasNext={hasNext}
          onPrev={() => load(filter, offset - PAGE_SIZE)} onNext={() => load(filter, offset + PAGE_SIZE)} />
      )}
    </div>
  );
}

function actionBtn(color: string, disabled = false): React.CSSProperties {
  return {
    padding: "0.15rem 0.5rem", fontSize: "var(--rmp-font-size-xs)",
    border: `1px solid ${color}`, borderRadius: "var(--rmp-radius-sm)",
    background: disabled ? "var(--rmp-gray-200)" : "var(--rmp-bg-surface)",
    color: disabled ? "var(--rmp-text-muted)" : color,
    cursor: disabled ? "default" : "pointer",
  };
}
