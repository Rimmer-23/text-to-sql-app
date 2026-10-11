import { useState } from "react";

import { FileUpload } from "./components/FileUpload";
import { TableList } from "./components/TableList";
import { TablePreview } from "./components/TablePreview";
import { useWorkspace } from "./hooks/useWorkspace";

export function App() {
  const workspace = useWorkspace();
  const [selectedName, setSelectedName] = useState<string | null>(null);

  // Falls back to the first table when nothing is selected or the selection was removed.
  const selected =
    workspace.tables.find((table) => table.name === selectedName) ?? workspace.tables[0] ?? null;

  async function handleUpload(files: File[]) {
    const created = await workspace.upload(files);
    if (created[0]) setSelectedName(created[0]);
  }

  return (
    <div className="app">
      <header className="app-header">
        <span className="wordmark">Text-to-SQL</span>
      </header>

      <aside className="sidebar" aria-labelledby="sidebar-title">
        <h2 id="sidebar-title" className="sidebar-title">
          Your data
        </h2>
        <FileUpload onUpload={handleUpload} />
        {workspace.loadError && (
          <p className="error" role="alert">
            {workspace.loadError}
          </p>
        )}
        <TableList
          tables={workspace.tables}
          selected={selected?.name ?? null}
          onSelect={setSelectedName}
          onRemove={workspace.removeTable}
        />
      </aside>

      <main className="main">
        {workspace.loading ? (
          <p className="muted" aria-live="polite">
            Loading your data…
          </p>
        ) : selected ? (
          <TablePreview table={selected} />
        ) : (
          <div className="empty-state">
            <h1 className="empty-state-title">Upload a CSV file to get started</h1>
            <p className="empty-state-text">
              Each file becomes a table. Pick a table to check its columns and first rows.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
