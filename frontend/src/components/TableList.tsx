import { useState } from "react";

import { ApiError } from "../api/client";
import { plural } from "../format";
import type { TableSchema } from "../types";

interface TableListProps {
  tables: TableSchema[];
  selected: string | null;
  onSelect: (name: string) => void;
  onRemove: (name: string) => Promise<void>;
}

export function TableList({ tables, selected, onSelect, onRemove }: TableListProps) {
  if (tables.length === 0) return null;

  return (
    <ul className="table-list" aria-label="Your tables">
      {tables.map((table) => (
        <TableListItem
          key={table.name}
          table={table}
          selected={table.name === selected}
          onSelect={onSelect}
          onRemove={onRemove}
        />
      ))}
    </ul>
  );
}

interface TableListItemProps {
  table: TableSchema;
  selected: boolean;
  onSelect: (name: string) => void;
  onRemove: (name: string) => Promise<void>;
}

function TableListItem({ table, selected, onSelect, onRemove }: TableListItemProps) {
  const [confirming, setConfirming] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function remove() {
    setRemoving(true);
    setError(null);
    try {
      await onRemove(table.name);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not remove the table. Try again.");
      setRemoving(false);
      setConfirming(false);
    }
  }

  return (
    <li className="table-item" data-selected={selected || undefined}>
      <button
        type="button"
        className="table-item-select"
        aria-current={selected || undefined}
        onClick={() => onSelect(table.name)}
      >
        <span className="table-item-name">{table.name}</span>
        <span className="table-item-meta">
          {plural(table.row_count, "row")}, {plural(table.columns.length, "column")}
        </span>
      </button>

      {confirming ? (
        <div className="table-item-confirm" role="group" aria-label={`Remove ${table.name}?`}>
          <span>Remove this table?</span>
          <button type="button" className="link-button danger" disabled={removing} onClick={remove}>
            {removing ? "Removing…" : "Remove"}
          </button>
          <button
            type="button"
            className="link-button"
            disabled={removing}
            onClick={() => setConfirming(false)}
          >
            Keep
          </button>
        </div>
      ) : (
        <button
          type="button"
          className="link-button table-item-remove"
          aria-label={`Remove ${table.name}`}
          onClick={() => setConfirming(true)}
        >
          Remove
        </button>
      )}

      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
    </li>
  );
}
