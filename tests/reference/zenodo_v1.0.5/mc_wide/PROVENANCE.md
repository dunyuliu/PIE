# Provenance: wide Monte Carlo published-anchor slice

Source: Zenodo 10.5281/zenodo.16459292 ("Plotting and Analysis
Scripts.zip"'s companion full-dataset archive `work.tar`), extracted by
the user into the shared, read-only, cross-project cache
`~/shared_dataset/zenodo.16459292/extracted/PIE/{work.margot,work.genova}/`.
That tree's `src/` was diffed against this repo's `src/` (2026-09-28):
identical for every module that affects these results (globalvar.py,
planet_input.py, libCore.py, solver.py, coreEos.py, shootp.py,
driverp.py, main.py) -- only launcher/slurm scripts and `VERSION` (build
metadata) differ. So, as with `zenodo_v1.0.5/` proper, this is a
same-code REGRESSION ANCHOR, not an independent correctness oracle.

Each `work.<moi>/results/` holds 3072 directories: 1024 Monte-Carlo
(CMR2, CMC) draws x {S, Si, S+Si} light-element compositions, liquidus
`Edmund` ONLY (no `Steinbruegge` in this published dataset -- those
compositions have no published anchor at all, self-golden only; see
`tests/reference/self_v1.0.5/wide_sweep/`). Each directory holds ONLY
`pMetaData_*.csv` (scalar summary rows) -- no per-radius `.h5` profile
files in this dataset (unlike the smaller `For Supplemental Figures`
slice already in `zenodo_v1.0.5/`), so this fixture gates the 19
`presentday_columns` scalars only, not radial profiles.

## Selection (`select.py`'s picks, 4 per composition per MOI = 24 files)

For each of {margot, genova} x {S, Si, S+Si}:
- `low_cmr2_extreme` / `high_cmr2_extreme`: the smallest/largest CMR2
  drawn for that composition (many of these have ZERO converged rows --
  a real, common outcome at the tails of the MC distribution, not a
  bug; see `test_mc_wide_parity.py`, which asserts these cases
  CONTINUE to fail to converge, i.e. guards the failure mode itself).
- `centre_nominal`: the draw closest to the nominal (CMR2, CMC) for
  that MOI (Margot 0.346/0.426, Genova 0.333/0.443).
- `most_converged_rows`: the draw with the most converged
  inner-core-radius steps (widest radius range covered, most likely to
  include a snow-zone transition).

Committed size: 27 KB (well under the ~10 MB budget) -- this is the
CURATED slice; `manifest.json` records the exact source directory/CMR2/
CMC/row-count for each, `SHA256SUMS` the checksums.

## Regenerating / extending

`extract_zenodo_slice.py` (in `tests/reference/zenodo_v1.0.5/`) reads
from `~/shared_dataset/zenodo.16459292/` when present, falling back to
downloading the Zenodo URL otherwise -- see that script for the
`--mc-wide` mode that reproduces this directory's selection logic
(`low/high/centre/most_converged_rows` per composition x MOI).

## The wider (uncurated) published-wide check

`tests/e2e/test_published_wide_sweep.py` (marker `published_wide`)
samples a few hundred of the full 6144 (work.margot + work.genova)
directories DIRECTLY from `~/shared_dataset/...` (never copied) --
skipped with a clear reason when that path is absent (e.g. in CI, which
has no access to another user's home directory's shared cache).
