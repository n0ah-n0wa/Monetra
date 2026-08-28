import { useId, useState } from "react";
import { getErrorMessage } from "@/api/errors";
import { Link } from "react-router-dom";
import { Alert } from "@/components/ui/Alert";
import { PageContainer } from "@/components/layout/PageContainer";
import { PageHeader } from "@/components/layout/PageHeader";
import { EmptyState } from "@/components/states/EmptyState";
import { ErrorState } from "@/components/states/ErrorState";
import { LoadingState } from "@/components/states/LoadingState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useAccountsQuery } from "@/features/accounts/hooks";
import {
  formatImportStatus,
  importStatusVariant,
  type ImportJob,
} from "@/features/imports/api";
import { ImportConfirmSection } from "@/features/imports/components/ImportConfirmSection";
import {
  ImportErrorsSection,
  ImportPreviewSection,
} from "@/features/imports/components/ImportPreviewSection";
import { ImportStatsPanel } from "@/features/imports/components/ImportStatsPanel";
import {
  useConfirmImportMutation,
  useImportJobsQuery,
  useUploadImportMutation,
} from "@/features/imports/hooks";
import { routes } from "@/lib/routes";
import { AccessibleDataTable } from "@/features/analytics/components/AccessibleDataTable";
import {
  formatTransactionType,
  type TransactionType,
} from "@/features/transactions/api";
import { formatMoneyDisplay } from "@/lib/money";

const WIZARD_STEPS = [
  { id: "select", label: "Select file" },
  { id: "upload", label: "Upload" },
  { id: "parse", label: "Parse" },
  { id: "preview", label: "Preview" },
  { id: "review", label: "Review errors" },
  { id: "confirm", label: "Confirm" },
  { id: "import", label: "Import" },
  { id: "result", label: "Result" },
] as const;

type WizardPhase = (typeof WIZARD_STEPS)[number]["id"];

function resolvePhase(
  job: ImportJob | null,
  uploading: boolean,
  confirming: boolean,
): WizardPhase {
  if (!job) {
    return uploading ? "upload" : "select";
  }
  if (confirming || job.status === "processing") {
    return "import";
  }
  if (job.status === "completed" || job.status === "failed") {
    return "result";
  }
  if (job.stats.invalid_rows > 0) {
    return "confirm";
  }
  return "preview";
}

function stepIndex(phase: WizardPhase): number {
  if (phase === "select") {
    return 0;
  }
  if (phase === "upload" || phase === "parse") {
    return phase === "upload" ? 1 : 2;
  }
  if (phase === "preview") {
    return 3;
  }
  if (phase === "review" || phase === "confirm") {
    return phase === "review" ? 4 : 5;
  }
  if (phase === "import") {
    return 6;
  }
  return 7;
}

type ImportWizardStepperProps = {
  phase: WizardPhase;
  hasErrors: boolean;
};

function ImportWizardStepper({ phase, hasErrors }: ImportWizardStepperProps) {
  const currentIndex = stepIndex(phase);

  return (
    <nav aria-label="Import progress" className="import-stepper">
      <ol className="import-stepper__list">
        {WIZARD_STEPS.map((step, index) => {
          if (step.id === "review" && !hasErrors) {
            return null;
          }
          const isComplete = index < currentIndex;
          const isCurrent = index === currentIndex;
          return (
            <li
              key={step.id}
              className={[
                "import-stepper__item",
                isComplete ? "import-stepper__item--complete" : "",
                isCurrent ? "import-stepper__item--current" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              aria-current={isCurrent ? "step" : undefined}
            >
              <span className="import-stepper__marker" aria-hidden="true">
                {isComplete ? "✓" : index + 1}
              </span>
              <span className="import-stepper__label">{step.label}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

type ImportDuplicatesSectionProps = {
  rows: ImportJob["preview_rows"];
  currency: string;
};

function ImportDuplicatesSection({ rows, currency }: ImportDuplicatesSectionProps) {
  const duplicates = rows.filter((row) => row.is_duplicate);
  if (duplicates.length === 0) {
    return null;
  }

  return (
    <section aria-labelledby="import-duplicates-heading">
      <h2 id="import-duplicates-heading" className="import-section__title">
        Duplicate rows
      </h2>
      <p className="import-section__description">
        {duplicates.length} row{duplicates.length === 1 ? "" : "s"} match existing
        transactions or earlier rows in this file.
      </p>
      <div className="import-table-wrap">
        <AccessibleDataTable
          caption="Duplicate import rows"
          columns={[
            { key: "row", header: "Row", cell: (row) => row.row_number },
            { key: "date", header: "Date", cell: (row) => row.transaction_date },
            {
              key: "type",
              header: "Type",
              cell: (row) =>
                formatTransactionType(row.transaction_type as TransactionType),
            },
            {
              key: "amount",
              header: "Amount",
              align: "right",
              cell: (row) => formatMoneyDisplay(row.amount, currency),
            },
            {
              key: "description",
              header: "Description",
              cell: (row) => row.description,
            },
            {
              key: "reason",
              header: "Reason",
              cell: (row) => row.duplicate_reason ?? "Duplicate",
            },
          ]}
          rows={duplicates}
          getRowKey={(row) => `dup-${row.row_number}`}
        />
      </div>
    </section>
  );
}

type ImportResultSectionProps = {
  job: ImportJob;
  onStartOver: () => void;
};

function ImportResultSection({ job, onStartOver }: ImportResultSectionProps) {
  const isSuccess = job.status === "completed";

  return (
    <section aria-labelledby="import-result-heading" className="import-result">
      <h2 id="import-result-heading" className="import-section__title">
        Import result
      </h2>

      {isSuccess ? (
        <Alert variant="success" title="Import completed">
          {job.stats.imported_rows} row{job.stats.imported_rows === 1 ? "" : "s"}{" "}
          imported.
          {job.stats.skipped_rows > 0
            ? ` ${job.stats.skipped_rows} row${job.stats.skipped_rows === 1 ? "" : "s"} skipped.`
            : ""}
        </Alert>
      ) : (
        <Alert variant="warning" title="Import failed">
          The import could not be completed. Review the file and try again.
        </Alert>
      )}

      <ImportStatsPanel stats={job.stats} title="Final statistics" />

      <div className="import-confirm__actions">
        <Button type="button" variant="secondary" onClick={onStartOver}>
          Import another file
        </Button>
        <Link className="btn btn--primary btn--md" to={routes.transactions}>
          View transactions
        </Link>
      </div>
    </section>
  );
}

export function ImportPage() {
  const fileInputId = useId();
  const [accountId, setAccountId] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeJob, setActiveJob] = useState<ImportJob | null>(null);

  const accountsQuery = useAccountsQuery({ status: "active", page_size: 100 });
  const recentImportsQuery = useImportJobsQuery({ page: 1, page_size: 5 });
  const uploadMutation = useUploadImportMutation();
  const confirmMutation = useConfirmImportMutation();

  const accounts = accountsQuery.data?.items ?? [];
  const selectedAccount = accounts.find((account) => account.id === accountId);
  const currency = selectedAccount?.currency ?? accounts[0]?.currency ?? "USD";

  const phase = resolvePhase(
    activeJob,
    uploadMutation.isPending,
    confirmMutation.isPending,
  );
  const hasErrors = (activeJob?.errors.length ?? 0) > 0;

  const canUpload = Boolean(accountId && selectedFile && !uploadMutation.isPending);

  function resetWizard() {
    setSelectedFile(null);
    setActiveJob(null);
    uploadMutation.reset();
    confirmMutation.reset();
  }

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!selectedFile || !accountId) {
      return;
    }
    const job = await uploadMutation.mutateAsync({ accountId, file: selectedFile });
    setActiveJob(job);
  }

  async function handleConfirm(options: { skipDuplicates: boolean }) {
    if (!activeJob) {
      return;
    }
    const job = await confirmMutation.mutateAsync({
      id: activeJob.id,
      payload: { skip_duplicates: options.skipDuplicates },
    });
    setActiveJob(job);
  }

  const recentJobs = recentImportsQuery.data?.items ?? [];

  const showUploadForm = !activeJob && !uploadMutation.isPending;
  const showPreview = activeJob && activeJob.status === "preview";
  const showResult =
    activeJob && (activeJob.status === "completed" || activeJob.status === "failed");

  return (
    <PageContainer>
      <PageHeader
        title="Import transactions"
        description="Upload a CSV file to preview, review validation issues, and import transactions into an account."
      />

      <ImportWizardStepper phase={phase} hasErrors={hasErrors} />

      {accountsQuery.isPending ? <LoadingState title="Loading accounts" /> : null}

      {accountsQuery.isError ? (
        <ErrorState
          title="Unable to load accounts"
          onRetry={() => accountsQuery.refetch()}
        />
      ) : null}

      {accountsQuery.isSuccess && accounts.length === 0 ? (
        <EmptyState
          title="No active accounts"
          description="Create an account before importing transactions."
          actionLabel="Go to accounts"
          actionHref={routes.accounts}
        />
      ) : null}

      {uploadMutation.isPending ? (
        <LoadingState
          title="Uploading and parsing CSV"
          description="Validating rows…"
        />
      ) : null}

      {showUploadForm && accounts.length > 0 ? (
        <section aria-labelledby="import-upload-heading" className="import-upload card">
          <h2 id="import-upload-heading" className="import-section__title">
            Select file and account
          </h2>
          <form className="stack" onSubmit={handleUpload}>
            <div className="form-field">
              <label className="form-field__label" htmlFor="import-account">
                Target account
              </label>
              <Select
                id="import-account"
                value={accountId}
                onChange={(event) => setAccountId(event.target.value)}
                required
              >
                <option value="">Select an account</option>
                {accounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.name} ({account.currency})
                  </option>
                ))}
              </Select>
            </div>

            <div className="form-field">
              <label className="form-field__label" htmlFor={fileInputId}>
                CSV file
              </label>
              <p className="form-field__description" id={`${fileInputId}-hint`}>
                Required columns: transaction_date, transaction_type, amount,
                description, category. UTF-8 encoding.
              </p>
              <input
                id={fileInputId}
                type="file"
                accept=".csv,text/csv"
                aria-describedby={`${fileInputId}-hint`}
                onChange={(event) => {
                  const file = event.target.files?.[0] ?? null;
                  setSelectedFile(file);
                }}
              />
              {selectedFile ? (
                <p className="form-field__description">
                  Selected: {selectedFile.name} ({Math.round(selectedFile.size / 1024)}{" "}
                  KB)
                </p>
              ) : null}
            </div>

            {uploadMutation.isError ? (
              <Alert variant="warning" title="Upload failed">
                {getErrorMessage(
                  uploadMutation.error,
                  "Could not upload the CSV. Check the file format and try again.",
                )}
              </Alert>
            ) : null}

            <div className="import-confirm__actions">
              <Button type="submit" disabled={!canUpload}>
                Upload and preview
              </Button>
            </div>
          </form>
        </section>
      ) : null}

      {showPreview ? (
        <div className="import-review stack">
          <div className="import-review__header">
            <div>
              <h2 className="import-section__title">
                Preview: {activeJob.original_filename}
              </h2>
              <p className="import-section__description">
                Account: {selectedAccount?.name ?? "Selected account"} · Status:{" "}
                <Badge variant={importStatusVariant(activeJob.status)}>
                  {formatImportStatus(activeJob.status)}
                </Badge>
              </p>
            </div>
          </div>

          <ImportStatsPanel stats={activeJob.stats} />

          <ImportPreviewSection rows={activeJob.preview_rows} currency={currency} />
          <ImportDuplicatesSection rows={activeJob.preview_rows} currency={currency} />
          <ImportErrorsSection errors={activeJob.errors} />

          <ImportConfirmSection
            job={activeJob}
            confirming={confirmMutation.isPending}
            error={confirmMutation.error}
            onConfirm={handleConfirm}
            onStartOver={resetWizard}
          />
        </div>
      ) : null}

      {confirmMutation.isPending ? (
        <LoadingState
          title="Importing transactions"
          description="Creating transactions…"
        />
      ) : null}

      {showResult && activeJob ? (
        <ImportResultSection job={activeJob} onStartOver={resetWizard} />
      ) : null}

      {!activeJob ? (
        <section aria-labelledby="import-history-heading" className="import-history">
          <h2 id="import-history-heading" className="import-section__title">
            Recent imports
          </h2>
          {recentImportsQuery.isPending ? (
            <LoadingState title="Loading recent imports" />
          ) : null}
          {recentImportsQuery.isError ? (
            <ErrorState
              title="Unable to load import history"
              onRetry={() => recentImportsQuery.refetch()}
            />
          ) : null}
          {recentImportsQuery.isSuccess && recentJobs.length === 0 ? (
            <EmptyState
              title="No imports yet"
              description="Uploaded CSV files will appear here after you import transactions."
            />
          ) : null}
          {recentImportsQuery.isSuccess && recentJobs.length > 0 ? (
            <ul className="data-list">
              {recentJobs.map((job) => (
                <li key={job.id} className="data-list__item">
                  <div>
                    <p className="data-list__title">{job.original_filename}</p>
                    <p className="data-list__meta">
                      {new Date(job.created_at).toLocaleString()} ·{" "}
                      {job.stats.imported_rows} imported
                    </p>
                  </div>
                  <Badge variant={importStatusVariant(job.status)}>
                    {formatImportStatus(job.status)}
                  </Badge>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}
    </PageContainer>
  );
}
