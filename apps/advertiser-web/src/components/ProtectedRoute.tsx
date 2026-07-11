import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const REQUIRED_PROVIDER = "local_advertiser";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading, logout } = useAuth();
  const location = useLocation();

  if (loading) {
    return null; // AuthProvider handles loading screen
  }

  if (!user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (user.auth_provider !== REQUIRED_PROVIDER) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "system-ui, sans-serif",
          background: "#f8fafc",
        }}
      >
        <div
          style={{
            background: "#fff",
            padding: "2rem",
            borderRadius: 8,
            boxShadow: "0 1px 3px rgba(0,0,0,0.1)",
            textAlign: "center",
            maxWidth: 400,
          }}
        >
          <h2 style={{ margin: "0 0 0.5rem", fontSize: "1.125rem", color: "#991b1b" }}>
            Нет доступа к кабинету рекламодателя
          </h2>
          <p style={{ margin: "0 0 1rem", color: "#64748b", fontSize: "0.875rem" }}>
            Ваша учётная запись не относится к рекламодателям. Войдите в соответствующий кабинет.
          </p>
          <button
            type="button"
            onClick={() => {
              logout();
            }}
            style={{
              padding: "0.5rem 1rem",
              background: "#dc2626",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontSize: "0.875rem",
            }}
          >
            Выйти
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
