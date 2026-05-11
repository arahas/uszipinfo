"""Engineered features derived from raw merged data."""

from __future__ import annotations

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


def add_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add urbanicity_tier, climate_zone, is_college_town, is_resort_area."""
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

    # College town heuristic: highly educated, moderately dense, non-trivial population
    df["is_college_town"] = (
        (df.get("pct_bachelors_or_higher").fillna(0) > 0.40)
        & df.get("population_density", pd.Series(0, index=df.index)).fillna(0).between(500, 5000)
        & (df.get("population", pd.Series(0, index=df.index)).fillna(0) > 5000)
    )

    # Resort area: high seasonal vacancy
    df["is_resort_area"] = df.get("vacancy_for_seasonal_use", pd.Series(0, index=df.index)).fillna(0) > 0.15

    return df


def _classify_climate(lat: float | None) -> str | None:
    if lat is None or pd.isna(lat):
        return None
    for low, high, label in CLIMATE_BANDS:
        if low <= lat < high:
            return label
    return None
