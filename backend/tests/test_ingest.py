import sqlite3
from pathlib import Path

import pytest

from app.errors import AppError, ErrorCode
from app.services.ingest_service import UploadedFile, ingest_files
from app.services.schema_service import get_schema
from app.utils.naming import make_unique, normalize_column_name, normalize_table_name


def csv_file(name: str, text: str, encoding: str = "utf-8") -> UploadedFile:
    return UploadedFile(filename=name, content=text.encode(encoding))


def fetch_all(db_path: Path, sql: str) -> list[tuple]:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


# --- naming ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Sales 2024", "sales_2024"),
        ("Продажи", "prodazhi"),
        ("2024 report", "t_2024_report"),
        ("__hidden__", "hidden"),
        ("!!!", "table"),
        ("Отчёт: Q1/Q2", "otchiot_q1_q2"),
    ],
)
def test_normalize_table_name(raw: str, expected: str) -> None:
    assert normalize_table_name(raw) == expected


def test_normalize_column_name() -> None:
    assert normalize_column_name("Сумма, руб.") == "summa_rub"
    assert normalize_column_name("1st place") == "c_1st_place"
    assert normalize_column_name("") == "column"


def test_make_unique() -> None:
    assert make_unique("sales", []) == "sales"
    assert make_unique("sales", ["sales"]) == "sales_2"
    assert make_unique("sales", ["sales", "sales_2"]) == "sales_3"
    assert make_unique("sales", ["SALES"]) == "sales_2"


# --- CSV parsing ----------------------------------------------------------------------


def test_utf8_comma_csv(db_path: Path) -> None:
    tables = ingest_files(db_path, [csv_file("sales.csv", "city,amount\nPraha,100\nBrno,250\n")])

    assert [t.name for t in tables] == ["sales"]
    assert tables[0].row_count == 2
    assert [(c.name, c.type) for c in tables[0].columns] == [
        ("city", "TEXT"),
        ("amount", "INTEGER"),
    ]
    assert fetch_all(db_path, "SELECT city, amount FROM sales") == [("Praha", 100), ("Brno", 250)]


def test_cp1251_semicolon_csv_with_cyrillic_names(db_path: Path) -> None:
    text = "Город;Сумма продаж\nМосква;1500,50\nКазань;99,9\n"
    tables = ingest_files(db_path, [csv_file("Продажи.csv", text, encoding="cp1251")])

    table = tables[0]
    assert table.name == "prodazhi"
    assert [(c.name, c.original_name, c.type) for c in table.columns] == [
        ("gorod", "Город", "TEXT"),
        ("summa_prodazh", "Сумма продаж", "REAL"),
    ]
    assert fetch_all(db_path, "SELECT gorod, summa_prodazh FROM prodazhi") == [
        ("Москва", 1500.5),
        ("Казань", 99.9),
    ]


def test_utf8_bom_and_tab_delimiter(db_path: Path) -> None:
    content = "﻿name\tqty\nA\t1\nB\t2\n".encode()
    tables = ingest_files(db_path, [UploadedFile("items.csv", content)])

    assert [c.name for c in tables[0].columns] == ["name", "qty"]
    assert fetch_all(db_path, "SELECT name, qty FROM items") == [("A", 1), ("B", 2)]


def test_columns_meta_stores_original_names(db_path: Path) -> None:
    ingest_files(db_path, [csv_file("people.csv", "Имя,Age (years)\nИван,30\n")])

    rows = fetch_all(
        db_path, "SELECT column_name, original_name FROM _columns_meta WHERE table_name='people'"
    )
    assert sorted(rows) == [("age_years", "Age (years)"), ("imia", "Имя")]


def test_duplicate_table_names_get_suffix(db_path: Path) -> None:
    first = ingest_files(db_path, [csv_file("sales.csv", "a\n1\n")])
    second = ingest_files(
        db_path, [csv_file("sales.csv", "a\n2\n"), csv_file("Sales.csv", "a\n3\n")]
    )

    assert [t.name for t in first] == ["sales"]
    assert [t.name for t in second] == ["sales_2", "sales_3"]


def test_duplicate_and_empty_column_headers(db_path: Path) -> None:
    tables = ingest_files(db_path, [csv_file("t.csv", "Name,name,,x\na,b,c,d\n")])

    names = [c.name for c in tables[0].columns]
    assert len(names) == len(set(names))
    assert names[0] == "name"
    assert names[2] == "column_3"


def test_drops_empty_rows_and_columns(db_path: Path) -> None:
    text = "a,empty,b\n1,,x\n,,\n2,,y\n , , \n"
    tables = ingest_files(db_path, [csv_file("t.csv", text)])

    assert [c.name for c in tables[0].columns] == ["a", "b"]
    assert tables[0].row_count == 2
    assert fetch_all(db_path, "SELECT a, b FROM t") == [(1, "x"), (2, "y")]


def test_type_inference(db_path: Path) -> None:
    text = (
        "id,price,zip,day,moment,ru_date,label,partial\n"
        "1,1.5,01234,2024-01-15,2024-01-15 10:30:00,15.01.2024,abc,5\n"
        "2,2,10001,2024-02-01,2024-02-01 00:00:00,01.02.2024,10,\n"
    )
    tables = ingest_files(db_path, [csv_file("t.csv", text)])

    types = {c.name: c.type for c in tables[0].columns}
    assert types == {
        "id": "INTEGER",
        "price": "REAL",
        "zip": "TEXT",
        "day": "TEXT",
        "moment": "TEXT",
        "ru_date": "TEXT",
        "label": "TEXT",
        "partial": "INTEGER",
    }
    assert fetch_all(db_path, "SELECT zip, day, moment, ru_date, label, partial FROM t") == [
        ("01234", "2024-01-15", "2024-01-15 10:30:00", "2024-01-15", "abc", 5),
        ("10001", "2024-02-01", "2024-02-01 00:00:00", "2024-02-01", "10", None),
    ]


# --- errors ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "file",
    [
        UploadedFile("data.txt", b"a,b\n1,2\n"),
        UploadedFile("empty.csv", b""),
        UploadedFile("blank.csv", b"   \n\n"),
        UploadedFile("header_only.csv", b"a,b\n"),
        UploadedFile("book.xlsx", b"PK..."),
    ],
)
def test_invalid_files(db_path: Path, file: UploadedFile) -> None:
    with pytest.raises(AppError) as exc_info:
        ingest_files(db_path, [file])
    assert exc_info.value.code == ErrorCode.INVALID_FILE


def test_bad_file_aborts_whole_upload(db_path: Path) -> None:
    with pytest.raises(AppError):
        ingest_files(db_path, [csv_file("good.csv", "a\n1\n"), UploadedFile("bad.txt", b"x")])

    assert get_schema(db_path) == []


# --- schema ---------------------------------------------------------------------------


def test_schema_hides_service_tables_and_limits_samples(db_path: Path) -> None:
    rows = "\n".join(f"{i},item{i}" for i in range(10))
    ingest_files(db_path, [csv_file("Товары.csv", f"Номер,Название\n{rows}\n")])

    schema = get_schema(db_path)

    assert [t.name for t in schema] == ["tovary"]
    table = schema[0]
    assert table.row_count == 10
    assert [(c.name, c.original_name) for c in table.columns] == [
        ("nomer", "Номер"),
        ("nazvanie", "Название"),
    ]
    assert table.sample_rows == [[0, "item0"], [1, "item1"], [2, "item2"]]
