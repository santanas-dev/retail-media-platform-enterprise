import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

type AuthProvider = "local_advertiser" | "local_break_glass" | "ad";

const PROVIDER_LABELS: Record<AuthProvider, string> = {
  ad: "Сотрудник / AD",
  local_advertiser: "Рекламодатель",
  local_break_glass: "Break-glass Admin",
};

/** Admin portal — default to AD (employee) provider, not advertiser. */
const DEFAULT_PROVIDER: AuthProvider = "ad";

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [provider, setProvider] = useState<AuthProvider>(DEFAULT_PROVIDER);
  const [localError, setLocalError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    try {
      await login(username, password, provider);
      navigate("/campaigns", { replace: true });
    } catch (e: unknown) {
      if (e instanceof Error && e.message.includes("503")) {
        setLocalError("Сервис AD/LDAPS временно недоступен. Используйте вход рекламодателя или break-glass.");
      } else {
        setLocalError("Неверное имя пользователя или пароль.");
      }
    }
  }

  const displayError = localError || error;

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--rmp-gray-100)",
        fontFamily: "var(--rmp-font-family)",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: "var(--rmp-bg-surface)",
          padding: "var(--rmp-space-8)",
          borderRadius: "var(--rmp-radius-lg)",
          boxShadow: "var(--rmp-shadow-md)",
          width: "100%",
          maxWidth: 380,
        }}
      >
        <h1 style={{ margin: "0 0 var(--rmp-space-2)", fontSize: "var(--rmp-font-size-xl)", fontWeight: 600 }}>
          Центр управления рекламой
        </h1>
        <p style={{ margin: "0 0 var(--rmp-space-6)", color: "var(--rmp-text-secondary)", fontSize: "var(--rmp-font-size-base)" }}>
          Войдите в систему
        </p>

        {displayError && (
          <div
            role="alert"
            style={{
              background: "var(--rmp-danger-50)",
              color: "var(--rmp-danger-800)",
              padding: "var(--rmp-space-2) var(--rmp-space-3)",
              borderRadius: "var(--rmp-radius-sm)",
              marginBottom: "var(--rmp-space-4)",
              fontSize: "var(--rmp-font-size-base)",
            }}
          >
            {displayError}
          </div>
        )}

        <label
          htmlFor="login-provider"
          style={{ display: "block", marginBottom: "var(--rmp-space-1)", fontWeight: 500, fontSize: "var(--rmp-font-size-base)" }}
        >
          Тип учётной записи
        </label>
        <select
          id="login-provider"
          value={provider}
          onChange={(e) => setProvider(e.target.value as AuthProvider)}
          style={{
            width: "100%",
            padding: "var(--rmp-space-2)",
            marginBottom: "var(--rmp-space-4)",
            border: "1px solid var(--rmp-border-strong)",
            borderRadius: "var(--rmp-radius-sm)",
            fontSize: "var(--rmp-font-size-base)",
            boxSizing: "border-box",
            background: "var(--rmp-bg-surface)",
          }}
        >
          {Object.entries(PROVIDER_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>

        <label
          htmlFor="login-username"
          style={{ display: "block", marginBottom: "var(--rmp-space-1)", fontWeight: 500, fontSize: "var(--rmp-font-size-base)" }}
        >
          Имя пользователя
        </label>
        <input
          id="login-username"
          type="text"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          autoFocus
          style={{
            width: "100%",
            padding: "var(--rmp-space-2)",
            marginBottom: "var(--rmp-space-4)",
            border: "1px solid var(--rmp-border-strong)",
            borderRadius: "var(--rmp-radius-sm)",
            fontSize: "var(--rmp-font-size-base)",
            boxSizing: "border-box",
          }}
        />

        <label
          htmlFor="login-password"
          style={{ display: "block", marginBottom: "var(--rmp-space-1)", fontWeight: 500, fontSize: "var(--rmp-font-size-base)" }}
        >
          Пароль
        </label>
        <input
          id="login-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          style={{
            width: "100%",
            padding: "var(--rmp-space-2)",
            marginBottom: "var(--rmp-space-4)",
            border: "1px solid var(--rmp-border-strong)",
            borderRadius: "var(--rmp-radius-sm)",
            fontSize: "var(--rmp-font-size-base)",
            boxSizing: "border-box",
          }}
        />

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "var(--rmp-space-2) var(--rmp-space-4)",
            background: loading ? "var(--rmp-gray-400)" : "var(--rmp-primary-600)",
            color: "var(--rmp-text-inverse)",
            border: "none",
            borderRadius: "var(--rmp-radius-sm)",
            fontSize: "var(--rmp-font-size-base)",
            fontWeight: 500,
            cursor: loading ? "default" : "pointer",
          }}
        >
          {loading ? "Вход..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
