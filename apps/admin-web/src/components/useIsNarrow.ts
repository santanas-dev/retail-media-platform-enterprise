import { useEffect, useState } from "react";

/**
 * PORTAL-UX-002 — the one breakpoint the operator console reasons about.
 *
 * The layout itself is CSS, but the *semantics* differ: on a narrow screen the
 * sidebar becomes a modal drawer with a trigger, a focus trap boundary and a
 * body-scroll lock, and none of that can be expressed in a media query. So the
 * breakpoint is observed in JS as well, through matchMedia — real in a browser,
 * and mockable in jsdom so the two modes can actually be tested.
 *
 * Falls back to "wide" when matchMedia is unavailable, which keeps the desktop
 * console rendering exactly as it always has.
 */
export const NARROW_QUERY = "(max-width: 767px)";

export function useIsNarrow(query: string = NARROW_QUERY): boolean {
  const [isNarrow, setIsNarrow] = useState<boolean>(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return false;
    }
    return window.matchMedia(query).matches;
  });

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mql = window.matchMedia(query);
    const onChange = (e: MediaQueryListEvent) => setIsNarrow(e.matches);
    setIsNarrow(mql.matches);
    if (typeof mql.addEventListener === "function") {
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    }
    // Older Safari / jsdom shims
    mql.addListener(onChange);
    return () => mql.removeListener(onChange);
  }, [query]);

  return isNarrow;
}
