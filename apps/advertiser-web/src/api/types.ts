/**
 * Campaign domain types — matching backend package/domain/schemas.py.
 *
 * No PII, no storage secrets exposed. All fields are optional-read compatible
 * with backend DTOs using from_attributes=True.
 */

// ── Pagination ──

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

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
  status: string;
}

// ── Advertiser Contract ──

export interface AdvertiserContractOut {
  id: string;
  advertiser_organization_id: string;
  code: string;
  name: string | null;
  budget_limit_amount: number | null;
  budget_limit_currency: string;
  valid_from: string;
  valid_until: string | null;
  status: string;
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

// ── Campaign Approval ──

export interface CampaignApprovalOut {
  id: string;
  campaign_id: string;
  requested_by: string;
  requested_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  decision: string | null;
  rejection_reason: string | null;
  created_at: string;
}

// ── Campaign Brief (BP-004) ──

export interface CampaignBriefOut {
  id: string;
  advertiser_organization_id: string;
  title: string;
  objective: string | null;
  product_category: string | null;
  target_period_from: string | null;
  target_period_to: string | null;
  budget_amount: number | null;
  budget_currency: string;
  preferred_channels: string | null;
  comment: string | null;
  status: string;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CampaignBriefCreateRequest {
  title: string;
  objective?: string;
  product_category?: string;
  target_period_from?: string;
  target_period_to?: string;
  budget_amount?: number;
  budget_currency?: string;
  preferred_channels?: string;
  comment?: string;
}

export interface CampaignBriefUpdateRequest {
  title?: string;
  objective?: string;
  product_category?: string;
  target_period_from?: string;
  target_period_to?: string;
  budget_amount?: number;
  budget_currency?: string;
  preferred_channels?: string;
  comment?: string;
}

export const BRIEF_STATUS_LABELS: Record<string, string> = {
  draft: "Черновик",
  submitted: "На рассмотрении",
  reviewing: "На проверке",
  accepted: "Принята",
  rejected: "Отклонена",
};

// ── Campaign Status History ──

export interface CampaignStatusHistoryOut {
  id: string;
  campaign_id: string;
  old_status: string | null;
  new_status: string;
  changed_by: string;
  changed_at: string;
  reason: string | null;
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

// ── Campaign Update Request (matches backend CampaignUpdateRequest, all optional) ──

export interface CampaignUpdateRequest {
  advertiser_brand_id?: string | null;
  advertiser_contract_id?: string;
  code?: string;
  name?: string;
  description?: string | null;
  start_at?: string | null;
  end_at?: string | null;
  timezone?: string;
  budget_limit_amount?: number | null;
  budget_limit_currency?: string;
  priority?: number;
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

// ── Creative Asset Library / Upload (S-023c) ──

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

// Human-friendly media type labels
export const MEDIA_TYPE_OPTIONS: { value: string; label: string }[] = [
  { value: "image/png", label: "Изображение (PNG)" },
  { value: "image/jpeg", label: "Изображение (JPEG)" },
  { value: "image/gif", label: "Изображение (GIF)" },
  { value: "image/webp", label: "Изображение (WebP)" },
  { value: "video/mp4", label: "Видео (MP4)" },
  { value: "video/webm", label: "Видео (WebM)" },
  { value: "text/html", label: "HTML" },
  { value: "application/octet-stream", label: "Прочее" },
];

export function mediaTypeLabel(mt: string): string {
  return MEDIA_TYPE_OPTIONS.find((o) => o.value === mt)?.label ?? mt;
}

// ── Helper: contact type labels ──

export const CONTACT_TYPE_LABELS: Record<string, string> = {
  primary: "Основной",
  billing: "Бухгалтерия",
  technical: "Технический",
  emergency: "Аварийный",
};

export function contactTypeLabel(ct: string): string {
  return CONTACT_TYPE_LABELS[ct] ?? ct;
}

// ── Helper: auth provider labels ──

export const AUTH_PROVIDER_LABELS: Record<string, string> = {
  local_advertiser: "Локальная учётная запись",
  local_break_glass: "Администратор",
  ad: "Active Directory",
};

export function authProviderLabel(ap: string): string {
  return AUTH_PROVIDER_LABELS[ap] ?? ap;
}

// ── Helper: timezone labels ──

export const TIMEZONE_LABELS: Record<string, string> = {
  "Europe/Moscow": "Москва (GMT+3)",
  "Europe/Kaliningrad": "Калининград (GMT+2)",
  "Europe/Samara": "Самара (GMT+4)",
  "Asia/Yekaterinburg": "Екатеринбург (GMT+5)",
  "Asia/Omsk": "Омск (GMT+6)",
  "Asia/Krasnoyarsk": "Красноярск (GMT+7)",
  "Asia/Irkutsk": "Иркутск (GMT+8)",
  "Asia/Vladivostok": "Владивосток (GMT+10)",
};

export function timezoneLabel(tz: string): string {
  return TIMEZONE_LABELS[tz] ?? tz;
}

// ── Helper: surface display ──

export function surfaceLabel(id: string, code?: string): string {
  if (code) return code;
  // Truncate UUID — show last 8 chars as readable reference
  return `Поверхность ${id.slice(-8)}`;
}

// ── S-036: Helper: moderation status ──

export const MODERATION_STATUS_LABELS: Record<string, string> = {
  pending_review: "На проверке",
  approved: "Одобрен",
  rejected: "Отклонён",
};

export function moderationStatusLabel(s: string): string {
  return MODERATION_STATUS_LABELS[s] ?? s;
}
