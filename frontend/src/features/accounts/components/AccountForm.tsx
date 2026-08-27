import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  ACCOUNT_TYPES,
  formatAccountType,
  type Account,
} from "@/features/accounts/api";
import {
  accountCreateSchema,
  accountUpdateSchema,
  type AccountCreateFormValues,
  type AccountUpdateFormValues,
} from "@/features/accounts/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";

type AccountCreateFormProps = {
  defaultCurrency?: string;
  submitting?: boolean;
  onSubmit: (values: AccountCreateFormValues) => Promise<void>;
  onCancel?: () => void;
};

export function AccountCreateForm({
  defaultCurrency = "USD",
  submitting = false,
  onSubmit,
  onCancel,
}: AccountCreateFormProps) {
  const form = useZodForm<AccountCreateFormValues>(accountCreateSchema, {
    defaultValues: {
      name: "",
      account_type: "bank",
      currency: defaultCurrency,
      opening_balance: "0",
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(values);
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to create account.");
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
        id="account_type"
        label="Type"
        required
        error={form.formState.errors.account_type}
      >
        <Select
          id="account_type"
          hasError={Boolean(form.formState.errors.account_type)}
          {...form.register("account_type")}
        >
          {ACCOUNT_TYPES.map((type) => (
            <option key={type} value={type}>
              {formatAccountType(type)}
            </option>
          ))}
        </Select>
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
        id="opening_balance"
        label="Opening balance"
        required
        error={form.formState.errors.opening_balance}
      >
        <Input
          id="opening_balance"
          inputMode="decimal"
          hasError={Boolean(form.formState.errors.opening_balance)}
          {...form.register("opening_balance")}
        />
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
          Create account
        </Button>
      </div>
    </form>
  );
}

type AccountEditFormProps = {
  account: Account;
  submitting?: boolean;
  onSubmit: (values: AccountUpdateFormValues) => Promise<void>;
  onCancel?: () => void;
};

export function AccountEditForm({
  account,
  submitting = false,
  onSubmit,
  onCancel,
}: AccountEditFormProps) {
  const form = useZodForm<AccountUpdateFormValues>(accountUpdateSchema, {
    defaultValues: {
      name: account.name,
      account_type: account.account_type,
    },
  });

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(values);
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to update account.");
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
        id="account_type"
        label="Type"
        required
        error={form.formState.errors.account_type}
      >
        <Select
          id="account_type"
          hasError={Boolean(form.formState.errors.account_type)}
          {...form.register("account_type")}
        >
          {ACCOUNT_TYPES.map((type) => (
            <option key={type} value={type}>
              {formatAccountType(type)}
            </option>
          ))}
        </Select>
      </FormField>
      <p className="form-field__description">
        Currency and opening balance cannot be changed after creation.
      </p>
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
