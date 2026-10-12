import { columnFormats, formatCell } from "../tableData";
import type { ColumnFormat } from "../tableData";
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
  /** Per-column number formatting. Defaults to deciding from `rows`. */
  formats?: ColumnFormat[];
}

/**
 * Rows in alternating bands, like green-bar printout paper. Numbers align right with the same
 * number of decimals per column. The table is as wide as its content and scrolls sideways
 * when that is wider than the page.
 */
export function DataTable({ columns, rows, caption, formats: formatsProp }: DataTableProps) {
  const formats = formatsProp ?? columnFormats(rows, columns.length);

  return (
    <div className="data-table-scroll" tabIndex={0} role="region" aria-label={caption}>
      <table className="data-table">
        {caption && <caption className="visually-hidden">{caption}</caption>}
        <thead>
          <tr>
            {columns.map((column, index) => (
              <th key={index} scope="col" data-numeric={formats[index]?.numeric || undefined}>
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
                <td key={index} data-numeric={formats[index]?.numeric || undefined}>
                  <Cell value={row[index] ?? null} format={formats[index]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Cell({ value, format }: { value: CellValue; format: ColumnFormat | undefined }) {
  if (value === null) {
    return (
      <span className="data-table-null" title="Empty">
        —
      </span>
    );
  }
  return <>{formatCell(value, format)}</>;
}
