/**
 * Campaign API methods — typed wrappers over the identity endpoints.
 *
 * IMPORTANT: The backend does NOT have a dedicated /campaigns/:id endpoint.
 * Detail views join campaigns with related data client-side.
 *
 * All endpoints require campaigns.read permission (scoped + RLS).
 * 401 triggers the existing onUnauthorized → session clear flow.
 */

import { api } from "./client";
import type {
  CampaignOut,
  CampaignCreateRequest,
  CampaignFlightOut,
  CampaignFlightCreateRequest,
  CampaignFlightUpdateRequest,
  CampaignPlacementOut,
  CampaignPlacementCreateRequest,
  CampaignPlacementUpdateRequest,
  CampaignCreativeOut,
  CampaignCreativeCreateRequest,
  CreativeAssetOut,
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  CampaignApprovalOut,
  CampaignApprovalResponse,
  CampaignStatusHistoryOut,
  CampaignPopSummaryOut,
  CampaignPopByDayOut,
  CampaignPopBySurfaceOut,
} from "./types";

// ── Campaigns ──

/** Fetch all campaigns visible to the current user (RLS-scoped). */
export function listCampaigns(): Promise<CampaignOut[]> {
  return api.get<CampaignOut[]>("/campaigns");
}

/** Get a single campaign by ID from the list.
 *  Backend has no dedicated detail endpoint — we filter client-side. */
export async function getCampaign(id: string): Promise<CampaignOut | null> {
  const all = await listCampaigns();
  return all.find((c) => c.id === id) ?? null;
}

/** Create a draft campaign. Returns the created campaign with its ID. */
export function createCampaign(body: CampaignCreateRequest): Promise<CampaignOut> {
  return api.post<CampaignOut>("/campaigns", body);
}

// ── Flights ──

export function listFlights(): Promise<CampaignFlightOut[]> {
  return api.get<CampaignFlightOut[]>("/campaign-flights");
}

export async function getFlightsByCampaign(campaignId: string): Promise<CampaignFlightOut[]> {
  const all = await listFlights();
  return all.filter((f) => f.campaign_id === campaignId);
}

// ── Placements ──

export function listPlacements(): Promise<CampaignPlacementOut[]> {
  return api.get<CampaignPlacementOut[]>("/campaign-placements");
}

export async function getPlacementsByCampaign(campaignId: string): Promise<CampaignPlacementOut[]> {
  const all = await listPlacements();
  return all.filter((p) => p.campaign_id === campaignId);
}

// ── Creatives (links + assets) ──

export function listCampaignCreatives(): Promise<CampaignCreativeOut[]> {
  return api.get<CampaignCreativeOut[]>("/campaign-creatives");
}

export function listCreativeAssets(): Promise<CreativeAssetOut[]> {
  return api.get<CreativeAssetOut[]>("/creative-assets");
}

export async function getCreativesByCampaign(
  campaignId: string,
): Promise<Array<CampaignCreativeOut & { asset: CreativeAssetOut | null }>> {
  const [links, assets] = await Promise.all([
    listCampaignCreatives(),
    listCreativeAssets(),
  ]);
  const assetMap = new Map(assets.map((a) => [a.id, a]));
  return links
    .filter((l) => l.campaign_id === campaignId)
    .map((l) => ({ ...l, asset: assetMap.get(l.creative_asset_id) ?? null }));
}

// ── Advertiser entities (ID → name lookups) ──

export function listAdvertisers(): Promise<AdvertiserOrganizationOut[]> {
  return api.get<AdvertiserOrganizationOut[]>("/advertiser-organizations");
}

export function listBrands(): Promise<AdvertiserBrandOut[]> {
  return api.get<AdvertiserBrandOut[]>("/advertiser-brands");
}

export function listContracts(): Promise<AdvertiserContractOut[]> {
  return api.get<AdvertiserContractOut[]>("/advertiser-contracts");
}

// ── Campaign Mutations ──

export function createFlight(
  campaignId: string,
  body: CampaignFlightCreateRequest,
): Promise<CampaignFlightOut> {
  return api.post<CampaignFlightOut>(`/campaigns/${campaignId}/flights`, body);
}

export function updateFlight(
  campaignId: string,
  flightId: string,
  body: CampaignFlightUpdateRequest,
): Promise<CampaignFlightOut> {
  return api.patch<CampaignFlightOut>(
    `/campaigns/${campaignId}/flights/${flightId}`,
    body,
  );
}

export function createPlacement(
  campaignId: string,
  body: CampaignPlacementCreateRequest,
): Promise<CampaignPlacementOut> {
  return api.post<CampaignPlacementOut>(
    `/campaigns/${campaignId}/placements`,
    body,
  );
}

export function updatePlacement(
  campaignId: string,
  placementId: string,
  body: CampaignPlacementUpdateRequest,
): Promise<CampaignPlacementOut> {
  return api.patch<CampaignPlacementOut>(
    `/campaigns/${campaignId}/placements/${placementId}`,
    body,
  );
}

export function createCreative(
  campaignId: string,
  body: CampaignCreativeCreateRequest,
): Promise<CreativeAssetOut> {
  return api.post<CreativeAssetOut>(
    `/campaigns/${campaignId}/creatives`,
    body,
  );
}

export function requestApproval(
  campaignId: string,
): Promise<CampaignApprovalResponse> {
  return api.post<CampaignApprovalResponse>(
    `/campaigns/${campaignId}/request-approval`,
  );
}

// ── Approvals & History ──

export function listApprovals(): Promise<CampaignApprovalOut[]> {
  return api.get<CampaignApprovalOut[]>("/campaign-approvals");
}

export function listStatusHistory(): Promise<CampaignStatusHistoryOut[]> {
  return api.get<CampaignStatusHistoryOut[]>("/campaign-status-history");
}

export async function getApprovalsByCampaign(campaignId: string): Promise<CampaignApprovalOut[]> {
  const all = await listApprovals();
  return all.filter((a) => a.campaign_id === campaignId);
}

// ── PoP Reporting ──
// Note: Backend PoP endpoints may not yet be wired in control-api route tree;
// these stubs are ready for when /pop/* routes are available.

const POP_BASE = "/api/v1/pop";

let _popAvailable: boolean | null = null;

async function pop<T>(path: string): Promise<T | null> {
  if (_popAvailable === false) return null;
  try {
    const res = await fetch(`${POP_BASE}${path}`);
    if (!res.ok) {
      if (res.status === 404) {
        _popAvailable = false;
        return null;
      }
      return null;
    }
    _popAvailable = true;
    return res.json();
  } catch {
    _popAvailable = false;
    return null;
  }
}

export function getCampaignPopSummary(campaignId: string): Promise<CampaignPopSummaryOut | null> {
  return pop<CampaignPopSummaryOut>(`/campaigns/${campaignId}/pop-summary`);
}

export function getCampaignPopByDay(
  campaignId: string,
): Promise<CampaignPopByDayOut[] | null> {
  return pop<CampaignPopByDayOut[]>(
    `/campaigns/${campaignId}/pop-by-day?limit=30`,
  );
}

export function getCampaignPopBySurface(
  campaignId: string,
): Promise<CampaignPopBySurfaceOut[] | null> {
  return pop<CampaignPopBySurfaceOut[]>(
    `/campaigns/${campaignId}/pop-by-surface?limit=30`,
  );
}
