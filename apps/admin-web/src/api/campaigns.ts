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
  CampaignFlightOut,
  CampaignPlacementOut,
  CampaignCreativeOut,
  CreativeAssetOut,
  AdvertiserOrganizationOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  CampaignApprovalOut,
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
