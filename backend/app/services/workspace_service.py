import sqlite3
import uuid
from pathlib import Path

from app.errors import AppError, ErrorCode

DB_FILENAME = "data.db"
COLUMNS_META_TABLE = "_columns_meta"


def create_workspace(data_dir: Path) -> str:
    workspace_id = str(uuid.uuid4())
    workspace_dir = data_dir / workspace_id
    workspace_dir.mkdir(parents=True, exist_ok=False)

    conn = sqlite3.connect(workspace_dir / DB_FILENAME)
    try:
        conn.execute(f"""
            CREATE TABLE {COLUMNS_META_TABLE} (
                table_name TEXT NOT NULL,
                column_name TEXT NOT NULL,
                original_name TEXT NOT NULL,
                PRIMARY KEY (table_name, column_name)
            )
            """)
        conn.commit()
    finally:
        conn.close()
    return workspace_id


def get_db_path(data_dir: Path, workspace_id: str) -> Path:
    """Resolve the workspace DB path; the id must be a canonical UUID (no path traversal)."""
    try:
        canonical_id = str(uuid.UUID(workspace_id))
    except ValueError:
        canonical_id = None

    db_path = data_dir / canonical_id / DB_FILENAME if canonical_id == workspace_id else None
    if db_path is None or not db_path.is_file():
        raise AppError(ErrorCode.WORKSPACE_NOT_FOUND, f"Workspace '{workspace_id}' not found", 404)
    return db_path
