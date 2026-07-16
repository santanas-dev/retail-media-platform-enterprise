import type { ReactNode } from "react";

export type StatusBadgeVariant = "active" | "draft" | "review" | "rejected" | "neutral";

const VARIANT_COLORS: Record<StatusBadgeVariant, { text: string; bg: string }> = {
  active:   { text: "var(--rmp-status-active-text)",   bg: "var(--rmp-status-active-bg)" },
  draft:    { text: "var(--rmp-status-draft-text)",    bg: "var(--rmp-status-draft-bg)" },
  review:   { text: "var(--rmp-status-review-text)",   bg: "var(--rmp-status-review-bg)" },
  rejected: { text: "var(--rmp-status-rejected-text)", bg: "var(--rmp-status-rejected-bg)" },
  neutral:  { text: "var(--rmp-text-secondary)",       bg: "var(--rmp-gray-100)" },
};

export interface StatusBadgeProps {
  variant: StatusBadgeVariant;
  children: ReactNode;
}

export default function StatusBadge({ variant, children }: StatusBadgeProps) {
  const colors = VARIANT_COLORS[variant];
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.15rem 0.5rem",
        borderRadius: "9999px",
        fontSize: "var(--rmp-font-size-xs)",
        fontWeight: 600,
        color: colors.text,
        background: colors.bg,
        lineHeight: "1.5",
      }}
    >
      {children}
    </span>
  );
}
