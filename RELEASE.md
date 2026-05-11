# Release process

Step-by-step for publishing a new version of `uszipinfo`. The first
time through these steps, you're doing one-time setup; subsequent
releases skip Section 1.

---

## 1. One-time setup (first release only)

### 1a. Create the GitHub repository

```bash
# On github.com:
# - Sign in as arahas
# - Click "New repository"
# - Name: uszipinfo
# - Description: "ML-ready ZIP-code-level metadata for the United States"
# - Visibility: Public
# - Do NOT initialize with README/LICENSE (we already have them)
# - Click "Create repository"
```

### 1b. Push the code to GitHub

```bash
# From the repo root:
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/arahas/uszipinfo.git
git push -u origin main
```

### 1c. Reserve the name on PyPI (first release only)

The cleanest way is to publish v1.0.0 directly via PyPI's trusted
publishing feature, which doesn't require you to handle tokens at all.

**Set up PyPI Trusted Publishing**:

1. Go to https://pypi.org/manage/account/publishing/
2. Sign in (create an account if needed; never reuse the password)
3. Click **Add a new pending publisher**
4. Fill in:
   - **PyPI Project Name**: `uszipinfo`
   - **Owner**: `arahas`
   - **Repository name**: `uszipinfo`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`
5. Click **Add**

This tells PyPI: "When GitHub repo `arahas/uszipinfo` runs the
`publish.yml` workflow in environment `pypi`, trust it to upload to the
`uszipinfo` package."

No tokens are stored anywhere. PyPI verifies via OpenID Connect (OIDC)
that the publishing request came from your GitHub Actions workflow.

### 1d. Configure the GitHub repo's `pypi` environment

1. Go to https://github.com/arahas/uszipinfo/settings/environments
2. Click **New environment**, name it `pypi`
3. (Optional) Add a protection rule requiring manual approval for the
   environment — gives you a chance to abort a bad release before it
   uploads

---

## 2. Per-release workflow

### 2a. Confirm the package is in releasable state

```bash
# From the repo root:

# All tests pass?
PYTHONPATH=src python -m pytest tests/ -v

# Build the artifact locally to verify
pip install build
python -m build
ls dist/
# Should show:
#   dist/uszipinfo-1.0.0.tar.gz
#   dist/uszipinfo-1.0.0-py3-none-any.whl

# Verify the wheel includes the bundled Parquet
unzip -l dist/uszipinfo-1.0.0-py3-none-any.whl | grep parquet
# Should show: uszipinfo/_data/zip_metadata_2022.parquet
```

### 2b. Smoke-test the wheel in a clean environment

```bash
# In a temp directory
python -m venv /tmp/test_uszipinfo
source /tmp/test_uszipinfo/bin/activate
pip install ./dist/uszipinfo-1.0.0-py3-none-any.whl

python -c "
import uszipinfo
print(f'Version: {uszipinfo.__version__}')
print(f'Data year: {uszipinfo.DATA_YEAR}')
info = uszipinfo.lookup('98004')
print(f'Bellevue: pop={info.population:,}, income=\${info.median_household_income:,}')
"

deactivate
rm -rf /tmp/test_uszipinfo
```

### 2c. Update CHANGELOG and version

1. Edit `CHANGELOG.md`: move `[Unreleased]` content under a new
   `[X.Y.Z] - YYYY-MM-DD` section
2. Edit `pyproject.toml`: bump `version = "X.Y.Z"`
3. Edit `src/uszipinfo/__init__.py`: bump `__version__ = "X.Y.Z"`

For the very first release, version 1.0.0 is already set.

### 2d. Commit, tag, and push

```bash
git add CHANGELOG.md pyproject.toml src/uszipinfo/__init__.py
git commit -m "Release v1.0.0"
git tag -a v1.0.0 -m "v1.0.0 — initial release"
git push origin main
git push origin v1.0.0
```

### 2e. Create the GitHub Release

1. Go to https://github.com/arahas/uszipinfo/releases
2. Click **Draft a new release**
3. Choose tag: **v1.0.0**
4. Release title: `v1.0.0 — Initial release`
5. Description: paste the CHANGELOG entry for this version
6. Click **Publish release**

When you click **Publish release**, GitHub Actions will run the
`publish.yml` workflow, which:
1. Builds the wheel and sdist
2. Verifies the version matches the tag
3. Verifies the wheel contains the bundled Parquet
4. Uploads to PyPI via OIDC trusted publishing

You can watch progress at
https://github.com/arahas/uszipinfo/actions

### 2f. Verify the release

```bash
# Wait ~1 minute after the workflow succeeds for PyPI to index
pip install uszipinfo
python -c "import uszipinfo; print(uszipinfo.__version__)"
```

You should also see your package at https://pypi.org/project/uszipinfo/

---

## 3. Subsequent releases

After the first release, the workflow simplifies to:

1. Make changes
2. Update `CHANGELOG.md` and version in `pyproject.toml` + `__init__.py`
3. Commit, tag, push
4. Draft a GitHub Release from the tag
5. Publish — Actions does the rest

---

## 4. If something goes wrong

### Bad release published

PyPI does not allow re-uploading the same version. You must yank the
broken release and publish a new patch version:

```bash
# Yank the broken version (keeps it visible but prevents new installs)
pip install twine
twine yank uszipinfo --version 1.0.0 --reason "Critical bug: ..."

# Then publish 1.0.1 with the fix following the normal process
```

### GitHub Actions workflow fails

Check the Actions tab on the repo. Common causes:
- **Version mismatch**: tag doesn't match `pyproject.toml` version
- **Trusted publishing not configured**: revisit Section 1c
- **Bundled Parquet missing**: the wheel build didn't include data;
  check `pyproject.toml` `[tool.hatch.build.targets.wheel.force-include]`
- **Tests failing on Actions but passing locally**: may be a
  Python-version-specific issue; check the matrix

---

## Notes on credentials

This project uses **PyPI Trusted Publishing** rather than API tokens.

Benefits:
- No tokens to manage, rotate, or accidentally leak
- Cryptographically tied to the specific GitHub repo and workflow
- Cannot be misused outside the Actions environment

If you ever need an actual PyPI token (e.g., to publish from your local
machine for testing), get one at https://pypi.org/manage/account/token/
and pass it via the `TWINE_PASSWORD` environment variable. Never put
tokens in code, commits, or `.pypirc` files in the repo.
