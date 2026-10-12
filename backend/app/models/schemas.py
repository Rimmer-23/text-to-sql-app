from typing import Annotated, Any

from pydantic import BaseModel, StringConstraints


class HealthResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str
    sql: str | None = None  # only for SQL_NOT_ALLOWED / SQL_EXECUTION_ERROR


class ErrorResponse(BaseModel):
    error: ErrorDetail


class WorkspaceCreated(BaseModel):
    workspace_id: str


class ColumnInfo(BaseModel):
    name: str
    original_name: str
    type: str


class UploadedTable(BaseModel):
    name: str
    source_file: str
    row_count: int
    columns: list[ColumnInfo]


class UploadResponse(BaseModel):
    tables: list[UploadedTable]


class TableSchema(BaseModel):
    name: str
    row_count: int
    columns: list[ColumnInfo]
    sample_rows: list[list[Any]]


class SchemaResponse(BaseModel):
    workspace_id: str
    tables: list[TableSchema]


class QueryRequest(BaseModel):
    question: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
    ]


class QueryResponse(BaseModel):
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
