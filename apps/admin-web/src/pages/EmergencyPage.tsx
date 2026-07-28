import { useState, useEffect, useCallback } from "react";
import { api, ApiError, type EmergencyStatusOut } from "../api/client";

const styles = {
  page: { fontFamily: "system-ui, sans-serif" },
  h1: { fontSize: "1.5rem", fontWeight: 600, margin: "0 0 1rem" },
  card: { padding: "1.5rem", borderRadius: 8, background: "#fff", border: "1px solid #e2e8f0", marginBottom: "1.5rem" },
  statusActive: { display: "inline-block", padding: "0.25rem 0.75rem", borderRadius: 9999, fontSize: "0.85rem", fontWeight: 700, background: "#fef2f2", color: "#991b1b" },
  statusInactive: { display: "inline-block", padding: "0.25rem 0.75rem", borderRadius: 9999, fontSize: "0.85rem", fontWeight: 700, background: "#f0fdf4", color: "#166534" },
  warning: { padding: "1rem", marginBottom: "1rem", borderRadius: 6, background: "#fef2f2", border: "2px solid #dc2626", color: "#991b1b" },
  label: { display: "block", fontSize: "0.85rem", color: "#64748b", marginBottom: "0.25rem" },
  value: { fontSize: "1rem", color: "#0f172a", marginBottom: "0.75rem" },
  form: { display: "flex", flexDirection: "column" as const, gap: "0.75rem", maxWidth: 400 },
  textarea: { width: "100%", minHeight: 80, padding: "0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.9rem", resize: "vertical" as const },
  btnDanger: { padding: "0.6rem 1.2rem", border: "none", borderRadius: 6, background: "#dc2626", color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: "0.9rem" },
  btnSecondary: { padding: "0.5rem 1rem", border: "1px solid #cbd5e1", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: "0.85rem" },
  loading: { padding: "2rem", textAlign: "center" as const, color: "#94a3b8" },
  error: { padding: "1rem", color: "#991b1b", background: "#fef2f2", borderRadius: 6, marginBottom: "1rem" },
  success: { padding: "1rem", color: "#166534", background: "#f0fdf4", borderRadius: 6, marginBottom: "1rem" },
  meta: { fontSize: "0.8rem", color: "#94a3b8", marginTop: "0.5rem" },
  confirmRow: { display: "flex", gap: "0.5rem", alignItems: "center" },
};

function formatTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("ru-RU", { timeZone: "Europe/Moscow" });
  } catch {
    return iso;
  }
}

export default function EmergencyPage() {
  const [status, setStatus] = useState<EmergencyStatusOut | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [confirmMode, setConfirmMode] = useState<"activate" | "deactivate" | null>(null);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    setError(null);
    setPermissionDenied(false);
    try {
      const res = await api.get<EmergencyStatusOut>("/emergency/status");
      setStatus(res);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setPermissionDenied(true);
      } else {
        setError(e instanceof Error ? e.message : "Ошибка загрузки");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  async function handleActivate() {
    setError(null);
    setSuccessMsg(null);
    try {
      await api.post("/emergency/activate", { reason });
      setSuccessMsg("Аварийный режим активирован");
      setReason("");
      setConfirmMode(null);
      await fetchStatus();
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setError("Недостаточно прав для активации аварийного режима");
      } else if (e instanceof ApiError && e.status === 409) {
        setError("Аварийный режим уже активен");
      } else {
        setError(e instanceof Error ? e.message : "Ошибка активации");
      }
      setConfirmMode(null);
    }
  }

  async function handleDeactivate() {
    setError(null);
    setSuccessMsg(null);
    try {
      await api.post("/emergency/deactivate", { reason });
      setSuccessMsg("Аварийный режим деактивирован");
      setReason("");
      setConfirmMode(null);
      await fetchStatus();
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setError("Недостаточно прав для деактивации аварийного режима");
      } else if (e instanceof ApiError && e.status === 409) {
        setError("Аварийный режим не активен");
      } else {
        setError(e instanceof Error ? e.message : "Ошибка деактивации");
      }
      setConfirmMode(null);
    }
  }

  const isActive = status?.active === true;

  return (
    <div style={styles.page} data-testid="emergency-page">
      <h1 style={styles.h1}>Аварийный режим</h1>

      {loading && <div style={styles.loading}>Загрузка...</div>}
      {permissionDenied && (
        <div style={styles.error}>
          Недостаточно прав для доступа к аварийному режиму. Требуется разрешение emergency.read.
        </div>
      )}
      {error && <div style={styles.error} data-testid="emergency-error">{error}</div>}
      {successMsg && <div style={styles.success} data-testid="emergency-success">{successMsg}</div>}

      {status && (
        <>
          <div style={styles.card}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.75rem" }}>
              <span>Статус:</span>
              <span style={isActive ? styles.statusActive : styles.statusInactive} data-testid="emergency-status">
                {isActive ? "АКТИВЕН" : "НЕ АКТИВЕН"}
              </span>
            </div>
            {isActive && (
              <>
                <div style={styles.label}>Причина активации</div>
                <div style={styles.value}>{status.reason || "—"}</div>
                <div style={styles.label}>Активировал</div>
                <div style={styles.value}>{status.activated_by || "—"}</div>
                <div style={styles.label}>Время активации</div>
                <div style={styles.value}>{formatTime(status.activated_at)}</div>
              </>
            )}
          </div>

          {isActive && (
            <div style={styles.warning} data-testid="emergency-warning">
              <strong>⚠️ Внимание:</strong> аварийный режим активирован на уровне платформы.
              Состояние сохранено в backend, события аудита и outbox записаны.
              Остановка показа на реальных устройствах произойдёт только после реализации
              player-side emergency handling в KSO runtime.
            </div>
          )}

          {!isActive && (
            <div style={styles.card}>
              <div style={styles.label}>Причина активации *</div>
              <textarea
                style={styles.textarea}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                data-testid="emergency-reason-input"
                placeholder="Опишите причину включения аварийного режима"
                maxLength={500}
              />
              {confirmMode === "activate" ? (
                <div style={styles.confirmRow}>
                  <span style={{ color: "#991b1b", fontWeight: 600 }}>Подтвердите активацию:</span>
                  <button style={styles.btnDanger} disabled={!reason.trim()} onClick={handleActivate} data-testid="emergency-confirm-activate">
                    Да, активировать
                  </button>
                  <button style={styles.btnSecondary} onClick={() => { setConfirmMode(null); setReason(""); }}>
                    Отмена
                  </button>
                </div>
              ) : (
                <button
                  style={{ ...styles.btnDanger, marginTop: "0.5rem" }}
                  disabled={!reason.trim()}
                  onClick={() => setConfirmMode("activate")}
                  data-testid="emergency-activate-btn"
                >
                  Активировать аварийный режим
                </button>
              )}
            </div>
          )}

          {isActive && (
            <div style={styles.card}>
              <div style={styles.label}>Причина деактивации *</div>
              <textarea
                style={styles.textarea}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                data-testid="emergency-reason-input"
                placeholder="Опишите причину отключения аварийного режима"
                maxLength={500}
              />
              {confirmMode === "deactivate" ? (
                <div style={styles.confirmRow}>
                  <span style={{ color: "#166534", fontWeight: 600 }}>Подтвердите деактивацию:</span>
                  <button style={{ ...styles.btnDanger, background: "#16a34a" }} disabled={!reason.trim()} onClick={handleDeactivate} data-testid="emergency-confirm-deactivate">
                    Да, деактивировать
                  </button>
                  <button style={styles.btnSecondary} onClick={() => { setConfirmMode(null); setReason(""); }}>
                    Отмена
                  </button>
                </div>
              ) : (
                <button
                  style={{ ...styles.btnDanger, background: "#16a34a", marginTop: "0.5rem" }}
                  disabled={!reason.trim()}
                  onClick={() => setConfirmMode("deactivate")}
                  data-testid="emergency-deactivate-btn"
                >
                  Деактивировать аварийный режим
                </button>
              )}
            </div>
          )}

          <div style={styles.meta} data-testid="emergency-scope-note">
            Текущий scope: platform emergency state (backend) + audit/outbox events.
            Player-side enforcement (остановка показа на устройствах) — deferred, требует KSO runtime integration.
          </div>
        </>
      )}
    </div>
  );
}
