/**
 * UX-FIX-002 — Unit tests for shared formatApiError.
 *
 * Verifies FastAPI 422 array detail, string detail, object detail,
 * and generic errors are all human-readable.
 */
import { describe, it, expect } from "vitest";
import { ApiError } from "../api/client";
import { formatApiError } from "../api/errors";

describe("formatApiError", () => {
  it("handles FastAPI 422 array detail with field: msg", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "string_too_short",
          loc: ["body", "inn"],
          msg: "String should have at least 10 characters",
          input: "77",
        },
        {
          type: "missing",
          loc: ["body", "legal_address"],
          msg: "Field required",
          input: "",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).not.toContain("[object Object]");
    expect(result).toContain("inn");
    expect(result).toContain("String should have at least 10");
    expect(result).toContain("legal_address");
    expect(result).toContain("Field required");
  });

  it("handles FastAPI 422 single-element array", () => {
    const err = new ApiError(422, {
      detail: [
        { type: "missing", loc: ["body", "code"], msg: "Field required", input: "" },
      ],
    });
    const result = formatApiError(err);
    expect(result).not.toContain("[object Object]");
    expect(result).toContain("code");
    expect(result).toContain("Field required");
  });

  it("handles string detail as-is", () => {
    const err = new ApiError(400, { detail: "Invalid request" });
    const result = formatApiError(err);
    expect(result).toBe("Invalid request");
  });

  it("handles object detail with msg", () => {
    const err = new ApiError(409, {
      detail: { code: "DUPLICATE", msg: "Код уже используется" },
    });
    const result = formatApiError(err);
    expect(result).toBe("Код уже используется");
  });

  it("handles object detail with message", () => {
    const err = new ApiError(500, {
      detail: { message: "Internal error" },
    });
    const result = formatApiError(err);
    expect(result).toBe("Internal error");
  });

  it("handles generic Error", () => {
    const err = new Error("Network failure");
    const result = formatApiError(err);
    expect(result).toBe("Network failure");
  });

  it("handles [object Object] from bad Error.message", () => {
    const err = new Error("[object Object]");
    const result = formatApiError(err);
    expect(result).not.toBe("[object Object]");
    expect(result).toContain("Ошибка запроса");
  });

  it("handles unknown non-Error", () => {
    const result = formatApiError("просто строка");
    expect(result).toBe("просто строка");
  });

  it("handles null/undefined gracefully", () => {
    const result = formatApiError(null);
    expect(result).not.toContain("[object Object]");
    expect(result.length).toBeGreaterThan(0);
  });

  it("never returns [object Object] for ApiError with empty detail", () => {
    const err = new ApiError(422, { detail: [] });
    const result = formatApiError(err);
    expect(result).not.toContain("[object Object]");
  });
});
