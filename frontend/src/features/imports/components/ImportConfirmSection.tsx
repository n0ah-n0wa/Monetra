import { useId, useState } from "react";
import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  canConfirmImport,
  requiresInvalidRowAcknowledgment,
  type ImportJob,
} from "@/features/imports/api";

type ImportConfirmSectionProps = {
  job: ImportJob;
  confirming?: boolean;
  error?: unknown;
  onConfirm: (options: { skipDuplicates: boolean }) => void;
  onStartOver: () => void;
};

export function ImportConfirmSection({
  job,
  confirming = false,
  error,
  onConfirm,
  onStartOver,
}: ImportConfirmSectionProps) {
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [acknowledgedInvalidRows, setAcknowledgedInvalidRows] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);
  const acknowledgmentId = useId();

  const needsAcknowledgment = requiresInvalidRowAcknowledgment(job);
  const confirmAllowed =
    canConfirmImport(job) && (!needsAcknowledgment || acknowledgedInvalidRows);

  const hasDuplicates = job.stats.duplicate_rows > 0;
  const hasInvalid = job.stats.invalid_rows > 0;

  function handleConfirmClick() {
    if (!confirmAllowed) {
      return;
    }
    if (hasInvalid || hasDuplicates) {
      setShowConfirmDialog(true);
      return;
    }
    onConfirm({ skipDuplicates });
  }

  return (
    <section aria-labelledby="import-confirm-heading" className="import-confirm">
      <h2 id="import-confirm-heading" className="import-section__title">
        Confirm import
      </h2>

      {!canConfirmImport(job) ? (
        <Alert variant="warning" title="Nothing to import">
          All rows are invalid. Fix the CSV and upload again.
        </Alert>
      ) : null}

      {hasInvalid ? (
        <Alert variant="warning" title="Invalid rows will be skipped">
          {job.stats.invalid_rows} invalid row{job.stats.invalid_rows === 1 ? "" : "s"}{" "}
          will not be imported. Only {job.stats.valid_rows} valid row
          {job.stats.valid_rows === 1 ? "" : "s"} can proceed.
        </Alert>
      ) : null}

      {hasDuplicates ? (
        <label className="checkbox-list__item import-confirm__option">
          <input
            type="checkbox"
            checked={skipDuplicates}
            onChange={(event) => setSkipDuplicates(event.target.checked)}
          />
          <span>
            Skip duplicate rows during import ({job.stats.duplicate_rows} detected)
          </span>
        </label>
      ) : null}

      {needsAcknowledgment ? (
        <label
          className="checkbox-list__item import-confirm__option"
          htmlFor={acknowledgmentId}
        >
          <input
            id={acknowledgmentId}
            type="checkbox"
            checked={acknowledgedInvalidRows}
            onChange={(event) => setAcknowledgedInvalidRows(event.target.checked)}
          />
          <span>
            I reviewed the validation errors and understand invalid rows will not be
            imported.
          </span>
        </label>
      ) : null}

      <div className="import-confirm__actions">
        <Button
          type="button"
          variant="secondary"
          onClick={onStartOver}
          disabled={confirming}
        >
          Upload a different file
        </Button>
        <Button
          type="button"
          onClick={handleConfirmClick}
          loading={confirming}
          disabled={!confirmAllowed || confirming}
          aria-describedby={needsAcknowledgment ? acknowledgmentId : undefined}
        >
          Import valid rows
        </Button>
      </div>

      <ConfirmDialog
        open={showConfirmDialog}
        title="Confirm CSV import?"
        description={
          hasInvalid && hasDuplicates
            ? `${job.stats.valid_rows} valid rows will be imported. ${job.stats.invalid_rows} invalid rows will be skipped. ${skipDuplicates ? `${job.stats.duplicate_rows} duplicates will also be skipped.` : "Duplicates may be imported where allowed."}`
            : hasInvalid
              ? `${job.stats.valid_rows} valid rows will be imported and ${job.stats.invalid_rows} invalid rows will be skipped.`
              : hasDuplicates
                ? `${job.stats.valid_rows} rows will be imported. ${skipDuplicates ? `${job.stats.duplicate_rows} duplicates will be skipped.` : "Duplicates may be imported where allowed."}`
                : `${job.stats.valid_rows} rows will be imported.`
        }
        confirmLabel="Confirm import"
        loading={confirming}
        error={error}
        tone="primary"
        onCancel={() => setShowConfirmDialog(false)}
        onConfirm={() => {
          setShowConfirmDialog(false);
          onConfirm({ skipDuplicates });
        }}
      />
    </section>
  );
}
