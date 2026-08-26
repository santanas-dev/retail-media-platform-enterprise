import { useId } from "react";
import type { ReactNode } from "react";
import s from "./FormField.module.css";

export interface FormFieldRenderProps {
  /** Put this on the control — it is what the label points at. */
  id: string;
  "aria-describedby"?: string;
  "aria-invalid"?: boolean;
  "aria-required"?: boolean;
  required?: boolean;
  disabled?: boolean;
  readOnly?: boolean;
}

export interface FormFieldProps {
  label: string;
  /** Supply one when the control already has an id the page depends on. */
  htmlFor?: string;
  required?: boolean;
  help?: string;
  error?: string;
  disabled?: boolean;
  readOnly?: boolean;
  children: (props: FormFieldRenderProps) => ReactNode;
}

/**
 * PORTAL-UX-003 — the accessible field contract.
 *
 * The audit found labels that looked like labels and were not: six of eight
 * fields on the AD settings screen had no programmatic association, so a screen
 * reader announced an unnamed text box. This component hands the control an id
 * and wires `label for`, `aria-describedby`, `aria-invalid` and `aria-required`
 * around it, so a page cannot accidentally ship a field that is only visually
 * labelled.
 *
 * It takes a render prop rather than wrapping an input, because the same
 * contract has to hold for `<input>`, `<select>`, `<textarea>` and a file
 * trigger, and because the pages already own their control styling.
 *
 * Requirement and error are never colour-only: the label carries a textual
 * "обязательное" note and the error line is prefixed with a mark.
 */
export default function FormField({
  label,
  htmlFor,
  required = false,
  help,
  error,
  disabled = false,
  readOnly = false,
  children,
}: FormFieldProps) {
  const generatedId = useId();
  const id = htmlFor ?? `field-${generatedId}`;
  const helpId = help ? `${id}-help` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={`${s.field}${disabled ? ` ${s.disabled}` : ""}`} data-testid="form-field">
      <label className={s.label} htmlFor={id}>
        {label}
        {required && (
          <>
            <span className={s.required} aria-hidden="true">*</span>
            <span className={s.requiredNote}>обязательное</span>
          </>
        )}
      </label>

      <div className={s.control}>
        {children({
          id,
          "aria-describedby": describedBy,
          "aria-invalid": error ? true : undefined,
          "aria-required": required || undefined,
          required: required || undefined,
          disabled: disabled || undefined,
          readOnly: readOnly || undefined,
        })}
      </div>

      {help && (
        <div className={s.help} id={helpId}>{help}</div>
      )}

      <div className={s.errorSlot} id={errorId} role={error ? "alert" : undefined}>
        {error && (
          <>
            <span className={s.errorMark} aria-hidden="true">!</span>
            <span>{error}</span>
          </>
        )}
      </div>
    </div>
  );
}
