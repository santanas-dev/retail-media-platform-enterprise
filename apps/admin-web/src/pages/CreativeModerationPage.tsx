import { useEffect, useState, useCallback } from "react";
import { listModerationQueue, approveCreative, rejectCreative } from "../api/campaigns";
import { ApiError } from "../api/client";
import type { CreativeModerationQueueItem } from "../api/types";
import { moderationStatusLabel, statusLabel } from "../api/types";

function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString("ru-RU", {
    day: "numeric", month: "short", year: "numeric",
  });
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
      <span style={{ color: "#64748b" }}>{from}–{to} из {total}</span>
      <div style={{ display: "flex", gap: "0.25rem" }}>
        <button onClick={onPrev} disabled={!hasPrev} style={pgnBtn(hasPrev)}>← Назад</button>
        <button onClick={onNext} disabled={!hasNext} style={pgnBtn(hasNext)}>Вперёд →</button>
      </div>
    </div>
  );
}

function pgnBtn(enabled: boolean): React.CSSProperties {
  return {
    padding: "0.2rem 0.6rem", fontSize: "0.75rem", border: "1px solid #cbd5e1",
    borderRadius: 4, background: enabled ? "#fff" : "#f1f5f9",
    color: enabled ? "#334155" : "#94a3b8", cursor: enabled ? "pointer" : "default",
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
      setRejectingId(null);
      setRejectReason("");
      await load(filter, offset);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : "Ошибка при отклонении");
    }
  };

  const openReject = (id: string) => {
    setRejectingId(id);
    setRejectReason("");
    setActionError(null);
  };

  const FILTERS = [
    { value: "pending_review", label: "На проверке" },
    { value: "approved", label: "Одобрены" },
    { value: "rejected", label: "Отклонены" },
    { value: "all", label: "Все" },
  ];

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
        Модерация креативов
      </h1>
      {actionError && (
        <div style={{ padding: "0.5rem 1rem", marginBottom: "0.5rem", background: "#fef2f2", color: "#dc2626", borderRadius: 4, fontSize: "0.875rem" }}>
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
              border: "1px solid #cbd5e1",
              background: filter === f.value ? "#1e293b" : "#fff",
              color: filter === f.value ? "#fff" : "#334155",
              cursor: "pointer",
              fontSize: "0.8125rem",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>
      {loading && <p style={{ color: "#64748b" }}>Загрузка...</p>}
      {error && !loading && <p style={{ color: "#dc2626" }}>{error}</p>}
      {!loading && !error && items.length === 0 && (
        <p style={{ color: "#64748b" }}>Очередь пуста</p>
      )}
      {!loading && items.length > 0 && (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
          <thead>
            <tr style={{ background: "#f1f5f9", textAlign: "left" }}>
              <th style={thStyle}>Креатив</th>
              <th style={thStyle}>Рекламодатель</th>
              <th style={thStyle}>Тип</th>
              <th style={thStyle}>Размер</th>
              <th style={thStyle}>Статус</th>
              <th style={thStyle}>Модерация</th>
              <th style={thStyle}>Создан</th>
              <th style={thStyle}>Действия</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                <td style={tdStyle}>
                  <div style={{ fontWeight: 600 }}>{item.name}</div>
                  <div style={{ color: "#64748b", fontSize: "0.75rem" }}>{item.code}</div>
                </td>
                <td style={tdStyle}>{item.advertiser_name ?? item.advertiser_code ?? "—"}</td>
                <td style={tdStyle}>{item.media_type}</td>
                <td style={tdStyle}>
                  {fmtSize(item.file_size_bytes)}
                  {item.resolution_w && <><br />{fmtResolution(item.resolution_w, item.resolution_h)}</>}
                  {item.duration_ms && <><br />{fmtDuration(item.duration_ms)}</>}
                </td>
                <td style={tdStyle}>{statusLabel(item.status)}</td>
                <td style={tdStyle}>
                  <span style={{
                    color: item.moderation_status === "approved" ? "#059669"
                      : item.moderation_status === "rejected" ? "#dc2626"
                      : "#d97706",
                    fontWeight: 500,
                  }}>
                    {moderationStatusLabel(item.moderation_status)}
                  </span>
                  {item.moderation_notes && item.moderation_status === "rejected" && (
                    <div style={{ color: "#64748b", fontSize: "0.75rem", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {item.moderation_notes}
                    </div>
                  )}
                </td>
                <td style={tdStyle}>{fmtDate(item.created_at)}</td>
                <td style={tdStyle}>
                  {rejectingId === item.id ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                      <input
                        type="text"
                        placeholder="Причина отказа"
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem", border: "1px solid #cbd5e1", borderRadius: 4, width: 140 }}
                      />
                      <div style={{ display: "flex", gap: 4 }}>
                        <button onClick={() => handleReject(item.id)} disabled={!rejectReason.trim()} style={actionBtnStyle("#dc2626", !rejectReason.trim())}>Отклонить</button>
                        <button onClick={() => setRejectingId(null)} style={actionBtnStyle("#64748b")}>Отмена</button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: "flex", gap: 4 }}>
                      <button onClick={() => handleApprove(item.id)} style={actionBtnStyle("#059669")}>Одобрить</button>
                      <button onClick={() => openReject(item.id)} style={actionBtnStyle("#dc2626")}>Отклонить</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
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
  padding: "0.5rem 0.75rem",
  fontWeight: 600,
  color: "#475569",
  fontSize: "0.75rem",
};

const tdStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  verticalAlign: "top",
};

function actionBtnStyle(color: string, disabled = false): React.CSSProperties {
  return {
    padding: "0.15rem 0.5rem",
    fontSize: "0.75rem",
    border: `1px solid ${color}`,
    borderRadius: 4,
    background: disabled ? "#e2e8f0" : "#fff",
    color: disabled ? "#94a3b8" : color,
    cursor: disabled ? "default" : "pointer",
  };
}
