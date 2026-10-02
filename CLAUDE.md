# CLAUDE.md

Guidance for Claude Code (or any agent) working in this repository. See
`PROJECT_RULES.md` for the binding rules; this file is the working reference.

## Project overview

PIE (Planetary Interior Evolution) inverts Mercury's present-day interior
structure (Fe core with S and/or Si light elements) against CMR2/CMC
constraints, and is developing a companion interior-evolution model. All code
is serial Python under `src/`. No compiled component, no MPI, no conda.

## Environment

Environment setup (interpreter, Python version, dependencies) is in flux as of
this date. See README.md's Quickstart/install section for the current 
authoritative guidance (target interpreter, dependency pins, venv setup if needed).
See also `PROJECT_RULES.md` rule 3 (exact-pin enforcement) and `requirements.txt`
(runtime deps, single source of truth).

## Running

```bash
mkdir results                       # required before any run; nothing creates it
python scheduler.py CMR2 CMC        # single case, e.g. 0.346 0.424 (Margot fit)
python monteCarlo.run.py            # Monte Carlo ensemble around a mean CMR2/STD
```

Batches and large ensembles (knox or TACC Lonestar6), resumable, one
manifest -- `src/robust_runner.py` (item 22; README "Large ensemble Monte
Carlo simulation"):

```bash
python3 src/robust_runner.py make-mc-manifest mc.csv --n 1024 --seed-base 20260930
python3 src/robust_runner.py run mc.csv                    # knox, PIE_WORKERS-capped
python3 src/robust_runner.py run mc.csv --backend tacc     # LS6: then cd src && sbatch TACC.LS6.parallel.run.slurm
```

Legacy: `src/TACC.LS6.create.parallel.launcher.py` + `monteCarlo.run.py`
(its resume check treats a killed draw as finished -- README).

## Layout

- `src/` — all source, flat (no package/subdir structure yet).
  `main.py` is the entry point; `driverp.py`/`shootp.py`
  drive the present-day model, `drivere.py`/`shoote.py` the evolution model
  (under development); `libCore.py` + `coreEos.py` hold the physics;
  `globalvar.py`/`planet_input.py` hold shared state, imported with
  `from x import *` throughout — a known refactor target (`PATHWAY_FORWARD.md`
  item 9), not yet started, and not safe to touch until `testsys/` is green
  (`PROJECT_RULES.md` rule 3a).
- `src/test.py` and `src/main_abbey_plot.py` were dead/scratch files pending
  triage (`PATHWAY_FORWARD.md` item 9); confirmed unreferenced anywhere in
  `src/`/`testsys/` and broken when run on current `src/` (undefined names
  from stale `globalvar.py`/`planet_input.py` APIs), so both were deleted.
  `src/TEST_visualization_evolution.py` was triaged the same way but kept —
  `src/drivere.py` imports it, so it is not dead, just part of the
  evolution branch parked under item 11; do not extend or delete it.
- `historical_versions/` — frozen zip/tar snapshots of prior versions.
  Read-only (`PROJECT_RULES.md` rule 7).
- `CHANGELOG.md` — per-release change list; git tags are the version source of truth
  (`PROJECT_RULES.md` rule 1a). `update_log` is the frozen pre-v1.0.5 dev log;
  it gets no new entries.

## Version state (as of 2026-10-02)

- v1.0.5 (tag on `683a51d`): the code archived with Dunnigan et al. 2026
  (Zenodo 10.5281/zenodo.16929504). v1.1.0: first tested baseline (testsys,
  CI, rules, citation) with `src/` byte-identical to v1.0.5.
- v1.0.2/v1.0.3 were zipped externally but never tagged; don't tag them.
- v1.1.1 (2026-09-29): scipy interp2d port to RectBivariateSpline.
- v1.2.0 (2026-09-30): error codes, clean exits, solver log, dependency manifest.
- v1.3.0 (2026-09-30): bounded line-search Newton, getk2 nrs=0 fix, 
  continue-after-failure sweeps, failure rows in csv (PATHWAY_FORWARD.md item 17).
- v1.3.1 (2026-10-01): pytest-xdist parallelism, no physics change (patch).
- v1.3.2 (2026-10-01): linear-solve performance (spsolve over inv), no algorithm change (patch).
- v1.3.3 (2026-10-01): opt-in vectorised GK21 quadrature (PIE_FAST_QUAD, default off, patch).
- v1.4.0 (2026-10-02): robust-runner feature, src/ import narrowing (items 9, 22), 
  test-coverage/doc hardening (items 23, 18, 25).

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
