import { useState } from "react";

import { plural } from "../format";
import type { QueryResponse } from "../types";
import { columnFormats } from "../tableData";
import { DataTable } from "./DataTable";

export const PAGE_SIZE = 50;

/** Query result with client-side pagination. Remount (via `key`) for each new result. */
export function ResultTable({ result }: { result: QueryResponse }) {
  const [page, setPage] = useState(0);

  if (result.row_count === 0) {
    return <p className="result-empty">No rows match this question.</p>;
  }

  const pageCount = Math.ceil(result.rows.length / PAGE_SIZE);
  const start = page * PAGE_SIZE;
  const rows = result.rows.slice(start, start + PAGE_SIZE);

  return (
    <div className="result-table">
      <DataTable
        caption="Query result"
        columns={result.columns.map((label) => ({ label }))}
        rows={rows}
        // Decided on all rows, so alignment and decimals don't jump between pages.
        formats={columnFormats(result.rows, result.columns.length)}
      />

      {pageCount > 1 && (
        <nav className="pager" aria-label="Result pages">
          <button
            type="button"
            className="link-button"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <span className="pager-position">
            Rows {(start + 1).toLocaleString("en-US")}–
            {(start + rows.length).toLocaleString("en-US")} of{" "}
            {result.row_count.toLocaleString("en-US")}
          </span>
          <button
            type="button"
            className="link-button"
            disabled={page === pageCount - 1}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </nav>
      )}

      {result.truncated && (
        <p className="result-note">
          Only the first {plural(result.row_count, "row")} are shown. Add a filter to the question
          to narrow it down.
        </p>
      )}
    </div>
  );
}
