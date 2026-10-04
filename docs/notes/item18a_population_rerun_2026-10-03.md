# Item 18(a) — population-level re-run of the non-finished published MC runs — 2026-10-03

**UNAUDITED — pending priya-nair, not for coauthor communication.**
Regression-class analysis only (PROJECT_RULES rule 5): the published Zenodo
dataset and this re-run are the same code family (v1.0.5 vs v1.6.0 HEAD);
nothing here is an independent truth oracle. No number in this note goes to a
coauthor; the erratum/comment decision stays with the owner (item 18).

Author: dunyu-liu. Scripts and outputs: `item18a_population_rerun_2026-10-03_scripts/`.
Zenodo tree `~/shared_dataset/zenodo.16459292/extracted/PIE` read-only throughout.

## Verdict

Works with caveats. Census complete and cross-checked; full census-level
re-run infeasible on knox (~100 h wall), so a stratified size-weighted sample
of 1,400 runs (93 strata) was re-run in 4.2 h. Population-scaled result
(section 4): the discarded runs add an estimated ~18,000 admissible rows
(+3.8% on 474,075) and ~2,600 snow rows; **margot** snow fractions move
**down** by 0.2–1.0 pp in every composition (CI95 excludes zero for S+Si
0.01, 0.04, 0.06, 0.07, 0.11, and the zero-snow classes S+Si 0.00/0.12);
**genova** S and low-chi S+Si move by |delta| <= 0.3 pp, while genova S+Si
>= 0.05 moves **up** by +0.5 to +10 pp with CIs mostly including zero
(small published denominators of 2,000–19,000 rows; 101 of the 135 recovered
snow rows sit at ricb >= 1,750 km, next to the geometric limit). Si-only
admissible snow fraction stays exactly 0 (20 recovered admissible Si rows,
none snow-bearing). Three things a reviewer must know before any of these
numbers is read: (i) 326 of 1,400 sampled runs (23%) crash the v1.6.0 code with an
*uncaught* `ValueError` at radius index 31–37 (ricb 1.55–1.85 Mm), losing
the rest of the sweep; (ii) the re-run is not a superset of the published
run — 6,964 of 23,608 radii (30%) the published v1.0.5 code converged on
fail in v1.6.0; (iii) the warm-start sweep and the cold-start single-radius
solver disagree on 28 of 977 recovered rows (different Newton roots,
|dchi| up to 0.38), and 20 of the 135 recovered snow rows are "no snow" when
solved cold — the recovered snow rows are start-dependent.

## 1. Census (deliverable 1) — `census.py` -> `census_runs.csv`, `census_summary.json`

Derived directly from the 2,048 stdout logs (`results/log.<CMR2>.<CMC>.txt`,
18 segments each) and csv row counts; not inherited from earlier notes.
Classification reused from `failure_analysis_2026-09-28_scripts/inventory.py`.

| quantity | value |
|---|---|
| runs (2 MOI x 1024 draws x 18 compositions) | 36,864 |
| finish | 860 |
| si_exceed (Mode F, by design, chi_Si > 0.12) | 6,144 |
| **non-finished, excl. si_exceed (sampling frame)** | **29,860** = margot 15,102 + genova 14,758 |
| by mode: detJ0 (A) / crash_lt_1.95Mm (B or C-on-iterate) / newton_maxit (D) / crash_at_1.95Mm (C candidates) | 16,026 / 12,028 / 1,303 / 503 |
| by stage (last attempted radius): 10 m / 50 km–1.45 Mm / >= 1.5 Mm | 13,579 / 9,649 / 6,632 |
| radii beyond the published stop (40-radius sweep) | 754,725 |
| published rows (all csvs) | 474,075 (margot 201,633 + genova 272,442; matches `published_census.json`) |
| log-vs-csv row-count mismatches | 0 |

Cross-check: crash runs in the stdout logs equal singular + IndexError
tracebacks in the launcher stderr logs for both MOIs (margot 4,250 =
4,037 + 213; genova 8,281 = 7,749 + 532); the script fails otherwise.

**Mode B vs C cannot be attributed per run from the published artefacts.**
The stderr log has no per-run identity, and the `last_r == 1.95 Mm` proxy
gives 129/374 runs vs 213/532 IndexErrors: the getk2 IndexError fires on a
Newton *iterate's* rcmb, so Mode C also hits at earlier radii. The ricb/rcmb
ratio gives no clean separation either (boundary ~0.85). Kept as
`crash_at_1.95Mm` / `crash_lt_1.95Mm`; only the re-run's per-radius
`error_code` can attribute them (and in the pilot, code 3 NONFINITE_SHOOT
appears on 73 of 1,097 beyond-stop radii).

Per-(MOI, composition, mode, stage) counts: `census_summary.json`
(`per_moi_composition`); S+Si 0.00 and 0.12 and Si/S included.

## 2. Sizing decision (deliverable 2) — `design.py` -> `pilot_*`, `main_*`

Pilot (72 runs, strata (moi, mode, stage), proportional, seed 20261003):
wall per job **mean 217 s, median 224 s, p90 364 s, max 463 s** over the 67
jobs that finished inside 27 min; 5 further jobs were still running at
>20–27 min (one had 29 of 40 radii after 27 min, all `error_code 4`, ~56 s
per radius). Contended: 24 workers on 64 cores, load 2.4 before launch,
~25 during. That is ~5.4 s/radius, 2x the ~2.6 s/radius reference, because
failing radii (Newton maxit + cold fallback) cost more than converged ones.

- Full census-level re-run: 29,860 jobs x ~285 s (mean with a 1,200 s
  timeout on the long tail) / 24 workers = **~98 h wall**. Infeasible for
  this mission; also pointless at that precision given the result below.
- Main sample: **1,400 runs**, strata = (moi, composition, mode) = 93
  strata, proportional allocation with floor 8 (largest-remainder rounding,
  seed 20261004, `--timeout 1200`) = ~4.6 h wall at the pilot rate. Stage
  dropped as an allocation variable: admissible recoveries are rare events
  (100 of 1,097 beyond-stop radii in the pilot, 8 snow-bearing), so precision
  is set by runs per composition; (moi, composition, mode, stage) would be
  400+ strata whose floor alone exceeds the budget. Stage is kept in
  `main_sample.csv` as a descriptive variable. 6/93 strata are fully
  enumerated; 7 strata have N_h < 10 (direction only).
- Pilot runs stay in the main frame: `robust_runner` sentinels resume the 47
  complete ones for free; the 25 partial ones (no sentinel) are re-run.

## 3. Methodology statement (deliverable 3)

Two solvers are in play and the choice is explicit:

- **Production path (what the re-run uses):** `pie/robust_runner.py` ->
  `python -m pie p ...` -> `pie/driverp.py` sweep, v1.3.0 policy:
  warm start from the last converged `v`, cold fallback from `param['v0']`,
  continue after failure, one row per radius with `error_code`. Chosen
  because it yields exactly the csv schema (isnow, chi_li_icb,
  chi_li_eut_icb, error_code, start) the stage-3/4 code consumes, and it is
  what a future production re-run would be.
- **Cold-start single-radius solver** (`testsys/pielib.py::solve_full_model`,
  the 2026-10-03 note's method) is run as a cross-check on every recovered
  admissible row (`coldcheck.py`). The task brief asked for the cold-start
  methodology *and* for the robust_runner workflow; those are different
  solvers, so this note runs the production path and bridges with the
  cross-check rather than silently picking one. Disagreement is recorded
  here, not acted on.

Pilot cross-check (113 recovered admissible rows, 4 workers, mean ~4.4 s per
cold solve): 108/113 reconverge cold; 107 of those agree with the warm row to
|dchi_li_icb| < 1e-6 and 106/108 agree on isnow. Exceptions: 5 cold failures
(`SolverError`; warm-start-only recoveries, same class as the 39th row of the
predecessor note); 1 row (genova S+Si 0.09, ricb 1,900 km) converges to a
*different root* (warm chi_Si_icb 0.1105, isnow 2; cold 0.2179, isnow 0;
both inside the admissible box) and 1 row (genova S, 1,450 km) differs in
snow class 3 vs 2 at the same chi. Non-uniqueness of the Newton root is a
real caveat for any recovered row.

Resumability verified: sentinel `.runner_done_<chi>.json` per job
(`pie/robust_runner.py:364-380`); crashed/timeout jobs get no sentinel and
are retried on resume.

Rule-15 compliance: `uptime` immediately before each launch (pilot load 2.36,
main 6.25), `PIE_WORKERS=24` = min(24, (64-1-load)//2), `nice -n 10`, one
BLAS thread per worker (robust_runner `_child_env`). During the first ~30 min
of the main run 5 pilot stragglers were still running (29 solver processes,
load ~32 on 64 cores) — a transient 5 over the cap, noted here.

Provenance: host knox (64 cores), worktree HEAD `d7d9941` (origin/main; the
scripts are uncommitted additions, so the runner records `git_src_dirty`),
`<repo>/.venv/bin/python3` 3.12.15, numpy 2.5.3, scipy 1.18.1
(pins match), `PYTHONPATH=<worktree>` so `pie` resolves to the worktree.
Commands: `design.py pilot --n 72 --seed 20261003`;
`PIE_WORKERS=24 python3 pie/robust_runner.py run <pilot_manifest.csv> --status-log pie/results/pilot_status.jsonl --timeout 3600`
(PID 1238329, 19:46 CDT); `design.py main --n 1400 --min 8 --seed 20261004`;
same runner command on `main_manifest.csv`, `--status-log pie/results/main_status.jsonl --timeout 1200` (20:14 CDT).

### 3.1 Pilot findings (fresh, `pilot_snowfraction.json`, `pilot_rerun_rows.json`)

| quantity | value |
|---|---|
| sampled / completed 40 radii / partial | 72 / 47 / 25 (20 crashed mid-sweep, 5 hit the 3,600 s timeout at 29–37 radii) |
| **re-run crashed mid-sweep** | **20/72** — all `ValueError: All components of the initial state y0 must be finite` from `scipy.integrate.solve_ivp` at `pie/shootp.py:117` (`shoot_mercmodel`), via `mercmodel_trial` (`shootp.py:301`), at radius index 31–37 (ricb 1.55–1.85 Mm). `pie/driverp.py` catches only `lc.SolverError` (lines 171-204), so the process dies and the remaining 3–9 radii are never attempted; robust_runner records PROCESS_CRASHED with `n_rows 0` (it does not read the csv on a non-zero return code, hiding the 31–37 rows that were written) and writes no sentinel, so a resume re-runs the whole job. Hits S+Si 19, S 1; modes detJ0 10, crash 8, maxit 2; all stages. Rows the crashed jobs did write are analysed; the lost radii count as zero. |
| pre-stop rows (radii the published run reached), 72 runs | 1,153; max rel diff chi_li_icb/rcmb vs published 2.9e-4; isnow mismatches 0; **335 failed in the re-run** (v1.6.0 is not a superset of v1.0.5 on these runs) |
| beyond-stop radii attempted | 1,584 (of 1,763 in the sample); error codes 4 CHI_OUTSIDE_BOX 1,307, 0 CONVERGED 113, 3 NONFINITE_SHOOT 83, 5 RICB_GE_RCMB 43, 1 NEWTON_MAXIT 35, 2 SINGULAR_JACOBIAN 3 |
| converged = admissible | 113 (code 4 already excludes outside-box rows); in 25 of 72 runs |
| snow-bearing among them | 8 (genova S+Si 0.09 x2, genova S x3, margot S+Si 0.05 x1, margot S+Si 0.02 x2); all at ricb >= 1,400 km |
| wall per job incl. the 5 timeouts | mean 452 s, median 232 s, p90 396 s (`pilot_snowfraction.json`) |
| Si-only runs in the pilot | 4: two `crash_at_1.95Mm` (1 radius beyond, code 5), two `newton_maxit` at 10 m (39 x code 4, 1 x code 5) — zero converged Si rows |

### 3.2 Main run (fresh, `main_snowfraction.json`, `main_rerun_rows.json`, `main_coldcheck.json`)

| quantity | value |
|---|---|
| wall | **4.22 h** (20:14:35 → 00:27:43 CDT, 2026-10-03/04), 1,397 jobs ran + 3 resumed from pilot sentinels; per job mean 259 s, median 206 s, p90 412 s (contended: 24 workers, load ~27 on 64 cores; plus 5 pilot stragglers for the first 30 min) |
| completion | 1,400/1,400 analysed: 1,022 full 40-radius sweeps; **326 mid-sweep `ValueError` crashes** (rows reached 25–38, median 34); 52 timeouts at 1,200 s (rows reached 26–37); 1 job `SKIPPED_LOCKED` (held by a pilot straggler; its pilot partial csv, 29 rows, is what is analysed) |
| pre-stop rows | 23,608 in 875 runs; isnow mismatches 0; 865/875 runs agree to rel diff < 1e-3 on chi_li_icb/rcmb, 10 runs do not (6 < 1e-2, 3 < 1, one genova S+Si 0.03 newton_maxit run at rel diff 45 = a different root on a pre-stop radius); **6,964 pre-stop radii (30%) fail in v1.6.0** |
| beyond-stop radii attempted | 30,169 (of ~35,500 in the sample); codes 4 CHI_OUTSIDE_BOX 25,727, 3 NONFINITE_SHOOT 1,674, 0 CONVERGED 1,098, 5 RICB_GE_RCMB 886, 1 NEWTON_MAXIT 748, 2 SINGULAR_J 36 |
| converged = admissible | **1,098 (3.6%)** in 576 of 1,400 runs; warm 949, cold-fallback 149 |
| snow-bearing | **135** (12% of recovered); by ricb: < 750 km 32, 1.25–1.5 Mm 2, **>= 1.75 Mm 101** |
| by mode (runs / beyond / conv / snow) | detJ0 596/10,127/211/0; crash_lt_1.95Mm 512/16,069/463/102; newton_maxit 257/3,938/424/33; crash_at_1.95Mm 35/35/0/0 (all code 5: the Mode-C candidates are at the geometric limit, nothing to recover) |
| cold-start cross-check (1,098 rows, 16 workers, 5.9 s/solve) | 977 reconverge; 942 agree to |dchi| < 1e-6, 7 to < 1e-3, **28 to a different root** (max |dchi| 0.38; 1 of them cold-inadmissible); isnow agrees on 950/977; **20 warm snow rows are cold no-snow**, 0 the other way; 121 cold failures (`SolverError`, warm-start-only recoveries) |

## 4. Before/after snow fraction (deliverable 4) — `snowfraction.py main` -> `main_table.md`, `main_snowfraction.json`

Method (stages 3/4 of `resolve_and_census.py`, code imported not re-typed):
published census per (moi, composition) re-derived from the raw csvs and
asserted equal to `published_census.json`; re-run rows beyond the published
stop with `error_code == 0` and `is_admissible` (chi in [0, chi_li_eut_icb]
for S/S+Si, [0, max_Si=0.12] for Si); stratified totals A (added admissible
rows) and S (added snow rows) with design weights N_h/n_h and a stratified
normal CI95 (per-run variance, finite-population correction); after =
(pub_snow + S)/(pub_rows + A) for both denominators (all published rows;
admissible-only published rows). Crashed re-runs contribute zero.

Reading the table (`main_table.md`, reproduced below): `n/N` = sampled runs
over non-finished runs in that (moi, composition); "(k/m strata n<10)" flags
strata that are direction-only; A and S are population totals (weighted);
the delta CI propagates the variance of S only (A treated as fixed, so
zero-snow classes show a degenerate CI); both denominators as in the
predecessor note. Population totals: **A ≈ 18,310 added admissible rows
(+3.9% on 474,075), S ≈ 2,580 added snow rows.** Numbers below are
weighted estimates from 1,400 sampled runs, truncated by the 326 crashes and
52 timeouts (which bias A and S low, mostly at ricb >= 1.55 Mm — exactly
where the snow rows concentrate).

| moi/composition | published rows | before isnow>0 | sampled runs n/N | sample: beyond/conv/adm/snow | est. added adm A [CI95] | est. added snow S [CI95] | after | delta (pp) [CI95] | before adm-only | after adm-only | delta (pp) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| genova/S | 27545 | 0.1517 | 50/1024 (2/4 strata n<10) | 502/18/18/0 | 312 [184, 440] | 0 [0, 0] | 0.1500 | -0.170 [-0.170, -0.170] | 0.1774 | 0.1750 | -0.232 |
| genova/S+Si_0.00 | 27492 | 0.1517 | 50/1024 (2/4 strata n<10) | 566/26/26/0 | 500 [350, 650] | 0 [0, 0] | 0.1490 | -0.271 [-0.271, -0.271] | 0.1774 | 0.1737 | -0.369 |
| genova/S+Si_0.01 | 27676 | 0.1128 | 47/1024 (1/3 strata n<10) | 603/21/21/1 | 429 [283, 574] | 17 [0, 50] | 0.1117 | -0.111 [-0.172, +0.005] | 0.1403 | 0.1384 | -0.190 |
| genova/S+Si_0.02 | 27126 | 0.0875 | 48/1024 | 626/26/26/4 | 503 [303, 702] | 78 [0, 180] | 0.0888 | +0.124 [-0.159, +0.492] | 0.1187 | 0.1196 | +0.091 |
| genova/S+Si_0.03 | 25730 | 0.0686 | 48/1024 | 723/23/23/2 | 433 [278, 588] | 43 [0, 99] | 0.0691 | +0.051 [-0.114, +0.266] | 0.1006 | 0.1005 | -0.003 |
| genova/S+Si_0.04 | 23335 | 0.0547 | 47/1024 (1/3 strata n<10) | 711/35/35/2 | 744 [115, 1374] | 47 [0, 108] | 0.0550 | +0.025 [-0.169, +0.281] | 0.0872 | 0.0860 | -0.117 |
| genova/S+Si_0.05 | 18901 | 0.0488 | 47/1024 (1/3 strata n<10) | 776/33/33/5 | 797 [538, 1057] | 133 [7, 259] | 0.0536 | +0.478 [-0.161, +1.117] | 0.0793 | 0.0849 | +0.562 |
| genova/S+Si_0.06 | 16219 | 0.0412 | 47/1024 (1/3 strata n<10) | 939/68/68/6 | 933 [539, 1326] | 144 [11, 278] | 0.0474 | +0.618 [-0.162, +1.398] | 0.0712 | 0.0787 | +0.756 |
| genova/S+Si_0.07 | 12695 | 0.0372 | 47/1024 (1/3 strata n<10) | 1036/53/53/6 | 1132 [700, 1563] | 178 [29, 326] | 0.0470 | +0.979 [-0.094, +2.053] | 0.0661 | 0.0785 | +1.242 |
| genova/S+Si_0.08 | 9482 | 0.0349 | 47/1024 (1/3 strata n<10) | 1135/48/48/6 | 989 [542, 1436] | 182 [0, 394] | 0.0490 | +1.409 [-0.330, +3.432] | 0.0637 | 0.0829 | +1.925 |
| genova/S+Si_0.09 | 6909 | 0.0307 | 48/1024 (1/3 strata n<10) | 1103/51/51/9 | 1073 [650, 1496] | 272 [20, 524] | 0.0606 | +2.994 [-0.167, +6.156] | 0.0597 | 0.1046 | +4.495 |
| genova/S+Si_0.10 | 4864 | 0.0288 | 47/1024 (1/3 strata n<10) | 1210/41/41/10 | 896 [459, 1332] | 311 [34, 588] | 0.0783 | +4.953 [+0.148, +9.757] | 0.0587 | 0.1375 | +7.878 |
| genova/S+Si_0.11 | 3058 | 0.0271 | 46/1024 (2/3 strata n<10) | 1116/34/34/3 | 728 [316, 1140] | 95 [0, 197] | 0.0470 | +1.987 [-0.522, +4.684] | 0.0563 | 0.0808 | +2.453 |
| genova/S+Si_0.12 | 1980 | 0.0273 | 40/1024 (1/2 strata n<10) | 1207/27/27/9 | 693 [307, 1080] | 284 [49, 519] | 0.1264 | +9.914 [+1.138, +18.691] | 0.0541 | 0.1998 | +14.571 |
| genova/Si | 39430 | 0.0043 | 30/422 (2/3 strata n<10) | 308/20/20/0 | 109 [0, 272] | 0 [0, 0] | 0.0043 | -0.001 [-0.001, -0.001] | 0.0000 | 0.0000 | +0.000 |
| margot/S | 13168 | 0.3852 | 49/1024 (2/4 strata n<10) | 1208/27/27/7 | 387 [171, 603] | 84 [0, 168] | 0.3804 | -0.480 [-1.097, +0.137] | 0.4504 | 0.4426 | -0.775 |
| margot/S+Si_0.00 | 13109 | 0.3863 | 49/1024 (2/4 strata n<10) | 1358/23/23/0 | 295 [157, 433] | 0 [0, 0] | 0.3778 | -0.851 [-0.851, -0.851] | 0.4506 | 0.4391 | -1.153 |
| margot/S+Si_0.01 | 13208 | 0.3563 | 47/1024 (1/3 strata n<10) | 1148/26/26/5 | 454 [266, 642] | 68 [0, 155] | 0.3494 | -0.689 [-1.185, -0.047] | 0.4118 | 0.4017 | -1.004 |
| margot/S+Si_0.02 | 13373 | 0.3276 | 48/1024 (1/3 strata n<10) | 1335/29/29/7 | 511 [266, 755] | 100 [16, 185] | 0.3228 | -0.482 [-1.091, +0.126] | 0.3817 | 0.3738 | -0.789 |
| margot/S+Si_0.03 | 13291 | 0.3038 | 47/1024 (1/3 strata n<10) | 1203/38/38/9 | 488 [294, 681] | 87 [22, 151] | 0.2993 | -0.447 [-0.916, +0.022] | 0.3495 | 0.3425 | -0.697 |
| margot/S+Si_0.04 | 13412 | 0.2809 | 48/1024 (1/3 strata n<10) | 1232/44/44/6 | 617 [369, 864] | 35 [0, 79] | 0.2710 | -0.987 [-1.235, -0.675] | 0.3267 | 0.3130 | -1.373 |
| margot/S+Si_0.05 | 13195 | 0.2634 | 48/1024 (1/3 strata n<10) | 1337/30/30/3 | 288 [144, 432] | 39 [0, 84] | 0.2606 | -0.277 [-0.563, +0.061] | 0.3047 | 0.3005 | -0.421 |
| margot/S+Si_0.06 | 13266 | 0.2467 | 48/1024 (1/3 strata n<10) | 1138/29/29/2 | 393 [184, 603] | 8 [0, 18] | 0.2402 | -0.648 [-0.710, -0.578] | 0.2856 | 0.2768 | -0.876 |
| margot/S+Si_0.07 | 13268 | 0.2337 | 47/1024 (1/3 strata n<10) | 1173/44/44/4 | 631 [356, 905] | 30 [0, 72] | 0.2253 | -0.843 [-1.061, -0.543] | 0.2712 | 0.2595 | -1.167 |
| margot/S+Si_0.08 | 13143 | 0.2221 | 47/1024 (1/3 strata n<10) | 1061/69/69/13 | 1102 [706, 1498] | 116 [0, 246] | 0.2130 | -0.907 [-1.718, +0.011] | 0.2570 | 0.2435 | -1.345 |
| margot/S+Si_0.09 | 12993 | 0.2107 | 48/1024 (1/3 strata n<10) | 976/51/51/8 | 508 [278, 739] | 85 [0, 212] | 0.2090 | -0.165 [-0.793, +0.778] | 0.2421 | 0.2389 | -0.323 |
| margot/S+Si_0.10 | 13017 | 0.1990 | 48/1024 (1/3 strata n<10) | 1045/52/52/5 | 867 [509, 1224] | 71 [0, 197] | 0.1917 | -0.730 [-1.242, +0.179] | 0.2305 | 0.2199 | -1.063 |
| margot/S+Si_0.11 | 13280 | 0.1866 | 48/1024 (1/3 strata n<10) | 1113/62/62/3 | 931 [542, 1319] | 70 [0, 166] | 0.1793 | -0.733 [-1.222, -0.051] | 0.2200 | 0.2089 | -1.109 |
| margot/S+Si_0.12 | 13163 | 0.1813 | 48/1024 (1/3 strata n<10) | 1092/50/50/0 | 568 [239, 897] | 0 [0, 0] | 0.1738 | -0.750 [-0.750, -0.750] | 0.2097 | 0.1997 | -0.997 |
| margot/Si | 16747 | 0.0376 | 41/766 | 1189/0/0/0 | 0 [0, 0] | 0 [0, 0] | 0.0376 | +0.000 [+0.000, +0.000] | 0.0000 | 0.0000 | +0.000 |

Interpretation (regression-class, UNAUDITED): the recovered rows are mostly
no-snow (88%), so wherever the published snow fraction is high (margot,
0.18–0.39) adding them dilutes it: margot moves down by 0.2–1.0 pp
everywhere. Where the published fraction is low and the denominator small
(genova S+Si >= 0.08, 2,000–9,500 rows) a few dozen recovered snow rows at
ricb >= 1.75 Mm raise it by several pp with wide CIs. Against the 2026-10-03
note's 39-row result (max +0.05 pp) this is the population-scale answer:
magnitudes of order 1 pp, direction composition-dependent, not negligible
for margot — but 20/135 of the snow rows are start-dependent (section 3.2),
so the genova upticks in particular should not be quoted without the
cold-start caveat.

## 5. Si-only admissible-zero question

Published Si rows: margot 16,747 (snow 630; chi_li_icb > 0.12: 885; < 0:
3,382), genova 39,430 (snow 170; > 0.12: 617; < 0: 4,590). **Every published
Si snow row has chi_li_icb < 0** (margot range [-0.1275, -0.0483]; genova
[-0.0697, -0.0491]), all at ricb 10 m – ~1.5 Mm; rows with chi > 0.12 have
snow fraction 0. Hence admissible-only Si snow fraction = 0 exactly.

Mechanism (read-only, file:line at HEAD `d7d9941`):
- `pie/libCore.py:238-250` (`getchi_li_grun`, `el == 'Si'`): the eutectic
  stand-in is `chi_li_eut = max_Si_Edmund2022`, and the root is clamped only
  from above, `chi_li = min(sol.x[0], chi_li_eut)`; a negative root just sets
  `err = True`. The liquidus root along the adiabat is therefore allowed to go
  negative in the fluid core.
- `pie/shootp.py:201-214`: `isnow = 1` when `chi_li[-1] - chi_li_icb >
  1e-10`, i.e. snow requires chi *increasing outward*; classes 2/3 refine
  where the increase starts. For Si the Edmund liquidus slope makes chi
  increase outward only when the ICB value is low; with no lower bound the
  Newton solve lands on negative chi_Si_icb for exactly those models.
- `pie/shootp.py:305-357` (`mercmodel_box`): the v1.3.0 line search bounds
  chi from above (eutectic / max_Si) and rejects rcmb <= ricb, but
  `CHI_MIN = None` (line 357) disables the lower bound by default (lines
  315, 342-343), so v1.6.0 can still *converge* to negative chi_Si_icb; the
  row is then tagged `error_code 4` by `pie/driverp.py:288`
  (`chi_li < 0` → CHI_OUTSIDE_ADMISSIBLE_BOX) and excluded as inadmissible.

Does the re-run change the answer? **No.** Main run: 71 Si runs sampled,
1,497 beyond-stop radii attempted, 20 converged (all genova, ricb 1.1–1.65
Mm, chi_Si_icb 0.0014–0.022, inside the box), **0 snow-bearing**; margot Si
recovered nothing (`main_snowfraction.json::si_only_admissible_snow_runs`
is empty). Admissible-only Si snow fraction stays exactly 0 in both MOIs.
Mechanistically the answer cannot change: an admissible Si row
needs 0 <= chi_Si_icb <= 0.12, and in that range the Edmund Si liquidus along
the adiabat does not produce chi increasing outward in any published row,
so `isnow` stays 0. Whether the negative-chi snow rows are "real" is a
physics question for rafael-santos, not settled here.

## 6. Tried and rejected

| Approach | Why rejected | Evidence |
|---|---|---|
| Mode C per-run attribution via `last_r == 1.95 Mm` | undercounts 129/374 vs 213/532 launcher IndexErrors; getk2 index fires on Newton iterates | `census.py` docstring, `probe_modeC` scratch (ratio boundary ~0.85, no separation) |
| Full census-level re-run (29,860 jobs) | ~98 h wall at 24 workers; recoveries are rare so a sample suffices | pilot timing above |
| Strata (moi, composition, mode, stage) | 400+ strata, floor alone > budget | `design.py` docstring |
| Cold-start-only methodology for the production run | would need a new sweep harness and would not produce robust_runner csvs; used as cross-check instead | section 3 |

## 7. What a reviewer would attack

- The 20/72 uncaught-`ValueError` crash class (and robust_runner's `n_rows 0`
  on a non-zero return code): v1.6.0 robustness gaps, not physics results;
  route to lars-eriksson (bug) — not fixed here (read-only). The lost upper
  radii contribute zero recoveries, biasing A and S low.
- 335/1,153 pre-stop rows that v1.0.5 converged but v1.6.0 does not: the
  "after" dataset is not published + additions; a true re-publication would
  change existing rows too. This note only adds rows (as the brief asked).
- Root non-uniqueness (28/977 recovered rows, 20/135 snow rows, and one
  pre-stop run at rel diff 45): recovered rows depend on the start; the
  genova high-chi upticks rest on a few dozen such rows.
- 52 jobs cut at 1,200 s and 326 crashed mid-sweep lose their upper radii
  (counted as zero) — where the snow rows are.
- The delta CI propagates only the variance of S (A fixed); zero-snow
  classes show a degenerate CI. A proper ratio-estimator CI would be wider.
- Per-composition n is 40–50 runs over 2–4 strata; strata with n<10 are
  flagged and are direction-only.
- 7 strata with N_h < 10 and the pilot's per-stratum n: direction only.
- Same-code-family comparison; no independent oracle (rule 5).
