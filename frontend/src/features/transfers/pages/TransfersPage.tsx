import { useMemo, useState } from "react";
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
import { AccessibleDataTable } from "@/features/analytics/components/AccessibleDataTable";

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function accountLabel(account: Account): string {
  return `${account.name} (${account.currency})`;
}

export function TransfersPage() {
  const [transferSuccess, setTransferSuccess] = useState(false);
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
        <PageHeader
          title="Transfers"
          description="Move money between accounts. Balances update on the server."
        />
        <LoadingState title="Loading accounts" />
      </PageContainer>
    );
  }

  if (accountsQuery.isError) {
    return (
      <PageContainer>
        <PageHeader title="Transfers" description="Move money between your accounts." />
        <ErrorState
          error={accountsQuery.error}
          title="Unable to load accounts"
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
          actionLabel="Manage accounts"
          actionHref={routes.accounts}
        />
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
      setTransferSuccess(true);
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
        <h2 className="section-title">New transfer</h2>
        {transferSuccess ? (
          <Alert variant="success" title="Transfer recorded">
            Funds moved successfully. Enter another transfer below or review recent
            activity.
          </Alert>
        ) : null}
        {crossCurrencyMismatch ? (
          <Alert variant="warning" title="Currency mismatch">
            Selected accounts use different currencies. Choose accounts with the same
            currency.
          </Alert>
        ) : null}
        <form
          className="stack"
          onSubmit={(event) => {
            setTransferSuccess(false);
            void onSubmit(event);
          }}
          noValidate
        >
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
        <h2 className="section-title">Recent transfers</h2>
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
          <AccessibleDataTable
            caption="Transfers"
            className="transaction-data-table"
            rows={transfersQuery.data.items}
            getRowKey={(transfer) => transfer.id}
            columns={[
              {
                key: "date",
                header: "Date",
                cell: (transfer) => transfer.transaction_date,
              },
              {
                key: "from",
                header: "From",
                cell: (transfer) =>
                  accountById.get(transfer.source_account_id)?.name ??
                  transfer.source_account_id,
              },
              {
                key: "to",
                header: "To",
                cell: (transfer) =>
                  accountById.get(transfer.destination_account_id)?.name ??
                  transfer.destination_account_id,
              },
              {
                key: "description",
                header: "Description",
                cell: (transfer) => transfer.description ?? "—",
              },
              {
                key: "amount",
                header: "Amount",
                align: "right",
                cellClassName: "transaction-data-table__amount",
                cell: (transfer) =>
                  formatMoneyDisplay(
                    transfer.source_amount,
                    transfer.source_currency,
                  ),
              },
            ]}
          />
        ) : null}
      </section>
    </PageContainer>
  );
}
