import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const REQUIRED_PROVIDER = "local_advertiser";
const REQUIRED_PERMISSION = "campaigns.read";

function AccessDenied({
  title,
  message,
  onLogout,
}: {
  title: string;
  message: string;
  onLogout: () => void;
}) {
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
          {title}
        </h2>
        <p style={{ margin: "0 0 1rem", color: "#64748b", fontSize: "0.875rem" }}>
          {message}
        </p>
        <button
          type="button"
          onClick={onLogout}
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
      <AccessDenied
        title="Нет доступа к кабинету рекламодателя"
        message="Ваша учётная запись не относится к рекламодателям. Войдите в соответствующий кабинет."
        onLogout={() => logout()}
      />
    );
  }

  const perms = user.permissions ?? [];
  if (!perms.includes(REQUIRED_PERMISSION)) {
    return (
      <AccessDenied
        title="Нет прав на просмотр кампаний"
        message='У вашей учётной записи отсутствует разрешение "campaigns.read". Обратитесь к администратору.'
        onLogout={() => logout()}
      />
    );
  }

  return <>{children}</>;
}
