import { vi } from "vitest";

/**
 * jsdom has no matchMedia, and the shell's narrow/wide behaviour is deliberately
 * observed in JS (see useIsNarrow) precisely so it can be tested. This installs
 * a controllable implementation that answers a single width query.
 */
export function setViewportWidth(width: number): void {
  const listeners = new Set<(e: MediaQueryListEvent) => void>();

  function evaluate(query: string): boolean {
    const max = /\(max-width:\s*(\d+)px\)/.exec(query);
    if (max) return width <= Number(max[1]);
    const min = /\(min-width:\s*(\d+)px\)/.exec(query);
    if (min) return width >= Number(min[1]);
    return false;
  }

  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      media: query,
      matches: evaluate(query),
      onchange: null,
      addEventListener: (_: string, cb: (e: MediaQueryListEvent) => void) => listeners.add(cb),
      removeEventListener: (_: string, cb: (e: MediaQueryListEvent) => void) => listeners.delete(cb),
      addListener: (cb: (e: MediaQueryListEvent) => void) => listeners.add(cb),
      removeListener: (cb: (e: MediaQueryListEvent) => void) => listeners.delete(cb),
      dispatchEvent: () => false,
    })),
  });
}

export const DESKTOP_WIDTH = 1440;
export const MOBILE_WIDTH = 390;
