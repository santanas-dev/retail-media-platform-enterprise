/**
 * CommerceTariffsPage — tariff version + price item management.
 *
 * COMMERCE-CONTUR2-001A3a: admin-web UI for tariff and price management.
 *
 * Two sub-tabs:
 *   - Тарифы: list, create, edit tariff versions
 *   - Прайс-листы: select tariff → list, create, edit price items
 */
import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { formatApiError } from "../api/errors";
import {
  listTariffVersions,
  createTariffVersion,
  updateTariffVersion,
  listPriceItems,
  createPriceItem,
  updatePriceItem,
} from "../api/commerce";
import type {
  CommerceTariffVersionOut,
  CommercePriceItemOut,
} from "../api/types";

// ── Helpers ──

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  active: "Активен",
  archived: "Архивный",
};

// ── Styles ──

const pageStyle: React.CSSProperties = {
  maxWidth: "1100px",
  margin: "0 auto",
  padding: "var(--rmp-space-4)",
};

const tabBtn = (active: boolean): React.CSSProperties => ({
  padding: "var(--rmp-space-1) var(--rmp-space-3)",
  borderRadius: "var(--rmp-radius-sm)",
  border: "1px solid var(--rmp-border-strong)",
  background: active ? "var(--rmp-gray-800)" : "var(--rmp-bg-surface)",
  color: active ? "var(--rmp-text-inverse)" : "var(--rmp-text-primary)",
  cursor: "pointer",
  fontSize: "var(--rmp-font-size-sm)",
});

const tableStyle: React.CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: "var(--rmp-font-size-sm)",
};

const thStyle: React.CSSProperties = {
  textAlign: "left",
  padding: "var(--rmp-space-2)",
  borderBottom: "2px solid var(--rmp-border-strong)",
  fontWeight: 600,
};

const tdStyle: React.CSSProperties = {
  padding: "var(--rmp-space-2)",
  borderBottom: "1px solid var(--rmp-border-strong)",
  verticalAlign: "middle",
};

const formGrid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
  gap: "var(--rmp-space-2)",
  padding: "var(--rmp-space-3)",
  border: "1px solid var(--rmp-border-strong)",
  borderRadius: "var(--rmp-radius-md)",
  marginBottom: "var(--rmp-space-3)",
};

// ── Tariff Form ──

interface TariffFormState {
  code: string;
  name: string;
  status: string;
  valid_from: string;
  valid_to: string;
  currency: string;
}

const emptyTariffForm = (): TariffFormState => ({
  code: "",
  name: "",
  status: "draft",
  valid_from: new Date().toISOString().slice(0, 10),
  valid_to: "",
  currency: "RUB",
});

function TariffForm({
  onSubmit,
  initial,
  onCancel,
}: {
  onSubmit: (data: TariffFormState) => Promise<void>;
  initial?: CommerceTariffVersionOut;
  onCancel?: () => void;
}) {
  const [form, setForm] = useState<TariffFormState>(
    initial
      ? {
          code: initial.code,
          name: initial.name,
          status: initial.status,
          valid_from: fmtDate(initial.valid_from),
          valid_to: initial.valid_to ? fmtDate(initial.valid_to) : "",
          currency: initial.currency,
        }
      : emptyTariffForm(),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.code.trim() || !form.name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form);
      setForm(emptyTariffForm());
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      data-testid="commerce-tariff-form"
      onSubmit={handleSubmit}
      style={formGrid}
    >
      <div>
        <label htmlFor="ct-code">Код *</label>
        <input
          id="ct-code"
          data-testid="commerce-tariff-code"
          value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value })}
          disabled={!!initial}
          required
        />
      </div>
      <div>
        <label htmlFor="ct-name">Название *</label>
        <input
          id="ct-name"
          data-testid="commerce-tariff-name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
      </div>
      {initial && (
        <div>
          <label htmlFor="ct-status">Статус</label>
          <select
            id="ct-status"
            data-testid="commerce-tariff-status"
            value={form.status}
            onChange={(e) => setForm({ ...form, status: e.target.value })}
          >
            <option value="draft">Черновик</option>
            <option value="active">Активен</option>
            <option value="archived">Архивный</option>
          </select>
        </div>
      )}
      <div>
        <label htmlFor="ct-currency">Валюта</label>
        <input
          id="ct-currency"
          data-testid="commerce-tariff-currency"
          value={form.currency}
          onChange={(e) => setForm({ ...form, currency: e.target.value })}
          maxLength={3}
        />
      </div>
      <div>
        <label htmlFor="ct-valid-from">Действует с *</label>
        <input
          id="ct-valid-from"
          type="date"
          data-testid="commerce-tariff-valid-from"
          value={form.valid_from}
          onChange={(e) => setForm({ ...form, valid_from: e.target.value })}
          required
        />
      </div>
      <div>
        <label htmlFor="ct-valid-to">Действует по</label>
        <input
          id="ct-valid-to"
          type="date"
          data-testid="commerce-tariff-valid-to"
          value={form.valid_to}
          onChange={(e) => setForm({ ...form, valid_to: e.target.value })}
        />
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: "var(--rmp-space-2)" }}>
        <button type="submit" data-testid="commerce-tariff-submit" disabled={saving}>
          {saving ? "Сохранение…" : initial ? "Сохранить" : "Создать тариф"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={saving}>
            Отмена
          </button>
        )}
      </div>
      {error && (
        <div
          data-testid="commerce-tariff-error"
          style={{
            gridColumn: "1 / -1",
            color: "var(--rmp-danger-600)",
            fontSize: "var(--rmp-font-size-sm)",
          }}
        >
          {error}
        </div>
      )}
    </form>
  );
}

// ── Price Item Form ──

interface PriceFormState {
  surface_id: string;
  unit_price_amount: string;
}

const emptyPriceForm = (): PriceFormState => ({
  surface_id: "",
  unit_price_amount: "",
});

function PriceForm({
  onSubmit,
  initial,
  onCancel,
}: {
  onSubmit: (data: PriceFormState) => Promise<void>;
  initial?: CommercePriceItemOut;
  onCancel?: () => void;
}) {
  const [form, setForm] = useState<PriceFormState>(
    initial
      ? {
          surface_id: initial.surface_id,
          unit_price_amount: String(initial.unit_price_amount),
        }
      : emptyPriceForm(),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.surface_id.trim() || !form.unit_price_amount) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form);
      setForm(emptyPriceForm());
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form
      data-testid="commerce-price-item-form"
      onSubmit={handleSubmit}
      style={formGrid}
    >
      <div>
        <label htmlFor="cpi-surface">Поверхность *</label>
        <input
          id="cpi-surface"
          data-testid="commerce-price-item-surface"
          value={form.surface_id}
          onChange={(e) => setForm({ ...form, surface_id: e.target.value })}
          disabled={!!initial}
          required
          placeholder="UUID поверхности"
        />
      </div>
      <div>
        <label htmlFor="cpi-price">Цена за surface_day *</label>
        <input
          id="cpi-price"
          type="number"
          data-testid="commerce-price-item-unit-price"
          value={form.unit_price_amount}
          onChange={(e) =>
            setForm({ ...form, unit_price_amount: e.target.value })
          }
          min="0.01"
          step="0.01"
          required
        />
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: "var(--rmp-space-2)" }}>
        <button type="submit" data-testid="commerce-price-item-submit" disabled={saving}>
          {saving ? "Сохранение…" : initial ? "Сохранить" : "Добавить цену"}
        </button>
        {onCancel && (
          <button type="button" onClick={onCancel} disabled={saving}>
            Отмена
          </button>
        )}
      </div>
      {error && (
        <div
          data-testid="commerce-price-item-error"
          style={{
            gridColumn: "1 / -1",
            color: "var(--rmp-danger-600)",
            fontSize: "var(--rmp-font-size-sm)",
          }}
        >
          {error}
        </div>
      )}
    </form>
  );
}

// ── Page ──

type SubTab = "tariffs" | "prices";

export default function CommerceTariffsPage() {
  const { user } = useAuth();
  const canManage =
    user?.permissions?.includes("commerce.tariff_manage") ?? false;

  const [subTab, setSubTab] = useState<SubTab>("tariffs");

  // Tariff state
  const [tariffs, setTariffs] = useState<CommerceTariffVersionOut[]>([]);
  const [tariffsLoading, setTariffsLoading] = useState(true);
  const [tariffsError, setTariffsError] = useState<string | null>(null);
  const [showCreateTariff, setShowCreateTariff] = useState(false);
  const [editingTariff, setEditingTariff] =
    useState<CommerceTariffVersionOut | null>(null);

  // Price state
  const [selectedTariffId, setSelectedTariffId] = useState<string>("");
  const [priceItems, setPriceItems] = useState<CommercePriceItemOut[]>([]);
  const [pricesLoading, setPricesLoading] = useState(false);
  const [pricesError, setPricesError] = useState<string | null>(null);
  const [showCreatePrice, setShowCreatePrice] = useState(false);
  const [editingPrice, setEditingPrice] =
    useState<CommercePriceItemOut | null>(null);

  // Load tariffs
  const loadTariffs = useCallback(async () => {
    setTariffsLoading(true);
    setTariffsError(null);
    try {
      const data = await listTariffVersions();
      setTariffs(data);
    } catch (e) {
      setTariffsError(
        e instanceof ApiError && e.status === 403
          ? "Нет прав на просмотр тарифов."
          : formatApiError(e),
      );
    } finally {
      setTariffsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTariffs();
  }, [loadTariffs]);

  // Load prices for selected tariff
  const loadPrices = useCallback(async (tariffId: string) => {
    if (!tariffId) {
      setPriceItems([]);
      return;
    }
    setPricesLoading(true);
    setPricesError(null);
    try {
      const data = await listPriceItems(tariffId);
      setPriceItems(data);
    } catch (e) {
      setPricesError(
        e instanceof ApiError && e.status === 403
          ? "Нет прав на просмотр прайс-листов."
          : formatApiError(e),
      );
    } finally {
      setPricesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadPrices(selectedTariffId);
    setShowCreatePrice(false);
    setEditingPrice(null);
  }, [selectedTariffId, loadPrices]);

  // ── Handlers ──

  async function handleCreateTariff(form: TariffFormState) {
    await createTariffVersion({
      code: form.code.trim(),
      name: form.name.trim(),
      valid_from: form.valid_from,
      valid_to: form.valid_to || null,
      currency: form.currency,
    });
    setShowCreateTariff(false);
    await loadTariffs();
  }

  async function handleUpdateTariff(form: TariffFormState) {
    if (!editingTariff) return;
    await updateTariffVersion(editingTariff.id, {
      name: form.name.trim(),
      status: form.status,
      valid_from: form.valid_from,
      valid_to: form.valid_to || null,
    });
    setEditingTariff(null);
    await loadTariffs();
  }

  async function handleCreatePrice(form: PriceFormState) {
    await createPriceItem(selectedTariffId, {
      surface_id: form.surface_id.trim(),
      unit_price_amount: Number(form.unit_price_amount),
    });
    setShowCreatePrice(false);
    await loadPrices(selectedTariffId);
  }

  async function handleUpdatePrice(form: PriceFormState) {
    if (!editingPrice) return;
    await updatePriceItem(editingPrice.id, {
      unit_price_amount: Number(form.unit_price_amount),
    });
    setEditingPrice(null);
    await loadPrices(selectedTariffId);
  }

  // ── Tariffs tab ──

  function renderTariffsTab() {
    return (
      <div>
        {canManage && !showCreateTariff && !editingTariff && (
          <button
            data-testid="commerce-tariff-create-open"
            onClick={() => {
              setShowCreateTariff(true);
              setEditingTariff(null);
            }}
            style={{ marginBottom: "var(--rmp-space-3)" }}
          >
            + Создать тариф
          </button>
        )}

        {showCreateTariff && (
          <TariffForm
            onSubmit={handleCreateTariff}
            onCancel={() => setShowCreateTariff(false)}
          />
        )}

        {tariffsLoading && <p>Загрузка тарифов…</p>}

        {tariffsError && (
          <div
            style={{
              color: "var(--rmp-danger-600)",
              marginBottom: "var(--rmp-space-3)",
            }}
          >
            {tariffsError}
          </div>
        )}

        {!tariffsLoading && !tariffsError && tariffs.length === 0 && (
          <p style={{ color: "var(--rmp-text-secondary)" }}>
            Нет тарифных версий. Создайте первую.
          </p>
        )}

        {tariffs.length > 0 && (
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>Код</th>
                <th style={thStyle}>Название</th>
                <th style={thStyle}>Статус</th>
                <th style={thStyle}>Действует с</th>
                <th style={thStyle}>Действует по</th>
                <th style={thStyle}>Валюта</th>
                {canManage && <th style={thStyle}></th>}
              </tr>
            </thead>
            <tbody>
              {tariffs.map((tv) =>
                editingTariff?.id === tv.id ? (
                  <tr key={tv.id}>
                    <td colSpan={canManage ? 7 : 6} style={tdStyle}>
                      <TariffForm
                        onSubmit={handleUpdateTariff}
                        initial={tv}
                        onCancel={() => setEditingTariff(null)}
                      />
                    </td>
                  </tr>
                ) : (
                  <tr
                    key={tv.id}
                    data-testid={`commerce-tariff-row-${tv.id}`}
                    style={{
                      cursor: subTab === "prices" ? "pointer" : "default",
                      background:
                        selectedTariffId === tv.id
                          ? "var(--rmp-gray-100)"
                          : undefined,
                    }}
                    onClick={() => setSelectedTariffId(tv.id)}
                  >
                    <td style={tdStyle}>
                      <code>{tv.code}</code>
                    </td>
                    <td style={tdStyle}>{tv.name}</td>
                    <td style={tdStyle}>
                      {STATUS_LABELS[tv.status] ?? tv.status}
                    </td>
                    <td style={tdStyle}>{fmtDate(tv.valid_from)}</td>
                    <td style={tdStyle}>
                      {tv.valid_to ? fmtDate(tv.valid_to) : "—"}
                    </td>
                    <td style={tdStyle}>{tv.currency}</td>
                    {canManage && (
                      <td style={tdStyle}>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingTariff(tv);
                            setShowCreateTariff(false);
                          }}
                        >
                          Изменить
                        </button>
                      </td>
                    )}
                  </tr>
                ),
              )}
            </tbody>
          </table>
        )}
      </div>
    );
  }

  // ── Prices tab ──

  function renderPricesTab() {
    const selectedTariff = tariffs.find((t) => t.id === selectedTariffId);

    if (!selectedTariffId || !selectedTariff) {
      return (
        <p style={{ color: "var(--rmp-text-secondary)" }}>
          Выберите тариф на вкладке «Тарифы», чтобы управлять прайс-листом.
        </p>
      );
    }

    return (
      <div>
        <h3 style={{ margin: "0 0 var(--rmp-space-3) 0" }}>
          Прайс-лист: {selectedTariff.code} — {selectedTariff.name}
        </h3>

        {canManage && !showCreatePrice && !editingPrice && (
          <button
            data-testid="commerce-price-item-create-open"
            onClick={() => {
              setShowCreatePrice(true);
              setEditingPrice(null);
            }}
            style={{ marginBottom: "var(--rmp-space-3)" }}
          >
            + Добавить цену
          </button>
        )}

        {showCreatePrice && (
          <PriceForm
            onSubmit={handleCreatePrice}
            onCancel={() => setShowCreatePrice(false)}
          />
        )}

        {pricesLoading && <p>Загрузка…</p>}

        {pricesError && (
          <div style={{ color: "var(--rmp-danger-600)" }}>{pricesError}</div>
        )}

        {!pricesLoading && !pricesError && priceItems.length === 0 && (
          <p style={{ color: "var(--rmp-text-secondary)" }}>
            Нет позиций прайс-листа. Добавьте первую.
          </p>
        )}

        {priceItems.length > 0 && (
          <table style={tableStyle} data-testid="commerce-price-items-table">
            <thead>
              <tr>
                <th style={thStyle}>Поверхность</th>
                <th style={thStyle}>Billing unit</th>
                <th style={thStyle}>Цена</th>
                <th style={thStyle}>Валюта</th>
                {canManage && <th style={thStyle}></th>}
              </tr>
            </thead>
            <tbody>
              {priceItems.map((pi) =>
                editingPrice?.id === pi.id ? (
                  <tr key={pi.id}>
                    <td colSpan={canManage ? 5 : 4} style={tdStyle}>
                      <PriceForm
                        onSubmit={handleUpdatePrice}
                        initial={pi}
                        onCancel={() => setEditingPrice(null)}
                      />
                    </td>
                  </tr>
                ) : (
                  <tr
                    key={pi.id}
                    data-testid={`commerce-price-item-row-${pi.id}`}
                  >
                    <td style={tdStyle}>
                      <code style={{ fontSize: "0.75rem" }}>
                        {pi.surface_id.slice(0, 12)}…
                      </code>
                    </td>
                    <td style={tdStyle}>{pi.billing_unit}</td>
                    <td style={tdStyle}>
                      {pi.unit_price_amount.toLocaleString("ru-RU")}
                    </td>
                    <td style={tdStyle}>{pi.currency}</td>
                    {canManage && (
                      <td style={tdStyle}>
                        <button
                          onClick={() => {
                            setEditingPrice(pi);
                            setShowCreatePrice(false);
                          }}
                        >
                          Изменить
                        </button>
                      </td>
                    )}
                  </tr>
                ),
              )}
            </tbody>
          </table>
        )}
      </div>
    );
  }

  // ── Render ──

  return (
    <div data-testid="commerce-tariffs-page" style={pageStyle}>
      <h1 style={{ margin: "0 0 var(--rmp-space-4) 0" }}>Коммерция</h1>

      <div
        style={{
          display: "flex",
          gap: "var(--rmp-space-2)",
          marginBottom: "var(--rmp-space-4)",
          flexWrap: "wrap",
        }}
      >
        <button
          onClick={() => setSubTab("tariffs")}
          style={tabBtn(subTab === "tariffs")}
        >
          Тарифы
        </button>
        <button
          onClick={() => setSubTab("prices")}
          style={tabBtn(subTab === "prices")}
        >
          Прайс-листы
        </button>
      </div>

      {subTab === "tariffs" && renderTariffsTab()}
      {subTab === "prices" && renderPricesTab()}
    </div>
  );
}
