import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import s from "./PageHeader.module.css";

export interface Breadcrumb {
  label: string;
  /** Omit on the last crumb — the current page is not a link. */
  to?: string;
}

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  /** Trail above the title. The final entry is rendered as plain text. */
  breadcrumbs?: Breadcrumb[];
  /** Actions slot (primary first). Wraps under the title on narrow screens. */
  children?: ReactNode;
}

/**
 * The page header contract every screen should reach for.
 *
 * Deliberately small: a title, an optional subtitle, an optional trail, and a
 * slot. No card wrapper and no hero-scale type — this is an operator console,
 * and the header should not cost a third of the viewport.
 */
export default function PageHeader({ title, subtitle, breadcrumbs, children }: PageHeaderProps) {
  return (
    <header className={s.header} data-testid="page-header">
      <div className={s.titles}>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav aria-label="Навигационная цепочка">
            <ol className={s.breadcrumbs} data-testid="page-header-breadcrumbs">
              {breadcrumbs.map((crumb, i) => {
                const isLast = i === breadcrumbs.length - 1;
                return (
                  <li key={`${crumb.label}-${i}`} style={{ display: "contents" }}>
                    {crumb.to && !isLast ? (
                      <Link className={s.crumbLink} to={crumb.to}>{crumb.label}</Link>
                    ) : (
                      <span aria-current={isLast ? "page" : undefined}>{crumb.label}</span>
                    )}
                    {!isLast && <span className={s.crumbSeparator} aria-hidden="true">/</span>}
                  </li>
                );
              })}
            </ol>
          </nav>
        )}
        <h1 className={s.title}>{title}</h1>
        {subtitle && <p className={s.subtitle}>{subtitle}</p>}
      </div>
      {children && (
        <div className={s.actions} data-testid="page-header-actions">{children}</div>
      )}
    </header>
  );
}
