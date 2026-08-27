import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { useAccountsQuery } from "@/features/accounts/hooks";
import {
  type Goal,
  type GoalCreatePayload,
  type GoalUpdatePayload,
} from "@/features/goals/api";
import {
  goalCreateSchema,
  goalUpdateSchema,
  type GoalCreateFormValues,
  type GoalUpdateFormValues,
} from "@/features/goals/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";

function toCreatePayload(values: GoalCreateFormValues): GoalCreatePayload {
  return {
    name: values.name,
    target_amount: values.target_amount,
    current_amount: values.current_amount?.trim() ? values.current_amount : "0",
    currency: values.currency,
    target_date: values.target_date?.trim() ? values.target_date : null,
    linked_account_id: values.linked_account_id?.trim()
      ? values.linked_account_id
      : null,
  };
}

function toUpdatePayload(values: GoalUpdateFormValues): GoalUpdatePayload {
  return {
    name: values.name,
    target_amount: values.target_amount,
    current_amount: values.current_amount?.trim() ? values.current_amount : "0",
    target_date: values.target_date?.trim() ? values.target_date : null,
    linked_account_id: values.linked_account_id?.trim()
      ? values.linked_account_id
      : null,
  };
}

type GoalCreateFormProps = {
  defaultCurrency?: string;
  submitting?: boolean;
  onSubmit: (payload: GoalCreatePayload) => Promise<void>;
  onCancel?: () => void;
};

export function GoalCreateForm({
  defaultCurrency = "USD",
  submitting = false,
  onSubmit,
  onCancel,
}: GoalCreateFormProps) {
  const accountsQuery = useAccountsQuery({
    page: 1,
    page_size: 100,
    status: "active",
  });

  const form = useZodForm<GoalCreateFormValues>(goalCreateSchema, {
    defaultValues: {
      name: "",
      target_amount: "",
      current_amount: "0",
      currency: defaultCurrency,
      target_date: "",
      linked_account_id: "",
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(toCreatePayload(values));
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to create goal.");
    }
  });

  return (
    <form
      className="stack"
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
      aria-busy={submitting}
    >
      <FormField id="name" label="Name" required error={form.formState.errors.name}>
        <Input
          id="name"
          autoComplete="off"
          autoFocus
          hasError={Boolean(form.formState.errors.name)}
          {...form.register("name")}
        />
      </FormField>
      <FormField
        id="target_amount"
        label="Target amount"
        required
        error={form.formState.errors.target_amount}
      >
        <Input
          id="target_amount"
          inputMode="decimal"
          hasError={Boolean(form.formState.errors.target_amount)}
          {...form.register("target_amount")}
        />
      </FormField>
      <FormField
        id="current_amount"
        label="Current amount"
        description="Amount already saved toward this goal."
        error={form.formState.errors.current_amount}
      >
        <Input
          id="current_amount"
          inputMode="decimal"
          hasError={Boolean(form.formState.errors.current_amount)}
          {...form.register("current_amount")}
        />
      </FormField>
      <FormField
        id="currency"
        label="Currency"
        required
        description="ISO 4217 code, for example USD."
        error={form.formState.errors.currency}
      >
        <Input
          id="currency"
          autoComplete="off"
          maxLength={3}
          hasError={Boolean(form.formState.errors.currency)}
          {...form.register("currency")}
        />
      </FormField>
      <FormField
        id="target_date"
        label="Target date"
        description="Optional deadline for reaching this goal."
        error={form.formState.errors.target_date}
      >
        <Input
          id="target_date"
          type="date"
          hasError={Boolean(form.formState.errors.target_date)}
          {...form.register("target_date")}
        />
      </FormField>
      <FormField
        id="linked_account_id"
        label="Linked account"
        description="Optional account used to estimate contribution rate."
        error={form.formState.errors.linked_account_id}
      >
        <Select
          id="linked_account_id"
          hasError={Boolean(form.formState.errors.linked_account_id)}
          {...form.register("linked_account_id")}
        >
          <option value="">None</option>
          {accountsQuery.data?.items.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name} ({account.currency})
            </option>
          ))}
        </Select>
      </FormField>
      {form.formState.errors.root ? (
        <FormError>{form.formState.errors.root.message}</FormError>
      ) : null}
      <div className="modal__actions">
        {onCancel ? (
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
        ) : null}
        <Button type="submit" loading={submitting}>
          Create goal
        </Button>
      </div>
    </form>
  );
}

type GoalEditFormProps = {
  goal: Goal;
  submitting?: boolean;
  onSubmit: (payload: GoalUpdatePayload) => Promise<void>;
  onCancel?: () => void;
};

export function GoalEditForm({
  goal,
  submitting = false,
  onSubmit,
  onCancel,
}: GoalEditFormProps) {
  const accountsQuery = useAccountsQuery({
    page: 1,
    page_size: 100,
    status: "active",
  });

  const form = useZodForm<GoalUpdateFormValues>(goalUpdateSchema, {
    defaultValues: {
      name: goal.name,
      target_amount: goal.target_amount,
      current_amount: goal.current_amount,
      currency: goal.currency,
      target_date: goal.target_date ?? "",
      linked_account_id: goal.linked_account_id ?? "",
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(toUpdatePayload(values));
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to update goal.");
    }
  });

  return (
    <form
      className="stack"
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
      aria-busy={submitting}
    >
      <FormField id="name" label="Name" required error={form.formState.errors.name}>
        <Input
          id="name"
          autoComplete="off"
          autoFocus
          hasError={Boolean(form.formState.errors.name)}
          {...form.register("name")}
        />
      </FormField>
      <FormField
        id="target_amount"
        label="Target amount"
        required
        error={form.formState.errors.target_amount}
      >
        <Input
          id="target_amount"
          inputMode="decimal"
          hasError={Boolean(form.formState.errors.target_amount)}
          {...form.register("target_amount")}
        />
      </FormField>
      <FormField
        id="current_amount"
        label="Current amount"
        error={form.formState.errors.current_amount}
      >
        <Input
          id="current_amount"
          inputMode="decimal"
          hasError={Boolean(form.formState.errors.current_amount)}
          {...form.register("current_amount")}
        />
      </FormField>
      <p className="form-field__description">
        Currency ({goal.currency}) cannot be changed after creation.
      </p>
      <FormField
        id="target_date"
        label="Target date"
        error={form.formState.errors.target_date}
      >
        <Input
          id="target_date"
          type="date"
          hasError={Boolean(form.formState.errors.target_date)}
          {...form.register("target_date")}
        />
      </FormField>
      <FormField
        id="linked_account_id"
        label="Linked account"
        error={form.formState.errors.linked_account_id}
      >
        <Select
          id="linked_account_id"
          hasError={Boolean(form.formState.errors.linked_account_id)}
          {...form.register("linked_account_id")}
        >
          <option value="">None</option>
          {accountsQuery.data?.items.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name} ({account.currency})
            </option>
          ))}
        </Select>
      </FormField>
      {form.formState.errors.root ? (
        <FormError>{form.formState.errors.root.message}</FormError>
      ) : null}
      <div className="modal__actions">
        {onCancel ? (
          <Button
            type="button"
            variant="secondary"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </Button>
        ) : null}
        <Button type="submit" loading={submitting}>
          Save changes
        </Button>
      </div>
    </form>
  );
}
