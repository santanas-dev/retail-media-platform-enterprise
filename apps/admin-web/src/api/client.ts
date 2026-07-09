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
 * Routes: /api/v1/auth/* (login, me), /api/v1/identity/* (campaigns, etc.)
 */

const BASE_URL = import.meta.env.VITE_API_BASE || "/api/v1";

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
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (_token) {
    headers["Authorization"] = `Bearer ${_token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

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
  get<T>(path: string): Promise<T> {
    return request<T>("GET", path);
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("POST", path, body);
  },
  patch<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("PATCH", path, body);
  },

  // ── Auth ──

  login(credentials: { username: string; password: string }) {
    return request<LoginResponse>("POST", "/auth/login", credentials);
  },

  refresh(refreshToken: string) {
    return request<LoginResponse>("POST", "/auth/refresh", { refresh_token: refreshToken });
  },

  logout(refreshToken: string) {
    return request<void>("POST", "/auth/logout", { refresh_token: refreshToken });
  },

  getMe() {
    return request<MeResponse>("GET", "/auth/me");
  },
};

// ── Response types ──

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface MeResponse {
  sub: string;
  username: string;
  display_name: string;
  permissions: string[];
  scope: {
    is_admin: boolean;
    advertiser_scope_ids: string[];
  };
}
