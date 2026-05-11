# uszipinfo — v1 Requirements

> **What:** A `pip install`-able Python package providing ML-ready ZIP-code-level metadata for the United States.
> **Audience:** Data scientists, researchers, and ML engineers who want clean ZIP demographics, geography, and metro context without re-implementing the Census API plumbing.
> **License:** MIT (code), public-domain (data, all sources are US government).
> **Scope:** US ZIPs only in v1. International expansion is v2+.

---

## 1. Motivation

Existing PyPI packages for ZIP code data have gaps:

- `uszipcode` — has demographics but uses dated ACS data and is slow to update
- `pgeocode` — multi-country geographic data, no demographics
- `pyzipcode` — basic geographic info only
- `zipcodes` — basic geographic info only

**The unmet need:** a single package that combines:
- Recent Census ACS demographics (refreshed annually)
- Geographic identity (state, county, MSA, lat/lon)
- Housing characteristics (single-family vs multi-family, ownership)
- Economic indicators (income, poverty, employment)
- Engineered ML features (urbanicity tier, climate zone, college-town flag)
- Clean, typed Python API with one-line lookups
- Bundled data so `pip install` just works

`uszipinfo` fills this niche.

---

## 2. Scope

### 2.1 In scope (v1)

- Static, demand-relevant ZIP attributes
- US ZIP codes (~41,000)
- Annual data refresh cadence
- Bundled Parquet data (no runtime download required)
- Pure-Python read-side API
- Build pipeline checked into the repo for transparency

### 2.2 Out of scope (v1)

- International ZIP codes / postal codes
- Time-varying data (real-time weather, current package volumes)
- Coverage of US territories (Puerto Rico, Guam, USVI) — may add in v1.x
- Sub-ZIP geography (block group, census tract)
- Authoritative USPS ZIP type (their data isn't redistributable; we use heuristic)
- Real-time API (data is bundled, not queried)

### 2.3 Future considerations (v1.x or v2)

- Multi-country support
- Sub-ZIP geographies
- Time-series enrichments (separate package or table)
- ZIP-to-school-district mapping
- Congressional district mapping

---

## 3. Data Sources

All sources are US government public-domain (no licensing restrictions on redistribution).

| Source | Provides | Refresh cadence |
|---|---|---|
| **Census ACS 5-Year Estimates** | Demographics, housing, economic indicators | Annual (December) |
| **Census Gazetteer Files** | Lat/lon, land/water area | Annual |
| **HUD ZIP-County Crosswalk** | ZIP-to-county mapping with population weighting | Quarterly |
| **HUD ZIP-CBSA Crosswalk** | ZIP-to-MSA/CBSA mapping | Quarterly |
| **OMB CBSA Delineation Files** | CBSA-to-MSA classification, CSA hierarchy | Annual |
| **Census Region/Division Definitions** | Region (Northeast/Midwest/South/West), Division | Static |

USPS authoritative ZIP type data is **not** redistributable; v1 uses heuristic derivation.

---

## 4. Schema (v1) — 54 fields

### 4.1 Geographic identity (11 fields)

| Field | Type | Description |
|---|---|---|
| `zip` | string(5) | 5-digit ZIP, zero-padded. Primary key. |
| `state` | string(2) | 2-letter state code |
| `state_name` | string | Full state name |
| `county` | string | Dominant county name (when ZIP spans multiple) |
| `county_fips` | string(5) | County FIPS code (state + county) |
| `primary_city` | string | Most-associated city name |
| `lat` | float | Interior point latitude |
| `lon` | float | Interior point longitude |
| `timezone` | string | IANA timezone (e.g., "America/Los_Angeles") |
| `land_area_sq_mi` | float | Land area in square miles |
| `water_area_sq_mi` | float | Water area in square miles |

### 4.2 Metro / region (10 fields)

| Field | Type | Description |
|---|---|---|
| `cbsa_code` | string | Core-Based Statistical Area code (5-digit) |
| `cbsa_name` | string | CBSA name (e.g., "Seattle-Tacoma-Bellevue, WA") |
| `cbsa_type` | enum | "Metro" / "Micro" / null |
| `msa_code` | string | Same as cbsa_code if Metro, else null |
| `msa_name` | string | Same as cbsa_name if Metro, else null |
| `csa_code` | string | Combined Statistical Area code (parent of CBSA), nullable |
| `csa_name` | string | CSA name, nullable |
| `is_metro` | bool | True iff cbsa_type == "Metro" |
| `census_region` | enum | "Northeast" / "Midwest" / "South" / "West" |
| `census_division` | enum | One of 9 Census divisions (e.g., "Pacific", "New England") |

### 4.3 Population (6 fields)

| Field | Type | Description |
|---|---|---|
| `population` | int | Total population |
| `population_density` | float | Population per square mile of land |
| `households` | int | Total households |
| `median_age` | float | Median age in years |
| `pct_under_18` | float | Percent of population under 18 (0–1 range) |
| `pct_65_plus` | float | Percent of population 65 or older (0–1 range) |

### 4.4 Economic (5 fields)

| Field | Type | Description |
|---|---|---|
| `median_household_income` | int | Median household income in USD |
| `pct_below_poverty` | float | Percent below federal poverty line |
| `pct_employed` | float | Labor force participation rate |
| `mean_travel_time_to_work_minutes` | float | Average commute time |
| `pct_no_vehicles` | float | Percent of households with no vehicles |

### 4.5 Education (1 field)

| Field | Type | Description |
|---|---|---|
| `pct_bachelors_or_higher` | float | Percent of adults 25+ with bachelor's degree or higher |

### 4.6 Housing (7 fields)

| Field | Type | Description |
|---|---|---|
| `total_housing_units` | int | Total housing units |
| `pct_owner_occupied` | float | Percent of occupied units that are owner-occupied |
| `pct_vacant` | float | Percent of housing units that are vacant |
| `pct_single_family` | float | Percent that are 1-unit structures (detached or attached) |
| `pct_multi_family` | float | Percent that are 5+ unit structures |
| `median_home_value` | int | Median home value in USD |
| `vacancy_for_seasonal_use` | float | Percent vacant for seasonal/recreational use |

### 4.7 Race / ethnicity (6 fields)

All percentages in 0–1 range, sourced from Census ACS.

| Field | Type | Description |
|---|---|---|
| `pct_white` | float | Non-Hispanic white population share |
| `pct_black` | float | Black or African American population share |
| `pct_hispanic` | float | Hispanic or Latino population share |
| `pct_asian` | float | Asian population share |
| `pct_native_american` | float | American Indian / Alaska Native population share |
| `pct_pacific_islander` | float | Native Hawaiian / Pacific Islander population share |

### 4.8 USPS classification (1 field)

| Field | Type | Description |
|---|---|---|
| `zip_type` | enum | Heuristic derivation: "Standard" / "PO_Box" / "Unique" / "Military". Source field documents this is heuristic, not USPS-authoritative. |

### 4.9 Engineered features (4 fields)

| Field | Type | Description | Logic |
|---|---|---|---|
| `urbanicity_tier` | enum | "rural" / "suburban" / "urban" / "dense_urban" | Binned `population_density`: <100, 100–1000, 1000–10000, >10000 |
| `climate_zone` | enum | "tropical" / "subtropical" / "temperate" / "continental" / "cold" | Binned latitude with ad-hoc western/eastern adjustments |
| `is_college_town` | bool | College-town indicator | `pct_bachelors_or_higher > 0.40` AND `population_density between 500 and 5000` AND `population > 5000` |
| `is_resort_area` | bool | Resort/seasonal area indicator | `vacancy_for_seasonal_use > 0.15` |

Heuristic flags are documented as approximate. Users who need authoritative classifications should verify.

### 4.10 Build metadata (3 fields)

| Field | Type | Description |
|---|---|---|
| `data_year` | int | ACS vintage year (e.g., 2022 for the 2018-2022 5-year estimate) |
| `build_date` | date | Date the artifact was built |
| `build_version` | string | Package version that built this artifact |

---

## 5. Public API

The consumer API is intentionally small. Three operations cover almost all use cases.

### 5.1 Module-level functions

```python
import uszipinfo

# Load the full dataset as a pandas DataFrame
df = uszipinfo.load()

# Single-zip lookup, returns a typed dataclass
info = uszipinfo.lookup("98004")
print(info.population, info.urbanicity_tier, info.msa_name)

# Bulk lookup, returns a DataFrame
df = uszipinfo.lookup_many(["98004", "98005", "98006"])

# Filter by criteria, returns a DataFrame
urban_wa = uszipinfo.filter_zips(state="WA", urbanicity_tier="urban")

# Geographic queries
nearby = uszipinfo.nearest_zips("98004", n=10, max_distance_mi=20)

# Distance between two ZIPs (great-circle, miles)
d = uszipinfo.distance_mi("98004", "10001")
```

### 5.2 The ZipInfo dataclass

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class ZipInfo:
    zip: str
    state: str
    state_name: str
    county: str
    # ... all 54 fields with appropriate types
    
    def to_dict(self) -> dict: ...
```

Frozen dataclass for immutability and hashability.

### 5.3 Version metadata

```python
uszipinfo.__version__        # package version, e.g., "1.0.0"
uszipinfo.DATA_YEAR          # ACS vintage, e.g., 2022
uszipinfo.BUILD_DATE         # date the bundled artifact was built
```

---

## 6. Package layout

```
uszipinfo/
├── README.md
├── LICENSE                              # MIT for code
├── DATA_LICENSE                         # public-domain attribution
├── pyproject.toml
├── src/uszipinfo/
│   ├── __init__.py                      # public API exports
│   ├── _data/
│   │   └── zip_metadata_2022.parquet    # bundled
│   ├── client.py                        # load/lookup/filter
│   ├── schema.py                        # ZipInfo dataclass
│   ├── geo.py                           # distance, nearest
│   └── _internal/
│       ├── data_loader.py
│       └── filters.py
├── pipeline/                            # build pipeline (separate from runtime)
│   ├── __init__.py
│   ├── fetch_acs.py
│   ├── fetch_gazetteer.py
│   ├── fetch_hud.py
│   ├── fetch_omb.py
│   ├── derive_zip_types.py
│   ├── engineer_features.py
│   ├── merger.py
│   ├── validator.py
│   └── build.py                         # orchestrator
├── tests/
│   ├── unit/
│   │   ├── test_lookup.py
│   │   ├── test_filter.py
│   │   ├── test_geo.py
│   │   └── test_schema.py
│   └── fixtures/
│       └── small_zip_metadata.parquet   # 100-zip sample for tests
└── docs/
    ├── index.md
    ├── api.md
    ├── data_sources.md
    └── examples/
```

---

## 7. Build pipeline

The build pipeline is run by the maintainer annually to regenerate the bundled Parquet.

### 7.1 Pipeline steps

1. **Fetch Census ACS** — pull all required variables for all ZCTAs
2. **Fetch Census Gazetteer** — lat/lon, land/water area
3. **Fetch HUD ZIP-County crosswalk** — for county assignment
4. **Fetch HUD ZIP-CBSA crosswalk** — for MSA assignment
5. **Fetch OMB CBSA delineation** — for Metro/Micro classification and CSA hierarchy
6. **Derive ZIP types heuristically** — Standard/PO_Box/Unique/Military
7. **Merge sources** — left-join on ZIP, handle PO Box ZIPs that lack ZCTAs
8. **Engineer features** — urbanicity tier, climate zone, college-town, resort
9. **Validate** — schema, value ranges, coverage, NaN rates
10. **Write Parquet** — bundled into `src/uszipinfo/_data/`

### 7.2 Validation checks

The build pipeline must fail loudly on:

- Duplicate ZIPs
- Invalid ZIP format (not 5 digits)
- ZIP count outside expected range (30k–45k)
- Missing states (must have ≥50)
- Total population <300M (sanity check)
- Lat/lon outside US bounds
- Excessive NaN rates (>20% on any field)

### 7.3 Operational

- Run by maintainer once per year (after ACS December release)
- Optionally automated via GitHub Actions `annual-build.yml`
- Build artifacts checked into the repo (so `pip install` includes them)
- Bumps minor version on each rebuild (e.g., 1.1.0 → 1.2.0)

---

## 8. Versioning

Standard semver:

| Bump | Trigger |
|---|---|
| Major (1.0.0 → 2.0.0) | Schema breaking changes (field rename, type change, removal) |
| Minor (1.0.0 → 1.1.0) | New ACS vintage, new fields added (additive), new helpers |
| Patch (1.0.0 → 1.0.1) | Bug fixes, doc updates, no data or schema change |

Data vintage is tracked separately in `DATA_YEAR`. A package release at `1.2.0` with `DATA_YEAR=2023` is a typical annual release.

---

## 9. Distribution

- Published to **PyPI** as `uszipinfo`
- Source on **GitHub** (public repo)
- Documentation via **ReadTheDocs** or **mkdocs** GitHub Pages
- License: **MIT** for code, **public-domain** for data

### 9.1 Data bundling

For v1, data is bundled inside the wheel. ~5–8 MB compressed Parquet × 41k rows × 54 fields.

PyPI's per-file size limit is 60 MB; we're well under. Total wheel size ~6–9 MB.

If data outgrows this in the future (e.g., adding territories, sub-ZIP geographies), switch to download-on-first-use with a local cache.

---

## 10. Testing

### 10.1 Unit tests

- Schema correctness (every field has expected type, value range)
- Lookup for known ZIPs returns expected values (e.g., 90210 has known demographics)
- Filter operators work correctly
- Distance calculation accuracy (compared against known reference distances)
- Nearest-zip query returns sensible neighbors
- Edge cases: nonexistent ZIP, malformed ZIP input

### 10.2 Integration tests

- Full DataFrame load works
- Bundled Parquet file is readable
- Public API matches documented interface

### 10.3 Test fixtures

A 100-zip sample of the bundled data is included in `tests/fixtures/`. Tests run against the sample for speed; integration tests verify the full bundled file loads.

---

## 11. Documentation

### 11.1 README

- One-paragraph pitch
- Quickstart (5 lines of code)
- Comparison to existing packages
- License notice

### 11.2 API reference

- Every public function with type hints, examples, expected behavior
- The `ZipInfo` dataclass with every field documented
- Version metadata

### 11.3 Data sources doc

- Per-field source attribution
- Data vintage
- Known limitations (heuristic ZIP type, ZCTA-vs-ZIP edge cases)
- Refresh cadence

### 11.4 Examples

- Notebook walkthroughs for common use cases
- ML feature engineering example
- Geographic analysis example

---

## 12. Quality bar

For v1 release:

- All 54 fields populated for ≥95% of ZIPs
- ZIP coverage ≥41,000 (the typical USPS ZIP count)
- Field-level NaN rates documented
- Test coverage ≥85% for the consumer API
- Documentation complete enough that a new user can get started in <5 minutes

---

## 13. Open items / decisions deferred

- **US territory coverage:** include Puerto Rico, Guam, USVI? Defer to v1.1 unless trivially included.
- **Annual refresh automation:** GitHub Actions vs manual? Decide once v1 is stable.
- **CDN for download-on-use:** not needed if bundling works; revisit if data grows.

---

## 14. Success criteria

v1 is successful if:

1. `pip install uszipinfo` followed by 3 lines of code returns demographic data for any US ZIP
2. The package works as a drop-in replacement for FTG's planned ZIP metadata table
3. At least one external project (outside FTG) adopts it within 6 months of release
4. PyPI downloads exceed 1,000/month within a year
