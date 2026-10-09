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
python scripts/run/scheduler.py CMR2 CMC        # loops S/Si/S+Si x liquidus x Si%wt
python scripts/run/monteCarlo.run.py            # Monte Carlo ensemble around a mean CMR2/STD
```

`pie p ...` (the console entry point, `pyproject.toml`'s `[project.scripts]`)
is equivalent to `python -m pie p ...`.

Batches and large ensembles (knox or TACC Lonestar6), resumable, one
manifest -- `pie/robust_runner.py` (item 22; kept inside the `pie` package,
not moved to `scripts/run/`, because three `tests/` files import it as
`from pie import robust_runner` and it self-locates its results dir to the
package dir):

```bash
python3 pie/robust_runner.py make-mc-manifest mc.csv --n 1024 --seed-base 20260930
python3 pie/robust_runner.py run mc.csv                    # knox, PIE_WORKERS-capped
python3 pie/robust_runner.py run mc.csv --backend tacc     # LS6: then sbatch scripts/run/TACC.LS6.parallel.run.slurm
```

### Legacy recipe

`scripts/run/TACC.LS6.create.parallel.launcher.py` (run with the working
directory set to `scripts/run/`, where `monteCarlo.run.py` lives and where its
`./results/` output lands) writes a `commands_launcher` of 1024
`monteCarlo.run.py <seed>` lines, for LAUNCHER on LS6 or a plain `xargs`
pool on knox:

```bash
cd scripts/run
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

The admissible-box test (`box_fun`) runs on every line-search trial, but the
`converged_now` fast path returns the final iterate without re-checking it,
and `x0` itself is never box-checked either (PATHWAY_FORWARD.md item 36).
`PIE_BOX_CHECK_FINAL=1` (env var; also `true`/`yes`/`on`; default unset
= off) adds both checks, raising the box's own error code if the converged
iterate or `x0` is outside it. Off is bit-identical to pre-item-36
behaviour. On is not: 1,502 of 474,075 converged rows (0.317%) in the
published v1.0.5 Zenodo dataset fail the box, all Si-only with `chi_li_icb`
above the 0.12 Si cap (audited, board item 36; none is in the paper's
S+Si figure population). So it stays opt-in.

## Performance options

`coreEos.py`'s `eosAndersonGrueneisen.Gibbs` uses, by default, a vectorised
21-point Gauss-Kronrod (GK21) evaluation of its `scipy.integrate.quad` call,
falling back to the real `scipy.integrate.quad` per call whenever
QUADPACK's own single-panel accept test (replicated from `dqagse.f`) would
reject it -- measured ~4x faster per call on the pinned environment (see
`docs/dev/notes/perf_v1.3.3.md` for the full timing table).

`PIE_FAST_QUAD=0` (env var) is the explicit escape hatch back to the
unconditional `scipy.integrate.quad` call -- identical to the pre-GK21
behaviour on every environment. `PIE_FAST_QUAD` unset, or set to any other
value (e.g. `1`), means GK21-on. On the environment it was measured on in v1.3.3
(`numpy==1.21.5`, `scipy==1.8.0`), GK21 is
bit-identical to `scipy.integrate.quad` (max diff 0.0, measured over 237057
real captured solver (p, T) calls,
`tests/unit/test_perf_v1_3_3_gk21_quad.py`). Off that environment
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
- `scripts/plot/` — `summaryPlot.py`, `visualization_present.py`,
  `read_plot_datah5.py`, `plotAll.py`/`plotAll.sh` (relocated from `src/` by
  board item 28, then from `util/` to `scripts/` by board item 39).
  `scripts/run/` — `scheduler.py`, `monteCarlo.run.py`,
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
- `CHANGELOG.md` — per-release change list; git tags are the version source of truth
  (`PROJECT_RULES.md` rule 1a). Pre-v1.0.5 development history lives in
  CHANGELOG.md's own pre-v1.0.5 entries (v1.0.4 and earlier) and the `v1.0.0`
  git tag; both `historical_versions/` (frozen zip/tar snapshots) and
  `update_log` (the pre-v1.0.5 dev log) were removed from the tree as
  redundant with git history (board item 39) -- still retrievable via the
  `v1.0.0` tag or earlier commits, not from the working tree.

## Version state

Git tags are the version source of truth, `CHANGELOG.md` the per-release
change list (`PROJECT_RULES.md` rule 1a). Fixed points worth knowing:
v1.0.5 (`683a51d`) is the code archived with Dunnigan et al. 2026 (Zenodo
10.5281/zenodo.16929504); v1.1.0 is the first tested baseline with `src/`
byte-identical to v1.0.5; v1.0.2/v1.0.3 were zipped externally but never
tagged, so don't tag them. Breaking path changes shipped as minor bumps
under the standing owner grant for v1.x (v1.6.0 `src/`->`pie/`, v1.7.0
root layout).

## Known correctness caveats

- `pie/coreEos.py`'s `get_mass_core` was missing a factor of `pi` until fixed
  at `bb37b0a` (v1.0.5, then `src/coreEos.py`) — a reminder that nothing in
  this codebase was tested against an independent check before the test
  suite landed (v1.1.0).
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
