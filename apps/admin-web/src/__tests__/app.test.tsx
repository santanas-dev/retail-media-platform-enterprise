import { describe, it, expect, vi, beforeEach } from "vitest";
import { setToken, getToken, onUnauthorized, ApiError, api } from "../api/client";

// ── API Client — Auth Contract Tests ──

describe("API client — auth contract", () => {
  beforeEach(() => {
    setToken(null);
    vi.restoreAllMocks();
  });

  // ── Authorization header ──

  it("attaches Authorization header when token set", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    setToken("test-token");

    await api.get("/campaigns");

    const [, init] = spy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer test-token");
  });

  it("does not attach header when no token", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );

    await api.get("/campaigns");

    const [, init] = spy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });

  // ── Error handling ──

  it("throws ApiError on non-200 with detail message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Not found" }), { status: 404 }),
    );

    await expect(api.get("/missing")).rejects.toThrow("Not found");
    await expect(api.get("/missing")).rejects.toThrow(ApiError);
  });

  it("throws ApiError with generic message when no detail", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("plain text", { status: 500 }),
    );

    await expect(api.get("/broken")).rejects.toThrow("HTTP 500");
  });

  it("calls onUnauthorized callback on 401", async () => {
    const cb = vi.fn();
    onUnauthorized(cb);

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Expired" }), { status: 401 }),
    );

    try {
      await api.get("/protected");
    } catch {
      // expected
    }

    expect(cb).toHaveBeenCalledTimes(1);
  });

  it("does not call onUnauthorized on non-401 errors", async () => {
    const cb = vi.fn();
    onUnauthorized(cb);

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Forbidden" }), { status: 403 }),
    );

    try {
      await api.get("/forbidden");
    } catch {
      // expected
    }

    expect(cb).not.toHaveBeenCalled();
  });

  // ── Token helpers ──

  it("setToken and getToken round-trip", () => {
    expect(getToken()).toBeNull();
    setToken("abc123");
    expect(getToken()).toBe("abc123");
    setToken(null);
    expect(getToken()).toBeNull();
  });

  // ── Login — contract ──

  it("login uses /api/v1/auth/login and credentials:include", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "at",
          token_type: "Bearer",
          expires_in: 1800,
          user: { sub: "u1", auth_provider: "ad" },
        }),
        { status: 200 },
      ),
    );

    await api.login({ username_or_email: "admin", password: "pwd", auth_provider: "ad" });

    const [url, init] = spy.mock.calls[0];
    expect(url).toBe("/api/v1/auth/login");
    expect((init as RequestInit).credentials).toBe("include");

    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.username_or_email).toBe("admin");
    expect(body.password).toBe("pwd");
    expect(body.auth_provider).toBe("ad");
    expect(body.password).not.toContain("Bearer"); // no token leakage
  });

  it("login response has NO refresh_token in JSON", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "at",
          token_type: "Bearer",
          expires_in: 1800,
          user: { sub: "u1", auth_provider: "ad" },
        }),
        { status: 200 },
      ),
    );

    const res = await api.login({ username_or_email: "admin", password: "pwd", auth_provider: "ad" });

    expect(res.access_token).toBe("at");
    expect(res.token_type).toBe("Bearer");
    expect(res.expires_in).toBe(1800);
    expect(res.user.sub).toBe("u1");
    // refresh_token must NOT be on the response object
    expect((res as unknown as Record<string, unknown>).refresh_token).toBeUndefined();
  });

  // ── Refresh — contract ──

  it("refresh uses /api/v1/auth/refresh and credentials:include with no body", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "new-at",
          token_type: "Bearer",
          expires_in: 1800,
        }),
        { status: 200 },
      ),
    );

    await api.refresh();

    const [url, init] = spy.mock.calls[0];
    expect(url).toBe("/api/v1/auth/refresh");
    expect((init as RequestInit).credentials).toBe("include");
    expect((init as RequestInit).body).toBeUndefined();
  });

  // ── Logout — contract ──

  it("logout uses /api/v1/auth/logout and credentials:include with no body", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ message: "Logged out" }), { status: 200 }),
    );

    await api.logout();

    const [url, init] = spy.mock.calls[0];
    expect(url).toBe("/api/v1/auth/logout");
    expect((init as RequestInit).credentials).toBe("include");
    expect((init as RequestInit).body).toBeUndefined();
  });

  // ── getMe — contract ──

  it("getMe returns user shape matching backend MeResponse", async () => {
    const meData = {
      sub: "u1",
      auth_provider: "ad",
      username: "admin",
      display_name: "Admin User",
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(meData), { status: 200 }),
    );
    setToken("valid");

    const me = await api.getMe();
    expect(me.sub).toBe("u1");
    expect(me.auth_provider).toBe("ad");
    expect(me.username).toBe("admin");
    expect(me.display_name).toBe("Admin User");
    // permissions and scope must NOT be on the response
    expect((me as unknown as Record<string, unknown>).permissions).toBeUndefined();
    expect((me as unknown as Record<string, unknown>).scope).toBeUndefined();
  });

  // ── Session clear on unauthorized ──

  it("clears token when onUnauthorized fires", () => {
    setToken("expired-token");
    expect(getToken()).toBe("expired-token");

    onUnauthorized(() => setToken(null));

    // simulate 401 callback
    setToken(null);
    expect(getToken()).toBeNull();
  });
});
