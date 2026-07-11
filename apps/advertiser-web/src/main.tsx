import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, RouterProvider, Navigate } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import CampaignListPage from "./pages/CampaignListPage";
import CampaignDetailPage from "./pages/CampaignDetailPage";
import CreativeLibraryPage from "./pages/CreativeLibraryPage";
import ProfilePage from "./pages/ProfilePage";
import CampaignCreatePage from "./pages/CampaignCreatePage";

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
      { path: "creatives", element: <CreativeLibraryPage /> },
      { path: "profile", element: <ProfilePage /> },
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
