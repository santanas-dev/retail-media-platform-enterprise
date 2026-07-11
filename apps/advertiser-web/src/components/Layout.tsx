import { useState, useCallback } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import s from "./Layout.module.css";

const NAV_ITEMS = [
  { to: "/campaigns", label: "Кампании" },
  { to: "/creatives", label: "Креативы" },
  { to: "/reports", label: "Отчётность", disabled: true },
  { to: "/profile", label: "Профиль" },
];

export default function Layout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = useCallback(() => setMenuOpen(false), []);

  if (loading) {
    return <div className={s.loading}>Загрузка...</div>;
  }

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  const sidebarCls = `${s.sidebar}${menuOpen ? ` ${s.open}` : ""}`;
  const overlayCls = `${s.overlay}${menuOpen ? ` ${s.open}` : ""}`;

  return (
    <div className={s.shell}>
      {/* Hamburger toggle — visible only on narrow screens */}
      <button
        className={s.hamburger}
        onClick={() => setMenuOpen((o) => !o)}
        aria-label="Меню"
      >
        <span />
        <span />
        <span />
      </button>

      {/* Overlay behind sidebar on narrow screens */}
      <div className={overlayCls} onClick={closeMenu} />

      {/* Sidebar */}
      <aside className={sidebarCls}>
        <div className={s.logo}>Кабинет рекламодателя</div>
        <nav className={s.nav}>
          {NAV_ITEMS.map((item) =>
            item.disabled ? (
              <span
                key={item.to}
                className={`${s.navLink} ${s.navLinkDisabled}`}
                title="Скоро будет доступно"
              >
                {item.label}
              </span>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `${s.navLink}${isActive ? ` ${s.navLinkActive}` : ""}`
                }
                onClick={closeMenu}
              >
                {item.label}
              </NavLink>
            ),
          )}
          <div className={s.userRow}>
            <span className={s.userName}>
              {user?.display_name || user?.username || "—"}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              className={s.logoutBtn}
            >
              Выход
            </button>
          </div>
        </nav>
      </aside>

      {/* Main content */}
      <main className={s.main}>
        <Outlet />
      </main>
    </div>
  );
}
