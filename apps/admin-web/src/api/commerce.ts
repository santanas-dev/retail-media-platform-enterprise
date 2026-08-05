/**
 * Commerce API methods — tariff/price management.
 *
 * COMMERCE-CONTUR2-001A3a: admin-web tariff + price UI.
 */
import { api } from "./client";
import type {
  CommerceTariffVersionOut,
  CommerceTariffVersionCreate,
  CommerceTariffVersionUpdate,
  CommercePriceItemOut,
  CommercePriceItemCreate,
  CommercePriceItemUpdate,
} from "./types";

// ── Tariff versions ──

export function listTariffVersions(): Promise<CommerceTariffVersionOut[]> {
  return api.get<CommerceTariffVersionOut[]>("/commerce/tariff-versions");
}

export function createTariffVersion(
  body: CommerceTariffVersionCreate,
): Promise<CommerceTariffVersionOut> {
  return api.post<CommerceTariffVersionOut>("/commerce/tariff-versions", body);
}

export function updateTariffVersion(
  tariffId: string,
  body: CommerceTariffVersionUpdate,
): Promise<CommerceTariffVersionOut> {
  return api.patch<CommerceTariffVersionOut>(
    `/commerce/tariff-versions/${tariffId}`,
    body,
  );
}

// ── Price items ──

export function listPriceItems(
  tariffVersionId: string,
): Promise<CommercePriceItemOut[]> {
  return api.get<CommercePriceItemOut[]>(
    `/commerce/price-items?tariff_version_id=${encodeURIComponent(tariffVersionId)}`,
  );
}

export function createPriceItem(
  tariffVersionId: string,
  body: CommercePriceItemCreate,
): Promise<CommercePriceItemOut> {
  return api.post<CommercePriceItemOut>(
    `/commerce/price-items?tariff_version_id=${encodeURIComponent(tariffVersionId)}`,
    body,
  );
}

export function updatePriceItem(
  priceItemId: string,
  body: CommercePriceItemUpdate,
): Promise<CommercePriceItemOut> {
  return api.patch<CommercePriceItemOut>(
    `/commerce/price-items/${priceItemId}`,
    body,
  );
}

// ── Orders ──

import type {
  CommerceOrderOut,
  CommerceOrderCreate,
  CommerceOrderUpdate,
  CommerceOrderLineCreate,
} from "./types";

export function listOrders(): Promise<CommerceOrderOut[]> {
  return api.get<CommerceOrderOut[]>("/commerce/orders");
}

export function getOrder(orderId: string): Promise<CommerceOrderOut> {
  return api.get<CommerceOrderOut>(`/commerce/orders/${orderId}`);
}

export function createOrder(
  body: CommerceOrderCreate,
): Promise<CommerceOrderOut> {
  return api.post<CommerceOrderOut>("/commerce/orders", body);
}

export function updateOrder(
  orderId: string,
  body: CommerceOrderUpdate,
): Promise<CommerceOrderOut> {
  return api.patch<CommerceOrderOut>(
    `/commerce/orders/${orderId}`,
    body,
  );
}
