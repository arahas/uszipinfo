"""Tests for uszipinfo.lookup and lookup_many."""

import pandas as pd
import pytest

import uszipinfo


def test_lookup_known_zip_returns_zipinfo():
    info = uszipinfo.lookup("98004")
    assert info.zip == "98004"
    assert info.state == "WA"
    # Bellevue is a non-trivial-population urban ZIP regardless of vintage
    assert info.population is not None and info.population > 5_000
    assert info.is_metro is True


def test_lookup_pads_short_zip():
    # 4-digit input should be zero-padded
    info = uszipinfo.lookup("2139")
    assert info.zip == "02139"


def test_lookup_handles_zip_plus_4():
    info = uszipinfo.lookup("98004-1234")
    assert info.zip == "98004"


def test_lookup_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        uszipinfo.lookup("00000")


def test_lookup_invalid_format_raises_valueerror():
    with pytest.raises(ValueError):
        uszipinfo.lookup("ABCDE")


def test_lookup_many_returns_dataframe():
    df = uszipinfo.lookup_many(["98004", "10001"])
    assert isinstance(df, pd.DataFrame)
    assert set(df["zip"]) == {"98004", "10001"}


def test_lookup_many_preserves_order():
    df = uszipinfo.lookup_many(["10001", "98004", "02139"])
    assert df["zip"].tolist() == ["10001", "98004", "02139"]


def test_lookup_many_drops_unknown_zips_silently():
    df = uszipinfo.lookup_many(["98004", "00000"])
    assert df["zip"].tolist() == ["98004"]


def test_load_returns_full_table():
    df = uszipinfo.load()
    assert isinstance(df, pd.DataFrame)
    assert "zip" in df.columns
    # We expect either real data (~33k ZIPs) or fallback synthetic (5)
    assert len(df) >= 5


def test_zipinfo_to_dict_round_trip():
    info = uszipinfo.lookup("98004")
    d = info.to_dict()
    assert d["zip"] == "98004"
    assert d["state"] == "WA"


def test_msa_fields_match_cbsa_for_metros():
    # Bellevue is in the Seattle MSA
    info = uszipinfo.lookup("98004")
    assert info.cbsa_type == "Metro"
    assert info.msa_code == info.cbsa_code
    assert info.msa_name == info.cbsa_name


def test_dense_urban_classification_for_manhattan():
    info = uszipinfo.lookup("10001")
    assert info.urbanicity_tier in {"dense_urban", "urban"}
    assert info.is_metro is True
