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
  login: (username: string, password: string, authProvider?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Access token lives ONLY in memory (module-level _token in client.ts).
 * No localStorage, no sessionStorage.  Session restore after reload
 * goes through POST /api/v1/auth/refresh (HttpOnly cookie → new access token).
 */

function saveSession(access: string) {
  setToken(access);
}

function clearSession() {
  setToken(null);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // On mount: restore session via refresh cookie (no localStorage)
  useEffect(() => {
    api
      .refresh()
      .then((res) => {
        setToken(res.access_token);
        return api.getMe();
      })
      .then((me) => setUser(me))
      .catch(() => clearSession())
      .finally(() => setLoading(false));
  }, []);

  // Register 401 handler
  useEffect(() => {
    onUnauthorized(() => {
      clearSession();
      setUser(null);
      setError("Session expired. Please log in again.");
    });
  }, []);

  const login = useCallback(async (username: string, password: string, authProvider: string = "local_advertiser") => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.login({
        username_or_email: username,
        password,
        auth_provider: authProvider,
      });
      setToken(res.access_token);
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
    clearSession();
    setUser(null);
    api.logout().catch(() => {
      /* fire-and-forget */
    });
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
