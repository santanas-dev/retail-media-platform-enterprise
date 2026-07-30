/**
 * Shared API error formatter — UX-FIX-002.
 *
 * Single source of truth for human-readable error messages.
 * Handles FastAPI/Pydantic 422 validation arrays, object detail, and generic errors.
 * Never returns "[object Object]".
 */
import { ApiError } from "./client";

/**
 * Format a FastAPI 422 detail — array of {type, loc, msg, input}.
 * Returns readable semicolon-joined field messages.
 */
function formatDetailArray(detail: unknown[]): string {
  const parts = detail.map((item: unknown) => {
    if (typeof item !== "object" || item === null) {
      return String(item);
    }
    const d = item as Record<string, unknown>;
    const field = Array.isArray(d.loc) ? d.loc[d.loc.length - 1] : undefined;
    const msg = typeof d.msg === "string" ? d.msg : "";
    if (field && msg) return `${field}: ${msg}`;
    if (msg) return msg;
    return String(d.msg ?? JSON.stringify(d));
  });
  return parts.join("; ");
}

/**
 * Convert any caught error into a human-readable string.
 *
 * Handles:
 *  - ApiError with array detail (FastAPI 422) → field: message format
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
