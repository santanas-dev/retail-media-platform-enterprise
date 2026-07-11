import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type {
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  CampaignCreateRequest,
} from "../api/types";

const styles = {
  page: { maxWidth: 700 },
  h2: { fontSize: "1.25rem", fontWeight: 600, margin: "0 0 1rem" },
  field: { marginBottom: "0.75rem" },
  label: { display: "block", fontSize: "0.85rem", fontWeight: 500, color: "#475569", marginBottom: "0.25rem" },
  input: {
    width: "100%",
    padding: "0.5rem",
    border: "1px solid #cbd5e1",
    borderRadius: 6,
    fontSize: "0.9rem",
    boxSizing: "border-box" as const,
  },
  select: {
    width: "100%",
    padding: "0.5rem",
    border: "1px solid #cbd5e1",
    borderRadius: 6,
    fontSize: "0.9rem",
    background: "#fff",
    boxSizing: "border-box" as const,
  },
  row: { display: "flex", gap: "0.75rem" },
  rowItem: { flex: 1 },
  btn: {
    padding: "0.5rem 1.5rem",
    background: "#1e293b",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    fontSize: "0.9rem",
    cursor: "pointer",
    marginTop: "0.5rem",
  },
  cancelBtn: {
    ...{} as Record<string, unknown>,
    padding: "0.5rem 1.5rem",
    background: "transparent",
    color: "#475569",
    border: "1px solid #cbd5e1",
    borderRadius: 6,
    fontSize: "0.9rem",
    cursor: "pointer",
    marginTop: "0.5rem",
    marginLeft: "0.5rem",
  } as React.CSSProperties,
  error: { color: "#dc2626", fontSize: "0.85rem", marginTop: "0.25rem" },
  fieldError: { color: "#dc2626", fontSize: "0.8rem", marginTop: "0.15rem" },
  loading: { color: "#64748b", padding: "1rem 0" },
};

export default function CampaignCreatePage() {
  const navigate = useNavigate();

  const [orgs, setOrgs] = useState<AdvertiserOrganizationOut[]>([]);
  const [brands, setBrands] = useState<AdvertiserBrandOut[]>([]);
  const [contracts, setContracts] = useState<AdvertiserContractOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  // Form state
  const [orgId, setOrgId] = useState("");
  const [brandId, setBrandId] = useState("");
  const [contractId, setContractId] = useState("");
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [description, setDescription] = useState("");
  const [timezone, setTimezone] = useState("Europe/Moscow");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [budgetCurrency, setBudgetCurrency] = useState("RUB");
  const [priority, setPriority] = useState("0");

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

  // Auto-generate code from name (slug-style)
  function nameToCode(n: string): string {
    return n
      .trim()
      .replace(/[^a-zA-Zа-яА-ЯёЁ0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .toUpperCase()
      .slice(0, 64);
  }

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [orgList, brandList, contractList] = await Promise.all([
          api.get<AdvertiserOrganizationOut[]>("/advertiser-organizations"),
          api.get<AdvertiserBrandOut[]>("/advertiser-brands"),
          api.get<AdvertiserContractOut[]>("/advertiser-contracts"),
        ]);
        if (cancelled) return;
        setOrgs(orgList as AdvertiserOrganizationOut[]);
        setBrands(brandList as AdvertiserBrandOut[]);
        setContracts(contractList as AdvertiserContractOut[]);
        // Auto-select first org
        if ((orgList as AdvertiserOrganizationOut[]).length > 0) {
          setOrgId((orgList as AdvertiserOrganizationOut[])[0].id);
        }
      } catch (e: unknown) {
        if (!cancelled) {
          if (e instanceof ApiError && e.status === 403) {
            setLoadError("Нет прав на создание кампаний");
          } else {
            setLoadError("Не удалось загрузить данные");
          }
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  function validate(): boolean {
    const fe: Record<string, string> = {};
    if (!name.trim()) fe.name = "Название обязательно";
    if (!code.trim()) fe.code = "Код обязателен";
    if (!contractId) fe.contractId = "Договор обязателен";
    if (!orgId) fe.orgId = "Организация обязательна";
    if (startAt && endAt && startAt >= endAt) fe.period = "Дата начала должна быть раньше даты окончания";
    setFieldErrors(fe);
    return Object.keys(fe).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    setSaving(true);
    setError("");

    const payload: CampaignCreateRequest = {
      advertiser_organization_id: orgId,
      advertiser_brand_id: brandId || null,
      advertiser_contract_id: contractId,
      code: code.trim(),
      name: name.trim(),
      description: description.trim() || null,
      start_at: startAt || null,
      end_at: endAt || null,
      timezone,
      budget_limit_amount: budgetAmount ? parseFloat(budgetAmount) : null,
      budget_limit_currency: budgetCurrency,
      priority: parseInt(priority, 10) || 0,
    };

    try {
      const created = await api.post<{ id: string }>("/campaigns", payload);
      navigate(`/campaigns/${created.id}`);
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 403) setError("Нет прав на создание кампаний");
        else if (e.status === 422) setError(e.message || "Ошибка валидации данных");
        else if (e.status === 409) setError(e.message || "Конфликт данных");
        else setError(e.message || "Ошибка при создании кампании");
      } else {
        setError("Неизвестная ошибка");
      }
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div style={styles.loading}>Загрузка...</div>;
  if (loadError) return <div style={{ color: "#dc2626" }}>{loadError}</div>;

  return (
    <div style={styles.page}>
      <h2 style={styles.h2}>Создание кампании</h2>
      <form onSubmit={handleSubmit}>
        {/* Organization (read-only, scoped) */}
        <div style={styles.field}>
          <label style={styles.label}>Организация</label>
          {orgs.length === 0 ? (
            <div style={{ color: "#94a3b8", fontSize: "0.85rem" }}>Нет доступных организаций</div>
          ) : (
            <select
              style={styles.select}
              value={orgId}
              onChange={(e) => setOrgId(e.target.value)}
              disabled={orgs.length <= 1}
            >
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>{o.display_name}</option>
              ))}
            </select>
          )}
          {fieldErrors.orgId && <div style={styles.fieldError}>{fieldErrors.orgId}</div>}
        </div>

        {/* Brand */}
        <div style={styles.field}>
          <label style={styles.label}>Бренд</label>
          <select style={styles.select} value={brandId} onChange={(e) => setBrandId(e.target.value)}>
            <option value="">— Не выбран —</option>
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
            ))}
          </select>
        </div>

        {/* Contract */}
        <div style={styles.field}>
          <label htmlFor="field-contract" style={styles.label}>Договор *</label>
          <select
            id="field-contract"
            style={{ ...styles.select, borderColor: fieldErrors.contractId ? "#dc2626" : "#cbd5e1" }}
            value={contractId}
            onChange={(e) => setContractId(e.target.value)}
          >
            <option value="">— Выберите договор —</option>
            {contracts.map((c) => (
              <option key={c.id} value={c.id}>
                {c.code} — {c.name || "Без названия"}
                {c.budget_limit_amount != null ? ` (${c.budget_limit_amount.toLocaleString()} ${c.budget_limit_currency})` : ""}
              </option>
            ))}
          </select>
          {fieldErrors.contractId && <div style={styles.fieldError}>{fieldErrors.contractId}</div>}
        </div>

        {/* Name + Code row */}
        <div style={styles.row}>
          <div style={{ ...styles.field, ...styles.rowItem }}>
            <label style={styles.label}>Название *</label>
            <input
              style={{ ...styles.input, borderColor: fieldErrors.name ? "#dc2626" : "#cbd5e1" }}
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setCode(nameToCode(e.target.value));
              }}
              placeholder="Название кампании"
              maxLength={255}
            />
            {fieldErrors.name && <div style={styles.fieldError}>{fieldErrors.name}</div>}
          </div>
          <div style={{ ...styles.field, ...styles.rowItem }}>
            <label style={styles.label}>Код *</label>
            <input
              style={{ ...styles.input, borderColor: fieldErrors.code ? "#dc2626" : "#cbd5e1" }}
              value={code}
              onChange={(e) => setCode(e.target.value.toUpperCase())}
              placeholder="Автоматически"
              maxLength={64}
            />
            {fieldErrors.code && <div style={styles.fieldError}>{fieldErrors.code}</div>}
          </div>
        </div>

        {/* Description */}
        <div style={styles.field}>
          <label style={styles.label}>Описание</label>
          <textarea
            style={{ ...styles.input, minHeight: 60, resize: "vertical" } as React.CSSProperties}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Опционально"
            rows={2}
          />
        </div>

        {/* Period + Timezone */}
        <div style={styles.row}>
          <div style={{ ...styles.field, ...styles.rowItem }}>
            <label style={styles.label}>Начало</label>
            <input
              style={styles.input}
              type="datetime-local"
              value={startAt}
              onChange={(e) => setStartAt(e.target.value)}
            />
          </div>
          <div style={{ ...styles.field, ...styles.rowItem }}>
            <label style={styles.label}>Окончание</label>
            <input
              style={styles.input}
              type="datetime-local"
              value={endAt}
              onChange={(e) => setEndAt(e.target.value)}
            />
          </div>
        </div>
        {fieldErrors.period && <div style={styles.fieldError}>{fieldErrors.period}</div>}
        <div style={styles.field}>
          <label style={styles.label}>Часовой пояс</label>
          <input style={styles.input} value={timezone} onChange={(e) => setTimezone(e.target.value)} />
        </div>

        {/* Budget + Priority */}
        <div style={styles.row}>
          <div style={{ ...styles.field, ...styles.rowItem }}>
            <label style={styles.label}>Бюджет</label>
            <input
              style={styles.input}
              type="number"
              min="0"
              step="0.01"
              value={budgetAmount}
              onChange={(e) => setBudgetAmount(e.target.value)}
              placeholder="Сумма"
            />
          </div>
          <div style={{ ...styles.field, width: 100 }}>
            <label style={styles.label}>Валюта</label>
            <select style={styles.select} value={budgetCurrency} onChange={(e) => setBudgetCurrency(e.target.value)}>
              <option value="RUB">RUB</option>
              <option value="USD">USD</option>
              <option value="EUR">EUR</option>
            </select>
          </div>
          <div style={{ ...styles.field, width: 100 }}>
            <label style={styles.label}>Приоритет</label>
            <input
              style={styles.input}
              type="number"
              min="0"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            />
          </div>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        <button type="submit" style={styles.btn} disabled={saving}>
          {saving ? "Создание..." : "Создать кампанию"}
        </button>
        <button type="button" style={styles.cancelBtn} onClick={() => navigate("/campaigns")}>
          Отмена
        </button>
      </form>
    </div>
  );
}
