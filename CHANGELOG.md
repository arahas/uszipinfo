# Changelog

All notable changes to `uszipinfo` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — 2026-05-11

Initial release.

### Added

- 54-column ZIP-code metadata schema covering geographic identity, metro
  context, demographics, economic indicators, education, housing,
  race/ethnicity, USPS classification, and engineered ML features
- Coverage of 41,994 ZIPs across all 50 states + DC + 5 US territories +
  military APO/FPO/DPO addresses
- Bundled Parquet artifact (~7 MB) with ACS 2022 5-Year Estimates
- Public Python API: `load`, `lookup`, `lookup_many`, `filter_zips`,
  `nearest_zips`, `distance_mi`, `haversine_mi`
- `ZipInfo` typed dataclass for single-record returns
- Build pipeline pulling from Census ACS, Census Gazetteer, Census ZCTA
  relationship files, OMB CBSA delineations, and GeoNames postal data
- 56 unit tests covering API correctness, schema validation, and
  coverage of non-residential ZIPs
- Heuristic `zip_type` derivation (Standard / PO_Box / Unique / Military)
  using public signals (USPS authoritative classifications are not
  redistributable)
- Engineered features: `urbanicity_tier`, `climate_zone`,
  `is_college_town`, `is_resort_area`
