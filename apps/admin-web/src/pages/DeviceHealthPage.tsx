import { useState, useEffect, useCallback } from "react";
import { api, type PaginatedDevices, type DeviceOut, type DeviceSummaryOut } from "../api/client";

const PAGE_SIZE = 50;

const STATUS_LABELS: Record<string, string> = {
  active: "Активен",
  inactive: "Неактивен",
  error: "Ошибка",
  unregistered: "Не зарегистрирован",
};

const STATUS_COLORS: Record<string, React.CSSProperties> = {
  active: { background: "#f0fdf4", color: "#166534" },
  inactive: { background: "#f1f5f9", color: "#475569" },
  error: { background: "#fef2f2", color: "#991b1b" },
  unregistered: { background: "#fefce8", color: "#854d0e" },
};

const styles = {
  page: { fontFamily: "system-ui, sans-serif" },
  h1: { fontSize: "1.5rem", fontWeight: 600, margin: "0 0 1rem" },
  summaryRow: { display: "flex", gap: "1rem", marginBottom: "1.5rem", flexWrap: "wrap" as const },
  summaryCard: { flex: "1 1 140px", padding: "1rem", borderRadius: 8, background: "#fff", border: "1px solid #e2e8f0", textAlign: "center" as const },
  summaryLabel: { fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" as const, marginBottom: "0.25rem" },
  summaryValue: { fontSize: "1.5rem", fontWeight: 700, color: "#0f172a" },
  table: { width: "100%", borderCollapse: "collapse" as const, fontSize: "0.85rem", background: "#fff" },
  th: { textAlign: "left" as const, padding: "0.5rem", borderBottom: "2px solid #e2e8f0", color: "#64748b", fontWeight: 600, whiteSpace: "nowrap" as const },
  td: { padding: "0.5rem", borderBottom: "1px solid #e2e8f0", verticalAlign: "top" as const },
  mono: { fontFamily: "monospace", fontSize: "0.8rem", color: "#334155" },
  statusPill: (status: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "0.15rem 0.5rem",
    borderRadius: 9999,
    fontSize: "0.75rem",
    fontWeight: 600,
    ...(STATUS_COLORS[status] || STATUS_COLORS.unregistered),
  }),
  pagination: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem", fontSize: "0.85rem" },
  btn: { padding: "0.3rem 0.7rem", border: "1px solid #cbd5e1", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: "0.85rem" },
  loading: { padding: "2rem", textAlign: "center" as const, color: "#94a3b8" },
  error: { padding: "1rem", color: "#991b1b", background: "#fef2f2", borderRadius: 6 },
  empty: { padding: "2rem", textAlign: "center" as const, color: "#94a3b8" },
};

function formatTime(iso: string | null): string {
  if (!iso) return "нет данных";
  try {
    return new Date(iso).toLocaleString("ru-RU", { timeZone: "Europe/Moscow" });
  } catch {
    return iso;
  }
}

function formatCache(bytes: number): string {
  if (bytes === 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DeviceHealthPage() {
  const [devices, setDevices] = useState<PaginatedDevices | null>(null);
  const [summary, setSummary] = useState<DeviceSummaryOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const fetchPage = useCallback(async (newOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const [devResult, sumResult] = await Promise.all([
        api.get<PaginatedDevices>(`/devices?limit=${PAGE_SIZE}&offset=${newOffset}`),
        api.get<DeviceSummaryOut>("/devices/summary"),
      ]);
      setDevices(devResult);
      setSummary(sumResult);
      setOffset(newOffset);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPage(0); }, [fetchPage]);

  const totalPages = devices ? Math.ceil(devices.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div style={styles.page}>
      <h1 style={styles.h1}>Устройства</h1>

      {summary && (
        <div style={styles.summaryRow}>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>Всего</div>
            <div style={styles.summaryValue}>{summary.total}</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>Активны</div>
            <div style={{ ...styles.summaryValue, color: "#166534" }}>{summary.active}</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>Неактивны</div>
            <div style={{ ...styles.summaryValue, color: "#475569" }}>{summary.inactive}</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>С ошибками</div>
            <div style={{ ...styles.summaryValue, color: "#991b1b" }}>{summary.error}</div>
          </div>
          <div style={styles.summaryCard}>
            <div style={styles.summaryLabel}>Не зарегистр.</div>
            <div style={{ ...styles.summaryValue, color: "#854d0e" }}>{summary.unregistered}</div>
          </div>
        </div>
      )}

      {loading && <div style={styles.loading}>Загрузка...</div>}
      {error && <div style={styles.error}>{error}</div>}

      {!loading && !error && devices && devices.items.length === 0 && (
        <div style={styles.empty}>Нет устройств</div>
      )}

      {!loading && !error && devices && devices.items.length > 0 && (
        <>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Код</th>
                <th style={styles.th}>Статус</th>
                <th style={styles.th}>Последняя активность</th>
                <th style={styles.th}>Манифест</th>
                <th style={styles.th}>ОС</th>
                <th style={styles.th}>IP</th>
                <th style={styles.th}>Кеш</th>
              </tr>
            </thead>
            <tbody>
              {devices.items.map((d: DeviceOut) => (
                <tr key={d.id}>
                  <td style={{ ...styles.td, ...styles.mono }} title={d.id}>{d.code}</td>
                  <td style={styles.td}>
                    <span style={styles.statusPill(d.status)}>
                      {STATUS_LABELS[d.status] || d.status}
                    </span>
                  </td>
                  <td style={styles.td}>{formatTime(d.last_seen_at)}</td>
                  <td style={{ ...styles.td, ...styles.mono }}>
                    {d.current_manifest_id ? d.current_manifest_id.slice(0, 12) + "…" : "—"}
                  </td>
                  <td style={styles.td}>{d.os_version || "нет данных"}</td>
                  <td style={{ ...styles.td, ...styles.mono }}>{d.ip_address || "—"}</td>
                  <td style={styles.td}>{formatCache(d.cache_size_bytes)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={styles.pagination}>
            <span>
              Всего: {devices.total} · Стр. {currentPage} из {totalPages || 1}
            </span>
            <div style={{ display: "flex", gap: "0.5rem" }}>
              <button
                style={styles.btn}
                disabled={offset === 0}
                onClick={() => fetchPage(Math.max(0, offset - PAGE_SIZE))}
              >
                ← Назад
              </button>
              <button
                style={styles.btn}
                disabled={offset + PAGE_SIZE >= devices.total}
                onClick={() => fetchPage(offset + PAGE_SIZE)}
              >
                Вперёд →
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
