import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";

/** Supported theme identifiers. */
export type ThemeId = "light" | "dark";

/** Available themes for the ThemeProvider toggle. */
const AVAILABLE_THEMES: readonly ThemeId[] = ["light", "dark"] as const;

const DEFAULT_THEME: ThemeId = "light";
const STORAGE_KEY = "rmp-admin-theme";

interface ThemeState {
  /** Current active theme. */
  theme: ThemeId;
  /** Switch to another theme. No-op if the theme is not in availableThemes. */
  setTheme: (next: ThemeId) => void;
  /** All recognised theme identifiers. */
  availableThemes: readonly ThemeId[];
}

const ThemeContext = createContext<ThemeState | null>(null);

/** Read persisted theme from localStorage, validate, fall back to default. */
function readStoredTheme(): ThemeId {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw && (AVAILABLE_THEMES as readonly string[]).includes(raw)) {
      return raw as ThemeId;
    }
  } catch {
    // localStorage unavailable (SSR / private browsing)
  }
  return DEFAULT_THEME;
}

/** Apply theme as data-theme on <html>. */
function applyTheme(theme: ThemeId): void {
  document.documentElement.dataset.theme = theme;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeId>(readStoredTheme);

  // Apply on mount and whenever theme changes
  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const setTheme = useCallback((next: ThemeId) => {
    if (!(AVAILABLE_THEMES as readonly string[]).includes(next)) {
      return; // silently ignore unknown themes
    }
    setThemeState(next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // localStorage write failed — non-critical
    }
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, availableThemes: AVAILABLE_THEMES }}>
      {children}
    </ThemeContext.Provider>
  );
}

/** Access the current theme context. Throws if used outside ThemeProvider. */
export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
