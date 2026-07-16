import { useState } from "react";
import { ApiError } from "../api/client";

const PUBLIC_BASE = "/api/v1/public";

const S = {
  page: { maxWidth: 600, margin: "2rem auto", padding: "0 1rem", fontFamily: "system-ui, sans-serif" },
  h1: { fontSize: "1.5rem", fontWeight: 700, margin: "0 0 0.5rem" },
  subtitle: { color: "#64748b", marginBottom: "1.5rem", lineHeight: 1.5 },
  field: { marginBottom: "1rem" },
  label: { display: "block", fontSize: "0.85rem", fontWeight: 600, marginBottom: "0.25rem" },
  input: { width: "100%", padding: "0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.95rem", boxSizing: "border-box" as const },
  textarea: { width: "100%", padding: "0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.95rem", resize: "vertical" as const, minHeight: 80, boxSizing: "border-box" as const },
  required: { color: "#dc2626" },
  checkbox: { display: "flex", alignItems: "flex-start", gap: "0.5rem" },
  checkboxLabel: { fontSize: "0.85rem", color: "#475569", cursor: "pointer" },
  btn: { padding: "0.6rem 1.5rem", border: "none", borderRadius: 6, background: "#2563eb", color: "#fff", fontWeight: 600, fontSize: "1rem", cursor: "pointer" },
  btnDisabled: { padding: "0.6rem 1.5rem", border: "none", borderRadius: 6, background: "#93c5fd", color: "#fff", fontWeight: 600, fontSize: "1rem", cursor: "not-allowed" },
  error: { padding: "1rem", color: "#991b1b", background: "#fef2f2", borderRadius: 6, marginBottom: "1rem" },
  success: { padding: "1.5rem", color: "#166534", background: "#f0fdf4", borderRadius: 6, textAlign: "center" as const },
  successTitle: { fontSize: "1.2rem", fontWeight: 700, marginBottom: "0.5rem" },
  successBody: { color: "#166534", lineHeight: 1.6 },
  validation: { color: "#dc2626", fontSize: "0.8rem", marginTop: "0.25rem" },
};

interface FormData {
  company_name: string;
  contact_name: string;
  email: string;
  phone: string;
  website: string;
  comment: string;
  consent: boolean;
}

interface FormErrors {
  company_name?: string;
  contact_name?: string;
  email?: string;
  consent?: string;
}

function validate(form: FormData): FormErrors {
  const errors: FormErrors = {};
  if (!form.company_name.trim()) errors.company_name = "Обязательное поле";
  if (!form.contact_name.trim()) errors.contact_name = "Обязательное поле";
  if (!form.email.trim()) errors.email = "Обязательное поле";
  if (!form.consent) errors.consent = "Необходимо согласие на обработку данных";
  return errors;
}

export default function ApplyAdvertiserPage() {
  const [form, setForm] = useState<FormData>({
    company_name: "",
    contact_name: "",
    email: "",
    phone: "",
    website: "",
    comment: "",
    consent: false,
  });
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function onChange(field: keyof FormData, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(null);

    const clientErrors = validate(form);
    if (Object.keys(clientErrors).length > 0) {
      setErrors(clientErrors);
      return;
    }

    setSubmitting(true);
    try {
      const resp = await fetch(`${PUBLIC_BASE}/advertiser-applications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: form.company_name.trim(),
          contact_name: form.contact_name.trim(),
          email: form.email.trim(),
          phone: form.phone.trim(),
          website: form.website.trim(),
          comment: form.comment.trim(),
          consent: form.consent,
        }),
      });

      if (!resp.ok) {
        let detail = "Ошибка отправки заявки";
        try {
          const body = await resp.json();
          detail = body.detail || detail;
        } catch {}
        throw new ApiError(resp.status, { detail });
      }

      setSubmitted(true);
    } catch (e) {
      setServerError(e instanceof ApiError ? e.message : "Ошибка соединения");
    } finally {
      setSubmitting(false);
    }
  }

  if (submitted) {
    return (
      <div style={S.page}>
        <div style={S.success}>
          <div style={S.successTitle}>Заявка отправлена</div>
          <div style={S.successBody}>
            Спасибо! Ваша заявка на подключение отправлена на рассмотрение.
            Это не даёт немедленного доступа к платформе — заявка проходит проверку
            администратором. Мы свяжемся с вами после рассмотрения.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Стать рекламодателем</h1>
      <div style={S.subtitle}>
        Заполните заявку, и мы рассмотрим возможность подключения вашей компании
        к платформе Retail Media.
      </div>

      {serverError && <div style={S.error}>{serverError}</div>}

      <form onSubmit={handleSubmit}>
        <div style={S.field}>
          <label style={S.label}>Название компании <span style={S.required}>*</span></label>
          <input
            style={S.input}
            type="text"
            value={form.company_name}
            onChange={(e) => onChange("company_name", e.target.value)}
            placeholder="ООО Ромашка"
          />
          {errors.company_name && <div style={S.validation}>{errors.company_name}</div>}
        </div>

        <div style={S.field}>
          <label style={S.label}>Контактное лицо <span style={S.required}>*</span></label>
          <input
            style={S.input}
            type="text"
            value={form.contact_name}
            onChange={(e) => onChange("contact_name", e.target.value)}
            placeholder="Иванов Иван"
          />
          {errors.contact_name && <div style={S.validation}>{errors.contact_name}</div>}
        </div>

        <div style={S.field}>
          <label style={S.label}>Email <span style={S.required}>*</span></label>
          <input
            style={S.input}
            type="email"
            value={form.email}
            onChange={(e) => onChange("email", e.target.value)}
            placeholder="ivan@example.com"
          />
          {errors.email && <div style={S.validation}>{errors.email}</div>}
        </div>

        <div style={S.field}>
          <label style={S.label}>Телефон</label>
          <input
            style={S.input}
            type="tel"
            value={form.phone}
            onChange={(e) => onChange("phone", e.target.value)}
            placeholder="+7 (999) 123-45-67"
          />
        </div>

        <div style={S.field}>
          <label style={S.label}>Сайт</label>
          <input
            style={S.input}
            type="url"
            value={form.website}
            onChange={(e) => onChange("website", e.target.value)}
            placeholder="https://example.com"
          />
        </div>

        <div style={S.field}>
          <label style={S.label}>Комментарий</label>
          <textarea
            style={S.textarea}
            value={form.comment}
            onChange={(e) => onChange("comment", e.target.value)}
            placeholder="Дополнительная информация о вашей компании или целях рекламы"
          />
        </div>

        <div style={S.field}>
          <div style={S.checkbox}>
            <input
              type="checkbox"
              id="consent"
              checked={form.consent}
              onChange={(e) => onChange("consent", e.target.checked)}
              style={{ marginTop: "0.25rem" }}
            />
            <label htmlFor="consent" style={S.checkboxLabel}>
              Я даю согласие на обработку персональных данных <span style={S.required}>*</span>
            </label>
          </div>
          {errors.consent && <div style={S.validation}>{errors.consent}</div>}
        </div>

        <div style={{ marginTop: "1.5rem" }}>
          <button
            type="submit"
            disabled={submitting}
            style={submitting ? S.btnDisabled : S.btn}
          >
            {submitting ? "Отправка..." : "Отправить заявку"}
          </button>
        </div>
      </form>
    </div>
  );
}
