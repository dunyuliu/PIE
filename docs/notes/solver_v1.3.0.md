# v1.3.0 solver: bounded line-search Newton, getk2 nrs=0 fix, continue-after-failure sweeps

Status: written incrementally during the v1.3.0 work (2026-09-30 / 10-01); every number states whether it is measured on this branch (fresh) or inherited from `docs/notes/failure_analysis_2026-09-28.md` + its audit. Board item: `PATHWAY_FORWARD.md` 17 (and 19, 12 partly).

## 1. What changed and why

Evidence base (inherited, audited): every published v1.0.5 sweep died at the first inner-core radius where the **undamped** Newton step (`x -= J^-1 f`) threw the light-element unknown `chi_li_icb` out of its admissible range -- past the eutectic (the `min(sol, chi_eut)` clamp in `libCore.getchi_li_grun` then zeroes the finite-difference Jacobian column -> exact `det(J)==0`), well below zero (S) or above the Si maximum (Si) (-> NaN in the fluid-core RK4 -> NaN density fit -> NaN matrix in `getpotvsr` -> SuperLU "Factor is exactly singular"), or past `rcmb` (-> `IndexError` in `getk2`). A separate real bug: at the 10-m first radius `getk2` has `nrs = round(400*ricb/rcmb) = 0` and its fluid loop indexed `k+nrs-1 = -1` at `k = 0`, reading the CMB end and the never-set `g[399]` of an `np.empty` array (B5).

### 1.1 `mynewtonSys` (src/shootp.py)
- Direction unchanged: `dx = J^-1 f` (`np.dot(np.linalg.inv(J), f)`, same call as v1.2.0).
- Convergence test unchanged and evaluated **first**: if `|f| < ftol` or `|dx| < xtol` at the current iterate, `x - dx` is returned before any trial evaluation -- exactly v1.2.0's order, so a converging final step cannot be altered by the box.
- Otherwise `alpha = 1` is tried; the trial `x - alpha*dx` is evaluated with `shoot_mercmodel` (`mercmodel_trial`) and rejected -- `alpha` halved -- if `mercmodel_box` says: non-finite `f`/`fout` (NONFINITE_SHOOT); `rcmb <= ricb` (RICB_GE_RCMB); `chi_li_icb >` eutectic at the trial's own `P_icb` (S, S+Si) or `>` liquidus Si max (Si), or `chi_li_icb < -CHI_NEG_TOL = -0.01` (CHI_OUTSIDE_ADMISSIBLE_BOX); or `|f_trial| > GROWTH_MAX = 100 * |f|`. A `SolverError` raised inside the trial shoot is a rejection, except SI_ABOVE_LIQUIDUS_MAX, which is re-raised. Below `ALPHA_MIN = 1e-3` (10 halvings) the radius fails with the last rejection's code; every rejected trial (alpha, code, detail, trial iterate) is in the solver log.
- Singular Jacobian: `cond(J) > COND_MAX = 1e12` or a `LinAlgError` -> SINGULAR_JACOBIAN (v1.2.0: exact `det(J) == 0`). A zero FD column gives `cond = inf`. `cond(J)` on converging Mercury paths measured <= 7.3e5 (inherited, audit claim 3c) / <= 6.2e6 (fresh, line-search sample); `detJ` is still logged.
- `line_search=False` restores the v1.2.0 step exactly; toy Jacobians without a `trial_fun` get no line search (unchanged unit tests).

**Why no Armijo test, and why the lower chi bound is -0.01, not 0** (the owner's invariant: wherever v1.2.0 converged, `alpha = 1` must pass on every iteration):
- Armijo (measured, fresh, on the 108-case stratified sample's v1.2.0-equivalent paths, `runs/base/*.json` of the failure analysis): 1841 converged radii, 3553 accepted Newton steps; **48 steps (1.4%) on 32 radii (1.7%) increase |f|** (median growth 1.6x, 90th pct 5.1x, max 18.6x) and those paths converge anyway. Any sufficient-decrease rule would have altered them. `GROWTH_MAX = 100` sits 5x above the largest growth seen on a converging path.
- Chi lower bound (measured, fresh, full published dataset): **103,243 of 474,075 converged rows (21.8%) have `chi_li_icb < 0`** (typically -0.001 to -0.003; the low-CMR2 draws that need almost no S), and 1,502 (0.3%) have `chi_li_icb > chi_eut_icb` (a converging final step past the clamp). A hard lower bound at 0 would reject `alpha = 1` on those paths. The overshoot that actually killed sweeps is to chi ~ -0.02 .. -0.06, where the fluid-core RK4 returns NaN -- caught by the non-finite test regardless of `CHI_NEG_TOL`. Slightly negative converged rows keep being written with `error_code 4` as in v1.2.0.

### 1.2 `getk2` at `nrs = 0` (src/shootp.py)
Owner decision: treat the core as fully fluid from the centre. The inner-core block is skipped (`if nrs > 0`), and the fluid loop's `k = 0` shell is `[0, r[0]]` with `rho[0] = rhof(r[0]/2)`, `g[0] = (4 pi G_nd/3) rho[0] r[0]` (g(0) = 0). No `k+nrs-1` wrap, arrays `np.zeros`, and a non-finite / non-positive `rho`,`g` check raises NONFINITE_SHOOT. `BsAs` sums over `range(nrs)` = nothing, so `xi = 0` exactly as before. `nrs >= 400` or `ricb >= rcmb` raises RICB_GE_RCMB instead of an `IndexError`. Unit test: constant density gives `g = (4 pi G_nd/3) r` on every grid point including `r[0]` (`testsys/unit/test_line_search.py`).

### 1.3 Sweep policy (src/driverp.py, owner decision 2026-09-30)
Per radius: (1) warm start from the last **converged** solution; (2) if it fails with a radius-dependent code and differs from the generic `v0 = [0.8, 1.0, 0.8, 0.7, 0.05]`, one cold start from `v0`; (3) otherwise a failure with the last attempt's code (the warm-start error is kept in the log context); (4) the next radius warm-starts from the last converged solution -- a failed radius is never a start; (5) code 6 is checked once before the sweep, writes one row and ends the composition. Every attempted radius is a csv row; failed rows carry `ricb`, `chi_Si_icb`, `error_code`, `start`, `newton_iters`, `resid_norm` and NaN in every physical column; `.h5` only for converged radii. v1.2.0 stopped the composition at the first failure and wrote nothing for it.

## 2. The invariant and how it is enforced
`testsys/integration/test_v1_2_0_invariant.py` with the fixed 14-case sample `testsys/reference/v1_2_0_sweeps/sample.json` (one published MC draw per failure class; 6 cases with converged v1.2.0 rows -- 4 to 12 each within the 600-km cap -- and 8 zero-row cases). Reference `v1_2_0_sweeps.json`: `generate_sweeps.py --src <main at 18cf78a> --policy stop`, pinned env (numpy 1.21.5, scipy 1.8.0, /usr/bin/python3 3.10.12), wall 237 s on 8 workers. The test re-runs the sample with the current `src/` and the continue policy capped at (v1.2.0 rows + 2) radii, then asserts bit-identical `v`, `f`, `fout` for every v1.2.0-converged row (exact on the pinned env, rtol 1e-9 elsewhere), validity + smoothness for every additional ("recovered") row, and reproduction of `recovered_rows_v1_3_0.json`.

Result (fresh, this branch): TODO-FILL (rows compared / identical; recovered rows; 10-m rows identical incl. getk2 change).

## 3. Recovery statistics (fresh; 37-case stratified sample, one published run per {MOI x composition x end state x died-at-10-m}, full 40-radius grid)
TODO-FILL: per failure mode, rows/radii recovered by line search alone (stop policy) vs line search + continue policy (warm+cold), n and Clopper-Pearson 95% CI; adaptive-continuation measurement (report only); runtime per sweep v1.2.0 vs v1.3.0.

## 4. Gate results
TODO-FILL: `testsys/run.py all` counts and runtime on the committed tree; fast tiers in a pins-stripped venv.

## 5. What a reviewer would attack / open
- The recovered models are validated numerically (residual, box, positivity, smoothness) but have no independent physical oracle -- same standing as every other S+Si result (`CLAUDE.md`, item 4).
- `CHI_NEG_TOL = -0.01` and `GROWTH_MAX = 100` are calibrated on the measured converged-path distribution, not derived; both are module constants with the measurement quoted next to them.
- The continue policy multiplies runtime for compositions whose solution branch ends early (every later radius costs a warm + a cold failure) -- quantified in §3.
- Item 20 (`get_mass_core` quadrature) and B6 (evolution mode) untouched, as instructed.

## Reproduce
```
W=<worktree>; cd $W/testsys/reference/v1_2_0_sweeps
PYTHONNOUSERSITE=1 /usr/bin/python3 generate_sweeps.py --src /path/to/v1.2.0/src --policy stop --out v1_2_0_sweeps.json          # fixture (done at 18cf78a)
PYTHONNOUSERSITE=1 /usr/bin/python3 generate_sweeps.py --src $W/src --policy continue --extra-radii 2 --out /tmp/v130_inv.json    # what the test does
PYTHONNOUSERSITE=1 /usr/bin/python3 generate_sweeps.py --src $W/src --policy continue --adaptive --cases cases36.json --out /tmp/v130_measure36.json   # §3
/usr/bin/python3 testsys/run.py all
```
