import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "../api/client";
import type {
  InventoryStoreOut,
  InventorySurfaceOut,
  InventorySurfacePatchRequest,
  PaginatedResponse,
  InventoryAvailabilityRequest,
  InventoryAvailabilityResponse,
  InventorySlotAvailability,
  InventoryConflictCheckRequest,
  InventoryConflictCheckResponse,
  InventoryConflictItem,
} from "../api/types";
import PageHeader from "../components/PageHeader";

function fmtRes(w: number, h: number): string { return `${w}×${h}`; }

const PAGE_SIZE = 50;

function Pagination({ total, offset, limit, hasPrev, hasNext, onPrev, onNext }: {
  total: number; offset: number; limit: number; hasPrev: boolean; hasNext: boolean;
  onPrev: () => void; onNext: () => void;
}) {
  if (total <= limit) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "var(--rmp-space-3)", fontSize: "var(--rmp-font-size-sm)" }}>
      <span style={{ color: "var(--rmp-text-secondary)" }}>{from}–{to} из {total}</span>
      <div style={{ display: "flex", gap: "var(--rmp-space-1)" }}>
        <button onClick={onPrev} disabled={!hasPrev} style={pgnBtn(hasPrev)}>← Назад</button>
        <button onClick={onNext} disabled={!hasNext} style={pgnBtn(hasNext)}>Вперёд →</button>
      </div>
    </div>
  );
}

function pgnBtn(enabled: boolean): React.CSSProperties {
  return { padding: "0.15rem 0.5rem", fontSize: "var(--rmp-font-size-xs)", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", background: enabled ? "var(--rmp-bg-surface)" : "var(--rmp-gray-100)", color: enabled ? "var(--rmp-text-primary)" : "var(--rmp-text-muted)", cursor: enabled ? "pointer" : "default" };
}

function fetchInventoryStores(limit: number, offset: number): Promise<PaginatedResponse<InventoryStoreOut>> {
  return api.get<PaginatedResponse<InventoryStoreOut>>(`/inventory/stores?limit=${limit}&offset=${offset}`);
}

function fetchInventorySurfaces(limit: number, offset: number): Promise<PaginatedResponse<InventorySurfaceOut>> {
  return api.get<PaginatedResponse<InventorySurfaceOut>>(`/inventory/surfaces?limit=${limit}&offset=${offset}`);
}

// ── Tab types ──

type Tab = "catalog" | "availability" | "conflicts" | "rules";

const TAB_LABELS: Record<Tab, string> = {
  catalog: "Каталог",
  availability: "Доступность",
  conflicts: "Конфликты",
  rules: "Правила",
};

// ── Tab button styles (S-073 token-based) ──

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: "var(--rmp-space-1) var(--rmp-space-3)",
  borderRadius: "var(--rmp-radius-sm)",
  border: "1px solid var(--rmp-border-strong)",
  background: active ? "var(--rmp-gray-800)" : "var(--rmp-bg-surface)",
  color: active ? "var(--rmp-text-inverse)" : "var(--rmp-text-primary)",
  cursor: "pointer",
  fontSize: "var(--rmp-font-size-sm)",
});

const TAB_ORDER: Tab[] = ["catalog", "availability", "conflicts", "rules"];

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<Tab>("catalog");

  return (
    <div>
      <PageHeader title="Инвентарь" />
      <div style={{ display: "flex", gap: "var(--rmp-space-2)", marginBottom: "var(--rmp-space-4)", flexWrap: "wrap" }}>
        {TAB_ORDER.map((t) => (
          <button key={t} onClick={() => setActiveTab(t)} style={tabBtn(activeTab === t)}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>
      {activeTab === "catalog" && <CatalogTab />}
      {activeTab === "availability" && <AvailabilityTab />}
      {activeTab === "conflicts" && <ConflictsTab />}
      {activeTab === "rules" && <RulesTab />}
    </div>
  );
}

// ═══════════════════════════════════════════════
// Catalog tab — existing stores + surfaces
// ═══════════════════════════════════════════════

function CatalogTab() {
  const [subTab, setSubTab] = useState<"stores" | "surfaces">("stores");
  return (
    <div>
      <div style={{ display: "flex", gap: "var(--rmp-space-2)", marginBottom: "var(--rmp-space-3)" }}>
        {(["stores", "surfaces"] as const).map((t) => (
          <button key={t} onClick={() => setSubTab(t)} style={tabBtn(subTab === t)}>
            {t === "stores" ? "Магазины" : "Поверхности"}
          </button>
        ))}
      </div>
      {subTab === "stores" ? <StoresTab /> : <SurfacesTab />}
    </div>
  );
}

function StoresTab() {
  const [stores, setStores] = useState<InventoryStoreOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = useCallback(async (pageOffset: number) => {
    setLoading(true); setError(null);
    try {
      const data = await fetchInventoryStores(PAGE_SIZE, pageOffset);
      setStores(data.items); setTotal(data.total); setOffset(pageOffset);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) setError("Нет доступа к инвентарю");
      else setError("Ошибка загрузки");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(0); }, [load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;
  const filtered = search ? stores.filter((s) => s.name.toLowerCase().includes(search.toLowerCase()) || s.code.toLowerCase().includes(search.toLowerCase())) : stores;

  return (
    <div>
      <input type="text" placeholder="Поиск по названию или коду..." value={search} onChange={(e) => setSearch(e.target.value)}
        style={{ padding: "var(--rmp-space-1) var(--rmp-space-2)", fontSize: "var(--rmp-font-size-sm)", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", marginBottom: "var(--rmp-space-2)", width: 280 }} />
      {loading && <p style={{ color: "var(--rmp-text-secondary)" }}>Загрузка...</p>}
      {error && !loading && <p style={{ color: "var(--rmp-danger-600)" }}>{error}</p>}
      {!loading && !error && filtered.length === 0 && <p style={{ color: "var(--rmp-text-secondary)" }}>{search ? "Ничего не найдено" : "Нет магазинов"}</p>}
      {!loading && filtered.length > 0 && (
        <>
          <table className="rmp-table">
            <thead>
              <tr>
                <th>Код</th><th>Название</th><th>Филиал</th><th>Кластер</th><th>Адрес</th><th>Поверхностей</th><th>Активен</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id}>
                  <td>{s.code}</td>
                  <td><strong>{s.name}</strong></td>
                  <td>{s.branch_name ?? "—"}</td>
                  <td>{s.cluster_name ?? "—"}</td>
                  <td>{s.address || "—"}</td>
                  <td>{s.surface_count}</td>
                  <td><span style={{ color: s.is_active ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>{s.is_active ? "Да" : "Нет"}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination total={total} offset={offset} limit={PAGE_SIZE} hasPrev={hasPrev} hasNext={hasNext} onPrev={() => load(offset - PAGE_SIZE)} onNext={() => load(offset + PAGE_SIZE)} />
        </>
      )}
    </div>
  );
}

function SurfacesTab() {
  const [surfaces, setSurfaces] = useState<InventorySurfaceOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [toggling, setToggling] = useState<string | null>(null);

  const load = useCallback(async (pageOffset: number) => {
    setLoading(true); setError(null);
    try {
      const data = await fetchInventorySurfaces(PAGE_SIZE, pageOffset);
      setSurfaces(data.items); setTotal(data.total); setOffset(pageOffset);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) setError("Нет доступа к инвентарю");
      else setError("Ошибка загрузки");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(0); }, [load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;
  const filtered = search ? surfaces.filter((s) => s.code.toLowerCase().includes(search.toLowerCase()) || (s.store_name ?? "").toLowerCase().includes(search.toLowerCase())) : surfaces;

  const handleToggle = async (surface: InventorySurfaceOut) => {
    setToggling(surface.id);
    try {
      const body: InventorySurfacePatchRequest = { is_active: !surface.is_active };
      await api.patch<InventorySurfaceOut>(`/inventory/surfaces/${surface.id}`, body);
      await load(offset);
    } catch { /* silently ignore */ }
    finally { setToggling(null); }
  };

  return (
    <div>
      <input type="text" placeholder="Поиск по коду или магазину..." value={search} onChange={(e) => setSearch(e.target.value)}
        style={{ padding: "var(--rmp-space-1) var(--rmp-space-2)", fontSize: "var(--rmp-font-size-sm)", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-sm)", marginBottom: "var(--rmp-space-2)", width: 280 }} />
      {loading && <p style={{ color: "var(--rmp-text-secondary)" }}>Загрузка...</p>}
      {error && !loading && <p style={{ color: "var(--rmp-danger-600)" }}>{error}</p>}
      {!loading && !error && filtered.length === 0 && <p style={{ color: "var(--rmp-text-secondary)" }}>{search ? "Ничего не найдено" : "Нет поверхностей"}</p>}
      {!loading && filtered.length > 0 && (
        <>
          <table className="rmp-table">
            <thead>
              <tr>
                <th>Код</th><th>Магазин</th><th>Разрешение</th><th>Активна</th><th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((ds) => (
                <tr key={ds.id}>
                  <td><strong>{ds.code}</strong></td>
                  <td>{ds.store_name ?? ds.store_code ?? ds.store_id}</td>
                  <td>{fmtRes(ds.resolution_w, ds.resolution_h)}</td>
                  <td><span style={{ color: ds.is_active ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>{ds.is_active ? "Да" : "Нет"}</span></td>
                  <td>
                    <button onClick={() => handleToggle(ds)} disabled={toggling === ds.id}
                      style={{
                        padding: "0.15rem 0.5rem", fontSize: "var(--rmp-font-size-xs)",
                        border: `1px solid ${ds.is_active ? "var(--rmp-danger-600)" : "var(--rmp-success-600)"}`,
                        borderRadius: "var(--rmp-radius-sm)", background: "var(--rmp-bg-surface)",
                        color: ds.is_active ? "var(--rmp-danger-600)" : "var(--rmp-success-600)",
                        cursor: toggling === ds.id ? "default" : "pointer", opacity: toggling === ds.id ? 0.5 : 1,
                      }}>
                      {toggling === ds.id ? "..." : ds.is_active ? "Деактивировать" : "Активировать"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination total={total} offset={offset} limit={PAGE_SIZE} hasPrev={hasPrev} hasNext={hasNext} onPrev={() => load(offset - PAGE_SIZE)} onNext={() => load(offset + PAGE_SIZE)} />
        </>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// Shared helpers for availability/conflicts tabs
// ═══════════════════════════════════════════════

const fieldStyle: React.CSSProperties = {
  padding: "var(--rmp-space-1) var(--rmp-space-2)",
  fontSize: "var(--rmp-font-size-sm)",
  border: "1px solid var(--rmp-border-strong)",
  borderRadius: "var(--rmp-radius-sm)",
};

const labelStyle: React.CSSProperties = {
  fontSize: "var(--rmp-font-size-sm)",
  fontWeight: 500,
  display: "block",
  marginBottom: "var(--rmp-space-1)",
};

const btnPrimary: React.CSSProperties = {
  padding: "var(--rmp-space-1) var(--rmp-space-4)",
  fontSize: "var(--rmp-font-size-sm)",
  background: "var(--rmp-gray-800)",
  color: "var(--rmp-text-inverse)",
  border: "none",
  borderRadius: "var(--rmp-radius-sm)",
  cursor: "pointer",
};

const summaryBox: React.CSSProperties = {
  padding: "var(--rmp-space-3)",
  borderRadius: "var(--rmp-radius-md)",
  border: "1px solid var(--rmp-border-strong)",
  marginBottom: "var(--rmp-space-4)",
};

function toLocalDatetimeStr(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

// ═══════════════════════════════════════════════
// Availability tab
// ═══════════════════════════════════════════════

function AvailabilityTab() {
  const [surfaces, setSurfaces] = useState<InventorySurfaceOut[]>([]);
  const [surfacesLoading, setSurfacesLoading] = useState(true);
  const [surfacesError, setSurfacesError] = useState<string | null>(null);

  // Form state
  const [surfaceId, setSurfaceId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [startHour, setStartHour] = useState("9");
  const [endDate, setEndDate] = useState("");
  const [endHour, setEndHour] = useState("18");
  const [reqUnits, setReqUnits] = useState("");
  const [reqSov, setReqSov] = useState("");

  // Result state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InventoryAvailabilityResponse | null>(null);

  // Load surfaces for the selector
  useEffect(() => {
    (async () => {
      try {
        const data = await fetchInventorySurfaces(200, 0);
        setSurfaces(data.items.filter((s) => s.is_active));
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) setSurfacesError("Нет доступа");
        else setSurfacesError("Ошибка загрузки поверхностей");
      } finally {
        setSurfacesLoading(false);
      }
    })();
  }, []);

  // Default date: today 09:00 → today 18:00
  useEffect(() => {
    const now = new Date();
    const start = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 9, 0);
    const end = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 18, 0);
    if (!startDate) setStartDate(start.toISOString().slice(0, 10));
    if (!endDate) setEndDate(end.toISOString().slice(0, 10));
  }, [startDate, endDate]);

  async function handleCheck() {
    if (!surfaceId) return;
    setLoading(true); setError(null); setResult(null);

    const startDt = new Date(`${startDate || "2026-01-01"}T${String(startHour).padStart(2, "0")}:00:00`);
    const endDt = new Date(`${endDate || "2026-01-01"}T${String(endHour).padStart(2, "0")}:00:00`);

    try {
      const body: InventoryAvailabilityRequest = {
        surface_id: surfaceId,
        starts_at: startDt.toISOString(),
        ends_at: endDt.toISOString(),
      };
      if (reqUnits) body.requested_capacity_units = Number(reqUnits);
      if (reqSov) body.requested_sov_percent = Number(reqSov);

      const data: InventoryAvailabilityResponse = await api.post("/inventory/availability", body);
      setResult(data);
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
      else setError("Ошибка при проверке доступности");
    } finally {
      setLoading(false);
    }
  }

  const selectedSurface = surfaces.find((s) => s.id === surfaceId);

  return (
    <div>
      <h2 style={{ fontSize: "var(--rmp-font-size-lg)", fontWeight: 600, marginBottom: "var(--rmp-space-4)" }}>
        Проверка доступности
      </h2>

      {/* Form */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "var(--rmp-space-3)", marginBottom: "var(--rmp-space-4)", padding: "var(--rmp-space-3)", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-md)" }}>
        <div>
          <label style={labelStyle} htmlFor="av-surface">Поверхность</label>
          <select id="av-surface" value={surfaceId} onChange={(e) => setSurfaceId(e.target.value)} style={{ ...fieldStyle, width: "100%" }}>
            <option value="">— Выберите поверхность —</option>
            {surfaces.map((s) => (
              <option key={s.id} value={s.id}>{s.code} ({s.store_name ?? s.store_id})</option>
            ))}
          </select>
          {surfacesLoading && <span style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Загрузка...</span>}
          {surfacesError && <span style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-danger-600)" }}>{surfacesError}</span>}
        </div>

        <div>
          <label style={labelStyle} htmlFor="av-start">Начало</label>
          <div style={{ display: "flex", gap: "var(--rmp-space-1)" }}>
            <input id="av-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={fieldStyle} />
            <input type="number" min="0" max="23" value={startHour} onChange={(e) => setStartHour(e.target.value)} style={{ ...fieldStyle, width: 56 }} aria-label="Начальный час" />
          </div>
        </div>

        <div>
          <label style={labelStyle} htmlFor="av-end">Конец</label>
          <div style={{ display: "flex", gap: "var(--rmp-space-1)" }}>
            <input id="av-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={fieldStyle} />
            <input type="number" min="0" max="23" value={endHour} onChange={(e) => setEndHour(e.target.value)} style={{ ...fieldStyle, width: 56 }} aria-label="Конечный час" />
          </div>
        </div>

        <div>
          <label style={labelStyle} htmlFor="av-units">Запрошено единиц</label>
          <input id="av-units" type="number" min="1" value={reqUnits} onChange={(e) => setReqUnits(e.target.value)} placeholder="10" style={{ ...fieldStyle, width: "100%" }} />
        </div>

        <div>
          <label style={labelStyle} htmlFor="av-sov">SOV %</label>
          <input id="av-sov" type="number" min="1" max="100" value={reqSov} onChange={(e) => setReqSov(e.target.value)} placeholder="30" style={{ ...fieldStyle, width: "100%" }} />
        </div>

        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button onClick={handleCheck} disabled={!surfaceId || loading} style={{ ...btnPrimary, opacity: (!surfaceId || loading) ? 0.5 : 1 }}>
            {loading ? "Проверка..." : "Проверить доступность"}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && !loading && (
        <div style={{ ...summaryBox, borderColor: "var(--rmp-danger-600)", color: "var(--rmp-danger-600)", background: "var(--rmp-danger-50)" }}>
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && <p style={{ color: "var(--rmp-text-secondary)" }}>Проверка доступности...</p>}

      {/* Results */}
      {result && !loading && (
        <div>
          {/* Summary */}
          <div style={summaryBox}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "var(--rmp-space-2)" }}>
              <div><div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Поверхность</div><strong>{selectedSurface?.code ?? result.surface_id}</strong></div>
              <div><div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Запрошено</div><strong>{result.total_requested}</strong></div>
              <div><div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Доступно</div><strong>{result.total_available}</strong></div>
              <div><div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Конфликтов</div><strong style={{ color: result.conflicts.length > 0 ? "var(--rmp-danger-600)" : "var(--rmp-success-600)" }}>{result.conflicts.length}</strong></div>
              <div>
                <div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Результат</div>
                <strong style={{ color: result.all_available ? "var(--rmp-success-600)" : "var(--rmp-danger-600)" }}>
                  {result.all_available ? "Доступно" : "Недоступно"}
                </strong>
              </div>
            </div>
          </div>

          {/* Slot table */}
          {result.slots.length > 0 && (
            <div style={{ marginBottom: "var(--rmp-space-4)" }}>
              <h3 style={{ fontSize: "var(--rmp-font-size-base)", fontWeight: 600, marginBottom: "var(--rmp-space-2)" }}>Слоты</h3>
              <div style={{ overflowX: "auto" }}>
                <table className="rmp-table" style={{ fontSize: "var(--rmp-font-size-xs)" }}>
                  <thead>
                    <tr>
                      <th>Дата</th><th>Час</th><th>Всего</th><th>Занято</th><th>Резерв</th><th>Доступно</th><th>Запрошено</th><th>Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.slots.map((slot: InventorySlotAvailability) => (
                      <tr key={slot.slot_id}>
                        <td>{slot.slot_date}</td>
                        <td>{slot.slot_hour}</td>
                        <td>{slot.total_capacity}</td>
                        <td>{slot.booked_capacity}</td>
                        <td>{slot.reserved_capacity}</td>
                        <td>{slot.available_capacity}</td>
                        <td>{slot.requested_capacity}</td>
                        <td>
                          {slot.blocked
                            ? <span style={{ color: "var(--rmp-danger-600)" }}>Заблокирован</span>
                            : slot.sold_out
                              ? <span style={{ color: "var(--rmp-danger-600)" }}>Нет мест</span>
                              : slot.available
                                ? <span style={{ color: "var(--rmp-success-600)" }}>Доступен</span>
                                : <span style={{ color: "var(--rmp-danger-600)" }}>Недоступен</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Conflicts */}
          {result.conflicts.length > 0 && (
            <div>
              <h3 style={{ fontSize: "var(--rmp-font-size-base)", fontWeight: 600, marginBottom: "var(--rmp-space-2)", color: "var(--rmp-danger-600)" }}>Конфликты ({result.conflicts.length})</h3>
              <div style={{ overflowX: "auto" }}>
                <table className="rmp-table" style={{ fontSize: "var(--rmp-font-size-xs)" }}>
                  <thead>
                    <tr>
                      <th>Дата</th><th>Час</th><th>Доступно</th><th>Запрошено</th><th>Статус</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.conflicts.map((c: InventorySlotAvailability) => (
                      <tr key={c.slot_id}>
                        <td>{c.slot_date}</td>
                        <td>{c.slot_hour}</td>
                        <td>{c.available_capacity}</td>
                        <td>{c.requested_capacity}</td>
                        <td>
                          {c.blocked
                            ? <span style={{ color: "var(--rmp-danger-600)" }}>Заблокирован</span>
                            : <span style={{ color: "var(--rmp-danger-600)" }}>Недоступен</span>}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Empty slots */}
          {result.slots.length === 0 && result.conflicts.length === 0 && (
            <p style={{ color: "var(--rmp-text-secondary)" }}>Нет данных для отображения.</p>
          )}
        </div>
      )}

      {/* Empty state (no check done yet) */}
      {!loading && !result && !error && (
        <p style={{ color: "var(--rmp-text-secondary)" }}>Выберите поверхность и нажмите «Проверить доступность».</p>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════
// Conflicts tab
// ═══════════════════════════════════════════════

function ConflictsTab() {
  const [surfaces, setSurfaces] = useState<InventorySurfaceOut[]>([]);
  const [surfacesLoading, setSurfacesLoading] = useState(true);
  const [surfacesError, setSurfacesError] = useState<string | null>(null);

  const [surfaceId, setSurfaceId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [startHour, setStartHour] = useState("9");
  const [endDate, setEndDate] = useState("");
  const [endHour, setEndHour] = useState("18");
  const [reqUnits, setReqUnits] = useState("");
  const [reqSov, setReqSov] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<InventoryConflictCheckResponse | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const data = await fetchInventorySurfaces(200, 0);
        setSurfaces(data.items.filter((s) => s.is_active));
      } catch (e) {
        if (e instanceof ApiError && e.status === 403) setSurfacesError("Нет доступа");
        else setSurfacesError("Ошибка загрузки поверхностей");
      } finally { setSurfacesLoading(false); }
    })();
  }, []);

  useEffect(() => {
    const now = new Date();
    if (!startDate) setStartDate(now.toISOString().slice(0, 10));
    if (!endDate) setEndDate(now.toISOString().slice(0, 10));
  }, [startDate, endDate]);

  async function handleCheck() {
    if (!surfaceId) return;
    setLoading(true); setError(null); setResult(null);
    const startDt = new Date(`${startDate || "2026-01-01"}T${String(startHour).padStart(2, "0")}:00:00`);
    const endDt = new Date(`${endDate || "2026-01-01"}T${String(endHour).padStart(2, "0")}:00:00`);
    try {
      const body: InventoryConflictCheckRequest = {
        surface_id: surfaceId,
        starts_at: startDt.toISOString(),
        ends_at: endDt.toISOString(),
      };
      if (reqUnits) body.requested_capacity_units = Number(reqUnits);
      if (reqSov) body.requested_sov_percent = Number(reqSov);
      const data = await api.post<InventoryConflictCheckResponse>("/inventory/conflicts/check", body);
      setResult(data);
    } catch (e) {
      if (e instanceof ApiError) setError(e.message);
      else setError("Ошибка при проверке конфликтов");
    } finally { setLoading(false); }
  }

  const selectedSurface = surfaces.find((s) => s.id === surfaceId);

  return (
    <div>
      <h2 style={{ fontSize: "var(--rmp-font-size-lg)", fontWeight: 600, marginBottom: "var(--rmp-space-4)" }}>
        Проверка конфликтов
      </h2>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "var(--rmp-space-3)", marginBottom: "var(--rmp-space-4)", padding: "var(--rmp-space-3)", border: "1px solid var(--rmp-border-strong)", borderRadius: "var(--rmp-radius-md)" }}>
        <div>
          <label style={labelStyle} htmlFor="cf-surface">Поверхность</label>
          <select id="cf-surface" value={surfaceId} onChange={(e) => setSurfaceId(e.target.value)} style={{ ...fieldStyle, width: "100%" }}>
            <option value="">— Выберите поверхность —</option>
            {surfaces.map((s) => (
              <option key={s.id} value={s.id}>{s.code} ({s.store_name ?? s.store_id})</option>
            ))}
          </select>
          {surfacesLoading && <span style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Загрузка...</span>}
          {surfacesError && <span style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-danger-600)" }}>{surfacesError}</span>}
        </div>

        <div>
          <label style={labelStyle} htmlFor="cf-start">Начало</label>
          <div style={{ display: "flex", gap: "var(--rmp-space-1)" }}>
            <input id="cf-start" type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} style={fieldStyle} />
            <input type="number" min="0" max="23" value={startHour} onChange={(e) => setStartHour(e.target.value)} style={{ ...fieldStyle, width: 56 }} aria-label="Начальный час" />
          </div>
        </div>

        <div>
          <label style={labelStyle} htmlFor="cf-end">Конец</label>
          <div style={{ display: "flex", gap: "var(--rmp-space-1)" }}>
            <input id="cf-end" type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} style={fieldStyle} />
            <input type="number" min="0" max="23" value={endHour} onChange={(e) => setEndHour(e.target.value)} style={{ ...fieldStyle, width: 56 }} aria-label="Конечный час" />
          </div>
        </div>

        <div>
          <label style={labelStyle} htmlFor="cf-units">Запрошено единиц</label>
          <input id="cf-units" type="number" min="1" value={reqUnits} onChange={(e) => setReqUnits(e.target.value)} placeholder="10" style={{ ...fieldStyle, width: "100%" }} />
        </div>

        <div>
          <label style={labelStyle} htmlFor="cf-sov">SOV %</label>
          <input id="cf-sov" type="number" min="1" max="100" value={reqSov} onChange={(e) => setReqSov(e.target.value)} placeholder="30" style={{ ...fieldStyle, width: "100%" }} />
        </div>

        <div style={{ display: "flex", alignItems: "flex-end" }}>
          <button onClick={handleCheck} disabled={!surfaceId || loading} style={{ ...btnPrimary, opacity: (!surfaceId || loading) ? 0.5 : 1 }}>
            {loading ? "Проверка..." : "Проверить конфликты"}
          </button>
        </div>
      </div>

      {error && !loading && (
        <div style={{ ...summaryBox, borderColor: "var(--rmp-danger-600)", color: "var(--rmp-danger-600)" }}>{error}</div>
      )}

      {loading && <p style={{ color: "var(--rmp-text-secondary)" }}>Проверка конфликтов...</p>}

      {result && !loading && (
        <div>
          <div style={summaryBox}>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))", gap: "var(--rmp-space-2)" }}>
              <div><div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Поверхность</div><strong>{selectedSurface?.code ?? result.blocking[0]?.surface_id ?? surfaceId}</strong></div>
              <div><div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Блокирующих</div><strong style={{ color: result.blocking.length > 0 ? "var(--rmp-danger-600)" : "var(--rmp-success-600)" }}>{result.blocking.length}</strong></div>
              <div><div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Предупреждений</div><strong style={{ color: result.warnings.length > 0 ? "var(--rmp-warning-600)" : "var(--rmp-text-primary)" }}>{result.warnings.length}</strong></div>
              <div>
                <div style={{ fontSize: "var(--rmp-font-size-xs)", color: "var(--rmp-text-secondary)" }}>Результат</div>
                <strong style={{ color: result.has_conflicts ? "var(--rmp-danger-600)" : "var(--rmp-success-600)" }}>
                  {result.has_conflicts ? "Есть конфликты" : "Конфликтов нет"}
                </strong>
              </div>
            </div>
          </div>

          {result.blocking.length > 0 && (
            <div style={{ marginBottom: "var(--rmp-space-4)" }}>
              <h3 style={{ fontSize: "var(--rmp-font-size-base)", fontWeight: 600, marginBottom: "var(--rmp-space-2)", color: "var(--rmp-danger-600)" }}>Блокирующие конфликты</h3>
              <ConflictTable items={result.blocking} />
            </div>
          )}

          {result.warnings.length > 0 && (
            <div style={{ marginBottom: "var(--rmp-space-4)" }}>
              <h3 style={{ fontSize: "var(--rmp-font-size-base)", fontWeight: 600, marginBottom: "var(--rmp-space-2)", color: "var(--rmp-warning-600)" }}>Предупреждения</h3>
              <ConflictTable items={result.warnings} />
            </div>
          )}

          {result.blocking.length === 0 && result.warnings.length === 0 && (
            <p style={{ color: "var(--rmp-success-600)" }}>Конфликтов не обнаружено.</p>
          )}
        </div>
      )}

      {!loading && !result && !error && (
        <p style={{ color: "var(--rmp-text-secondary)" }}>Выберите поверхность и нажмите «Проверить конфликты».</p>
      )}
    </div>
  );
}

function ConflictTable({ items }: { items: InventoryConflictItem[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table className="rmp-table" style={{ fontSize: "var(--rmp-font-size-xs)" }}>
        <thead>
          <tr>
            <th>Тип</th><th>Тип правила</th><th>Сообщение</th><th>Дата</th><th>Час</th><th>Доступно</th><th>Запрошено</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c: InventoryConflictItem, i: number) => (
            <tr key={`${c.conflict_type}-${i}`}>
              <td><span style={{ color: c.severity === "blocking" ? "var(--rmp-danger-600)" : "var(--rmp-warning-600)" }}>{c.conflict_type}</span></td>
              <td>{c.rule_type ?? "—"}</td>
              <td style={{ maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis" }}>{c.message}</td>
              <td>{c.slot_date ?? "—"}</td>
              <td>{c.slot_hour ?? "—"}</td>
              <td>{c.available_capacity ?? "—"}</td>
              <td>{c.requested_capacity ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ═══════════════════════════════════════════════
// Rules tab — read-only placeholder
// ═══════════════════════════════════════════════

function RulesTab() {
  return (
    <div>
      <h2 style={{ fontSize: "var(--rmp-font-size-lg)", fontWeight: 600, marginBottom: "var(--rmp-space-4)" }}>
        Правила инвентаря
      </h2>
      <div style={{ ...summaryBox, borderColor: "var(--rmp-border-strong)", background: "var(--rmp-gray-50)" }}>
        <p style={{ fontSize: "var(--rmp-font-size-base)", color: "var(--rmp-text-secondary)", margin: 0 }}>
          Правила инвентаря (блэкауты, лимиты SOV, внутренние блокировки) работают на уровне backend-движка.
        </p>
        <p style={{ fontSize: "var(--rmp-font-size-base)", color: "var(--rmp-text-secondary)", margin: "var(--rmp-space-2) 0 0 0" }}>
          Просмотр и управление правилами через интерфейс появится в следующей версии (S-082).
        </p>
      </div>
    </div>
  );
}
