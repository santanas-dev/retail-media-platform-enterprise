import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

type AuthProvider = "local_advertiser" | "local_break_glass" | "ad";

const PROVIDER_LABELS: Record<AuthProvider, string> = {
  local_advertiser: "Рекламодатель",
  local_break_glass: "Break-glass Admin",
  ad: "Сотрудник / AD",
};

export default function LoginPage() {
  const { login, loading, error } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [provider, setProvider] = useState<AuthProvider>("local_advertiser");
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
        background: "#f5f5f5",
        fontFamily: "system-ui, sans-serif",
      }}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          background: "#fff",
          padding: "2rem",
          borderRadius: 8,
          boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
          width: "100%",
          maxWidth: 360,
        }}
      >
        <h1 style={{ margin: "0 0 0.5rem", fontSize: "1.25rem" }}>
          Центр управления рекламой
        </h1>
        <p style={{ margin: "0 0 1.5rem", color: "#666", fontSize: "0.875rem" }}>
          Войдите в систему
        </p>

        {displayError && (
          <div
            role="alert"
            style={{
              background: "#fef2f2",
              color: "#991b1b",
              padding: "0.5rem 0.75rem",
              borderRadius: 4,
              marginBottom: "1rem",
              fontSize: "0.875rem",
            }}
          >
            {displayError}
          </div>
        )}

        <label
          htmlFor="login-provider"
          style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500, fontSize: "0.875rem" }}
        >
          Тип учётной записи
        </label>
        <select
          id="login-provider"
          value={provider}
          onChange={(e) => setProvider(e.target.value as AuthProvider)}
          style={{
            width: "100%",
            padding: "0.5rem",
            marginBottom: "1rem",
            border: "1px solid #d1d5db",
            borderRadius: 4,
            fontSize: "0.875rem",
            boxSizing: "border-box",
            background: "#fff",
          }}
        >
          {Object.entries(PROVIDER_LABELS).map(([key, label]) => (
            <option key={key} value={key}>{label}</option>
          ))}
        </select>

        <label
          htmlFor="login-username"
          style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500, fontSize: "0.875rem" }}
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
            padding: "0.5rem",
            marginBottom: "1rem",
            border: "1px solid #d1d5db",
            borderRadius: 4,
            fontSize: "0.875rem",
            boxSizing: "border-box",
          }}
        />

        <label
          htmlFor="login-password"
          style={{ display: "block", marginBottom: "0.25rem", fontWeight: 500, fontSize: "0.875rem" }}
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
            padding: "0.5rem",
            marginBottom: "1rem",
            border: "1px solid #d1d5db",
            borderRadius: 4,
            fontSize: "0.875rem",
            boxSizing: "border-box",
          }}
        />

        <button
          type="submit"
          disabled={loading}
          style={{
            width: "100%",
            padding: "0.5rem",
            background: loading ? "#9ca3af" : "#2563eb",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            fontSize: "0.875rem",
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
