import { useMemo } from "react";
import { Link } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { FormError } from "@/components/forms/FormError";
import { FormField } from "@/components/forms/FormField";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import type { Account } from "@/features/accounts/api";
import { useAccountsQuery } from "@/features/accounts/hooks";
import { transferSchema, type TransferFormValues } from "@/features/transfers/schemas";
import {
  useCreateTransferMutation,
  useTransfersQuery,
} from "@/features/transfers/hooks";
import { applyApiErrorToForm, useZodForm } from "@/lib/form";
import { formatMoneyDisplay } from "@/lib/money";
import { routes } from "@/lib/routes";

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function accountLabel(account: Account): string {
  return `${account.name} (${account.currency})`;
}

export function TransfersPage() {
  const accountsQuery = useAccountsQuery({ status: "active", page_size: 100 });
  const transfersQuery = useTransfersQuery({ page: 1, page_size: 20 });
  const createMutation = useCreateTransferMutation();

  const form = useZodForm<TransferFormValues>(transferSchema, {
    defaultValues: {
      source_account_id: "",
      destination_account_id: "",
      source_amount: "",
      transaction_date: todayIsoDate(),
      description: "",
    },
    mode: "onSubmit",
  });

  const accounts = useMemo(
    () => accountsQuery.data?.items ?? [],
    [accountsQuery.data?.items],
  );
  const accountById = useMemo(
    () => new Map(accounts.map((account) => [account.id, account])),
    [accounts],
  );

  const sourceAccountId = form.watch("source_account_id");
  const destinationAccountId = form.watch("destination_account_id");
  const sourceAccount = sourceAccountId ? accountById.get(sourceAccountId) : undefined;
  const destinationAccount = destinationAccountId
    ? accountById.get(destinationAccountId)
    : undefined;
  const crossCurrencyMismatch =
    sourceAccount &&
    destinationAccount &&
    sourceAccount.currency !== destinationAccount.currency;

  if (accountsQuery.isPending) {
    return (
      <PageContainer>
        <LoadingState title="Loading accounts" />
      </PageContainer>
    );
  }

  if (accountsQuery.isError) {
    return (
      <PageContainer>
        <ErrorState
          error={accountsQuery.error}
          onRetry={() => void accountsQuery.refetch()}
        />
      </PageContainer>
    );
  }

  if (accounts.length < 2) {
    return (
      <PageContainer>
        <PageHeader title="Transfers" description="Move money between your accounts." />
        <EmptyState
          title="At least two accounts required"
          description="Create another account before transferring funds."
        >
          <Link className="btn btn--primary" to={routes.accounts}>
            Manage accounts
          </Link>
        </EmptyState>
      </PageContainer>
    );
  }

  const onSubmit = form.handleSubmit(async (values) => {
    form.clearErrors("root");
    const source = accountById.get(values.source_account_id);
    const destination = accountById.get(values.destination_account_id);
    if (!source || !destination) {
      form.setError("root", { message: "Select valid accounts." });
      return;
    }
    if (source.currency !== destination.currency) {
      form.setError("root", {
        message:
          "Cross-currency transfers require matching currencies in this release.",
      });
      return;
    }
    try {
      await createMutation.mutateAsync({
        source_account_id: values.source_account_id,
        destination_account_id: values.destination_account_id,
        source_amount: values.source_amount,
        transaction_date: values.transaction_date,
        description: values.description?.trim() || undefined,
      });
      form.reset({
        source_account_id: "",
        destination_account_id: "",
        source_amount: "",
        transaction_date: todayIsoDate(),
        description: "",
      });
    } catch (error) {
      applyApiErrorToForm(error, form.setError, "Unable to create transfer.");
    }
  });

  return (
    <PageContainer>
      <PageHeader
        title="Transfers"
        description="Move money between accounts. Balances update on the server."
      />

      <section className="card stack">
        <h2 className="import-section__title">New transfer</h2>
        {crossCurrencyMismatch ? (
          <Alert variant="warning" title="Currency mismatch">
            Selected accounts use different currencies. Choose accounts with the same
            currency.
          </Alert>
        ) : null}
        <form className="stack" onSubmit={(event) => void onSubmit(event)} noValidate>
          <FormField
            id="source_account_id"
            label="From account"
            required
            error={form.formState.errors.source_account_id}
          >
            <Select
              id="source_account_id"
              hasError={Boolean(form.formState.errors.source_account_id)}
              {...form.register("source_account_id")}
            >
              <option value="">Select source account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {accountLabel(account)}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField
            id="destination_account_id"
            label="To account"
            required
            error={form.formState.errors.destination_account_id}
          >
            <Select
              id="destination_account_id"
              hasError={Boolean(form.formState.errors.destination_account_id)}
              {...form.register("destination_account_id")}
            >
              <option value="">Select destination account</option>
              {accounts.map((account) => (
                <option key={account.id} value={account.id}>
                  {accountLabel(account)}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField
            id="source_amount"
            label="Amount"
            required
            error={form.formState.errors.source_amount}
          >
            <Input
              id="source_amount"
              inputMode="decimal"
              hasError={Boolean(form.formState.errors.source_amount)}
              {...form.register("source_amount")}
            />
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

          <FormField
            id="description"
            label="Description"
            error={form.formState.errors.description}
          >
            <Input
              id="description"
              hasError={Boolean(form.formState.errors.description)}
              {...form.register("description")}
            />
          </FormField>

          {form.formState.errors.root ? (
            <FormError>{form.formState.errors.root.message}</FormError>
          ) : null}

          <Button type="submit" loading={createMutation.isPending}>
            Transfer funds
          </Button>
        </form>
      </section>

      <section className="stack">
        <h2 className="import-section__title">Recent transfers</h2>
        {transfersQuery.isPending ? <LoadingState title="Loading transfers" /> : null}
        {transfersQuery.isError ? (
          <ErrorState
            error={transfersQuery.error}
            onRetry={() => void transfersQuery.refetch()}
          />
        ) : null}
        {transfersQuery.data?.items.length === 0 ? (
          <EmptyState
            title="No transfers yet"
            description="Your transfers will appear here."
          />
        ) : null}
        {transfersQuery.data && transfersQuery.data.items.length > 0 ? (
          <div className="transaction-table" role="table" aria-label="Transfers">
            <div className="transaction-table__header" role="row">
              <span role="columnheader">Date</span>
              <span role="columnheader">From</span>
              <span role="columnheader">To</span>
              <span role="columnheader">Description</span>
              <span role="columnheader" className="transaction-table__amount">
                Amount
              </span>
            </div>
            {transfersQuery.data.items.map((transfer) => {
              const source = accountById.get(transfer.source_account_id);
              const destination = accountById.get(transfer.destination_account_id);
              return (
                <article
                  key={transfer.id}
                  className="transaction-table__row"
                  role="row"
                >
                  <span role="cell">{transfer.transaction_date}</span>
                  <span role="cell">{source?.name ?? transfer.source_account_id}</span>
                  <span role="cell">
                    {destination?.name ?? transfer.destination_account_id}
                  </span>
                  <span role="cell">{transfer.description ?? "—"}</span>
                  <span role="cell" className="transaction-table__amount">
                    {formatMoneyDisplay(
                      transfer.source_amount,
                      transfer.source_currency,
                    )}
                  </span>
                </article>
              );
            })}
          </div>
        ) : null}
      </section>
    </PageContainer>
  );
}
