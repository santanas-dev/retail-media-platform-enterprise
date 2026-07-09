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

function saveSession(access: string) {
  localStorage.setItem(TOKEN_KEY, access);
  setToken(access);
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
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
      const res = await api.login({
        username_or_email: username,
        password,
        auth_provider: "ad",
      });
      saveSession(res.access_token);
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
