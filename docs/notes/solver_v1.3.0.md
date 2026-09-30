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

Result (fresh, this branch at 7378273, pinned env, `generate_sweeps.py --policy continue --extra-radii 2`, wall 878 s / 8 workers): **84 v1.2.0-converged rows compared, 84 bit-identical** (`v`, `f`, `fout`), including all 7 rows at ricb = 10 m, i.e. the getk2 nrs=0 change leaves 10-m outputs unchanged (xi = 0 exactly in both). An earlier iteration of the box with a chi lower bound of -0.01 gave 28/84 identical (2 Si-only sweeps with chi_li_icb ~ -0.04 rejected at every radius, and two S/S+Si sweeps whose intermediate iterates dip below -0.01 took different paths) -- that is why the shipped box has no lower bound (§1.1). The published dataset's most negative converged chi_li_icb is -0.175 (margot S+Si), -0.164 (margot Si), -0.070 (genova Si), -0.036 (genova S); 19,305 published rows have chi < -0.01.

Rows converged by v1.3.0 that v1.2.0 did not produce on this sample (7): `margot_SpSi_005_newton_maxit_later` k=5 (warm start after a v1.2.0 NEWTON_MAXIT at k=4, chi = 0.096, admissible, resid 2e-11); and 6 rows at k=0,1 of the 10-m singular-LU cases `genova_S`, `margot_S`, `genova_SpSi_005` with **chi_li_icb = -0.018 … -0.036** -- converged, finite, but outside the admissible box (written with error_code 4 by `driverp.py`'s err / `(chi_li<0).any()` checks) and therefore NOT counted as recovered valid models. The 10-m failures that remain fail with CHI_OUTSIDE_ADMISSIBLE_BOX after backtracking (cold start; 3–8 iterations). Fixture: `testsys/reference/v1_2_0_sweeps/recovered_rows_v1_3_0.json` (tag `admissible`).

Consequence for the failure-analysis claim "10-m singular-LU crashes are ~2/3 numerical, recovered models are admissible": the line search does turn those crashes into converged solutions, but on this sample the solutions have chi_li_icb < 0, i.e. they are the same class as the 21.8% of published converged rows with negative chi (error_code 4). Whether such rows are "models" is the owner's call (item 18); v1.3.0 records them and tags them, it does not decide.

## 3. Recovery statistics (fresh, this branch; line search + continue-after-failure; Clopper-Pearson 95% CIs; `recovery_stats.py` in the scratch copy, table `recovery_stats.txt`)

### 3.1 Invariant sample (14 published draws, radii capped at v1.2.0 rows + 2) -- PARTIAL evidence, small n
"Radii beyond the stop" = radii the v1.2.0/v1.0.5 sweep never reached. A converged radius is **admissible** when chi_li_icb is in [0, bound] and the shoot raised no negative-chi flag (otherwise it is written with error_code 4 and counted as "inadmissible").

| published class | cases | radii beyond stop | converged (CI95) | admissible (CI95) | inadmissible (chi<0) | remaining failures |
|---|---|---|---|---|---|---|
| singular-LU crash at 10 m | 5 | 10 | 6 (0.26–0.88) | 0 (0.00–0.31) | 6 | 4 CHI_OUTSIDE_ADMISSIBLE_BOX |
| det(J)==0 at 10 m | 2 | 2 | 0 (0.00–0.84) | 0 | 0 | 2 CHI_OUTSIDE_ADMISSIBLE_BOX |
| Newton maxit at 10 m (Si) | 1 | 2 | 0 (0.00–0.84) | 0 | 0 | 2 CHI_OUTSIDE_ADMISSIBLE_BOX |
| Newton maxit, later radius | 3 | 2 | 1 (0.01–0.99) | 1 (0.01–0.99) | 0 | 1 NEWTON_MAXIT |
| **total** | 14 | 16 | 7 (0.20–0.70) | **1 (0.00–0.30)** | 6 | 9 |

Cases with at least one admissible recovered radius: 1/14 (CI95 0.00–0.34). The 6 "inadmissible" conversions are the 10-m singular-LU class of S / S+Si models: the line search turns the NaN crash into a converged root with chi_li_icb = -0.018 … -0.036 -- consistent with the failure analysis (those models sit at the low-CMR2 edge where the constraints want less than zero sulfur). Whether error_code-4 rows count as models is item 18's question, not the solver's.
Runtime (contended host, load 40–60, 8 workers, `OMP_NUM_THREADS=1`): converged radius median 26 s (n=91); a failed radius costs a warm and a cold attempt, median 88 s (n=9). The 14-case invariant run took 878 s wall vs 237 s for the v1.2.0 fixture on the same sample (the extra radii and the failed-radius double attempts).

### 3.2 37-case full-grid measurement (one published run per {MOI x composition x end state x died-at-10-m}, 40 radii, continue policy, plus the report-only adaptive-halving probe; and a line-search-only / stop-policy pass)
Running in the background at PR time (resumable: `generate_sweeps.py --partial-dir`); results will be posted as a PR comment / follow-up notes commit. Numbers above are the evidence the PR ships with and are explicitly partial.

## 4. Gate results (fresh, committed tree, this shared 64-core box at load 40–60, `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=1`, `nice -n 10`)
- Pinned env (`/usr/bin/python3` 3.10.12, numpy 1.21.5, scipy 1.8.0), `testsys/run.py all` at 6cbf39f: 237 passed, 3 xfailed, 1 failed + 5 errors in 1884 s — the 5 errors were the e2e `main.py` sweep timing out at the v1.2.0 budget of 900 s (the 40-radius continue policy plus warm+cold attempts on failed radii), the 1 failure a published_wide inadmissible solve accepted on the |dx| < xtol criterion with |f| = 6.8e-5 > ftol. Both fixed in 7feb91d (timeout 5400 s; validity uses the solver's own stop rule). Re-run of the two affected e2e tests at 7feb91d: **6 passed in 2540 s**; published_wide: 240 sampled, 171 converged+matched, 46 non-convergence reproduced, **1 recovered (admissible)**, 22 converged-inadmissible (chi < 0, error_code 4), **0 hard failures** (B5 flake allowance removed). Fast tiers at 7feb91d (unit+contract+integration): 201 passed, 3 xfailed, 1110 s.
- Pins-stripped venv (numpy 2.2.6, scipy 1.15.3, pandas 2.3.3, tables 3.10.1, pytest 9.1.1), fast tiers at 7feb91d: **200 passed, 1 skipped (interp2d legacy reference, by design), 3 xfailed, 777 s**.
- Runtime change: fast tiers 194–307 s (v1.1.0, 106 tests) → ~1110 s (v1.3.0, 204 tests; the 14-case identity re-run is ~15 min of it, the 10-m determinism test ~1.5 min). The e2e `main.py p 0.346 0.424 S Edmund` sweep grew from ~4.5 min (v1.2.0, stopped at the first failure) to ~35 min (40 radii, failed radii cost two attempts) — the owner-accepted cost of the continue policy; the v1.3.1 speed work is the intended remedy.

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
