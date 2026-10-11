from typing import Any

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ErrorDetail(BaseModel):
    code: str
    message: str


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
