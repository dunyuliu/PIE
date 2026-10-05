# Install

## Required environment

Python 3.12 with the exact pins in `requirements.txt`
(`PROJECT_RULES.md` rule 3b/3c). This is the **one supported environment**,
not a suggestion -- a different Python version, or unpinned/"latest"
packages, is unsupported and untested here. CI runs an additional
`fast-latest` canary with pins stripped, but that job is informational
only and never gates a merge or release.

## One-command setup with `uv`

```bash
~/.local/bin/uv venv --python 3.12 .venv
~/.local/bin/uv pip install --python .venv/bin/python3.12 -e .
```

(The absolute path to `uv` is shown because it is not on the default
`PATH` on most hosts.)

Setup is an editable install of the `pie` package, not a raw
`pip install -r requirements.txt` into a bare venv. `pyproject.toml`'s
pinned `[project.dependencies]` must agree with `requirements.txt`, which
remains the single source of truth; a contract test
(`testsys/contract/test_dependency_pins_match.py`) enforces that
agreement.

## Pre-commit hook (machine-local path hygiene)

Run once after cloning, to block machine-local path leaks before they
reach CI:

```bash
git config core.hooksPath .githooks
```

## Running the CLI

`pie` is an installed package -- run as a console script or via `-m`,
from any directory, not a flat `src/` tree you `cd` into:

```bash
mkdir -p results
pie p 0.346 0.424 S Edmund
# equivalently:
python -m pie p 0.346 0.424 S Edmund
```

Outputs are written to `./results/`, relative to the directory the
command runs from.

## Testing

```bash
.venv/bin/python3.12 testsys/run.py            # fast tiers: unit + contract + integration, ~3-5 min
.venv/bin/python3.12 testsys/run.py all        # all tiers incl. e2e + published_wide (needs ~/shared_dataset), ~14 min
```

See `testsys/README.md` in the repository for tier definitions and the
published-paper parity check against the Zenodo-archived output.
