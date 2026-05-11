"""Fetch IPEDS institution and enrollment data, aggregated by ZIP.

IPEDS (Integrated Postsecondary Education Data System) is the
Department of Education's authoritative database of every degree-granting
institution in the United States. Data is public domain.

We pull two annual files:

  * **HD** (institutional characteristics directory): ZIP, institution name,
    sector, level, etc. ~6,000 institutions.
  * **EFFY** (Fall Enrollment): student headcount per institution, broken
    down by level. We only need the "all students, all levels" total.

The result is aggregated to the ZIP level: how many institutions are in
each ZIP, and what the total student enrollment is across them.

Source URLs:
    https://nces.ed.gov/ipeds/datacenter/data/HD{year}.zip
    https://nces.ed.gov/ipeds/datacenter/data/EFFY{year}.zip
"""

from __future__ import annotations

import io
import logging
import zipfile

import pandas as pd
import requests

logger = logging.getLogger(__name__)

IPEDS_HD_URL = "https://nces.ed.gov/ipeds/datacenter/data/HD{year}.zip"
IPEDS_EFFY_URL = "https://nces.ed.gov/ipeds/datacenter/data/EFFY{year}.zip"


def _download_zip_member(url: str, expected_csv: str) -> pd.DataFrame:
    logger.info("Fetching %s", url)
    resp = requests.get(url, timeout=180)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        members = zf.namelist()
        target = next((m for m in members if m.lower() == expected_csv.lower()), None)
        if target is None:
            raise RuntimeError(
                f"{expected_csv} not in {url}; got {members}"
            )
        with zf.open(target) as fh:
            return pd.read_csv(fh, encoding="latin-1", dtype=str, low_memory=False)


def fetch_ipeds(year: int = 2022) -> pd.DataFrame:
    """Aggregate IPEDS HD + EFFY data by ZIP.

    Returns columns:
      ``zip``, ``college_count``, ``college_enrollment_total``.

    Each row represents one ZIP. ZIPs not appearing in IPEDS are absent
    from the result (the merger left-joins, leaving 0 / null).
    """
    hd = _download_zip_member(IPEDS_HD_URL.format(year=year), f"hd{year}.csv")
    effy = _download_zip_member(IPEDS_EFFY_URL.format(year=year), f"effy{year}.csv")

    # Clean ZIPs to 5-digit format
    hd["zip"] = hd["ZIP"].str.split("-").str[0].str.zfill(5)
    hd = hd[["UNITID", "zip", "INSTNM"]].rename(columns={"INSTNM": "name"})

    # EFFY rows where EFFYALEV == 1 are "all students, all levels, total"
    effy["EFFYALEV"] = pd.to_numeric(effy["EFFYALEV"], errors="coerce")
    total_enrollment = effy[effy["EFFYALEV"] == 1].copy()
    total_enrollment["enrollment"] = pd.to_numeric(
        total_enrollment["EFYTOTLT"], errors="coerce"
    )
    total_enrollment = total_enrollment[["UNITID", "enrollment"]]

    # Join institutions with enrollment
    merged = hd.merge(total_enrollment, on="UNITID", how="left")

    # Aggregate by ZIP
    by_zip = merged.groupby("zip", as_index=False).agg(
        college_count=("UNITID", "count"),
        college_enrollment_total=("enrollment", "sum"),
    )
    by_zip["college_enrollment_total"] = (
        by_zip["college_enrollment_total"].fillna(0).round().astype(int)
    )

    return by_zip
