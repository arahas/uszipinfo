"""Fetch the Census Gazetteer ZCTA file for lat/lon and area data.

The Gazetteer is a tab-separated text file. URLs follow a stable pattern:
    https://www2.census.gov/geo/docs/maps-data/data/gazetteer/{year}_Gazetteer/{year}_Gaz_zcta_national.zip
"""

from __future__ import annotations

import io
import logging
import zipfile

import pandas as pd
import requests

logger = logging.getLogger(__name__)

GAZETTEER_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/"
    "{year}_Gazetteer/{year}_Gaz_zcta_national.zip"
)

# 1 square mile = 2,589,988.110336 square meters
SQ_M_PER_SQ_MI = 2_589_988.110336


def fetch_gazetteer(year: int) -> pd.DataFrame:
    """Download the Gazetteer ZCTA file and return a tidy DataFrame.

    Returns columns: ``zip``, ``lat``, ``lon``, ``land_area_sq_mi``,
    ``water_area_sq_mi``.
    """
    url = GAZETTEER_URL.format(year=year)
    logger.info("Fetching Gazetteer from %s", url)
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()

    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # The file inside the zip is named like "{year}_Gaz_zcta_national.txt"
        members = [n for n in zf.namelist() if n.endswith(".txt")]
        if not members:
            raise RuntimeError(f"No text file found in Gazetteer zip from {url}")
        with zf.open(members[0]) as fh:
            df = pd.read_csv(fh, sep="\t", dtype={"GEOID": str})

    # Column names vary slightly across years; rename defensively
    rename_map = {
        "GEOID": "zip",
        "ALAND": "land_area_sq_m",
        "AWATER": "water_area_sq_m",
        "INTPTLAT": "lat",
        "INTPTLONG": "lon",
    }
    # Strip whitespace from column names (Census files sometimes have trailing spaces)
    df.columns = [c.strip() for c in df.columns]
    rename_present = {k: v for k, v in rename_map.items() if k in df.columns}
    df = df.rename(columns=rename_present)

    df = df[["zip", "lat", "lon", "land_area_sq_m", "water_area_sq_m"]]
    df["zip"] = df["zip"].astype(str).str.zfill(5)
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["land_area_sq_mi"] = pd.to_numeric(df["land_area_sq_m"], errors="coerce") / SQ_M_PER_SQ_MI
    df["water_area_sq_mi"] = pd.to_numeric(df["water_area_sq_m"], errors="coerce") / SQ_M_PER_SQ_MI
    df = df.drop(columns=["land_area_sq_m", "water_area_sq_m"])

    return df
