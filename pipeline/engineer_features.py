"""Engineered features derived from raw merged data."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

#: Population-density bin edges defining urbanicity tiers.
URBANICITY_BINS = [-float("inf"), 100, 1000, 10000, float("inf")]
URBANICITY_LABELS = ["rural", "suburban", "urban", "dense_urban"]

#: Latitude bands for a coarse climate classification.
#: Rough rule of thumb covering the 50 states + territories.
#: Tropical band covers PR/USVI/Guam/American Samoa as well as FL Keys.
CLIMATE_BANDS = [
    (-float("inf"), 25, "tropical"),     # FL Keys, PR, USVI, Guam, Am. Samoa
    (25, 32, "subtropical"),              # FL, deep South, southern TX
    (32, 42, "temperate"),                # most of CONUS
    (42, 50, "continental"),              # northern tier
    (50, float("inf"), "cold"),           # AK
]

#: Earth's mean radius in miles, for haversine.
_EARTH_RADIUS_MI = 3958.7613


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add engineered columns:

    - ``urbanicity_tier``
    - ``climate_zone``
    - ``is_college_town`` (derived from academic signals)
    - ``is_resort_area``
    - ``is_top_100_metro``
    - ``dist_to_metro_center_mi``
    """
    df = df.copy()

    # Urbanicity tier
    if "population_density" in df.columns:
        df["urbanicity_tier"] = pd.cut(
            df["population_density"],
            bins=URBANICITY_BINS,
            labels=URBANICITY_LABELS,
            include_lowest=True,
        ).astype("object")

    # Climate zone
    if "lat" in df.columns:
        df["climate_zone"] = df["lat"].apply(_classify_climate)

    # ── Redefined college-town heuristic ─────────────────────────────────
    # Combines direct academic signals: a meaningful student population
    # OR substantial dorm presence OR a sizeable institution physically
    # in the ZIP. This catches dense urban college zones (Cambridge MA,
    # Berkeley CA, university districts) that the old density-bounded
    # heuristic missed.
    df["is_college_town"] = (
        (df.get("pct_dorm_population", pd.Series(0, index=df.index)).fillna(0) > 0.10)
        | (df.get("pct_college_enrolled", pd.Series(0, index=df.index)).fillna(0) > 0.25)
        | (df.get("college_enrollment_total", pd.Series(0, index=df.index)).fillna(0) >= 5000)
    )

    # Resort area: high seasonal vacancy
    df["is_resort_area"] = (
        df.get("vacancy_for_seasonal_use", pd.Series(0, index=df.index)).fillna(0) > 0.15
    )

    # ── is_top_100_metro and dist_to_metro_center_mi ────────────────────
    df = _add_metro_center_features(df)

    return df


def _classify_climate(lat: float | None) -> str | None:
    if lat is None or pd.isna(lat):
        return None
    for low, high, label in CLIMATE_BANDS:
        if low <= lat < high:
            return label
    return None


def _add_metro_center_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute is_top_100_metro and dist_to_metro_center_mi.

    For each CBSA, find the ZIP within that CBSA whose population is the
    largest, and use its lat/lon as the proxy for the CBSA's centroid.
    Then compute the distance from each ZIP to its CBSA's centroid.

    The top-100 ranking is computed by total population per CBSA (sum
    across all ZIPs in the CBSA).
    """
    df = df.copy()
    df["is_top_100_metro"] = False
    df["dist_to_metro_center_mi"] = pd.NA

    if "cbsa_code" not in df.columns:
        return df

    # CBSA total population (sum population across constituent ZIPs)
    cbsa_pop = (
        df.dropna(subset=["cbsa_code"])
        .groupby("cbsa_code")["population"]
        .sum(min_count=1)
        .sort_values(ascending=False)
    )
    top_100 = set(cbsa_pop.head(100).index)
    df["is_top_100_metro"] = df["cbsa_code"].isin(top_100).fillna(False)

    # Anchor each CBSA at its highest-population ZIP
    cbsa_anchors: dict[str, tuple[float, float]] = {}
    for cbsa, group in df.dropna(subset=["cbsa_code"]).groupby("cbsa_code"):
        valid = group[group["lat"].notna() & group["lon"].notna()]
        if valid.empty:
            continue
        anchor_row = valid.loc[valid["population"].idxmax()] if valid["population"].notna().any() else valid.iloc[0]
        cbsa_anchors[cbsa] = (float(anchor_row["lat"]), float(anchor_row["lon"]))

    # Compute distance per row
    def _distance(row):
        if pd.isna(row.get("cbsa_code")) or pd.isna(row.get("lat")) or pd.isna(row.get("lon")):
            return None
        anchor = cbsa_anchors.get(row["cbsa_code"])
        if anchor is None:
            return None
        return _haversine_mi(row["lat"], row["lon"], anchor[0], anchor[1])

    df["dist_to_metro_center_mi"] = df.apply(_distance, axis=1)
    return df


def _haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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
