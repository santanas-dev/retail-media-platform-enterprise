import { useMemo } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

interface NavItem {
  to: string;
  label: string;
  requiredPermissions: string[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/campaigns", label: "Кампании", requiredPermissions: ["campaigns.read"] },
  { to: "/campaigns/approvals", label: "Согласование кампаний", requiredPermissions: ["campaigns.approve"] },
  { to: "/creatives/moderation", label: "Модерация креативов", requiredPermissions: ["creatives.moderate"] },
  { to: "/inventory", label: "Инвентарь", requiredPermissions: ["inventory.read"] },
  { to: "/advertisers", label: "Рекламодатели", requiredPermissions: ["advertisers.read"] },
  { to: "/users", label: "Пользователи", requiredPermissions: ["users.read"] },
  { to: "/settings/ad", label: "Настройки AD", requiredPermissions: ["users.manage"] },
  { to: "/audit", label: "Журнал аудита", requiredPermissions: ["audit.read"] },
  { to: "/devices", label: "Устройства", requiredPermissions: ["devices.read"] },
  { to: "/emergency", label: "Аварийный режим", requiredPermissions: ["emergency.read"] },
];

function hasAnyPermission(userPermissions: string[] | undefined, required: string[]): boolean {
  if (!userPermissions || userPermissions.length === 0) return false;
  return required.some((p) => userPermissions.includes(p));
}

export default function Layout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  const visibleItems = useMemo(() => {
    if (!user) return [];
    return NAV_ITEMS.filter((item) =>
      hasAnyPermission(user.permissions, item.requiredPermissions),
    );
  }, [user]);

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          minHeight: "100vh",
          fontFamily: "var(--rmp-font-family)",
          color: "var(--rmp-text-secondary)",
        }}
      >
        Загрузка...
      </div>
    );
  }

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div style={{ display: "flex", minHeight: "100vh", fontFamily: "var(--rmp-font-family)" }}>
      <aside
        style={{
          width: 220,
          background: "var(--rmp-sidebar-bg)",
          color: "var(--rmp-sidebar-text)",
          padding: "var(--rmp-space-4) 0",
          flexShrink: 0,
        }}
      >
        <div
          style={{
            padding: "0 var(--rmp-space-4) var(--rmp-space-4)",
            fontSize: "var(--rmp-font-size-base)",
            fontWeight: 600,
            color: "var(--rmp-text-inverse)",
            borderBottom: "1px solid var(--rmp-gray-700)",
            marginBottom: "var(--rmp-space-2)",
          }}
        >
          ЦУР
        </div>
        <nav style={{ display: "flex", flexDirection: "column", flex: 1 }}>
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => ({
                display: "block",
                padding: "var(--rmp-space-2) var(--rmp-space-4)",
                color: isActive ? "var(--rmp-text-inverse)" : "var(--rmp-gray-400)",
                textDecoration: "none",
                fontSize: "var(--rmp-font-size-base)",
                background: isActive ? "var(--rmp-sidebar-active)" : "transparent",
                transition: "background 0.15s, color 0.15s",
              })}
              onMouseEnter={(e) => {
                if (!e.currentTarget.classList.contains("active")) {
                  e.currentTarget.style.background = "var(--rmp-sidebar-hover)";
                }
              }}
              onMouseLeave={(e) => {
                if (!e.currentTarget.classList.contains("active")) {
                  e.currentTarget.style.background = "transparent";
                }
              }}
            >
              {item.label}
            </NavLink>
          ))}
          <div
            style={{
              marginTop: "auto",
              padding: "var(--rmp-space-3) var(--rmp-space-4)",
              borderTop: "1px solid var(--rmp-gray-700)",
              fontSize: "var(--rmp-font-size-sm)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
              {user?.display_name || user?.username || "—"}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              style={{
                background: "none",
                border: "1px solid var(--rmp-gray-600)",
                color: "var(--rmp-gray-400)",
                padding: "0.15rem 0.5rem",
                borderRadius: "var(--rmp-radius-sm)",
                cursor: "pointer",
                fontSize: "var(--rmp-font-size-xs)",
                transition: "background 0.15s, color 0.15s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--rmp-sidebar-hover)";
                e.currentTarget.style.color = "var(--rmp-text-inverse)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "none";
                e.currentTarget.style.color = "var(--rmp-gray-400)";
              }}
            >
              Выход
            </button>
          </div>
        </nav>
      </aside>
      <main
        style={{
          flex: 1,
          padding: "var(--rmp-space-6)",
          background: "var(--rmp-bg-page)",
          overflow: "auto",
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}
