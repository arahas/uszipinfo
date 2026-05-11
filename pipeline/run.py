"""End-to-end build orchestrator.

Pulls all source data from public, redistributable sources, merges,
engineers features, validates, and writes the bundled Parquet.

Run as a module::

    python -m build.build --year 2022 \\
        --omb-url https://www2.census.gov/programs-surveys/metro-micro/geographies/reference-files/2023/delineation-files/list1_2023.xlsx \\
        --out src/uszipinfo/_data/zip_metadata_2022.parquet

The Census API key is recommended for ACS pulls. Get a free key at
https://api.census.gov/data/key_signup.html and pass via
``--api-key`` or the ``CENSUS_API_KEY`` env var.

To ensure complete coverage of any specific ZIP set (e.g., AMD-derived
ZIPs), pass ``--extra-zips path/to/zips.csv``. ZIPs not covered by other
sources will be synthesized (military prefix detection or skeleton
records).
"""


from __future__ import annotations


import argparse
import logging
import os
import sys
from pathlib import Path

from pipeline.derive_zip_types import derive_zip_types
from pipeline.engineer_features import add_engineered_features
from pipeline.fetch_acs import fetch_acs
from pipeline.fetch_gazetteer import fetch_gazetteer
from pipeline.fetch_geonames import fetch_geonames
from pipeline.fetch_ipeds import fetch_ipeds
from pipeline.fetch_omb import DEFAULT_OMB_URL, fetch_omb_county_cbsa
from pipeline.fetch_zcta_county import fetch_zcta_county
from pipeline.merger import merge_sources, reorder_to_schema
from pipeline.validator import ValidationError, validate

logger = logging.getLogger("uszipinfo.build")

DEFAULT_BUILD_VERSION = "1.1.0"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build the uszipinfo Parquet artifact.")
    p.add_argument(
        "--year", type=int, required=True,
        help="ACS vintage year (e.g., 2022 for the 2018-2022 5-year estimate).",
    )
    p.add_argument(
        "--gazetteer-year", type=int, default=None,
        help="Gazetteer vintage. Defaults to ACS year.",
    )
    p.add_argument(
        "--omb-url", type=str, default=DEFAULT_OMB_URL,
        help="URL or local path for the OMB CBSA delineation Excel file.",
    )
    p.add_argument(
        "--out", type=str, required=True,
        help="Path to write the Parquet artifact.",
    )
    p.add_argument(
        "--api-key", type=str, default=None,
        help="Census API key. Falls back to CENSUS_API_KEY env var.",
    )
    p.add_argument(
        "--build-version", type=str, default=DEFAULT_BUILD_VERSION,
    )
    p.add_argument(
        "--extra-zips", type=str, default=None,
        help="Path to a CSV with one column 'zip'. ZIPs not covered by "
             "other sources will be added with synthesized records.",
    )
    p.add_argument(
        "--ipeds-year", type=int, default=2022,
        help="IPEDS vintage year for institution + enrollment data. "
             "Defaults to 2022.",
    )
    p.add_argument("--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    api_key = args.api_key or os.environ.get("CENSUS_API_KEY")
    gaz_year = args.gazetteer_year or args.year

    extra_zips: list[str] | None = None
    if args.extra_zips:
        import pandas as pd
        extra_df = pd.read_csv(args.extra_zips, dtype=str)
        zip_col = extra_df.columns[0]
        extra_zips = extra_df[zip_col].astype(str).str.zfill(5).tolist()
        logger.info("Loaded %d extra ZIPs from %s", len(extra_zips), args.extra_zips)

    logger.info("Step 1/10 — Fetching GeoNames postal coverage")
    geonames = fetch_geonames()
    logger.info("  GeoNames: %d ZIPs", len(geonames))

    logger.info("Step 2/10 — Fetching Census ACS %s", args.year)
    acs = fetch_acs(year=args.year, api_key=api_key)
    logger.info("  ACS: %d rows", len(acs))

    logger.info("Step 3/10 — Fetching Census Gazetteer %s", gaz_year)
    gaz = fetch_gazetteer(year=gaz_year)
    logger.info("  Gazetteer: %d rows", len(gaz))

    logger.info("Step 4/10 — Fetching Census ZCTA-County relationship")
    zcta_county = fetch_zcta_county()
    logger.info("  ZCTA-County: %d rows", len(zcta_county))

    logger.info("Step 5/10 — Fetching OMB delineation")
    county_cbsa = fetch_omb_county_cbsa(args.omb_url)
    logger.info("  County-CBSA: %d rows", len(county_cbsa))

    logger.info("Step 6/10 — Fetching IPEDS institution + enrollment %s", args.ipeds_year)
    ipeds = fetch_ipeds(year=args.ipeds_year)
    logger.info("  IPEDS: %d ZIPs with at least one institution", len(ipeds))

    logger.info("Step 7/10 — Merging sources")
    merged = merge_sources(
        geonames=geonames,
        acs=acs,
        gazetteer=gaz,
        zcta_county=zcta_county,
        county_cbsa=county_cbsa,
        ipeds=ipeds,
        data_year=args.year,
        build_version=args.build_version,
        extra_zips=extra_zips,
    )
    logger.info("  Merged: %d rows", len(merged))

    logger.info("Step 8/10 — Deriving ZIP types")
    merged["zip_type"] = derive_zip_types(merged)
    type_counts = merged["zip_type"].value_counts().to_dict()
    logger.info("  ZIP types: %s", type_counts)

    logger.info("Step 9/10 — Engineering features")
    merged = add_engineered_features(merged)
    merged = reorder_to_schema(merged)

    logger.info("Step 10/10 — Validating")
    try:
        validate(merged, expected_year=args.year)
    except ValidationError as exc:
        logger.error("Validation failed:\n%s", exc)
        return 2

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_parquet(out_path, index=False)
    logger.info(
        "Wrote %d records to %s (%.1f MB)",
        len(merged),
        out_path,
        out_path.stat().st_size / (1024 * 1024),
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
