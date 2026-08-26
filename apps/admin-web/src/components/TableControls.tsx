import { useId } from "react";
import type { ReactNode } from "react";
import s from "./TableControls.module.css";

export interface SortOption {
  value: string;
  label: string;
}

export interface TableControlsProps {
  /** Wire search only when the page can honestly search the whole set. */
  search?: {
    value: string;
    onChange: (value: string) => void;
    label?: string;
    placeholder?: string;
  };
  sort?: {
    value: string;
    options: SortOption[];
    onChange: (value: string) => void;
    label?: string;
  };
  /** Filter controls the page owns — chips, selects, date ranges. */
  filters?: ReactNode;
  /** How many rows the user is looking at, in the page's own words. */
  resultLabel?: string;
  /**
   * What the controls above actually apply to, when that is narrower than the
   * whole collection. Say it rather than let the count imply something untrue.
   */
  scopeNote?: string;
  onReset?: () => void;
  resetLabel?: string;
  /** Enabled only when something is actually filtered. */
  canReset?: boolean;
  /** Page-level actions that belong with the toolbar. */
  actions?: ReactNode;
  loading?: boolean;
  disabled?: boolean;
}

/**
 * PORTAL-UX-001 — the list toolbar contract.
 *
 * It renders only what the page gives it. In particular it does NOT filter
 * anything itself and never assumes the rows it sits above are the whole
 * collection: search and sort are callbacks the page implements, so a paginated
 * screen cannot accidentally search one page of results and present that as a
 * search of everything. Where a page can only filter what it has loaded, it
 * says so through `scopeNote`.
 */
export default function TableControls({
  search,
  sort,
  filters,
  resultLabel,
  scopeNote,
  onReset,
  resetLabel = "Сбросить",
  canReset = true,
  actions,
  loading = false,
  disabled = false,
}: TableControlsProps) {
  const baseId = useId();
  const searchId = `${baseId}-search`;
  const sortId = `${baseId}-sort`;
  const isDisabled = disabled || loading;

  return (
    <div className={s.controls} data-testid="table-controls">
      {search && (
        <div className={`${s.group} ${s.search}`}>
          <label className={s.controlLabel} htmlFor={searchId}>
            {search.label ?? "Поиск"}
          </label>
          <input
            id={searchId}
            className={s.input}
            type="search"
            value={search.value}
            placeholder={search.placeholder}
            disabled={isDisabled}
            data-testid="table-controls-search"
            onChange={(e) => search.onChange(e.target.value)}
          />
        </div>
      )}

      {sort && (
        <div className={s.group}>
          <label className={s.controlLabel} htmlFor={sortId}>
            {sort.label ?? "Сортировка"}
          </label>
          <select
            id={sortId}
            className={s.select}
            value={sort.value}
            disabled={isDisabled}
            data-testid="table-controls-sort"
            onChange={(e) => sort.onChange(e.target.value)}
          >
            {sort.options.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      )}

      {filters && (
        <div className={s.filters} data-testid="table-controls-filters">{filters}</div>
      )}

      <div className={s.meta}>
        {resultLabel && (
          <span className={s.count} data-testid="table-controls-count" aria-live="polite">
            {loading ? "Загрузка…" : resultLabel}
          </span>
        )}
        {scopeNote && (
          <span className={s.scopeNote} data-testid="table-controls-scope">{scopeNote}</span>
        )}
        {onReset && (
          <button
            type="button"
            className={s.reset}
            data-testid="table-controls-reset"
            disabled={isDisabled || !canReset}
            onClick={onReset}
          >
            {resetLabel}
          </button>
        )}
        {actions && (
          <div className={s.actions} data-testid="table-controls-actions">{actions}</div>
        )}
      </div>
    </div>
  );
}
