import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
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
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </StrictMode>,
);
