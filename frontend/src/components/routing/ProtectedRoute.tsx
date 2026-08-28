import { Navigate, Outlet, useLocation } from "react-router-dom";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/features/auth/hooks";
import { safeInternalPath } from "@/lib/navigation";
import { routes } from "@/lib/routes";

export function ProtectedRoute() {
  const {
    isAuthenticated,
    isBootstrapping,
    sessionExpired,
    profileLoadError,
    retryProfileLoad,
    logout,
    isLoggingOut,
  } = useAuth();
  const location = useLocation();

  if (isBootstrapping) {
    return (
      <LoadingState title="Starting Monetra" description="Restoring your session…" />
    );
  }

  if (!isAuthenticated) {
    return (
      <Navigate
        to={routes.login}
        replace
        state={{
          from: location.pathname,
          reason: sessionExpired ? "session-expired" : undefined,
        }}
      />
    );
  }

  if (profileLoadError) {
    return (
      <div className="stack">
        <ErrorState
          error={profileLoadError}
          title="Unable to load your profile"
          onRetry={retryProfileLoad}
        />
        <div>
          <Button
            variant="secondary"
            loading={isLoggingOut}
            onClick={() => void logout()}
          >
            Sign out
          </Button>
        </div>
      </div>
    );
  }

  return <Outlet />;
}

export function GuestRoute() {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();
  const redirectTo = safeInternalPath(
    (location.state as { from?: string } | null)?.from,
    routes.dashboard,
  );

  if (isBootstrapping) {
    return (
      <LoadingState title="Starting Monetra" description="Checking your session…" />
    );
  }

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return <Outlet />;
}
