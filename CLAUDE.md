# CLAUDE.md

Guidance for Claude Code (or any agent) working in this repository. See
`PROJECT_RULES.md` for the binding rules; this file is the working reference.

## Project overview

PIE (Planetary Interior Evolution) inverts Mercury's present-day interior
structure (Fe core with S and/or Si light elements) against CMR2/CMC
constraints, and is developing a companion interior-evolution model. All code
is serial Python under `src/`. No compiled component, no MPI, no conda.

## Environment

- Use **`/usr/bin/python3`**, not whatever `python3` resolves to first on
  `PATH` — the default on this box is a venv missing `h5py`
  (`read_plot_datah5.py` needs it). Verify: `/usr/bin/python3 -c "import
  h5py"`.
- No conda for this project.
- Dependencies (no manifest exists yet — `PATHWAY_FORWARD.md` item 8):
  `numpy`, `scipy`, `pandas`, `matplotlib`, `h5py`.

## Running

```bash
mkdir results                       # required before any run; nothing creates it
python scheduler.py CMR2 CMC        # single case, e.g. 0.346 0.424 (Margot fit)
python monteCarlo.run.py            # Monte Carlo ensemble around a mean CMR2/STD
```

Large ensembles on TACC Lonestar6:

```bash
python src/TACC.LS6.create.parallel.launcher.py   # README says TACC.create.parallel.launcher.py — wrong, see PROJECT_RULES.md rule 11
sbatch TACC.LS6.parallel.run.slurm
```

## Layout

- `src/` — all source, flat (no package/subdir structure yet).
  `main.py`/`main_abbey_plot.py` are entry points; `driverp.py`/`shootp.py`
  drive the present-day model, `drivere.py`/`shoote.py` the evolution model
  (under development); `libCore.py` + `coreEos.py` hold the physics;
  `globalvar.py`/`planet_input.py` hold shared state, imported with
  `from x import *` throughout — a known refactor target (`PATHWAY_FORWARD.md`
  item 9), not yet started, and not safe to touch until `testsys/` is green
  (`PROJECT_RULES.md` rule 3a).
- `src/test.py`, `src/TEST_visualization_evolution.py`,
  `src/main_abbey_plot.py` are dead/scratch files pending triage
  (`PATHWAY_FORWARD.md` item 9) — do not extend them; do not delete them
  either without checking they're truly unused first.
- `historical_versions/` — frozen zip/tar snapshots of prior versions.
  Read-only (`PROJECT_RULES.md` rule 7).
- `testsys/`, `.github/` — owned by a separate, concurrent effort building the
  tiered test suite (unit/contract/integration/e2e) and CI. Do not create or
  edit anything here from this working context.
- `CHANGELOG.md` — per-release change list; git tags are the version source of truth
  (`PROJECT_RULES.md` rule 1a). `update_log` is the frozen pre-v1.0.5 dev log;
  it gets no new entries.

## Version state (as of 2026-09-29)

- v1.0.5 (tag on `683a51d`): the code archived with Dunnigan et al. 2026
  (Zenodo 10.5281/zenodo.16929504). v1.1.0: first tested baseline (testsys,
  CI, rules, citation) with `src/` byte-identical to v1.0.5.
- v1.0.2/v1.0.3 were zipped externally but never tagged; don't tag them.
- v1.1.1: scipy interp2d port. v1.2.0: error codes, clean exits, solver log. v1.3.0: bounded line-search Newton, getk2 nrs=0 fix, continue-after-failure sweeps, failure rows in the csv (item 17; `docs/notes/solver_v1.3.0.md`).

## Known correctness caveats

- `src/coreEos.py`'s `get_mass_core` was missing a factor of `pi` until fixed
  at `bb37b0a` (v1.0.5) — a reminder that nothing in this codebase has been
  tested against an independent check until `testsys/` lands.
- The S+Si (two-light-element) case now has a regression anchor: the Zenodo
  dataset (10.5281/zenodo.16459292) for Dunnigan et al. 2026 JGR Planets
  (doi:10.1029/2025JE009368), produced by this same v1.0.5 code (published
  code 10.5281/zenodo.16929504 == current HEAD `src/`). It still has **no
  independent truth oracle** — the old predecessor codes (v1.0.3/v1.0.4) are
  Fe-S/Fe-Si only, so S+Si correctness beyond regression parity still rests
  on self-consistency (limit checks as Si%wt or S%wt → 0). State that
  distinction — "regression-anchored" vs "independently verified" — wherever
  S+Si results are reported.
- Regression anchors (old PIE versions, and the Zenodo/Dunnigan dataset) are
  same-code-family comparisons, not independent ground truth — see
  `PROJECT_RULES.md` rule 5.

## Where to look for open work

`PATHWAY_FORWARD.md` — the living board. Check it before assuming any claim
in `README.md` or `CHANGELOG.md` still holds.
