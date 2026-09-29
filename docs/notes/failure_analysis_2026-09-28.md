# PIE present-day model failures — when, how, why (analysis notes, 2026-09-28/29)

Scope: PIE v1.0.5 present-day solver (`src/driverp.py` → `shootp.mynewtonSys` → `J_mercmodel` → `shoot_mercmodel` → `getk2` → `libCore.getpotvsr`) and the published Monte Carlo dataset `~/shared_dataset/zenodo.16459292/extracted/PIE/work.{margot,genova}` (read-only; verified complete against the md5-checked archive: 1,057,809 files). No file under `src/` or `testsys/` was modified; all instrumentation is in a scratch copy (see "Reproduce"). Scripts and raw result tables: `failure_analysis_2026-09-28_scripts/`. Figures: `failure_analysis_fig{1,2,3}_*.png` next to this file.

## Summary (one paragraph)
Every published present-day sweep dies at the first inner-core radius where the **undamped** Newton step (`x -= J⁻¹f`, no step control, FD Jacobian) throws the iterate out of the admissible box in the light-element unknown chi_li_icb: past the eutectic (→ `min(sol, chi_eut)` clamp → Jacobian column exactly zero → `det(J)==0` → `sys.exit`), below zero or above the Si maximum (→ NaN in the fluid-core RK4 → NaN density fit → NaN matrix in `getpotvsr` → SuperLU "Factor is exactly singular" → uncaught traceback), or past rcmb (→ `IndexError` in `getk2`). Nothing is recorded: the CSV simply stops. Failures at large ricb are predominantly the physical end of the solution branch (chi_li_icb reaches the eutectic within one 50-km step of a converged model; or ricb > rcmb). Failures **at the first radius (10 m)** are half physical (no model with chi in [0, eutectic] satisfies CMR2/CmC/mass — a sharp CMR2 threshold), half **numerical** (a damped Newton finds a full 30–37-radius sweep for 15/22 sampled 10-m crashes). The numerically lost models are systematically **no-snow, small-core, low-CMR2 (S, S+Si) models**, so discarding them biases the published snow-state statistics upward (e.g. margot S+Si 10 wt% Si: rows with snow 19.9% published → ≈12.8% corrected; genova S+Si 5 wt%: 4.9% → ≈2.8%).

## 0. Facts about the published run that frame everything below
- One MC draw = `monteCarlo.run.py` → `scheduler.py` → 18 sequential `python main.py p CMR2 CMC light Edmund [chi_Si]` processes: S+Si with chi_Si = 0.00…0.15 (16), then S, then Si. Liquidus = Edmund only. CMC = 0.426·0.346/CMR2 (1-D family).
- Radius grid `rs = np.arange(1e1, 2e6, 50e3)`: 40 radii (10 m, 50.01, …, 1950.01 km). Warm start: `v0` = previous radius' solution.
- **`mynewtonSys` never returns `None`: on maxit and on `det(J)==0` it calls `sys.exit()`** (shootp.py ~L300/311). `driverp.py:38 if v is None: break` is dead code. A Newton failure kills the process for that (CMR2, CMC, light, chi_Si); larger radii are never attempted; the other 17 compositions of the draw are unaffected (separate processes).
- stdout of the 18 processes → `results/log.<CMR2>.<CMC>.txt`; stderr (uncaught tracebacks) → launcher file `a.log.o<jobid>`. Authoritative launcher logs: margot `a.log.o2494644` (Jul 11 2025 = `results/timeLog.20250711.txt`), genova `a.log.o2491704` (Jul 10 2025). Older `a.log.*` are aborted earlier attempts (HDF5/FileExists errors, older dir-name format).
- `error_code` is 0 in all 201,633 margot + 272,442 genova rows: `shoot_mercmodel` hard-codes `err0=False` and discards the RK4 `err2` array, so `error_code=1` cannot fire; `error_code=2` (`chi_li.any()<0`) is dead. **No failure is recorded in any data product; the logs are the only record.**
- Log/CSV consistency: for all 18,432 margot runs, `n_rows == n_radii_attempted − 1` (`== n_radii` if finished). Row count is an exact proxy for the death radius.

## 1. WHEN

### 1.1 Per MOI × composition (end state of the `main.py` process; counts of 1024 draws)
Margot (CMR2 ~ N(0.346, 0.014)):

| composition | finished 40 radii | Newton maxit exit | det(J)==0 exit | uncaught traceback | died at 10 m (zero rows) | died 50 km–1.45 Mm | died ≥1.5 Mm |
|---|---|---|---|---|---|---|---|
| S | 0 | 50 | 841 | 133 | 439 | 487 | 98 |
| Si | 258 | 194 | 0 | 572 | 572 | 39 | 155 |
| S+Si 0.00 | 0 | 49 | 840 | 135 | 441 | 486 | 97 |
| S+Si 0.05 | 0 | 34 | 746 | 244 | 464 | 437 | 123 |
| S+Si 0.10 | 0 | 21 | 630 | 373 | 513 | 351 | 160 |
| S+Si 0.12 | 0 | 33 | 557 | 434 | 516 | 329 | 179 |
| S+Si 0.13–0.15 | 1024 each: immediate exit "Exceeding allowed maximum Si%wt of 12%" — by design |

Genova (CMR2 ~ N(0.333, 0.005)):

| composition | finished | Newton maxit | det(J)==0 | traceback | died at 10 m | 50 km–1.45 Mm | ≥1.5 Mm |
|---|---|---|---|---|---|---|---|
| S | 0 | 62 | 779 | 183 | 18 | 725 | 281 |
| Si | 602 | 49 | 0 | 373 | 18 | 14 | 390 |
| S+Si 0.00 | 0 | 62 | 778 | 184 | 20 | 723 | 281 |
| S+Si 0.05 | 0 | 44 | 448 | 532 | 404 | 189 | 431 |
| S+Si 0.10 | 0 | 9 | 113 | 902 | 874 | 14 | 136 |
| S+Si 0.12 | 0 | 0 | 46 | 978 | 964 | 5 | 55 |

Totals (excluding the 3072 by-design chi_Si>0.12 exits per set): margot 15,360 runs → det(J)==0 10,152 / traceback 4,250 / maxit 700 / finished 258; zero-row runs 7,166 (46.7%); genova 15,360 → det(J)==0 5,874 / traceback 8,281 / maxit 603 / finished 602; zero-row 6,413 (41.8%).
Traceback census (authoritative launcher logs): margot 4037 "Factor is exactly singular" (libCore.py:266) + 213 `IndexError ... size 400` (shootp.py getk2) = 4250 = the stdout-log crash count exactly; genova 8,281 (≈ 7.8k singular + ~0.5k IndexError).

### 1.2 Where in (CMR2, CMC) and at which radius (Fig. 1, Fig. 2, Fig. 3)
- **det(J)==0 at 10 m** (margot S: 367 draws): CMR2 ∈ [0.3505, 0.3753] — a sharp threshold at CMR2 ≈ 0.3505 (S+Si 0.05: ≈0.3544). Above it no S-bearing model exists at any radius.
- **det(J)==0 at a later radius** (margot S: 474): CMR2 ∈ [0.3244, 0.3505]; death radius 1.0–1.65 Mm (mode 1.1–1.2 Mm margot, 1.5–1.65 Mm genova).
- **Singular-LU crash at 10 m** (margot S: 72; S+Si 0.05: 184; Si: 422; genova S+Si 0.10: 874): concentrated at the *low*-CMR2 edge for S and S+Si (mean CMR2 0.329 vs 0.343 for survivors, margot S+Si 0.05; KS p < 1e-3 for every composition) and at the *high*-CMR2 edge for Si (0.359 vs 0.334). For S+Si the zero-row fraction rises monotonically with chi_Si (Fig. 3), because more Si lowers the S required and the 10-m step overshoots to chi_S < 0.
- **Newton maxit**: mostly later radii; at 10 m only for Si with CMR2 ∈ [0.3442, 0.3494] (margot 150, genova 17) and S+Si 0.05 at CMR2 ≈ 0.354 (4).
- **IndexError** crashes: at 1.95 Mm (Si only: inner core reaches rcmb ≈ 1.92–1.94 Mm).
- Last converged radius distribution (Fig. 2): broad, peak 1.05–1.35 Mm (margot) / 1.4–1.6 Mm (genova); only Si sweeps reach 1.95 Mm.

## 2. HOW — taxonomy (margot counts; genova in parentheses)

| mode | mechanism | count (runs) | typical radius |
|---|---|---|---|
| A. det(J)==0 → `sys.exit` | iterate chi_li_icb ≥ chi_eut → `min(sol, eut)` clamp → FD column J[:,4] ≡ 0 | 10,152 (5,874); 3,749 (6) of them at 10 m | 10 m if CMR2 above threshold; else 1.0–1.7 Mm |
| B. `RuntimeError: Factor is exactly singular` | iterate chi_li_icb < 0 (S) or > Si max (Si) → NaN in RK4/EOS → NaN `polyfit` → 797 non-finite entries in A → SuperLU | 4,037 (≈7.8k); ≈3,250 (6,388) at 10 m | 10 m, or 1.3–1.7 Mm |
| C. `IndexError` in `getk2` | iterate rcmb ≤ ricb → nrs ≥ 400 | 213 (≈0.5k) | 1.95 Mm |
| D. Newton maxit (12) → `sys.exit` | period-2 oscillation (22/31 sampled), divergence (4), stagnation (3) | 700 (603) | mixed |
| E. `error_code` 1/2 rows | dead code | 0 | — |
| F. chi_Si > 0.12 with Edmund → `sys.exit` | by design | 3,072 (3,072) | 10 m |

Mode A dominates margot; mode B dominates genova (because genova's low CMR2 needs little S and the 10-m step overshoots to chi_S < 0).

## 3. WHY — root causes (fresh, instrumented reproductions on this host)

### 3.1 The failures are deterministic properties of the algorithm, not of LS6
Stratified sample: 108 published runs, 3 per {MOI × composition ∈ {S, Si, S+Si 0.05, S+Si 0.10} × end state × died-at-10-m?}. Full warm-started sweep as in `driverp.py`, `OMP/OPENBLAS_NUM_THREADS=1`, 16 concurrent processes (`run_batch.py cases.json base`; table `runs_base_analysis.txt`).
**Row count reproduced exactly in 107/108 runs** (one run gained one radius); failure mode reproduced in kind: 22/22 "crash at 10 m" → NaN → singular LU here; 29/29 det(J)==0 → zero chi column; 31/33 maxit → maxit; 6/6 Si-at-1.95-Mm crashes → rcmb (1.92–1.935 Mm) < ricb (1.95 Mm).

### 3.2 Mode B (singular LU) — NaN from a chi overshoot, plus a real uninitialised-memory bug at 10 m
Traces at the crash (all 22 sampled 10-m crashes): iteration 1–2, iterate e.g. S: `v=[0.88, 1.94, 0.78, 0.50, −0.063]` (chi_S < 0); Si: `v[4]=0.314` (> 0.12 max) or −0.021/−0.038; then `nan_yc=8, nan_rhof=2` (fluid RK4), `polyfit` → NaN coefficients, 400/400 non-finite rho and g in `getk2`, 797 non-finite entries in A → SuperLU reports a NaN matrix as "exactly singular". cond(A) for finite A is ~3.5e27 (rows scaled by `r[0]^(2l+1) ≈ 1e-27`) but SuperLU/dense LAPACK both solve it; conditioning is not the trigger.
Separately, **`getk2` reads uninitialised memory whenever nrs = round(400·ricb/rcmb) = 0, i.e. ricb < ~2.5 km — only the 10-m radius**: the inner-core loop never initialises `r[0], rho[0], g[0]`; `g[1+nrs]` is built from garbage `g[0]`, and the fluid loop's k=0 step builds `g[0]` from `g[k+nrs−1] = g[−1]`, the last element of an `np.empty` array, scaled by `(r[−1]/r[0])² ≈ 6e10`. Forced-fill experiment on the test's flaky case (margot CMR2=0.33521178639464477, S+Si 0.05, 10 m): fill 0 / 1 / 1e300 / stale value → converged identically (alpha[0] → 0 whenever |g[0]| is large; xi ≡ 0 at nrs=0 because `BsAs` sums over an empty range); **fill NaN → 797 non-finite entries → "Factor is exactly singular" with no Newton iteration at all**. One sampled line-search run showed exactly this signature (`nonfinite_g=400, nonfinite_rho=0, nan_yc=0`). This is the run-to-run nondeterminism seen in the fixed-seed test (1 vs 2 singular failures): heap contents differ between processes/platforms. Environment: here `/usr/bin/python3` 3.10.12, numpy 1.21.5, scipy 1.8.0, OpenBLAS-pthread; LS6 `/opt/apps/intel19/python3/3.9.7`, scipy 1.6.1.

### 3.3 Mode A (det(J)==0) — chi_li_icb pushed past the eutectic; at later radii it is the end of the solution branch
In every det(J)==0 stop the FD Jacobian has column 5 (chi_li_icb) identically zero, other column norms O(1), cond(J) ~1e2 at the previous iterate. `getchi_li_grun` clamps `chi_li = min(sol, chi_li_eut)`; once x[4] ≥ chi_eut(P_icb) (0.13–0.15) the 1e-6 relative perturbation changes nothing. Iterates at the stop: x[4] = 0.139 (S, 10 m), 0.18–0.31 (later radii) — a large overshoot from a converged neighbour 50 km away, the signature of a fold in ricb. Last converged rows before a det(J)==0 death have chi_li_icb/chi_eut median 0.86–0.92 (10th pct 0.54, 90th 0.98; `runs_make_cases.txt`). **Clamped Newton (x[4] ≤ 0.999·eut, min-norm step on the zero column, line search, maxit 25) recovered 0/29 det(J)==0 cases to a further converged radius**, best residual floors |f| = 3e-3…1e-1 (tolerance 1e-6): no root with chi below the eutectic → **physical**.

### 3.4 Mode D (maxit) — step control, not conditioning or tolerance
Example (margot Si CMR2=0.347, 10 m, maxit 40): |f| alternates 2.77e-2 ↔ 8.82e-2 with |dx|=0.176 for 40 iterations, cond(J) 60–150 — an exact period-2 Newton cycle. eps=1e-5 (3/33 improved by ≤1 radius) and maxit=40 (11/33 improved, mostly by 1–3 radii) do not fix it; line search converts it into a residual floor 1e-3…2e-2 for the 10-m Si cases (CMR2 0.3444–0.3469: no admissible Si-only model; consistent with the finished Si sweeps ending at CMR2 ≤ 0.3429).

### 3.5 Mode C — physical (ricb ≥ rcmb) but crashes instead of stopping cleanly.

## 4. VERDICT on "failures are wrong models — discard them"

Partly true, partly false, and the false part is biased:
- **Later-radius deaths (≈60% of all deaths; ~all det(J)==0 and IndexError cases) are physical**: the branch ends when chi_li_icb reaches the eutectic or the inner core reaches rcmb. Recovery attempts gained 0–3 radii (never ≥5) in 66 sampled later-radius cases except 3 (4.5%). The published rows up to that radius are valid; only the truncation is legitimate.
- **10-m det(J)==0 and 10-m Si maxit deaths are physical** (0/11 and 0/6 recovered; residual floors ≥3e-3): no admissible model above CMR2 ≈ 0.3505 (S) / 0.3544 (S+Si 0.05) / in [0.344, 0.349] (Si). Discarding is correct.
- **10-m singular-LU crashes are ~2/3 numerical**: 15/22 sampled cases (S 5/6, S+Si 0.05 4/6, S+Si 0.10 4/6, Si 0/4) converge with a damped Newton and continue for 30–37 radii (`runs_recovered_vs_published.txt`). Scaled to the population: ≈48 of 72 margot S draws, ≈64/184 S+Si 0.05, ≈213/320 S+Si 0.10, ≈404/404 genova S+Si 0.05, ≈583/874 genova S+Si 0.10 are **admissible models that were dropped by a solver artefact** (`runs_bias_estimate.txt`).
- **Bias — yes.** The recovered models are all no-snow (isnow = 0 in 100% of their 12×~34 radii vs 5–39% snow rows among published survivors), have smaller cores (rcmb 1.87–1.98 Mm vs published medians 1.96–2.03 Mm) and lower CMR2. Correcting the row-weighted snow fraction: margot S 38.5% → ≈34.5%; margot S+Si 0.05 26.3% → ≈22.7%; margot S+Si 0.10 19.9% → ≈12.8%; genova S+Si 0.05 4.9% → ≈2.8%; genova S+Si 0.10 2.9% → ≈0.5% (only 150 of 1024 draws survive in the published set). Si-only and genova S/Si are unaffected (their 10-m losses are physical). The mean CMR2 of surviving S+Si 0.10 margot draws shifts 0.3482 → ≈0.3427. These are sample-based extrapolations (3 cases per class); the direction is unambiguous, the magnitudes are ±30%.

## 5. Recovery experiments (on the 108-case sample; "more/fewer/same" = rows vs published; full table `runs_bestof.txt`)

| variant | more | fewer | same | comment |
|---|---|---|---|---|
| backtracking line search (halve step while |f| does not decrease, ≤6 halvings) | 20 | 9 | 79 | **recovers 12/22 10-m crashes to full sweeps**; 9 later-radius cases stop 1–3 radii earlier (finds a local |f| minimum) — use with fallback to the undamped step |
| clamp chi to [1e-4, 0.999·eut] + lstsq on zero column + line search, maxit 25 | 9 | 34 | 65 | recovers 3 more 10-m crashes; hurts later radii — clamping fights the fold |
| start at 50 km instead of 10 m | 2 | 0 | 40 | does **not** fix 10-m crashes (same overshoot at 50 km); avoids the nrs=0 memory bug only |
| maxit 12 → 40 | 11 | 0 | 22 | +1–3 radii; period-2 cycles never converge |
| FD eps 1e-6 → 1e-5 | 3 | 0 | 30 | negligible |
| cold start (generic v0 every radius) | 15 | 7 | 44 | inconsistent; not a fix |
| dense `np.linalg.solve` in `getpotvsr` | — | — | — | identical result to SuperLU on finite A; irrelevant to the NaN case |
| force nrs ≥ 1 in `getk2` | — | — | — | removes the uninitialised read; k2/xi unchanged to solver tolerance |

**Recommended fix (not applied):** (1) in `mynewtonSys`, guard the step — reject any iterate with x[4] outside [0, chi_eut(P_icb)] (or > Si max) or x[2] ≤ ricb, and backtrack (halve) instead; return `None` on failure and let `driverp.py` record a `fail_mode` row (the existing `break` then works). (2) In `getk2`, `nrs = max(1, …)` and initialise arrays with `np.zeros`. (3) Treat det(J)==0 and NaN in `f` as "branch ended" — record and stop cleanly. Then re-run the ~2,800 (margot) + ~1,300 (genova) 10-m singular-LU compositions; expected ≈65% return full sweeps.

## Reproduce
```
S=<scratch>; cp -r PIE/src $S/src_instr; python3 $S/patch_instr.py; python3 $S/patch2.py      # instrumentation, no src/ edits
export PYTHONNOUSERSITE=1 MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python3 $S/probe.py CMR2 CMC {S|Si|S+Si} Edmund chi_Si out.json [only_ricb=10] [cond=1] [k2_fill=NaN|0] [k2_min_nrs=1] [dense=1] [linesearch=1] [clamp_chi=1] [maxit=40] [eps=1e-5] [start_ricb=50010] [cold=1]
python3 $S/inventory.py inventory.json && python3 $S/summarize_inventory.py inventory.json   # published-set census (read-only, ~15 min on the shared FS)
python3 $S/make_cases.py inventory.json cases.json 3; NW=16 python3 $S/run_batch.py cases.json base [probe opts]
python3 $S/analyze_runs.py base ls ...; python3 $S/bestof.py; python3 $S/bias_estimate.py ls clamp clamp_rest start50 maxit40 eps5 cold; python3 $S/figures.py
```
Environment: /usr/bin/python3 3.10.12, numpy 1.21.5, scipy 1.8.0 (SuperLU bundled), BLAS/LAPACK = OpenBLAS-pthread 0.3.x (`/usr/lib/x86_64-linux-gnu/openblas-pthread`), 64-core shared host, load 50–85 during runs (all timings contended, none quoted). Test-flake case: `testsys/e2e/test_published_wide_sweep.py` margot/S+Si/CMR2_0.33521178639464477_CMC_0.43971007578615007 at 10 m — reproduced only with NaN heap garbage (§3.2).
