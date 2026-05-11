"""Merge data from all sources into the canonical metadata DataFrame.

The merger is structured to ensure **complete USPS ZIP coverage**, not
just ZCTA coverage. It uses a layered fallback:

  1. **GeoNames** is the *master ZIP coverage source* — covers
     ~99.3% of all USPS deliverable ZIPs including PO Box, Unique,
     and Territory ZIPs that lack ZCTAs.

  2. **Census ACS** demographics are layered on top via left-join
     on ZIP. PO Box and Unique ZIPs get null demographics here, which
     is correct (they have no residential population to measure).

  3. **Census Gazetteer** lat/lon and area data takes precedence
     over GeoNames where present (Census data has authoritative ZCTA
     boundaries; GeoNames uses approximate centroids).

  4. **Census ZCTA-County relationship** + **OMB CBSA delineation**
     provide MSA / metro context. Available for ZIPs that have a ZCTA.

  5. **Military synthesis** fills in APO/FPO/DPO ZIPs that don't appear
     in any geographic source.
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd

from pipeline.synthesize_military import synthesize_military_records
from uszipinfo.schema import COLUMNS

logger = logging.getLogger(__name__)


# State FIPS code → (USPS abbrev, full name, census region, census division)
STATE_INFO: dict[str, tuple[str, str, str, str]] = {
    "01": ("AL", "Alabama", "South", "East South Central"),
    "02": ("AK", "Alaska", "West", "Pacific"),
    "04": ("AZ", "Arizona", "West", "Mountain"),
    "05": ("AR", "Arkansas", "South", "West South Central"),
    "06": ("CA", "California", "West", "Pacific"),
    "08": ("CO", "Colorado", "West", "Mountain"),
    "09": ("CT", "Connecticut", "Northeast", "New England"),
    "10": ("DE", "Delaware", "South", "South Atlantic"),
    "11": ("DC", "District of Columbia", "South", "South Atlantic"),
    "12": ("FL", "Florida", "South", "South Atlantic"),
    "13": ("GA", "Georgia", "South", "South Atlantic"),
    "15": ("HI", "Hawaii", "West", "Pacific"),
    "16": ("ID", "Idaho", "West", "Mountain"),
    "17": ("IL", "Illinois", "Midwest", "East North Central"),
    "18": ("IN", "Indiana", "Midwest", "East North Central"),
    "19": ("IA", "Iowa", "Midwest", "West North Central"),
    "20": ("KS", "Kansas", "Midwest", "West North Central"),
    "21": ("KY", "Kentucky", "South", "East South Central"),
    "22": ("LA", "Louisiana", "South", "West South Central"),
    "23": ("ME", "Maine", "Northeast", "New England"),
    "24": ("MD", "Maryland", "South", "South Atlantic"),
    "25": ("MA", "Massachusetts", "Northeast", "New England"),
    "26": ("MI", "Michigan", "Midwest", "East North Central"),
    "27": ("MN", "Minnesota", "Midwest", "West North Central"),
    "28": ("MS", "Mississippi", "South", "East South Central"),
    "29": ("MO", "Missouri", "Midwest", "West North Central"),
    "30": ("MT", "Montana", "West", "Mountain"),
    "31": ("NE", "Nebraska", "Midwest", "West North Central"),
    "32": ("NV", "Nevada", "West", "Mountain"),
    "33": ("NH", "New Hampshire", "Northeast", "New England"),
    "34": ("NJ", "New Jersey", "Northeast", "Middle Atlantic"),
    "35": ("NM", "New Mexico", "West", "Mountain"),
    "36": ("NY", "New York", "Northeast", "Middle Atlantic"),
    "37": ("NC", "North Carolina", "South", "South Atlantic"),
    "38": ("ND", "North Dakota", "Midwest", "West North Central"),
    "39": ("OH", "Ohio", "Midwest", "East North Central"),
    "40": ("OK", "Oklahoma", "South", "West South Central"),
    "41": ("OR", "Oregon", "West", "Pacific"),
    "42": ("PA", "Pennsylvania", "Northeast", "Middle Atlantic"),
    "44": ("RI", "Rhode Island", "Northeast", "New England"),
    "45": ("SC", "South Carolina", "South", "South Atlantic"),
    "46": ("SD", "South Dakota", "Midwest", "West North Central"),
    "47": ("TN", "Tennessee", "South", "East South Central"),
    "48": ("TX", "Texas", "South", "West South Central"),
    "49": ("UT", "Utah", "West", "Mountain"),
    "50": ("VT", "Vermont", "Northeast", "New England"),
    "51": ("VA", "Virginia", "South", "South Atlantic"),
    "53": ("WA", "Washington", "West", "Pacific"),
    "54": ("WV", "West Virginia", "South", "South Atlantic"),
    "55": ("WI", "Wisconsin", "Midwest", "East North Central"),
    "56": ("WY", "Wyoming", "West", "Mountain"),
    # US territories
    "60": ("AS", "American Samoa", "Territories", "Pacific Territories"),
    "66": ("GU", "Guam", "Territories", "Pacific Territories"),
    "69": ("MP", "Northern Mariana Islands", "Territories", "Pacific Territories"),
    "72": ("PR", "Puerto Rico", "Territories", "Caribbean Territories"),
    "78": ("VI", "US Virgin Islands", "Territories", "Caribbean Territories"),
}

#: Military "state codes" used for APO/FPO/DPO ZIPs.
MILITARY_STATES = {"AA", "AE", "AP"}


def _backfill_state_from_county_fips(df: pd.DataFrame) -> pd.DataFrame:
    """For rows missing state info but with county_fips, look up state."""
    df = df.copy()
    needs_fill = df["state"].isna() & df["county_fips"].notna()
    if not needs_fill.any():
        return df
    state_fips = df.loc[needs_fill, "county_fips"].astype("string").str[:2]
    df.loc[needs_fill, "state"] = state_fips.map(
        lambda f: STATE_INFO.get(f, (None, None, None, None))[0]
    )
    df.loc[needs_fill, "state_name"] = state_fips.map(
        lambda f: STATE_INFO.get(f, (None, None, None, None))[1]
    )
    return df


def _add_region_division(df: pd.DataFrame) -> pd.DataFrame:
    """Add census_region and census_division based on state."""
    df = df.copy()
    region_map = {abbr: info[2] for abbr, info in
                  ((info[0], info) for info in STATE_INFO.values())}
    division_map = {abbr: info[3] for abbr, info in
                    ((info[0], info) for info in STATE_INFO.values())}
    # Military states: route to "Territories" / "Military Mail" so they're
    # in a known enum but distinguishable.
    region_map.update({"AA": "Territories", "AE": "Territories", "AP": "Territories"})
    division_map.update({
        "AA": "Caribbean Territories",  # Americas military
        "AE": "Caribbean Territories",  # Europe/Africa military
        "AP": "Pacific Territories",     # Pacific military
    })
    df["census_region"] = df["state"].map(region_map)
    df["census_division"] = df["state"].map(division_map)
    return df


def _add_timezone(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort timezone lookup from lat/lon."""
    df = df.copy()
    try:
        from timezonefinder import TimezoneFinder
    except ImportError:
        logger.warning("timezonefinder not installed; timezone column will be null")
        df["timezone"] = None
        return df

    tf = TimezoneFinder()

    def _lookup(row):
        lat, lon = row.get("lat"), row.get("lon")
        if pd.isna(lat) or pd.isna(lon):
            return None
        try:
            return tf.timezone_at(lng=float(lon), lat=float(lat))
        except Exception:
            return None

    df["timezone"] = df.apply(_lookup, axis=1)
    return df


def merge_sources(
    geonames: pd.DataFrame,
    acs: pd.DataFrame,
    gazetteer: pd.DataFrame,
    zcta_county: pd.DataFrame,
    county_cbsa: pd.DataFrame,
    ipeds: Optional[pd.DataFrame] = None,
    *,
    data_year: int,
    build_version: str,
    extra_zips: Optional[list[str]] = None,
) -> pd.DataFrame:
    """Combine all source DataFrames into the canonical metadata table.

    Parameters
    ----------
    geonames:
        Output of :func:`build.fetch_geonames.fetch_geonames`. The master
        ZIP coverage list, with primary_city, state, county_name, lat, lon.
    acs:
        Output of :func:`build.fetch_acs.fetch_acs`. Demographic columns
        keyed by ``zip``.
    gazetteer:
        Output of :func:`build.fetch_gazetteer.fetch_gazetteer`. Census
        Gazetteer with land/water area and authoritative lat/lon for ZCTAs.
    zcta_county:
        Output of :func:`build.fetch_zcta_county.fetch_zcta_county`.
    county_cbsa:
        Output of :func:`build.fetch_omb.fetch_omb_county_cbsa`.
    data_year:
        ACS vintage to record in the build metadata.
    build_version:
        Package version that built this artifact.
    extra_zips:
        Optional list of additional ZIPs that should appear in the output
        (e.g., AMD-derived ZIPs). Any ZIPs in this list not already covered
        get synthesized records (military prefix detection, fallback to
        nulls). Used to ensure ``uszipinfo.lookup(z)`` succeeds for every
        ZIP a downstream consumer cares about.
    """
    logger.info("Merging sources...")

    # ── Step 1: Start from GeoNames as the master ZIP list ──────────────
    df = geonames.copy()

    # ── Step 2: Layer in ACS demographics ───────────────────────────────
    df = df.merge(acs, on="zip", how="left")

    # ── Step 3: Layer in Census Gazetteer ───────────────────────────────
    # Gazetteer has authoritative lat/lon and land area for ZCTAs; prefer
    # over GeoNames coordinates where present.
    df = df.merge(gazetteer, on="zip", how="left", suffixes=("", "_gaz"))
    df["lat"] = df["lat"].fillna(df["lat_geonames"])
    df["lon"] = df["lon"].fillna(df["lon_geonames"])
    df = df.drop(columns=["lat_geonames", "lon_geonames"], errors="ignore")

    # ── Step 4: Layer in county FIPS via Census ZCTA-County ─────────────
    df = df.merge(zcta_county, on="zip", how="left", suffixes=("", "_zc"))
    # Use Census county name where available, fallback to GeoNames county_name
    df["county"] = df["county"].fillna(df["county_name_geonames"])
    df = df.drop(columns=["county_name_geonames"], errors="ignore")

    # ── Step 5: Layer in CBSA via county FIPS ───────────────────────────
    df = df.merge(county_cbsa, on="county_fips", how="left")

    # ── Step 6: Backfill state info from county_fips for ZCTAs ──────────
    # GeoNames provides state for residential ZIPs; for ZCTAs whose state
    # we already have, this is a no-op. For ZIPs missing state in GeoNames
    # but having a county_fips, this fills in.
    df = _backfill_state_from_county_fips(df)

    # ── Step 7: Add region/division and timezone ────────────────────────
    df = _add_region_division(df)
    df = _add_timezone(df)

    # ── Step 8: Population density ──────────────────────────────────────
    df["population_density"] = (
        pd.to_numeric(df.get("population"), errors="coerce")
        / pd.to_numeric(df.get("land_area_sq_mi"), errors="coerce")
    )
    df["population_density"] = df["population_density"].replace(
        [float("inf"), -float("inf")], pd.NA
    )

    # ── Step 9: MSA fields ──────────────────────────────────────────────
    is_metro_mask = df["cbsa_type"].fillna("") == "Metro"
    df["msa_code"] = df["cbsa_code"].where(is_metro_mask)
    df["msa_name"] = df["cbsa_name"].where(is_metro_mask)
    df["is_metro"] = is_metro_mask.fillna(False)

    # ── Step 9.5: Layer in IPEDS institution counts and enrollment ──────
    if ipeds is not None and not ipeds.empty:
        df = df.merge(ipeds, on="zip", how="left")
    df["college_count"] = (
        pd.to_numeric(df.get("college_count"), errors="coerce").fillna(0).astype(int)
    )
    df["college_enrollment_total"] = (
        pd.to_numeric(df.get("college_enrollment_total"), errors="coerce").fillna(0).astype(int)
    )

    # ── Step 10: Add any extra_zips not yet covered (e.g., military) ────
    if extra_zips:
        present = set(df["zip"])
        missing = sorted(set(extra_zips) - present)
        if missing:
            logger.info("Synthesizing %d additional records (military / unknown)", len(missing))
            synth = synthesize_military_records(missing)
            synth = _add_region_division(synth)
            df = pd.concat([df, synth], ignore_index=True)

    # ── Step 11: Build metadata ─────────────────────────────────────────
    df["data_year"] = data_year
    df["build_date"] = pd.Timestamp.today().date()
    df["build_version"] = build_version

    return df


def reorder_to_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Return ``df`` with columns in canonical schema order."""
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[COLUMNS]
