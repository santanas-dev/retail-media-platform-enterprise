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
  refreshMe: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Access token lives ONLY in memory (module-level _token in client.ts).
 * No localStorage, no sessionStorage.  Session restore after reload
 * goes through POST /api/v1/auth/refresh (HttpOnly cookie → new access token).
 *
 * Provider gate: after restore, only local_advertiser users may proceed.
 */

const REQUIRED_PROVIDER = "local_advertiser";

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
      .then((me) => {
        if (me.auth_provider !== REQUIRED_PROVIDER) {
          clearSession();
          setError("Нет доступа к кабинету рекламодателя.");
        } else {
          setUser(me);
        }
      })
      .catch(() => clearSession())
      .finally(() => setLoading(false));
  }, []);

  // Register 401 handler
  useEffect(() => {
    onUnauthorized(() => {
      clearSession();
      setUser(null);
      setError("Сессия истекла. Пожалуйста, войдите снова.");
    });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.login({
        username_or_email: username,
        password,
        auth_provider: REQUIRED_PROVIDER,
      });
      setToken(res.access_token);
      const me = await api.getMe();
      if (me.auth_provider !== REQUIRED_PROVIDER) {
        clearSession();
        setError("Нет доступа к кабинету рекламодателя.");
        throw new Error("Нет доступа к кабинету рекламодателя.");
      }
      setUser(me);
    } catch (e) {
      clearSession();
      const msg =
        e instanceof Error ? e.message : "Ошибка входа. Попробуйте снова.";
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

  const refreshMe = useCallback(async () => {
    try {
      const me = await api.getMe();
      setUser(me);
    } catch {
      // Silently keep current user on failure
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout, refreshMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
