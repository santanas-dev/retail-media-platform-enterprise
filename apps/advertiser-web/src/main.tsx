import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import { ErrorBoundary } from "./components/ErrorBoundary";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CampaignListPage from "./pages/CampaignListPage";
import CampaignDetailPage from "./pages/CampaignDetailPage";
import CreativeLibraryPage from "./pages/CreativeLibraryPage";
import ProfilePage from "./pages/ProfilePage";
import CampaignCreatePage from "./pages/CampaignCreatePage";
import ApplyAdvertiserPage from "./pages/ApplyAdvertiserPage";

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
    path: "/become-advertiser",
    element: <ApplyAdvertiserPage />,
  },
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
      { path: "creatives", element: <CreativeLibraryPage /> },
      { path: "profile", element: <ProfilePage /> },
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
