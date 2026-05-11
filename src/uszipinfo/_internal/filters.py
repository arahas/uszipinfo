"""Filter helpers used by ``uszipinfo.filter_zips``."""

from __future__ import annotations

from typing import Any

import pandas as pd

# Numeric range filters: maps "min_<field>" / "max_<field>" to the column name.
_RANGE_PREFIXES = ("min_", "max_")


def apply_filters(df: pd.DataFrame, criteria: dict[str, Any]) -> pd.DataFrame:
    """Apply filter criteria to a DataFrame and return the matching rows.

    Supported criteria:
      * Equality: ``state="WA"`` matches rows where state == "WA".
      * Membership: ``state=["WA", "OR"]`` matches rows where state is in the list.
      * Range: ``min_population=1000`` matches rows where population >= 1000.
                ``max_population=50000`` matches rows where population <= 50000.
    """
    mask = pd.Series(True, index=df.index)

    for key, value in criteria.items():
        if key.startswith(_RANGE_PREFIXES):
            mask &= _range_filter(df, key, value)
        else:
            mask &= _equality_filter(df, key, value)

    return df[mask].copy()


def _equality_filter(df: pd.DataFrame, column: str, value: Any) -> pd.Series:
    if column not in df.columns:
        raise KeyError(f"Unknown filter column: {column!r}")
    if isinstance(value, (list, tuple, set)):
        return df[column].isin(list(value))
    return df[column] == value


def _range_filter(df: pd.DataFrame, key: str, value: Any) -> pd.Series:
    if key.startswith("min_"):
        column = key[4:]
        op = ">="
    else:
        column = key[4:]
        op = "<="
    if column not in df.columns:
        raise KeyError(f"Unknown filter column: {column!r}")
    if op == ">=":
        return df[column] >= value
    return df[column] <= value
