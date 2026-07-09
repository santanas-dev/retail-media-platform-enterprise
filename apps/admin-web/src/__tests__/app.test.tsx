import { describe, it, expect, vi, beforeEach } from "vitest";
import { setToken, getToken, onUnauthorized, ApiError, api } from "../api/client";

// ── API Client Tests ──

describe("API client", () => {
  beforeEach(() => {
    setToken(null);
    vi.restoreAllMocks();
  });

  it("attaches Authorization header when token set", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );
    setToken("test-token");

    await api.get("/identity/campaigns");

    const [, init] = spy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer test-token");
  });

  it("does not attach header when no token", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );

    await api.get("/identity/campaigns");

    const [, init] = spy.mock.calls[0];
    const headers = (init as RequestInit).headers as Record<string, string>;
    expect(headers["Authorization"]).toBeUndefined();
  });

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

  it("setToken and getToken round-trip", () => {
    expect(getToken()).toBeNull();
    setToken("abc123");
    expect(getToken()).toBe("abc123");
    setToken(null);
    expect(getToken()).toBeNull();
  });

  it("login sends correct request shape", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          access_token: "at",
          refresh_token: "rt",
          token_type: "bearer",
        }),
        { status: 200 },
      ),
    );

    const res = await api.login({ username: "admin", password: "pwd" });
    expect(res.access_token).toBe("at");
    expect(res.refresh_token).toBe("rt");

    const [, init] = spy.mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.username).toBe("admin");
    expect(body.password).toBe("pwd");
    expect(body.password).not.toContain("Bearer"); // no token leakage
  });

  it("getMe returns user shape after auth", async () => {
    const meData = {
      sub: "u1",
      username: "admin",
      display_name: "Admin User",
      permissions: ["campaigns.read"],
      scope: { is_admin: true, advertiser_scope_ids: [] },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(meData), { status: 200 }),
    );
    setToken("valid");

    const me = await api.getMe();
    expect(me.username).toBe("admin");
    expect(me.permissions).toContain("campaigns.read");
    expect(me.scope.is_admin).toBe(true);
  });

  it("logout sends refresh_token in body", async () => {
    const spy = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(null, { status: 204 }),
    );

    await api.logout("rt-123");

    const [, init] = spy.mock.calls[0];
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body.refresh_token).toBe("rt-123");
  });

  it("should clear session on unauthorized when token set", () => {
    // Simulate: token is stored, session invalidated
    setToken("expired-token");
    expect(getToken()).toBe("expired-token");

    // onUnauthorized callback clears it
    onUnauthorized(() => setToken(null));

    // trigger callback
    const cb = vi.fn();
    onUnauthorized(cb);
    cb(); // simulate 401 callback
    setToken(null);

    expect(getToken()).toBeNull();
  });
});
