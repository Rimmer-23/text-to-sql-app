import type {
  ErrorCode,
  ErrorResponse,
  QueryResponse,
  SchemaResponse,
  UploadResponse,
  WorkspaceCreated,
} from "../types";

export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number;

  constructor(code: ErrorCode, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(
      "NETWORK_ERROR",
      "Can't reach the server. Check that the backend is running.",
      0,
    );
  }

  if (!response.ok) {
    throw await toApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  try {
    const body = (await response.json()) as Partial<ErrorResponse>;
    if (body.error?.code && body.error.message) {
      return new ApiError(body.error.code, body.error.message, response.status);
    }
  } catch {
    // Not our JSON error format (e.g. a proxy error page); fall through to a generic error.
  }
  return new ApiError(
    "UNKNOWN_ERROR",
    `Request failed with status ${response.status}`,
    response.status,
  );
}

const workspacePath = (workspaceId: string) => `/workspaces/${encodeURIComponent(workspaceId)}`;

export const api = {
  createWorkspace: () => request<WorkspaceCreated>("/workspaces", { method: "POST" }),

  getSchema: (workspaceId: string) =>
    request<SchemaResponse>(`${workspacePath(workspaceId)}/schema`),

  uploadFiles: (workspaceId: string, files: File[]) => {
    const form = new FormData();
    for (const file of files) {
      form.append("files", file);
    }
    return request<UploadResponse>(`${workspacePath(workspaceId)}/files`, {
      method: "POST",
      body: form,
    });
  },

  deleteTable: (workspaceId: string, table: string) =>
    request<void>(`${workspacePath(workspaceId)}/tables/${encodeURIComponent(table)}`, {
      method: "DELETE",
    }),

  query: (workspaceId: string, question: string) =>
    request<QueryResponse>(`${workspacePath(workspaceId)}/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
};
