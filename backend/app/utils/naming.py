import re
import unicodedata
from collections.abc import Iterable

MAX_IDENTIFIER_LENGTH = 63


def normalize_identifier(name: str, fallback: str, digit_prefix: str) -> str:
    """Latin letters, digits and `_`, lower case, never starts with a digit or `_`.

    Data is English-only: accents are dropped (`Café` -> `cafe`), other non-Latin
    characters are removed. Leading `_` is reserved for service tables (`_columns_meta`).
    """
    decomposed = unicodedata.normalize("NFKD", str(name))
    ascii_name = decomposed.encode("ascii", "ignore").decode().lower()
    result = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")
    if not result:
        result = fallback
    if result[0].isdigit():
        result = f"{digit_prefix}_{result}"
    return result[:MAX_IDENTIFIER_LENGTH].rstrip("_")


def normalize_table_name(name: str) -> str:
    return normalize_identifier(name, fallback="table", digit_prefix="t")


def normalize_column_name(name: str) -> str:
    return normalize_identifier(name, fallback="column", digit_prefix="c")


def make_unique(name: str, existing: Iterable[str]) -> str:
    """Append `_2`, `_3`, ... until the name is not in `existing` (case-insensitive)."""
    taken = {item.lower() for item in existing}
    if name.lower() not in taken:
        return name
    index = 2
    while f"{name}_{index}".lower() in taken:
        index += 1
    return f"{name}_{index}"
