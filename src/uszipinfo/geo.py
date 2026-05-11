"""Geographic helpers: distance and nearest-neighbor queries."""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
import pandas as pd

from uszipinfo._internal.data_loader import load_dataframe

# Earth's mean radius in miles.
_EARTH_RADIUS_MI = 3958.7613


def haversine_mi(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Great-circle distance in miles between two points (degrees)."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(min(1.0, math.sqrt(a)))
    return _EARTH_RADIUS_MI * c


def _haversine_vectorized(
    lat1: float, lon1: float, lats: np.ndarray, lons: np.ndarray
) -> np.ndarray:
    """Vectorized haversine distance from one point to many points."""
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lats_r = np.radians(lats.astype(float))
    lons_r = np.radians(lons.astype(float))
    dlat = lats_r - lat1_r
    dlon = lons_r - lon1_r
    a = (
        np.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * np.cos(lats_r) * np.sin(dlon / 2) ** 2
    )
    return _EARTH_RADIUS_MI * 2 * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def distance_mi(zip_a: str, zip_b: str) -> float:
    """Return great-circle distance in miles between two ZIPs.

    Raises ``KeyError`` if either ZIP is not found, or ``ValueError`` if
    either lacks geographic coordinates (e.g., some PO Box ZIPs).
    """
    df = load_dataframe()
    df_indexed = df.set_index("zip")
    zip_a = str(zip_a).zfill(5)
    zip_b = str(zip_b).zfill(5)

    for z in (zip_a, zip_b):
        if z not in df_indexed.index:
            raise KeyError(f"ZIP not found: {z}")

    a = df_indexed.loc[zip_a]
    b = df_indexed.loc[zip_b]

    if pd.isna(a["lat"]) or pd.isna(a["lon"]):
        raise ValueError(f"ZIP {zip_a} has no coordinates")
    if pd.isna(b["lat"]) or pd.isna(b["lon"]):
        raise ValueError(f"ZIP {zip_b} has no coordinates")

    return haversine_mi(
        float(a["lat"]), float(a["lon"]),
        float(b["lat"]), float(b["lon"]),
    )


def nearest_zips(
    zip_code: str,
    n: int = 10,
    max_distance_mi: Optional[float] = None,
) -> pd.DataFrame:
    """Return the ``n`` nearest ZIPs to ``zip_code``.

    The result includes a ``distance_mi`` column. Excludes ``zip_code`` itself.
    If ``max_distance_mi`` is given, results are also filtered to within that
    radius (so fewer than ``n`` ZIPs may be returned).
    """
    df = load_dataframe()
    zip_code = str(zip_code).zfill(5)

    src = df[df["zip"] == zip_code]
    if src.empty:
        raise KeyError(f"ZIP not found: {zip_code}")
    src_lat = src.iloc[0]["lat"]
    src_lon = src.iloc[0]["lon"]
    if pd.isna(src_lat) or pd.isna(src_lon):
        raise ValueError(f"ZIP {zip_code} has no coordinates")

    candidates = df[df["lat"].notna() & df["lon"].notna() & (df["zip"] != zip_code)].copy()
    candidates["distance_mi"] = _haversine_vectorized(
        float(src_lat), float(src_lon),
        candidates["lat"].values, candidates["lon"].values,
    )

    if max_distance_mi is not None:
        candidates = candidates[candidates["distance_mi"] <= max_distance_mi]

    return candidates.nsmallest(n, "distance_mi").reset_index(drop=True)
