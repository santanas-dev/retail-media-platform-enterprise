import { useEffect, useState, useCallback } from "react";
import { api, ApiError } from "../api/client";
import type { InventoryStoreOut, InventorySurfaceOut, InventorySurfacePatchRequest, PaginatedResponse } from "../api/types";

// ── Helpers ──

function fmtRes(w: number, h: number): string {
  return `${w}×${h}`;
}

const PAGE_SIZE = 50;

// ── Pagination ──

function Pagination({
  total, offset, limit, hasPrev, hasNext, onPrev, onNext,
}: {
  total: number; offset: number; limit: number;
  hasPrev: boolean; hasNext: boolean;
  onPrev: () => void; onNext: () => void;
}) {
  if (total <= limit) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: "0.75rem", fontSize: "0.8125rem" }}>
      <span style={{ color: "#64748b" }}>{from}–{to} из {total}</span>
      <div style={{ display: "flex", gap: "0.25rem" }}>
        <button onClick={onPrev} disabled={!hasPrev} style={pgnBtn(hasPrev)}>← Назад</button>
        <button onClick={onNext} disabled={!hasNext} style={pgnBtn(hasNext)}>Вперёд →</button>
      </div>
    </div>
  );
}

function pgnBtn(enabled: boolean): React.CSSProperties {
  return {
    padding: "0.2rem 0.6rem", fontSize: "0.75rem", border: "1px solid #cbd5e1",
    borderRadius: 4, background: enabled ? "#fff" : "#f1f5f9",
    color: enabled ? "#334155" : "#94a3b8", cursor: enabled ? "pointer" : "default",
  };
}

// ── API helpers ──

function fetchInventoryStores(limit: number, offset: number): Promise<PaginatedResponse<InventoryStoreOut>> {
  return api.get<PaginatedResponse<InventoryStoreOut>>(`/inventory/stores?limit=${limit}&offset=${offset}`);
}

function fetchInventorySurfaces(limit: number, offset: number): Promise<PaginatedResponse<InventorySurfaceOut>> {
  return api.get<PaginatedResponse<InventorySurfaceOut>>(`/inventory/surfaces?limit=${limit}&offset=${offset}`);
}

// ── Component ──

export default function InventoryPage() {
  const [activeTab, setActiveTab] = useState<"stores" | "surfaces">("stores");

  return (
    <div>
      <h1 style={{ fontSize: "1.25rem", fontWeight: 600, marginBottom: "1rem" }}>
        Инвентарь
      </h1>
      <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        {(["stores", "surfaces"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setActiveTab(t)}
            style={{
              padding: "0.25rem 0.75rem",
              borderRadius: 4,
              border: "1px solid #cbd5e1",
              background: activeTab === t ? "#1e293b" : "#fff",
              color: activeTab === t ? "#fff" : "#334155",
              cursor: "pointer",
              fontSize: "0.8125rem",
            }}
          >
            {t === "stores" ? "Магазины" : "Поверхности"}
          </button>
        ))}
      </div>
      {activeTab === "stores" ? <StoresTab /> : <SurfacesTab />}
    </div>
  );
}

// ── Stores Tab ──

function StoresTab() {
  const [stores, setStores] = useState<InventoryStoreOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const load = useCallback(async (pageOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInventoryStores(PAGE_SIZE, pageOffset);
      setStores(data.items);
      setTotal(data.total);
      setOffset(pageOffset);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setError("Нет доступа к инвентарю");
      } else {
        setError("Ошибка загрузки");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(0); }, [load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  const filtered = search
    ? stores.filter((s) =>
        s.name.toLowerCase().includes(search.toLowerCase()) ||
        s.code.toLowerCase().includes(search.toLowerCase())
      )
    : stores;

  return (
    <div>
      <input
        type="text"
        placeholder="Поиск по названию или коду..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          padding: "0.25rem 0.5rem",
          fontSize: "0.8125rem",
          border: "1px solid #cbd5e1",
          borderRadius: 4,
          marginBottom: "0.5rem",
          width: 280,
        }}
      />
      {loading && <p style={{ color: "#64748b" }}>Загрузка...</p>}
      {error && !loading && <p style={{ color: "#dc2626" }}>{error}</p>}
      {!loading && !error && filtered.length === 0 && (
        <p style={{ color: "#64748b" }}>{search ? "Ничего не найдено" : "Нет магазинов"}</p>
      )}
      {!loading && filtered.length > 0 && (
        <>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f1f5f9", textAlign: "left" }}>
                <th style={thStyle}>Код</th>
                <th style={thStyle}>Название</th>
                <th style={thStyle}>Филиал</th>
                <th style={thStyle}>Кластер</th>
                <th style={thStyle}>Адрес</th>
                <th style={thStyle}>Поверхностей</th>
                <th style={thStyle}>Активен</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr key={s.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                  <td style={tdStyle}>{s.code}</td>
                  <td style={tdStyle}><strong>{s.name}</strong></td>
                  <td style={tdStyle}>{s.branch_name ?? "—"}</td>
                  <td style={tdStyle}>{s.cluster_name ?? "—"}</td>
                  <td style={tdStyle}>{s.address || "—"}</td>
                  <td style={tdStyle}>{s.surface_count}</td>
                  <td style={tdStyle}>
                    <span style={{ color: s.is_active ? "#059669" : "#dc2626" }}>
                      {s.is_active ? "Да" : "Нет"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination
            total={total} offset={offset} limit={PAGE_SIZE}
            hasPrev={hasPrev} hasNext={hasNext}
            onPrev={() => load(offset - PAGE_SIZE)}
            onNext={() => load(offset + PAGE_SIZE)}
          />
        </>
      )}
    </div>
  );
}

// ── Surfaces Tab ──

function SurfacesTab() {
  const [surfaces, setSurfaces] = useState<InventorySurfaceOut[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [toggling, setToggling] = useState<string | null>(null);

  const load = useCallback(async (pageOffset: number) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchInventorySurfaces(PAGE_SIZE, pageOffset);
      setSurfaces(data.items);
      setTotal(data.total);
      setOffset(pageOffset);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setError("Нет доступа к инвентарю");
      } else {
        setError("Ошибка загрузки");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(0); }, [load]);

  const hasPrev = offset > 0;
  const hasNext = offset + PAGE_SIZE < total;

  const filtered = search
    ? surfaces.filter((s) =>
        s.code.toLowerCase().includes(search.toLowerCase()) ||
        (s.store_name ?? "").toLowerCase().includes(search.toLowerCase())
      )
    : surfaces;

  const handleToggle = async (surface: InventorySurfaceOut) => {
    setToggling(surface.id);
    try {
      const body: InventorySurfacePatchRequest = { is_active: !surface.is_active };
      await api.patch<InventorySurfaceOut>(`/inventory/surfaces/${surface.id}`, body);
      await load(offset);
    } catch (e) {
      // silently ignore
    } finally {
      setToggling(null);
    }
  };

  return (
    <div>
      <input
        type="text"
        placeholder="Поиск по коду или магазину..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{
          padding: "0.25rem 0.5rem",
          fontSize: "0.8125rem",
          border: "1px solid #cbd5e1",
          borderRadius: 4,
          marginBottom: "0.5rem",
          width: 280,
        }}
      />
      {loading && <p style={{ color: "#64748b" }}>Загрузка...</p>}
      {error && !loading && <p style={{ color: "#dc2626" }}>{error}</p>}
      {!loading && !error && filtered.length === 0 && (
        <p style={{ color: "#64748b" }}>{search ? "Ничего не найдено" : "Нет поверхностей"}</p>
      )}
      {!loading && filtered.length > 0 && (
        <>
          <table style={tableStyle}>
            <thead>
              <tr style={{ background: "#f1f5f9", textAlign: "left" }}>
                <th style={thStyle}>Код</th>
                <th style={thStyle}>Магазин</th>
                <th style={thStyle}>Разрешение</th>
                <th style={thStyle}>Активна</th>
                <th style={thStyle}></th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((ds) => (
                <tr key={ds.id} style={{ borderBottom: "1px solid #e2e8f0" }}>
                  <td style={tdStyle}><strong>{ds.code}</strong></td>
                  <td style={tdStyle}>{ds.store_name ?? ds.store_code ?? ds.store_id}</td>
                  <td style={tdStyle}>{fmtRes(ds.resolution_w, ds.resolution_h)}</td>
                  <td style={tdStyle}>
                    <span style={{ color: ds.is_active ? "#059669" : "#dc2626" }}>
                      {ds.is_active ? "Да" : "Нет"}
                    </span>
                  </td>
                  <td style={tdStyle}>
                    <button
                      onClick={() => handleToggle(ds)}
                      disabled={toggling === ds.id}
                      style={{
                        padding: "0.15rem 0.5rem",
                        fontSize: "0.75rem",
                        border: `1px solid ${ds.is_active ? "#dc2626" : "#059669"}`,
                        borderRadius: 4,
                        background: "#fff",
                        color: ds.is_active ? "#dc2626" : "#059669",
                        cursor: toggling === ds.id ? "default" : "pointer",
                        opacity: toggling === ds.id ? 0.5 : 1,
                      }}
                    >
                      {toggling === ds.id ? "..." : ds.is_active ? "Деактивировать" : "Активировать"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <Pagination
            total={total} offset={offset} limit={PAGE_SIZE}
            hasPrev={hasPrev} hasNext={hasNext}
            onPrev={() => load(offset - PAGE_SIZE)}
            onNext={() => load(offset + PAGE_SIZE)}
          />
        </>
      )}
    </div>
  );
}

// ── Styles ──

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "0.8125rem",
};

const thStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  fontWeight: 600,
  color: "#475569",
  fontSize: "0.75rem",
};

const tdStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  verticalAlign: "top",
};
