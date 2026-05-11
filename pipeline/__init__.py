"""Build pipeline for the bundled uszipinfo Parquet artifact.

This package is *not* part of the runtime API. It exists for transparency
and reproducibility — anyone can rebuild the dataset from primary sources.

Run with::

    python -m build.build --year 2022 --out src/uszipinfo/_data/zip_metadata_2022.parquet
"""
