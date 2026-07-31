/**
 * Shared API error formatter — UX-FIX-002 + UX-POLISH-001B.
 *
 * Single source of truth for human-readable error messages.
 * Handles FastAPI/Pydantic 422 validation arrays, object detail, and generic errors.
 * Localized to Russian: field labels + type-based messages, no i18n framework.
 * Never returns "[object Object]".
 */
import { ApiError } from "./client";

// ── Field label map ────────────────────────────────────────────────────────

const FIELD_LABELS: Record<string, string> = {
  code: "Код",
  name: "Название",
  title: "Название",
  display_name: "Отображаемое название",
  legal_name: "Юр. название",
  legal_entity_type: "Тип юрлица",
  legal_form: "ОПФ",
  legal_form_other: "ОПФ",
  inn: "ИНН",
  kpp: "КПП",
  ogrn: "ОГРН",
  ogrnip: "ОГРНИП",
  bik: "БИК",
  settlement_account: "Расчётный счёт",
  correspondent_account: "Корр. счёт",
  legal_address: "Юр. адрес",
  bank_name: "Банк",
  contract_number: "№ договора",
  budget_limit_amount: "Бюджет",
  username: "Логин",
  email: "Email",
  phone: "Телефон",
  description: "Описание",
  starts_at: "Дата начала",
  ends_at: "Дата окончания",
  file: "Файл",
  file_name: "Файл",
};

function fieldLabel(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

// ── FastAPI / Pydantic type translation ─────────────────────────────────────

interface DetailCtx {
  min_length?: number;
  max_length?: number;
  gt?: number;
  ge?: number;
  lt?: number;
  le?: number;
}

/**
 * Translate a FastAPI/Pydantic validation error type to a Russian message.
 * Uses `type` from the detail item, not fragile English msg matching.
 * Returns empty string for unknown types — caller falls back to original msg.
 */
function translateType(type: string, ctx: DetailCtx | undefined): string {
  if (type === "missing") return "обязательное поле";

  if (type === "string_too_short") {
    const min = typeof ctx?.min_length === "number" ? ctx.min_length : 0;
    if (min <= 1) return "обязательное поле";
    return `минимум ${min} симв.`;
  }

  if (type === "string_too_long") {
    const max = typeof ctx?.max_length === "number" ? ctx.max_length : undefined;
    return max !== undefined ? `максимум ${max} симв.` : "превышена длина";
  }

  if (type === "string_pattern_mismatch") return "неверный формат";
  if (type === "value_error") return "неверное значение";
  if (type === "literal_error") return "недопустимое значение";

  // Enum variants: `enum`, `type_error.enum`, etc.
  if (type.includes("enum")) return "недопустимое значение";

  if (type === "int_parsing" || type === "float_parsing") return "должно быть числом";

  if (type === "greater_than") {
    const value = typeof ctx?.gt === "number" ? ctx.gt : undefined;
    return value !== undefined ? `должно быть больше ${value}` : "неверное значение";
  }
  if (type === "greater_than_equal") {
    const value = typeof ctx?.ge === "number" ? ctx.ge : undefined;
    return value !== undefined ? `должно быть не меньше ${value}` : "неверное значение";
  }
  if (type === "less_than") {
    const value = typeof ctx?.lt === "number" ? ctx.lt : undefined;
    return value !== undefined ? `должно быть меньше ${value}` : "неверное значение";
  }
  if (type === "less_than_equal") {
    const value = typeof ctx?.le === "number" ? ctx.le : undefined;
    return value !== undefined ? `должно быть не больше ${value}` : "неверное значение";
  }

  // Unknown type — fall back to original msg
  return "";
}

// ── Detail formatting ──────────────────────────────────────────────────────

/**
 * Format a FastAPI 422 detail — array of {type, loc, msg, input, ctx}.
 * Uses type-based Russian translations and field label map.
 * Returns readable semicolon-joined field messages.
 */
function formatDetailArray(detail: unknown[]): string {
  const parts = detail.map((item: unknown) => {
    if (typeof item !== "object" || item === null) {
      return String(item);
    }
    const d = item as Record<string, unknown>;
    const loc = Array.isArray(d.loc) ? d.loc : [];
    const field =
      typeof loc[loc.length - 1] === "string"
        ? (loc[loc.length - 1] as string)
        : undefined;
    const msg = typeof d.msg === "string" ? d.msg : "";
    const type = typeof d.type === "string" ? d.type : "";
    const ctx: DetailCtx | undefined = d.ctx as DetailCtx | undefined;

    // Try type-based Russian translation
    const translated = translateType(type, ctx);
    if (translated) {
      const label = field ? fieldLabel(field) : "";
      return label ? `${label}: ${translated}` : translated;
    }

    // Fallback: field label + original msg
    if (field && msg) {
      const label = fieldLabel(field);
      return `${label}: ${msg}`;
    }
    if (msg) return msg;
    return String(d.msg ?? JSON.stringify(d));
  });
  return parts.join("; ");
}

// ── Public API ─────────────────────────────────────────────────────────────

/**
 * Convert any caught error into a human-readable string.
 *
 * Handles:
 *  - ApiError with array detail (FastAPI 422) → localized field: message format
 *  - ApiError with string detail → as-is
 *  - ApiError with object detail → prefer msg/message field
 *  - Generic Error → message
 *  - Unknown → fallback
 */
export function formatApiError(e: unknown): string {
  if (e instanceof ApiError) {
    const detail = (e.body as Record<string, unknown> | null)?.detail;

    // FastAPI 422: detail is an array of validation errors
    if (Array.isArray(detail) && detail.length > 0) {
      return formatDetailArray(detail);
    }

    // String detail — use as-is unless it's a generic English status message
    if (typeof detail === "string" && detail.length > 0) {
      // Don't return bare English status messages when we have Russian equivalents
      if (e.status === 403 && detail === "Forbidden") {
        return "Нет прав на это действие.";
      }
      return detail;
    }

    // Object detail — prefer msg/message
    if (typeof detail === "object" && detail !== null) {
      const d = detail as Record<string, unknown>;
      if (typeof d.msg === "string") return d.msg;
      if (typeof d.message === "string") return d.message;
      return `Ошибка: ${JSON.stringify(d).slice(0, 200)}`;
    }

    // Status-based fallbacks for common codes with no usable detail
    if (e.status === 403) return "Нет прав на это действие.";
    if (e.status === 409) return "Конфликт данных.";
    if (e.status === 422) {
      // Generic 422 without detail array
      if (e.message && e.message !== `HTTP ${e.status}`) return e.message;
      return "Ошибка валидации данных.";
    }

    // Fallback to message if it's informative
    if (e.message && e.message !== `HTTP ${e.status}`) {
      return e.message;
    }
    return `Ошибка сервера (${e.status})`;
  }

  if (e instanceof Error) {
    const msg = e.message;
    if (msg && msg !== "[object Object]") return msg;
    return "Ошибка запроса. Проверьте данные и попробуйте снова.";
  }

  const str = String(e);
  if (str && str !== "[object Object]") return str;
  return "Ошибка запроса. Проверьте данные и попробуйте снова.";
}
