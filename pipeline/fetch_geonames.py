"""Fetch ZIP coverage data from GeoNames.

GeoNames publishes a free, redistributable (CC BY 4.0) postal code dataset
with broad coverage of US ZIPs including PO Box, Unique, and other
non-residential ZIPs that don't appear in Census ZCTA-based sources.

This is what closes the Census coverage gap (~7,000 ZIPs that exist as
USPS deliverable addresses but lack a ZCTA).

Source files:
    https://download.geonames.org/export/zip/US.zip
    https://download.geonames.org/export/zip/PR.zip
    https://download.geonames.org/export/zip/VI.zip
    https://download.geonames.org/export/zip/GU.zip
    https://download.geonames.org/export/zip/AS.zip
    https://download.geonames.org/export/zip/MP.zip

Schema (tab-delimited):
    country, zip, city, state_name, state, county, county_code,
    admin3_name, admin3_code, lat, lon, accuracy
"""

from __future__ import annotations

import io
import logging
import zipfile

import pandas as pd
import requests

logger = logging.getLogger(__name__)

GEONAMES_URL = "https://download.geonames.org/export/zip/{country}.zip"

#: ISO codes for the territories whose ZIPs we want to merge in alongside
#: the main US dataset. Each becomes a separate ZIP file download.
TERRITORIES = ["PR", "VI", "GU", "AS", "MP"]

GEONAMES_COLUMNS = [
    "country", "zip", "city", "state_name", "state",
    "county", "county_code",
    "admin3_name", "admin3_code",
    "lat", "lon", "accuracy",
]


def _fetch_one(country_code: str) -> pd.DataFrame:
    """Download and parse one GeoNames ZIP file."""
    url = GEONAMES_URL.format(country=country_code)
    logger.info("Fetching GeoNames %s from %s", country_code, url)
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        with zf.open(f"{country_code}.txt") as fh:
            df = pd.read_csv(
                fh,
                sep="\t",
                header=None,
                names=GEONAMES_COLUMNS,
                dtype=str,
                na_values=[""],
                keep_default_na=False,
            )
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    return df


def fetch_geonames() -> pd.DataFrame:
    """Fetch GeoNames postal data for the US plus all territories.

    Returns columns: ``zip``, ``primary_city``, ``state``, ``state_name``,
    ``county_name_geonames``, ``lat_geonames``, ``lon_geonames``.

    Suffixes on lat/lon and county_name disambiguate from the more
    authoritative Census Gazetteer values; the merger uses GeoNames only
    as a fallback where Census data is absent.
    """
    parts = [_fetch_one("US")]
    for terr in TERRITORIES:
        try:
            parts.append(_fetch_one(terr))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to fetch %s: %s", terr, exc)

    df = pd.concat(parts, ignore_index=True)
    df["zip"] = df["zip"].astype(str).str.zfill(5)

    # Drop duplicates if any (the territory files sometimes overlap with US.zip)
    df = df.drop_duplicates(subset="zip", keep="first")

    # Territory files (PR, VI, GU, AS, MP) put the municipality/island
    # in the state column rather than the territory abbrev. Override using
    # the country code, which is the authoritative territory identifier.
    territory_state_map = {
        "PR": ("PR", "Puerto Rico"),
        "VI": ("VI", "US Virgin Islands"),
        "GU": ("GU", "Guam"),
        "AS": ("AS", "American Samoa"),
        "MP": ("MP", "Northern Mariana Islands"),
    }
    territory_mask = df["country"].isin(territory_state_map.keys())
    if territory_mask.any():
        df.loc[territory_mask, "state"] = df.loc[territory_mask, "country"].map(
            lambda c: territory_state_map[c][0]
        )
        df.loc[territory_mask, "state_name"] = df.loc[territory_mask, "country"].map(
            lambda c: territory_state_map[c][1]
        )

    # Military APO/FPO/DPO ZIPs in the US file have empty state but encode
    # the military "state" (AA/AE/AP) in the place name column. Detect and
    # populate the state from the city name.
    military_region_map = {
        "AA": ("AA", "Armed Forces Americas"),
        "AE": ("AE", "Armed Forces Europe"),
        "AP": ("AP", "Armed Forces Pacific"),
    }
    for code, (state, name) in military_region_map.items():
        # match place names like "APO AE", "FPO AA", "DPO AP"
        mask = (
            df["state"].isna() | (df["state"].astype(str).str.strip() == "")
        ) & df["city"].astype(str).str.match(rf"^[AFD]PO\s+{code}\b", na=False)
        if mask.any():
            df.loc[mask, "state"] = state
            df.loc[mask, "state_name"] = name

    df = df.rename(columns={
        "city": "primary_city",
        "county": "county_name_geonames",
        "lat": "lat_geonames",
        "lon": "lon_geonames",
    })

    return df[[
        "zip", "primary_city",
        "state", "state_name",
        "county_name_geonames",
        "lat_geonames", "lon_geonames",
    ]]
