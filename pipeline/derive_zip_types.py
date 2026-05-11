"""Heuristic derivation of USPS ZIP type classification.

The official USPS classification (the .csv file behind their ZIP4 Product)
is not redistributable. This module infers the type from publicly-available
signals:

  * Military prefixes (090-098, 340, 962-966, 099): definitive Military
  * Existing state code AA/AE/AP (set by synthesize_military): definitive Military
  * No ZCTA + no land area + zero/null population: PO Box
  * Has ZCTA + small population + measurable land area: Unique
  * Otherwise: Standard

The result is approximate but usable. The build pipeline records that
this column is heuristic-derived in the data sources doc.
"""

from __future__ import annotations

import pandas as pd

#: Prefix → military region. These are well-published USPS conventions.
MILITARY_PREFIX_RANGES: list[tuple[str, str]] = [
    ("090", "099"),    # Europe / Middle East / Africa (AE)
    ("340", "340"),    # Americas non-Canada (AA)
    ("962", "966"),    # Pacific (AP)
]


def _is_military_prefix(zip_code: str) -> bool:
    prefix = zip_code[:3]
    for low, high in MILITARY_PREFIX_RANGES:
        if low <= prefix <= high:
            return True
    return False


def derive_zip_types(df: pd.DataFrame) -> pd.Series:
    """Return a Series of zip_type strings, indexed like ``df``.

    Heuristics applied in order (first match wins):

      1. **Military** if state ∈ {AA, AE, AP} OR ZIP prefix matches a known
         military range.
      2. **PO_Box** if there is no ZCTA-derived demographic data
         (no population, no county_fips) and no land area, OR if population
         is zero with land area zero.
      3. **Unique** if low-but-nonzero population alongside measurable
         land area (institutional ZIPs like university campuses).
      4. **Standard** for everything else.
    """
    zip_codes = df["zip"].astype(str).str.zfill(5)
    state = df.get("state")
    population = pd.to_numeric(df.get("population"), errors="coerce")
    land_area = pd.to_numeric(df.get("land_area_sq_mi"), errors="coerce")
    county_fips = df.get("county_fips")

    out = pd.Series("Standard", index=df.index, dtype="object")

    # Layer 1: Military
    is_military_state = state.isin(["AA", "AE", "AP"]) if state is not None else pd.Series(False, index=df.index)
    is_military_prefix = zip_codes.map(_is_military_prefix)
    is_military = is_military_state | is_military_prefix
    out[is_military] = "Military"

    # Layer 2: PO Box — no ZCTA-derived data and no population
    has_no_zcta = (
        population.isna()
        & land_area.isna()
        & ((county_fips is None) | (county_fips.isna() if hasattr(county_fips, "isna") else True))
    )
    is_po_box = (
        (out == "Standard") & (
            (population.fillna(0) == 0) & (land_area.fillna(0) < 0.1)
            | has_no_zcta
        )
    )
    out[is_po_box] = "PO_Box"

    # Layer 3: Unique — very low population but has measurable land area
    is_unique = (
        (out == "Standard")
        & (population.fillna(0) > 0)
        & (population.fillna(1e9) < 100)
        & (land_area.fillna(0) >= 0.1)
    )
    out[is_unique] = "Unique"

    return out
