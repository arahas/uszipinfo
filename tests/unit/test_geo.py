"""Tests for geographic helpers (distance and nearest-neighbor)."""

import pytest

import uszipinfo
from uszipinfo.geo import haversine_mi


def test_haversine_zero_distance():
    assert haversine_mi(40.0, -74.0, 40.0, -74.0) == pytest.approx(0.0, abs=1e-6)


def test_haversine_known_distance():
    # NYC (~40.7128, -74.0060) to LA (~34.0522, -118.2437) ≈ 2451 miles
    d = haversine_mi(40.7128, -74.0060, 34.0522, -118.2437)
    assert 2400 < d < 2500


def test_distance_mi_via_zip_codes():
    # Bellevue WA → Manhattan NY ≈ 2400 miles
    d = uszipinfo.distance_mi("98004", "10001")
    assert 2300 < d < 2500


def test_distance_mi_unknown_zip_raises():
    with pytest.raises(KeyError):
        uszipinfo.distance_mi("98004", "00000")


def test_nearest_zips_returns_dataframe_with_distance():
    df = uszipinfo.nearest_zips("98004", n=5)
    assert "distance_mi" in df.columns
    assert "98004" not in df["zip"].tolist()
    assert df["distance_mi"].is_monotonic_increasing
    # Real data: there should be other ZIPs within reasonable distance
    assert (df["distance_mi"] < 100).all()


def test_nearest_zips_respects_max_distance():
    df = uszipinfo.nearest_zips("98004", n=20, max_distance_mi=10)
    assert (df["distance_mi"] <= 10).all()


def test_nearest_zips_short_radius():
    # In dense urban areas there should be many ZIPs within 5 mi
    df = uszipinfo.nearest_zips("10001", n=20, max_distance_mi=5)
    assert len(df) > 5
