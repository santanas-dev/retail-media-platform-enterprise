import type { ReactNode } from "react";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  children?: ReactNode;  // actions slot (right side)
}

export default function PageHeader({ title, subtitle, children }: PageHeaderProps) {
  return (
    <header
      style={{
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "space-between",
        marginBottom: "var(--rmp-space-6)",
        gap: "var(--rmp-space-4)",
        flexWrap: "wrap",
      }}
    >
      <div>
        <h1
          style={{
            margin: 0,
            fontSize: "var(--rmp-font-size-2xl)",
            fontWeight: 600,
            color: "var(--rmp-text-primary)",
            lineHeight: "1.3",
          }}
        >
          {title}
        </h1>
        {subtitle && (
          <p
            style={{
              margin: "var(--rmp-space-1) 0 0",
              fontSize: "var(--rmp-font-size-base)",
              color: "var(--rmp-text-secondary)",
            }}
          >
            {subtitle}
          </p>
        )}
      </div>
      {children && <div style={{ display: "flex", gap: "var(--rmp-space-2)", flexShrink: 0 }}>{children}</div>}
    </header>
  );
}
