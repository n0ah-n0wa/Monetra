import { useQuery } from "@tanstack/react-query";
import { FeaturePlaceholder } from "@/components/FeaturePlaceholder";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { useAuth } from "@/features/auth/hooks";
import { fetchNotificationPreferences } from "@/features/notifications/api";
import { queryKeys } from "@/lib/query-client";

export function SettingsPage() {
  const { user } = useAuth();
  const preferencesQuery = useQuery({
    queryKey: queryKeys.notifications.preferences,
    queryFn: fetchNotificationPreferences,
  });

  return (
    <FeaturePlaceholder
      title="Settings"
      description="Manage profile preferences, reporting currency, and notification delivery."
    >
      {user ? <p>Signed in as {user.email}</p> : null}
      {preferencesQuery.isPending ? <LoadingState title="Loading preferences" /> : null}
      {preferencesQuery.isError ? (
        <ErrorState error={preferencesQuery.error} onRetry={() => void preferencesQuery.refetch()} />
      ) : null}
      {preferencesQuery.isSuccess ? (
        <p>Email notifications: {preferencesQuery.data.email_enabled ? "enabled" : "disabled"}</p>
      ) : null}
    </FeaturePlaceholder>
  );
}
