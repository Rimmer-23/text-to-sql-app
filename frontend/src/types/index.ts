// Mirrors backend/app/models/schemas.py. Keep the two in sync.

export interface WorkspaceCreated {
  workspace_id: string;
}

export interface ColumnInfo {
  name: string;
  original_name: string;
  type: string;
}

export interface UploadedTable {
  name: string;
  source_file: string;
  row_count: number;
  columns: ColumnInfo[];
}

export interface UploadResponse {
  tables: UploadedTable[];
}

export type CellValue = string | number | boolean | null;

export interface TableSchema {
  name: string;
  row_count: number;
  columns: ColumnInfo[];
  sample_rows: CellValue[][];
}

export interface SchemaResponse {
  workspace_id: string;
  tables: TableSchema[];
}

export interface QueryRequest {
  question: string;
}

export interface QueryResponse {
  sql: string;
  columns: string[];
  rows: CellValue[][];
  row_count: number;
  truncated: boolean;
}

export type ErrorCode =
  | "INVALID_FILE"
  | "INVALID_REQUEST"
  | "SQL_NOT_ALLOWED"
  | "SQL_EXECUTION_ERROR"
  | "AI_ERROR"
  | "WORKSPACE_NOT_FOUND"
  | "TABLE_NOT_FOUND"
  // Client-side only: the request never got a well-formed answer from the backend.
  | "NETWORK_ERROR"
  | "UNKNOWN_ERROR";

export interface ErrorResponse {
  // `sql` is set for SQL_NOT_ALLOWED and SQL_EXECUTION_ERROR from /query.
  error: { code: ErrorCode; message: string; sql?: string };
}
