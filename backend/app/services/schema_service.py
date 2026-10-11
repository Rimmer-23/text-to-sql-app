import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.services.workspace_service import COLUMNS_META_TABLE

SAMPLE_ROWS = 3


@dataclass
class SchemaColumn:
    name: str
    original_name: str
    type: str


@dataclass
class SchemaTable:
    name: str
    row_count: int
    columns: list[SchemaColumn]
    sample_rows: list[list[Any]]


def is_service_table(name: str) -> bool:
    return name.startswith("_") or name.lower().startswith("sqlite_")


def get_schema(db_path: Path, sample_rows: int = SAMPLE_ROWS) -> list[SchemaTable]:
    """User tables with columns, types, original column names, row count and sample rows.

    Service tables (prefix `_`) are never included — this schema is also what the AI sees.
    """
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        table_names = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
            if not is_service_table(row[0])
        ]

        original_names: dict[tuple[str, str], str] = {
            (table, column): original
            for table, column, original in conn.execute(
                f"SELECT table_name, column_name, original_name FROM {COLUMNS_META_TABLE}"
            )
        }

        tables = []
        for table in table_names:
            quoted = '"' + table.replace('"', '""') + '"'
            columns = [
                SchemaColumn(
                    name=name,
                    original_name=original_names.get((table, name), name),
                    type=col_type,
                )
                for _, name, col_type, *_ in conn.execute(f"PRAGMA table_info({quoted})")
            ]
            row_count = conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
            samples = [
                list(row) for row in conn.execute(f"SELECT * FROM {quoted} LIMIT ?", (sample_rows,))
            ]
            tables.append(
                SchemaTable(name=table, row_count=row_count, columns=columns, sample_rows=samples)
            )
        return tables
    finally:
        conn.close()
