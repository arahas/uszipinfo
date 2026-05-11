"""Public consumer API for uszipinfo."""

from __future__ import annotations

from typing import Any, Iterable, Optional

import pandas as pd

from uszipinfo._internal.data_loader import load_dataframe
from uszipinfo._internal.filters import apply_filters
from uszipinfo.schema import COLUMNS, ZipInfo


def load(year: Optional[int] = None) -> pd.DataFrame:
    """Return the full ZIP metadata table as a DataFrame.

    Parameters
    ----------
    year:
        ACS vintage to load. If ``None`` (default), uses the latest bundled.
    """
    df = load_dataframe(year)
    return df.copy()


def lookup(zip_code: str, year: Optional[int] = None) -> ZipInfo:
    """Return a :class:`ZipInfo` for a single ZIP code.

    Raises
    ------
    KeyError
        If the ZIP is not in the dataset.
    """
    zip_code = _normalize_zip(zip_code)
    df = load_dataframe(year)
    rows = df[df["zip"] == zip_code]
    if rows.empty:
        raise KeyError(f"ZIP not found: {zip_code}")
    record = rows.iloc[0].to_dict()
    return _record_to_zipinfo(record)


def lookup_many(
    zip_codes: Iterable[str],
    year: Optional[int] = None,
) -> pd.DataFrame:
    """Return a DataFrame of metadata for the given ZIPs.

    Missing ZIPs are silently dropped. Result preserves input order
    where possible but rows for ZIPs not in the dataset will be absent.
    """
    normalized = [_normalize_zip(z) for z in zip_codes]
    df = load_dataframe(year)
    result = df[df["zip"].isin(normalized)].copy()
    # Preserve input order
    order = pd.Categorical(result["zip"], categories=normalized, ordered=True)
    result = result.assign(_order=order).sort_values("_order").drop(columns="_order")
    return result.reset_index(drop=True)


def filter_zips(
    year: Optional[int] = None,
    **criteria: Any,
) -> pd.DataFrame:
    """Return ZIPs matching the given criteria.

    Examples
    --------
    >>> filter_zips(state="WA", urbanicity_tier="urban")
    >>> filter_zips(state=["WA", "OR"], min_population=10000)
    >>> filter_zips(is_metro=True, max_median_household_income=50000)

    Supported criteria forms:
      * Equality: ``state="WA"`` or ``is_metro=True``
      * Membership: ``state=["WA", "OR"]``
      * Range: ``min_<field>=value`` or ``max_<field>=value``
    """
    df = load_dataframe(year)
    return apply_filters(df, criteria)


# ────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────


def _normalize_zip(zip_code: str) -> str:
    """Standardize ZIP code input to 5-digit zero-padded string."""
    zip_str = str(zip_code).strip()
    # Drop ZIP+4 suffix if present
    zip_str = zip_str.split("-")[0]
    if not zip_str.isdigit() or len(zip_str) > 5:
        raise ValueError(f"Invalid ZIP code: {zip_code!r}")
    return zip_str.zfill(5)


def _record_to_zipinfo(record: dict) -> ZipInfo:
    """Convert a DataFrame row dict to a typed ZipInfo."""
    # Only pass fields that exist in the schema; ignore extras.
    kwargs = {k: record.get(k) for k in COLUMNS}
    # Convert NaN to None for optional fields
    for key, value in list(kwargs.items()):
        if isinstance(value, float) and pd.isna(value):
            kwargs[key] = None
    # Coerce types where the dataclass demands non-Optional
    if kwargs.get("is_metro") is None:
        kwargs["is_metro"] = False
    if kwargs.get("is_college_town") is None:
        kwargs["is_college_town"] = False
    if kwargs.get("is_resort_area") is None:
        kwargs["is_resort_area"] = False
    return ZipInfo(**kwargs)
