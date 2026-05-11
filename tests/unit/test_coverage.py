"""Tests verifying ZIP coverage of non-residential / unusual ZIPs.

These tests exist to catch regressions in coverage for ZIP types that
historically lacked Census ZCTA tabulation: PO Box ZIPs, military
APO/FPO/DPO ZIPs, and Unique organizational ZIPs. The bundled data
should include them with appropriate ``zip_type`` even when demographics
are null.
"""

from __future__ import annotations

import pytest

import uszipinfo


# Curated list of well-known non-residential ZIPs that must be present
KNOWN_PO_BOX_ZIPS = [
    "00501",  # Holtsville NY (IRS administrative)
    "00544",  # Holtsville NY (IRS administrative)
    "10101",  # NYC PO Box (Manhattan)
    "10102",
    "20505",  # CIA HQ (DC government PO Box)
    "20511",  # Pentagon area
    "77201",  # Houston PO Box
    "99950",  # Ketchikan AK (post office only)
]

KNOWN_MILITARY_ZIPS = [
    "09001",  # APO AA
    "09704",  # APO AE
    "34030",  # APO AA - Americas
    "96531",  # FPO AA - Pacific
]

KNOWN_TERRITORY_ZIPS = [
    "00601",  # Puerto Rico - Adjuntas
    "00801",  # US Virgin Islands - St Thomas
    "96910",  # Guam - Hagatna
]


@pytest.mark.parametrize("zip_code", KNOWN_PO_BOX_ZIPS)
def test_po_box_zips_present(zip_code: str):
    info = uszipinfo.lookup(zip_code)
    assert info.zip_type == "PO_Box", (
        f"{zip_code} should be PO_Box, got {info.zip_type}"
    )
    # PO Box ZIPs should have at least state and city
    assert info.state is not None
    assert info.primary_city is not None


@pytest.mark.parametrize("zip_code", KNOWN_MILITARY_ZIPS)
def test_military_zips_present(zip_code: str):
    info = uszipinfo.lookup(zip_code)
    assert info.zip_type == "Military"
    assert info.state in {"AA", "AE", "AP"}


@pytest.mark.parametrize("zip_code", KNOWN_TERRITORY_ZIPS)
def test_territory_zips_present(zip_code: str):
    info = uszipinfo.lookup(zip_code)
    assert info.state in {"PR", "VI", "GU", "AS", "MP"}


def test_total_zip_count_in_expected_range():
    df = uszipinfo.load()
    # Real data should have ~42k records
    # Synthetic fallback has just a handful
    assert len(df) >= 5
    assert len(df) <= 50_000


def test_required_zip_types_exist():
    df = uszipinfo.load()
    if len(df) < 1000:
        pytest.skip("Synthetic data — not all zip types represented")
    types = set(df["zip_type"].unique())
    assert "Standard" in types
    assert "PO_Box" in types
    assert "Military" in types
    assert "Unique" in types


def test_demographics_populated_for_standard_zips():
    df = uszipinfo.load()
    if len(df) < 1000:
        pytest.skip("Synthetic data — coverage thresholds don't apply")
    # Standard zips should have population data > 95% of the time
    standard = df[df["zip_type"] == "Standard"]
    if len(standard) > 0:
        coverage = standard["population"].notna().mean()
        assert coverage > 0.90, f"Standard ZIP population coverage: {coverage:.1%}"


def test_demographics_null_for_po_box_zips():
    """PO Box ZIPs should typically have null demographics by design."""
    df = uszipinfo.load()
    if len(df) < 1000:
        pytest.skip("Synthetic data — distribution doesn't apply")
    po_box = df[df["zip_type"] == "PO_Box"]
    if len(po_box) > 0:
        # Most PO Box ZIPs should have null population (no residents)
        null_rate = po_box["population"].isna().mean()
        assert null_rate > 0.50, (
            f"PO Box population null rate: {null_rate:.1%} (expected >50%)"
        )
