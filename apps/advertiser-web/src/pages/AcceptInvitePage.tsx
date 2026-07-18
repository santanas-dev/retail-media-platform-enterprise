import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { ApiError } from "../api/client";

const PUBLIC_BASE = "/api/v1/public";

const S = {
  page: { maxWidth: 480, margin: "4rem auto", padding: "0 1rem", fontFamily: "system-ui, sans-serif" },
  h1: { fontSize: "1.5rem", fontWeight: 700, margin: "0 0 1rem", textAlign: "center" as const },
  field: { marginBottom: "1rem" },
  label: { display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" },
  input: { width: "100%", padding: "0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.95rem", boxSizing: "border-box" as const },
  btn: { width: "100%", padding: "0.6rem", border: "none", borderRadius: 6, background: "#2563eb", color: "#fff", fontWeight: 600, fontSize: "1rem", cursor: "pointer" },
  btnDisabled: { width: "100%", padding: "0.6rem", border: "none", borderRadius: 6, background: "#93c5fd", color: "#fff", fontWeight: 600, fontSize: "1rem", cursor: "not-allowed" },
  error: { padding: "1rem", color: "#991b1b", background: "#fef2f2", borderRadius: 6, marginBottom: "1rem", textAlign: "center" as const },
  success: { padding: "1.5rem", color: "#166534", background: "#f0fdf4", borderRadius: 6, textAlign: "center" as const },
  successTitle: { fontSize: "1.2rem", fontWeight: 700, marginBottom: "0.5rem" },
  validation: { color: "#dc2626", fontSize: "0.8rem", marginTop: "0.25rem" },
  hint: { color: "#64748b", fontSize: "0.8rem", marginTop: "0.25rem" },
};

export default function AcceptInvitePage() {
  const { token } = useParams<{ token: string }>();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Пароль должен быть не менее 8 символов");
      return;
    }

    setSubmitting(true);
    try {
      const resp = await fetch(`${PUBLIC_BASE}/advertiser-invites/${token}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });

      if (!resp.ok) {
        let detail = "Ошибка активации";
        try {
          const body = await resp.json();
          detail = body.detail || detail;
        } catch {}
        throw new ApiError(resp.status, { detail });
      }

      setSuccess(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Ошибка соединения");
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <div style={S.page}>
        <div style={S.error}>Не указан код приглашения. Проверьте ссылку.</div>
      </div>
    );
  }

  if (success) {
    return (
      <div style={S.page}>
        <div style={S.success}>
          <div style={S.successTitle}>Приглашение принято!</div>
          <div style={{ color: "#166534", lineHeight: 1.6, marginBottom: "1rem" }}>
            Ваша учётная запись создана. Теперь вы можете войти в портал рекламодателя.
          </div>
          <Link
            to="/login"
            style={{ color: "#2563eb", fontWeight: 600, textDecoration: "none" }}
          >
            Перейти к входу
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Принять приглашение</h1>

      {error && <div style={S.error}>{error}</div>}

      <form onSubmit={handleSubmit}>
        <div style={S.field}>
          <label style={S.label}>Придумайте пароль для входа</label>
          <input
            style={S.input}
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Минимум 8 символов"
            autoFocus
          />
          <div style={S.hint}>Пароль будет использоваться для входа в портал рекламодателя</div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          style={submitting ? S.btnDisabled : S.btn}
        >
          {submitting ? "Активация..." : "Активировать доступ"}
        </button>
      </form>
    </div>
  );
}
