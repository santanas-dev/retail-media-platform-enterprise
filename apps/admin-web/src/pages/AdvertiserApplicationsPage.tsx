import { useState, useEffect, useCallback } from "react";
import { api, ApiError } from "../api/client";
import type { AdvertiserApplicationOut, PaginatedApplications } from "../api/client";

const S = {
  page: { fontFamily: "system-ui, sans-serif" } as const,
  h1: { fontSize: "1.25rem", fontWeight: 600, margin: "0 0 1rem" } as const,
  table: { width: "100%", borderCollapse: "collapse" as const, fontSize: "0.9rem" },
  th: { textAlign: "left" as const, padding: "0.5rem", borderBottom: "2px solid #e2e8f0", background: "#f8fafc" },
  td: { padding: "0.5rem", borderBottom: "1px solid #e2e8f0", verticalAlign: "top" as const },
  badge: (color: string) =>
    ({ display: "inline-block", padding: "0.15rem 0.5rem", borderRadius: 9999, fontSize: "0.75rem", fontWeight: 700, background: color, color: "#fff" }) as const,
  loading: { padding: "2rem", textAlign: "center" as const, color: "#94a3b8" },
  error: { padding: "1rem", color: "#991b1b", background: "#fef2f2", borderRadius: 6, marginBottom: "1rem" },
  detail: { marginTop: "1.5rem", padding: "1rem", borderRadius: 6, background: "#f8fafc", border: "1px solid #e2e8f0" },
  label: { fontSize: "0.8rem", color: "#64748b", marginBottom: "0.25rem" },
  value: { fontSize: "0.95rem", marginBottom: "0.75rem" },
  actions: { display: "flex", gap: "0.5rem", marginTop: "1rem" },
  btn: (bg: string) => ({ padding: "0.4rem 1rem", border: "none", borderRadius: 4, background: bg, color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: "0.85rem" }) as const,
  textarea: { width: "100%", minHeight: 60, padding: "0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.85rem", resize: "vertical" as const },
  success: { padding: "1rem", color: "#166534", background: "#f0fdf4", borderRadius: 6, marginBottom: "1rem" },
  tokenBox: { marginTop: "1rem", padding: "0.75rem", borderRadius: 6, background: "#fefce8", border: "1px solid #fde68a", fontSize: "0.8rem" },
  tokenCode: { fontSize: "0.75rem", fontFamily: "monospace", background: "#f1f5f9", padding: "0.25rem 0.5rem", borderRadius: 4, wordBreak: "break-all" as const },
  note: { color: "#92400e", fontSize: "0.75rem", marginTop: "0.5rem" },
};

const STATUS_LABELS: Record<string, string> = {
  new: "Новая",
  reviewing: "На рассмотрении",
  approved: "Одобрена",
  rejected: "Отклонена",
};

const STATUS_COLORS: Record<string, string> = {
  new: "#3b82f6",
  reviewing: "#f59e0b",
  approved: "#16a34a",
  rejected: "#dc2626",
};

const INVITE_STATUS_LABELS: Record<string, string> = {
  pending: "Ожидает принятия",
  accepted: "Принято",
  expired: "Истекло",
};

const INVITE_STATUS_COLORS: Record<string, string> = {
  pending: "#8b5cf6",
  accepted: "#16a34a",
  expired: "#94a3b8",
};

function formatDt(iso: string | null): string {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("ru-RU", { timeZone: "Europe/Moscow" }); } catch { return iso; }
}

interface InviteData {
  id: string;
  token: string;
  contact_email: string;
  status: string;
  expires_at: string;
  accepted_at: string | null;
}

export default function AdvertiserApplicationsPage() {
  const [apps, setApps] = useState<AdvertiserApplicationOut[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [selected, setSelected] = useState<AdvertiserApplicationOut | null>(null);
  const [reason, setReason] = useState("");
  const [invite, setInvite] = useState<InviteData | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);

  const fetchList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get<PaginatedApplications>("/advertiser-applications?limit=50");
      setApps(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка загрузки");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchList(); }, [fetchList]);

  const fetchInvite = useCallback(async (appId: string) => {
    setInviteLoading(true);
    try {
      const data = await api.get<InviteData | null>(`/advertiser-applications/${appId}/invite`);
      setInvite(data);
    } catch {
      setInvite(null);
    } finally {
      setInviteLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selected && selected.status === "approved") {
      fetchInvite(selected.id);
    } else {
      setInvite(null);
    }
  }, [selected, fetchInvite]);

  async function handleReview(action: "reviewing" | "approve" | "reject", appId: string) {
    setError(null);
    setSuccess(null);
    try {
      await api.post(`/advertiser-applications/${appId}/review`, { action, reason });
      const messages: Record<string, string> = {
        reviewing: "Заявка переведена в статус «На рассмотрении».",
        approve: "Заявка одобрена. Организация создана.",
        reject: "Заявка отклонена.",
      };
      setSuccess(messages[action]);
      setReason("");
      setSelected(null);
      await fetchList();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка");
    }
  }

  async function handleCreateInvite(appId: string) {
    setError(null);
    setSuccess(null);
    try {
      await api.post(`/advertiser-applications/${appId}/invite`);
      setSuccess("Приглашение создано.");
      await fetchInvite(appId);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка создания приглашения");
    }
  }

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Заявки рекламодателей ({total})</h1>

      {loading && <div style={S.loading}>Загрузка...</div>}
      {error && <div style={S.error}>{error}</div>}
      {success && <div style={S.success}>{success}</div>}

      {!loading && apps.length === 0 && !error && (
        <div style={{ color: "#94a3b8", padding: "2rem", textAlign: "center" }}>Нет заявок</div>
      )}

      {apps.length > 0 && (
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>Компания</th>
              <th style={S.th}>Контакт</th>
              <th style={S.th}>Email</th>
              <th style={S.th}>Статус</th>
              <th style={S.th}>Приглашение</th>
              <th style={S.th}>Дата</th>
            </tr>
          </thead>
          <tbody>
            {apps.map((a) => (
              <tr key={a.id} style={{ cursor: "pointer" }} onClick={() => setSelected(selected?.id === a.id ? null : a)}>
                <td style={S.td}>{a.company_name}</td>
                <td style={S.td}>{a.contact_name}</td>
                <td style={S.td}>{a.email}</td>
                <td style={S.td}>
                  <span style={S.badge(STATUS_COLORS[a.status] || "#94a3b8")}>{STATUS_LABELS[a.status] || a.status}</span>
                </td>
                <td style={S.td}>
                  {a.status === "approved" ? (selected?.id === a.id ? "..." : "—") : "—"}
                </td>
                <td style={S.td}>{formatDt(a.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selected && (
        <div style={S.detail}>
          <h3 style={{ margin: "0 0 0.75rem", fontSize: "1.1rem" }}>{selected.company_name}</h3>
          <div style={S.label}>Контакт</div><div style={S.value}>{selected.contact_name}</div>
          <div style={S.label}>Email</div><div style={S.value}>{selected.email}</div>
          {selected.phone && <><div style={S.label}>Телефон</div><div style={S.value}>{selected.phone}</div></>}
          {selected.website && <><div style={S.label}>Сайт</div><div style={S.value}>{selected.website}</div></>}
          {selected.comment && <><div style={S.label}>Комментарий</div><div style={S.value}>{selected.comment}</div></>}
          <div style={S.label}>Согласие на обработку</div><div style={S.value}>{selected.consent ? "✅ Да" : "❌ Нет"}</div>
          {selected.reviewed_at && <><div style={S.label}>Рассмотрена</div><div style={S.value}>{formatDt(selected.reviewed_at)}</div></>}
          {selected.review_reason && <><div style={S.label}>Причина решения</div><div style={S.value}>{selected.review_reason}</div></>}

          {selected.status === "new" && (
            <div>
              <div style={S.actions}>
                <button style={S.btn("#f59e0b")} onClick={() => handleReview("reviewing", selected.id)}>Начать рассмотрение</button>
              </div>
            </div>
          )}

          {selected.status === "reviewing" && (
            <div>
              <div style={S.label}>Причина решения</div>
              <textarea style={S.textarea} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Причина одобрения или отклонения" />
              <div style={S.actions}>
                <button style={S.btn("#16a34a")} onClick={() => handleReview("approve", selected.id)}>Одобрить</button>
                <button style={S.btn("#dc2626")} onClick={() => handleReview("reject", selected.id)}>Отклонить</button>
              </div>
            </div>
          )}

          {selected.status === "approved" && (
            <div>
              <div style={S.label}>Приглашение</div>
              {inviteLoading ? (
                <div style={S.value}>Загрузка...</div>
              ) : invite ? (
                <div>
                  <div style={S.value}>
                    <span style={S.badge(INVITE_STATUS_COLORS[invite.status] || "#94a3b8")}>
                      {INVITE_STATUS_LABELS[invite.status] || invite.status}
                    </span>
                    {" "}до {formatDt(invite.expires_at)}
                    {invite.accepted_at && <> — принято {formatDt(invite.accepted_at)}</>}
                  </div>
                  <div style={S.tokenBox}>
                    <div style={S.label}>Код приглашения (dev/pilot — реальная отправка email будет позже)</div>
                    <div style={S.tokenCode}>{invite.token}</div>
                    <div style={S.note}>⚠️ В режиме разработки токен показывается в интерфейсе. Скопируйте код и передайте контактному лицу. В production токен будет отправляться по email.</div>
                  </div>
                  <div style={S.actions}>
                    <button style={S.btn("#8b5cf6")} onClick={() => handleCreateInvite(selected.id)}>
                      {invite.status === "expired" || invite.status === "accepted" ? "Создать новое приглашение" : "Переслать приглашение"}
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div style={S.value}>Не отправлено</div>
                  <div style={S.actions}>
                    <button style={S.btn("#8b5cf6")} onClick={() => handleCreateInvite(selected.id)}>Создать приглашение</button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
