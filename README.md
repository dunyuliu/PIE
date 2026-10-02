# PIE: Planetary Interior Evolution 
PIE is a Python-based software to invert Mercury present-day interior structure by matching geodetic, geochemical, and thermodynamic constraints, and simulate evolutions of its interior structure (under development). <br/>

./src/ contains the Python source code to simulate the present-day Mercury inteior structure and its evolution.
Compared to its predecesor present-day model ([GitHub repo](https://github.com/gregorsteinbruegge/MercuryInterior.git)) used in [Steinbruegge et al. (2020)](https://doi.org/10.1029/2020GL089895), two light elements in the core - S and Si - are implemented, based on late thermodynamic liquidus constraints, and iron snow model can be produced. 

Si %wt is currently assumed to be a constant throughout the core, while S %wt are adjusted according to liqudius properties, variable over the core radius. 

# Quickstart guide

**Required environment**: Python 3.12 with the exact pins in
`requirements.txt` (PROJECT_RULES.md rule 3b/3c) -- this is the one
supported environment, not a suggestion; anything else (a different Python,
unpinned/"latest" packages) is unsupported and untested here.

One-command setup with [`uv`](https://docs.astral.sh/uv/) (absolute path
shown because `uv` is not on default `PATH` on most hosts):
```
~/.local/bin/uv venv --python 3.12 .venv
~/.local/bin/uv pip install --python .venv/bin/python3.12 -r requirements.txt
```

Fallback (no `uv`): any Python 3.12 interpreter, `pip install -r
requirements.txt`. On a PEP 668 "externally managed" system Python you may
need a venv first (`python3.12 -m venv .venv && .venv/bin/pip install -r
requirements.txt`) -- see `testsys/conftest.py`'s module docstring for why a
bare `pip install --user` fallback is handled explicitly in the test harness.

All commands below run from `src/` (outputs are written to `./results/`,
relative to the current directory when the script runs):
```
cd src
mkdir -p results
```

## Monte Carlo simulation on CMR2:
```
python monteCarlo.run.py
```
will generate a suite of Mercury present-day interior models fitting a set of CMR2 and CMC that are randomly generated from assigned mean CMR2 and its STD.

## General run with specified CMR2 and CMC:
```
python scheduler.py CMR2 CMC
```
where CMR2 and CMC, for Margot et al. constraints, are 0.346 and 0.424, respectively. The scheduler.py will loop over cases (S, Si, S+Si), liquidus equation (Steinbruegge, Edmund), and in particular for the case with S+Si, Si%wt from 0% to 15% in 1% increment. 

# Large ensemble Monte Carlo simulation

`src/robust_runner.py` runs any list of present-day jobs on knox (local)
or TACC Lonestar6 from one manifest file (PATHWAY_FORWARD.md item 22).
One job = one `main.py p CMR2 CMC light_element liquidus_eq [chi_Si_icb]`
call.

```
# 1. manifest: write it by hand (CSV columns CMR2,CMC,light_element,
#    liquidus_eq,chi_Si_icb[,seed]; chi_Si_icb only for S+Si), or generate
#    the seeded Monte Carlo ensemble (same draw as monteCarlo.run.py,
#    same compositions as scheduler.py: S+Si x 16 chi_Si_icb, S, Si):
python3 src/robust_runner.py make-mc-manifest mc.csv --n 1024 --seed-base 20260930

# 2a. knox / any shared box: PIE_WORKERS-capped pool, nice 10, 1 BLAS thread/job
python3 src/robust_runner.py run mc.csv

# 2b. Lonestar6: writes src/commands_launcher (pending jobs only), then the
#     existing slurm script runs it under LAUNCHER
python3 src/robust_runner.py run mc.csv --backend tacc
cd src && sbatch TACC.LS6.parallel.run.slurm
```

- **Resume**: re-run the same command. A job counts as done only when its
  sentinel `results/<model dir>/.runner_done_<chi>.json` exists, written
  after `main.py` exits 0 and its csv reads back. A killed job's partial
  csv does not count (`main.py` writes the csv header before the sweep).
  `--force` re-runs finished jobs.
- **Status**: `src/results/runner_status.jsonl` (`--status-log`), one
  `start` and one `end` record per attempt. A finished job's status is an
  `ErrorCode` name (README "Outputs and error codes"): `CONVERGED` if every
  radius converged, else the most frequent failure code, with per-code row
  counts. A job that never finished is `PROCESS_CRASHED` or
  `INCOMPLETE_OUTPUT`. Exit code 0 only if every job attempted finished.
- **Provenance** (every record and every sentinel): git SHA and whether
  `src/` was dirty, `requirements.txt` pins and the versions actually
  installed, host, interpreter, run id, start/end time.
- **Workers**: `PIE_WORKERS`, default `max(4, floor(free cores/2))`, the
  same formula as `testsys/conftest.py` (PROJECT_RULES.md rule 15); check
  `uptime`/`who` first and set it explicitly on a loaded box.
- The ricb grid is not a manifest field: it is fixed in `src/main.py`.

### Legacy recipes

`src/TACC.LS6.create.parallel.launcher.py` writes a `commands_launcher`
of 1024 `monteCarlo.run.py <seed>` lines, for LAUNCHER on LS6 or, on knox:

```
cd src
python TACC.LS6.create.parallel.launcher.py   # writes commands_launcher
nice -n 10 xargs -P "${PIE_WORKERS:-4}" -I{} sh -c '{}' < commands_launcher
```

Its resume check is weaker than the runner's: `monteCarlo.run.py` skips a
draw if the draw's `S+Si` `pMetaData_*.csv` exists, but `main.py` creates
that csv (header row) before the sweep starts, so a draw killed mid-run is
skipped as if finished. Prefer `robust_runner.py`.

## Testing

```
.venv/bin/python3.12 testsys/run.py            # fast tiers: unit + contract + integration, ~3-5 min
.venv/bin/python3.12 testsys/run.py all        # all tiers incl. e2e + published_wide (needs ~/shared_dataset), ~14 min
```

See [`testsys/README.md`](testsys/README.md) for tier definitions and the
published-paper parity check against Zenodo-archived output.

## Solver

Each present-day model is a 5-unknown shooting problem (P and T at the
centre, core radius, mantle density, light-element fraction at the
inner-core boundary) solved by Newton's method with a finite-difference
Jacobian (`src/shootp.py`, `mynewtonSys`). Since v1.3.0 the Newton step is
bounded (PATHWAY_FORWARD.md item 17; design and measurements in
`docs/notes/solver_v1.3.0.md`):

- direction `dx = J^-1 f` as before; step length `alpha` starts at 1 and is
  halved while the trial iterate is outside the admissible box -- non-finite
  residual, `rcmb <= ricb`, `chi_li_icb` above the eutectic at the trial's
  own P_icb (S, S+Si) or above the liquidus table's Si maximum (Si) -- or while `|f|` grows by more than 100x. Below
  `alpha = 1e-3` the radius fails with the code of the last rejection.
- an Armijo decrease test is deliberately NOT used: on 1841 converged
  v1.2.0 radii, 1.4% of accepted steps increase `|f|` (up to 18.6x) and
  those paths converge anyway. Wherever v1.2.0 converged, `alpha = 1` is
  accepted on every iteration and the result is bit-identical.
- a singular Jacobian is `cond(J) > 1e12` (or `LinAlgError`), not an exact
  `det(J) == 0` compare; a chi column clamped at the eutectic gives
  `cond = inf` and is caught the same way.
- the ellipticity grid (`getk2`) at the 10-m first radius (`nrs = 0`) treats
  the core as fully fluid from the centre (`g(0) = 0`, no inner-core term)
  instead of wrapping an index to the CMB end and reading uninitialised
  memory (bug B5); `xi` is exactly 0 there as before, so 10-m outputs are
  unchanged.

Sweep policy (v1.3.0): a failure at one radius is recorded and the sweep
continues to the next radius, warm-starting from the last *converged*
solution; if the warm start fails and differs from the generic initial
guess, one cold start from that guess is tried. Only code 6 (Si above the
liquidus cap, radius-independent, by design) ends a composition, with a
single row. Before v1.3.0 the first failure ended the composition.

## Performance options

`PIE_FAST_QUAD=1` (env var, default **off**) opts `coreEos.py`'s
`eosAndersonGrueneisen.Gibbs` into a vectorised 21-point Gauss-Kronrod
(GK21) evaluation of its `scipy.integrate.quad` call, falling back to the
real `scipy.integrate.quad` per call whenever QUADPACK's own single-panel
accept test (replicated from `dqagse.f`) would reject it. Measured ~4x
faster per call on this box's pinned environment (see
`docs/notes/perf_v1.3.3.md` for the full timing table).

Default (`PIE_FAST_QUAD` unset or `0`) is the unconditional
`scipy.integrate.quad` call -- **identical to pre-v1.3.3 behaviour on
every environment**. `PIE_FAST_QUAD=1` is bit-identical to default on the
pinned environment (`numpy==1.21.5`, `scipy==1.8.0`) but is NOT
bit-identical on every environment: `eosAndersonGrueneisen.volume`'s
`CubicSpline` does not return exactly the same values for a vectorised
array call vs one-scalar-call-per-point on newer numpy/scipy (floating-
point non-associativity in `CubicSpline`'s own vectorized-vs-scalar code
path), so the max relative difference is bounded at **<=1e-14** rather
than exactly 0 off the pinned environment
(`testsys/unit/test_perf_v1_3_3_gk21_quad.py`). Set `PIE_FAST_QUAD=1` only
if you have verified that bound is acceptable for your use (it is far
below the solver's own convergence tolerance, `ftol=xtol=1e-6`).

## Outputs and error codes

Each run writes, per light-element setting, `pMetaData_<chi_Si>.csv` and
`solverLog_<chi_Si>.jsonl` (Newton iterations incl. step lengths and
rejected trials, failure context), plus one `Data*_R<ricb>.h5` profile file
per **converged** radius.

Since v1.3.0 the csv has **one row per attempted radius** (40 rows for
`rs = arange(10 m, 2e6, 50e3)`; a composition that fails everywhere has 40
failed rows, not an empty file). A failed radius has `ricb`, `chi_Si_icb`,
`error_code`, `start`, `newton_iters`, `resid_norm` set and **every physical
column NaN**; no `.h5` is written for it. Consumers must keep converged
rows only, e.g. `df[df.error_code == 0]` (the repo's own plotting scripts
do). Three columns were appended in v1.3.0 (positions of the original 19
are unchanged): `start` (`warm`/`cold`: which start converged, or was last
tried), `newton_iters`, `resid_norm` (final `||f||`). The `error_code`
column:

| code | meaning |
|---|---|
| 0 | converged |
| 1 | Newton hit maxit |
| 2 | singular Jacobian (`cond(J) > 1e12`, e.g. chi clamped at the eutectic) |
| 3 | non-finite shoot (NaN in the fluid-core integration, singular sparse solve, non-finite k2 grid) |
| 4 | light-element fraction outside its admissible range (also after line-search backtracking) |
| 5 | inner-core radius reached the core-mantle boundary |
| 6 | Si above the liquidus table's maximum (by design; checked once before the sweep) |

History: before v1.2.0 `error_code` was always 0 and a failure silently
truncated the csv; in v1.2.0 failures were recorded only in the jsonl log
and still ended the sweep; since v1.3.0 they are rows in the csv and the
sweep continues.

## Citation

If you use PIE, please cite:

Dunnigan, A. H., Liu, D., Steinbrügge, G. B., Rivoldini, A., Dumberry, M., Cao, H., & Soderlund, K. M. (2026). Interior models of Mercury and conditions for iron snow formation in a Fe-S-Si core. *Journal of Geophysical Research: Planets*, 131(4), e2025JE009368. https://doi.org/10.1029/2025JE009368

Code and data archived on Zenodo for that paper (PIE v1.0.5):
- Code: https://doi.org/10.5281/zenodo.16929504
- Simulation dataset and plotting scripts: https://doi.org/10.5281/zenodo.16459292

Machine-readable metadata is in [`CITATION.cff`](CITATION.cff) (GitHub's "Cite this repository" button).

## Copyright and distribution

All the material in this repository is open-source and distributed under the GNU General Public License v3.0. For detials, see ``LICENSE``.

Contributors: Liu, Dunnigan, Steinbruegge, Rivoldini.

If you have any questions and comments, feel free to reach out to Dunyu Liu (dliu@ig.utexas.edu). 
