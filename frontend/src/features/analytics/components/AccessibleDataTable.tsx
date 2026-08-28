import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Column<T> = {
  key: string;
  header: string;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  headerClassName?: string;
  cellClassName?: string;
};

type AccessibleDataTableProps<T> = {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  getRowKey: (row: T) => string;
  footer?: ReactNode;
  className?: string;
};

export function AccessibleDataTable<T>({
  caption,
  columns,
  rows,
  getRowKey,
  footer,
  className,
}: AccessibleDataTableProps<T>) {
  return (
    <table className={cn("dashboard-table", className)}>
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          {columns.map((column) => (
            <th
              key={column.key}
              scope="col"
              className={column.headerClassName}
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
                className={column.cellClassName}
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
