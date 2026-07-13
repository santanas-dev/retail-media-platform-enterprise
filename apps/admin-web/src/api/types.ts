/**
 * Campaign domain types — matching backend package/domain/schemas.py.
 *
 * No PII, no storage secrets exposed. All fields are optional-read compatible
 * with backend DTOs using from_attributes=True.
 */

// ── Campaign ──

export interface CampaignOut {
  id: string;
  advertiser_organization_id: string;
  advertiser_brand_id: string | null;
  advertiser_contract_id: string;
  code: string;
  name: string;
  description: string | null;
  status: string;
  priority: number;
  budget_limit_amount: number | null;
  budget_limit_currency: string;
  start_at: string | null;
  end_at: string | null;
  timezone: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

// ── Campaign Flight ──

export interface CampaignFlightOut {
  id: string;
  campaign_id: string;
  name: string | null;
  start_at: string;
  end_at: string;
  dayparting_json: unknown | null;
  days_of_week: number[] | null;
  priority: number;
  created_at: string;
}

// ── Campaign Placement ──

export interface CampaignPlacementOut {
  id: string;
  campaign_id: string;
  display_surface_id: string | null;
  store_id: string | null;
  cluster_id: string | null;
  branch_id: string | null;
  share_of_voice_pct: number;
  max_impressions: number | null;
  impressions_delivered: number;
  status: string;
  created_at: string;
}

// ── Campaign Creative (link table) ──

export interface CampaignCreativeOut {
  id: string;
  campaign_id: string;
  creative_asset_id: string;
  sort_order: number;
  duration_override_ms: number | null;
  created_at: string;
}

// ── Creative Asset (metadata, no storage secrets) ──

export interface CreativeAssetOut {
  id: string;
  advertiser_organization_id: string;
  code: string;
  name: string;
  media_type: string;
  sha256_checksum: string;
  file_size_bytes: number;
  duration_ms: number | null;
  resolution_w: number | null;
  resolution_h: number | null;
  status: string;
  moderation_status: string;
  moderation_notes: string | null;
  created_at: string;
  updated_at: string;
}

// ── Advertiser Organization ──

export interface AdvertiserOrganizationOut {
  id: string;
  code: string;
  legal_name: string;
  display_name: string;
  status: string;
}

// ── Advertiser Brand ──

export interface AdvertiserBrandOut {
  id: string;
  advertiser_organization_id: string;
  code: string;
  name: string;
  description: string | null;
  status: string;
}

// ── Advertiser Contract ──

export interface AdvertiserContractOut {
  id: string;
  advertiser_organization_id: string;
  code: string;
  name: string;
  contract_number: string | null;
  budget_limit_amount: number | null;
  budget_limit_currency: string;
  valid_from: string | null;
  valid_until: string | null;
  status: string;
  terms_url: string | null;
}

// ── Advertiser Contact ──

export interface AdvertiserContactOut {
  id: string;
  advertiser_organization_id: string;
  contact_type: string;
  full_name: string;
  email: string;
  phone: string | null;
  is_primary: boolean;
  status: string;
}

// ── Advertiser User Membership ──

export interface AdvertiserUserMembershipOut {
  id: string;
  user_id: string;
  username: string;
  display_name: string;
  email: string | null;
  auth_provider: string;
  user_status: string;
  must_change_password: boolean;
  membership_status: string;
  membership_created_at: string | null;
}

// ── Advertiser Organization Detail ──

export interface AdvertiserOrganizationDetailOut {
  id: string;
  code: string;
  legal_name: string;
  display_name: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
}

// ── Campaign Approval ──

export interface CampaignApprovalOut {
  id: string;
  campaign_id: string;
  reviewed_by: string;
  action: string;
  reason: string | null;
  created_at: string;
}

// ── Campaign Status History ──

export interface CampaignStatusHistoryOut {
  id: string;
  campaign_id: string;
  changed_by: string;
  old_status: string;
  new_status: string;
  created_at: string;
}

// ── PoP Reporting ──
// Matches backend packages/domain/schemas.py exactly.

export interface CampaignPopSummaryOut {
  campaign_id: string;
  impressions_count: number;
  total_duration_ms: number;
  first_rendered_at: string | null;
  last_rendered_at: string | null;
  unique_devices: number;
  unique_surfaces: number;
}

export interface CampaignPopByDayOut {
  date: string; // YYYY-MM-DD
  impressions_count: number;
  total_duration_ms: number;
}

export interface CampaignPopBySurfaceOut {
  surface_id: string;
  impressions_count: number;
  total_duration_ms: number;
}

// ── S-009h: Reference data (branches, clusters, stores, surfaces) ──

export interface BranchOut {
  id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface ClusterOut {
  id: string;
  branch_id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface StoreOut {
  id: string;
  cluster_id: string;
  code: string;
  name: string;
  address: string;
  is_active: boolean;
}

export interface DisplaySurfaceRefOut {
  id: string;
  store_id: string;
  code: string;
  resolution_w: number;
  resolution_h: number;
  is_active: boolean;
}

// ── S-037: Inventory Management ──

export interface InventoryStoreOut {
  id: string;
  code: string;
  name: string;
  address: string;
  is_active: boolean;
  cluster_name: string | null;
  branch_name: string | null;
  surface_count: number;
}

export interface InventorySurfaceOut {
  id: string;
  code: string;
  store_id: string;
  store_code: string | null;
  store_name: string | null;
  resolution_w: number;
  resolution_h: number;
  is_active: boolean;
}

export interface InventorySurfacePatchRequest {
  is_active?: boolean;
}

// ── S-038: Campaign Approval Queue ──

export interface CampaignApprovalQueueItem {
  campaign_id: string;
  campaign_code: string;
  campaign_name: string;
  campaign_status: string;
  advertiser_org_id: string | null;
  advertiser_org_name: string | null;
  advertiser_brand_name: string | null;
  requested_at: string | null;
  requested_by: string | null;
  has_flight: boolean;
  has_placement: boolean;
  has_creative: boolean;
  all_creatives_ready: boolean;
  all_creatives_approved: boolean;
  rejection_reason: string | null;
}

// ── Helper: localized status labels ──

// ── Campaign Create Request (matches backend CampaignCreateRequest) ──

export interface CampaignCreateRequest {
  advertiser_organization_id: string;
  advertiser_brand_id: string | null;
  advertiser_contract_id: string;
  code: string;
  name: string;
  description: string | null;
  start_at: string | null;
  end_at: string | null;
  timezone: string;
  budget_limit_amount: number | null;
  budget_limit_currency: string;
  priority: number;
}

// ── Flight Mutation ──

export interface CampaignFlightCreateRequest {
  name: string | null;
  start_at: string;
  end_at: string;
  dayparting_json?: unknown;
  days_of_week?: number[];
  priority: number;
}

export interface CampaignFlightUpdateRequest {
  name?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  dayparting_json?: unknown;
  days_of_week?: number[];
  priority?: number;
}

// ── Placement Mutation ──

export interface CampaignPlacementCreateRequest {
  display_surface_id: string | null;
  store_id: string | null;
  cluster_id: string | null;
  branch_id: string | null;
  share_of_voice_pct: number;
  max_impressions: number | null;
}

export interface CampaignPlacementUpdateRequest {
  display_surface_id?: string | null;
  store_id?: string | null;
  cluster_id?: string | null;
  branch_id?: string | null;
  share_of_voice_pct?: number;
  max_impressions?: number | null;
}

// ── Creative Mutation (creates new asset + attaches to campaign) ──

export interface CampaignCreativeCreateRequest {
  code: string;
  name: string;
  media_type: string;
  sha256_checksum?: string;
  file_size_bytes?: number | null;
  duration_ms: number | null;
  resolution_w: number | null;
  resolution_h: number | null;
  sort_order: number;
  duration_override_ms: number | null;
}

export interface CampaignCreativeAttachRequest {
  creative_asset_id: string;
  sort_order: number;
}

// ── S-009j: Standalone creative asset creation (library intake) ──

export interface CreativeAssetCreateRequest {
  code: string;
  name: string;
  media_type: string;
  advertiser_organization_id?: string;
  sha256_checksum?: string;
  file_size_bytes?: number | null;
  resolution_w?: number | null;
  resolution_h?: number | null;
  duration_ms?: number | null;
}

// ── Approval ──

export interface CampaignApprovalResponse {
  message: string;
  campaign_id: string;
  old_status: string;
  new_status: string;
}

export interface CampaignRejectRequest {
  reason: string;
}

// ── S-017: Creative Upload ──

export interface UploadIntentRequest {
  filename: string;
  content_type: string;
  content_length: number;
}

export interface UploadIntentResponse {
  upload_id: string;
  upload_url: string;
  method: string;
  headers: Record<string, string>;
  expires_at: string;
}

export interface CompleteUploadRequest {
  upload_id: string;
}

export interface CompleteUploadResponse {
  asset_id: string;
  sha256_checksum: string;
  file_size_bytes: number;
  status: string;
  moderation_status: string;
}

// ── Helper: localized status labels ──

export const STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  pending_approval: "На согласовании",
  approved: "Согласована",
  published: "Опубликована",
  active: "Активна",
  paused: "Приостановлена",
  completed: "Завершена",
  rejected: "Отклонена",
  archived: "Архив",
  metadata_only: "Ожидает загрузки",
  ready: "Готов",
};

export function statusLabel(s: string): string {
  return STATUS_LABELS[s] ?? s;
}

export const STATUS_COLORS: Record<string, string> = {
  draft: "#64748b",
  pending_approval: "#d97706",
  approved: "#2563eb",
  published: "#059669",
  active: "#059669",
  paused: "#9333ea",
  completed: "#6b7280",
  rejected: "#dc2626",
  archived: "#9ca3af",
};

export function statusColor(s: string): string {
  return STATUS_COLORS[s] ?? "#6b7280";
}


// ── S-033: Admin User Management ──

export interface UserOut {
  id: string;
  code: string;
  username: string;
  email: string | null;
  display_name: string;
  auth_provider: string;
  status: string;
  is_break_glass: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface PaginatedUsers {
  items: UserOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface UserRoleAssignmentOut {
  id: string;
  role_id: string;
  role_code: string;
  role_name: string;
  scope_type: string | null;
  scope_id: string | null;
}

export interface UserDetailOut extends UserOut {
  must_change_password: boolean;
  roles: UserRoleAssignmentOut[];
}

// ── S-036: Creative Moderation ──

export interface CreativeModerationQueueItem {
  id: string;
  advertiser_organization_id: string;
  code: string;
  name: string;
  media_type: string;
  file_size_bytes: number;
  duration_ms: number | null;
  resolution_w: number | null;
  resolution_h: number | null;
  status: string;
  moderation_status: string;
  moderation_notes: string | null;
  created_at: string;
  updated_at: string;
  advertiser_name: string | null;
  advertiser_code: string | null;
}

export interface CreativeRejectRequest {
  reason: string;
}

export interface CreativeModerationResponse {
  asset_id: string;
  moderation_status: string;
  message: string;
}

export const MODERATION_STATUS_LABELS: Record<string, string> = {
  pending_review: "На проверке",
  approved: "Одобрен",
  rejected: "Отклонён",
};

export function moderationStatusLabel(s: string): string {
  return MODERATION_STATUS_LABELS[s] ?? s;
}

// ── S-039: Advertiser contact / auth / membership labels ──

export const CONTACT_TYPE_LABELS: Record<string, string> = {
  primary: "Основной",
  finance: "Финансовый",
  technical: "Технический",
  legal: "Юридический",
  marketing: "Маркетинговый",
};

export function contactTypeLabel(t: string): string {
  return CONTACT_TYPE_LABELS[t] ?? t;
}

export const AUTH_PROVIDER_LABELS: Record<string, string> = {
  local: "Локальная",
  local_advertiser: "Локальная (рекламодатель)",
  ad: "Active Directory",
  break_glass: "Аварийный доступ",
};

export function authProviderLabel(p: string): string {
  return AUTH_PROVIDER_LABELS[p] ?? p;
}
