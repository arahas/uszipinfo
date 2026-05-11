"""Test fixtures and shared setup."""

from __future__ import annotations

import datetime as _dt
from pathlib import Path

import pandas as pd
import pytest

from uszipinfo.schema import COLUMNS

# Where the bundled data file is expected to land
BUNDLED_DATA_PATH = Path(__file__).parents[1] / "src" / "uszipinfo" / "_data" / "zip_metadata_2022.parquet"


def _build_synthetic_record(
    zip_code: str,
    state: str = "WA",
    state_name: str = "Washington",
    county: str = "King",
    county_fips: str = "53033",
    primary_city: str = "Bellevue",
    lat: float = 47.6,
    lon: float = -122.2,
    timezone: str = "America/Los_Angeles",
    land_area_sq_mi: float = 10.0,
    water_area_sq_mi: float = 1.0,
    cbsa_code: str = "42660",
    cbsa_name: str = "Seattle-Tacoma-Bellevue, WA",
    cbsa_type: str = "Metro",
    csa_code: str = "500",
    csa_name: str = "Seattle-Tacoma, WA",
    is_metro: bool = True,
    census_region: str = "West",
    census_division: str = "Pacific",
    population: int = 30000,
    population_density: float = 3000.0,
    households: int = 12000,
    median_age: float = 38.0,
    pct_under_18: float = 0.20,
    pct_65_plus: float = 0.15,
    median_household_income: int = 100000,
    pct_below_poverty: float = 0.05,
    pct_employed: float = 0.7,
    mean_travel_time_to_work_minutes: float = 28.0,
    pct_no_vehicles: float = 0.06,
    pct_bachelors_or_higher: float = 0.6,
    total_housing_units: int = 13000,
    pct_owner_occupied: float = 0.55,
    pct_vacant: float = 0.05,
    pct_single_family: float = 0.5,
    pct_multi_family: float = 0.4,
    median_home_value: int = 700000,
    vacancy_for_seasonal_use: float = 0.02,
    pct_white: float = 0.6,
    pct_black: float = 0.05,
    pct_hispanic: float = 0.1,
    pct_asian: float = 0.2,
    pct_native_american: float = 0.005,
    pct_pacific_islander: float = 0.005,
    zip_type: str = "Standard",
    urbanicity_tier: str = "urban",
    climate_zone: str = "temperate",
    is_college_town: bool = False,
    is_resort_area: bool = False,
) -> dict:
    """Construct a synthetic ZIP record for fixtures."""
    msa_code = cbsa_code if cbsa_type == "Metro" else None
    msa_name = cbsa_name if cbsa_type == "Metro" else None
    return dict(
        zip=zip_code,
        state=state, state_name=state_name,
        county=county, county_fips=county_fips,
        primary_city=primary_city,
        lat=lat, lon=lon, timezone=timezone,
        land_area_sq_mi=land_area_sq_mi, water_area_sq_mi=water_area_sq_mi,
        cbsa_code=cbsa_code, cbsa_name=cbsa_name, cbsa_type=cbsa_type,
        msa_code=msa_code, msa_name=msa_name,
        csa_code=csa_code, csa_name=csa_name,
        is_metro=is_metro,
        census_region=census_region, census_division=census_division,
        population=population, population_density=population_density,
        households=households, median_age=median_age,
        pct_under_18=pct_under_18, pct_65_plus=pct_65_plus,
        median_household_income=median_household_income,
        pct_below_poverty=pct_below_poverty,
        pct_employed=pct_employed,
        mean_travel_time_to_work_minutes=mean_travel_time_to_work_minutes,
        pct_no_vehicles=pct_no_vehicles,
        pct_bachelors_or_higher=pct_bachelors_or_higher,
        total_housing_units=total_housing_units,
        pct_owner_occupied=pct_owner_occupied, pct_vacant=pct_vacant,
        pct_single_family=pct_single_family, pct_multi_family=pct_multi_family,
        median_home_value=median_home_value,
        vacancy_for_seasonal_use=vacancy_for_seasonal_use,
        pct_white=pct_white, pct_black=pct_black, pct_hispanic=pct_hispanic,
        pct_asian=pct_asian, pct_native_american=pct_native_american,
        pct_pacific_islander=pct_pacific_islander,
        zip_type=zip_type,
        urbanicity_tier=urbanicity_tier, climate_zone=climate_zone,
        is_college_town=is_college_town, is_resort_area=is_resort_area,
        data_year=2022, build_date=_dt.date(2026, 5, 10), build_version="1.0.0-test",
    )


def _ensure_synthetic_bundle() -> None:
    """Create a small synthetic bundled Parquet so tests can run end-to-end.

    Used only as a fallback when no real data is bundled. If a real
    Parquet built from Census data already exists, leave it alone — the
    tests then run against real data instead of synthetic data.
    """
    if BUNDLED_DATA_PATH.exists():
        return

    records = [
        # Bellevue WA (urban metro)
        _build_synthetic_record("98004"),
        # New York (dense_urban)
        _build_synthetic_record(
            "10001", state="NY", state_name="New York", county="New York",
            county_fips="36061", primary_city="New York",
            lat=40.7506, lon=-73.9971, timezone="America/New_York",
            land_area_sq_mi=0.6, water_area_sq_mi=0.0,
            cbsa_code="35620", cbsa_name="New York-Newark-Jersey City, NY-NJ-PA",
            cbsa_type="Metro", csa_code="408",
            csa_name="New York-Newark, NY-NJ-CT-PA",
            is_metro=True, census_region="Northeast", census_division="Middle Atlantic",
            population=20000, population_density=33333.0,
            urbanicity_tier="dense_urban",
        ),
        # Cambridge MA (college town)
        _build_synthetic_record(
            "02139", state="MA", state_name="Massachusetts", county="Middlesex",
            county_fips="25017", primary_city="Cambridge",
            lat=42.3636, lon=-71.1056, timezone="America/New_York",
            land_area_sq_mi=2.4, water_area_sq_mi=0.1,
            cbsa_code="14460", cbsa_name="Boston-Cambridge-Newton, MA-NH",
            cbsa_type="Metro", csa_code="148",
            csa_name="Boston-Worcester-Providence, MA-RI-NH-CT",
            is_metro=True, census_region="Northeast", census_division="New England",
            population=37000, population_density=15400.0,
            pct_bachelors_or_higher=0.78,
            urbanicity_tier="dense_urban",
            is_college_town=True,
        ),
        # Rural Vermont
        _build_synthetic_record(
            "05753", state="VT", state_name="Vermont", county="Addison",
            county_fips="50001", primary_city="Middlebury",
            lat=44.0153, lon=-73.1668, timezone="America/New_York",
            land_area_sq_mi=42.0, water_area_sq_mi=0.5,
            cbsa_code=None, cbsa_name=None, cbsa_type=None,
            csa_code=None, csa_name=None,
            is_metro=False, census_region="Northeast", census_division="New England",
            population=8500, population_density=200.0,
            pct_bachelors_or_higher=0.55,
            pct_white=0.95, pct_black=0.01, pct_hispanic=0.01, pct_asian=0.02,
            urbanicity_tier="suburban",
            is_college_town=True,
        ),
        # PO Box (no land area)
        _build_synthetic_record(
            "10008", state="NY", state_name="New York", county="New York",
            county_fips="36061", primary_city="New York",
            lat=None, lon=None, timezone=None,
            land_area_sq_mi=0.0, water_area_sq_mi=0.0,
            cbsa_code=None, cbsa_name=None, cbsa_type=None,
            csa_code=None, csa_name=None,
            is_metro=False, census_region="Northeast", census_division="Middle Atlantic",
            population=0, population_density=None, households=0,
            median_age=None, pct_under_18=None, pct_65_plus=None,
            median_household_income=None, pct_below_poverty=None, pct_employed=None,
            mean_travel_time_to_work_minutes=None, pct_no_vehicles=None,
            pct_bachelors_or_higher=None,
            total_housing_units=0, pct_owner_occupied=None, pct_vacant=None,
            pct_single_family=None, pct_multi_family=None,
            median_home_value=None, vacancy_for_seasonal_use=None,
            pct_white=None, pct_black=None, pct_hispanic=None, pct_asian=None,
            pct_native_american=None, pct_pacific_islander=None,
            zip_type="PO_Box",
            urbanicity_tier=None, climate_zone="temperate",
        ),
    ]

    df = pd.DataFrame(records)
    df = df[COLUMNS]
    BUNDLED_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(BUNDLED_DATA_PATH, index=False)


@pytest.fixture(scope="session", autouse=True)
def synthetic_bundle():
    """Ensure a synthetic Parquet exists for tests."""
    _ensure_synthetic_bundle()
    # Reset any in-process cache so tests pick up the freshly written file
    from uszipinfo._internal import data_loader

    data_loader.clear_cache()
    yield
