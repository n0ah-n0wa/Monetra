import { useMemo } from "react";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import {
  BUDGET_PERIODS,
  BUDGET_SCOPES,
  formatBudgetPeriod,
  formatBudgetScope,
  type Budget,
  type BudgetCreatePayload,
  type BudgetUpdatePayload,
} from "@/features/budgets/api";
import {
  budgetFormToCreatePayload,
  budgetFormToUpdatePayload,
} from "@/features/budgets/budget-form-payload";
import {
  budgetCreateSchema,
  budgetUpdateSchema,
  type BudgetCreateFormValues,
  type BudgetUpdateFormValues,
} from "@/features/budgets/schemas";
import { useCategoriesQuery } from "@/features/categories/hooks";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";

type BudgetCreateFormProps = {
  defaultCurrency?: string;
  submitting?: boolean;
  onSubmit: (payload: BudgetCreatePayload) => Promise<void>;
  onCancel?: () => void;
};

export function BudgetCreateForm({
  defaultCurrency = "USD",
  submitting = false,
  onSubmit,
  onCancel,
}: BudgetCreateFormProps) {
  const categoriesQuery = useCategoriesQuery({
    page: 1,
    page_size: 100,
    status: "active",
    category_type: "expense",
    include_system: false,
  });

  const form = useZodForm<BudgetCreateFormValues>(budgetCreateSchema, {
    defaultValues: {
      name: "",
      amount: "",
      currency: defaultCurrency,
      period: "monthly",
      scope: "overall",
      start_date: new Date().toISOString().slice(0, 10),
      end_date: "",
      warning_threshold_percent: 80,
      category_ids: [],
    },
  });

  const period = form.watch("period");
  const scope = form.watch("scope");
  const selectedCategoryIds = form.watch("category_ids");

  const expenseCategories = useMemo(
    () => categoriesQuery.data?.items ?? [],
    [categoriesQuery.data?.items],
  );

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(budgetFormToCreatePayload(values));
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to create budget.");
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
        id="amount"
        label="Amount"
        required
        error={form.formState.errors.amount}
      >
        <Input
          id="amount"
          inputMode="decimal"
          hasError={Boolean(form.formState.errors.amount)}
          {...form.register("amount")}
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
        id="period"
        label="Period"
        required
        error={form.formState.errors.period}
      >
        <Select
          id="period"
          hasError={Boolean(form.formState.errors.period)}
          {...form.register("period")}
        >
          {BUDGET_PERIODS.map((value) => (
            <option key={value} value={value}>
              {formatBudgetPeriod(value)}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField id="scope" label="Scope" required error={form.formState.errors.scope}>
        <Select
          id="scope"
          hasError={Boolean(form.formState.errors.scope)}
          {...form.register("scope")}
        >
          {BUDGET_SCOPES.map((value) => (
            <option key={value} value={value}>
              {formatBudgetScope(value)}
            </option>
          ))}
        </Select>
      </FormField>
      {scope === "category" ? (
        <fieldset
          className="form-field"
          aria-invalid={form.formState.errors.category_ids ? true : undefined}
          aria-describedby={
            form.formState.errors.category_ids ? "category_ids-error" : undefined
          }
        >
          <legend className="form-field__label">
            Categories <span aria-hidden="true">*</span>
          </legend>
          <p className="form-field__description">
            Select expense categories included in this budget.
          </p>
          {categoriesQuery.isPending ? (
            <p>Loading categories…</p>
          ) : expenseCategories.length === 0 ? (
            <p>No expense categories available. Create one first.</p>
          ) : (
            <div className="checkbox-list" role="group" aria-label="Budget categories">
              {expenseCategories.map((category) => {
                const checked = selectedCategoryIds.includes(category.id);
                return (
                  <label key={category.id} className="checkbox-list__item">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(event) => {
                        const current = form.getValues("category_ids");
                        if (event.target.checked) {
                          form.setValue("category_ids", [...current, category.id], {
                            shouldValidate: true,
                          });
                        } else {
                          form.setValue(
                            "category_ids",
                            current.filter((id) => id !== category.id),
                            { shouldValidate: true },
                          );
                        }
                      }}
                    />
                    <span>{category.name}</span>
                  </label>
                );
              })}
            </div>
          )}
          {form.formState.errors.category_ids ? (
            <p id="category_ids-error" className="form-field__error" role="alert">
              {form.formState.errors.category_ids.message}
            </p>
          ) : null}
        </fieldset>
      ) : null}
      <FormField
        id="start_date"
        label="Start date"
        required
        error={form.formState.errors.start_date}
      >
        <Input
          id="start_date"
          type="date"
          hasError={Boolean(form.formState.errors.start_date)}
          {...form.register("start_date")}
        />
      </FormField>
      {period === "custom" ? (
        <FormField
          id="end_date"
          label="End date"
          required
          error={form.formState.errors.end_date}
        >
          <Input
            id="end_date"
            type="date"
            hasError={Boolean(form.formState.errors.end_date)}
            {...form.register("end_date")}
          />
        </FormField>
      ) : null}
      <FormField
        id="warning_threshold_percent"
        label="Warning threshold (%)"
        required
        description="Show a warning when spending reaches this percentage of the budget."
        error={form.formState.errors.warning_threshold_percent}
      >
        <Input
          id="warning_threshold_percent"
          type="number"
          min={0}
          max={100}
          hasError={Boolean(form.formState.errors.warning_threshold_percent)}
          {...form.register("warning_threshold_percent")}
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
          Create budget
        </Button>
      </div>
    </form>
  );
}

type BudgetEditFormProps = {
  budget: Budget;
  submitting?: boolean;
  onSubmit: (payload: BudgetUpdatePayload) => Promise<void>;
  onCancel?: () => void;
};

export function BudgetEditForm({
  budget,
  submitting = false,
  onSubmit,
  onCancel,
}: BudgetEditFormProps) {
  const categoriesQuery = useCategoriesQuery({
    page: 1,
    page_size: 100,
    status: "active",
    category_type: "expense",
    include_system: false,
  });

  const form = useZodForm<BudgetUpdateFormValues>(budgetUpdateSchema, {
    defaultValues: {
      name: budget.name,
      amount: budget.amount,
      period: budget.period,
      scope: budget.scope,
      start_date: budget.start_date,
      end_date: budget.end_date ?? "",
      warning_threshold_percent: budget.warning_threshold_percent,
      category_ids: budget.categories.map((category) => category.id),
    },
  });

  const period = form.watch("period");
  const scope = form.watch("scope");
  const selectedCategoryIds = form.watch("category_ids");

  const expenseCategories = useMemo(
    () => categoriesQuery.data?.items ?? [],
    [categoriesQuery.data?.items],
  );

  const handleSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    try {
      await onSubmit(budgetFormToUpdatePayload(values));
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to update budget.");
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
        id="amount"
        label="Amount"
        required
        error={form.formState.errors.amount}
      >
        <Input
          id="amount"
          inputMode="decimal"
          hasError={Boolean(form.formState.errors.amount)}
          {...form.register("amount")}
        />
      </FormField>
      <p className="form-field__description">
        Currency ({budget.currency}) cannot be changed after creation.
      </p>
      <FormField
        id="period"
        label="Period"
        required
        error={form.formState.errors.period}
      >
        <Select
          id="period"
          hasError={Boolean(form.formState.errors.period)}
          {...form.register("period")}
        >
          {BUDGET_PERIODS.map((value) => (
            <option key={value} value={value}>
              {formatBudgetPeriod(value)}
            </option>
          ))}
        </Select>
      </FormField>
      <FormField id="scope" label="Scope" required error={form.formState.errors.scope}>
        <Select
          id="scope"
          hasError={Boolean(form.formState.errors.scope)}
          {...form.register("scope")}
        >
          {BUDGET_SCOPES.map((value) => (
            <option key={value} value={value}>
              {formatBudgetScope(value)}
            </option>
          ))}
        </Select>
      </FormField>
      {scope === "category" ? (
        <fieldset
          className="form-field"
          aria-invalid={form.formState.errors.category_ids ? true : undefined}
          aria-describedby={
            form.formState.errors.category_ids ? "category_ids-error" : undefined
          }
        >
          <legend className="form-field__label">
            Categories <span aria-hidden="true">*</span>
          </legend>
          {categoriesQuery.isPending ? (
            <p>Loading categories…</p>
          ) : (
            <div className="checkbox-list" role="group" aria-label="Budget categories">
              {expenseCategories.map((category) => {
                const checked = selectedCategoryIds.includes(category.id);
                return (
                  <label key={category.id} className="checkbox-list__item">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(event) => {
                        const current = form.getValues("category_ids");
                        if (event.target.checked) {
                          form.setValue("category_ids", [...current, category.id], {
                            shouldValidate: true,
                          });
                        } else {
                          form.setValue(
                            "category_ids",
                            current.filter((id) => id !== category.id),
                            { shouldValidate: true },
                          );
                        }
                      }}
                    />
                    <span>{category.name}</span>
                  </label>
                );
              })}
            </div>
          )}
          {form.formState.errors.category_ids ? (
            <p id="category_ids-error" className="form-field__error" role="alert">
              {form.formState.errors.category_ids.message}
            </p>
          ) : null}
        </fieldset>
      ) : null}
      <FormField
        id="start_date"
        label="Start date"
        required
        error={form.formState.errors.start_date}
      >
        <Input
          id="start_date"
          type="date"
          hasError={Boolean(form.formState.errors.start_date)}
          {...form.register("start_date")}
        />
      </FormField>
      {period === "custom" ? (
        <FormField
          id="end_date"
          label="End date"
          required
          error={form.formState.errors.end_date}
        >
          <Input
            id="end_date"
            type="date"
            hasError={Boolean(form.formState.errors.end_date)}
            {...form.register("end_date")}
          />
        </FormField>
      ) : null}
      <FormField
        id="warning_threshold_percent"
        label="Warning threshold (%)"
        required
        error={form.formState.errors.warning_threshold_percent}
      >
        <Input
          id="warning_threshold_percent"
          type="number"
          min={0}
          max={100}
          hasError={Boolean(form.formState.errors.warning_threshold_percent)}
          {...form.register("warning_threshold_percent")}
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
          Save changes
        </Button>
      </div>
    </form>
  );
}
