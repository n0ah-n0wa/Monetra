import { Navigate, Outlet, useLocation } from "react-router-dom";
import { LoadingState } from "@/components/states/LoadingState";
import { useAuth } from "@/features/auth/hooks";
import { routes } from "@/lib/routes";

export function ProtectedRoute() {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();

  if (isBootstrapping) {
    return <LoadingState title="Starting Monetra" description="Restoring your session…" />;
  }

  if (!isAuthenticated) {
    return <Navigate to={routes.login} replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}

export function GuestRoute() {
  const { isAuthenticated, isBootstrapping } = useAuth();
  const location = useLocation();
  const redirectTo =
    (location.state as { from?: string } | null)?.from ?? routes.dashboard;

  if (isBootstrapping) {
    return <LoadingState title="Starting Monetra" description="Checking your session…" />;
  }

  if (isAuthenticated) {
    return <Navigate to={redirectTo} replace />;
  }

  return <Outlet />;
}
