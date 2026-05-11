"""Schema-level tests."""

from datetime import date

import pytest

import uszipinfo
from uszipinfo.schema import COLUMNS, ENUMS, REQUIRED_COLUMNS, ZipInfo


def test_columns_match_dataframe():
    df = uszipinfo.load()
    assert set(df.columns) == set(COLUMNS)


def test_required_columns_have_no_nulls():
    df = uszipinfo.load()
    for col in REQUIRED_COLUMNS:
        assert df[col].notna().all(), f"Column {col} has nulls"


def test_enum_values_within_allowed():
    df = uszipinfo.load()
    for col, allowed in ENUMS.items():
        actual = set(df[col].dropna().unique())
        unexpected = actual - allowed
        assert not unexpected, f"{col}: unexpected values {unexpected}"


def test_zipinfo_instances_constructable():
    info = uszipinfo.lookup("98004")
    assert isinstance(info, ZipInfo)


def test_zipinfo_is_immutable():
    info = uszipinfo.lookup("98004")
    with pytest.raises((AttributeError, Exception)):
        info.population = 99999  # type: ignore[misc]


def test_data_year_is_int():
    info = uszipinfo.lookup("98004")
    assert isinstance(info.data_year, int)


def test_build_date_is_date():
    info = uszipinfo.lookup("98004")
    assert isinstance(info.build_date, date)


def test_module_constants_present():
    assert hasattr(uszipinfo, "__version__")
    assert hasattr(uszipinfo, "DATA_YEAR")
    assert hasattr(uszipinfo, "COLUMNS")
    assert hasattr(uszipinfo, "ENUMS")
