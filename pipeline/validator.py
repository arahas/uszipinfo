"""Validation for the assembled metadata DataFrame.

The build pipeline must call ``validate`` before publishing an artifact.
A failed check raises ``ValidationError`` with a list of failures so
operators can see every problem in one pass instead of one at a time.
"""

from __future__ import annotations

import re
from typing import Callable

import pandas as pd

from uszipinfo.schema import COLUMNS, ENUMS, REQUIRED_COLUMNS


class ValidationError(Exception):
    """Raised when validation finds one or more problems."""

    def __init__(self, failures: list[str]):
        self.failures = failures
        super().__init__("\n  - " + "\n  - ".join(failures))


_ZIP_PATTERN = re.compile(r"^\d{5}$")


def validate(df: pd.DataFrame, *, expected_year: int | None = None) -> None:
    """Run all validation checks, raising ``ValidationError`` on any failure."""
    failures: list[str] = []
    for check in _CHECKS:
        try:
            result = check(df, expected_year)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{check.__name__} crashed: {exc!r}")
            continue
        if result:
            failures.append(f"{check.__name__}: {result}")

    if failures:
        raise ValidationError(failures)


# ────────────────────────────────────────────────────────────────────────
# Individual checks
# ────────────────────────────────────────────────────────────────────────

CheckFn = Callable[[pd.DataFrame, int | None], str | None]


def _check_columns_present(df: pd.DataFrame, _: int | None) -> str | None:
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        return f"Missing columns: {sorted(missing)}"
    extra = set(df.columns) - set(COLUMNS)
    if extra:
        return f"Unexpected columns: {sorted(extra)}"
    return None


def _check_zip_unique(df: pd.DataFrame, _: int | None) -> str | None:
    if not df["zip"].is_unique:
        dupes = df[df["zip"].duplicated()]["zip"].head(5).tolist()
        return f"Duplicate zips (first 5): {dupes}"
    return None


def _check_zip_format(df: pd.DataFrame, _: int | None) -> str | None:
    bad = df[~df["zip"].astype(str).str.match(_ZIP_PATTERN)]
    if not bad.empty:
        return f"Invalid zip format ({len(bad)} rows): {bad['zip'].head(5).tolist()}"
    return None


def _check_row_count(df: pd.DataFrame, _: int | None) -> str | None:
    n = len(df)
    if not (30_000 <= n <= 50_000):
        return f"Suspicious row count: {n} (expected 30k–50k)"
    return None


def _check_state_coverage(df: pd.DataFrame, _: int | None) -> str | None:
    states = df["state"].dropna().unique()
    if len(states) < 50:
        return f"Only {len(states)} states found (expected ≥50)"
    return None


def _check_required_columns_non_null(df: pd.DataFrame, _: int | None) -> str | None:
    issues = []
    for col in REQUIRED_COLUMNS:
        if col in df.columns and df[col].isna().any():
            n_null = df[col].isna().sum()
            issues.append(f"{col}={n_null} nulls")
    if issues:
        return "Required columns have nulls: " + ", ".join(issues)
    return None


def _check_enum_values(df: pd.DataFrame, _: int | None) -> str | None:
    issues = []
    for col, allowed in ENUMS.items():
        if col not in df.columns:
            continue
        actual = set(df[col].dropna().unique())
        unexpected = actual - allowed
        if unexpected:
            issues.append(f"{col}={sorted(unexpected)}")
    if issues:
        return "Unexpected enum values: " + "; ".join(issues)
    return None


def _check_lat_lon_ranges(df: pd.DataFrame, _: int | None) -> str | None:
    """Lat/lon must be valid global coordinates.

    Military APO/FPO ZIPs may have lat/lon at military bases worldwide,
    so we don't restrict to US bounds.
    """
    lat = df["lat"].dropna()
    lon = df["lon"].dropna()
    if len(lat) and not lat.between(-90, 90).all():
        bad = lat[~lat.between(-90, 90)].head(3).tolist()
        return f"Some lat values outside [-90, 90]: {bad}"
    if len(lon) and not lon.between(-180, 180).all():
        bad = lon[~lon.between(-180, 180)].head(3).tolist()
        return f"Some lon values outside [-180, 180]: {bad}"
    return None


def _check_population_total(df: pd.DataFrame, _: int | None) -> str | None:
    total = df["population"].sum()
    if total < 300_000_000:
        return f"Total population too low: {total:,}"
    if total > 400_000_000:
        return f"Total population too high: {total:,}"
    return None


def _check_pct_ranges(df: pd.DataFrame, _: int | None) -> str | None:
    pct_cols = [c for c in df.columns if c.startswith("pct_") or c.startswith("vacancy_")]
    issues = []
    for col in pct_cols:
        non_null = df[col].dropna()
        if len(non_null) == 0:
            continue
        if not non_null.between(0, 1, inclusive="both").all():
            issues.append(
                f"{col}: range [{non_null.min():.2f}, {non_null.max():.2f}]"
            )
    if issues:
        return "Percentage columns out of [0, 1]: " + "; ".join(issues)
    return None


def _check_data_year(df: pd.DataFrame, expected_year: int | None) -> str | None:
    if expected_year is None:
        return None
    actual = df["data_year"].iloc[0]
    if int(actual) != int(expected_year):
        return f"data_year={actual}, expected {expected_year}"
    return None


#: Columns that are *expected* to have high NaN rates and should not
#: trigger the NaN-rate validator. CBSA-related columns are null for ZIPs
#: outside any metro/micropolitan area (~30% of US ZIPs are rural).
#: `primary_city` is null until a city-lookup data source is integrated.
NAN_TOLERATED_COLUMNS = {
    "primary_city",
    "cbsa_code", "cbsa_name", "cbsa_type",
    "msa_code", "msa_name",
    "csa_code", "csa_name",
}


def _check_nan_rates(df: pd.DataFrame, _: int | None) -> str | None:
    """NaN-rate check restricted to Standard residential ZIPs.

    PO Box, Military, and Unique ZIPs *should* have null demographics —
    they have no residential population for the Census to measure. We
    only validate that Standard ZIPs have full demographic coverage.
    """
    # Filter to ZIPs where we expect demographics to exist
    if "zip_type" in df.columns:
        scope = df[df["zip_type"] == "Standard"]
    else:
        scope = df
    if len(scope) == 0:
        return None
    nan_rates = scope.isna().mean()
    high = nan_rates[nan_rates > 0.20]
    high = high[~high.index.isin(REQUIRED_COLUMNS | NAN_TOLERATED_COLUMNS)]
    if not high.empty:
        return "High NaN rates among Standard ZIPs: " + ", ".join(
            f"{c}={r:.0%}" for c, r in high.items()
        )
    return None


_CHECKS: list[CheckFn] = [
    _check_columns_present,
    _check_zip_unique,
    _check_zip_format,
    _check_row_count,
    _check_state_coverage,
    _check_required_columns_non_null,
    _check_enum_values,
    _check_lat_lon_ranges,
    _check_population_total,
    _check_pct_ranges,
    _check_data_year,
    _check_nan_rates,
]
