# uszipinfo

**ML-ready ZIP-code-level metadata for the United States.**

A single, fast, typed Python package providing demographic, geographic, and
metro-context features for every US ZIP code — including PO Boxes, military
APO/FPO/DPO ZIPs, and US territories. Designed for machine learning
pipelines and data analysis where you need rich features per ZIP without
re-implementing the Census API plumbing.

```python
import uszipinfo

info = uszipinfo.lookup("98004")
print(info.population)               # 39161
print(info.urbanicity_tier)          # 'urban'
print(info.msa_name)                 # 'Seattle-Tacoma-Bellevue, WA'
print(info.median_household_income)  # 157784
print(info.pct_bachelors_or_higher)  # 0.7488
```

---

## Why this exists

Existing PyPI ZIP packages each have gaps:

| Package | Demographics | Recent data | ML features | PO Boxes | Military |
|---|---|---|---|---|---|
| `uszipcode` | Yes | Older ACS | Limited | Partial | No |
| `pgeocode` | No | Geographic only | No | No | No |
| `pyzipcode` | No | Basic only | No | No | No |
| `zipcodes` | No | Basic only | No | No | No |
| **`uszipinfo`** | **Yes** | **Annual** | **Yes** | **Yes** | **Yes** |

`uszipinfo` combines recent Census ACS demographics, HUD-style ZIP
crosswalks, Census Gazetteer geography, GeoNames postal coverage, and
engineered ML features into a single package with a clean, typed
Python API.

---

## Coverage

The bundled data covers **41,994 ZIPs** spanning all 50 states, DC, 5
US territories, and military APO/FPO/DPO addresses.

| ZIP type | Count | Description |
|---|---|---|
| `Standard` | 32,164 | Residential ZIPs with full demographics |
| `PO_Box` | 7,669 | PO Box-only ZIPs (city/state/lat/lon, null demographics) |
| `Unique` | 1,377 | Institutional ZIPs (universities, large companies) |
| `Military` | 784 | APO/FPO/DPO with state ∈ {AA, AE, AP} |

For Standard ZIPs, all 54 fields are populated (≥95% coverage on
demographic columns). For non-residential ZIPs (PO Box, Unique, Military),
demographics are deliberately null — they have no residential population
to measure — but `zip_type`, `state`, `primary_city`, and
geographic fields are populated.

---

## Installation

```bash
pip install uszipinfo
```

The bundled Parquet data file (~7 MB) ships with the package — no API key,
no separate download, no internet connection required at runtime.

Optional dependencies:

```bash
pip install uszipinfo[build]   # for rebuilding the dataset from sources
pip install uszipinfo[dev]     # pytest, ruff, mypy for development
```

---

## Quick start

```python
import uszipinfo

# Single ZIP lookup, returns a typed ZipInfo dataclass
info = uszipinfo.lookup("98004")
print(info.population)

# Bulk lookup, returns a DataFrame
df = uszipinfo.lookup_many(["98004", "98005", "98006"])

# Filter by criteria
urban_wa = uszipinfo.filter_zips(state="WA", urbanicity_tier="urban")
high_income = uszipinfo.filter_zips(min_median_household_income=100000)
nyc_metro = uszipinfo.filter_zips(msa_code="35620")

# Geographic queries
nearby = uszipinfo.nearest_zips("98004", n=10, max_distance_mi=20)
distance = uszipinfo.distance_mi("98004", "10001")  # great-circle miles

# Load the full DataFrame
df = uszipinfo.load()
```

---

## API reference

### `uszipinfo.load(year=None) -> pd.DataFrame`

Return the full ZIP metadata as a pandas DataFrame with all 54 columns.

Pass `year=` to load a specific ACS vintage (only relevant if multiple
years are bundled; defaults to latest).

### `uszipinfo.lookup(zip_code, year=None) -> ZipInfo`

Return a typed `ZipInfo` dataclass for a single ZIP.

- Accepts ZIP codes as 4- or 5-digit strings: `"02139"`, `"2139"`, `2139`
- Accepts ZIP+4 format: `"98004-1234"` (suffix is dropped)
- Raises `KeyError` if the ZIP is not in the dataset
- Raises `ValueError` for malformed input

### `uszipinfo.lookup_many(zip_codes, year=None) -> pd.DataFrame`

Bulk lookup. Returns a DataFrame in the order of the input. ZIPs not
present in the dataset are silently dropped from the output.

### `uszipinfo.filter_zips(year=None, **criteria) -> pd.DataFrame`

Filter the dataset by criteria. Supports three forms:

- **Equality**: `state="WA"`, `is_metro=True`, `urbanicity_tier="urban"`
- **Membership**: `state=["WA", "OR"]`
- **Range**: `min_population=1000`, `max_median_household_income=50000`

Range filters use the prefix `min_` (≥) or `max_` (≤) on any numeric column.

### `uszipinfo.nearest_zips(zip_code, n=10, max_distance_mi=None) -> pd.DataFrame`

Return the `n` nearest ZIPs to `zip_code`, sorted by great-circle distance.
Optionally filter to within `max_distance_mi`. Excludes the source ZIP.

### `uszipinfo.distance_mi(zip_a, zip_b) -> float`

Return great-circle distance in miles between two ZIPs.

Raises `KeyError` if either ZIP is unknown, or `ValueError` if either ZIP
lacks coordinates (some PO Box ZIPs may have no lat/lon).

### `uszipinfo.haversine_mi(lat1, lon1, lat2, lon2) -> float`

Direct great-circle distance from raw coordinates (degrees).

### Module-level constants

```python
uszipinfo.__version__   # package version, e.g., "1.0.0"
uszipinfo.DATA_YEAR     # ACS vintage of the bundled data
uszipinfo.COLUMNS       # list of all 54 column names
uszipinfo.ENUMS         # allowed values for enum-like columns
```

---

## Schema

54 columns across 10 categories. All percentage fields are in 0–1 range
(not 0–100). `Optional` fields can be null when source data is unavailable.

### Geographic identity

| Field | Type | Description |
|---|---|---|
| `zip` | str(5) | 5-digit ZIP, zero-padded. Primary key. |
| `state` | str(2) | 2-letter USPS state code (or AA/AE/AP for military) |
| `state_name` | str | Full state name |
| `county` | str? | Dominant county name (when ZIP spans multiple) |
| `county_fips` | str(5)? | County FIPS code (state + county) |
| `primary_city` | str? | Most-associated city name |
| `lat` | float? | Interior point latitude |
| `lon` | float? | Interior point longitude |
| `timezone` | str? | IANA timezone (e.g., `America/Los_Angeles`) |
| `land_area_sq_mi` | float? | Land area in square miles |
| `water_area_sq_mi` | float? | Water area in square miles |

### Metro / region

| Field | Type | Description |
|---|---|---|
| `cbsa_code` | str? | Core-Based Statistical Area code (5-digit) |
| `cbsa_name` | str? | CBSA name (e.g., `Seattle-Tacoma-Bellevue, WA`) |
| `cbsa_type` | enum? | `Metro` / `Micro` / null |
| `msa_code` | str? | Same as cbsa_code if Metro, else null |
| `msa_name` | str? | Same as cbsa_name if Metro, else null |
| `csa_code` | str? | Combined Statistical Area code (parent of CBSA) |
| `csa_name` | str? | CSA name |
| `is_metro` | bool | True iff cbsa_type == `Metro` |
| `census_region` | enum? | `Northeast` / `Midwest` / `South` / `West` / `Territories` |
| `census_division` | enum? | One of 11 divisions (9 standard + 2 territory) |

### Population

| Field | Type | Description |
|---|---|---|
| `population` | int? | Total population |
| `population_density` | float? | Population per square mile of land |
| `households` | int? | Total households |
| `median_age` | float? | Median age in years |
| `pct_under_18` | float? | Percent of population under 18 |
| `pct_65_plus` | float? | Percent 65 or older |

### Economic

| Field | Type | Description |
|---|---|---|
| `median_household_income` | int? | USD |
| `pct_below_poverty` | float? | Percent below federal poverty line |
| `pct_employed` | float? | Labor force participation rate |
| `mean_travel_time_to_work_minutes` | float? | Average commute time |
| `pct_no_vehicles` | float? | Percent of households with no vehicles |

### Education

| Field | Type | Description |
|---|---|---|
| `pct_bachelors_or_higher` | float? | Percent of adults 25+ with bachelor's or higher |

### Housing

| Field | Type | Description |
|---|---|---|
| `total_housing_units` | int? | Total housing units |
| `pct_owner_occupied` | float? | Percent of occupied units owner-occupied |
| `pct_vacant` | float? | Percent of housing units vacant |
| `pct_single_family` | float? | Percent that are 1-unit structures |
| `pct_multi_family` | float? | Percent that are 5+ unit structures |
| `median_home_value` | int? | USD |
| `vacancy_for_seasonal_use` | float? | Percent vacant for seasonal use |

### Race / ethnicity

All percentages in 0–1 range, sourced from Census ACS B03002 table.

| Field | Type | Description |
|---|---|---|
| `pct_white` | float? | Non-Hispanic white |
| `pct_black` | float? | Black or African American |
| `pct_hispanic` | float? | Hispanic or Latino (any race) |
| `pct_asian` | float? | Asian |
| `pct_native_american` | float? | American Indian / Alaska Native |
| `pct_pacific_islander` | float? | Native Hawaiian / Pacific Islander |

### USPS classification

| Field | Type | Description |
|---|---|---|
| `zip_type` | enum | `Standard` / `PO_Box` / `Unique` / `Military` (heuristic) |

The official USPS classification is not redistributable. `zip_type` is
inferred from population, area, and prefix conventions. Accuracy is high
for residential ZIPs and military ZIPs but may misclassify some edge
cases (e.g., very small Unique ZIPs as PO_Box).

### Engineered features

| Field | Type | Description |
|---|---|---|
| `urbanicity_tier` | enum? | `rural` (<100/sq mi) / `suburban` (100–1000) / `urban` (1000–10000) / `dense_urban` (>10000) |
| `climate_zone` | enum? | `tropical` / `subtropical` / `temperate` / `continental` / `cold` (latitude-based) |
| `is_college_town` | bool | Heuristic: high education + moderate density + non-trivial population |
| `is_resort_area` | bool | Heuristic: high seasonal-housing-vacancy ratio |

### Build metadata

| Field | Type | Description |
|---|---|---|
| `data_year` | int | ACS vintage year |
| `build_date` | date | Date the artifact was built |
| `build_version` | str | Package version that built this artifact |

---

## Examples

### Basic lookup

```python
import uszipinfo

info = uszipinfo.lookup("90210")
print(f"{info.primary_city}, {info.state}")
# Beverly Hills, CA

print(f"Population: {info.population:,}")
# Population: 19,180

print(f"Median income: ${info.median_household_income:,}")
# Median income: $172,285

print(f"In MSA: {info.msa_name}")
# In MSA: Los Angeles-Long Beach-Anaheim, CA
```

### Filter by demographic criteria

```python
# All college-town ZIPs in Massachusetts
ma_college = uszipinfo.filter_zips(
    state="MA",
    is_college_town=True,
)
print(ma_college[["zip", "primary_city", "population"]])

# High-income suburban ZIPs nationwide
wealthy_suburbs = uszipinfo.filter_zips(
    urbanicity_tier="suburban",
    min_median_household_income=150000,
)
```

### Bulk feature engineering for an ML model

```python
import pandas as pd
import uszipinfo

# You have a DataFrame with a 'zip' column from your modeling pipeline
my_data = pd.DataFrame({"zip": ["98004", "98005", "98006", "10001"]})

# Enrich with ZIP metadata in one line
features = my_data.merge(uszipinfo.load(), on="zip", how="left")

# Use as model features:
# population, population_density, median_household_income,
# pct_bachelors_or_higher, pct_multi_family, urbanicity_tier, etc.
```

### Geographic queries

```python
# Find the 10 nearest ZIPs to Bellevue
nearby = uszipinfo.nearest_zips("98004", n=10)
print(nearby[["zip", "primary_city", "distance_mi"]])

# Distance between two ZIPs
miles = uszipinfo.distance_mi("98004", "10001")
print(f"Bellevue to Manhattan: {miles:.0f} miles")
# Bellevue to Manhattan: 2395 miles

# Nearby high-density ZIPs only
nyc_dense = uszipinfo.filter_zips(
    state="NY",
    urbanicity_tier="dense_urban",
)
```

### Identifying non-standard ZIPs

```python
# Check if a ZIP is a PO Box
info = uszipinfo.lookup("00501")  # IRS administrative ZIP
print(info.zip_type)
# 'PO_Box'

# Find all military ZIPs in the dataset
military = uszipinfo.filter_zips(zip_type="Military")
print(f"Military ZIPs: {len(military)}")

# Check that demographics are appropriately null for non-residential ZIPs
po_box = uszipinfo.lookup("10101")  # Manhattan PO Box
print(po_box.population)             # None
print(po_box.primary_city)           # 'New York'
print(po_box.zip_type)               # 'PO_Box'
```

---

## Data sources

All sources are public-domain or permissively licensed:

| Source | Provides | License | Refresh |
|---|---|---|---|
| **US Census ACS 5-Year Estimates** | Demographics, housing, economic indicators | Public domain | Annual (December) |
| **US Census Gazetteer** | Lat/lon, land/water area for ZCTAs | Public domain | Annual |
| **US Census ZCTA-County Relationship** | ZIP-to-county mapping | Public domain | Decennial |
| **OMB CBSA Delineations** | County-to-CBSA, MSA classification, CSA hierarchy | Public domain | Annual |
| **GeoNames Postal Codes** | Full ZIP coverage including PO Box / Military / Territory ZIPs, primary city, lat/lon | CC BY 4.0 | Continuous |

GeoNames attribution: data ©  GeoNames (https://www.geonames.org), used
under CC BY 4.0.

USPS authoritative ZIP type classifications are NOT redistributable. The
`zip_type` field is inferred from public signals; see `DATA_LICENSE` for
details.

---

## Building from source

The build pipeline is checked into the repo for transparency. Anyone can
regenerate the bundled Parquet from primary sources.

```bash
# Get a free Census API key (recommended; avoids rate limiting):
# https://api.census.gov/data/key_signup.html
export CENSUS_API_KEY=your_key_here

# Run the build (downloads ~50 MB of source data, takes 1–2 minutes)
python -m pipeline.run \
    --year 2022 \
    --out src/uszipinfo/_data/zip_metadata_2022.parquet

# To guarantee coverage of a specific ZIP set
# (e.g., from a downstream system like AMD), pass --extra-zips:
python -m pipeline.run \
    --year 2022 \
    --extra-zips ./my_required_zips.csv \
    --out src/uszipinfo/_data/zip_metadata_2022.parquet
```

The `--extra-zips` flag accepts a CSV with a single `zip` column. Any
ZIPs not covered by other sources will be added with synthesized records
(military prefix detection or skeleton fallback). This guarantees
`uszipinfo.lookup(z)` succeeds for every ZIP in your downstream system.

The build pipeline runs the following steps:

1. Fetch GeoNames (master ZIP list, primary city, lat/lon)
2. Fetch Census ACS (demographics)
3. Fetch Census Gazetteer (authoritative geography)
4. Fetch Census ZCTA-County (county FIPS)
5. Fetch OMB CBSA delineation (metro context)
6. Merge sources in priority order
7. Derive ZIP types heuristically
8. Engineer features (urbanicity, climate, college-town, resort)
9. Validate (schema, value ranges, coverage thresholds)

If validation fails, the build refuses to write the artifact and prints
all detected problems.

---

## Versioning

`uszipinfo` follows semver:

- **Major** (1.0.0 → 2.0.0): schema-breaking changes (field rename, type
  change, removal)
- **Minor** (1.0.0 → 1.1.0): new ACS vintage, new fields added (additive),
  new helper functions
- **Patch** (1.0.0 → 1.0.1): bug fixes, doc updates, no data or schema change

The data vintage is independent of the package version and accessible via
`uszipinfo.DATA_YEAR`.

---

## Performance

The bundled Parquet is loaded once on first call and cached in memory.

| Operation | Cold | Warm |
|---|---|---|
| First import + `lookup()` | ~150 ms | — |
| `lookup()` after first call | ~1 ms | <1 ms |
| `lookup_many(1000)` | ~10 ms | ~5 ms |
| `load()` returning full DataFrame | ~50 ms | ~10 ms |
| `filter_zips(...)` | ~20 ms | ~10 ms |
| `nearest_zips()` | ~30 ms | ~30 ms |

Memory footprint: ~20 MB for the in-memory DataFrame.

---

## Testing

```bash
pip install uszipinfo[dev]
pytest tests/
```

The test suite includes:
- API correctness (lookup, filter, geo)
- Schema validation
- Coverage tests for known PO Box, Military, and Territory ZIPs
- Sanity checks against well-known ZIPs (90210, 10001, etc.)

---

## Contributing

Issues and pull requests welcome. Areas where contributions are
particularly valuable:

- **Field additions**: vehicle ownership detail, school district mapping,
  congressional district, etc.
- **International expansion**: a `zipinfo` umbrella package covering
  postal codes for other countries
- **Vintage backfill**: building artifacts for older ACS years for
  historical analysis
- **Heuristic refinements**: improvements to `is_college_town`,
  `is_resort_area`, climate banding, etc.

---

## License

- **Code**: MIT
- **Data**: Public domain (US government work) + GeoNames CC BY 4.0
  (attribution required)

See `LICENSE` and `DATA_LICENSE` for full text.

---

## FAQ

### Why aren't there ~42,000 USPS ZIPs in your data when USPS says there are ~42,000 ZIPs?

There are. We have 41,994 ZIPs covering all USPS-deliverable ZIPs that
appear in any of our sources. USPS allocates ZIPs continuously; our
annual rebuild may lag a few months behind brand-new ZIP allocations.

### Why are some demographic fields null?

Three reasons:
1. **PO Box / Unique / Military ZIPs** have no residential population, so
   Census doesn't tabulate demographics for them. The `zip_type` field
   tells you which kind.
2. **Newly-allocated ZIPs** may not yet have ACS data. They show up with
   `Standard` zip_type but null demographics until the next ACS release.
3. **Very small ZCTAs** sometimes have null Census fields due to privacy
   suppression. This affects <1% of Standard ZIPs.

### Why does `urbanicity_tier` say `urban` for my suburban ZIP?

Tiers are based on population density:
- rural: <100 / sq mi
- suburban: 100–1000 / sq mi
- urban: 1000–10000 / sq mi
- dense_urban: >10000 / sq mi

These bands are coarse on purpose. ML models often want a categorical
density signal; the boundaries are tuned to align with patterns in
delivery, retail, and other practical use cases. If you need finer
control, use the raw `population_density` field directly.

### How accurate is `is_college_town` / `is_resort_area`?

These are heuristic flags with documented rules:
- **`is_college_town`**: `pct_bachelors_or_higher > 0.40`,
  `population_density between 500 and 5000`, `population > 5000`
- **`is_resort_area`**: `vacancy_for_seasonal_use > 0.15`

They catch most well-known examples but will have false positives and
false negatives. If you need authoritative classifications, validate
against your own source.

### How is `zip_type` derived?

Heuristic, in order:
1. **Military** if state ∈ {AA, AE, AP} OR ZIP prefix is in known military
   ranges (090–099, 340, 962–966)
2. **PO_Box** if no ZCTA data + zero population + zero land area
3. **Unique** if non-zero population < 100 + measurable land area
4. **Standard** otherwise

This is approximate. If you need authoritative USPS classification,
purchase the USPS Address Information System or licensed equivalent.

### Can I use this for non-US postal codes?

Not yet — v1 is US-only (including all 50 states + DC + 5 territories +
military). International support is a planned v2+ feature. For
international postal data, see `pgeocode` or GeoNames directly.

### How often is this updated?

Annually after the December ACS release. Patch releases for bug fixes
ship as needed.

---

## Acknowledgments

Data sources:
- US Census Bureau (ACS, Gazetteer, ZCTA-County relationship files)
- Office of Management and Budget (CBSA delineations)
- GeoNames postal data (https://www.geonames.org)

This package is not affiliated with the US Census Bureau, USPS, OMB, or
GeoNames.
