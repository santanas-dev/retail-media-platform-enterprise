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

const TOKEN_KEY = "rmp_access_token";
const PROVIDER_KEY = "rmp_auth_provider";
const REQUIRED_PROVIDER = "local_advertiser";

function saveSession(access: string, provider: string) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(PROVIDER_KEY, provider);
  setToken(access);
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(PROVIDER_KEY);
  setToken(null);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // On mount: try to restore session from stored token
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    const storedProvider = localStorage.getItem(PROVIDER_KEY);

    // If wrong provider, clear session immediately
    if (stored && storedProvider && storedProvider !== REQUIRED_PROVIDER) {
      clearSession();
      setLoading(false);
      return;
    }

    if (stored) {
      setToken(stored);
      api
        .getMe()
        .then((me) => {
          // Double-check: user must have local_advertiser provider
          if (me.auth_provider !== REQUIRED_PROVIDER) {
            clearSession();
          } else {
            setUser(me);
          }
        })
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
      saveSession(res.access_token, REQUIRED_PROVIDER);
      const me = await api.getMe();
      // Ensure the logged-in user has the correct provider
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
