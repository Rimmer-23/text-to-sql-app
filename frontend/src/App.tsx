import { useState } from "react";

import { FileUpload } from "./components/FileUpload";
import { QueryInput } from "./components/QueryInput";
import { QueryResult } from "./components/QueryResult";
import { TableList } from "./components/TableList";
import { TablePreview } from "./components/TablePreview";
import { useQuery } from "./hooks/useQuery";
import { useWorkspace } from "./hooks/useWorkspace";

export function App() {
  const workspace = useWorkspace();
  const query = useQuery(workspace.workspaceId, workspace.forget);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  // The main area shows either the latest question's result or a table preview.
  const [view, setView] = useState<"result" | "preview">("preview");

  // Falls back to the first table when nothing is selected or the selection was removed.
  const selected =
    workspace.tables.find((table) => table.name === selectedName) ?? workspace.tables[0] ?? null;
  const showResult = view === "result" && query.state.status !== "idle";

  async function handleUpload(files: File[]) {
    const created = await workspace.upload(files);
    if (created[0]) {
      setSelectedName(created[0]);
      setView("preview");
    }
  }

  function handleSelect(name: string) {
    setSelectedName(name);
    setView("preview");
  }

  function handleAsk(question: string) {
    setView("result");
    void query.ask(question);
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
          selected={showResult ? null : (selected?.name ?? null)}
          onSelect={handleSelect}
          onRemove={workspace.removeTable}
        />
      </aside>

      <main className="main">
        <QueryInput
          tableNames={workspace.tables.map((table) => table.name)}
          busy={query.state.status === "loading"}
          onAsk={handleAsk}
        />

        {workspace.loading ? (
          <p className="muted" aria-live="polite">
            Loading your data…
          </p>
        ) : showResult && query.state.status !== "idle" ? (
          <QueryResult state={query.state} />
        ) : selected ? (
          <TablePreview table={selected} />
        ) : (
          <div className="empty-state">
            <h1 className="empty-state-title">Upload a CSV file to get started</h1>
            <p className="empty-state-text">
              Each file becomes a table. Then ask questions about your tables in plain English.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
