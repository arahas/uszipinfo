# Contributing to uszipinfo

Thanks for your interest in contributing. This is a small, focused
package — contributions that align with the project's scope are very
welcome.

## Project scope

`uszipinfo` provides **static, demand-relevant ZIP metadata for the
United States**. In scope:

- US ZIP codes (50 states + DC + territories + military)
- Static demographic, geographic, and economic attributes
- Engineered features useful for ML pipelines
- Annual data refresh aligned with Census ACS releases

Out of scope (at least for v1):

- International postal codes
- Time-varying data (real-time weather, current package volumes, etc.)
- Sub-ZIP geographies (block group, census tract)
- Authoritative USPS data that requires a paid USPS license

## Development setup

```bash
git clone https://github.com/YOUR_USERNAME/uszipinfo.git
cd uszipinfo
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,build]"
```

Run the tests:

```bash
pytest tests/ -v
```

Run the linter:

```bash
ruff check src/ tests/
```

## Submitting changes

1. **Open an issue first** for non-trivial changes. Saves both of us time
   if the change isn't a fit for the project.
2. **Fork and branch.** Branch names like `feat/college-towns-refinement`
   or `fix/territory-state-mapping` are clear.
3. **Add tests** for new behavior. The test suite must pass.
4. **Update the CHANGELOG.md** under an `[Unreleased]` section.
5. **Open a PR.** Describe the motivation and the approach.

## Releases

Releases are tagged with `vX.Y.Z` git tags. The GitHub Actions workflow
auto-publishes to PyPI when a release is created from the tag.

To cut a release:

1. Update version in `pyproject.toml` and `src/uszipinfo/__init__.py`
2. Move the `[Unreleased]` section in `CHANGELOG.md` under the new version
3. Commit, tag (`git tag v1.1.0`), and push (`git push --tags`)
4. Create a GitHub Release pointing at the tag — this triggers publish

## Annual data refresh

The build pipeline runs annually after the December ACS release:

```bash
python -m pipeline.run \
    --year 2023 \
    --out src/uszipinfo/_data/zip_metadata_2023.parquet
```

Then bump the package minor version (e.g., 1.0.0 → 1.1.0) and cut a
new release.

## Code style

- Black-compatible formatting (use `ruff format` or `black`)
- Type hints on all public functions
- Docstrings on all public functions in NumPy or Google style
- No `print()` statements in library code; use `logging`

## License

By contributing, you agree your contributions will be licensed under MIT
(matching the rest of the project).
