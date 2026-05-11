"""Fetch OMB CBSA delineation files for county-to-CBSA mapping.

OMB publishes county-level CBSA assignments annually via Census. Each row
describes one constituent county; the file gives both the (cbsa_code,
cbsa_name, cbsa_type) of the parent CBSA and the (csa_code, csa_name) of
its broader CSA, when applicable.

Direct download URL pattern (year-stamped):
    https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/{year}/delineation-files/list1_{year}.xlsx

The 2023 vintage URL works as of writing:
    https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx
"""

from __future__ import annotations

import logging
from io import BytesIO

import pandas as pd
import requests

logger = logging.getLogger(__name__)

DEFAULT_OMB_URL = (
    "https://www2.census.gov/programs-surveys/metro-micro/geographies/"
    "reference-files/2023/delineation-files/list1_2023.xlsx"
)


def fetch_omb_county_cbsa(url_or_path: str = DEFAULT_OMB_URL) -> pd.DataFrame:
    """Return one row per county with its CBSA/CSA assignment.

    Output columns:
      ``county_fips``, ``cbsa_code``, ``cbsa_name``, ``cbsa_type``,
      ``csa_code``, ``csa_name``

    Counties not in any CBSA are absent from the result; the merger
    handles them as null on the consumer side via a left join.
    """
    if url_or_path.startswith("http"):
        logger.info("Fetching OMB delineation from %s", url_or_path)
        resp = requests.get(url_or_path, timeout=180)
        resp.raise_for_status()
        df = pd.read_excel(BytesIO(resp.content), header=2, dtype=str)
    else:
        logger.info("Reading OMB delineation from %s", url_or_path)
        df = pd.read_excel(url_or_path, header=2, dtype=str)

    df.columns = [c.strip() for c in df.columns]

    # Detect column names defensively (they can shift across vintages)
    cbsa_code_col = next((c for c in df.columns if "CBSA Code" in c), None)
    cbsa_name_col = next((c for c in df.columns if "CBSA Title" in c), None)
    cbsa_type_col = next(
        (c for c in df.columns if "Metropolitan/Micropolitan" in c), None
    )
    csa_code_col = next((c for c in df.columns if "CSA Code" in c), None)
    csa_name_col = next((c for c in df.columns if "CSA Title" in c), None)
    state_fips_col = next((c for c in df.columns if "FIPS State Code" in c), None)
    county_fips_col = next((c for c in df.columns if "FIPS County Code" in c), None)

    required = [cbsa_code_col, state_fips_col, county_fips_col]
    if not all(required):
        raise RuntimeError(
            f"OMB file missing required columns. Got: {df.columns.tolist()}"
        )

    # Drop the trailing notes rows: OMB sheets often have explanatory text below the data.
    # We require valid state/county FIPS to filter to real rows.
    df = df.dropna(subset=[state_fips_col, county_fips_col, cbsa_code_col]).copy()

    # Build 5-digit county FIPS = state(2) + county(3)
    state_fips = df[state_fips_col].astype(float).astype(int).astype(str).str.zfill(2)
    county_fips_3 = df[county_fips_col].astype(float).astype(int).astype(str).str.zfill(3)
    df["county_fips"] = state_fips + county_fips_3

    df = df.rename(columns={
        cbsa_code_col: "cbsa_code",
        cbsa_name_col: "cbsa_name",
        cbsa_type_col: "_cbsa_type_raw",
        csa_code_col: "csa_code",
        csa_name_col: "csa_name",
    })

    df["cbsa_code"] = df["cbsa_code"].astype(str).str.zfill(5)
    type_map = {
        "Metropolitan Statistical Area": "Metro",
        "Micropolitan Statistical Area": "Micro",
    }
    df["cbsa_type"] = df["_cbsa_type_raw"].map(type_map)

    # CSA codes are floats in the source; coerce to padded string when present
    df["csa_code"] = (
        pd.to_numeric(df["csa_code"], errors="coerce")
        .astype("Int64")
        .astype(str)
        .replace("<NA>", pd.NA)
    )

    return df[["county_fips", "cbsa_code", "cbsa_name", "cbsa_type", "csa_code", "csa_name"]]
