"""Synthesize records for military APO/FPO/DPO ZIPs.

Military mail ZIPs don't appear in Census ZCTA data or GeoNames because
they don't have geographic coordinates — military mail goes through
fleet post offices that route to wherever the recipient currently is.

USPS uses three "state codes" for military mail:
    AA — Armed Forces Americas (excluding Canada)
    AE — Armed Forces Africa, Canada, Europe, Middle East
    AP — Armed Forces Pacific

The state code is implied by the ZIP prefix. For ZIPs that aren't covered
by any other data source, we generate skeleton records with the right
``zip_type`` and ``state`` so consumers can identify them.
"""


from __future__ import annotations


import pandas as pd

#: Mapping from ZIP prefix range to (military "state code", region name).
#: Sources: USPS Domestic Mail Manual; widely-published prefix conventions.
MILITARY_PREFIXES: list[tuple[str, str, str, str]] = [
    # (start_prefix, end_prefix_inclusive, state_code, region_name)
    ("090", "099", "AE", "Armed Forces Europe"),
    ("340", "340", "AA", "Armed Forces Americas"),
    ("962", "966", "AP", "Armed Forces Pacific"),
]


def _classify_military(zip_code: str) -> tuple[str, str] | None:
    """Return ``(state_code, region_name)`` if zip is military, else None."""
    prefix = zip_code[:3]
    for start, end, state_code, region in MILITARY_PREFIXES:
        if start <= prefix <= end:
            return state_code, region
    return None


def synthesize_military_records(missing_zips: list[str]) -> pd.DataFrame:
    """Generate skeleton records for military ZIPs missing from other sources.

    Parameters
    ----------
    missing_zips:
        ZIPs that have no data from Census/GeoNames but appear in
        downstream sources (e.g., AMD).

    Returns
    -------
    DataFrame with columns: ``zip``, ``state``, ``state_name``,
    ``primary_city``, ``zip_type``. ZIPs that don't match any military
    prefix range are returned with ``zip_type='Standard'`` and other
    fields null — these are typically newly-allocated USPS ZIPs that
    haven't been incorporated into any data source yet.
    """
    records = []
    for z in missing_zips:
        military = _classify_military(z)
        if military is not None:
            state_code, region = military
            records.append({
                "zip": z,
                "state": state_code,
                "state_name": region,
                "primary_city": region,  # No specific city; use region name
                "zip_type": "Military",
                "is_metro": False,
                "is_college_town": False,
                "is_resort_area": False,
            })
        else:
            # Unknown ZIP — preserve it as a record so consumers see it,
            # but don't claim demographics or geography.
            records.append({
                "zip": z,
                "state": None,
                "state_name": None,
                "primary_city": None,
                "zip_type": "Standard",
                "is_metro": False,
                "is_college_town": False,
                "is_resort_area": False,
            })
    return pd.DataFrame.from_records(records)
