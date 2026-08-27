import type { ReactNode } from "react";

type Column<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
};

type AccessibleDataTableProps<T> = {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  footer?: ReactNode;
};

export function AccessibleDataTable<T>({
  caption,
  columns,
  rows,
  getRowKey,
  footer,
}: AccessibleDataTableProps<T>) {
  return (
    <table className="dashboard-table analytics-table">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          {columns.map((column) => (
            <th
              key={column.key}
              scope="col"
              style={column.align === "right" ? { textAlign: "right" } : undefined}
            >
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={getRowKey(row)}>
            {columns.map((column) => (
              <td
                key={column.key}
                style={column.align === "right" ? { textAlign: "right" } : undefined}
              >
                {column.cell(row)}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
      {footer ? <tfoot>{footer}</tfoot> : null}
    </table>
  );
}
