import { useState, useEffect } from "react";
import { api, ApiError } from "../api/client";

interface ADSettings {
  enabled: boolean;
  mode: string;
  server_url: string;
  base_dn: string;
  user_search_base: string;
  user_search_filter: string;
  bind_dn: string;
  use_tls: boolean;
  certificate_validation: string;
  message: string;
}

interface ADTestResult {
  status: string;
  message: string;
  tested_at: string | null;
  error_code: string | null;
}

const modeLabel = (mode: string): string => {
  const map: Record<string, string> = {
    disabled: "Отключён",
    stub: "Заглушка (stub)",
    configured: "Настроен",
  };
  return map[mode] ?? mode;
};

const modeColor = (mode: string): string => {
  const map: Record<string, string> = {
    disabled: "#94a3b8",
    stub: "#f59e0b",
    configured: "#16a34a",
  };
  return map[mode] ?? "#94a3b8";
};

const testStatusLabel = (status: string): string => {
  const map: Record<string, string> = {
    ok: "✅ Подключение успешно",
    stub: "⚠️ Заглушка",
    not_configured: "❌ Не настроено",
    error: "❌ Ошибка",
  };
  return map[status] ?? status;
};

export default function ADSettingsPage() {
  const [settings, setSettings] = useState<ADSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<ADTestResult | null>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  async function loadSettings() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ADSettings>("/auth/ad-settings");
      setSettings(data);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка загрузки настроек";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.post<ADTestResult>("/auth/ad-settings/test");
      setTestResult(result);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка проверки";
      setTestResult({
        status: "error",
        message: msg,
        tested_at: null,
        error_code: null,
      });
    } finally {
      setTesting(false);
    }
  }

  const styles = {
    page: { maxWidth: 800, margin: "0 auto" } as React.CSSProperties,
    card: {
      background: "#fff",
      border: "1px solid #e2e8f0",
      borderRadius: 8,
      padding: "1.25rem",
      marginBottom: "1rem",
    } as React.CSSProperties,
    cardTitle: {
      fontSize: "1rem",
      fontWeight: 600,
      margin: "0 0 0.75rem",
      color: "#1e293b",
    } as React.CSSProperties,
    row: {
      display: "flex",
      justifyContent: "space-between",
      padding: "0.35rem 0",
      borderBottom: "1px solid #f1f5f9",
      fontSize: "0.85rem",
    } as React.CSSProperties,
    label: { color: "#64748b" } as React.CSSProperties,
    value: { color: "#1e293b", fontWeight: 500, textAlign: "right" as const } as React.CSSProperties,
    badge: (color: string): React.CSSProperties => ({
      display: "inline-block",
      padding: "0.15rem 0.5rem",
      borderRadius: 4,
      background: color,
      color: "#fff",
      fontSize: "0.75rem",
      fontWeight: 600,
    }),
    btn: {
      padding: "0.5rem 1.25rem",
      fontSize: "0.875rem",
      border: "1px solid #cbd5e1",
      borderRadius: 6,
      background: "#fff",
      cursor: "pointer",
      marginTop: "0.5rem",
    } as React.CSSProperties,
    resultBox: (status: string): React.CSSProperties => ({
      marginTop: "0.75rem",
      padding: "0.75rem",
      borderRadius: 6,
      background: status === "ok" ? "#dcfce7" : status === "stub" ? "#fef3c7" : "#fee2e2",
      fontSize: "0.85rem",
      color: "#1e293b",
    }),
  };

  if (loading) return <p>Загрузка настроек AD...</p>;
  if (error) return <p style={{ color: "#dc2626" }}>{error}</p>;
  if (!settings) return <p>Настройки AD не найдены.</p>;

  return (
    <div style={styles.page}>
      <h1 style={{ margin: "0 0 1rem", fontSize: "1.25rem" }}>Настройки AD / LDAPS</h1>

      {/* Status card */}
      <div style={styles.card}>
        <div style={styles.cardTitle}>Статус подключения</div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
          <span style={styles.badge(modeColor(settings.mode))}>
            {modeLabel(settings.mode)}
          </span>
        </div>
        <p style={{ margin: 0, fontSize: "0.85rem", color: "#475569", lineHeight: 1.5 }}>
          {settings.message}
        </p>
        {settings.mode === "stub" && (
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.8rem", color: "#94a3b8" }}>
            Вход сотрудников через AD в настоящее время недоступен (возвращает 503).
            Локальные учётные записи рекламодателей управляются отдельно в разделе «Пользователи».
          </p>
        )}
        <button
          type="button"
          onClick={handleTest}
          disabled={testing}
          style={{ ...styles.btn, opacity: testing ? 0.5 : 1 }}
        >
          {testing ? "Проверка..." : "Проверить подключение"}
        </button>
        {testResult && (
          <div style={styles.resultBox(testResult.status)}>
            <strong>{testStatusLabel(testResult.status)}</strong>
            <p style={{ margin: "0.25rem 0 0" }}>{testResult.message}</p>
            {testResult.tested_at && (
              <p style={{ margin: "0.25rem 0 0", fontSize: "0.75rem", color: "#94a3b8" }}>
                Проверено: {new Date(testResult.tested_at).toLocaleString("ru-RU")}
              </p>
            )}
          </div>
        )}
      </div>

      {/* Config details */}
      <div style={styles.card}>
        <div style={styles.cardTitle}>Параметры подключения</div>
        <div style={styles.row}>
          <span style={styles.label}>Сервер</span>
          <span style={styles.value}>{settings.server_url || "не указан"}</span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>Base DN</span>
          <span style={styles.value}>{settings.base_dn || "не указан"}</span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>Search Base</span>
          <span style={styles.value}>{settings.user_search_base || "не указан"}</span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>Search Filter</span>
          <span style={styles.value}><code>{settings.user_search_filter}</code></span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>Bind DN</span>
          <span style={styles.value}>{settings.bind_dn || "не указан"}</span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>TLS</span>
          <span style={styles.value}>{settings.use_tls ? "✅ Включён" : "❌ Выключен"}</span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>Проверка сертификата</span>
          <span style={styles.value}>
            {settings.certificate_validation === "required"
              ? "Обязательна"
              : settings.certificate_validation === "optional"
              ? "Опциональна"
              : "Отключена"}
          </span>
        </div>
        <p style={{ margin: "0.75rem 0 0", fontSize: "0.75rem", color: "#94a3b8" }}>
          Пароль для bind (AD_BIND_PASSWORD) не отображается и не передаётся через API.
        </p>
      </div>
    </div>
  );
}
