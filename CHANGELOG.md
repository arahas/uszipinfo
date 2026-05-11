# Changelog

All notable changes to `uszipinfo` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] — 2026-05-11

### Added

- **Academic / seasonality features**: 5 new columns capturing student-population seasonality, the largest annual demographic shift in many ZIPs.
  - `college_count` — number of degree-granting institutions in the ZIP (from IPEDS)
  - `college_enrollment_total` — total enrollment across institutions in the ZIP (from IPEDS)
  - `pct_college_enrolled` — fraction of residents currently enrolled in college (from ACS B14001)
  - `pct_dorm_population` — fraction of residents in group quarters / dormitories (from ACS B26001)
  - `pct_age_18_to_24` — college-age cohort (from ACS B01001)
- **Household composition**: 2 new columns
  - `avg_household_size` — average residents per household (from ACS B25010)
  - `pct_with_children` — fraction of households with children under 18 (from ACS B11005)
- **Income detail**: 3 new columns
  - `gini_index` — income inequality (from ACS B19083)
  - `pct_under_25k` — fraction of households earning <$25k
  - `pct_over_200k` — fraction of households earning ≥$200k
- **Metro context**: 2 new columns
  - `is_top_100_metro` — boolean for ZIPs in the 100 largest CBSAs by population
  - `dist_to_metro_center_mi` — distance to the largest-population ZIP in the same CBSA (proxy for inner suburb vs exurb)
- **New data source**: IPEDS (Department of Education's Integrated Postsecondary Education Data System) — public domain, ~6,000 institutions

### Changed

- **Redefined `is_college_town` heuristic**. Previous rule (`pct_bachelors_or_higher > 0.40 AND density 500–5000`) wrongly excluded dense urban college zones like MIT, Berkeley, UCLA. New rule uses direct academic signals:
  - `pct_dorm_population > 0.10`, OR
  - `pct_college_enrolled > 0.25`, OR
  - `college_enrollment_total >= 5000`
- Total schema grew from 54 to 66 columns.

## [1.0.1] — 2026-05-11

### Changed

- Raised minimum Python to 3.10. Python 3.9 reached end-of-life in
  October 2025 and modern pandas/pyarrow no longer support it; CI was
  failing on 3.9 because of dependency-resolution issues.
- Added explicit `from __future__ import annotations` to modules using
  PEP 585 generic syntax for clean import behavior across versions.

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
