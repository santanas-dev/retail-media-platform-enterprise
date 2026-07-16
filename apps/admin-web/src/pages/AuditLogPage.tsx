import { useState, useEffect, useCallback } from "react";
import { api, type PaginatedAuditEvents, type AuditEventOut } from "../api/client";

const PAGE_SIZE = 50;

/** Redact known secret keys from details_json before rendering. */
function safeDetails(details: unknown): unknown {
  if (!details || typeof details !== "object") return details;
  const SECRET_KEYS = new Set([
    "password", "password_hash", "password_hash_algorithm",
    "token", "refresh_token", "access_token", "bind_password",
    "secret", "api_key", "private_key",
  ]);
  const record = details as Record<string, unknown>;
  const clean: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(record)) {
    clean[k] = SECRET_KEYS.has(k) ? "[REDACTED]" : v;
  }
  return clean;
}

const styles = {
  page: { fontFamily: "system-ui, sans-serif" },
  header: { display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" },
  h1: { fontSize: "1.5rem", fontWeight: 600, margin: 0 },
  table: { width: "100%", borderCollapse: "collapse" as const, fontSize: "0.85rem", background: "#fff" },
  th: { textAlign: "left" as const, padding: "0.5rem", borderBottom: "2px solid #e2e8f0", color: "#64748b", fontWeight: 600, whiteSpace: "nowrap" as const },
  td: { padding: "0.5rem", borderBottom: "1px solid #e2e8f0", verticalAlign: "top" as const },
  mono: { fontFamily: "monospace", fontSize: "0.8rem", color: "#334155" },
  actionPill: (action: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "0.1rem 0.4rem",
    borderRadius: 4,
    fontSize: "0.75rem",
    fontWeight: 600,
    background: action.includes("failure") || action.includes("blocked") ? "#fef2f2"
               : action.includes("success") || action.includes("login") ? "#f0fdf4"
               : "#f1f5f9",
    color: action.includes("failure") || action.includes("blocked") ? "#991b1b"
          : action.includes("success") || action.includes("login") ? "#166534"
          : "#334155",
  }),
  pagination: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem", fontSize: "0.85rem" },
  btn: { padding: "0.3rem 0.7rem", border: "1px solid #cbd5e1", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: "0.85rem" },
  loading: { padding: "2rem", textAlign: "center" as const, color: "#94a3b8" },
  error: { padding: "1rem", color: "#991b1b", background: "#fef2f2", borderRadius: 6 },
  empty: { padding: "2rem", textAlign: "center" as const, color: "#94a3b8" },
  details: { fontSize: "0.78rem", color: "#475569", wordBreak: "break-all" as const },
};

export default function AuditLogPage() {
  const [data, setData] = useState<PaginatedAuditEvents | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const fetchPage = useCallback(async (newOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await api.get<PaginatedAuditEvents>(`/audit-events?limit=${PAGE_SIZE}&offset=${newOffset}`);
      setData(result);
      setOffset(newOffset);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchPage(0); }, [fetchPage]);

  function renderDetails(details: unknown): string {
    if (details === null || details === undefined) return "—";
    const safe = safeDetails(details);
    try {
      return JSON.stringify(safe, null, 2);
    } catch {
      return String(details);
    }
  }

  function formatTime(iso: string | null): string {
    if (!iso) return "—";
    try {
      return new Date(iso).toLocaleString("ru-RU", { timeZone: "Europe/Moscow" });
    } catch {
      return iso;
    }
  }

  function actionLabel(action: string): string {
    const map: Record<string, string> = {
      "auth.login.success": "Вход",
      "auth.login.failure": "Ошибка входа",
      "auth.login.blocked": "Вход заблокирован",
      "auth.logout": "Выход",
      "auth.break_glass": "Break-glass",
      "auth.password_change": "Смена пароля",
      "user.create": "Создание пользователя",
      "user.update": "Обновление пользователя",
      "user.delete": "Удаление пользователя",
      "user.role_change": "Изменение ролей",
      "user.scope_change": "Изменение scope",
      "campaign.create": "Создание кампании",
      "campaign.update": "Обновление кампании",
      "campaign.submit": "Отправка на согласование",
      "campaign.approve": "Согласование",
      "campaign.reject": "Отклонение",
      "campaign.publish": "Публикация",
      "creative.moderate": "Модерация креатива",
    };
    return map[action] || action;
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.h1}>Журнал аудита</h1>
      </div>

      {loading && <div style={styles.loading}>Загрузка...</div>}
      {error && <div style={styles.error}>{error}</div>}

      {!loading && !error && data && data.items.length === 0 && (
        <div style={styles.empty}>Нет записей аудита</div>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>Время</th>
                <th style={styles.th}>Действие</th>
                <th style={styles.th}>Исполнитель</th>
                <th style={styles.th}>Тип объекта</th>
                <th style={styles.th}>Объект</th>
                <th style={styles.th}>Детали</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((event: AuditEventOut) => (
                <tr key={event.id}>
                  <td style={styles.td}>{formatTime(event.created_at)}</td>
                  <td style={styles.td}>
                    <span style={styles.actionPill(event.action)}>{actionLabel(event.action)}</span>
                  </td>
                  <td style={{ ...styles.td, ...styles.mono }}>{event.actor_user_id || "—"}</td>
                  <td style={styles.td}>{event.target_type}</td>
                  <td style={{ ...styles.td, ...styles.mono }}>{event.target_id || "—"}</td>
                  <td style={{ ...styles.td, ...styles.details }}>
                    <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontSize: "0.75rem" }}>
                      {renderDetails(event.details_json)}
                    </pre>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div style={styles.pagination}>
            <span>
              Всего: {data.total} · Стр. {currentPage} из {totalPages || 1}
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
                disabled={offset + PAGE_SIZE >= data.total}
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
