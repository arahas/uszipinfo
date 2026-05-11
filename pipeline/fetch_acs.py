"""Fetch demographic data from the US Census ACS 5-Year Estimates.

The Census API requires no authentication for small queries but the
500-variable-per-request limit means we batch our pulls. Fields we want
map to the cryptic Census variable codes via the ``ACS_VARS`` dictionary.

Variable codes are stable across recent ACS years; the year only affects
the URL path.

Variable code references documented at::

    https://api.census.gov/data/{year}/acs/acs5/variables.html
"""

from __future__ import annotations

import logging
from typing import Optional

import pandas as pd
import requests

logger = logging.getLogger(__name__)

ACS_BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"

#: Mapping from internal field name (Census variable code).
#: Names starting with "_" are intermediate counts that the post-processing
#: step combines into the final output columns.
ACS_VARS: dict[str, str] = {
    # ── Population basics ────────────────────────────────────────────────
    "population":                            "B01003_001E",
    "households":                            "B11001_001E",
    "median_age":                            "B01002_001E",
    # Under-18 buckets (sum of male + female under-18 brackets)
    "_pop_u18_m_lt5":   "B01001_003E",
    "_pop_u18_m_5_9":   "B01001_004E",
    "_pop_u18_m_10_14": "B01001_005E",
    "_pop_u18_m_15_17": "B01001_006E",
    "_pop_u18_f_lt5":   "B01001_027E",
    "_pop_u18_f_5_9":   "B01001_028E",
    "_pop_u18_f_10_14": "B01001_029E",
    "_pop_u18_f_15_17": "B01001_030E",
    # 65+ population (single aggregate)
    "_pop_65_plus":     "B09020_001E",

    # ── Economic ─────────────────────────────────────────────────────────
    "median_household_income":               "B19013_001E",
    "_pop_below_poverty":                    "B17001_002E",
    "_pop_for_poverty":                      "B17001_001E",
    "_in_labor_force":                       "B23025_002E",
    "_civilian_pop_16_plus":                 "B23025_001E",
    # Travel time = aggregate minutes / number of workers
    "_aggregate_travel_minutes":             "B08013_001E",
    "_workers_who_commute":                  "B08303_001E",
    # No-vehicle = owner-occupied no-vehicle + renter-occupied no-vehicle
    "_owner_occupied_no_vehicle":            "B25044_003E",
    "_renter_occupied_no_vehicle":           "B25044_010E",
    "_total_households_for_vehicle":         "B25044_001E",

    # ── Education (population 25+ with bachelor's or higher) ─────────────
    "_bachelors":                            "B15003_022E",
    "_masters":                              "B15003_023E",
    "_professional":                         "B15003_024E",
    "_doctorate":                            "B15003_025E",
    "_pop_25_plus":                          "B15003_001E",

    # ── Housing ──────────────────────────────────────────────────────────
    "total_housing_units":                   "B25001_001E",
    "_owner_occupied_units":                 "B25003_002E",
    "_total_occupied_units":                 "B25003_001E",
    "_vacant_units":                         "B25002_003E",
    "_total_units_for_vacancy":              "B25002_001E",
    # Structure type buckets (B25024). Verified against Census docs:
    #   002 = 1, detached      003 = 1, attached
    #   004 = 2                005 = 3 or 4
    #   006 = 5 to 9           007 = 10 to 19
    #   008 = 20 to 49         009 = 50 or more
    "_units_1_detached":                     "B25024_002E",
    "_units_1_attached":                     "B25024_003E",
    "_units_5_to_9":                         "B25024_006E",
    "_units_10_to_19":                       "B25024_007E",
    "_units_20_to_49":                       "B25024_008E",
    "_units_50_plus":                        "B25024_009E",
    "_units_total_for_type":                 "B25024_001E",
    "median_home_value":                     "B25077_001E",
    "_seasonal_vacant":                      "B25004_006E",

    # ── Race / ethnicity (B03002 — by Hispanic origin) ───────────────────
    "_pop_white_nh":                         "B03002_003E",
    "_pop_black":                            "B03002_004E",
    "_pop_native":                           "B03002_005E",
    "_pop_asian":                            "B03002_006E",
    "_pop_pacific":                          "B03002_007E",
    "_pop_hispanic":                         "B03002_012E",
    "_pop_for_race":                         "B03002_001E",
}


def _batch(seq: list[str], size: int) -> list[list[str]]:
    return [seq[i : i + size] for i in range(0, len(seq), size)]


def fetch_acs(
    year: int,
    api_key: Optional[str] = None,
    batch_size: int = 40,
    geography: str = "zip code tabulation area:*",
) -> pd.DataFrame:
    """Fetch ACS 5-year estimates for all ZCTAs.

    Returns a DataFrame keyed by ``zip`` with the canonical post-processed
    columns (population, percentages, etc.).

    The Census API allows up to 50 variables per request and throttles
    aggressive callers. Get a free API key from
    https://api.census.gov/data/key_signup.html and pass via ``api_key``
    to avoid rate limits.
    """
    url = ACS_BASE_URL.format(year=year)

    # Each unique variable code is fetched at most once
    code_to_internal: dict[str, list[str]] = {}
    for internal_name, code in ACS_VARS.items():
        code_to_internal.setdefault(code, []).append(internal_name)
    var_codes = sorted(code_to_internal.keys())

    frames: list[pd.DataFrame] = []
    for batch in _batch(var_codes, batch_size):
        params = {
            "get": ",".join(batch),
            "for": geography,
        }
        if api_key:
            params["key"] = api_key
        logger.info("Fetching %d ACS variables", len(batch))
        resp = requests.get(url, params=params, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        cols = data[0]
        df = pd.DataFrame(data[1:], columns=cols)
        frames.append(df)

    merged = frames[0]
    for f in frames[1:]:
        merged = merged.merge(f, on="zip code tabulation area")
    merged = merged.rename(columns={"zip code tabulation area": "zip"})

    # Numeric cast (Census returns strings; sentinel negative codes mean null)
    for col in merged.columns:
        if col == "zip":
            continue
        merged[col] = pd.to_numeric(merged[col], errors="coerce")
        merged.loc[merged[col] < 0, col] = pd.NA

    # Map each Census code to all the internal column names that share it.
    # We do the renames into intermediate columns that post_process_acs uses.
    out = pd.DataFrame({"zip": merged["zip"].astype(str).str.zfill(5)})
    for code, internal_names in code_to_internal.items():
        for name in internal_names:
            out[name] = merged[code]

    return post_process_acs(out)


def post_process_acs(raw: pd.DataFrame) -> pd.DataFrame:
    """Compute derived percentage and ratio fields from raw counts."""
    df = raw.copy()

    # pct_under_18: sum of under-18 buckets / population
    under_18_cols = [c for c in df.columns if c.startswith("_pop_u18_")]
    df["_pop_under_18"] = df[under_18_cols].sum(axis=1, min_count=1)
    df["pct_under_18"] = df["_pop_under_18"] / df["population"]

    df["pct_65_plus"] = df["_pop_65_plus"] / df["population"]

    # Mean travel time = aggregate / workers
    df["mean_travel_time_to_work_minutes"] = (
        df["_aggregate_travel_minutes"] / df["_workers_who_commute"]
    )

    df["pct_below_poverty"] = df["_pop_below_poverty"] / df["_pop_for_poverty"]
    df["pct_employed"] = df["_in_labor_force"] / df["_civilian_pop_16_plus"]

    # No vehicles = (owner-occ no-vehicle + renter-occ no-vehicle) / total households
    df["_no_vehicle_total"] = (
        df["_owner_occupied_no_vehicle"].fillna(0)
        + df["_renter_occupied_no_vehicle"].fillna(0)
    )
    df["pct_no_vehicles"] = df["_no_vehicle_total"] / df["_total_households_for_vehicle"]

    df["pct_bachelors_or_higher"] = (
        df[["_bachelors", "_masters", "_professional", "_doctorate"]].sum(axis=1, min_count=1)
        / df["_pop_25_plus"]
    )

    df["pct_owner_occupied"] = df["_owner_occupied_units"] / df["_total_occupied_units"]
    df["pct_vacant"] = df["_vacant_units"] / df["_total_units_for_vacancy"]
    df["pct_single_family"] = (
        (df["_units_1_detached"].fillna(0) + df["_units_1_attached"].fillna(0))
        / df["_units_total_for_type"]
    )
    df["pct_multi_family"] = (
        (df["_units_5_to_9"].fillna(0)
         + df["_units_10_to_19"].fillna(0)
         + df["_units_20_to_49"].fillna(0)
         + df["_units_50_plus"].fillna(0))
        / df["_units_total_for_type"]
    )
    # Seasonal vacancy uses total housing units as denominator
    df["vacancy_for_seasonal_use"] = df["_seasonal_vacant"] / df["total_housing_units"]

    pop_for_race = df["_pop_for_race"]
    df["pct_white"] = df["_pop_white_nh"] / pop_for_race
    df["pct_black"] = df["_pop_black"] / pop_for_race
    df["pct_hispanic"] = df["_pop_hispanic"] / pop_for_race
    df["pct_asian"] = df["_pop_asian"] / pop_for_race
    df["pct_native_american"] = df["_pop_native"] / pop_for_race
    df["pct_pacific_islander"] = df["_pop_pacific"] / pop_for_race

    # Drop intermediates
    intermediates = [c for c in df.columns if c.startswith("_")]
    df = df.drop(columns=intermediates)

    # Cast counts back to nullable int where appropriate
    for int_col in ("population", "households", "median_household_income",
                    "total_housing_units", "median_home_value"):
        if int_col in df.columns:
            df[int_col] = df[int_col].round().astype("Int64")

    # Final pct clipping
    pct_cols = [c for c in df.columns if c.startswith("pct_") or c.startswith("vacancy_")]
    for c in pct_cols:
        df[c] = df[c].clip(lower=0, upper=1)

    return df
