"""Fetch the Census ZCTA-to-County relationship file.

This is the public, no-auth-required alternative to the HUD ZIP-County
crosswalk. The Census Bureau publishes 2020-vintage ZCTA-to-county
relationships at:

    https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/tab20_zcta520_county20_natl.txt

The file is pipe-delimited and contains one row per (ZCTA, county) pair.
For ZCTAs that span multiple counties, we keep the county with the
largest shared land area as the dominant county.
"""

from __future__ import annotations

import logging

import pandas as pd
import requests

logger = logging.getLogger(__name__)

ZCTA_COUNTY_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/zcta520/"
    "tab20_zcta520_county20_natl.txt"
)


def fetch_zcta_county(url: str = ZCTA_COUNTY_URL) -> pd.DataFrame:
    """Fetch the Census ZCTA-to-County relationship file.

    Returns columns: ``zip``, ``county_fips``, ``county_name``.
    For ZCTAs spanning multiple counties, the dominant county (largest
    shared land area) is selected.
    """
    logger.info("Fetching ZCTA-County relationship from %s", url)
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    from io import StringIO
    raw = pd.read_csv(StringIO(resp.text), sep="|", dtype=str)

    # Strip BOM from leading column name if present
    raw.columns = [c.lstrip("﻿") for c in raw.columns]

    # Required columns
    zcta_col = "GEOID_ZCTA5_20"
    county_col = "GEOID_COUNTY_20"
    name_col = "NAMELSAD_COUNTY_20"
    area_col = "AREALAND_PART"

    if zcta_col not in raw.columns:
        raise RuntimeError(
            f"Expected column '{zcta_col}' missing. Got: {raw.columns.tolist()}"
        )

    df = raw[[zcta_col, county_col, name_col, area_col]].copy()
    df = df.rename(columns={
        zcta_col: "zip",
        county_col: "county_fips",
        name_col: "county",
        area_col: "shared_area",
    })

    # Drop rows where ZCTA is missing (header artifact rows)
    df = df.dropna(subset=["zip", "county_fips"])
    df["zip"] = df["zip"].astype(str).str.zfill(5)
    df["county_fips"] = df["county_fips"].astype(str).str.zfill(5)
    df["shared_area"] = pd.to_numeric(df["shared_area"], errors="coerce").fillna(0)

    # Strip " County", " Parish", etc. suffixes from name (keep raw for now)
    df["county"] = df["county"].astype(str).str.strip()

    # Pick the dominant county per ZCTA (largest shared land area)
    df = df.sort_values("shared_area", ascending=False)
    df = df.groupby("zip", as_index=False).first()
    df = df[["zip", "county_fips", "county"]]

    return df
