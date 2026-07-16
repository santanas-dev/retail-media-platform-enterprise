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
  // system_admin typically has all permissions — check one of them
  return required.some((p) => userPermissions.includes(p));
}

const styles = {
  shell: {
    display: "flex",
    minHeight: "100vh",
    fontFamily: "system-ui, sans-serif",
  },
  sidebar: {
    width: 220,
    background: "#1e293b",
    color: "#e2e8f0",
    padding: "1rem 0",
    flexShrink: 0,
  },
  logo: {
    padding: "0 1rem 1rem",
    fontSize: "0.875rem",
    fontWeight: 600,
    color: "#fff",
    borderBottom: "1px solid #334155",
    marginBottom: "0.5rem",
  },
  navLink: (active: boolean): React.CSSProperties => ({
    display: "block",
    padding: "0.5rem 1rem",
    color: active ? "#fff" : "#94a3b8",
    textDecoration: "none",
    fontSize: "0.875rem",
    background: active ? "#334155" : "transparent",
  }),
  userRow: {
    marginTop: "auto",
    padding: "0.75rem 1rem",
    borderTop: "1px solid #334155",
    fontSize: "0.8rem",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  logoutBtn: {
    background: "none",
    border: "1px solid #475569",
    color: "#94a3b8",
    padding: "0.2rem 0.5rem",
    borderRadius: 4,
    cursor: "pointer",
    fontSize: "0.75rem",
  },
  main: {
    flex: 1,
    padding: "1.5rem",
    background: "#f8fafc",
    overflow: "auto",
  },
  loading: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    fontFamily: "system-ui, sans-serif",
    color: "#64748b",
  },
};

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
    return <div style={styles.loading}>Загрузка...</div>;
  }

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div style={styles.shell}>
      <aside style={styles.sidebar}>
        <div style={styles.logo}>ЦУР</div>
        <nav style={{ display: "flex", flexDirection: "column", flex: 1 }}>
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              style={({ isActive }) => styles.navLink(isActive)}
            >
              {item.label}
            </NavLink>
          ))}
          <div style={styles.userRow}>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>
              {user?.display_name || user?.username || "—"}
            </span>
            <button type="button" onClick={handleLogout} style={styles.logoutBtn}>
              Выход
            </button>
          </div>
        </nav>
      </aside>
      <main style={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
