from pathlib import Path

import pytest

from app.errors import AppError, ErrorCode
from app.services.ingest_service import UploadedFile, ingest_files
from app.services.query_service import run_query

SALES_CSV = "city,amount\nPraha,100\nBrno,250\nPraha,80\nOstrava,40\nBrno,60\n"


def _load_sales(db_path: Path) -> None:
    ingest_files(db_path, [UploadedFile(filename="sales.csv", content=SALES_CSV.encode())])


def test_runs_a_simple_select(db_path: Path) -> None:
    _load_sales(db_path)
    result = run_query(
        db_path,
        "SELECT city, amount FROM sales ORDER BY amount DESC",
        max_rows=1000,
        timeout_seconds=5,
    )
    assert result.columns == ["city", "amount"]
    assert result.rows[0] == ["Brno", 250]
    assert result.row_count == 5
    assert result.truncated is False


def test_truncates_when_result_exceeds_max_rows(db_path: Path) -> None:
    _load_sales(db_path)
    result = run_query(db_path, "SELECT * FROM sales", max_rows=2, timeout_seconds=5)
    assert result.row_count == 2
    assert result.truncated is True


def test_respects_explicit_limit_within_cap(db_path: Path) -> None:
    _load_sales(db_path)
    result = run_query(db_path, "SELECT * FROM sales LIMIT 2", max_rows=1000, timeout_seconds=5)
    assert result.row_count == 2
    # The user asked for exactly 2 rows themselves; that's not us cutting it off.
    assert result.truncated is False


def test_aggregation_query(db_path: Path) -> None:
    _load_sales(db_path)
    result = run_query(
        db_path,
        "SELECT city, SUM(amount) AS total FROM sales GROUP BY city ORDER BY total DESC",
        max_rows=1000,
        timeout_seconds=5,
    )
    assert result.columns == ["city", "total"]
    assert result.rows[0] == ["Brno", 310]


def test_rejects_write_before_touching_the_database(db_path: Path) -> None:
    _load_sales(db_path)
    with pytest.raises(AppError) as exc_info:
        run_query(db_path, "DELETE FROM sales", max_rows=1000, timeout_seconds=5)
    assert exc_info.value.code == ErrorCode.SQL_NOT_ALLOWED

    # Nothing was touched: the read-only connection is a second line of defense, but the
    # guard should already have stopped this before any connection was opened.
    result = run_query(db_path, "SELECT * FROM sales", max_rows=1000, timeout_seconds=5)
    assert result.row_count == 5


def test_unknown_column_raises_execution_error(db_path: Path) -> None:
    _load_sales(db_path)
    with pytest.raises(AppError) as exc_info:
        run_query(db_path, "SELECT nope FROM sales", max_rows=1000, timeout_seconds=5)
    assert exc_info.value.code == ErrorCode.SQL_EXECUTION_ERROR


def test_query_times_out(db_path: Path) -> None:
    _load_sales(db_path)
    heavy_sql = (
        "WITH RECURSIVE cnt(x) AS ("
        "SELECT 1 UNION ALL SELECT x + 1 FROM cnt WHERE x < 50000000"
        ") SELECT COUNT(*) FROM cnt"
    )
    with pytest.raises(AppError) as exc_info:
        run_query(db_path, heavy_sql, max_rows=1000, timeout_seconds=0.05)
    assert exc_info.value.code == ErrorCode.SQL_EXECUTION_ERROR
    assert "timed out" in exc_info.value.message.lower()


def test_huge_values_are_rejected_instead_of_eating_memory(db_path: Path) -> None:
    # A single SQLite operation can't be interrupted by the timeout, so the value size
    # itself has to be capped.
    _load_sales(db_path)
    with pytest.raises(AppError) as exc_info:
        run_query(db_path, "SELECT length(randomblob(500000000))", max_rows=1000, timeout_seconds=5)
    assert exc_info.value.code == ErrorCode.SQL_EXECUTION_ERROR
