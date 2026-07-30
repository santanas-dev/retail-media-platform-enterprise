/**
 * ADVERTISER-UX-001C2 — Advertiser Create Wizard.
 *
 * Multi-step guided onboarding reusing existing A/B/C backend endpoints.
 * Steps: Main → Legal → Contact → Confirm.
 */
import { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import {
  createAdvertiserOrganization,
  updateAdvertiserLegalRequisites,
  createAdvertiserContact,
} from "../api/campaigns";
import { ApiError } from "../api/client";
import type { AdvertiserOrganizationOut, AdvertiserLegalRequisitesUpdate } from "../api/types";

// ── Types ──

const STEPS = [
  { id: "main", label: "Основное", testid: "advertiser-wizard-step-main" },
  { id: "legal", label: "Реквизиты", testid: "advertiser-wizard-step-legal" },
  { id: "contact", label: "Контакты", testid: "advertiser-wizard-step-contact-contract" },
  { id: "confirm", label: "Подтверждение", testid: "advertiser-wizard-step-confirm" },
] as const;
type StepId = (typeof STEPS)[number]["id"];

interface MainForm {
  legal_name: string;
  display_name: string;
}

interface LegalForm {
  legal_entity_type: string;
  legal_form: string;
  legal_form_other: string;
  legal_name: string;
  inn: string;
  kpp: string;
  ogrn: string;
  ogrnip: string;
  legal_address: string;
  settlement_account: string;
  correspondent_account: string;
  bik: string;
  bank_name: string;
}

interface ContactForm {
  full_name: string;
  email: string;
  phone: string;
  title: string;
}

// ── Defaults ──

const EMPTY_MAIN: MainForm = { legal_name: "", display_name: "" };
const EMPTY_LEGAL: LegalForm = {
  legal_entity_type: "legal_entity",
  legal_form: "ooo",
  legal_form_other: "",
  legal_name: "",
  inn: "",
  kpp: "",
  ogrn: "",
  ogrnip: "",
  legal_address: "",
  settlement_account: "",
  correspondent_account: "",
  bik: "",
  bank_name: "",
};
const LEGAL_MIN_ADDRESS = "—";  // API requires non-empty legal_address
const EMPTY_CONTACT: ContactForm = { full_name: "", email: "", phone: "", title: "" };

// ── Inline styles ──

const S = {
  overlay: {
    position: "fixed", top: 0, left: 0, right: 0, bottom: 0,
    background: "rgba(0,0,0,0.4)", display: "flex",
    alignItems: "center", justifyContent: "center", zIndex: 1000,
  } as React.CSSProperties,
  panel: {
    background: "#fff", borderRadius: 8, padding: "1.5rem",
    minWidth: 520, maxWidth: 600, maxHeight: "90vh", overflow: "auto",
  } as React.CSSProperties,
  stepper: {
    display: "flex", gap: 4, marginBottom: "1.25rem",
  } as React.CSSProperties,
  stepDot: (active: boolean, done: boolean): React.CSSProperties => ({
    flex: 1, height: 4, borderRadius: 2,
    background: active ? "#2563eb" : done ? "#16a34a" : "#e2e8f0",
    transition: "background 0.2s",
  }),
  stepLabel: {
    display: "flex", justifyContent: "space-between",
    fontSize: "0.75rem", color: "#64748b", marginBottom: "0.25rem",
  } as React.CSSProperties,
  input: {
    width: "100%", padding: "0.4rem 0.5rem", border: "1px solid #e2e8f0",
    borderRadius: 4, fontSize: "0.875rem", marginBottom: "0.5rem",
    boxSizing: "border-box" as const,
  },
  select: {
    width: "100%", padding: "0.4rem 0.5rem", border: "1px solid #e2e8f0",
    borderRadius: 4, fontSize: "0.875rem", marginBottom: "0.5rem",
    background: "#fff",
  },
  label: {
    fontSize: "0.75rem", color: "#64748b", marginBottom: "0.15rem",
  } as React.CSSProperties,
  btnRow: {
    display: "flex", gap: "0.5rem", justifyContent: "space-between",
    marginTop: "1rem",
  } as React.CSSProperties,
  btnPrimary: {
    padding: "0.5rem 1rem", cursor: "pointer", background: "#2563eb",
    color: "#fff", border: "none", borderRadius: 4, fontWeight: 500,
  } as React.CSSProperties,
  btnSecondary: {
    padding: "0.5rem 1rem", cursor: "pointer", background: "#f1f5f9",
    color: "#475569", border: "1px solid #e2e8f0", borderRadius: 4,
  } as React.CSSProperties,
  error: {
    color: "#dc2626", fontSize: "0.8125rem", marginBottom: "0.5rem",
  } as React.CSSProperties,
  success: {
    color: "#16a34a", fontSize: "0.8125rem", marginBottom: "0.5rem",
  } as React.CSSProperties,
  summaryRow: {
    display: "flex", justifyContent: "space-between",
    padding: "0.3rem 0", borderBottom: "1px solid #f1f5f9",
    fontSize: "0.875rem",
  } as React.CSSProperties,
  note: {
    padding: "0.5rem", background: "#f0f9ff", borderRadius: 4,
    fontSize: "0.8125rem", color: "#0369a1", marginBottom: "0.5rem",
  } as React.CSSProperties,
};

// ── Component ──

interface AdvertiserWizardProps {
  onClose: () => void;
  onCreated: (orgId: string) => void;
}

export default function AdvertiserWizard({ onClose, onCreated }: AdvertiserWizardProps) {
  const { user } = useAuth();
  const canManage = user?.permissions?.includes("advertisers.manage") ?? false;

  const [stepIdx, setStepIdx] = useState(0);
  const [main, setMain] = useState<MainForm>(EMPTY_MAIN);
  const [legal, setLegal] = useState<LegalForm>(EMPTY_LEGAL);
  const [contact, setContact] = useState<ContactForm>(EMPTY_CONTACT);

  const [orgId, setOrgId] = useState<string | null>(null);
  const [orgCode, setOrgCode] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const step = STEPS[stepIdx];

  function goNext() { setError(""); setStepIdx((s) => Math.min(s + 1, STEPS.length - 1)); }
  function goBack() { setError(""); setStepIdx((s) => Math.max(s - 1, 0)); }

  // ── Step 1: Create org ──

  async function handleMainSubmit() {
    setError("");
    if (!main.legal_name.trim() || !main.display_name.trim()) {
      setError("Заполните все обязательные поля"); return;
    }
    setSaving(true);
    try {
      const org = await createAdvertiserOrganization({
        legal_name: main.legal_name.trim(),
        display_name: main.display_name.trim(),
      });
      setOrgId(org.id);
      setOrgCode(org.code);
      setSuccess("Организация создана");
      goNext();
    } catch (e: unknown) {
      setError(e instanceof ApiError ? e.message : "Ошибка создания организации");
    } finally {
      setSaving(false);
    }
  }

  // ── Step 2: Legal requisites ──

  const isLE = legal.legal_entity_type === "legal_entity";

  async function handleLegalSubmit() {
    setError("");
    if (!legal.inn.trim()) { setError("Укажите ИНН"); return; }
    if (!orgId) { setError("Организация не создана"); return; }
    setSaving(true);
    try {
      const body: AdvertiserLegalRequisitesUpdate = {
        legal_entity_type: legal.legal_entity_type,
        legal_form: legal.legal_form,
        legal_name: legal.legal_name || main.legal_name,
        inn: legal.inn,
        legal_address: legal.legal_address || LEGAL_MIN_ADDRESS,
        settlement_account: legal.settlement_account || "",
        correspondent_account: legal.correspondent_account || "",
        bik: legal.bik || "",
        bank_name: legal.bank_name || "",
      };
      if (legal.legal_form === "other" && legal.legal_form_other) {
        body.legal_form_other = legal.legal_form_other;
      }
      if (isLE) {
        body.kpp = legal.kpp || null;
        body.ogrn = legal.ogrn || null;
      } else {
        body.ogrnip = legal.ogrnip || null;
      }
      await updateAdvertiserLegalRequisites(orgId, body);
      setSuccess("Реквизиты сохранены");
      goNext();
    } catch (e: unknown) {
      setError(
        e instanceof ApiError
          ? typeof e.body === "object" && e.body !== null && "detail" in e.body
            ? String(JSON.stringify((e.body as Record<string, unknown>).detail))
            : e.message
          : "Ошибка сохранения реквизитов",
      );
    } finally {
      setSaving(false);
    }
  }

  // ── Step 3: Contact ──

  async function handleContactSubmit() {
    setError("");
    if (!contact.full_name.trim()) { setError("Укажите имя контакта"); return; }
    if (!contact.email.trim()) { setError("Укажите email"); return; }
    if (!orgId) { setError("Организация не создана"); return; }
    setSaving(true);
    try {
      await createAdvertiserContact({
        advertiser_organization_id: orgId,
        full_name: contact.full_name.trim(),
        email: contact.email.trim(),
        phone: contact.phone.trim() || null,
        title: contact.title.trim() || null,
      });
      setSuccess("Контакт создан");
      goNext();
    } catch (e: unknown) {
      setError(e instanceof ApiError ? e.message : "Ошибка создания контакта");
    } finally {
      setSaving(false);
    }
  }

  // ── Step 4: Confirm / Finish ──

  function handleFinish() {
    if (orgId) {
      onCreated(orgId);
    }
  }

  // ── Render helpers ──

  function renderStepDots() {
    return (
      <div style={S.stepper}>
        {STEPS.map((s, i) => (
          <div
            key={s.id}
            style={S.stepDot(i === stepIdx, i < stepIdx)}
            data-testid={i === stepIdx ? `${s.testid}-active` : s.testid}
          />
        ))}
      </div>
    );
  }

  function renderStepLabel() {
    return (
      <div style={S.stepLabel}>
        <span>{STEPS[stepIdx].label}</span>
        <span>{stepIdx + 1} / {STEPS.length}</span>
      </div>
    );
  }

  // ── Main step ──

  function renderMainStep() {
    return (
      <div data-testid="advertiser-wizard-step-main">
        <div style={S.note} data-testid="advertiser-wizard-code-note">
          Код организации будет создан автоматически
        </div>
        <div style={S.label}>Юридическое название *</div>
        <input style={S.input} placeholder="ООО «Ромашка»" value={main.legal_name}
          onChange={(e) => setMain((f) => ({ ...f, legal_name: e.target.value }))}
          data-testid="advertiser-wizard-name" />
        <div style={S.label}>Отображаемое название *</div>
        <input style={S.input} placeholder="Ромашка" value={main.display_name}
          onChange={(e) => setMain((f) => ({ ...f, display_name: e.target.value }))}
          data-testid="advertiser-wizard-display-name" />
      </div>
    );
  }

  // ── Legal step ──

  function renderLegalStep() {
    return (
      <div data-testid="advertiser-wizard-step-legal">
        <div style={S.label}>Тип</div>
        <select style={S.select} value={legal.legal_entity_type}
          onChange={(e) => setLegal((f) => ({ ...f, legal_entity_type: e.target.value, kpp: "", ogrn: "", ogrnip: "" }))}
          data-testid="advertiser-wizard-legal-type">
          <option value="legal_entity">Юридическое лицо</option>
          <option value="individual">ИП / Физическое лицо</option>
        </select>

        <div style={S.label}>Форма</div>
        <select style={S.select} value={legal.legal_form}
          onChange={(e) => setLegal((f) => ({ ...f, legal_form: e.target.value }))}
          data-testid="advertiser-wizard-legal-form">
          <option value="ooo">ООО</option>
          <option value="ao">АО</option>
          <option value="other">Другая</option>
        </select>

        {legal.legal_form === "other" && (
          <>
            <div style={S.label}>Уточнение формы</div>
            <input style={S.input} value={legal.legal_form_other}
              onChange={(e) => setLegal((f) => ({ ...f, legal_form_other: e.target.value }))} />
          </>
        )}

        <div style={S.label}>ИНН *</div>
        <input style={S.input} placeholder="7700000000" value={legal.inn}
          onChange={(e) => setLegal((f) => ({ ...f, inn: e.target.value }))}
          data-testid="advertiser-wizard-legal-inn" />

        {isLE && (
          <>
            <div style={S.label}>КПП</div>
            <input style={S.input} placeholder="770101001" value={legal.kpp}
              onChange={(e) => setLegal((f) => ({ ...f, kpp: e.target.value }))}
              data-testid="advertiser-wizard-legal-kpp" />
            <div style={S.label}>ОГРН</div>
            <input style={S.input} placeholder="1027700000000" value={legal.ogrn}
              onChange={(e) => setLegal((f) => ({ ...f, ogrn: e.target.value }))}
              data-testid="advertiser-wizard-legal-ogrn" />
          </>
        )}

        {!isLE && (
          <>
            <div style={S.label}>ОГРНИП</div>
            <input style={S.input} placeholder="300000000000000" value={legal.ogrnip}
              onChange={(e) => setLegal((f) => ({ ...f, ogrnip: e.target.value }))}
              data-testid="advertiser-wizard-legal-ogrnip" />
          </>
        )}

        <div style={S.label}>Банк</div>
        <input style={S.input} placeholder="ПАО Сбербанк" value={legal.bank_name}
          onChange={(e) => setLegal((f) => ({ ...f, bank_name: e.target.value }))}
          data-testid="advertiser-wizard-legal-bank" />

        <div style={S.label}>БИК</div>
        <input style={S.input} placeholder="044525225" value={legal.bik}
          onChange={(e) => setLegal((f) => ({ ...f, bik: e.target.value }))}
          data-testid="advertiser-wizard-legal-bik" />

        <div style={S.label}>Расчётный счёт</div>
        <input style={S.input} placeholder="40702810000000000000" value={legal.settlement_account}
          onChange={(e) => setLegal((f) => ({ ...f, settlement_account: e.target.value }))}
          data-testid="advertiser-wizard-legal-settlement" />

        <div style={S.label}>Корр. счёт</div>
        <input style={S.input} placeholder="30101810000000000225" value={legal.correspondent_account}
          onChange={(e) => setLegal((f) => ({ ...f, correspondent_account: e.target.value }))} />

        <div style={S.label}>Юридический адрес</div>
        <input style={S.input} placeholder="г. Москва, ул. Примерная, д. 1" value={legal.legal_address}
          onChange={(e) => setLegal((f) => ({ ...f, legal_address: e.target.value }))} />
      </div>
    );
  }

  // ── Contact step ──

  function renderContactStep() {
    return (
      <div data-testid="advertiser-wizard-step-contact-contract">
        <div style={S.note}>
          Добавьте контактное лицо. Договор можно будет добавить позже в карточке рекламодателя.
        </div>

        <div style={S.label}>ФИО *</div>
        <input style={S.input} placeholder="Иванов Иван Иванович" value={contact.full_name}
          onChange={(e) => setContact((f) => ({ ...f, full_name: e.target.value }))}
          data-testid="advertiser-wizard-contact-name" />

        <div style={S.label}>Email *</div>
        <input style={S.input} placeholder="contact@example.com" value={contact.email}
          onChange={(e) => setContact((f) => ({ ...f, email: e.target.value }))}
          data-testid="advertiser-wizard-contact-email" />

        <div style={S.label}>Телефон</div>
        <input style={S.input} placeholder="+7-999-000-00-00" value={contact.phone}
          onChange={(e) => setContact((f) => ({ ...f, phone: e.target.value }))}
          data-testid="advertiser-wizard-contact-phone" />

        <div style={S.label}>Должность</div>
        <input style={S.input} placeholder="Менеджер" value={contact.title}
          onChange={(e) => setContact((f) => ({ ...f, title: e.target.value }))}
          data-testid="advertiser-wizard-contact-title" />
      </div>
    );
  }

  // ── Confirm step ──

  function renderConfirmStep() {
    return (
      <div data-testid="advertiser-wizard-step-confirm">
        <h3 style={{ margin: "0 0 0.75rem", fontSize: "1rem" }}>Проверьте данные</h3>

        <div style={S.summaryRow}>
          <span style={{ color: "#64748b" }}>Код</span>
          <strong data-testid="advertiser-wizard-summary-code">{orgCode || "—"}</strong>
        </div>
        <div style={S.summaryRow}>
          <span style={{ color: "#64748b" }}>Организация</span>
          <span>{main.display_name}</span>
        </div>
        <div style={S.summaryRow}>
          <span style={{ color: "#64748b" }}>ИНН</span>
          <span data-testid="advertiser-wizard-summary-inn">{legal.inn || "—"}</span>
        </div>
        <div style={S.summaryRow}>
          <span style={{ color: "#64748b" }}>Банк</span>
          <span>{legal.bank_name || "—"}</span>
        </div>
        <div style={S.summaryRow}>
          <span style={{ color: "#64748b" }}>Контакт</span>
          <span data-testid="advertiser-wizard-summary-contact">
            {contact.full_name}{contact.email ? ` (${contact.email})` : ""}
          </span>
        </div>
        <div style={{ ...S.summaryRow, marginBottom: "0.5rem" }}>
          <span style={{ color: "#64748b" }}>Договор</span>
          <span style={{ color: "#64748b", fontStyle: "italic" }}>
            Будет добавлен в карточке
          </span>
        </div>

        {success && <div style={S.success} data-testid="advertiser-wizard-success">{success}</div>}
      </div>
    );
  }

  // ── Main render ──

  if (!canManage) return null;

  return (
    <div style={S.overlay} onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      data-testid="advertiser-wizard">
      <div style={S.panel} onClick={(e) => e.stopPropagation()}>
        {renderStepDots()}
        {renderStepLabel()}

        {error && <div style={S.error} data-testid="advertiser-wizard-error">{error}</div>}

        {step.id === "main" && renderMainStep()}
        {step.id === "legal" && renderLegalStep()}
        {step.id === "contact" && renderContactStep()}
        {step.id === "confirm" && renderConfirmStep()}

        <div style={S.btnRow}>
          <div>
            {stepIdx > 0 && (
              <button style={S.btnSecondary} onClick={goBack} data-testid="advertiser-wizard-back">
                Назад
              </button>
            )}
          </div>
          <div style={{ display: "flex", gap: "0.5rem" }}>
            {step.id === "confirm" ? (
              <button style={S.btnPrimary} onClick={handleFinish} data-testid="advertiser-wizard-submit"
                disabled={saving}>
                Открыть карточку рекламодателя
              </button>
            ) : (
              <button style={S.btnPrimary}
                onClick={
                  step.id === "main" ? handleMainSubmit :
                  step.id === "legal" ? handleLegalSubmit :
                  handleContactSubmit
                }
                data-testid="advertiser-wizard-next"
                disabled={saving}>
                {saving ? "Сохранение..." : "Далее"}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
