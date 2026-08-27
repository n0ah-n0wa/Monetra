import type { ImportJobStats } from "@/features/imports/api";

type ImportStatsPanelProps = {
  stats: ImportJobStats;
  title?: string;
};

export function ImportStatsPanel({
  stats,
  title = "Import statistics",
}: ImportStatsPanelProps) {
  return (
    <section aria-labelledby="import-stats-heading">
      <h2 id="import-stats-heading" className="import-section__title">
        {title}
      </h2>
      <dl className="import-stats">
        <div className="import-stats__item">
          <dt>Total rows</dt>
          <dd>{stats.total_rows}</dd>
        </div>
        <div className="import-stats__item">
          <dt>Valid rows</dt>
          <dd>{stats.valid_rows}</dd>
        </div>
        <div className="import-stats__item">
          <dt>Invalid rows</dt>
          <dd>{stats.invalid_rows}</dd>
        </div>
        <div className="import-stats__item">
          <dt>Duplicates</dt>
          <dd>{stats.duplicate_rows}</dd>
        </div>
        <div className="import-stats__item">
          <dt>Imported rows</dt>
          <dd>{stats.imported_rows}</dd>
        </div>
        <div className="import-stats__item">
          <dt>Skipped rows</dt>
          <dd>{stats.skipped_rows}</dd>
        </div>
      </dl>
    </section>
  );
}
