/**
 * CommerceOrdersTab — order list, create, detail, status management.
 *
 * COMMERCE-CONTUR2-001A3b: admin-web UI for order CRUD + status.
 */
import { useState, useEffect, useCallback } from "react";
import { ApiError } from "../api/client";
import { formatApiError } from "../api/errors";
import {
  listOrders,
  createOrder,
  updateOrder,
  listTariffVersions,
} from "../api/commerce";
import { listAdvertisers, listInventorySurfaces } from "../api/campaigns";
import type {
  CommerceOrderOut,
  CommerceOrderLineCreate,
  CommerceTariffVersionOut,
  AdvertiserOrganizationOut,
  InventorySurfaceOut,
} from "../api/types";

// ── Constants ──

const ORDER_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  offered: "Предложен",
  booked: "Забронирован",
  confirmed: "Подтверждён",
  closed: "Закрыт",
  cancelled: "Отменён",
};

const PAYMENT_STATUS_LABELS: Record<string, string> = {
  not_required: "Не требуется",
  unpaid: "Не оплачен",
  partial: "Частично",
  paid: "Оплачен",
  overdue: "Просрочен",
};

const TARIFF_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  active: "Активен",
  archived: "Архивный",
};

// Valid status transitions
const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  draft: ["offered", "cancelled"],
  offered: ["booked", "cancelled"],
  booked: ["confirmed", "cancelled"],
  confirmed: ["closed", "cancelled"],
};

const PAYMENT_STATUSES = [
  "not_required",
  "unpaid",
  "partial",
  "paid",
  "overdue",
];

// ── Helpers ──

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return iso.slice(0, 10);
}

// ── Styles ──

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
  gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
  gap: "var(--rmp-space-2)",
  padding: "var(--rmp-space-3)",
  border: "1px solid var(--rmp-border-strong)",
  borderRadius: "var(--rmp-radius-md)",
  marginBottom: "var(--rmp-space-3)",
};

// ── Create Order Form ──

interface CreateOrderFormState {
  advertiser_organization_id: string;
  tariff_version_id: string;
  surface_id: string;
  date_from: string;
  date_to: string;
}

const emptyForm = (): CreateOrderFormState => ({
  advertiser_organization_id: "",
  tariff_version_id: "",
  surface_id: "00000000-0000-0000-0000-000000000031", // SEED_SURFACE_ID
  date_from: new Date().toISOString().slice(0, 10),
  date_to: new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10),
});

interface CreateOrderFormProps {
  onSubmit: (data: CreateOrderFormState) => Promise<void>;
  onCancel: () => void;
  canManage: boolean;
  advertisers: AdvertiserOrganizationOut[];
  tariffs: CommerceTariffVersionOut[];
  surfaces: InventorySurfaceOut[];
}

function CreateOrderForm({ onSubmit, onCancel, advertisers, tariffs, surfaces }: CreateOrderFormProps) {
  const [form, setForm] = useState<CreateOrderFormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.advertiser_organization_id) return;
    if (!form.tariff_version_id) return;
    setSaving(true);
    setError(null);
    try {
      await onSubmit(form);
      setForm(emptyForm());
    } catch (err) {
      setError(formatApiError(err));
    } finally {
      setSaving(false);
    }
  }

  const today = new Date().toISOString().slice(0, 10);

  function advertiserLabel(a: AdvertiserOrganizationOut): string {
    return `${a.code} — ${a.display_name || a.legal_name}`;
  }

  function tariffLabel(t: CommerceTariffVersionOut): string {
    const status = TARIFF_STATUS_LABELS[t.status] ?? t.status;
    return `${t.code} — ${t.name} (${status})`;
  }

  function surfaceLabel(s: InventorySurfaceOut): string {
    const parts = [s.code];
    if (s.store_name) parts.push(s.store_name);
    parts.push(`${s.resolution_w}×${s.resolution_h}`);
    return parts.join(" — ");
  }

  return (
    <form
      data-testid="commerce-order-create-form"
      onSubmit={handleSubmit}
      style={formGrid}
    >
      <div>
        <label htmlFor="co-org">Организация *</label>
        {advertisers.length === 0 ? (
          <p style={{ color: "var(--rmp-text-muted)", fontSize: "var(--rmp-font-size-sm)", margin: "var(--rmp-space-1) 0" }}>
            Нет доступных организаций
          </p>
        ) : (
          <select
            id="co-org"
            data-testid="commerce-order-org-id"
            value={form.advertiser_organization_id}
            onChange={(e) => setForm({ ...form, advertiser_organization_id: e.target.value })}
            required
          >
            <option value="">— Выберите организацию —</option>
            {advertisers.map((a) => (
              <option key={a.id} value={a.id} data-testid={`commerce-order-org-option-${a.id}`}>
                {advertiserLabel(a)}
              </option>
            ))}
          </select>
        )}
      </div>
      <div>
        <label htmlFor="co-tariff">Тариф *</label>
        {tariffs.length === 0 ? (
          <p style={{ color: "var(--rmp-text-muted)", fontSize: "var(--rmp-font-size-sm)", margin: "var(--rmp-space-1) 0" }}>
            Нет доступных тарифов
          </p>
        ) : (
          <select
            id="co-tariff"
            data-testid="commerce-order-tariff-id"
            value={form.tariff_version_id}
            onChange={(e) => setForm({ ...form, tariff_version_id: e.target.value })}
            required
          >
            <option value="">— Выберите тариф —</option>
            {tariffs.map((t) => (
              <option key={t.id} value={t.id} data-testid={`commerce-order-tariff-option-${t.id}`}>
                {tariffLabel(t)}
              </option>
            ))}
          </select>
        )}
      </div>
      <div>
        <label htmlFor="co-surface">Поверхность *</label>
        {surfaces.length === 0 ? (
          <p style={{ color: "var(--rmp-text-muted)", fontSize: "var(--rmp-font-size-sm)", margin: "var(--rmp-space-1) 0" }}>
            Нет доступных поверхностей
          </p>
        ) : (
          <select
            id="co-surface"
            data-testid="commerce-order-surface-id"
            value={form.surface_id}
            onChange={(e) => setForm({ ...form, surface_id: e.target.value })}
            required
          >
            <option value="">— Выберите поверхность —</option>
            {surfaces.map((s) => (
              <option key={s.id} value={s.id} data-testid={`commerce-order-surface-option-${s.id}`}>
                {surfaceLabel(s)}
              </option>
            ))}
          </select>
        )}
      </div>
      <div>
        <label htmlFor="co-from">С *</label>
        <input
          id="co-from"
          type="date"
          data-testid="commerce-order-date-from"
          value={form.date_from}
          min={today}
          onChange={(e) => setForm({ ...form, date_from: e.target.value })}
          required
        />
      </div>
      <div>
        <label htmlFor="co-to">По *</label>
        <input
          id="co-to"
          type="date"
          data-testid="commerce-order-date-to"
          value={form.date_to}
          min={form.date_from || today}
          onChange={(e) => setForm({ ...form, date_to: e.target.value })}
          required
        />
      </div>
      <div style={{ display: "flex", alignItems: "flex-end", gap: "var(--rmp-space-2)" }}>
        <button type="submit" data-testid="commerce-order-submit" disabled={saving}>
          {saving ? "Создание…" : "Создать заказ"}
        </button>
        <button type="button" onClick={onCancel} disabled={saving}>
          Отмена
        </button>
      </div>
      {error && (
        <div
          data-testid="commerce-order-error"
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

// ── Order Detail ──

function OrderDetail({
  order,
  onStatusChange,
  onPaymentChange,
  canManage,
}: {
  order: CommerceOrderOut;
  onStatusChange: (newStatus: string) => Promise<void>;
  onPaymentChange: (paymentStatus: string) => Promise<void>;
  canManage: boolean;
}) {
  const [statusError, setStatusError] = useState<string | null>(null);
  const [payError, setPayError] = useState<string | null>(null);
  const [updating, setUpdating] = useState(false);

  const allowed = ALLOWED_TRANSITIONS[order.status] || [];

  async function handleStatusChange(newStatus: string) {
    setUpdating(true);
    setStatusError(null);
    try {
      await onStatusChange(newStatus);
    } catch (err) {
      setStatusError(formatApiError(err));
    } finally {
      setUpdating(false);
    }
  }

  async function handlePaymentChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const val = e.target.value;
    if (!val) return;
    setUpdating(true);
    setPayError(null);
    try {
      await onPaymentChange(val);
    } catch (err) {
      setPayError(formatApiError(err));
    } finally {
      setUpdating(false);
    }
  }

  return (
    <div data-testid="commerce-order-detail" style={{ marginTop: "var(--rmp-space-3)" }}>
      <h3 style={{ margin: "0 0 var(--rmp-space-3) 0" }}>
        Заказ {order.code}
      </h3>

      <div style={{ display: "flex", gap: "var(--rmp-space-4)", flexWrap: "wrap", marginBottom: "var(--rmp-space-3)" }}>
        <div>
          <strong>Статус:</strong>{" "}
          <span data-testid="commerce-order-status">
            {ORDER_STATUS_LABELS[order.status] ?? order.status}
          </span>
        </div>
        <div>
          <strong>Оплата:</strong>{" "}
          <span data-testid="commerce-order-payment-status">
            {PAYMENT_STATUS_LABELS[order.payment_status] ?? order.payment_status}
          </span>
        </div>
        <div>
          <strong>Сумма:</strong>{" "}
          <span data-testid="commerce-order-total">
            {order.total_amount?.toLocaleString("ru-RU") ?? "—"} {order.currency}
          </span>
        </div>
      </div>

      {canManage && (
        <div style={{ marginBottom: "var(--rmp-space-3)", display: "flex", gap: "var(--rmp-space-2)", flexWrap: "wrap", alignItems: "center" }}>
          {/* Status transitions */}
          {allowed.map((ns) => (
            <button
              key={ns}
              data-testid={`commerce-order-transition-${ns}`}
              disabled={updating}
              onClick={() => handleStatusChange(ns)}
              style={{ fontSize: "var(--rmp-font-size-sm)" }}
            >
              → {ORDER_STATUS_LABELS[ns] ?? ns}
            </button>
          ))}

          {/* Payment status */}
          <select
            data-testid="commerce-order-payment-select"
            value=""
            onChange={handlePaymentChange}
            disabled={updating}
            style={{ fontSize: "var(--rmp-font-size-sm)" }}
          >
            <option value="">Оплата…</option>
            {PAYMENT_STATUSES.map((ps) => (
              <option key={ps} value={ps}>
                {PAYMENT_STATUS_LABELS[ps] ?? ps}
              </option>
            ))}
          </select>
        </div>
      )}

      {statusError && (
        <div data-testid="commerce-order-status-error" style={{ color: "var(--rmp-danger-600)", fontSize: "var(--rmp-font-size-sm)", marginBottom: "var(--rmp-space-2)" }}>
          {statusError}
        </div>
      )}
      {payError && (
        <div data-testid="commerce-order-pay-error" style={{ color: "var(--rmp-danger-600)", fontSize: "var(--rmp-font-size-sm)", marginBottom: "var(--rmp-space-2)" }}>
          {payError}
        </div>
      )}

      {/* Lines table */}
      {order.lines.length > 0 && (
        <table style={tableStyle} data-testid="commerce-order-lines-table">
          <thead>
            <tr>
              <th style={thStyle}>Поверхность</th>
              <th style={thStyle}>Период</th>
              <th style={thStyle}>Дней</th>
              <th style={thStyle}>Цена/день</th>
              <th style={thStyle}>Сумма</th>
            </tr>
          </thead>
          <tbody>
            {order.lines.map((ln) => (
              <tr key={ln.id} data-testid={`commerce-order-line-${ln.id}`}>
                <td style={tdStyle}>
                  <code style={{ fontSize: "0.75rem" }}>
                    {ln.surface_id.slice(0, 12)}…
                  </code>
                </td>
                <td style={tdStyle}>
                  {fmtDate(ln.date_from)} – {fmtDate(ln.date_to)}
                </td>
                <td style={tdStyle}>{ln.quantity_days}</td>
                <td style={tdStyle}>
                  {ln.unit_price_amount.toLocaleString("ru-RU")}
                </td>
                <td style={tdStyle} data-testid={`commerce-order-line-amount-${ln.id}`}>
                  {ln.line_amount.toLocaleString("ru-RU")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Orders Tab ──

interface CommerceOrdersTabProps {
  canManage: boolean;
}

export default function CommerceOrdersTab({ canManage }: CommerceOrdersTabProps) {
  const [orders, setOrders] = useState<CommerceOrderOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<CommerceOrderOut | null>(null);

  // Reference data for selects
  const [advertisers, setAdvertisers] = useState<AdvertiserOrganizationOut[]>([]);
  const [tariffs, setTariffs] = useState<CommerceTariffVersionOut[]>([]);
  const [surfaces, setSurfaces] = useState<InventorySurfaceOut[]>([]);

  useEffect(() => {
    async function loadRefs() {
      const [adv, tar, sur] = await Promise.all([
        listAdvertisers().catch(() => [] as AdvertiserOrganizationOut[]),
        listTariffVersions().catch(() => [] as CommerceTariffVersionOut[]),
        listInventorySurfaces().catch(() => [] as InventorySurfaceOut[]),
      ]);
      setAdvertisers(adv);
      setTariffs(tar);
      setSurfaces(sur);
    }
    loadRefs();
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listOrders();
      setOrders(data);
    } catch (e) {
      setError(formatApiError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleCreate(form: CreateOrderFormState) {
    const lines: CommerceOrderLineCreate[] = [
      {
        surface_id: form.surface_id.trim(),
        date_from: form.date_from,
        date_to: form.date_to,
      },
    ];
    await createOrder({
      advertiser_organization_id: form.advertiser_organization_id.trim(),
      tariff_version_id: form.tariff_version_id || null,
      currency: "RUB",
      lines,
    });
    setShowCreate(false);
    await load();
  }

  async function handleStatusChange(orderId: string, newStatus: string) {
    const updated = await updateOrder(orderId, { new_status: newStatus });
    setSelectedOrder(updated);
    await load();
  }

  async function handlePaymentChange(orderId: string, paymentStatus: string) {
    const updated = await updateOrder(orderId, { payment_status: paymentStatus });
    setSelectedOrder(updated);
    await load();
  }

  return (
    <div>
      {canManage && !showCreate && (
        <button
          data-testid="commerce-order-create-open"
          onClick={() => setShowCreate(true)}
          style={{ marginBottom: "var(--rmp-space-3)" }}
        >
          + Создать заказ
        </button>
      )}

      {showCreate && (
        <CreateOrderForm
          onSubmit={handleCreate}
          onCancel={() => setShowCreate(false)}
          canManage={canManage}
          advertisers={advertisers}
          tariffs={tariffs}
          surfaces={surfaces}
        />
      )}

      {loading && <p>Загрузка заказов…</p>}

      {error && (
        <div style={{ color: "var(--rmp-danger-600)", marginBottom: "var(--rmp-space-3)" }}>
          {error}
        </div>
      )}

      {!loading && !error && orders.length === 0 && (
        <p style={{ color: "var(--rmp-text-secondary)" }}>
          Нет заказов. Создайте первый.
        </p>
      )}

      {orders.length > 0 && (
        <table style={tableStyle} data-testid="commerce-orders-table">
          <thead>
            <tr>
              <th style={thStyle}>Код</th>
              <th style={thStyle}>Статус</th>
              <th style={thStyle}>Оплата</th>
              <th style={thStyle}>Сумма</th>
              <th style={thStyle}>Создан</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr
                key={o.id}
                data-testid={`commerce-order-row-${o.id}`}
                style={{
                  cursor: "pointer",
                  background:
                    selectedOrder?.id === o.id
                      ? "var(--rmp-gray-100)"
                      : undefined,
                }}
                onClick={() =>
                  setSelectedOrder(selectedOrder?.id === o.id ? null : o)
                }
              >
                <td style={tdStyle}>
                  <code>{o.code}</code>
                </td>
                <td style={tdStyle}>
                  {ORDER_STATUS_LABELS[o.status] ?? o.status}
                </td>
                <td style={tdStyle}>
                  {PAYMENT_STATUS_LABELS[o.payment_status] ?? o.payment_status}
                </td>
                <td style={tdStyle}>
                  {o.total_amount?.toLocaleString("ru-RU") ?? "—"} {o.currency}
                </td>
                <td style={tdStyle}>{fmtDate(o.created_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedOrder && (
        <OrderDetail
          order={selectedOrder}
          onStatusChange={(ns) => handleStatusChange(selectedOrder.id, ns)}
          onPaymentChange={(ps) => handlePaymentChange(selectedOrder.id, ps)}
          canManage={canManage}
        />
      )}
    </div>
  );
}
