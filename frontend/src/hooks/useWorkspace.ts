import { useCallback, useEffect, useState } from "react";

import { ApiError, api } from "../api/client";
import type { TableSchema } from "../types";

const STORAGE_KEY = "textToSql.workspaceId";

// localStorage can be unavailable (private mode, blocked storage); the app then simply
// forgets the workspace on reload instead of crashing.
function readStoredId(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function storeId(id: string | null): void {
  try {
    if (id) {
      localStorage.setItem(STORAGE_KEY, id);
    } else {
      localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    // see readStoredId
  }
}

const isMissingWorkspace = (error: unknown) =>
  error instanceof ApiError && error.code === "WORKSPACE_NOT_FOUND";

export interface Workspace {
  workspaceId: string | null;
  tables: TableSchema[];
  loading: boolean;
  loadError: string | null;
  /** Uploads files, creating the workspace on first use. Returns the new table names. */
  upload: (files: File[]) => Promise<string[]>;
  removeTable: (name: string) => Promise<void>;
}

export function useWorkspace(): Workspace {
  const [workspaceId, setWorkspaceId] = useState<string | null>(readStoredId);
  const [tables, setTables] = useState<TableSchema[]>([]);
  const [loading, setLoading] = useState(() => readStoredId() !== null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const forgetWorkspace = useCallback(() => {
    storeId(null);
    setWorkspaceId(null);
    setTables([]);
  }, []);

  const startWorkspace = useCallback(async (): Promise<string> => {
    const { workspace_id } = await api.createWorkspace();
    storeId(workspace_id);
    setWorkspaceId(workspace_id);
    return workspace_id;
  }, []);

  useEffect(() => {
    const storedId = readStoredId();
    if (!storedId) return;

    let cancelled = false;
    api
      .getSchema(storedId)
      .then((schema) => {
        if (!cancelled) setTables(schema.tables);
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        // The server no longer has this workspace (e.g. its data folder was cleared):
        // start fresh on the next upload instead of showing an error.
        if (isMissingWorkspace(error)) {
          forgetWorkspace();
        } else {
          setLoadError(error instanceof Error ? error.message : "Could not load your data.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [forgetWorkspace]);

  const upload = useCallback(
    async (files: File[]): Promise<string[]> => {
      let id = workspaceId ?? (await startWorkspace());
      let result;
      try {
        result = await api.uploadFiles(id, files);
      } catch (error) {
        if (!isMissingWorkspace(error)) throw error;
        id = await startWorkspace();
        result = await api.uploadFiles(id, files);
      }

      const schema = await api.getSchema(id);
      setTables(schema.tables);
      setLoadError(null);
      return result.tables.map((table) => table.name);
    },
    [workspaceId, startWorkspace],
  );

  const removeTable = useCallback(
    async (name: string): Promise<void> => {
      if (!workspaceId) return;
      await api.deleteTable(workspaceId, name);
      setTables((current) => current.filter((table) => table.name !== name));
    },
    [workspaceId],
  );

  return { workspaceId, tables, loading, loadError, upload, removeTable };
}
