import { useEffect, useId, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { FormError } from "@/components/forms/FormError";
import type { NotificationPreferences } from "@/features/notifications/api";
import { useUpdateNotificationPreferencesMutation } from "@/features/notifications/hooks";

type PreferenceField = {
  key: keyof Pick<
    NotificationPreferences,
    | "budget_warning_enabled"
    | "budget_exceeded_enabled"
    | "recurring_executed_enabled"
    | "goal_milestone_enabled"
    | "import_completed_enabled"
    | "import_failed_enabled"
    | "email_enabled"
  >;
  label: string;
  description: string;
};

const PREFERENCE_FIELDS: PreferenceField[] = [
  {
    key: "budget_warning_enabled",
    label: "Budget warnings",
    description: "Notify when a budget approaches its warning threshold.",
  },
  {
    key: "budget_exceeded_enabled",
    label: "Budget exceeded",
    description: "Notify when spending exceeds a budget limit.",
  },
  {
    key: "recurring_executed_enabled",
    label: "Recurring transactions",
    description: "Notify when a recurring transaction is executed.",
  },
  {
    key: "goal_milestone_enabled",
    label: "Goal milestones",
    description: "Notify when a financial goal reaches a milestone.",
  },
  {
    key: "import_completed_enabled",
    label: "Import completed",
    description: "Notify when a CSV import finishes successfully.",
  },
  {
    key: "import_failed_enabled",
    label: "Import failed",
    description: "Notify when a CSV import fails.",
  },
  {
    key: "email_enabled",
    label: "Email delivery",
    description: "Send notifications to your account email when enabled.",
  },
];

type NotificationPreferencesFormProps = {
  preferences: NotificationPreferences;
};

export function NotificationPreferencesForm({
  preferences,
}: NotificationPreferencesFormProps) {
  const formId = useId();
  const [values, setValues] = useState(preferences);
  const updateMutation = useUpdateNotificationPreferencesMutation();

  useEffect(() => {
    setValues(preferences);
  }, [preferences]);

  const isDirty = PREFERENCE_FIELDS.some(
    (field) => values[field.key] !== preferences[field.key],
  );

  function handleToggle(key: PreferenceField["key"], checked: boolean) {
    setValues((current) => ({ ...current, [key]: checked }));
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!isDirty) {
      return;
    }
    const payload = Object.fromEntries(
      PREFERENCE_FIELDS.filter(
        (field) => values[field.key] !== preferences[field.key],
      ).map((field) => [field.key, values[field.key]]),
    );
    await updateMutation.mutateAsync(payload);
  }

  return (
    <form
      id={formId}
      className="notification-preferences stack"
      onSubmit={(event) => void handleSubmit(event)}
      aria-labelledby="notification-preferences-heading"
    >
      <fieldset className="notification-preferences__fieldset">
        <legend id="notification-preferences-heading" className="import-section__title">
          Notification preferences
        </legend>
        <p className="import-section__description">
          Choose which in-app notifications you want to receive.
        </p>
        <ul className="notification-preferences__list">
          {PREFERENCE_FIELDS.map((field) => (
            <li key={field.key} className="notification-preferences__item">
              <label
                className="notification-preferences__label"
                htmlFor={`${formId}-${field.key}`}
              >
                <input
                  id={`${formId}-${field.key}`}
                  type="checkbox"
                  checked={values[field.key]}
                  onChange={(event) => handleToggle(field.key, event.target.checked)}
                />
                <span className="notification-preferences__text">
                  <span className="notification-preferences__name">{field.label}</span>
                  <span className="notification-preferences__description">
                    {field.description}
                  </span>
                </span>
              </label>
            </li>
          ))}
        </ul>
      </fieldset>

      <FormError error={updateMutation.error} />

      {updateMutation.isSuccess && !isDirty ? (
        <Alert variant="success" title="Preferences saved">
          Your notification settings were updated.
        </Alert>
      ) : null}

      <div className="import-confirm__actions">
        <Button type="submit" loading={updateMutation.isPending} disabled={!isDirty}>
          Save preferences
        </Button>
      </div>
    </form>
  );
}
