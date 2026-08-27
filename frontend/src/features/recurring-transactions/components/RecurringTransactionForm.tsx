import { useEffect, useMemo } from "react";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Account } from "@/features/accounts/api";
import type { Category } from "@/features/categories/api";
import {
  RECURRING_FREQUENCIES,
  formatRecurringFrequency,
  type RecurringTransaction,
  type RecurringTransactionCreatePayload,
  type RecurringTransactionUpdatePayload,
} from "@/features/recurring-transactions/api";
import {
  recurringTransactionCreateSchema,
  recurringTransactionUpdateSchema,
  todayIsoDate,
  type RecurringTransactionCreateFormValues,
  type RecurringTransactionUpdateFormValues,
} from "@/features/recurring-transactions/schemas";
import {
  TRANSACTION_TYPES,
  formatTransactionType,
  type TransactionType,
} from "@/features/transactions/api";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";

function filterCategoriesForType(
  categories: Category[],
  transactionType: TransactionType,
): Category[] {
  return categories.filter(
    (category) =>
      category.status === "active" &&
      (category.category_type === transactionType ||
        category.category_type === "universal"),
  );
}

function toCreatePayload(
  values: RecurringTransactionCreateFormValues,
): RecurringTransactionCreatePayload {
  return {
    account_id: values.account_id,
    category_id: values.category_id,
    transaction_type: values.transaction_type,
    amount: values.amount,
    description: values.description,
    frequency: values.frequency,
    start_date: values.start_date,
    end_date: values.end_date?.trim() ? values.end_date : null,
  };
}

function toUpdatePayload(
  values: RecurringTransactionUpdateFormValues,
): RecurringTransactionUpdatePayload {
  return {
    account_id: values.account_id,
    category_id: values.category_id,
    transaction_type: values.transaction_type,
    amount: values.amount,
    description: values.description,
    frequency: values.frequency,
    start_date: values.start_date,
    end_date: values.end_date?.trim() ? values.end_date : null,
  };
}

type RecurringTransactionCreateFormProps = {
  accounts: Account[];
  categories: Category[];
  submitting?: boolean;
  onSubmit: (payload: RecurringTransactionCreatePayload) => Promise<void>;
  onCancel?: () => void;
};

export function RecurringTransactionCreateForm({
  accounts,
  categories,
  submitting = false,
  onSubmit,
  onCancel,
}: RecurringTransactionCreateFormProps) {
  const form = useZodForm<RecurringTransactionCreateFormValues>(
    recurringTransactionCreateSchema,
    {
      defaultValues: {
        account_id: accounts[0]?.id ?? "",
        category_id: "",
        transaction_type: "expense",
        amount: "",
        description: "",
        frequency: "monthly",
        start_date: todayIsoDate(),
        end_date: "",
      },
    },
  );

  const transactionType = form.watch("transaction_type");
  const filteredCategories = useMemo(
    () => filterCategoriesForType(categories, transactionType),
    [categories, transactionType],
  );

  useEffect(() => {
    const currentCategoryId = form.getValues("category_id");
    const isValid = filteredCategories.some(
      (category) => category.id === currentCategoryId,
    );
    if (!isValid) {
      form.setValue("category_id", filteredCategories[0]?.id ?? "");
    }
  }, [filteredCategories, form]);

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(toCreatePayload(values));
    } catch (error) {
      applyApiErrorToForm(
        error,
        form.setError,
        "Unable to create recurring transaction.",
      );
    }
  });

  return (
    <form
      className="stack"
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
      aria-busy={submitting}
    >
      <RecurringTransactionFormFields
        form={form}
        accounts={accounts}
        filteredCategories={filteredCategories}
      />
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
          Create recurring transaction
        </Button>
      </div>
    </form>
  );
}

type RecurringTransactionEditFormProps = {
  recurring: RecurringTransaction;
  accounts: Account[];
  categories: Category[];
  submitting?: boolean;
  onSubmit: (payload: RecurringTransactionUpdatePayload) => Promise<void>;
  onCancel?: () => void;
};

export function RecurringTransactionEditForm({
  recurring,
  accounts,
  categories,
  submitting = false,
  onSubmit,
  onCancel,
}: RecurringTransactionEditFormProps) {
  const form = useZodForm<RecurringTransactionUpdateFormValues>(
    recurringTransactionUpdateSchema,
    {
      defaultValues: {
        account_id: recurring.account_id,
        category_id: recurring.category_id,
        transaction_type: recurring.transaction_type,
        amount: recurring.amount,
        description: recurring.description,
        frequency: recurring.frequency,
        start_date: recurring.start_date,
        end_date: recurring.end_date ?? "",
      },
    },
  );

  const transactionType = form.watch("transaction_type");
  const filteredCategories = useMemo(
    () => filterCategoriesForType(categories, transactionType),
    [categories, transactionType],
  );

  useEffect(() => {
    const currentCategoryId = form.getValues("category_id");
    const isValid = filteredCategories.some(
      (category) => category.id === currentCategoryId,
    );
    if (!isValid) {
      form.setValue("category_id", filteredCategories[0]?.id ?? "");
    }
  }, [filteredCategories, form]);

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(toUpdatePayload(values));
    } catch (error) {
      applyApiErrorToForm(
        error,
        form.setError,
        "Unable to update recurring transaction.",
      );
    }
  });

  return (
    <form
      className="stack"
      onSubmit={(event) => void handleSubmit(event)}
      noValidate
      aria-busy={submitting}
    >
      <RecurringTransactionFormFields
        form={form}
        accounts={accounts}
        filteredCategories={filteredCategories}
      />
      <p className="form-field__description">
        Currency ({recurring.currency}) is derived from the selected account.
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

type RecurringFormFieldsProps = {
  form: ReturnType<typeof useZodForm<RecurringTransactionCreateFormValues>>;
  accounts: Account[];
  filteredCategories: Category[];
};

function RecurringTransactionFormFields({
  form,
  accounts,
  filteredCategories,
}: RecurringFormFieldsProps) {
  return (
    <>
      <FormField
        id="account_id"
        label="Account"
        required
        error={form.formState.errors.account_id}
      >
        <Select
          id="account_id"
          hasError={Boolean(form.formState.errors.account_id)}
          {...form.register("account_id")}
        >
          <option value="">Select an account</option>
          {accounts.map((account) => (
            <option key={account.id} value={account.id}>
              {account.name} ({account.currency})
            </option>
          ))}
        </Select>
      </FormField>
      <FormField
        id="transaction_type"
        label="Type"
        required
        error={form.formState.errors.transaction_type}
      >
        <Select
          id="transaction_type"
          hasError={Boolean(form.formState.errors.transaction_type)}
          {...form.register("transaction_type")}
        >
          {TRANSACTION_TYPES.map((type) => (
            <option key={type} value={type}>
              {formatTransactionType(type)}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField
        id="category_id"
        label="Category"
        required
        error={form.formState.errors.category_id}
      >
        <Select
          id="category_id"
          hasError={Boolean(form.formState.errors.category_id)}
          {...form.register("category_id")}
        >
          <option value="">Select a category</option>
          {filteredCategories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField
        id="amount"
        label="Amount"
        required
        error={form.formState.errors.amount}
      >
        <Input
          id="amount"
          inputMode="decimal"
          autoFocus
          hasError={Boolean(form.formState.errors.amount)}
          {...form.register("amount")}
        />
      </FormField>
      <FormField
        id="description"
        label="Description"
        required
        error={form.formState.errors.description}
      >
        <Input
          id="description"
          autoComplete="off"
          hasError={Boolean(form.formState.errors.description)}
          {...form.register("description")}
        />
      </FormField>
      <FormField
        id="frequency"
        label="Frequency"
        required
        error={form.formState.errors.frequency}
      >
        <Select
          id="frequency"
          hasError={Boolean(form.formState.errors.frequency)}
          {...form.register("frequency")}
        >
          {RECURRING_FREQUENCIES.map((frequency) => (
            <option key={frequency} value={frequency}>
              {formatRecurringFrequency(frequency)}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField
        id="start_date"
        label="Start date"
        required
        description="First execution date and schedule anchor."
        error={form.formState.errors.start_date}
      >
        <Input
          id="start_date"
          type="date"
          hasError={Boolean(form.formState.errors.start_date)}
          {...form.register("start_date")}
        />
      </FormField>
      <FormField
        id="end_date"
        label="End date"
        description="Optional last date on which execution may occur."
        error={form.formState.errors.end_date}
      >
        <Input
          id="end_date"
          type="date"
          hasError={Boolean(form.formState.errors.end_date)}
          {...form.register("end_date")}
        />
      </FormField>
    </>
  );
}
