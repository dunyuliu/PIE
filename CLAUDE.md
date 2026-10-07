# CLAUDE.md

Guidance for Claude Code (or any agent) working in this repository. See
`PROJECT_RULES.md` for the binding rules; this file is the working reference.

## Project overview

PIE (Planetary Interior Evolution) inverts Mercury's present-day interior
structure (Fe core with S and/or Si light elements) against CMR2/CMC
constraints, and is developing a companion interior-evolution model. All code
is serial Python, packaged as the installable `pie` package (`pie/`, board
item 28e). No compiled component, no MPI, no conda.

## Environment

Target interpreter: Python 3.12, exact pins in `requirements.txt` (the single
source of truth; `pyproject.toml`'s `[project.dependencies]` must match it —
`PROJECT_RULES.md` rule 3b, enforced by
`tests/contract/test_dependency_pins_match.py`). Setup is
`uv pip install -e .` (editable install of the `pie` package) into a venv
built against that pin set — see README.md's Quickstart for the exact
commands. `PROJECT_RULES.md` rule 3c: the pinned manifest is the one
supported environment; an unpinned/"latest" install is a non-blocking CI
canary only.

## Running

```bash
mkdir results                       # required before any run; nothing creates it
python -m pie p CMR2 CMC light_element liquidus_eq [chi_Si_icb]  # single case, e.g. S Edmund 0.346 0.424 (Margot fit)
python util/run/scheduler.py CMR2 CMC        # loops S/Si/S+Si x liquidus x Si%wt
python util/run/monteCarlo.run.py            # Monte Carlo ensemble around a mean CMR2/STD
```

`pie p ...` (the console entry point, `pyproject.toml`'s `[project.scripts]`)
is equivalent to `python -m pie p ...`.

Batches and large ensembles (knox or TACC Lonestar6), resumable, one
manifest -- `pie/robust_runner.py` (item 22; kept inside the `pie` package,
not moved to `util/run/`, because three `tests/` files import it as
`from pie import robust_runner` and it self-locates its results dir to the
package dir):

```bash
python3 pie/robust_runner.py make-mc-manifest mc.csv --n 1024 --seed-base 20260930
python3 pie/robust_runner.py run mc.csv                    # knox, PIE_WORKERS-capped
python3 pie/robust_runner.py run mc.csv --backend tacc     # LS6: then sbatch util/run/TACC.LS6.parallel.run.slurm
```

### Legacy recipe

`util/run/TACC.LS6.create.parallel.launcher.py` (run with the working
directory set to `util/run/`, where `monteCarlo.run.py` lives and where its
`./results/` output lands) writes a `commands_launcher` of 1024
`monteCarlo.run.py <seed>` lines, for LAUNCHER on LS6 or a plain `xargs`
pool on knox:

```bash
cd util/run
python TACC.LS6.create.parallel.launcher.py   # writes commands_launcher
nice -n 10 xargs -P "${PIE_WORKERS:-4}" -I{} sh -c '{}' < commands_launcher
```

Its resume check is weaker than `robust_runner.py`'s: `monteCarlo.run.py`
skips a draw if the draw's `S+Si` `pMetaData_*.csv` exists, but `pie.main`
creates that csv (header row) before the sweep starts, so a draw killed
mid-run is skipped as if finished. Prefer `robust_runner.py`.

## Testing

```bash
.venv/bin/python3.12 tests/run.py            # fast tiers: unit + contract + integration, ~3-5 min
.venv/bin/python3.12 tests/run.py all        # all tiers incl. e2e + published_wide (needs ~/shared_dataset), ~14 min
```

See `tests/README.md` for tier definitions and the published-paper parity
check against Zenodo-archived output.

## Solver

Each present-day model is a 5-unknown shooting problem (P and T at the
centre, core radius, mantle density, light-element fraction at the
inner-core boundary) solved by Newton's method with a finite-difference
Jacobian (`pie/shootp.py`, `mynewtonSys`). The Newton step is bounded:

- direction `dx = J^-1 f` as before; step length `alpha` starts at 1 and is
  halved while the trial iterate is outside the admissible box -- non-finite
  residual, `rcmb <= ricb`, `chi_li_icb` above the eutectic at the trial's
  own P_icb (S, S+Si) or above the liquidus table's Si maximum (Si) -- or
  while `|f|` grows by more than 100x. Below `alpha = 1e-3` the radius fails
  with the code of the last rejection.
- an Armijo decrease test is deliberately NOT used: accepted steps can
  increase `|f|` (observed up to 18.6x) and those paths converge anyway.
- a singular Jacobian is `cond(J) > 1e12` (or `LinAlgError`), not an exact
  `det(J) == 0` compare; a chi column clamped at the eutectic gives
  `cond = inf` and is caught the same way.
- the ellipticity grid (`getk2`) at the 10-m first radius (`nrs = 0`) treats
  the core as fully fluid from the centre (`g(0) = 0`, no inner-core term)
  instead of wrapping an index to the CMB end and reading uninitialised
  memory; `xi` is exactly 0 there.

Sweep policy: a failure at one radius is recorded and the sweep continues to
the next radius, warm-starting from the last *converged* solution; if the
warm start fails and differs from the generic initial guess, one cold start
from that guess is tried. Only code 6 (Si above the liquidus cap,
radius-independent, by design) ends a composition, with a single row.

## Performance options

`coreEos.py`'s `eosAndersonGrueneisen.Gibbs` uses, by default, a vectorised
21-point Gauss-Kronrod (GK21) evaluation of its `scipy.integrate.quad` call,
falling back to the real `scipy.integrate.quad` per call whenever
QUADPACK's own single-panel accept test (replicated from `dqagse.f`) would
reject it -- measured ~4x faster per call on the pinned environment (see
`docs/notes/perf_v1.3.3.md` for the full timing table).

`PIE_FAST_QUAD=0` (env var) is the explicit escape hatch back to the
unconditional `scipy.integrate.quad` call -- identical to the pre-GK21
behaviour on every environment. `PIE_FAST_QUAD` unset, or set to any other
value (e.g. `1`), means GK21-on. On the pinned environment
(`numpy==1.21.5`, `scipy==1.8.0`, `tests/requirements.txt`), GK21 is
bit-identical to `scipy.integrate.quad` (max diff 0.0, measured over 237057
real captured solver (p, T) calls,
`tests/unit/test_perf_v1_3_3_gk21_quad.py`). Off the pinned environment
(e.g. CI's informational `fast-latest` canary, current numpy/scipy),
`eosAndersonGrueneisen.volume`'s `CubicSpline` does not return exactly the
same values for a vectorised array call vs one-scalar-call-per-point
(floating-point non-associativity in `CubicSpline`'s own
vectorized-vs-scalar code path), so the max relative difference is bounded
at <=1e-14 rather than exactly 0 there -- far below the solver's own
convergence tolerance (`ftol=xtol=1e-6`). Set `PIE_FAST_QUAD=0` if you need
byte-identical pre-GK21 behaviour on an environment you have not verified
against this bound.

## Outputs and error codes

Full column layout, file naming, and the generated `error_code` table now
live on the user-facing site (`docs/user/outputs.md`,
`docs/user/troubleshooting.md`, generated from `pie/globalvar.py`'s
`ErrorCode` enum and `ERROR_CODE_DESCRIPTIONS` by `docs/user/gen_params.py`)
-- read those rather than keeping a second copy here.

## Layout

- `pie/` — the installable Python package (renamed from flat `src/` by board
  item 28e; `uv pip install -e .`, `pyproject.toml` at root). `main.py` is the
  entry point (`pie/cli.py` + `pie/__main__.py` wrap it as `pie`/
  `python -m pie`); `driverp.py`/`shootp.py` drive the present-day model,
  `drivere.py`/`shoote.py` the evolution model (under development);
  `libCore.py` + `coreEos.py` hold the physics; `globalvar.py`/
  `planet_input.py` hold shared state. Sibling modules use package-relative
  imports (`from .globalvar import ...`); the former repo-wide
  `from x import *` star-imports were narrowed to explicit name lists module
  by module (`PATHWAY_FORWARD.md` item 9, closed for `main.py`/`shootp.py`/
  `solver.py`/`libCore.py`/`driverp.py`/`planet_input.py`/`summaryPlot.py`/
  `visualization_present.py`; `summaryPlot.py`'s two star-imports
  (`pie.drivere`, `pie.driverp`) were dropped outright rather than narrowed
  to a non-empty list -- its own code used no name from either module;
  `shoote.py`/`visualization_evolution.py` excluded, parked under item 11).
- `util/plot/` — `summaryPlot.py`, `visualization_present.py`,
  `read_plot_datah5.py`, `plotAll.py`/`plotAll.sh` (relocated from `src/` by
  board item 28). `util/run/` — `scheduler.py`, `monteCarlo.run.py`,
  `TACC.LS6.create.parallel.launcher.py` + its slurm script, `postp.slurm`
  (relocated the same way; `robust_runner.py` deliberately stayed in `pie/`,
  see "Running" above).
- `pie/test.py` and `pie/main_abbey_plot.py` (then `src/test.py`/
  `src/main_abbey_plot.py`) were dead/scratch files pending triage
  (`PATHWAY_FORWARD.md` item 9); confirmed unreferenced anywhere in
  `src/`/`tests/` and broken when run on current `src/` (undefined names
  from stale `globalvar.py`/`planet_input.py` APIs), so both were deleted
  before the `pie/` rename. `pie/TEST_visualization_evolution.py` was triaged
  the same way but kept — `pie/drivere.py` imports it, so it is not dead,
  just part of the evolution branch parked under item 11; do not extend or
  delete it.
- `historical_versions/` — frozen zip/tar snapshots of prior versions.
  Read-only (`PROJECT_RULES.md` rule 7).
- `CHANGELOG.md` — per-release change list; git tags are the version source of truth
  (`PROJECT_RULES.md` rule 1a). `update_log` is the frozen pre-v1.0.5 dev log;
  it gets no new entries.

## Version state (as of 2026-10-03)

- v1.0.5 (tag on `683a51d`): the code archived with Dunnigan et al. 2026
  (Zenodo 10.5281/zenodo.16929504). v1.1.0: first tested baseline (tests,
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
- v1.5.0 (2026-10-02): Python 3.10 -> 3.12 + current dependency pins (major dep bump), `uv`-managed venv the one supported environment.
- v1.5.1 (2026-10-03): `PIE_FAST_QUAD` (GK21 quadrature) defaults ON.
- v1.6.0 (2026-10-03, this release): `src/` renamed to the installable `pie/`
  package (item 28e, Breaking on setup/import-path/run-recipe axes but shipped
  as a minor bump under the standing owner grant for v1.x releases); `util/`
  split (`util/plot/`, `util/run/`, item 28) closed out; `summaryPlot.py`
  NameError/typo bugs and `robust_runner.py` lock-race/silent-fallback fixes
  (items 24, 26); `meltingDataFromFile` no-op `np.sort` skip (item 27 partial).
  Collapses what were drafted across PRs #52-#59 as three separate entries
  (v1.6.0/v1.6.1/v1.6.2) into this one tag, the only one actually cut — see
  CHANGELOG.md for the per-change breakdown (Breaking/Fixed/Performance).
- v1.6.1 (2026-10-04): patch, full release ceremony (owner-requested, not the
  lighter patch cadence). Board item 30 (`pie/shootp.py` non-finite ICB
  density now raises `SolverError` code 7 instead of an uncaught `ValueError`
  that killed the whole sweep; `pie/robust_runner.py::run_one_job` counts csv
  rows whenever the file exists, not only on `returncode == 0`) plus item 29a
  (stale-lock reclaim race fix, landed after v1.6.0 but not yet changelogged).
  No API/behaviour-breaking change, no numerical-output change.

## Known correctness caveats

- `pie/coreEos.py`'s `get_mass_core` was missing a factor of `pi` until fixed
  at `bb37b0a` (v1.0.5, then `src/coreEos.py`) — a reminder that nothing in
  this codebase has been tested against an independent check until `tests/`
  lands.
- The S+Si (two-light-element) case now has a regression anchor: the Zenodo
  dataset (10.5281/zenodo.16459292) for Dunnigan et al. 2026 JGR Planets
  (doi:10.1029/2025JE009368), produced by this same v1.0.5 code (published
  code 10.5281/zenodo.16929504 == v1.0.5's `src/`, byte-identical-modulo-
  import-rewrites to current HEAD `pie/`). It still has **no independent
  truth oracle** — the old predecessor codes (v1.0.3/v1.0.4) are Fe-S/Fe-Si
  only, so S+Si correctness beyond regression parity still rests on
  self-consistency (limit checks as Si%wt or S%wt → 0). State that
  distinction — "regression-anchored" vs "independently verified" — wherever
  S+Si results are reported.
- Regression anchors (old PIE versions, and the Zenodo/Dunnigan dataset) are
  same-code-family comparisons, not independent ground truth — see
  `PROJECT_RULES.md` rule 5.

## Where to look for open work

`PATHWAY_FORWARD.md` — the living board. Check it before assuming any claim
in `README.md` or `CHANGELOG.md` still holds.
