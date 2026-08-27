import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { fetchHealth } from "@/api/health";
import { useAuth } from "@/features/auth/hooks";
import { queryKeys } from "@/lib/query-client";
import { routes } from "@/lib/routes";

export function DashboardPage() {
  const { user } = useAuth();
  const healthQuery = useQuery({
    queryKey: queryKeys.health,
    queryFn: fetchHealth,
  });

  return (
    <PageContainer>
      <PageHeader
        title="Dashboard"
        description="Your financial overview will appear here as features are implemented."
      />
      <div className="dashboard-grid">
        <Card>
          <CardHeader>
            <CardTitle>Welcome back</CardTitle>
            <CardDescription>
              {user ? `Signed in as ${user.email}` : "Your session is active."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p>Reporting currency: {user?.reporting_currency ?? "—"}</p>
            <p>
              Jump to <Link to={routes.transactions}>transactions</Link> or{" "}
              <Link to={routes.accounts}>accounts</Link> to get started.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>System status</CardTitle>
            <CardDescription>Backend connectivity check.</CardDescription>
          </CardHeader>
          <CardContent>
            {healthQuery.isPending ? <LoadingState title="Checking API" /> : null}
            {healthQuery.isError ? (
              <ErrorState
                error={healthQuery.error}
                onRetry={() => void healthQuery.refetch()}
              />
            ) : null}
            {healthQuery.isSuccess ? (
              <Alert variant="success">API health: {healthQuery.data.status}</Alert>
            ) : null}
          </CardContent>
        </Card>
      </div>
    </PageContainer>
  );
}
