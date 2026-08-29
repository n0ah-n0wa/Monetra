import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { routes } from "@/lib/routes";

type AppErrorBoundaryProps = {
  children: ReactNode;
};

type AppErrorBoundaryState = {
  hasError: boolean;
};

export class AppErrorBoundary extends Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("Unhandled application error", error, info);
  }

  private handleReload = (): void => {
    window.location.assign(routes.dashboard);
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="error-boundary" role="alert">
          <h1>Something went wrong</h1>
          <p>An unexpected error occurred while loading this page.</p>
          <div className="error-boundary__actions">
            <button
              type="button"
              className="btn btn--primary btn--md"
              onClick={this.handleReload}
            >
              Go to dashboard
            </button>
            <Link className="btn btn--secondary btn--md" to={routes.dashboard}>
              Try again
            </Link>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
