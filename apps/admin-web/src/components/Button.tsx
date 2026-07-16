import type { ButtonHTMLAttributes, ReactNode } from "react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md";
  loading?: boolean;
  children: ReactNode;
}

const base: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "var(--rmp-space-2)",
  border: "1px solid transparent",
  borderRadius: "var(--rmp-radius-sm)",
  fontWeight: 500,
  cursor: "pointer",
  transition: "background 0.15s, border-color 0.15s, opacity 0.15s",
  whiteSpace: "nowrap",
  fontFamily: "inherit",
  lineHeight: "1.4",
};

const variants: Record<string, React.CSSProperties> = {
  primary: {
    background: "var(--rmp-primary-600)",
    color: "var(--rmp-text-inverse)",
    borderColor: "var(--rmp-primary-600)",
  },
  secondary: {
    background: "var(--rmp-bg-surface)",
    color: "var(--rmp-text-primary)",
    borderColor: "var(--rmp-border-strong)",
  },
  danger: {
    background: "var(--rmp-danger-600)",
    color: "var(--rmp-text-inverse)",
    borderColor: "var(--rmp-danger-600)",
  },
  ghost: {
    background: "transparent",
    color: "var(--rmp-text-secondary)",
    borderColor: "transparent",
  },
};

const sizes: Record<string, React.CSSProperties> = {
  sm: { padding: "0.25rem 0.625rem", fontSize: "var(--rmp-font-size-xs)" },
  md: { padding: "0.4rem 0.875rem", fontSize: "var(--rmp-font-size-base)" },
};

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  children,
  style,
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <button
      disabled={isDisabled}
      style={{
        ...base,
        ...variants[variant],
        ...sizes[size],
        ...(isDisabled ? { opacity: 0.5, cursor: "default" } : {}),
        ...(variant === "ghost" && !isDisabled
          ? {}
          : {}),
        ...style,
      }}
      {...rest}
    >
      {loading ? "…" : children}
    </button>
  );
}
