import { useState } from "react";

const S = {
  page: { fontFamily: "system-ui, sans-serif", maxWidth: 500, margin: "2rem auto", padding: "0 1rem" } as const,
  h1: { fontSize: "1.5rem", fontWeight: 600, marginBottom: "1.5rem" } as const,
  form: { display: "flex", flexDirection: "column" as const, gap: "0.75rem" },
  label: { fontSize: "0.85rem", color: "#475569", marginBottom: "0.15rem" },
  input: { width: "100%", padding: "0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.95rem", boxSizing: "border-box" as const },
  textarea: { width: "100%", minHeight: 80, padding: "0.5rem", border: "1px solid #cbd5e1", borderRadius: 4, fontSize: "0.95rem", resize: "vertical" as const, boxSizing: "border-box" as const },
  checkbox: { display: "flex", alignItems: "flex-start", gap: "0.5rem", fontSize: "0.85rem" } as const,
  btn: { padding: "0.7rem 1.5rem", border: "none", borderRadius: 6, background: "#2563eb", color: "#fff", fontWeight: 600, fontSize: "1rem", cursor: "pointer", alignSelf: "flex-start" as const },
  btnDisabled: { padding: "0.7rem 1.5rem", border: "none", borderRadius: 6, background: "#93c5fd", color: "#fff", fontWeight: 600, fontSize: "1rem", cursor: "not-allowed", alignSelf: "flex-start" as const },
  success: { padding: "2rem", textAlign: "center" as const, color: "#166534", background: "#f0fdf4", borderRadius: 8 },
  error: { padding: "1rem", color: "#991b1b", background: "#fef2f2", borderRadius: 6 },
  fieldError: { fontSize: "0.8rem", color: "#dc2626", marginTop: "0.15rem" },
};

export default function PublicApplicationForm() {
  const [form, setForm] = useState({ company_name: "", contact_name: "", email: "", phone: "", website: "", comment: "", consent: false });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  function update(field: string, value: string | boolean) {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => { const n = { ...prev }; delete n[field]; return n; });
  }

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!form.company_name.trim()) e.company_name = "Укажите название компании";
    if (!form.contact_name.trim()) e.contact_name = "Укажите контактное лицо";
    if (!form.email.trim()) e.email = "Укажите email";
    if (!form.consent) e.consent = "Необходимо согласие на обработку данных";
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  async function handleSubmit() {
    if (!validate()) return;
    setServerError(null);
    try {
      const res = await fetch("/api/v1/public/advertiser-applications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        setServerError(err.detail || "Ошибка отправки");
        return;
      }
      setSubmitted(true);
    } catch (e) {
      setServerError("Ошибка отправки. Попробуйте позже.");
    }
  }

  if (submitted) {
    return (
      <div style={S.page}>
        <div style={S.success}>
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "1.3rem" }}>Заявка отправлена</h2>
          <p style={{ margin: 0, fontSize: "0.95rem", color: "#166534" }}>
            Спасибо! Ваша заявка принята и будет рассмотрена в ближайшее время.
            Мы свяжемся с вами по указанному email.
          </p>
          <p style={{ marginTop: "1rem", fontSize: "0.8rem", color: "#94a3b8" }}>
            Это не даёт немедленного доступа к платформе — заявка проходит проверку администратором.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Стать рекламодателем</h1>
      <p style={{ color: "#64748b", fontSize: "0.9rem", marginBottom: "1.5rem" }}>
        Заполните форму, чтобы подать заявку на размещение рекламы. После проверки администратор свяжется с вами.
      </p>

      {serverError && <div style={S.error}>{serverError}</div>}

      <div style={S.form}>
        <div>
          <div style={S.label}>Компания *</div>
          <input style={S.input} value={form.company_name} onChange={(e) => update("company_name", e.target.value)} placeholder="ООО Название" data-testid="advertiser-apply-company-name" />
          {errors.company_name && <div style={S.fieldError}>{errors.company_name}</div>}
        </div>
        <div>
          <div style={S.label}>Контактное лицо *</div>
          <input style={S.input} value={form.contact_name} onChange={(e) => update("contact_name", e.target.value)} placeholder="Иван Иванов" data-testid="advertiser-apply-contact-name" />
          {errors.contact_name && <div style={S.fieldError}>{errors.contact_name}</div>}
        </div>
        <div>
          <div style={S.label}>Email *</div>
          <input style={S.input} type="email" value={form.email} onChange={(e) => update("email", e.target.value)} placeholder="company@example.com" data-testid="advertiser-apply-email" />
          {errors.email && <div style={S.fieldError}>{errors.email}</div>}
        </div>
        <div>
          <div style={S.label}>Телефон</div>
          <input style={S.input} value={form.phone} onChange={(e) => update("phone", e.target.value)} placeholder="+7..." data-testid="advertiser-apply-phone" />
        </div>
        <div>
          <div style={S.label}>Сайт</div>
          <input style={S.input} value={form.website} onChange={(e) => update("website", e.target.value)} placeholder="https://..." data-testid="advertiser-apply-website" />
        </div>
        <div>
          <div style={S.label}>Комментарий</div>
          <textarea style={S.textarea} value={form.comment} onChange={(e) => update("comment", e.target.value)} placeholder="Дополнительная информация" data-testid="advertiser-apply-comment" />
        </div>
        <div style={S.checkbox}>
          <input type="checkbox" checked={form.consent} onChange={(e) => update("consent", e.target.checked)} id="consent" data-testid="advertiser-apply-consent" />
          <label htmlFor="consent">
            Я согласен на обработку персональных данных и принимаю условия *
          </label>
        </div>
        {errors.consent && <div style={S.fieldError}>{errors.consent}</div>}
        <button style={form.company_name && form.contact_name && form.email && form.consent ? S.btn : S.btnDisabled} onClick={handleSubmit} disabled={!form.company_name || !form.contact_name || !form.email || !form.consent} data-testid="advertiser-apply-submit">
          Отправить заявку
        </button>
      </div>
    </div>
  );
}
