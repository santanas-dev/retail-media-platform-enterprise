import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CampaignListPage from "./pages/CampaignListPage";
import CampaignCreatePage from "./pages/CampaignCreatePage";
import CampaignDetailPage from "./pages/CampaignDetailPage";
import AdvertisersPage from "./pages/AdvertisersPage";
import UsersPage from "./pages/UsersPage";
import ADSettingsPage from "./pages/ADSettingsPage";
import CreativeModerationPage from "./pages/CreativeModerationPage";
import InventoryPage from "./pages/InventoryPage";
import ApprovalInboxPage from "./pages/ApprovalInboxPage";
import AuditLogPage from "./pages/AuditLogPage";
import DeviceHealthPage from "./pages/DeviceHealthPage";

/** Route-level error fallback — resets when the user navigates to a different route. */
function RouteErrorFallback() {
  return (
    <div
      role="alert"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        padding: "2rem",
        fontFamily: "system-ui, sans-serif",
        textAlign: "center",
        color: "#333",
      }}
    >
      <div style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "0.5rem" }}>
        Что-то пошло не так
      </div>
      <div style={{ color: "#666", marginBottom: "1.5rem", maxWidth: "400px" }}>
        Раздел временно недоступен.
      </div>
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: "0.6rem 1.5rem",
          fontSize: "0.95rem",
          border: "1px solid #ccc",
          borderRadius: "6px",
          background: "#fff",
          cursor: "pointer",
        }}
      >
        Обновить страницу
      </button>
    </div>
  );
}

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    errorElement: <RouteErrorFallback />,
    children: [
      { index: true, element: <Navigate to="/campaigns" replace /> },
      { path: "campaigns", element: <CampaignListPage /> },
      { path: "campaigns/new", element: <CampaignCreatePage /> },
      { path: "campaigns/:id", element: <CampaignDetailPage /> },
      { path: "advertisers", element: <AdvertisersPage /> },
      { path: "users", element: <UsersPage /> },
      { path: "settings/ad", element: <ADSettingsPage /> },
      { path: "creatives/moderation", element: <CreativeModerationPage /> },
      { path: "inventory", element: <InventoryPage /> },
      { path: "campaigns/approvals", element: <ApprovalInboxPage /> },
      { path: "audit", element: <AuditLogPage /> },
      { path: "devices", element: <DeviceHealthPage /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </ErrorBoundary>
  </StrictMode>,
);
