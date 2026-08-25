import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

/**
 * AUTHZ-CROSS-PORTAL-001 — the operator console and the advertiser cabinet
 * are served from the same host on different ports, and browser cookies are
 * NOT isolated by port: the refresh cookie issued to the cabinet is sent to
 * this origin too, so a cabinet session silently restores here.
 *
 * Authorisation itself is enforced by the API and by PostgreSQL RLS — an
 * advertiser never receives another organisation's data.  This guard is
 * defence in depth: an advertiser-cabinet identity must not mount the
 * operator shell at all, so no operator screen renders and no operator
 * request is issued on their behalf.
 *
 * The signal is ``advertiser_organization_id`` from /api/v1/auth/me: it is
 * populated only for users that carry an advertiser scope.  Operators
 * (AD or break-glass) have none.
 */
function isAdvertiserCabinetSession(user: { advertiser_organization_id?: string | null }) {
  return Boolean(user.advertiser_organization_id);
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

  if (isAdvertiserCabinetSession(user)) {
    return (
      <div
        data-testid="wrong-portal-notice"
        style={{
          maxWidth: "34rem",
          margin: "6rem auto",
          padding: "2rem",
          textAlign: "center",
          color: "var(--rmp-text-primary)",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", marginBottom: "0.75rem" }}>
          Это раздел оператора
        </h1>
        <p style={{ marginBottom: "1.5rem", lineHeight: 1.5 }}>
          Вы вошли как рекламодатель. Работа с кампаниями вашей организации
          доступна в кабинете рекламодателя.
        </p>
        <button
          type="button"
          data-testid="wrong-portal-logout"
          onClick={logout}
          style={{
            padding: "0.5rem 1.25rem",
            border: "1px solid var(--rmp-gray-400)",
            borderRadius: "0.25rem",
            background: "transparent",
            color: "inherit",
            cursor: "pointer",
          }}
        >
          Выйти
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
