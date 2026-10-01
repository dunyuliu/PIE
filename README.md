# PIE: Planetary Interior Evolution 
PIE is a Python-based software to invert Mercury present-day interior structure by matching geodetic, geochemical, and thermodynamic constraints, and simulate evolutions of its interior structure (under development). <br/>

./src/ contains the Python source code to simulate the present-day Mercury inteior structure and its evolution.
Compared to its predecesor present-day model ([GitHub repo](https://github.com/gregorsteinbruegge/MercuryInterior.git)) used in [Steinbruegge et al. (2020)](https://doi.org/10.1029/2020GL089895), two light elements in the core - S and Si - are implemented, based on late thermodynamic liquidus constraints, and iron snow model can be produced. 

Si %wt is currently assumed to be a constant throughout the core, while S %wt are adjusted according to liqudius properties, variable over the core radius. 

# Quickstart guide

Install exact-pinned dependencies once (see `requirements.txt`; target
interpreter per `CLAUDE.md`/`PROJECT_RULES.md` rule 3 -- `/usr/bin/python3`
on most hosts, or a pinned project venv where that interpreter is broken,
e.g. `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`):
```
pip install -r requirements.txt
```

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
To produce a large ensemble of interior models that samples a normal distribution from a CMR2 with its STD, supercomputuers such as Lonestar6 at TACC provides LAUNCHER computing module to run serial jobs in parallel.

```
python TACC.LS6.create.parallel.launcher.py
# create a command_launcher file that contains X number of lines of commands.
# command_launcher will be used by LAUNCHER module on TACC LS6.
# X is specified in variable total_CPU in the file.

sbatch TACC.LS6.parallel.run.slurm
# submit a parallel job requesting 8 computing nodes with a total of 1024 CPU cores,
#   in this example, that uses LAUNCHER to run all the 1024 models in parallel.

# The example run here takes less than 2 hours.
```

### On a shared machine without Slurm (e.g. knox)

Same `commands_launcher` file (each line already carries an explicit seed
and the pinned interpreter), run directly with `xargs` instead of LAUNCHER
-- capped and niced so other users' jobs on the same box keep headroom
(see `PROJECT_RULES.md`'s shared-machine rule):

```
cd src
python TACC.LS6.create.parallel.launcher.py   # writes commands_launcher
nice -n 10 xargs -P "${PIE_WORKERS:-4}" -I{} sh -c '{}' < commands_launcher
```

Resumable: each line (`monteCarlo.run.py <seed>`) skips its own CMR2/CMC
draw if `results/CMR2_*_CMC_*_S+Si_Edmund/pMetaData_*.csv` for that draw
already exists, so re-running the same `commands_launcher` after a
partial/interrupted ensemble only does the missing work. `PIE_WORKERS`
defaults to the same cap `testsys/run.py` uses (`max(4, floor(free
cores/2))`); set it explicitly on a loaded box (check `uptime`/`who`
first).

## Testing

```
/usr/bin/python3 testsys/run.py            # fast tiers: unit + contract + integration, ~3-5 min
/usr/bin/python3 testsys/run.py all        # all tiers incl. e2e + published_wide (needs ~/shared_dataset), ~11 min
```

See [`testsys/README.md`](testsys/README.md) for tier definitions, the
published-paper parity check against Zenodo-archived output, and a
known-environment note (`/usr/bin/python3` needs `PYTHONNOUSERSITE=1`
for subprocess runs -- see that file).

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
