import { useEffect, useMemo, useRef } from "react";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Account } from "@/features/accounts/api";
import type { Category } from "@/features/categories/api";
import {
  TRANSACTION_TYPES,
  formatTransactionType,
  type Transaction,
  type TransactionType,
} from "@/features/transactions/api";
import {
  todayIsoDate,
  transactionFormSchema,
  type TransactionFormValues,
} from "@/features/transactions/schemas";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";

export type TransactionFormMode = "create" | "edit";

type TransactionFormProps = {
  mode: TransactionFormMode;
  accounts: Account[];
  categories: Category[];
  transaction?: Transaction;
  submitting?: boolean;
  focusAmountOnMount?: boolean;
  showAddAnother?: boolean;
  onSubmit: (
    values: TransactionFormValues,
    options?: { addAnother: boolean },
  ) => Promise<void>;
  onCancel?: () => void;
};

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

function buildDefaults(
  accounts: Account[],
  transaction?: Transaction,
): TransactionFormValues {
  const defaultAccount = accounts[0];
  return {
    account_id: transaction?.account_id ?? defaultAccount?.id ?? "",
    category_id: transaction?.category_id ?? "",
    transaction_type: transaction?.transaction_type ?? "expense",
    amount: transaction?.amount ?? "",
    description: transaction?.description ?? "",
    transaction_date: transaction?.transaction_date ?? todayIsoDate(),
    notes: transaction?.notes ?? "",
  };
}

export function TransactionForm({
  mode,
  accounts,
  categories,
  transaction,
  submitting = false,
  focusAmountOnMount = false,
  showAddAnother = false,
  onSubmit,
  onCancel,
}: TransactionFormProps) {
  const amountRef = useRef<HTMLInputElement | null>(null);
  const form = useZodForm<TransactionFormValues>(transactionFormSchema, {
    defaultValues: buildDefaults(accounts, transaction),
  });
  const amountRegister = form.register("amount", {
    setValueAs: (value: string) => value.trim(),
  });

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
      const first = filteredCategories[0];
      form.setValue("category_id", first?.id ?? "");
      return;
    }
    if (!currentCategoryId) {
      const first = filteredCategories[0];
      if (first) {
        form.setValue("category_id", first.id);
      }
    }
  }, [filteredCategories, form]);

  useEffect(() => {
    if (focusAmountOnMount) {
      amountRef.current?.focus();
    }
  }, [focusAmountOnMount]);

  const handleSubmit = (addAnother: boolean) =>
    form.handleSubmit(async (values) => {
      form.clearErrors("root");
      try {
        await onSubmit(values, { addAnother });
        if (addAnother && mode === "create") {
          form.reset({
            ...values,
            amount: "",
            description: "",
            notes: "",
            transaction_date: todayIsoDate(),
          });
          amountRef.current?.focus();
        }
      } catch (error) {
        applyApiErrorToForm(error, form.setError, "Unable to save transaction.");
      }
    });

  const activeAccounts = accounts.filter((account) => account.status === "active");

  return (
    <form
      className="stack transaction-form"
      onSubmit={(event) => {
        event.preventDefault();
        void handleSubmit(false)(event);
      }}
      noValidate
      aria-busy={submitting}
    >
      <div className="transaction-form__grid">
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
          id="transaction_date"
          label="Date"
          required
          error={form.formState.errors.transaction_date}
        >
          <Input
            id="transaction_date"
            type="date"
            hasError={Boolean(form.formState.errors.transaction_date)}
            {...form.register("transaction_date")}
          />
        </FormField>
      </div>

      <div className="transaction-form__grid">
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
            {activeAccounts.length === 0 ? (
              <option value="">No active accounts</option>
            ) : (
              activeAccounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {account.name} ({account.currency})
                </option>
              ))
            )}
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
            {filteredCategories.length === 0 ? (
              <option value="">No matching categories</option>
            ) : (
              filteredCategories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))
            )}
          </Select>
        </FormField>
      </div>

      <FormField
        id="amount"
        label="Amount"
        required
        description="Enter the exact amount; balances are calculated on the server."
        error={form.formState.errors.amount}
      >
        <Input
          id="amount"
          inputMode="decimal"
          autoComplete="off"
          hasError={Boolean(form.formState.errors.amount)}
          {...amountRegister}
          ref={(element: HTMLInputElement | null) => {
            amountRegister.ref(element);
            amountRef.current = element;
          }}
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

      <FormField id="notes" label="Notes" error={form.formState.errors.notes}>
        <Input id="notes" autoComplete="off" {...form.register("notes")} />
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
        {showAddAnother ? (
          <Button
            type="button"
            variant="secondary"
            loading={submitting}
            onClick={() => void handleSubmit(true)()}
          >
            Save and add another
          </Button>
        ) : null}
        <Button type="submit" loading={submitting}>
          {mode === "create" ? "Save transaction" : "Save changes"}
        </Button>
      </div>
    </form>
  );
}

export function transactionFormToCreatePayload(
  values: TransactionFormValues,
): import("@/features/transactions/api").TransactionCreatePayload {
  return {
    account_id: values.account_id,
    category_id: values.category_id,
    transaction_type: values.transaction_type,
    amount: values.amount.trim(),
    description: values.description,
    transaction_date: values.transaction_date,
    notes: values.notes?.trim() ? values.notes.trim() : null,
  };
}

export function transactionFormToUpdatePayload(
  values: TransactionFormValues,
): import("@/features/transactions/api").TransactionUpdatePayload {
  return {
    account_id: values.account_id,
    category_id: values.category_id,
    transaction_type: values.transaction_type,
    amount: values.amount.trim(),
    description: values.description,
    transaction_date: values.transaction_date,
    notes: values.notes?.trim() ? values.notes.trim() : null,
  };
}
