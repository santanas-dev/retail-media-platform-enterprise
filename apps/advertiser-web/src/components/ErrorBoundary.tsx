import { Component, type ErrorInfo, type ReactNode } from "react";

export interface ErrorBoundaryProps {
  children: ReactNode;
  /** Key that, when changed, resets the error state (e.g. location.pathname). */
  resetKey?: string;
  /** Custom fallback element. If omitted, default Russian fallback is used. */
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Top-level and route-level error boundary.
 *
 * Catches render/runtime errors in its subtree, displays a friendly
 * Russian fallback with a "refresh" button instead of a white screen.
 *
 * Route-level reset:
 *   Pass `resetKey={location.pathname}` so that navigating to a new
 *   route clears the error state.  Without this, one crashed route
 *   would show the fallback forever, even after navigating away.
 *
 * Security:
 *   Stack traces are never rendered in the fallback UI.
 *   In development, the error message is shown for debugging
 *   (no secrets/stack).  In production, only the friendly message.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  public state: ErrorBoundaryState = { hasError: false, error: null };

  private prevResetKey: string | undefined;

  public static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, info: ErrorInfo): void {
    // Log to console for dev/debug — never rendered in UI
    if (import.meta.env.DEV) {
      console.error("[ErrorBoundary]", error.message, info.componentStack);
    }
    // TODO: future telemetry hook — report to backend observability
  }

  public componentDidUpdate(
    _prevProps: ErrorBoundaryProps,
    _prevState: ErrorBoundaryState,
  ): void {
    if (
      this.props.resetKey !== undefined &&
      this.props.resetKey !== this.prevResetKey
    ) {
      this.setState({ hasError: false, error: null });
    }
    this.prevResetKey = this.props.resetKey;
  }

  private handleRefresh = (): void => {
    window.location.reload();
  };

  public render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return <DefaultFallback error={this.state.error} onRefresh={this.handleRefresh} />;
    }
    return this.props.children;
  }
}

// ── Default fallback ──────────────────────────────────────────────

interface DefaultFallbackProps {
  error: Error | null;
  onRefresh: () => void;
}

function DefaultFallback({ error, onRefresh }: DefaultFallbackProps) {
  const isDev = import.meta.env.DEV;
  const rawMessage = isDev && error ? error.message : "";
  // Strip JWT-like tokens and credential patterns from dev message
  const message = rawMessage
    .replace(/\beyJ[a-zA-Z0-9_-]+\.(?:[a-zA-Z0-9_-]+\.)?[a-zA-Z0-9_-]*/g, "[redacted]")
    .replace(/\b(?:access_token|refresh_token|password|secret|api_key)=[^\s,;)]+/gi, "$1=[redacted]");

  return (
    <div
      role="alert"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        padding: "2rem",
        fontFamily: "system-ui, sans-serif",
        textAlign: "center",
        color: "#333",
      }}
    >
      <div style={{ fontSize: "1.5rem", fontWeight: 600, marginBottom: "0.5rem" }}>
        Что-то пошло не так
      </div>
      <div style={{ color: "#666", marginBottom: "1.5rem", maxWidth: "400px" }}>
        Раздел временно недоступен. Попробуйте обновить страницу.
      </div>
      {message && (
        <div
          style={{
            fontFamily: "monospace",
            fontSize: "0.8rem",
            color: "#888",
            background: "#f5f5f5",
            padding: "0.5rem 1rem",
            borderRadius: "4px",
            marginBottom: "1.5rem",
            maxWidth: "500px",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {message}
        </div>
      )}
      <button
        onClick={onRefresh}
        style={{
          padding: "0.6rem 1.5rem",
          fontSize: "0.95rem",
          border: "1px solid #ccc",
          borderRadius: "6px",
          background: "#fff",
          cursor: "pointer",
        }}
      >
        Обновить страницу
      </button>
    </div>
  );
}
