import { useEffect, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  listAdvertisers,
  listBrands,
  listContracts,
  createCampaign,
  listDisplaySurfaces,
  checkAvailability,
  suggestAlternatives,
} from "../api/campaigns";
import type {
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  CampaignCreateRequest,
  DisplaySurfaceRefOut,
  InventoryAvailabilityResponse,
  InventoryAlternativesResponse,
} from "../api/types";
import { ApiError } from "../api/client";

const TIMEZONES = [
  "Europe/Moscow",
  "Europe/Kaliningrad",
  "Europe/Samara",
  "Asia/Yekaterinburg",
  "Asia/Omsk",
  "Asia/Krasnoyarsk",
  "Asia/Irkutsk",
  "Asia/Yakutsk",
  "Asia/Vladivostok",
  "Asia/Magadan",
  "Asia/Kamchatka",
];

export default function CampaignCreatePage() {
  const navigate = useNavigate();

  // Reference data
  const [orgs, setOrgs] = useState<AdvertiserOrganizationOut[]>([]);
  const [brands, setBrands] = useState<AdvertiserBrandOut[]>([]);
  const [contracts, setContracts] = useState<AdvertiserContractOut[]>([]);
  const [refLoading, setRefLoading] = useState(true);
  const [refError, setRefError] = useState<string | null>(null);

  // Form fields
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [orgId, setOrgId] = useState("");
  const [brandId, setBrandId] = useState("");
  const [contractId, setContractId] = useState("");
  const [description, setDescription] = useState("");
  const [startAt, setStartAt] = useState("");
  const [endAt, setEndAt] = useState("");
  const [timezone, setTimezone] = useState("Europe/Moscow");
  const [budgetAmount, setBudgetAmount] = useState("");
  const [budgetCurrency] = useState("RUB");
  const [priority, setPriority] = useState("0");
  const [placementBasis, setPlacementBasis] = useState("commercial");

  // Submit state
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // ── Availability forecast state ──
  const [surfaces, setSurfaces] = useState<DisplaySurfaceRefOut[]>([]);
  const [surfacesLoaded, setSurfacesLoaded] = useState(false);
  const [forecastSurface, setForecastSurface] = useState("");
  const [forecastResult, setForecastResult] = useState<InventoryAvailabilityResponse | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState<string | null>(null);
  const [alternatives, setAlternatives] = useState<InventoryAlternativesResponse | null>(null);
  const [altLoading, setAltLoading] = useState(false);

  // Load reference data
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [orgList, brandList, contractList] = await Promise.all([
          listAdvertisers(),
          listBrands(),
          listContracts(),
        ]);

        if (cancelled) return;

        setOrgs(orgList);
        setBrands(brandList);
        setContracts(contractList);
      } catch (e: unknown) {
        if (cancelled) return;
        setRefError(e instanceof Error ? e.message : "Ошибка загрузки справочников");
      } finally {
        if (!cancelled) setRefLoading(false);
      }
    }

    load();

    // Load surfaces for availability forecast
    (async () => {
      try {
        const sf = await listDisplaySurfaces();
        if (!cancelled) { setSurfaces(sf.filter(s => s.is_active)); setSurfacesLoaded(true); }
      } catch { if (!cancelled) setSurfacesLoaded(true); }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  // Filter brands/contracts by selected org
  const filteredBrands = orgId
    ? brands.filter((b) => b.advertiser_organization_id === orgId)
    : [];
  const filteredContracts = orgId
    ? contracts.filter((c) => c.advertiser_organization_id === orgId)
    : [];

  // Clear brand/contract when org changes
  function handleOrgChange(value: string) {
    setOrgId(value);
    setBrandId("");
    setContractId("");
  }

  // Auto-generate code from name
  function handleNameChange(value: string) {
    setName(value);
    if (!code || code === slugify(name)) {
      setCode(slugify(value));
    }
  }

  // Validate
  function validate(): string | null {
    if (!name.trim()) return "Название кампании обязательно";
    if (!code.trim()) return "Код кампании обязателен";
    if (!orgId) return "Выберите рекламодателя";
    if (!contractId) return "Выберите договор";
    return null;
  }

  // Availability forecast
  async function handleForecast() {
    if (!forecastSurface || !startAt || !endAt) return;
    setForecastLoading(true); setForecastError(null); setForecastResult(null);
    setAlternatives(null);
    try {
      const result = await checkAvailability({
        surface_id: forecastSurface,
        starts_at: new Date(startAt).toISOString(),
        ends_at: new Date(endAt).toISOString(),
      });
      setForecastResult(result);
      // If not available, fetch alternatives
      if (!result.all_available) {
        await handleAlternatives();
      }
    } catch (e: unknown) {
      setForecastError(e instanceof ApiError ? e.message : "Ошибка проверки");
    } finally { setForecastLoading(false); }
  }

  // Fetch alternatives for unavailable surface
  async function handleAlternatives() {
    if (!forecastSurface || !startAt || !endAt) return;
    setAltLoading(true);
    try {
      const result = await suggestAlternatives({
        surface_id: forecastSurface,
        starts_at: new Date(startAt).toISOString(),
        ends_at: new Date(endAt).toISOString(),
        max_results: 5,
      });
      setAlternatives(result);
    } catch {
      setAlternatives(null);
    } finally { setAltLoading(false); }
  }

  // Submit
  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);

    try {
      const body: CampaignCreateRequest = {
        advertiser_organization_id: orgId,
        advertiser_brand_id: brandId || null,
        advertiser_contract_id: contractId,
        code: code.trim(),
        name: name.trim(),
        description: description.trim() || null,
        start_at: startAt ? new Date(startAt).toISOString() : null,
        end_at: endAt ? new Date(endAt).toISOString() : null,
        timezone,
        budget_limit_amount: budgetAmount ? parseFloat(budgetAmount) : null,
        budget_limit_currency: budgetCurrency,
        priority: parseInt(priority, 10) || 0,
        placement_basis: placementBasis,
      };

      const created = await createCampaign(body);
      navigate(`/campaigns/${created.id}`, { replace: true });
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        if (e.status === 422) {
          setError(`Ошибка данных: ${e.message}`);
        } else if (e.status === 403) {
          setError("Нет прав на создание кампании. Обратитесь к администратору.");
        } else if (e.status === 409) {
          setError("Кампания с таким кодом уже существует или конфликт данных.");
        } else {
          setError(`Ошибка сервера (${e.status}): ${e.message}`);
        }
      } else {
        setError(e instanceof Error ? e.message : "Неизвестная ошибка");
      }
    } finally {
      setSubmitting(false);
    }
  }

  // ── Render states ──

  if (refLoading) {
    return (
      <div style={css.centered}>
        <p style={css.muted}>Загрузка справочников...</p>
      </div>
    );
  }

  if (refError) {
    return (
      <div style={css.centered}>
        <div style={css.errorBox}>
          <p style={{ margin: 0, fontWeight: 600 }}>Ошибка</p>
          <p style={{ margin: "0.25rem 0 0.5rem", fontSize: "0.875rem" }}>{refError}</p>
          <button type="button" style={css.linkBtn} onClick={() => navigate("/campaigns")}>
            ← К списку кампаний
          </button>
        </div>
      </div>
    );
  }

  if (orgs.length === 0) {
    return (
      <div>
        <h2 style={css.heading}>Новая кампания</h2>
        <div style={css.emptyBox}>
          <p style={{ margin: 0, fontWeight: 500 }}>Нет доступных рекламодателей</p>
          <p style={{ margin: "0.25rem 0 0", fontSize: "0.875rem", color: "#94a3b8" }}>
            Для создания кампании необходим хотя бы один активный рекламодатель.
          </p>
        </div>
      </div>
    );
  }

  // ── Render form ──

  return (
    <div>
      <div style={{ marginBottom: "1rem" }}>
        <button
          type="button"
          style={css.linkBtn}
          onClick={() => navigate("/campaigns")}
        >
          ← К списку кампаний
        </button>
      </div>

      <h2 style={css.heading}>Новая кампания</h2>

      {error && (
        <div role="alert" style={css.errorBox}>
          <p style={{ margin: 0 }}>{error}</p>
        </div>
      )}

      <form onSubmit={handleSubmit} style={css.form}>
        {/* ── Basic info ── */}
        <fieldset style={css.fieldset}>
          <legend style={css.legend}>Основное</legend>

          <div style={css.fieldRow}>
            <label htmlFor="c-name" style={css.label}>
              Название <span style={{ color: "#dc2626" }}>*</span>
            </label>
            <input
              id="c-name"
              type="text"
              value={name}
              onChange={(e) => handleNameChange(e.target.value)}
              style={css.input}
              placeholder="Например: Весенняя акция 2026"
              maxLength={255}
            />
          </div>

          <div style={css.fieldRow}>
            <label htmlFor="c-code" style={css.label}>
              Код <span style={{ color: "#dc2626" }}>*</span>
            </label>
            <input
              id="c-code"
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              style={{ ...css.input, fontFamily: "monospace" }}
              placeholder="Автоматически из названия"
              maxLength={64}
            />
            <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "0.15rem" }}>
              Уникальный код кампании, до 64 символов
            </div>
          </div>

          <div style={css.fieldRow}>
            <label htmlFor="c-desc" style={css.label}>Описание</label>
            <textarea
              id="c-desc"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{ ...css.input, minHeight: 60, resize: "vertical" }}
              placeholder="Необязательно"
              rows={2}
            />
          </div>
        </fieldset>

        {/* ── Advertiser ── */}
        <fieldset style={css.fieldset}>
          <legend style={css.legend}>Рекламодатель</legend>

          <div style={css.fieldRow}>
            <label htmlFor="c-org" style={css.label}>
              Организация <span style={{ color: "#dc2626" }}>*</span>
            </label>
            <select
              id="c-org"
              value={orgId}
              onChange={(e) => handleOrgChange(e.target.value)}
              style={css.select}
            >
              <option value="">— Выберите организацию —</option>
              {orgs.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.display_name || o.legal_name} ({o.code})
                </option>
              ))}
            </select>
          </div>

          {orgId && (
            <>
              <div style={css.fieldRow}>
                <label htmlFor="c-brand" style={css.label}>Бренд</label>
                <select
                  id="c-brand"
                  value={brandId}
                  onChange={(e) => setBrandId(e.target.value)}
                  style={css.select}
                >
                  <option value="">— Без бренда —</option>
                  {filteredBrands.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name} ({b.code})
                    </option>
                  ))}
                </select>
                {filteredBrands.length === 0 && (
                  <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "0.15rem" }}>
                    У этой организации нет брендов
                  </div>
                )}
              </div>

              <div style={css.fieldRow}>
                <label htmlFor="c-contract" style={css.label}>
                  Договор <span style={{ color: "#dc2626" }}>*</span>
                </label>
                <select
                  id="c-contract"
                  value={contractId}
                  onChange={(e) => setContractId(e.target.value)}
                  style={css.select}
                >
                  <option value="">— Выберите договор —</option>
                  {filteredContracts.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.code}{c.name ? ` — ${c.name}` : ""}
                      {c.valid_until
                        ? ` (до ${new Date(c.valid_until).toLocaleDateString("ru-RU")})`
                        : ""}
                    </option>
                  ))}
                </select>
                {filteredContracts.length === 0 && (
                  <div style={{ fontSize: "0.7rem", color: "#dc2626", marginTop: "0.15rem" }}>
                    У организации нет договоров. Создайте договор перед созданием кампании.
                  </div>
                )}
              </div>
            </>
          )}
        </fieldset>

        {/* ── Placement basis ── (G1-FIX) */}
        <fieldset style={css.fieldset}>
          <legend style={css.legend}>Основание размещения</legend>
          <div style={css.fieldRow}>
            <select
              id="c-placement-basis"
              data-testid="campaign-create-placement-basis"
              value={placementBasis}
              onChange={(e) => setPlacementBasis(e.target.value)}
              style={css.select}
            >
              <option value="commercial">Коммерческое размещение</option>
              <option value="internal">Внутреннее размещение</option>
              <option value="compensation">Компенсация / make-good</option>
              <option value="test">Тестовое размещение</option>
            </select>
          </div>
        </fieldset>

        {/* ── Schedule ── */}
        <fieldset style={css.fieldset}>
          <legend style={css.legend}>Период и бюджет</legend>

          <div style={css.inlineFields}>
            <div style={css.fieldRow}>
              <label htmlFor="c-start" style={css.label}>Дата начала</label>
              <input
                id="c-start"
                type="date"
                value={startAt}
                onChange={(e) => setStartAt(e.target.value)}
                style={css.input}
              />
            </div>
            <div style={css.fieldRow}>
              <label htmlFor="c-end" style={css.label}>Дата окончания</label>
              <input
                id="c-end"
                type="date"
                value={endAt}
                onChange={(e) => setEndAt(e.target.value)}
                style={css.input}
              />
            </div>
          </div>

          <div style={css.inlineFields}>
            <div style={css.fieldRow}>
              <label htmlFor="c-tz" style={css.label}>Часовой пояс</label>
              <select
                id="c-tz"
                value={timezone}
                onChange={(e) => setTimezone(e.target.value)}
                style={css.select}
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz}</option>
                ))}
              </select>
            </div>
            <div style={css.fieldRow}>
              <label htmlFor="c-priority" style={css.label}>Приоритет</label>
              <input
                id="c-priority"
                type="number"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                min={0}
                max={99}
                style={{ ...css.input, width: 80 }}
              />
              <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "0.15rem" }}>
                0 — обычный, чем выше число — тем выше приоритет
              </div>
            </div>
          </div>

          <div style={css.fieldRow}>
            <label htmlFor="c-budget" style={css.label}>Бюджет (₽)</label>
            <input
              id="c-budget"
              type="number"
              value={budgetAmount}
              onChange={(e) => setBudgetAmount(e.target.value)}
              min={0}
              step={1000}
              style={{ ...css.input, width: 200 }}
              placeholder="Не ограничен"
            />
            <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "0.15rem" }}>
              Оставьте пустым, если бюджет не ограничен
            </div>
          </div>
        </fieldset>

        {/* ── Availability forecast ── */}
        {surfacesLoaded && surfaces.length > 0 && (
          <fieldset style={css.fieldset}>
            <legend style={css.legend}>Доступность инвентаря</legend>
            <p style={{ fontSize: "0.8rem", color: "#64748b", margin: "0 0 0.75rem" }}>
              Проверка показывает предварительную доступность. Финальное бронирование — при отправке на согласование.
            </p>
            <div style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end", flexWrap: "wrap" }}>
              <div>
                <label htmlFor="fc-surface" style={{ ...css.label, fontSize: "0.8rem" }}>Поверхность</label>
                <select id="fc-surface" value={forecastSurface} onChange={(e) => { setForecastSurface(e.target.value); setForecastResult(null); }}
                  style={{ ...css.select, width: 260 }}>
                  <option value="">— Выберите поверхность —</option>
                  {surfaces.map((s) => (
                    <option key={s.id} value={s.id}>{s.code} ({s.resolution_w}×{s.resolution_h})</option>
                  ))}
                </select>
              </div>
              <button type="button" onClick={handleForecast} disabled={!forecastSurface || !startAt || !endAt || forecastLoading}
                style={{ padding: "0.4rem 0.8rem", fontSize: "0.8rem", background: "var(--rmp-gray-800)", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", opacity: (!forecastSurface || !startAt || !endAt || forecastLoading) ? 0.5 : 1 }}>
                {forecastLoading ? "..." : "Проверить"}
              </button>
            </div>
            {/* Result */}
            {forecastResult && (
              <div style={{ marginTop: "0.75rem", padding: "0.5rem", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", fontSize: "0.8rem" }}>
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
                  <span>Слотов: <strong>{forecastResult.slots.length}</strong></span>
                  <span>Доступно: <strong style={{ color: forecastResult.all_available ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>{forecastResult.total_available}</strong></span>
                  <span>Конфликтов: <strong>{forecastResult.conflicts.length}</strong></span>
                  <span>Итог: <strong style={{ color: forecastResult.all_available ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>{forecastResult.all_available ? "Доступно" : "Недоступно"}</strong></span>
                </div>
              </div>
            )}
            {forecastError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: "0.5rem" }}>{forecastError}</div>}
            {/* S-087 — Alternatives */}
            {!forecastResult?.all_available && alternatives && (
              <div style={{ marginTop: "0.75rem", padding: "0.5rem", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", fontSize: "0.8rem" }}>
                <strong>Возможные альтернативы ({alternatives.total_found}):</strong>
                {altLoading ? (
                  <p style={{ color: "#64748b", margin: "0.25rem 0 0" }}>Загрузка...</p>
                ) : alternatives.alternatives.length === 0 ? (
                  <p style={{ color: "#64748b", margin: "0.25rem 0 0" }}>Альтернатив не найдено. Попробуйте изменить период или запрошенную ёмкость.</p>
                ) : (
                  <ul style={{ margin: "0.5rem 0 0", paddingLeft: "1.2rem", display: "flex", flexDirection: "column", gap: "0.35rem" }}>
                    {alternatives.alternatives.map((alt, i) => (
                      <li key={i}>
                        <strong>{alt.surface_code || alt.surface_id}</strong> — {alt.reason}{" "}
                        <span style={{ color: "var(--rmp-success-600)" }}>(доступно: {alt.available_capacity} ед.{alt.suggested_capacity_units ? `, предложено: ${alt.suggested_capacity_units} ед.` : ""})</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </fieldset>
        )}

        {/* ── Actions ── */}
        <div style={css.actions}>
          <button
            type="button"
            style={css.cancelBtn}
            onClick={() => navigate("/campaigns")}
            disabled={submitting}
          >
            Отмена
          </button>
          <button
            type="submit"
            style={{
              ...css.submitBtn,
              ...(submitting ? { background: "#9ca3af", cursor: "default" } : {}),
            }}
            disabled={submitting}
          >
            {submitting ? "Создание..." : "Создать черновик"}
          </button>
        </div>

        <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "0.5rem" }}>
          Кампания будет создана в статусе «Черновик». Флайты, плейсменты и креативы
          добавляются отдельно после создания.
        </div>
      </form>
    </div>
  );
}

// ── Helpers ──

function slugify(text: string): string {
  return text
    .trim()
    .toUpperCase()
    .replace(/[^A-ZА-ЯЁ0-9\s_-]/g, "")
    .replace(/\s+/g, "-")
    .replace(/_+/g, "-")
    .replace(/-+/g, "-")
    .slice(0, 64);
}

// ── Styles ──

const css: Record<string, React.CSSProperties> = {
  heading: {
    margin: "0 0 1rem",
    fontSize: "1.25rem",
    fontWeight: 600,
  },
  centered: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 200,
    flexDirection: "column",
  },
  muted: { color: "#64748b", fontSize: "0.875rem" },
  errorBox: {
    background: "#fef2f2",
    color: "#991b1b",
    padding: "0.75rem 1rem",
    borderRadius: 6,
    marginBottom: "1rem",
    fontSize: "0.875rem",
  },
  emptyBox: {
    background: "#f8fafc",
    border: "1px dashed #cbd5e1",
    borderRadius: 6,
    padding: "2rem",
    textAlign: "center",
    color: "#64748b",
  },
  linkBtn: {
    background: "none",
    border: "none",
    color: "#2563eb",
    cursor: "pointer",
    padding: 0,
    fontSize: "0.875rem",
    textDecoration: "underline",
  },
  form: {
    background: "#fff",
    borderRadius: 6,
    padding: "1.5rem",
    boxShadow: "0 1px 2px rgba(0,0,0,0.06)",
    maxWidth: 700,
  },
  fieldset: {
    border: "1px solid #e2e8f0",
    borderRadius: 4,
    padding: "1rem",
    marginBottom: "1rem",
  },
  legend: {
    fontSize: "0.8rem",
    fontWeight: 600,
    color: "#475569",
    padding: "0 0.5rem",
  },
  fieldRow: {
    marginBottom: "0.75rem",
  },
  label: {
    display: "block",
    fontSize: "0.8rem",
    fontWeight: 500,
    color: "#334155",
    marginBottom: "0.2rem",
  },
  input: {
    width: "100%",
    padding: "0.45rem 0.6rem",
    border: "1px solid #d1d5db",
    borderRadius: 4,
    fontSize: "0.875rem",
    boxSizing: "border-box" as const,
    fontFamily: "inherit",
  },
  select: {
    width: "100%",
    padding: "0.45rem 0.6rem",
    border: "1px solid #d1d5db",
    borderRadius: 4,
    fontSize: "0.875rem",
    background: "#fff",
    boxSizing: "border-box" as const,
  },
  inlineFields: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "1rem",
  },
  actions: {
    display: "flex",
    gap: "0.75rem",
    justifyContent: "flex-end",
    marginTop: "1rem",
  },
  cancelBtn: {
    padding: "0.45rem 1rem",
    background: "#fff",
    border: "1px solid #d1d5db",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: "0.875rem",
    color: "#475569",
  },
  submitBtn: {
    padding: "0.45rem 1.25rem",
    background: "#2563eb",
    color: "#fff",
    border: "none",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: "0.875rem",
    fontWeight: 500,
  },
};
