Corrected 2026-09-29 per docs/audits/AUDIT_2026-09-29_solver-failures.md.

# PIE present-day model failures — when, how, why (analysis notes, 2026-09-28/29)

Scope: PIE v1.0.5 present-day solver (`src/driverp.py` → `shootp.mynewtonSys` → `J_mercmodel` → `shoot_mercmodel` → `getk2` → `libCore.getpotvsr`) and the published Monte Carlo dataset `~/shared_dataset/zenodo.16459292/extracted/PIE/work.{margot,genova}` (read-only; verified complete against the md5-checked archive: 1,057,809 files). No file under `src/` or `testsys/` was modified; all instrumentation is in a scratch copy (see "Reproduce"). Scripts and raw result tables: `failure_analysis_2026-09-28_scripts/`. Figures: `failure_analysis_fig{1,2,3}_*.png` next to this file.

Wording convention (audit, claim 6a): "no root found" below means **no root found by the local Newton variants tried** (§5). It does not establish that no admissible model exists. That would need the test not yet run: continuation in ricb with fold detection, or a chi_li_icb scan over [0, chi_eut] at fixed ricb.

## Summary (one paragraph)
Every published present-day sweep dies at the first inner-core radius where the **undamped** Newton step (`x -= J⁻¹f`, no step control, FD Jacobian) throws the iterate out of the admissible box in the light-element unknown chi_li_icb. There are three exits. Past the eutectic, the `min(sol, chi_eut)` clamp zeroes a Jacobian column exactly → `det(J)==0` → `sys.exit`. Below zero or above the Si maximum, the fluid-core RK4 goes NaN → NaN density fit → NaN matrix in `getpotvsr` → SuperLU "Factor is exactly singular" → uncaught traceback. With ricb/rcmb ≥ 0.99875, `getk2` raises `IndexError`. Nothing is recorded: the CSV simply stops. At large ricb, no root was found by the local Newton variants tried: chi_li_icb reaches the eutectic within one 50-km step of a converged model, or ricb ≳ rcmb. Whether this is the true end of the solution branch is untested (no continuation / fold detection / chi scan). **At the first radius (10 m)**, a best-of-7-variant selection finds a full 30–37-radius sweep for **13/22** sampled 10-m singular-LU crashes; backtracking line search alone, the single-method figure, finds **12/22** (95% CI [0.32, 0.76]). A published 10-m det(J)==0 case (`runs/base/034.json`) also went from 0 to 30 radii on a plain re-run. So some 10-m losses are numerical. The recovered singular-LU models skew no-snow, small-core and low-CMR2, so discarding them *plausibly* biases the published snow-state statistics upward. **The magnitude is unknown** (§4). The only way to settle it is a full re-run of all 10-m zero-row compositions under one fixed solver, with bounds and validity checks on every row.

## 0. Facts about the published run that frame everything below
- One MC draw = `monteCarlo.run.py` → `scheduler.py` → 18 sequential `python main.py p CMR2 CMC light Edmund [chi_Si]` processes: S+Si with chi_Si = 0.00…0.15 (16), then S, then Si. Liquidus = Edmund only. CMC = 0.426·0.346/CMR2 (1-D family).
- Radius grid `rs = np.arange(1e1, 2e6, 50e3)`: 40 radii (10 m, 50.01, …, 1950.01 km). Warm start: `v0` = previous radius' solution.
- **`mynewtonSys` never returns `None`: on `det(J)==0` and on maxit it calls `sys.exit()`** (`src/shootp.py:298-300`, `:311`). The dead-code line `driverp.py:38 if v is None: break` is never reached. A Newton failure kills the process for that (CMR2, CMC, light, chi_Si). Larger radii are never attempted. The other 17 compositions of the draw are unaffected, because they run as separate processes. `det(J)==0` is an exact float test (`shootp.py:298`): it catches the exact zero column (Mode A) but misses a near-singular J.
- stdout of the 18 processes → `results/log.<CMR2>.<CMC>.txt`; stderr (uncaught tracebacks) → launcher file `a.log.o<jobid>`. Authoritative launcher logs: margot `a.log.o2494644` (Jul 11 2025 = `results/timeLog.20250711.txt`), genova `a.log.o2491704` (Jul 10 2025). Older `a.log.*` are aborted earlier attempts (HDF5/FileExists errors, older dir-name format). **Trap:** the aborted-run logs `a.log.o2490544` (margot) and `a.log.o2489079` (genova) would roughly double every traceback count if grepped together with the authoritative ones. All counts here use the authoritative logs only.
- `error_code` is 0 in all 201,633 margot + 272,442 genova rows. `shoot_mercmodel` hard-codes `err0 = False` (`src/shootp.py:131`) and returns `err0` (`:251`), discarding the `err` returned by the RK4. So `error_code=1` cannot fire, and `error_code=2` (`chi_li.any()<0`, `driverp.py:111`, which compares a bool to 0) is dead. `src/libCore.py:142-144` *does* set `err = True` on a negative chi, so the Mode-B precursor (§3.2) was detected and then thrown away. **No failure is recorded in any data product; the logs are the only record.**
- Log/CSV consistency: `n_rows == n_radii_attempted − 1` (`== n_radii` if finished) holds on **all** 18,432 runs of **each** MOI. The row count is an exact proxy for the death radius.

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

Totals, excluding the 3072 by-design chi_Si>0.12 exits per set:
- margot: 15,360 runs → det(J)==0 10,152 / traceback 4,250 / maxit 700 / finished 258. Zero-row runs 7,166 of 15,360 (46.7%).
- genova: 15,360 runs → det(J)==0 5,874 / traceback 8,281 / maxit 603 / finished 602. Zero-row runs 6,413 of 15,360 (41.8%).

Traceback census, from the authoritative launcher logs only (see §0 trap):
- margot: 4,037 "Factor is exactly singular" (`libCore.py:266`) + 213 `IndexError ... size 400` (`shootp.py` getk2) = 4,250, exactly the stdout-log crash count.
- genova: 7,749 singular LU + 532 IndexError = 8,281.
All of these counts were re-derived independently by the audit and match exactly.

### 1.2 Where in (CMR2, CMC) and at which radius (Fig. 1, Fig. 2, Fig. 3)
- **det(J)==0 at 10 m** (margot S: 367 draws): CMR2 ∈ [0.3505, 0.3753], a sharp threshold at CMR2 ≈ 0.3505 (S+Si 0.05: ≈0.3544). Above it the local Newton variants tried found no S-bearing root at 10 m (§3.3). One genova S case in this class is recovered (`runs/base/034.json`, §3.1), so the threshold is not a proven existence boundary.
- **det(J)==0 at a later radius** (margot S: 474): CMR2 ∈ [0.3244, 0.3505]; death radius 1.0–1.65 Mm (mode 1.1–1.2 Mm margot, 1.5–1.65 Mm genova).
- **Singular-LU crash at 10 m** (margot S: 72; S+Si 0.05: 184; Si: 422; genova S+Si 0.10: 874):
  - S and S+Si: concentrated at the *low*-CMR2 edge (margot S+Si 0.05: mean CMR2 0.329 vs 0.343 for survivors; KS p < 1e-3 for every composition).
  - Si: at the *high*-CMR2 edge (0.359 vs 0.334).
  - For S+Si the zero-row fraction rises monotonically with chi_Si (Fig. 3). More Si lowers the S required, so the 10-m step overshoots to chi_S < 0.
- **Newton maxit**: mostly at later radii. At 10 m it occurs only for Si with CMR2 ∈ [0.3442, 0.3494] (margot 150, genova 17) and for S+Si 0.05 at CMR2 ≈ 0.354 (4).
- **IndexError** crashes: at 1.95 Mm (Si only). The inner core reaches the IndexError condition ricb/rcmb ≥ 0.99875 (`round(400·ricb/rcmb) ≥ 400`, `src/shootp.py:421`, `:475`), with rcmb ≈ 1.92–1.94 Mm.
- Last converged radius distribution (Fig. 2): broad, peak 1.05–1.35 Mm (margot) / 1.4–1.6 Mm (genova); only Si sweeps reach 1.95 Mm.

## 2. HOW — taxonomy (margot counts; genova in parentheses)

| mode | mechanism | count (runs) | typical radius |
|---|---|---|---|
| A. det(J)==0 → `sys.exit` | iterate chi_li_icb ≥ chi_eut → `min(sol, eut)` clamp (`libCore.py:146`) → FD column J[:,4] ≡ 0 | 10,152 (5,874); 3,749 (6) of them at 10 m | 10 m if CMR2 above threshold; else 1.0–1.7 Mm |
| B. `RuntimeError: Factor is exactly singular` | iterate chi_li_icb < 0 (S) or > Si max (Si) → NaN in RK4/EOS → NaN `polyfit` → 797 non-finite entries in A → SuperLU (`libCore.py:266`, no try) | 4,037 (7,749); ≈3,250 (6,388) at 10 m | 10 m, or 1.3–1.7 Mm |
| C. `IndexError` in `getk2` | ricb/rcmb ≥ 0.99875 → nrs ≥ 400 → `rho[k+1]` with k=399 (`shootp.py:475`); can fire with ricb slightly *below* rcmb | 213 (532) | 1.95 Mm |
| D. Newton maxit (12) → `sys.exit` | classifier over 32 sampled cases: period-2 oscillation 9 / irregular 8 / stagnation 7 / slow_decrease 5 / divergence 3; cond(J) 1.9e1–7.3e5 | 700 (603) | mixed |
| E. `error_code` 1/2 rows | dead code (`err` discarded at `shootp.py:131`; `driverp.py:111` always False) | 0 | — |
| F. chi_Si > 0.12 with Edmund → `sys.exit` | by design | 3,072 (3,072) | 10 m |

Mode A dominates margot. Mode B dominates genova, because genova's low CMR2 needs little S and the 10-m step overshoots to chi_S < 0.

## 3. WHY — root causes (fresh, instrumented reproductions on this host)

### 3.1 The failures reproduce off LS6; determinism is not shown for boundary cases
Stratified sample: 108 published runs, 3 per {MOI × composition ∈ {S, Si, S+Si 0.05, S+Si 0.10} × end state × died-at-10-m?}. Only 34 of the 36 strata could be filled with 3 cases. Each case is a full warm-started sweep as in `driverp.py`, with `OMP/OPENBLAS_NUM_THREADS=1` and 16 concurrent processes (`run_batch.py cases.json base`; table `runs_base_analysis.txt`).

**The row count was reproduced exactly in 107/108 runs.** The exception is `runs/base/034.json` (genova S, CMR2=0.32910569, published det(J)==0 at 10 m). A plain re-run took it from **0 to 30 rows**, stopping det(J)==0 at 1.5 Mm. So a 10-m det(J)==0 case is recoverable without any solver change.

The failure mode was reproduced in kind:
- 22/22 "crash at 10 m" → NaN → singular LU here.
- 29/29 det(J)==0 → zero chi column.
- 31/33 maxit → maxit.
- 6/6 Si-at-1.95-Mm crashes → ricb/rcmb ≥ 0.99875 (rcmb 1.92–1.935 Mm, ricb 1.95 Mm).

The re-runs used a different host, Python, numpy and scipy from LS6. "Not LS6-specific" is supported. "Deterministic" is not shown for boundary cases (case 034; the sample is only 3 per stratum).

### 3.2 Mode B (singular LU) — NaN from a chi overshoot; separately, an index wrap-around bug in `getk2` at 10 m
Traces at the crash, for all 22 sampled 10-m crashes:
- The crash comes at iteration 1–2. Typical iterates: S `v=[0.88, 1.94, 0.78, 0.50, −0.063]` (chi_S < 0); Si `v[4]=0.314` (> 0.12 max), or −0.021 / −0.038.
- The RK4 then goes non-finite (`nan_yc=8, nan_rhof=2` in the fluid core), `polyfit` returns NaN coefficients, all 400/400 rho and g in `getk2` are non-finite, and A has 797 non-finite entries. SuperLU reports a NaN matrix as "exactly singular".
- `libCore.py:146` clamps chi only from above, so a negative chi reaches the EOS. `libCore.py:142-144` flags it (`err = True`), but the flag is discarded (§0).
- For finite A, cond(A) is ~3.5e27 (rows scaled by `r[0]^(2l+1) ≈ 1e-27`), but SuperLU and dense LAPACK both solve it. Conditioning is not the trigger.

Separately, **`getk2` has an index wrap-around whenever nrs = round(400·ricb/rcmb) = 0**, i.e. ricb < ~2.5 km, which means only the 10-m radius (`src/shootp.py:421`).
- `r[0]` is set by the fluid-grid loop, and `rho[0]` and `g[0]` are set unconditionally at `:442-443`. The inner-core values themselves are not the defect.
- The defect is the fluid loop at k=0 (`:456-460`). There `k+nrs−1 = −1` wraps to the CMB end, so `g[0]` is rebuilt from the valid `r[399]` and from `g[399]`, which is still uninitialised (`np.empty`, `:426`) because the loop has not reached it yet.
- The `(r[0]³ − r[399]³)/r[0]²` term is a huge, deterministic garbage value even if g were zeroed, and `g[399]` is scaled by `(r[399]/r[0])² ≈ 6e10`.
- **So `np.zeros` alone is not a fix.** It would turn the bug into deterministic wrong values (a silent fallback). The fix is to correct the indexing (e.g. `nrs = max(1, …)`) *and* raise on non-finite g/rho.

Forced-fill experiment on the test's flaky case (margot CMR2=0.33521178639464477, S+Si 0.05, 10 m):
- Fill 0 / 1 / 1e300 / stale value → converged identically. alpha[0] → 0 whenever |g[0]| is large, and xi ≡ 0 at nrs=0 because `BsAs` sums over an empty range.
- **Fill NaN → 797 non-finite entries → "Factor is exactly singular" with no Newton iteration at all.**
- One sampled line-search run showed exactly this signature (`nonfinite_g=400, nonfinite_rho=0, nan_yc=0`).

Heap contents therefore give a **sufficient mechanism, unconfirmed as the cause,** for the run-to-run flip in the fixed-seed test (1 vs 2 singular failures). The flipping run was never captured with its heap contents or a `nonfinite_g` trace.

This bug is *not* the cause of most published 10-m crashes. In the sampled traces, NaN first appears in the RK4 (`nan_yc>0`) with v[4] < 0, before `getk2`. The audit's code review had attributed most 10-m crashes to this bug; the traces contradict that.

Environment: here `/usr/bin/python3` 3.10.12, numpy 1.21.5, scipy 1.8.0, OpenBLAS-pthread; LS6 `/opt/apps/intel19/python3/3.9.7`, scipy 1.6.1.

### 3.3 Mode A (det(J)==0) — chi_li_icb pushed past the eutectic; at later radii no root found near the eutectic
Every det(J)==0 stop has the same shape:
- The FD Jacobian has column 5 (chi_li_icb) identically zero, other column norms O(1), and cond(J) ~1e2 at the previous iterate.
- `getchi_li_grun` clamps `chi_li = min(sol, chi_li_eut)`. Once x[4] ≥ chi_eut(P_icb) (0.13–0.15), the 1e-6 relative perturbation changes nothing.
- Iterates at the stop: x[4] = 0.139 (S, 10 m), 0.18–0.31 (later radii). This is a large overshoot from a converged neighbour 50 km away, consistent with (but not a demonstration of) a fold in ricb.
- The last converged rows before a det(J)==0 death have chi_li_icb/chi_eut median 0.86–0.92 (10th pct 0.54, 90th 0.98; `runs_make_cases.txt`).

**Clamped Newton (x[4] ≤ 0.999·eut, min-norm step on the zero column, line search, maxit 25) recovered 0/29 det(J)==0 cases to a further converged radius.** The best residual floors were |f| = 3e-3…1e-1 (tolerance 1e-6). Other runs did recover this mode:
- the plain re-run of case 034 (0 → 30 radii, §3.1);
- best-of-7 over the variants, which recovered genova S det(J)==0 at 10 m in 1/2 cases (`runs_bias_estimate.txt`).

Verdict: no root found by the local Newton variants tried. A residual floor after local variants shows only that no *nearby* root was found. The missing test is continuation in ricb with fold detection, or a chi_li_icb scan over [0, chi_eut].

### 3.4 Mode D (maxit) — step control, not tolerance
The 32 maxit cases have no single signature. By the classifier in `runs_base_analysis.txt`: 9 period-2, 8 irregular, 7 stagnation, 5 slow_decrease, 3 divergence. cond(J) ranges from 1.9e1 to 7.3e5.

Example of the period-2 subtype (margot Si CMR2=0.347, 10 m, maxit 40): |f| alternates 2.77e-2 ↔ 8.82e-2 with |dx|=0.176 for 40 iterations, cond(J) 60–150. This is an exact period-2 Newton cycle.

Neither eps=1e-5 (3/33 improved, by ≤1 radius) nor maxit=40 (11/33 improved, mostly by 1–3 radii) fixes Mode D. Line search turns it into a residual floor of 1e-3…2e-2 for the 10-m Si cases (CMR2 0.3444–0.3469). No root was found by the local Newton variants tried. This is consistent with the finished Si sweeps ending at CMR2 ≤ 0.3429, but that is not proof of non-existence.

### 3.5 Mode C — geometric limit (ricb/rcmb ≥ 0.99875, which can include ricb slightly below rcmb), but it crashes instead of stopping cleanly.

## 4. VERDICT on "failures are wrong models — discard them"

Not established either way. Some losses are demonstrably numerical, and the rest are unresolved:
- **Later-radius deaths** make up ≈60% of all deaths, and ~all det(J)==0 and IndexError cases fall here.
  - For det(J)==0, no root was found by the local Newton variants tried beyond the radius where chi_li_icb reaches the eutectic.
  - For IndexError, the inner core reaches ricb/rcmb ≥ 0.99875.
  - Recovery attempts gained 0–3 radii (never ≥5) in 63 of 66 sampled later-radius cases.
  - The published rows up to the death radius pass the production tolerance. Whether the truncation is the true branch end is untested (continuation / fold detection / chi scan).
- **10-m det(J)==0 and 10-m Si maxit deaths**:
  - Most sampled cases had no root found by the local Newton variants tried (residual floors ≥3e-3).
  - The class is *not* uniformly unrecoverable. `runs/base/034.json` (genova S, det(J)==0 at 10 m) went 0 → 30 radii on a plain re-run, and genova S det(J)==0 at 10 m was recovered in 1/2 cases.
  - Whether to discard these cases is therefore open.
- **10-m singular-LU crashes are partly numerical**:
  - Best-of-7-variant selection (`bias_estimate.py:12-19`) recovered **13/22** sampled cases to 30–37 radii (`runs_recovered_vs_published.txt`):
    - margot: S 2/3, S+Si 0.05 1/3, S+Si 0.10 2/3, Si 0/3;
    - genova: S 3/3, S+Si 0.05 3/3, S+Si 0.10 2/3, Si 0/1.
  - Backtracking line search alone, the single-method figure, recovered **12/22**.
  - The recovered rows pass the production tolerance (`probe.py:58-66`; spot-check |f| 1e-9 to 1e-11, smooth v(ricb)). But no script checks chi ∈ [0, eut], ricb < rcmb or ρ > 0 over the full recovered sweeps.
  - The per-class population scaling in `runs_bias_estimate.txt` ("est.recoverable") is **withdrawn**. It applies a 1–3-case rate to a whole class.
- **Bias — direction plausible, magnitude unknown.**
  - What holds: the recovered models in the singular-LU (crash_stderr) classes are all no-snow, with smaller cores (rcmb 1.87–1.98 Mm vs published medians 1.96–2.03 Mm) and lower CMR2 than published survivors.
  - The claim does not hold overall. Two snow-bearing recovered classes were left out of the estimate: margot S+Si 0.05 maxit at 10 m (recovered 2/3, snow fraction 0.35) and genova S det(J)==0 at 10 m (recovered 1/2, snow fraction 0.07). Leaving them out biases the estimate toward less snow.
  - Snow is confounded with CMR2. The crashes sit at the low-CMR2 edge, so a per-class rate applied to the whole class is really a CMR2 extrapolation.
  - Each class has n = 1–3 cases per MOI. Clopper–Pearson 95% intervals: 0/3 → [0, 0.71]; 1/3 → [0.008, 0.91]; 1/2 → [0.013, 0.99]; 2/3 → [0.09, 0.99]; 3/3 → [0.29, 1.0].
  - Rows are weighted by recovered sweeps of 30–37 radii against truncated published sweeps, and this weighting is undocumented.
  - **The corrected snow percentages and the corrected CMR2 means previously given here are withdrawn.** The "corrected" columns of `runs_bias_estimate.txt` are kept only as a record of that withdrawn estimate and must not be quoted.
  - **Next step:** settle the question with a full re-run of all 10-m zero-row compositions (margot 7,166, genova 6,413 zero-row runs) under one fixed solver, with bounds and validity checks (chi ∈ [0, eut], ricb < rcmb, ρ > 0, finite g/ρ) on every row.

## 5. Recovery experiments (on the 108-case sample; "more/fewer/same" = rows vs published; full table `runs_bestof.txt`)

| variant | more | fewer | same | comment |
|---|---|---|---|---|
| backtracking line search (halve step while |f| does not decrease, ≤6 halvings) | 20 | 9 | 79 | **recovers 12/22 10-m singular-LU crashes to full sweeps (the single-method figure)**. 9 later-radius cases stop 1–3 radii earlier because it finds a local |f| minimum, so use it with a fallback to the undamped step |
| clamp chi to [1e-4, 0.999·eut] + lstsq on zero column + line search, maxit 25 | 9 | 34 | 65 | together with the other variants adds 1 10-m crash beyond line search (best-of-7 union = 13/22); hurts later radii because clamping fights the fold |
| start at 50 km instead of 10 m | 2 | 0 | 40 | does **not** fix 10-m crashes (same overshoot at 50 km); only avoids the nrs=0 index wrap-around |
| maxit 12 → 40 | 11 | 0 | 22 | +1–3 radii; the maxit cases (9/32 period-2, rest irregular/stagnation/slow/divergent) do not converge |
| FD eps 1e-6 → 1e-5 | 3 | 0 | 30 | negligible |
| cold start (generic v0 every radius) | 15 | 7 | 44 | inconsistent; not a fix |
| dense `np.linalg.solve` in `getpotvsr` | — | — | — | identical result to SuperLU on finite A; irrelevant to the NaN case |
| force nrs ≥ 1 in `getk2` | — | — | — | removes the k+nrs−1 = −1 wrap-around (and with it the read of uninitialised `g[399]`); k2/xi unchanged to solver tolerance |

**Recommended fix (not applied; requirements per audit claim 8):**
1. In `mynewtonSys`, guard the step: reject any iterate with x[4] outside [0, chi_eut(P_icb)] (or > Si max), or with x[2] ≤ ricb, and backtrack (halve) instead. On failure, return `None` *and* have `driverp.py` write a `fail_mode` row. `return None` alone just turns the crash into the same silent truncation at `driverp.py:38`. Replace the exact `det(J)==0` test (`shootp.py:298`), which misses near-singular J, with a conditioning/rank check.
2. Catch `RuntimeError` (SuperLU), `IndexError` and non-finite f per radius, and record each as a `fail_mode`.
3. Restore `err` (`src/libCore.py:142-144` sets it on negative chi; `src/shootp.py:131` discards it) and fix `driverp.py:111` to `(chi_li<0).any()`.
4. In `getk2`, fix the fluid-loop indexing at nrs=0 (e.g. `nrs = max(1, …)`) and raise on non-finite g/ρ. `np.zeros` alone is not a fix, because it would silently produce deterministic wrong values.

Do **not** treat det(J)==0 as "branch ended": case 034 contradicts that. Then re-run all 10-m zero-row compositions under the fixed solver, with bounds and validity checks on every row (§4). No recovery rate is predicted.

## Reproduce
```
S=<scratch>; cp -r PIE/src $S/src_instr; python3 $S/patch_instr.py; python3 $S/patch2.py      # instrumentation, no src/ edits
export PYTHONNOUSERSITE=1 MPLBACKEND=Agg OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python3 $S/probe.py CMR2 CMC {S|Si|S+Si} Edmund chi_Si out.json [only_ricb=10] [cond=1] [k2_fill=NaN|0] [k2_min_nrs=1] [dense=1] [linesearch=1] [clamp_chi=1] [maxit=40] [eps=1e-5] [start_ricb=50010] [cold=1]
python3 $S/inventory.py inventory.json && python3 $S/summarize_inventory.py inventory.json   # published-set census (read-only, ~15 min on the shared FS; authoritative a.log.* only, see §0)
python3 $S/make_cases.py inventory.json cases.json 3; NW=16 python3 $S/run_batch.py cases.json base [probe opts]
python3 $S/analyze_runs.py base ls ...; python3 $S/bestof.py; python3 $S/bias_estimate.py ls clamp clamp_rest start50 maxit40 eps5 cold; python3 $S/figures.py
```
Environment: /usr/bin/python3 3.10.12, numpy 1.21.5, scipy 1.8.0 (SuperLU bundled), BLAS/LAPACK = OpenBLAS-pthread 0.3.x (`/usr/lib/x86_64-linux-gnu/openblas-pthread`), 64-core shared host, load 50–85 during runs (all timings contended, none quoted). Test-flake case: `testsys/e2e/test_published_wide_sweep.py` margot/S+Si/CMR2_0.33521178639464477_CMC_0.43971007578615007 at 10 m. Its failure signature is reproduced by a NaN fill of the uninitialised `g[399]` (§3.2). That mechanism is sufficient but unconfirmed as the cause of the flip.
