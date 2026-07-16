/**
 * S-089 — Inventory Simulation frontend tests.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { simulateInventory } from "../api/campaigns";

// Mock the API client
vi.mock("../api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
  ApiError: class extends Error {
    status: number;
    constructor(status: number, body: unknown) {
      super(typeof body === "string" ? body : String(body));
      this.status = status;
      this.name = "ApiError";
    }
  },
  getToken: vi.fn(() => "test-token"),
  IDENTITY_BASE_URL: "http://localhost:8000",
}));

import { api } from "../api/client";

describe("simulateInventory API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls POST /inventory/simulate with campaign_id", async () => {
    const mockResponse = {
      campaign_id: "c1",
      overall_fit: true,
      placements: [],
      blocking_count: 0,
      warning_count: 0,
    };
    vi.mocked(api.post).mockResolvedValueOnce(mockResponse);

    const result = await simulateInventory("c1");
    expect(api.post).toHaveBeenCalledWith("/inventory/simulate", {
      campaign_id: "c1",
    });
    expect(result.overall_fit).toBe(true);
  });

  it("returns fit=false when campaign doesn't fit", async () => {
    const mockResponse = {
      campaign_id: "c2",
      overall_fit: false,
      placements: [
        {
          placement_id: "p1",
          surface_id: "s1",
          surface_code: "KSO-001",
          fit: false,
          slot_fill_percent: 150,
          total_requested: 1500,
          total_available: 1000,
          conflicts: [
            {
              conflict_type: "capacity_overbook",
              severity: "blocking",
              surface_id: "s1",
              message: "Requested 1500, available 1000",
            },
          ],
          applied_rules: [],
        },
      ],
      blocking_count: 1,
      warning_count: 0,
    };
    vi.mocked(api.post).mockResolvedValueOnce(mockResponse);

    const result = await simulateInventory("c2");
    expect(result.overall_fit).toBe(false);
    expect(result.blocking_count).toBe(1);
    expect(result.placements[0].fit).toBe(false);
    expect(result.placements[0].conflicts[0].severity).toBe("blocking");
  });

  it("propagates API errors", async () => {
    const { ApiError } = await import("../api/client");
    vi.mocked(api.post).mockRejectedValueOnce(
      new ApiError(404, "Campaign not found"),
    );

    await expect(simulateInventory("c-unknown")).rejects.toThrow(
      "Campaign not found",
    );
  });
});
