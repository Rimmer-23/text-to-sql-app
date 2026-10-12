import { useCallback, useRef, useState } from "react";

import { ApiError, api } from "../api/client";
import type { QueryResponse } from "../types";

export type QueryState =
  | { status: "idle" }
  | { status: "loading"; id: number; question: string }
  | { status: "success"; id: number; question: string; result: QueryResponse }
  | { status: "error"; id: number; question: string; error: ApiError };

/**
 * Asks questions against one workspace. Only the latest question's answer is kept, so a slow
 * earlier request can never overwrite a newer one.
 */
export function useQuery(workspaceId: string | null, onWorkspaceMissing: () => void) {
  const [state, setState] = useState<QueryState>({ status: "idle" });
  const latestId = useRef(0);

  const ask = useCallback(
    async (question: string) => {
      if (!workspaceId) return;
      const id = ++latestId.current;
      setState({ status: "loading", id, question });
      try {
        const result = await api.query(workspaceId, question);
        if (id === latestId.current) setState({ status: "success", id, question, result });
      } catch (err) {
        if (id !== latestId.current) return;
        const error =
          err instanceof ApiError
            ? err
            : new ApiError("UNKNOWN_ERROR", "Something went wrong. Try again.", 0);
        if (error.code === "WORKSPACE_NOT_FOUND") onWorkspaceMissing();
        setState({ status: "error", id, question, error });
      }
    },
    [workspaceId, onWorkspaceMissing],
  );

  return { state, ask };
}
