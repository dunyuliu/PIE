"""PIE (Planetary Interior Evolution): Mercury interior model package.

`pie` is installed via `uv pip install -e .` (root `pyproject.toml`) and
imported as `pie`, not inserted onto `sys.path` as a bare directory.
Sibling modules import each other with package-relative imports
(`from .globalvar import ...`), not bare top-level names.

Entry points:
  - console script `pie` (`pie.cli:main`)
  - `python -m pie` (`pie/__main__.py`)

Both run `pie.main` (the legacy `main.py`) with `sys.argv` taken from the
real process argv, same argv contract as before:
`pie p CMR2 CMC light_element liquidus_eq [chi_Si_icb]`.
"""
