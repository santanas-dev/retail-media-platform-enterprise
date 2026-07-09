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

// ── PoP Reporting (Phase 4.3b) ──

export interface CampaignPopSummaryOut {
  campaign_id: string;
  campaign_code: string;
  campaign_name: string;
  total_impressions: number;
  total_play_time_ms: number;
  unique_devices: number;
  unique_stores: number;
  last_play_at: string | null;
}

export interface CampaignPopByDayOut {
  campaign_id: string;
  date: string;
  impressions: number;
  play_time_ms: number;
}

export interface CampaignPopBySurfaceOut {
  campaign_id: string;
  display_surface_id: string;
  surface_code: string | null;
  impressions: number;
  play_time_ms: number;
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
