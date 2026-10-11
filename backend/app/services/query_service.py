"""Execute AI-generated SQL against a workspace database, safely.

Two independent layers of defense, per CLAUDE.md:
1. `sql_guard` only lets a single read-only SELECT through, with a row limit enforced.
2. The connection itself is opened read-only (SQLite URI `mode=ro`), so even a guard bug
   can't turn into a write.
A soft timeout is enforced via SQLite's progress handler.
"""

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.errors import AppError, ErrorCode
from app.services.sql_guard import validate_and_prepare

# Call the timeout check roughly every this many SQLite VM instructions. Small enough to
# catch a runaway query promptly, large enough not to measurably slow queries down.
_PROGRESS_HANDLER_INTERVAL = 1000

# The timeout can't interrupt a single SQLite operation, and one call like
# `randomblob(900000000)` allocates ~900 MB on its own. Capping the size of any one value
# (string, blob or row) makes such queries fail fast instead. Uploads are capped at 50 MB
# per file, so no legitimate cell comes close.
_MAX_VALUE_BYTES = 10 * 1024 * 1024


@dataclass
class QueryResult:
    sql: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool


def run_query(db_path: Path, sql: str, *, max_rows: int, timeout_seconds: float) -> QueryResult:
    prepared = validate_and_prepare(sql, max_rows)

    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, _MAX_VALUE_BYTES)
        # The guard already rejects ATTACH; this makes it impossible at the engine level too.
        conn.setlimit(sqlite3.SQLITE_LIMIT_ATTACHED, 0)
        deadline = time.monotonic() + timeout_seconds
        conn.set_progress_handler(
            lambda: 1 if time.monotonic() > deadline else 0, _PROGRESS_HANDLER_INTERVAL
        )

        cursor = conn.cursor()
        try:
            cursor.execute(prepared.sql)
            fetched = cursor.fetchall()
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc).lower():
                raise AppError(ErrorCode.SQL_EXECUTION_ERROR, "Query timed out", 400) from exc
            raise AppError(ErrorCode.SQL_EXECUTION_ERROR, str(exc), 400) from exc
        except sqlite3.Error as exc:
            raise AppError(ErrorCode.SQL_EXECUTION_ERROR, str(exc), 400) from exc

        columns = [description[0] for description in cursor.description or []]
        truncated = len(fetched) > prepared.display_limit
        rows = [list(row) for row in fetched[: prepared.display_limit]]
        return QueryResult(
            sql=prepared.display_sql,
            columns=columns,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
        )
    finally:
        conn.set_progress_handler(None, 0)
        conn.close()
