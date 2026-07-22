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
  CreativeAssetCreateRequest,
  AdvertiserOrganizationOut,
  AdvertiserOrganizationDetailOut,
  AdvertiserBrandOut,
  AdvertiserContractOut,
  AdvertiserContactOut,
  AdvertiserUserMembershipOut,
  CampaignApprovalOut,
  CampaignApprovalResponse,
  CampaignStatusHistoryOut,
  CampaignPopSummaryOut,
  CampaignPopByDayOut,
  CampaignPopBySurfaceOut,
  BranchOut,
  ClusterOut,
  StoreOut,
  DisplaySurfaceRefOut,
  CampaignRejectRequest,
  CampaignCreativeAttachRequest,
  PaginatedResponse,
  InventoryAvailabilityRequest,
  InventoryAvailabilityResponse,
  InventoryConflictCheckRequest,
  InventoryConflictCheckResponse,
  InventoryAlternativesRequest,
  InventoryAlternativesResponse,
  InventoryRuleOut,
  InventoryRuleCreate,
  InventoryRuleUpdate,
  CampaignInventoryReservationsResponse,
  InventorySimulationResponse,
} from "./types";

// ── Campaigns ──

/** Fetch campaigns with pagination. */
export function listCampaigns(
  limit = 50,
  offset = 0,
): Promise<PaginatedResponse<CampaignOut>> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return api.get<PaginatedResponse<CampaignOut>>(`/campaigns?${params}`);
}

/** Get a single campaign by ID — fetches from first page and filters client-side.
 *  Temporary: will be replaced by dedicated detail endpoint (S-XXX). */
export async function getCampaign(id: string): Promise<CampaignOut | null> {
  const page = await listCampaigns(200, 0);
  return page.items.find((c) => c.id === id) ?? null;
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

export function createAdvertiserOrganization(body: {
  code: string;
  legal_name: string;
  display_name: string;
}): Promise<AdvertiserOrganizationOut> {
  return api.post<AdvertiserOrganizationOut>("/advertiser-organizations", body);
}

export function listBrands(): Promise<AdvertiserBrandOut[]> {
  return api.get<AdvertiserBrandOut[]>("/advertiser-brands");
}

export function listContracts(): Promise<AdvertiserContractOut[]> {
  return api.get<AdvertiserContractOut[]>("/advertiser-contracts");
}

// ── S-039: Advertiser detail + memberships ──

export function getAdvertiserDetail(orgId: string): Promise<AdvertiserOrganizationDetailOut> {
  return api.get<AdvertiserOrganizationDetailOut>(`/advertiser-organizations/${orgId}`);
}

export function listBrandsByOrg(orgId: string): Promise<AdvertiserBrandOut[]> {
  return api.get<AdvertiserBrandOut[]>(`/advertiser-brands-by-org?advertiser_organization_id=${orgId}`);
}

export function listContractsByOrg(orgId: string): Promise<AdvertiserContractOut[]> {
  return api.get<AdvertiserContractOut[]>(`/advertiser-contracts-by-org?advertiser_organization_id=${orgId}`);
}

export function listContactsByOrg(orgId: string): Promise<AdvertiserContactOut[]> {
  return api.get<AdvertiserContactOut[]>(`/advertiser-contacts-by-org?advertiser_organization_id=${orgId}`);
}

export function listMemberships(orgId: string): Promise<AdvertiserUserMembershipOut[]> {
  return api.get<AdvertiserUserMembershipOut[]>(`/advertiser-user-memberships?advertiser_organization_id=${orgId}`);
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

export function attachCreative(
  campaignId: string,
  body: CampaignCreativeAttachRequest,
): Promise<CreativeAssetOut> {
  return api.post<CreativeAssetOut>(
    `/campaigns/${campaignId}/creatives/attach`,
    body,
  );
}

// ── S-009j: Standalone creative asset creation (library intake) ──

export function createCreativeAsset(
  body: CreativeAssetCreateRequest,
): Promise<CreativeAssetOut> {
  return api.post<CreativeAssetOut>("/creative-assets", body);
}

export function requestApproval(
  campaignId: string,
): Promise<CampaignApprovalResponse> {
  return api.post<CampaignApprovalResponse>(
    `/campaigns/${campaignId}/request-approval`,
  );
}

export function approveCampaign(
  campaignId: string,
): Promise<CampaignApprovalResponse> {
  return api.post<CampaignApprovalResponse>(
    `/campaigns/${campaignId}/approve`,
  );
}

export function rejectCampaign(
  campaignId: string,
  body: CampaignRejectRequest,
): Promise<CampaignApprovalResponse> {
  return api.post<CampaignApprovalResponse>(
    `/campaigns/${campaignId}/reject`,
    body,
  );
}

// ── Approvals & History ──

export function listApprovals(): Promise<CampaignApprovalOut[]> {
  return api.get<CampaignApprovalOut[]>("/campaign-approvals");
}

// ── S-038: Campaign Approval Queue ──

import type { CampaignApprovalQueueItem } from "./types";

export function listApprovalQueue(
  status = "pending_approval",
  limit = 50,
  offset = 0,
): Promise<PaginatedResponse<CampaignApprovalQueueItem>> {
  const params = new URLSearchParams();
  if (status !== "pending_approval") {
    params.set("status", status);
  }
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return api.get<PaginatedResponse<CampaignApprovalQueueItem>>(
    `/campaigns/approval-queue?${params}`,
  );
}

export function listStatusHistory(): Promise<CampaignStatusHistoryOut[]> {
  return api.get<CampaignStatusHistoryOut[]>("/campaign-status-history");
}

export async function getApprovalsByCampaign(campaignId: string): Promise<CampaignApprovalOut[]> {
  const all = await listApprovals();
  return all.filter((a) => a.campaign_id === campaignId);
}

// ── PoP Reporting ──
// Backend endpoints are on identity router:
//   GET /api/v1/identity/campaigns/{id}/pop/summary
//   GET /api/v1/identity/campaigns/{id}/pop/by-day
//   GET /api/v1/identity/campaigns/{id}/pop/by-surface
// All require campaigns.read permission + RLS scope.

export function getCampaignPopSummary(campaignId: string): Promise<CampaignPopSummaryOut> {
  return api.get<CampaignPopSummaryOut>(`/campaigns/${campaignId}/pop/summary`);
}

export function getCampaignPopByDay(campaignId: string): Promise<CampaignPopByDayOut[]> {
  return api.get<CampaignPopByDayOut[]>(`/campaigns/${campaignId}/pop/by-day`);
}

export function getCampaignPopBySurface(campaignId: string): Promise<CampaignPopBySurfaceOut[]> {
  return api.get<CampaignPopBySurfaceOut[]>(`/campaigns/${campaignId}/pop/by-surface`);
}

// ── S-009h: Reference data (branches, clusters, stores, surfaces) ──
// Backend endpoints: GET /api/v1/identity/branches, /clusters, /stores, /display-surfaces
// All require campaigns.read permission + RLS.

export function listBranches(): Promise<BranchOut[]> {
  return api.get<BranchOut[]>("/branches");
}

export function listClusters(): Promise<ClusterOut[]> {
  return api.get<ClusterOut[]>("/clusters");
}

export function listStores(): Promise<StoreOut[]> {
  return api.get<StoreOut[]>("/stores");
}

export function listDisplaySurfaces(): Promise<DisplaySurfaceRefOut[]> {
  return api.get<DisplaySurfaceRefOut[]>("/display-surfaces");
}

// ── S-017: Creative Upload (presigned URL flow) ──

import type {
  UploadIntentRequest,
  UploadIntentResponse,
  CompleteUploadRequest,
  CompleteUploadResponse,
} from "./types";

export function createUploadIntent(
  assetId: string,
  body: UploadIntentRequest,
): Promise<UploadIntentResponse> {
  return api.post<UploadIntentResponse>(
    `/creative-assets/${assetId}/upload-intent`,
    body,
  );
}

export function completeUpload(
  assetId: string,
  body: CompleteUploadRequest,
): Promise<CompleteUploadResponse> {
  return api.post<CompleteUploadResponse>(
    `/creative-assets/${assetId}/complete-upload`,
    body,
  );
}

// ── S-036: Creative Moderation ──

import type {
  CreativeModerationQueueItem,
  CreativeRejectRequest,
  CreativeModerationResponse,
} from "./types";

export function listModerationQueue(
  moderationStatus = "pending_review",
  limit = 50,
  offset = 0,
): Promise<PaginatedResponse<CreativeModerationQueueItem>> {
  const params = new URLSearchParams();
  if (moderationStatus !== "pending_review") {
    params.set("moderation_status", moderationStatus);
  }
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  return api.get<PaginatedResponse<CreativeModerationQueueItem>>(
    `/creative-assets/moderation-queue?${params}`,
  );
}

export function approveCreative(
  assetId: string,
): Promise<CreativeModerationResponse> {
  return api.post<CreativeModerationResponse>(
    `/creative-assets/${assetId}/approve`,
  );
}

export function rejectCreative(
  assetId: string,
  body: CreativeRejectRequest,
): Promise<CreativeModerationResponse> {
  return api.post<CreativeModerationResponse>(
    `/creative-assets/${assetId}/reject`,
    body,
  );
}

export async function uploadFileToPresignedUrl(
  uploadUrl: string,
  file: File,
  headers: Record<string, string>,
  onProgress?: (uploaded: number, total: number) => void,
): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", uploadUrl);
    for (const [k, v] of Object.entries(headers)) {
      xhr.setRequestHeader(k, v);
    }
    // Intentionally do NOT set Authorization — presigned URL is self-authenticating
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(e.loaded, e.total);
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Upload failed: HTTP ${xhr.status}`));
    };
    xhr.onerror = () => reject(new Error("Сетевая ошибка при загрузке файла"));
    xhr.send(file);
  });
}

// ── S-078: Inventory Availability ──

export function checkAvailability(
  body: InventoryAvailabilityRequest,
): Promise<InventoryAvailabilityResponse> {
  return api.post<InventoryAvailabilityResponse>("/inventory/availability", body);
}

// ── S-080: Inventory Conflicts ──

export function checkConflicts(
  body: InventoryConflictCheckRequest,
): Promise<InventoryConflictCheckResponse> {
  return api.post<InventoryConflictCheckResponse>("/inventory/conflicts/check", body);
}

export function getCampaignInventoryConflicts(
  campaignId: string,
): Promise<InventoryConflictCheckResponse> {
  return api.get<InventoryConflictCheckResponse>(
    `/campaigns/${campaignId}/inventory-conflicts`,
  );
}

// ── S-079: Inventory Reservations ──

export function getCampaignInventoryReservations(
  campaignId: string,
): Promise<CampaignInventoryReservationsResponse> {
  return api.get<CampaignInventoryReservationsResponse>(
    `/campaigns/${campaignId}/inventory-reservations`,
  );
}

// ── S-087: Inventory Alternatives ──

export function suggestAlternatives(
  body: InventoryAlternativesRequest,
): Promise<InventoryAlternativesResponse> {
  return api.post<InventoryAlternativesResponse>("/inventory/alternatives", body);
}

// ── S-088: Inventory Rules ──

export function listRules(): Promise<InventoryRuleOut[]> {
  return api.get<InventoryRuleOut[]>("/inventory/rules");
}

export function createRule(body: InventoryRuleCreate): Promise<InventoryRuleOut> {
  return api.post<InventoryRuleOut>("/inventory/rules", body);
}

export function updateRule(ruleId: string, body: InventoryRuleUpdate): Promise<InventoryRuleOut> {
  return api.patch<InventoryRuleOut>(`/inventory/rules/${ruleId}`, body);
}

export function activateRule(ruleId: string): Promise<InventoryRuleOut> {
  return api.post<InventoryRuleOut>(`/inventory/rules/${ruleId}/activate`, {});
}

export function deactivateRule(ruleId: string): Promise<InventoryRuleOut> {
  return api.post<InventoryRuleOut>(`/inventory/rules/${ruleId}/deactivate`, {});
}

// ── S-089: Inventory Simulation ──

export function simulateInventory(
  campaignId: string,
): Promise<InventorySimulationResponse> {
  return api.post<InventorySimulationResponse>("/inventory/simulate", {
    campaign_id: campaignId,
  });
}
