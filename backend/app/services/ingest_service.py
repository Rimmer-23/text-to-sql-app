import csv
import io
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.errors import AppError, ErrorCode
from app.services.schema_service import is_service_table
from app.services.workspace_service import COLUMNS_META_TABLE
from app.utils.naming import make_unique, normalize_column_name, normalize_table_name

SUPPORTED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
CSV_ENCODING = "utf-8-sig"  # also accepts plain UTF-8 without a BOM
CSV_DELIMITERS = ",;\t|"
SNIFF_SAMPLE_CHARS = 64 * 1024

# Tried in order; the first format that parses every non-empty value wins.
DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%d.%m.%Y",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%Y/%m/%d",
)


@dataclass
class UploadedFile:
    filename: str
    content: bytes


@dataclass
class ParsedSheet:
    source_file: str
    base_name: str
    frame: pd.DataFrame
    original_columns: list[str]


@dataclass
class IngestedColumn:
    name: str
    original_name: str
    type: str


@dataclass
class IngestedTable:
    name: str
    source_file: str
    row_count: int
    columns: list[IngestedColumn]


def ingest_files(db_path: Path, files: list[UploadedFile]) -> list[IngestedTable]:
    """Parse all files first (so a bad file aborts before anything is written), then store them."""
    if not files:
        raise AppError(ErrorCode.INVALID_FILE, "No files uploaded")

    sheets = [sheet for file in files for sheet in parse_file(file)]

    conn = sqlite3.connect(db_path)
    try:
        existing = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        result = []
        for sheet in sheets:
            table = _write_sheet(conn, sheet, existing)
            existing.add(table.name)
            result.append(table)
        conn.commit()
        return result
    finally:
        conn.close()


def delete_table(db_path: Path, table_name: str) -> None:
    """Drop a user table together with its column metadata. Service tables are invisible here."""
    conn = sqlite3.connect(db_path)
    try:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table_name,)
        ).fetchone()
        if exists is None or is_service_table(table_name):
            raise AppError(ErrorCode.TABLE_NOT_FOUND, f"Table '{table_name}' not found", 404)

        quoted = '"' + table_name.replace('"', '""') + '"'
        conn.execute(f"DROP TABLE {quoted}")
        conn.execute(f"DELETE FROM {COLUMNS_META_TABLE} WHERE table_name = ?", (table_name,))
        conn.commit()
    finally:
        conn.close()


def parse_file(file: UploadedFile) -> list[ParsedSheet]:
    extension = Path(file.filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise AppError(
            ErrorCode.INVALID_FILE,
            f"'{file.filename}': unsupported file type, expected .csv, .xlsx or .xls",
        )
    if extension != ".csv":
        # TODO(step 7): Excel support, one table per sheet.
        raise AppError(ErrorCode.INVALID_FILE, f"'{file.filename}': Excel is not supported yet")

    frame = _read_csv(file)
    frame, original_columns = _clean_frame(frame)
    if frame.empty or not original_columns:
        raise AppError(ErrorCode.INVALID_FILE, f"'{file.filename}': file contains no data")

    return [
        ParsedSheet(
            source_file=file.filename,
            base_name=Path(file.filename).stem,
            frame=frame,
            original_columns=original_columns,
        )
    ]


def _decode(file: UploadedFile) -> str:
    try:
        return file.content.decode(CSV_ENCODING)
    except UnicodeDecodeError as exc:
        raise AppError(
            ErrorCode.INVALID_FILE, f"'{file.filename}': file must be UTF-8 encoded"
        ) from exc


def _detect_delimiter(text: str) -> str:
    sample = text[:SNIFF_SAMPLE_CHARS]
    if len(text) > SNIFF_SAMPLE_CHARS and "\n" in sample:
        sample = sample[: sample.rindex("\n")]
    try:
        return csv.Sniffer().sniff(sample, delimiters=CSV_DELIMITERS).delimiter
    except csv.Error:
        return ","


def _read_csv(file: UploadedFile) -> pd.DataFrame:
    text = _decode(file)
    if not text.strip():
        raise AppError(ErrorCode.INVALID_FILE, f"'{file.filename}': file is empty")

    delimiter = _detect_delimiter(text)
    try:
        frame = pd.read_csv(io.StringIO(text), sep=delimiter, dtype=str, skip_blank_lines=True)
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        raise AppError(
            ErrorCode.INVALID_FILE, f"'{file.filename}': cannot parse CSV ({exc})"
        ) from exc

    # Semicolon/tab separated files usually come from locales with a decimal comma.
    frame.attrs["decimal_comma"] = delimiter != ","
    return frame


def _clean_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Strip values, drop empty rows/columns, infer column types."""
    decimal_comma = frame.attrs.get("decimal_comma", False)
    frame = frame.apply(lambda col: col.str.strip()).replace("", pd.NA)
    frame = frame.dropna(axis=0, how="all").dropna(axis=1, how="all").reset_index(drop=True)

    original_columns = [
        "" if str(col).startswith("Unnamed: ") else str(col).strip() for col in frame.columns
    ]
    frame.columns = range(len(frame.columns))
    for col in frame.columns:
        frame[col] = _infer_column(frame[col], decimal_comma)
    return frame, original_columns


def _infer_column(series: pd.Series, decimal_comma: bool) -> pd.Series:
    numeric = _try_numeric(series, decimal_comma)
    if numeric is not None:
        return numeric
    dates = _try_dates(series)
    if dates is not None:
        return dates
    return series.astype(object).where(series.notna(), None)


def _try_numeric(series: pd.Series, decimal_comma: bool) -> pd.Series | None:
    values = series.dropna()
    # Values like "007" or "0123" are codes (zip, article), keep them as text.
    if values.str.match(r"^-?0\d").any():
        return None

    candidate = series.str.replace(",", ".", regex=False) if decimal_comma else series
    converted = pd.to_numeric(candidate, errors="coerce")
    if converted[series.notna()].isna().any():
        return None

    if (converted.dropna() % 1 == 0).all():
        return converted.astype("Int64")
    return converted.astype(float)


def _try_dates(series: pd.Series) -> pd.Series | None:
    values = series.dropna()
    for date_format in DATE_FORMATS:
        parsed = pd.to_datetime(values, format=date_format, errors="coerce")
        if parsed.isna().any():
            continue
        has_time = (parsed != parsed.dt.normalize()).any()
        output_format = "%Y-%m-%d %H:%M:%S" if has_time else "%Y-%m-%d"
        result = pd.Series([None] * len(series), index=series.index, dtype=object)
        result[values.index] = parsed.dt.strftime(output_format)
        return result
    return None


def _write_sheet(conn: sqlite3.Connection, sheet: ParsedSheet, existing: set[str]) -> IngestedTable:
    table_name = make_unique(normalize_table_name(sheet.base_name), existing)

    column_names: list[str] = []
    for index, original in enumerate(sheet.original_columns, start=1):
        normalized = normalize_column_name(original) if original else f"column_{index}"
        column_names.append(make_unique(normalized, column_names))

    frame = sheet.frame.copy()
    frame.columns = column_names
    frame.to_sql(table_name, conn, index=False, if_exists="fail")

    conn.executemany(
        f"INSERT INTO {COLUMNS_META_TABLE} (table_name, column_name, original_name) "
        "VALUES (?, ?, ?)",
        [
            (table_name, name, original or name)
            for name, original in zip(column_names, sheet.original_columns, strict=True)
        ],
    )

    types = {row[1]: row[2] for row in conn.execute(f'PRAGMA table_info("{table_name}")')}
    return IngestedTable(
        name=table_name,
        source_file=sheet.source_file,
        row_count=len(frame),
        columns=[
            IngestedColumn(name=name, original_name=original or name, type=types.get(name, ""))
            for name, original in zip(column_names, sheet.original_columns, strict=True)
        ],
    )
