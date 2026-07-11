import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const NAV_ITEMS = [
  { to: "/campaigns", label: "Кампании" },
  { to: "/creatives", label: "Креативы" },
  { to: "/reports", label: "Отчётность", disabled: true },
  { to: "/profile", label: "Профиль", disabled: true },
];

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
  navLink: (active: boolean, disabled?: boolean): React.CSSProperties => ({
    display: "block",
    padding: "0.5rem 1rem",
    color: disabled ? "#64748b" : active ? "#fff" : "#94a3b8",
    textDecoration: "none",
    fontSize: "0.875rem",
    background: active ? "#334155" : "transparent",
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.6 : 1,
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
        <div style={styles.logo}>Кабинет рекламодателя</div>
        <nav style={{ display: "flex", flexDirection: "column", flex: 1 }}>
          {NAV_ITEMS.map((item) => (
            item.disabled ? (
              <span
                key={item.to}
                style={styles.navLink(false, true)}
                title="Скоро будет доступно"
              >
                {item.label}
              </span>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                style={({ isActive }) => styles.navLink(isActive)}
              >
                {item.label}
              </NavLink>
            )
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
