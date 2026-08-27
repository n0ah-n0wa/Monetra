import { AccessibleDataTable } from "@/features/analytics/components/AccessibleDataTable";
import type { ImportPreviewRow, ImportRowError } from "@/features/imports/api";
import {
  formatTransactionType,
  type TransactionType,
} from "@/features/transactions/api";
import { formatMoneyDisplay } from "@/lib/money";

type ImportPreviewSectionProps = {
  rows: ImportPreviewRow[];
  currency: string;
};

export function ImportPreviewSection({ rows, currency }: ImportPreviewSectionProps) {
  if (rows.length === 0) {
    return (
      <section aria-labelledby="import-preview-heading">
        <h2 id="import-preview-heading" className="import-section__title">
          Preview rows
        </h2>
        <p className="import-section__description">No valid rows to preview.</p>
      </section>
    );
  }

  return (
    <section aria-labelledby="import-preview-heading">
      <h2 id="import-preview-heading" className="import-section__title">
        Preview rows
      </h2>
      <p className="import-section__description">
        Valid rows that can be imported into the selected account.
      </p>
      <div className="import-table-wrap">
        <AccessibleDataTable
          caption="Valid import preview rows"
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
            { key: "category", header: "Category", cell: (row) => row.category },
            {
              key: "duplicate",
              header: "Duplicate",
              cell: (row) =>
                row.is_duplicate ? (
                  <span className="import-row-flag import-row-flag--warning">
                    {row.duplicate_reason ?? "Duplicate"}
                  </span>
                ) : (
                  "No"
                ),
            },
          ]}
          rows={rows}
          getRowKey={(row) => String(row.row_number)}
        />
      </div>
    </section>
  );
}

type ImportErrorsSectionProps = {
  errors: ImportRowError[];
};

export function ImportErrorsSection({ errors }: ImportErrorsSectionProps) {
  if (errors.length === 0) {
    return null;
  }

  return (
    <section aria-labelledby="import-errors-heading">
      <h2 id="import-errors-heading" className="import-section__title">
        Validation errors
      </h2>
      <p className="import-section__description" role="alert">
        {errors.length} row{errors.length === 1 ? "" : "s"} failed validation and will
        not be imported.
      </p>
      <div className="import-table-wrap">
        <AccessibleDataTable
          caption="Import validation errors"
          columns={[
            { key: "row", header: "Row", cell: (row) => row.row_number },
            { key: "code", header: "Code", cell: (row) => row.code },
            { key: "message", header: "Message", cell: (row) => row.message },
          ]}
          rows={errors}
          getRowKey={(row) => `${row.row_number}-${row.code}`}
        />
      </div>
    </section>
  );
}
