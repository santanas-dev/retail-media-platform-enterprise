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

  changePassword(currentPassword: string, newPassword: string) {
    return request<{ message: string }>(
      "POST",
      "/change-password",
      { current_password: currentPassword, new_password: newPassword },
      AUTH_BASE_URL,
    );
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
  advertiser_organization_id?: string | null;
  advertiser_organization?: {
    id: string;
    code: string;
    legal_name: string;
    display_name: string;
    status: string;
  } | null;
}
