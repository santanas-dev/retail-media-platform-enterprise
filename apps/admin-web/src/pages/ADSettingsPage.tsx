import { useState, useEffect } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

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

const certLabel = (val: string): string => {
  const map: Record<string, string> = {
    required: "Обязательна",
    optional: "Опциональна",
    none: "Отключена",
  };
  return map[val] ?? val;
};

export default function ADSettingsPage() {
  const { user } = useAuth();
  const canManage = user?.permissions?.includes("users.manage");

  const [settings, setSettings] = useState<ADSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<ADTestResult | null>(null);
  const [testing, setTesting] = useState(false);

  // Form fields
  const [editEnabled, setEditEnabled] = useState(false);
  const [editServerUrl, setEditServerUrl] = useState("");
  const [editBaseDn, setEditBaseDn] = useState("");
  const [editUserSearchBase, setEditUserSearchBase] = useState("");
  const [editUserSearchFilter, setEditUserSearchFilter] = useState("");
  const [editBindDn, setEditBindDn] = useState("");
  const [editUseTls, setEditUseTls] = useState(true);
  const [editCertValidation, setEditCertValidation] = useState("required");

  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    loadSettings();
  }, []);

  function populateForm(s: ADSettings) {
    setEditEnabled(s.enabled);
    setEditServerUrl(s.server_url);
    setEditBaseDn(s.base_dn);
    setEditUserSearchBase(s.user_search_base);
    setEditUserSearchFilter(s.user_search_filter);
    setEditBindDn(s.bind_dn);
    setEditUseTls(s.use_tls);
    setEditCertValidation(s.certificate_validation);
  }

  async function loadSettings() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get<ADSettings>("/auth/ad-settings");
      setSettings(data);
      populateForm(data);
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

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      const payload = {
        enabled: editEnabled,
        server_url: editServerUrl,
        base_dn: editBaseDn,
        user_search_base: editUserSearchBase,
        user_search_filter: editUserSearchFilter,
        bind_dn: editBindDn,
        use_tls: editUseTls,
        certificate_validation: editCertValidation,
      };
      const updated = await api.put<ADSettings>("/auth/ad-settings", payload);
      setSettings(updated);
      populateForm(updated);
      setSaveSuccess(true);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Ошибка сохранения";
      setSaveError(msg);
    } finally {
      setSaving(false);
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
    primaryBtn: {
      padding: "0.5rem 1.25rem",
      fontSize: "0.875rem",
      border: "none",
      borderRadius: 6,
      background: "#2563eb",
      color: "#fff",
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
    field: {
      display: "flex",
      flexDirection: "column" as const,
      marginBottom: "0.65rem",
    },
    fieldLabel: {
      fontSize: "0.8rem",
      fontWeight: 500,
      color: "#475569",
      marginBottom: "0.2rem",
    },
    input: {
      padding: "0.4rem 0.55rem",
      fontSize: "0.85rem",
      border: "1px solid #cbd5e1",
      borderRadius: 4,
      width: "100%",
      boxSizing: "border-box" as const,
    },
    select: {
      padding: "0.4rem 0.55rem",
      fontSize: "0.85rem",
      border: "1px solid #cbd5e1",
      borderRadius: 4,
      background: "#fff",
    },
    checkbox: {
      marginRight: "0.4rem",
    },
    inlineRow: {
      display: "flex",
      alignItems: "center",
      gap: "0.3rem",
      fontSize: "0.85rem",
    },
    successBanner: {
      marginTop: "0.75rem",
      padding: "0.5rem 0.75rem",
      borderRadius: 4,
      background: "#dcfce7",
      color: "#166534",
      fontSize: "0.85rem",
    },
    errorBanner: {
      marginTop: "0.75rem",
      padding: "0.5rem 0.75rem",
      borderRadius: 4,
      background: "#fee2e2",
      color: "#991b1b",
      fontSize: "0.85rem",
    },
  };

  if (loading) return <p>Загрузка настроек AD...</p>;
  if (error) return <p style={{ color: "#dc2626" }}>{error}</p>;
  if (!settings) return <p>Настройки AD не найдены.</p>;

  return (
    <div style={styles.page} data-testid="adsettings-page">
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
        <button
          type="button"
          onClick={handleTest}
          disabled={testing}
          style={{ ...styles.btn, opacity: testing ? 0.5 : 1 }}
          data-testid="adsettings-test-btn"
        >
          {testing ? "Проверка..." : "Проверить подключение"}
        </button>
        {testResult && (
          <div style={styles.resultBox(testResult.status)}>
            <strong>{testStatusLabel(testResult.status)}</strong>
            <p style={{ margin: "0.25rem 0 0" }}>{testResult.message}</p>
          </div>
        )}
      </div>

      {/* Edit form */}
      {canManage && (
        <div style={styles.card} data-testid="adsettings-edit-form">
          <div style={styles.cardTitle}>Редактирование настроек</div>

          {/* Enabled checkbox */}
          <div style={styles.inlineRow}>
            <input
              type="checkbox"
              id="ad-enabled"
              checked={editEnabled}
              onChange={(e) => setEditEnabled(e.target.checked)}
              style={styles.checkbox}
              data-testid="adsettings-field-enabled"
            />
            <label htmlFor="ad-enabled" style={{ fontSize: "0.85rem", cursor: "pointer" }}>
              AD включён
            </label>
          </div>

          {/* Server URL */}
          <div style={styles.field}>
            <label style={styles.fieldLabel}>Сервер (LDAPS URL)</label>
            <input
              type="text"
              value={editServerUrl}
              onChange={(e) => setEditServerUrl(e.target.value)}
              style={styles.input}
              placeholder="ldaps://ad.example.com"
              data-testid="adsettings-field-server-url"
            />
          </div>

          {/* Base DN */}
          <div style={styles.field}>
            <label style={styles.fieldLabel}>Base DN</label>
            <input
              type="text"
              value={editBaseDn}
              onChange={(e) => setEditBaseDn(e.target.value)}
              style={styles.input}
              placeholder="dc=example,dc=com"
              data-testid="adsettings-field-base-dn"
            />
          </div>

          {/* User Search Base */}
          <div style={styles.field}>
            <label style={styles.fieldLabel}>User Search Base</label>
            <input
              type="text"
              value={editUserSearchBase}
              onChange={(e) => setEditUserSearchBase(e.target.value)}
              style={styles.input}
              placeholder="ou=users,dc=example,dc=com"
              data-testid="adsettings-field-search-base"
            />
          </div>

          {/* User Search Filter */}
          <div style={styles.field}>
            <label style={styles.fieldLabel}>Фильтр поиска</label>
            <input
              type="text"
              value={editUserSearchFilter}
              onChange={(e) => setEditUserSearchFilter(e.target.value)}
              style={styles.input}
              data-testid="adsettings-field-search-filter"
            />
          </div>

          {/* Bind DN */}
          <div style={styles.field}>
            <label style={styles.fieldLabel}>Bind DN</label>
            <input
              type="text"
              value={editBindDn}
              onChange={(e) => setEditBindDn(e.target.value)}
              style={styles.input}
              placeholder="cn=binduser,dc=example,dc=com"
              data-testid="adsettings-field-bind-dn"
            />
          </div>

          {/* TLS */}
          <div style={styles.inlineRow}>
            <input
              type="checkbox"
              id="ad-use-tls"
              checked={editUseTls}
              onChange={(e) => setEditUseTls(e.target.checked)}
              style={styles.checkbox}
              data-testid="adsettings-field-use-tls"
            />
            <label htmlFor="ad-use-tls" style={{ fontSize: "0.85rem", cursor: "pointer" }}>
              Использовать TLS
            </label>
          </div>

          {/* Certificate validation */}
          <div style={{ ...styles.field, marginTop: "0.5rem" }}>
            <label style={styles.fieldLabel}>Проверка сертификата</label>
            <select
              value={editCertValidation}
              onChange={(e) => setEditCertValidation(e.target.value)}
              style={styles.select}
              data-testid="adsettings-field-cert-validation"
            >
              <option value="required">Обязательна</option>
              <option value="optional">Опциональна</option>
              <option value="none">Отключена</option>
            </select>
          </div>

          {/* Save button */}
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            style={{
              ...styles.primaryBtn,
              opacity: saving ? 0.6 : 1,
              marginTop: "0.75rem",
            }}
            data-testid="adsettings-save-btn"
          >
            {saving ? "Сохранение..." : "Сохранить"}
          </button>

          {saveSuccess && (
            <div style={styles.successBanner} data-testid="adsettings-save-success">
              ✅ Настройки сохранены
            </div>
          )}
          {saveError && (
            <div style={styles.errorBanner} data-testid="adsettings-save-error">
              {saveError}
            </div>
          )}
        </div>
      )}

      {/* Config details (read-only summary) */}
      <div style={styles.card} data-testid="adsettings-details">
        <div style={styles.cardTitle}>Параметры подключения</div>
        <div style={styles.row}>
          <span style={styles.label}>Сервер</span>
          <span style={styles.value} data-testid="adsettings-detail-server-url">
            {settings.server_url || "не указан"}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>Base DN</span>
          <span style={styles.value} data-testid="adsettings-detail-base-dn">
            {settings.base_dn || "не указан"}
          </span>
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
          <span style={styles.value} data-testid="adsettings-detail-tls">
            {settings.use_tls ? "✅ Включён" : "❌ Выключен"}
          </span>
        </div>
        <div style={styles.row}>
          <span style={styles.label}>Проверка сертификата</span>
          <span style={styles.value} data-testid="adsettings-detail-cert">
            {certLabel(settings.certificate_validation)}
          </span>
        </div>
        <p style={{ margin: "0.75rem 0 0", fontSize: "0.75rem", color: "#94a3b8" }}>
          Пароль для bind (AD_BIND_PASSWORD) не отображается и не передаётся через API.
        </p>
      </div>
    </div>
  );
}
