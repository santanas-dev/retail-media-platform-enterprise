import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import { api, setToken, onUnauthorized, type MeResponse } from "../api/client";

interface AuthState {
  user: MeResponse | null;
  loading: boolean;
  error: string | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

const TOKEN_KEY = "rmp_access_token";
const REFRESH_KEY = "rmp_refresh_token";

function saveSession(access: string, refresh: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  setToken(access);
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  setToken(null);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // On mount: try to restore session from stored token
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (stored) {
      setToken(stored);
      api
        .getMe()
        .then((me) => setUser(me))
        .catch(() => clearSession())
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  // Register 401 handler
  useEffect(() => {
    onUnauthorized(() => {
      clearSession();
      setUser(null);
      setError("Session expired. Please log in again.");
    });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.login({ username, password });
      saveSession(res.access_token, res.refresh_token);
      const me = await api.getMe();
      setUser(me);
    } catch (e) {
      clearSession();
      const msg =
        e instanceof Error ? e.message : "Login failed. Please try again.";
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(() => {
    const refresh = localStorage.getItem(REFRESH_KEY);
    clearSession();
    setUser(null);
    if (refresh) {
      api.logout(refresh).catch(() => {
        /* fire-and-forget */
      });
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
