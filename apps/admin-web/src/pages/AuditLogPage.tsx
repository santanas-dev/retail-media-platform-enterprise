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
  table: { width: "100%", borderCollapse: "collapse" as const, fontSize: "0.85rem", background: "var(--rmp-bg-surface)" },
  th: { textAlign: "left" as const, padding: "0.5rem", borderBottom: "2px solid var(--rmp-border)", color: "var(--rmp-text-secondary)", fontWeight: 600, whiteSpace: "nowrap" as const },
  td: { padding: "0.5rem", borderBottom: "1px solid var(--rmp-border)", verticalAlign: "top" as const },
  mono: { fontFamily: "monospace", fontSize: "0.8rem", color: "var(--rmp-gray-700)" },
  actionPill: (action: string): React.CSSProperties => ({
    display: "inline-block",
    padding: "0.1rem 0.4rem",
    borderRadius: 4,
    fontSize: "0.75rem",
    fontWeight: 600,
    background: action.includes("failure") || action.includes("blocked") ? "var(--rmp-danger-50)"
               : action.includes("success") || action.includes("login") ? "var(--rmp-success-50)"
               : "var(--rmp-gray-100)",
    color: action.includes("failure") || action.includes("blocked") ? "var(--rmp-danger-800)"
          : action.includes("success") || action.includes("login") ? "var(--rmp-success-800)"
          : "var(--rmp-gray-700)",
  }),
  pagination: { display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1rem", fontSize: "0.85rem" },
  btn: { padding: "0.3rem 0.7rem", border: "1px solid var(--rmp-border-strong)", borderRadius: 4, background: "var(--rmp-bg-surface)", cursor: "pointer", fontSize: "0.85rem" },
  loading: { padding: "2rem", textAlign: "center" as const, color: "var(--rmp-text-muted)" },
  error: { padding: "1rem", color: "var(--rmp-danger-800)", background: "var(--rmp-danger-50)", borderRadius: 6 },
  empty: { padding: "2rem", textAlign: "center" as const, color: "var(--rmp-text-muted)" },
  details: { fontSize: "0.78rem", color: "var(--rmp-gray-600)", wordBreak: "break-all" as const },
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
      "emergency.activated": "Аварийный режим",
      "emergency.deactivated": "Отмена аварийного режима",
    };
    return map[action] || action;
  }

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <div style={styles.page} data-testid="audit-page">
      <div style={styles.header}>
        <h1 style={styles.h1}>Журнал аудита</h1>
      </div>

      {loading && <div style={styles.loading} data-testid="audit-loading">Загрузка...</div>}
      {error && <div style={styles.error} data-testid="audit-error">{error}</div>}

      {!loading && !error && data && data.items.length === 0 && (
        <div style={styles.empty} data-testid="audit-empty">Нет записей аудита</div>
      )}

      {!loading && !error && data && data.items.length > 0 && (
        <>
          <table style={styles.table} data-testid="audit-table">
            <thead>
              <tr>
                <th style={styles.th}>Время</th>
                <th style={styles.th}>Действие</th>
                <th style={styles.th}>Исполнитель</th>
                <th style={styles.th}>Ресурс</th>
                <th style={styles.th}>Детали</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((event: AuditEventOut) => (
                <tr key={event.id} data-testid={`audit-row-${event.id}`}>
                  <td style={styles.td} data-testid={`audit-created-at-${event.id}`}>{formatTime(event.created_at)}</td>
                  <td style={styles.td} data-testid={`audit-action-${event.id}`}>
                    <span style={styles.actionPill(event.action)}>{actionLabel(event.action)}</span>
                  </td>
                  <td style={{ ...styles.td, ...styles.mono }} data-testid={`audit-actor-${event.id}`}>{event.actor_user_id || "—"}</td>
                  <td style={styles.td} data-testid={`audit-resource-${event.id}`}>{event.target_type}{event.target_id ? `: ${event.target_id}` : ""}</td>
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
