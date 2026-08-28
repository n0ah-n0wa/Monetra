import { Link } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { useAuth } from "@/features/auth/hooks";
import { useNotificationPreferencesQuery } from "@/features/notifications/hooks";
import { routes } from "@/lib/routes";

export function SettingsPage() {
  const { user } = useAuth();
  const preferencesQuery = useNotificationPreferencesQuery();

  return (
    <PageContainer>
      <PageHeader
        title="Settings"
        description="View your account details and manage notification delivery."
      />

      {user ? (
        <section aria-labelledby="settings-profile-heading" className="card stack">
          <h2 id="settings-profile-heading" className="section-title">
            Profile
          </h2>
          <p className="section-description">
            Signed in as {user.email}. Reporting currency: {user.reporting_currency}.
          </p>
        </section>
      ) : null}

      <section aria-labelledby="settings-notifications-heading" className="card">
        <h2 id="settings-notifications-heading" className="section-title">
          Notifications
        </h2>
        {preferencesQuery.isPending ? (
          <LoadingState title="Loading preferences" />
        ) : null}
        {preferencesQuery.isError ? (
          <ErrorState
            error={preferencesQuery.error}
            title="Unable to load notification preferences"
            onRetry={() => void preferencesQuery.refetch()}
          />
        ) : null}
        {preferencesQuery.isSuccess ? (
          <p className="section-description">
            Email notifications are{" "}
            {preferencesQuery.data.email_enabled ? "enabled" : "disabled"}.{" "}
            <Link to={routes.notifications}>Manage notification preferences</Link>
          </p>
        ) : null}
      </section>
    </PageContainer>
  );
}
