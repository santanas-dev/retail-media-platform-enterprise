import { useState, useCallback } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { CAMPAIGNS_MANAGE, hasPermission } from "../auth/permissions";
import s from "./Layout.module.css";

type NavItem = {
  to: string;
  label: string;
  testid?: string;
  disabled?: boolean;
  /** Hide the item unless the user holds this permission. */
  permission?: string;
};

const NAV_ITEMS: NavItem[] = [
  { to: "/dashboard", label: "Кабинет" },
  { to: "/campaigns", label: "Кампании", testid: "nav-campaigns" },
  // CAMPAIGN-PERMISSION-SPLIT-001: creative upload is operator-only.
  { to: "/creatives", label: "Креативы", permission: CAMPAIGNS_MANAGE },
  { to: "/briefs", label: "Заявки", testid: "nav-briefs" },
  { to: "/documents", label: "Документы", disabled: true },
  { to: "/support", label: "Поддержка", disabled: true },
  { to: "/profile", label: "Профиль" },
];

export default function Layout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const closeMenu = useCallback(() => setMenuOpen(false), []);

  // Hide what the signed-in user provably cannot use. The API is still
  // the boundary — this only avoids offering a guaranteed 403.
  const navItems = NAV_ITEMS.filter(
    (item) => !item.permission || hasPermission(user, item.permission),
  );

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
          {navItems.map((item) =>
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
                {...("testid" in item ? { "data-testid": (item as any).testid } : {})}
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
