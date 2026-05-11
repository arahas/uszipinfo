"""Locate and load the bundled Parquet artifact.

The bundled data file is shipped inside the ``uszipinfo._data`` package.
This module discovers the latest available year and provides a cached
DataFrame loader.
"""


from __future__ import annotations


import re
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Optional

import pandas as pd

_DATA_PACKAGE = "uszipinfo._data"
_FILENAME_PATTERN = re.compile(r"^zip_metadata_(\d{4})\.parquet$")


def _list_bundled_files() -> list[tuple[int, Path]]:
    """Return ``(year, path)`` for every bundled metadata file."""
    files: list[tuple[int, Path]] = []
    try:
        package = resources.files(_DATA_PACKAGE)
    except (ModuleNotFoundError, FileNotFoundError):
        return files

    for entry in package.iterdir():
        match = _FILENAME_PATTERN.match(entry.name)
        if match:
            with resources.as_file(entry) as path:
                files.append((int(match.group(1)), Path(path)))
    return sorted(files)


def latest_data_year() -> Optional[int]:
    """Return the most recent ACS year bundled with the package, or None."""
    files = _list_bundled_files()
    return files[-1][0] if files else None


def _resolve_path(year: Optional[int]) -> Path:
    """Resolve which Parquet file to load."""
    files = _list_bundled_files()
    if not files:
        raise FileNotFoundError(
            "No bundled data found. The package may be installed without "
            "data files. See https://github.com/uszipinfo/uszipinfo for "
            "instructions on building or downloading the data."
        )
    if year is None:
        return files[-1][1]
    for y, path in files:
        if y == year:
            return path
    available = ", ".join(str(y) for y, _ in files)
    raise ValueError(
        f"No data bundled for year {year}. Available years: {available}"
    )


@lru_cache(maxsize=4)
def load_dataframe(year: Optional[int] = None) -> pd.DataFrame:
    """Load the bundled Parquet file as a pandas DataFrame.

    Cached so repeated calls in the same process are free after the first.
    """
    path = _resolve_path(year)
    df = pd.read_parquet(path)
    df["zip"] = df["zip"].astype(str).str.zfill(5)
    return df


def clear_cache() -> None:
    """Clear the in-process DataFrame cache. Mostly for tests."""
    load_dataframe.cache_clear()
