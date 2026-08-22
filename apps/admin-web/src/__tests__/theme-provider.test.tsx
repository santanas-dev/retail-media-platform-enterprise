import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { ThemeProvider, useTheme, type ThemeId } from "../theme/ThemeContext";

/** Minimal consumer that renders the current theme value. */
function ThemeConsumer() {
  const { theme, setTheme, availableThemes } = useTheme();
  return (
    <div>
      <span data-testid="theme-value">{theme}</span>
      <span data-testid="available-count">{availableThemes.length}</span>
      <button
        data-testid="set-light"
        onClick={() => setTheme("light")}
      >
        Set Light
      </button>
      <button
        data-testid="set-dark"
        onClick={() => setTheme("dark")}
      >
        Set Dark
      </button>
      {/* test invalid theme call */}
      <button
        data-testid="set-invalid"
        onClick={() => setTheme("purple" as ThemeId)}
      >
        Set Invalid
      </button>
    </div>
  );
}

function renderProvider() {
  return render(
    <ThemeProvider>
      <ThemeConsumer />
    </ThemeProvider>,
  );
}

describe("ThemeProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  afterEach(() => {
    localStorage.clear();
    delete document.documentElement.dataset.theme;
  });

  it("sets data-theme=light on mount", () => {
    renderProvider();
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("provides light as default theme", () => {
    renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("light");
  });

  it("exposes availableThemes with light and dark", () => {
    renderProvider();
    expect(screen.getByTestId("available-count").textContent).toBe("2");
  });

  it("reads persisted light theme from localStorage on mount", () => {
    localStorage.setItem("rmp-admin-theme", "light");
    renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("reads persisted dark theme from localStorage on mount", () => {
    localStorage.setItem("rmp-admin-theme", "dark");
    renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("falls back to light for invalid stored theme", () => {
    localStorage.setItem("rmp-admin-theme", "purple");
    renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("falls back to light for garbage stored value", () => {
    localStorage.setItem("rmp-admin-theme", "garbage");
    renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("light");
  });

  it("falls back to light when localStorage is empty", () => {
    renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("light");
  });

  it("persists light theme to localStorage on setTheme", () => {
    renderProvider();
    act(() => {
      screen.getByTestId("set-light").click();
    });
    expect(localStorage.getItem("rmp-admin-theme")).toBe("light");
  });

  it("persists dark theme to localStorage on setTheme", () => {
    renderProvider();
    act(() => {
      screen.getByTestId("set-dark").click();
    });
    expect(localStorage.getItem("rmp-admin-theme")).toBe("dark");
    expect(screen.getByTestId("theme-value").textContent).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("toggles dark → light → dark correctly", () => {
    renderProvider();
    act(() => {
      screen.getByTestId("set-dark").click();
    });
    expect(screen.getByTestId("theme-value").textContent).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");

    act(() => {
      screen.getByTestId("set-light").click();
    });
    expect(screen.getByTestId("theme-value").textContent).toBe("light");
    expect(document.documentElement.dataset.theme).toBe("light");

    act(() => {
      screen.getByTestId("set-dark").click();
    });
    expect(screen.getByTestId("theme-value").textContent).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("persists dark across remount (simulated reload)", () => {
    localStorage.setItem("rmp-admin-theme", "dark");
    const { unmount } = renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");

    // Simulate page reload — unmount and remount with localStorage still set
    unmount();
    delete document.documentElement.dataset.theme;

    renderProvider();
    expect(screen.getByTestId("theme-value").textContent).toBe("dark");
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("rmp-admin-theme")).toBe("dark");
  });

  it("ignores setTheme call with invalid theme", () => {
    renderProvider();
    act(() => {
      screen.getByTestId("set-invalid").click();
    });
    // Theme should still be light, not changed
    expect(screen.getByTestId("theme-value").textContent).toBe("light");
  });

  it("throws when useTheme is used outside provider", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<ThemeConsumer />)).toThrow(
      "useTheme must be used within ThemeProvider",
    );
    spy.mockRestore();
  });
});
