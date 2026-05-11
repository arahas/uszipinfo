"""uszipinfo — ML-ready ZIP-code-level metadata for the United States."""

from __future__ import annotations

from uszipinfo._internal.data_loader import latest_data_year
from uszipinfo.client import filter_zips, load, lookup, lookup_many
from uszipinfo.geo import distance_mi, haversine_mi, nearest_zips
from uszipinfo.schema import COLUMNS, ENUMS, REQUIRED_COLUMNS, ZipInfo

__version__ = "1.1.0"

#: ACS vintage of the bundled data, or ``None`` if no data is bundled.
DATA_YEAR = latest_data_year()


__all__ = [
    # Public API
    "load",
    "lookup",
    "lookup_many",
    "filter_zips",
    "nearest_zips",
    "distance_mi",
    "haversine_mi",
    # Types and metadata
    "ZipInfo",
    "COLUMNS",
    "ENUMS",
    "REQUIRED_COLUMNS",
    # Versioning
    "__version__",
    "DATA_YEAR",
]
