import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "../api/client";
import type { InventoryStoreOut, InventorySurfaceOut, InventorySurfacePatchRequest, PaginatedResponse } from "../api/types";
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

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<"stores" | "surfaces">("stores");
  return (
    <div>
      <PageHeader title="Инвентарь" />
      <div style={{ display: "flex", gap: "var(--rmp-space-2)", marginBottom: "var(--rmp-space-4)" }}>
        {(["stores", "surfaces"] as const).map((t) => (
          <button key={t} onClick={() => setActiveTab(t)}
            style={{
              padding: "var(--rmp-space-1) var(--rmp-space-3)", borderRadius: "var(--rmp-radius-sm)",
              border: "1px solid var(--rmp-border-strong)",
              background: activeTab === t ? "var(--rmp-gray-800)" : "var(--rmp-bg-surface)",
              color: activeTab === t ? "var(--rmp-text-inverse)" : "var(--rmp-text-primary)",
              cursor: "pointer", fontSize: "var(--rmp-font-size-sm)",
            }}>
            {t === "stores" ? "Магазины" : "Поверхности"}
          </button>
        ))}
      </div>
      {activeTab === "stores" ? <StoresTab /> : <SurfacesTab />}
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
