import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useTheme } from "../theme/ThemeContext";
import { useIsNarrow } from "./useIsNarrow";
import s from "./ResponsiveShell.module.css";

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
  { to: "/advertiser-applications", label: "Заявки рекламодателей", requiredPermissions: ["advertiser_applications.read"] },
  { to: "/commerce/tariffs", label: "Коммерция", requiredPermissions: ["commerce.tariff_read"] },
];

function hasAnyPermission(userPermissions: string[] | undefined, required: string[]): boolean {
  if (!userPermissions || userPermissions.length === 0) return false;
  return required.some((p) => userPermissions.includes(p));
}

/** A menu glyph, not a word: there is no icon library in this stack and adding
 *  one for a single glyph would be a dependency for its own sake. */
function MenuIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="2"
            strokeLinecap="round" fill="none" />
    </svg>
  );
}

/**
 * PORTAL-UX-002 — the operator console's application shell.
 *
 * Desktop is deliberately untouched: the same 220px sidebar, the same active
 * item, the content in the same place. Below 768px the sidebar stops eating
 * 220px of a 390px screen — which cut off the page title and the last table
 * column — and becomes a drawer behind an overlay, closing on Escape, on the
 * overlay and on choosing a destination, with focus returned to the trigger.
 */
export default function Layout() {
  const { user, loading, logout } = useAuth();
  const { theme, setTheme, availableThemes } = useTheme();
  const navigate = useNavigate();
  const isNarrow = useIsNarrow();
  const [menuOpen, setMenuOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const drawerRef = useRef<HTMLElement | null>(null);
  const navId = useId();

  const visibleItems = useMemo(() => {
    if (!user) return [];
    return NAV_ITEMS.filter((item) =>
      hasAnyPermission(user.permissions, item.requiredPermissions),
    );
  }, [user]);

  const closeMenu = useCallback((returnFocus = true) => {
    setMenuOpen(false);
    if (returnFocus) triggerRef.current?.focus();
  }, []);

  // Widening the window must not leave a drawer state behind.
  useEffect(() => {
    if (!isNarrow) setMenuOpen(false);
  }, [isNarrow]);

  // Escape closes the drawer wherever focus happens to be.
  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        closeMenu();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [menuOpen, closeMenu]);

  // The page behind an open drawer must not scroll away under it.
  useEffect(() => {
    if (!menuOpen) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [menuOpen]);

  // Focus moves into the drawer when it opens, so a keyboard user is not left
  // behind on the trigger with an open menu they cannot reach.
  useEffect(() => {
    if (!menuOpen) return;
    const first = drawerRef.current?.querySelector<HTMLElement>(
      'a[href], button:not([disabled])',
    );
    first?.focus();
  }, [menuOpen]);

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

  const drawerMode = isNarrow;
  const drawerHidden = drawerMode && !menuOpen;
  const SidebarElement = (drawerMode ? "div" : "aside") as "div";
  const sidebarClasses = [
    s.sidebar,
    drawerMode && menuOpen ? s.sidebarOpen : "",
    drawerHidden ? s.sidebarHidden : "",
  ].filter(Boolean).join(" ");

  return (
    <div className={s.shell}>
      {drawerMode && (
        <button
          type="button"
          ref={triggerRef}
          className={s.menuButton}
          data-testid="nav-menu-toggle"
          aria-label="Меню"
          aria-expanded={menuOpen}
          aria-controls={navId}
          onClick={() => setMenuOpen((open) => !open)}
        >
          <MenuIcon />
          <span>Меню</span>
        </button>
      )}

      {drawerMode && menuOpen && (
        <button
          type="button"
          className={s.overlay}
          data-testid="nav-overlay"
          aria-label="Закрыть меню"
          onClick={() => closeMenu()}
        />
      )}

      {/* Desktop keeps the <aside> landmark it always had — the UI-smoke suite
          navigates through `aside nav a[href=…]`, and this slice must not move
          the console's furniture. In drawer mode it becomes a <div role="dialog">
          instead: an <aside> is implicitly a complementary landmark, and axe
          rightly refuses a dialog role on top of one. */}
      <SidebarElement
        id={navId}
        ref={drawerRef as never}
        className={sidebarClasses}
        data-testid="nav-sidebar"
        {...(drawerMode
          ? { role: "dialog", "aria-modal": true, "aria-label": "Меню разделов" }
          : {})}
        {...(drawerHidden ? { inert: "" as unknown as boolean, "aria-hidden": true } : {})}
      >
        <div className={s.brand}>ЦУР</div>
        <nav className={s.nav} aria-label="Разделы">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => {
                if (drawerMode) closeMenu(false);
              }}
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
              gap: "var(--rmp-space-2)",
            }}
          >
            <span
              title={user?.display_name || user?.username || undefined}
              style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}
            >
              {user?.display_name || user?.username || "—"}
            </span>
            <div
              data-testid="theme-toggle"
              role="radiogroup"
              aria-label="Тема оформления"
              style={{ display: "flex", gap: 1 }}
            >
              {availableThemes.map((t) => (
                <button
                  key={t}
                  type="button"
                  role="radio"
                  aria-checked={theme === t}
                  aria-label={t === "light" ? "Светлая тема" : "Тёмная тема"}
                  data-testid={`theme-option-${t}`}
                  onClick={() => setTheme(t)}
                  style={{
                    background: theme === t ? "var(--rmp-gray-600)" : "transparent",
                    border: "1px solid var(--rmp-gray-600)",
                    color: theme === t ? "var(--rmp-text-inverse)" : "var(--rmp-gray-400)",
                    padding: "0.15rem 0.45rem",
                    borderRadius: "var(--rmp-radius-sm)",
                    cursor: "pointer",
                    fontSize: "var(--rmp-font-size-xs)",
                    lineHeight: 1.4,
                    transition: "background 0.15s, color 0.15s",
                  }}
                >
                  {t === "light" ? "☀️" : "🌙"}
                </button>
              ))}
            </div>
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
      </SidebarElement>

      <main className={s.main}>
        <Outlet />
      </main>
    </div>
  );
}
