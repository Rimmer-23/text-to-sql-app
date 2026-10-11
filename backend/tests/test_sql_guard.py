import pytest

from app.errors import AppError, ErrorCode
from app.services.sql_guard import validate_and_prepare

# --- allowed queries -------------------------------------------------------------------


def test_adds_limit_when_missing() -> None:
    prepared = validate_and_prepare("SELECT * FROM sales", max_rows=1000)
    assert "LIMIT 1001" in prepared.sql  # probe for one extra row to detect truncation
    assert prepared.display_limit == 1000


def test_caps_limit_that_exceeds_max_rows() -> None:
    prepared = validate_and_prepare("SELECT * FROM sales LIMIT 50000", max_rows=1000)
    assert "LIMIT 1001" in prepared.sql
    assert prepared.display_limit == 1000


def test_keeps_limit_within_max_rows() -> None:
    prepared = validate_and_prepare("SELECT * FROM sales LIMIT 5", max_rows=1000)
    assert "LIMIT 5" in prepared.sql
    assert prepared.display_limit == 5


def test_allows_cte() -> None:
    sql = (
        "WITH totals AS (SELECT city, SUM(amount) AS total FROM sales GROUP BY city) "
        "SELECT * FROM totals ORDER BY total DESC"
    )
    prepared = validate_and_prepare(sql, max_rows=10)
    assert "WITH totals AS" in prepared.sql
    assert "LIMIT 11" in prepared.sql


def test_allows_union() -> None:
    prepared = validate_and_prepare(
        "SELECT city FROM sales UNION SELECT city FROM customers", max_rows=10
    )
    assert "UNION" in prepared.sql


def test_rejects_empty_sql() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_and_prepare("   ", max_rows=10)
    assert exc_info.value.code == ErrorCode.SQL_NOT_ALLOWED


def test_rejects_unparsable_sql() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_and_prepare("SELECT FROM WHERE ***", max_rows=10)
    assert exc_info.value.code == ErrorCode.SQL_NOT_ALLOWED


# --- malicious / disallowed queries -----------------------------------------------------


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM sales; DROP TABLE sales;",
        "DROP TABLE sales",
        "DELETE FROM sales",
        "UPDATE sales SET amount = 0",
        "INSERT INTO sales VALUES (1, 'x')",
        "ALTER TABLE sales ADD COLUMN hacked TEXT",
        "CREATE TABLE evil (id INTEGER)",
        "ATTACH DATABASE 'other.db' AS other",
        "PRAGMA table_info(sales)",
        "VACUUM",
    ],
)
def test_rejects_non_select_statements(sql: str) -> None:
    with pytest.raises(AppError) as exc_info:
        validate_and_prepare(sql, max_rows=10)
    assert exc_info.value.code == ErrorCode.SQL_NOT_ALLOWED


def test_rejects_second_statement_smuggled_after_select() -> None:
    with pytest.raises(AppError) as exc_info:
        validate_and_prepare("SELECT * FROM sales WHERE 1=1; ATTACH DATABASE 'x' AS y", max_rows=10)
    assert exc_info.value.code == ErrorCode.SQL_NOT_ALLOWED


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM _columns_meta",
        "SELECT * FROM sqlite_master",
        "SELECT (SELECT COUNT(*) FROM _columns_meta)",
        "SELECT * FROM sales WHERE city IN (SELECT original_name FROM _columns_meta)",
    ],
)
def test_rejects_service_table_access(sql: str) -> None:
    with pytest.raises(AppError) as exc_info:
        validate_and_prepare(sql, max_rows=10)
    assert exc_info.value.code == ErrorCode.SQL_NOT_ALLOWED
