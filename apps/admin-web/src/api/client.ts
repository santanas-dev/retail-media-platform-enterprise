/**
 * API client for RMP Control API.
 *
 * Typed wrapper over fetch with:
 * - Authorization header injection
 * - JSON request/response
 * - 401 detection with callback
 * - Typed ApiError
 * - No token leakage in logs/UI
 *
 * Base URLs:
 *   AUTH_BASE_URL     = /api/v1/auth   (login, refresh, logout, me)
 *   IDENTITY_BASE_URL = /api/v1/identity (campaigns, advertisers, etc.)
 *
 * Cookie-based refresh token:
 *   login/refresh/logout use credentials: "include" so the HttpOnly
 *   refresh cookie flows automatically. The frontend never sees the
 *   refresh token.
 */

const AUTH_BASE_URL = "/api/v1/auth";
export const IDENTITY_BASE_URL = "/api/v1/identity";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as Record<string, unknown>).detail)
        : `HTTP ${status}`;
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

let _token: string | null = null;
let _onUnauthorized: (() => void) | null = null;

export function setToken(token: string | null) {
  _token = token;
}

export function getToken(): string | null {
  return _token;
}

export function onUnauthorized(cb: () => void) {
  _onUnauthorized = cb;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  baseUrl: string = IDENTITY_BASE_URL,
  credentials?: RequestCredentials,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  const init: RequestInit = {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  };
  if (credentials) {
    init.credentials = credentials;
  }

  const res = await fetch(`${baseUrl}${path}`, init);

  if (!res.ok) {
    if (res.status === 401 && _onUnauthorized) {
      _onUnauthorized();
    }
    let errorBody: unknown;
    try {
      errorBody = await res.json();
    } catch {
      errorBody = null;
    }
    throw new ApiError(res.status, errorBody);
  }

  // 204 No Content — return nothing
  if (res.status === 204) {
    return undefined as T;
  }
  return res.json();
}

// ── Public API ──

export const api = {
  // ── Identity-scoped (Bearer token) ──

  get<T>(path: string): Promise<T> {
    return request<T>("GET", path);
  },

  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("POST", path, body);
  },

  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PATCH", path, body);
  },

  put<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PUT", path, body);
  },

  del<T>(path: string): Promise<T> {
    return request<T>("DELETE", path);
  },

  // ── Auth (cookie-based refresh token) ──

  login(credentials: { username_or_email: string; password: string; auth_provider: string }) {
    return request<LoginResponse>(
      "POST",
      "/login",
      credentials,
      AUTH_BASE_URL,
      "include",
    );
  },

  refresh() {
    return request<RefreshResponse>(
      "POST",
      "/refresh",
      undefined,
      AUTH_BASE_URL,
      "include",
    );
  },

  logout() {
    return request<void>(
      "POST",
      "/logout",
      undefined,
      AUTH_BASE_URL,
      "include",
    );
  },

  getMe() {
    return request<MeResponse>("GET", "/me", undefined, AUTH_BASE_URL);
  },
};

// ── Response types — match backend schemas exactly ──

export interface UserRefOut {
  sub: string;
  auth_provider: string;
  username?: string;
  display_name?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: UserRefOut;
}

export interface RefreshResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface MeResponse {
  sub: string;
  auth_provider: string;
  username: string;
  display_name: string;
  permissions?: string[];
  must_change_password?: boolean;
}

// ── Audit ──

export interface AuditEventOut {
  id: string;
  actor_user_id: string | null;
  action: string;
  target_type: string;
  target_id: string | null;
  correlation_id: string | null;
  ip_address: string;
  details_json: unknown;
  created_at: string | null;
}

export interface PaginatedAuditEvents {
  items: AuditEventOut[];
  total: number;
  limit: number;
  offset: number;
}

// ── S-071 — Emergency ──

export interface EmergencyStatusOut {
  active: boolean;
  reason: string;
  activated_by: string | null;
  activated_at: string | null;
}

export interface DeviceOut {
  id: string;
  store_id: string;
  device_type_id: string;
  code: string;
  serial_number: string;
  os_version: string;
  ip_address: string;
  status: string;
  last_seen_at: string | null;
  current_manifest_id: string | null;
  cache_size_bytes: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface DeviceSummaryOut {
  total: number;
  active: number;
  inactive: number;
  error: number;
  unregistered: number;
}

export interface PaginatedDevices {
  items: DeviceOut[];
  total: number;
  limit: number;
  offset: number;
}

// ── BP-001 — Advertiser Applications ──

export interface AdvertiserApplicationOut {
  id: string;
  company_name: string;
  contact_name: string;
  email: string;
  phone: string;
  website: string;
  comment: string;
  consent: boolean;
  status: string;
  reviewer_id: string | null;
  review_reason: string | null;
  reviewed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PaginatedApplications {
  items: AdvertiserApplicationOut[];
  total: number;
  limit: number;
  offset: number;
}
