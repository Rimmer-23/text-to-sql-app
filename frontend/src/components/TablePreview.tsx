import { plural } from "../format";
import type { TableSchema } from "../types";
import { DataTable } from "./DataTable";

export function TablePreview({ table }: { table: TableSchema }) {
  const shown = table.sample_rows.length;

  return (
    <section className="preview" aria-labelledby="preview-title">
      <header className="preview-header">
        <h1 id="preview-title" className="preview-title">
          {table.name}
        </h1>
        <p className="preview-meta">
          {plural(table.row_count, "row")}, {plural(table.columns.length, "column")}
        </p>
      </header>

      <DataTable
        caption={`First rows of ${table.name}`}
        columns={table.columns.map((column) => ({
          label: column.original_name,
          detail: column.type.toLowerCase() || "text",
        }))}
        rows={table.sample_rows}
      />

      <p className="preview-note">
        {shown < table.row_count
          ? `Showing the first ${plural(shown, "row")} of ${table.row_count.toLocaleString("en-US")}.`
          : `Showing all ${plural(shown, "row")}.`}
      </p>
    </section>
  );
}
