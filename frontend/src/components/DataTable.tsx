import type { CellValue } from "../types";

export interface DataColumn {
  label: string;
  /** Shown under the label, e.g. the SQL type. */
  detail?: string;
}

interface DataTableProps {
  columns: DataColumn[];
  rows: CellValue[][];
  caption?: string;
}

/** Rows in alternating bands, like green-bar printout paper. Numbers align right. */
export function DataTable({ columns, rows, caption }: DataTableProps) {
  const numeric = columns.map((_, index) => isNumericColumn(rows, index));

  return (
    <div className="data-table-scroll" tabIndex={0} role="region" aria-label={caption}>
      <table className="data-table">
        {caption && <caption className="visually-hidden">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th key={index} scope="col" data-numeric={numeric[index] || undefined}>
                <span className="data-table-label">{column.label}</span>
                {column.detail && <span className="data-table-detail">{column.detail}</span>}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {columns.map((_, index) => (
                <td key={index} data-numeric={numeric[index] || undefined}>
                  <Cell value={row[index] ?? null} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Cell({ value }: { value: CellValue }) {
  if (value === null) {
    return (
      <span className="data-table-null" title="Empty">
        —
      </span>
    );
  }
  return <>{String(value)}</>;
}

function isNumericColumn(rows: CellValue[][], index: number): boolean {
  let sawNumber = false;
  for (const row of rows) {
    const value = row[index];
    if (value === null || value === undefined) continue;
    if (typeof value !== "number") return false;
    sawNumber = true;
  }
  return sawNumber;
}
