/**
 * UX-POLISH-001B — Unit tests for localized formatApiError.
 *
 * Verifies:
 *  - Pydantic type → Russian message (type-based, not English msg)
 *  - Field labels → Russian (ИНН, Код, etc.)
 *  - Multiple errors joined with "; "
 *  - Unknown type/field fallbacks don't crash
 *  - Status fallbacks (403, 409) still work
 *  - Object detail, string detail, generic Error unchanged
 */
import { describe, it, expect } from "vitest";
import { ApiError } from "../api/client";
import { formatApiError } from "../api/errors";

describe("formatApiError — UX-POLISH-001B", () => {
  // ── 422 array: type-based + field label ──────────────────────────────

  it("translates string_too_short min_length=1 → обязательное поле", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "string_too_short",
          loc: ["body", "code"],
          msg: "String should have at least 1 character",
          input: "",
          ctx: { min_length: 1 },
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Код");
    expect(result).toContain("обязательное поле");
    expect(result).not.toContain("[object Object]");
    expect(result).not.toContain("String should have");
  });

  it("translates string_too_short min_length=10 → минимум N симв.", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "string_too_short",
          loc: ["body", "inn"],
          msg: "String should have at least 10 characters",
          input: "77",
          ctx: { min_length: 10 },
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("ИНН");
    expect(result).toContain("минимум 10 симв.");
    expect(result).not.toContain("String should have");
  });

  it("translates missing → обязательное поле", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "missing",
          loc: ["body", "legal_address"],
          msg: "Field required",
          input: "",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Юр. адрес");
    expect(result).toContain("обязательное поле");
    expect(result).not.toContain("Field required");
  });

  it("translates string_too_long → максимум N симв.", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "string_too_long",
          loc: ["body", "name"],
          msg: "String should have at most 255 characters",
          input: "x".repeat(300),
          ctx: { max_length: 255 },
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Название");
    expect(result).toContain("максимум 255 симв.");
  });

  it("translates string_pattern_mismatch → неверный формат", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "string_pattern_mismatch",
          loc: ["body", "inn"],
          msg: "String should match pattern",
          input: "abc",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("ИНН");
    expect(result).toContain("неверный формат");
  });

  it("translates value_error → неверное значение", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "value_error",
          loc: ["body", "legal_entity_type"],
          msg: "value is not a valid enumeration member",
          input: "bad",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Тип юрлица");
    expect(result).toContain("неверное значение");
  });

  it("translates literal_error → недопустимое значение", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "literal_error",
          loc: ["body", "legal_form"],
          msg: "unexpected value",
          input: "bad",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("ОПФ");
    expect(result).toContain("недопустимое значение");
  });

  it("translates enum variants → недопустимое значение", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "type_error.enum",
          loc: ["body", "legal_form"],
          msg: "value is not a valid enumeration member",
          input: "bad",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("ОПФ");
    expect(result).toContain("недопустимое значение");
  });

  it("translates int_parsing → должно быть числом", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "int_parsing",
          loc: ["body", "budget_limit_amount"],
          msg: "Input should be a valid integer",
          input: "abc",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Бюджет");
    expect(result).toContain("должно быть числом");
  });

  it("translates float_parsing → должно быть числом", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "float_parsing",
          loc: ["body", "budget_limit_amount"],
          msg: "Input should be a valid number",
          input: "abc",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Бюджет");
    expect(result).toContain("должно быть числом");
  });

  it("translates greater_than → должно быть больше N", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "greater_than",
          loc: ["body", "budget_limit_amount"],
          msg: "Input should be greater than 0",
          input: -100,
          ctx: { gt: 0 },
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Бюджет");
    expect(result).toContain("должно быть больше 0");
  });

  it("translates greater_than_equal → должно быть не меньше N", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "greater_than_equal",
          loc: ["body", "budget_limit_amount"],
          msg: "Input should be greater than or equal to 1",
          input: 0,
          ctx: { ge: 1 },
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Бюджет");
    expect(result).toContain("должно быть не меньше 1");
  });

  it("translates less_than → должно быть меньше N", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "less_than",
          loc: ["body", "budget_limit_amount"],
          msg: "Input should be less than 999999999",
          input: 9999999999,
          ctx: { lt: 999999999 },
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Бюджет");
    expect(result).toContain("должно быть меньше 999999999");
  });

  it("translates less_than_equal → должно быть не больше N", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "less_than_equal",
          loc: ["body", "budget_limit_amount"],
          msg: "Input should be less than or equal to 999999999",
          input: 9999999999,
          ctx: { le: 999999999 },
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Бюджет");
    expect(result).toContain("должно быть не больше 999999999");
  });

  // ── Field label coverage ─────────────────────────────────────────────

  it("maps inn → ИНН", () => {
    const err = new ApiError(422, {
      detail: [
        { type: "missing", loc: ["body", "inn"], msg: "Field required", input: "" },
      ],
    });
    expect(formatApiError(err)).toContain("ИНН");
  });

  it("maps settlement_account → Расчётный счёт", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "missing",
          loc: ["body", "settlement_account"],
          msg: "Field required",
          input: "",
        },
      ],
    });
    expect(formatApiError(err)).toContain("Расчётный счёт");
  });

  it("maps correspondent_account → Корр. счёт", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "missing",
          loc: ["body", "correspondent_account"],
          msg: "Field required",
          input: "",
        },
      ],
    });
    expect(formatApiError(err)).toContain("Корр. счёт");
  });

  it("maps contract_number → № договора", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "missing",
          loc: ["body", "contract_number"],
          msg: "Field required",
          input: "",
        },
      ],
    });
    expect(formatApiError(err)).toContain("№ договора");
  });

  it("maps legal_name → Юр. название", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "missing",
          loc: ["body", "legal_name"],
          msg: "Field required",
          input: "",
        },
      ],
    });
    expect(formatApiError(err)).toContain("Юр. название");
  });

  // ── Multiple errors ──────────────────────────────────────────────────

  it("joins multiple errors with ; ", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "missing",
          loc: ["body", "code"],
          msg: "Field required",
          input: "",
        },
        {
          type: "string_too_short",
          loc: ["body", "inn"],
          msg: "String should have at least 10 characters",
          input: "77",
          ctx: { min_length: 10 },
        },
        {
          type: "string_pattern_mismatch",
          loc: ["body", "kpp"],
          msg: "String should match pattern",
          input: "abc",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("; ");
    expect(result).toContain("Код: обязательное поле");
    expect(result).toContain("ИНН: минимум 10 симв.");
    expect(result).toContain("КПП: неверный формат");
  });

  // ── Unknown type / field fallbacks ───────────────────────────────────

  it("unknown field — uses original field name as label", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "missing",
          loc: ["body", "custom_field"],
          msg: "Field required",
          input: "",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("custom_field");
    expect(result).toContain("обязательное поле");
    expect(result).not.toContain("Field required");
  });

  it("unknown type — falls back to original msg with field label", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "custom_validation_error",
          loc: ["body", "code"],
          msg: "Must be unique across advertisers",
          input: "DUP",
        },
      ],
    });
    const result = formatApiError(err);
    expect(result).toContain("Код: Must be unique across advertisers");
    expect(result).not.toContain("[object Object]");
  });

  it("unknown type without ctx but min_length from msg — still falls back to original", () => {
    const err = new ApiError(422, {
      detail: [
        {
          type: "string_too_short",
          loc: ["body", "inn"],
          msg: "String should have at least 10 characters",
          input: "77",
        },
      ],
    });
    const result = formatApiError(err);
    // Without ctx, min_length defaults to 0 → обязательное поле
    expect(result).toContain("ИНН: обязательное поле");
    expect(result).not.toContain("String should have");
  });

  // ── Status fallbacks still work ──────────────────────────────────────

  it("403 Forbidden → Нет прав на это действие", () => {
    const err = new ApiError(403, { detail: "Forbidden" });
    expect(formatApiError(err)).toBe("Нет прав на это действие.");
  });

  it("403 no detail → Нет прав на это действие", () => {
    const err = new ApiError(403, {});
    expect(formatApiError(err)).toBe("Нет прав на это действие.");
  });

  it("409 → Конфликт данных", () => {
    const err = new ApiError(409, {});
    expect(formatApiError(err)).toBe("Конфликт данных.");
  });

  // ── Object detail, string detail, generic Error (unchanged) ──────────

  it("handles string detail as-is", () => {
    const err = new ApiError(400, { detail: "Invalid request" });
    expect(formatApiError(err)).toBe("Invalid request");
  });

  it("handles object detail with msg", () => {
    const err = new ApiError(409, {
      detail: { code: "DUPLICATE", msg: "Код уже используется" },
    });
    expect(formatApiError(err)).toBe("Код уже используется");
  });

  it("handles object detail with message", () => {
    const err = new ApiError(500, {
      detail: { message: "Internal error" },
    });
    expect(formatApiError(err)).toBe("Internal error");
  });

  it("handles generic Error", () => {
    const err = new Error("Network failure");
    expect(formatApiError(err)).toBe("Network failure");
  });

  it("handles [object Object] from bad Error.message", () => {
    const err = new Error("[object Object]");
    const result = formatApiError(err);
    expect(result).not.toBe("[object Object]");
    expect(result).toContain("Ошибка запроса");
  });

  it("handles unknown non-Error", () => {
    expect(formatApiError("просто строка")).toBe("просто строка");
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
