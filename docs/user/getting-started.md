# Getting Started

## Requirements

PIE targets Python 3.12 exactly, with the exact dependency pins in
`requirements.txt` (`numpy`, `scipy`, `pandas`, `matplotlib`, `h5py`,
`tables`) -- this is the one supported environment, not a suggestion; a
different Python or unpinned/"latest" packages are untested here.

## Install

Clone the repository first:

```
git clone https://github.com/dunyu-liu/PIE.git
cd PIE
```

Install with [`uv`](https://docs.astral.sh/uv/) into a venv built against
the pinned dependencies -- an editable install of the `pie` package, not a
bare `pip install -r requirements.txt`. Absolute path shown because `uv`
is not on default `PATH` on most hosts:

```
~/.local/bin/uv venv --python 3.12 .venv
~/.local/bin/uv pip install --python .venv/bin/python3.12 -e .
```

`pie` is an installed package: it runs as the `pie` console script, or via
`python -m pie`, from anywhere -- it is not a flat directory you `cd` into.

Enable the repository's pre-commit hook once per clone (blocks
machine-local path leaks before they reach CI):

```
git config core.hooksPath .githooks
```

Outputs are written to `./results/`, relative to whatever directory the
command runs in:

```
mkdir -p results
```

## Running a first case

The quickest way to see PIE run end to end is a single present-day solve
at the Margot et al. CMR2/CMC fit, with sulfur as the only light element:

```
pie p 0.346 0.424 S Edmund
```

This solves the 5-unknown shooting problem (pressure and temperature at
the centre, core radius, mantle density, light-element fraction at the
inner-core boundary) by Newton's method at a sweep of trial inner-core
radii, and writes `pMetaData_0.00.csv`, `solverLog_0.00.jsonl`, and one
`Data*_R<ricb>.h5` profile per converged radius under
`results/CMR2_0.34600000000000003_CMC_0.42400000000000004_S_Edmund/`. See
[Running a Case](running-a-case.md) for the full set of entry points
(scheduler sweep, Monte Carlo ensembles, the resumable large-ensemble
runner) and [Output Files](outputs.md) for what each file contains.

## Check the install

```
~/.local/bin/uv pip install --python .venv/bin/python3.12 -r testsys/requirements.txt
.venv/bin/python3.12 testsys/run.py
```

This runs the fast tiers (unit, contract, integration -- the same gate CI
runs on every push and PR), ~3-5 minutes. See
[`testsys/README.md`](https://github.com/dunyu-liu/PIE/blob/main/testsys/README.md)
for tier definitions and runtimes, including the published-paper parity
check against Zenodo-archived output.
