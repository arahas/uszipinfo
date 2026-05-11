"""Schema definitions for uszipinfo.

The ``ZipInfo`` dataclass is the typed representation of a single ZIP record.
The module also exports COLUMNS, ENUMS, and REQUIRED_COLUMNS metadata for
use by the build pipeline and validators.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Optional


@dataclass(frozen=True)
class ZipInfo:
    """Typed metadata for a single US ZIP code.

    All percentage fields are in 0–1 range (not 0–100). Optional fields
    are ``None`` when source data is unavailable for the ZIP.
    """

    # ── Geographic identity ──────────────────────────────────────────────
    zip: str
    state: str
    state_name: str
    county: Optional[str]
    county_fips: Optional[str]
    primary_city: Optional[str]
    lat: Optional[float]
    lon: Optional[float]
    timezone: Optional[str]
    land_area_sq_mi: Optional[float]
    water_area_sq_mi: Optional[float]

    # ── Metro / region ───────────────────────────────────────────────────
    cbsa_code: Optional[str]
    cbsa_name: Optional[str]
    cbsa_type: Optional[str]      # "Metro" | "Micro" | None
    msa_code: Optional[str]
    msa_name: Optional[str]
    csa_code: Optional[str]
    csa_name: Optional[str]
    is_metro: bool
    is_top_100_metro: bool
    dist_to_metro_center_mi: Optional[float]
    census_region: Optional[str]
    census_division: Optional[str]

    # ── Population ───────────────────────────────────────────────────────
    population: Optional[int]
    population_density: Optional[float]
    households: Optional[int]
    avg_household_size: Optional[float]
    median_age: Optional[float]
    pct_under_18: Optional[float]
    pct_age_18_to_24: Optional[float]
    pct_65_plus: Optional[float]

    # ── Economic ─────────────────────────────────────────────────────────
    median_household_income: Optional[int]
    gini_index: Optional[float]
    pct_under_25k: Optional[float]
    pct_over_200k: Optional[float]
    pct_below_poverty: Optional[float]
    pct_employed: Optional[float]
    mean_travel_time_to_work_minutes: Optional[float]
    pct_no_vehicles: Optional[float]

    # ── Education / academic ─────────────────────────────────────────────
    pct_bachelors_or_higher: Optional[float]
    pct_college_enrolled: Optional[float]
    pct_dorm_population: Optional[float]
    college_count: int
    college_enrollment_total: int

    # ── Housing ──────────────────────────────────────────────────────────
    total_housing_units: Optional[int]
    pct_owner_occupied: Optional[float]
    pct_vacant: Optional[float]
    pct_single_family: Optional[float]
    pct_multi_family: Optional[float]
    pct_with_children: Optional[float]
    median_home_value: Optional[int]
    vacancy_for_seasonal_use: Optional[float]

    # ── Race / ethnicity ─────────────────────────────────────────────────
    pct_white: Optional[float]
    pct_black: Optional[float]
    pct_hispanic: Optional[float]
    pct_asian: Optional[float]
    pct_native_american: Optional[float]
    pct_pacific_islander: Optional[float]

    # ── USPS classification (heuristic) ──────────────────────────────────
    zip_type: str   # "Standard" | "PO_Box" | "Unique" | "Military"

    # ── Engineered features ──────────────────────────────────────────────
    urbanicity_tier: Optional[str]   # "rural" | "suburban" | "urban" | "dense_urban"
    climate_zone: Optional[str]      # "tropical" | "subtropical" | "temperate" | "continental" | "cold"
    is_college_town: bool
    is_resort_area: bool

    # ── Build metadata ───────────────────────────────────────────────────
    data_year: int
    build_date: date
    build_version: str

    def to_dict(self) -> dict:
        """Return a plain dict representation."""
        return asdict(self)


# ────────────────────────────────────────────────────────────────────────
# Schema metadata (used by the build pipeline and validators)
# ────────────────────────────────────────────────────────────────────────

#: All column names in canonical order. Must match the dataclass fields.
COLUMNS: list[str] = [
    # Geographic identity
    "zip", "state", "state_name", "county", "county_fips",
    "primary_city", "lat", "lon", "timezone",
    "land_area_sq_mi", "water_area_sq_mi",
    # Metro / region
    "cbsa_code", "cbsa_name", "cbsa_type",
    "msa_code", "msa_name",
    "csa_code", "csa_name",
    "is_metro", "is_top_100_metro", "dist_to_metro_center_mi",
    "census_region", "census_division",
    # Population
    "population", "population_density", "households", "avg_household_size",
    "median_age", "pct_under_18", "pct_age_18_to_24", "pct_65_plus",
    # Economic
    "median_household_income", "gini_index", "pct_under_25k", "pct_over_200k",
    "pct_below_poverty", "pct_employed",
    "mean_travel_time_to_work_minutes", "pct_no_vehicles",
    # Education / academic
    "pct_bachelors_or_higher", "pct_college_enrolled", "pct_dorm_population",
    "college_count", "college_enrollment_total",
    # Housing
    "total_housing_units", "pct_owner_occupied", "pct_vacant",
    "pct_single_family", "pct_multi_family", "pct_with_children",
    "median_home_value", "vacancy_for_seasonal_use",
    # Race / ethnicity
    "pct_white", "pct_black", "pct_hispanic", "pct_asian",
    "pct_native_american", "pct_pacific_islander",
    # USPS classification
    "zip_type",
    # Engineered features
    "urbanicity_tier", "climate_zone", "is_college_town", "is_resort_area",
    # Build metadata
    "data_year", "build_date", "build_version",
]


#: Allowed values for enum-like categorical columns.
ENUMS: dict[str, set[str]] = {
    "cbsa_type": {"Metro", "Micro"},
    "census_region": {"Northeast", "Midwest", "South", "West", "Territories"},
    "census_division": {
        "New England", "Middle Atlantic",
        "East North Central", "West North Central",
        "South Atlantic", "East South Central", "West South Central",
        "Mountain", "Pacific",
        "Pacific Territories", "Caribbean Territories",
    },
    "zip_type": {"Standard", "PO_Box", "Unique", "Military"},
    "urbanicity_tier": {"rural", "suburban", "urban", "dense_urban"},
    "climate_zone": {"tropical", "subtropical", "temperate", "continental", "cold"},
}


#: Columns that must never be null.
#: ``state`` and ``state_name`` may be null for the rare unclassifiable ZIP
#: (e.g., a brand-new ZIP not yet in any data source). They should be
#: populated for >99% of rows but the build doesn't fail if a small
#: number are null.
REQUIRED_COLUMNS: set[str] = {
    "zip", "is_metro", "is_top_100_metro", "zip_type",
    "is_college_town", "is_resort_area",
    "college_count", "college_enrollment_total",
    "data_year", "build_date", "build_version",
}
