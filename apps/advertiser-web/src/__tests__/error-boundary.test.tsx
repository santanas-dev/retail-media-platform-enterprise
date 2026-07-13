/**
 * Tests for ErrorBoundary component (advertiser-web).
 *
 * Covers:
 *   - Throwing component renders fallback, not white screen
 *   - Fallback has refresh button
 *   - Route change resets error state
 *   - No stack trace / secret text in fallback
 *   - Normal route still renders
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ErrorBoundary } from "../components/ErrorBoundary";

// ── Helper: component that always throws ──

function Bomb(): never {
  throw new Error("TEST_ERROR_simulated_crash");
}

function SafeComponent() {
  return <div>Everything is fine</div>;
}

// ── Tests ──

describe("ErrorBoundary", () => {
  it("renders children normally when no error", () => {
    render(
      <ErrorBoundary>
        <SafeComponent />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Everything is fine")).toBeDefined();
  });

  it("shows fallback when child throws during render", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Что-то пошло не так")).toBeDefined();
    expect(
      screen.getByText(/Раздел временно недоступен/),
    ).toBeDefined();

    spy.mockRestore();
  });

  it("fallback has a refresh button", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    const btn = screen.getByRole("button", { name: /Обновить страницу/i });
    expect(btn).toBeDefined();

    spy.mockRestore();
  });

  it("resets error state when resetKey changes", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    const { rerender } = render(
      <ErrorBoundary resetKey="route-a">
        <Bomb />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Что-то пошло не так")).toBeDefined();

    rerender(
      <ErrorBoundary resetKey="route-b">
        <SafeComponent />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Everything is fine")).toBeDefined();

    spy.mockRestore();
  });

  it("does not render stack trace in fallback", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <ErrorBoundary>
        <Bomb />
      </ErrorBoundary>,
    );

    const container = document.body.textContent || "";
    expect(container).not.toContain("at Bomb");
    expect(container).not.toContain("at ErrorBoundary");

    spy.mockRestore();
  });

  it("does not leak secret-like patterns in fallback", () => {
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    function SecretBomb(): never {
      throw new Error("access_token=eyJhbG...load");
    }

    render(
      <ErrorBoundary>
        <SecretBomb />
      </ErrorBoundary>,
    );

    const container = document.body.textContent || "";
    expect(container).not.toContain("eyJ");
    expect(container).not.toContain("access_token");

    spy.mockRestore();
  });
});
