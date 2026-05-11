"""Tests for uszipinfo.filter_zips."""

import pytest

import uszipinfo


def test_filter_by_state():
    df = uszipinfo.filter_zips(state="WA")
    assert (df["state"] == "WA").all()
    assert len(df) > 0


def test_filter_by_state_list():
    df = uszipinfo.filter_zips(state=["WA", "OR"])
    assert set(df["state"]) <= {"WA", "OR"}
    assert {"WA", "OR"}.issubset(df["state"].unique())


def test_filter_by_min_population():
    df = uszipinfo.filter_zips(min_population=10000)
    assert (df["population"].dropna() >= 10000).all()


def test_filter_by_max_population():
    df = uszipinfo.filter_zips(max_population=10000)
    assert (df["population"].dropna() <= 10000).all()


def test_filter_by_range_combination():
    df = uszipinfo.filter_zips(min_population=5000, max_population=50000)
    pop = df["population"].dropna()
    assert (pop >= 5000).all()
    assert (pop <= 50000).all()


def test_filter_by_boolean():
    df = uszipinfo.filter_zips(is_metro=True)
    assert df["is_metro"].all()
    assert len(df) > 0


def test_filter_by_urbanicity():
    df = uszipinfo.filter_zips(urbanicity_tier="urban")
    assert (df["urbanicity_tier"] == "urban").all()


def test_filter_unknown_column_raises():
    with pytest.raises(KeyError):
        uszipinfo.filter_zips(no_such_column="value")


def test_filter_unknown_range_column_raises():
    with pytest.raises(KeyError):
        uszipinfo.filter_zips(min_no_such_column=10)


def test_filter_combined():
    df = uszipinfo.filter_zips(state="WA", urbanicity_tier="urban", min_population=20000)
    if not df.empty:
        assert (df["state"] == "WA").all()
        assert (df["urbanicity_tier"] == "urban").all()
        assert (df["population"].dropna() >= 20000).all()
