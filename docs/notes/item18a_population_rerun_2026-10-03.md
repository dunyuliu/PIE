# Item 18(a) — population-level re-run of the non-finished published MC runs — 2026-10-03

**UNAUDITED — pending priya-nair, not for coauthor communication.**
Regression-class analysis only (PROJECT_RULES rule 5): the published Zenodo
dataset and this re-run are the same code family (v1.0.5 vs v1.6.0 HEAD);
nothing here is an independent truth oracle. No number in this note goes to a
coauthor; the erratum/comment decision stays with the owner (item 18).

Author: dunyu-liu. Scripts and outputs: `item18a_population_rerun_2026-10-03_scripts/`.
Zenodo tree `~/shared_dataset/zenodo.16459292/extracted/PIE` read-only throughout.

## Verdict (pilot stage; main-run section below is filled when the run completes)

Works with caveats. The census is complete and cross-checked; a full
census-level re-run is infeasible on knox (~100 h wall), so a stratified
size-weighted sample of 1,400 runs (93 strata) is running. The pilot already
shows three things a reviewer must know before any before/after number is
read: (i) ~30% of sampled non-finished runs crash the v1.6.0 code with an
*uncaught* `ValueError` before writing a single row; (ii) the re-run is not a
superset of the published run — 259 of 783 radii the published v1.0.5 code
converged on fail in v1.6.0; (iii) on 1 of 95 recovered rows the warm-start
sweep and the cold-start single-radius solver converge to different Newton
roots (chi_Si_icb 0.11 vs 0.22, isnow 2 vs 0).

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
- Pilot runs stay in the main frame: `robust_runner` sentinels resume them
  for free; the 20 crashed ones re-crash (~80 s each).

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

Pilot cross-check (100 recovered admissible rows, 4 workers, mean 4.4 s per
cold solve): 95/100 reconverge cold; 94 of those agree with the warm row to
|dchi_li_icb| < 1e-6 and 93/95 agree on isnow. Exceptions: 5 cold failures
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
`/home/utig5/dliu/PIE/.venv/bin/python3` 3.12.15, numpy 2.5.3, scipy 1.18.1
(pins match), `PYTHONPATH=<worktree>` so `pie` resolves to the worktree.
Commands: `design.py pilot --n 72 --seed 20261003`;
`PIE_WORKERS=24 python3 pie/robust_runner.py run <pilot_manifest.csv> --status-log pie/results/pilot_status.jsonl --timeout 3600`
(PID 1238329, 19:46 CDT); `design.py main --n 1400 --min 8 --seed 20261004`;
same runner command on `main_manifest.csv`, `--status-log pie/results/main_status.jsonl --timeout 1200` (20:14 CDT).

### 3.1 Pilot findings (fresh, `pilot_snowfraction.json`, `pilot_rerun_rows.json`)

| quantity | value |
|---|---|
| sampled / finished within 27 min | 72 / 67 |
| **re-run crashed, no csv** | **20/67** — all `ValueError: All components of the initial state y0 must be finite` from `scipy.integrate.solve_ivp` at `pie/shootp.py:117` (`shoot_mercmodel`), via `mercmodel_trial` (`shootp.py:301`). `pie/driverp.py` catches only `lc.SolverError` (lines 171-204), so the process dies before the first row; robust_runner records PROCESS_CRASHED, writes no sentinel. Hits S+Si 19, S 1; spread over modes detJ0 10, crash 8, maxit 2 and all stages. |
| pre-stop rows (radii the published run reached), 47 runs | 783; max rel diff chi_li_icb/rcmb vs published 1.2e-4; isnow mismatches 0; **259 failed in the re-run** (v1.6.0 is not a superset of v1.0.5 on these runs) |
| beyond-stop radii | 1,097; error codes 4 CHI_OUTSIDE_BOX 853, 0 CONVERGED 100, 3 NONFINITE_SHOOT 73, 5 RICB_GE_RCMB 43, 1 NEWTON_MAXIT 28 |
| converged = admissible | 100 (code 4 already excludes outside-box rows); warm 96, cold-fallback 4; in 19 of 47 runs |
| snow-bearing among them | 8 (genova S+Si 0.09 x2, genova S x3, margot S+Si 0.05 x1, margot S+Si 0.02 x2); all at ricb >= 1,400 km |
| by mode (runs / beyond / converged / snow) | detJ0 32/473/37/2; crash_lt 24/457/15/3; newton_maxit 8/164/48/3; crash_at_1.95Mm 3/3/0/0 |
| Si-only runs in the pilot | 4: two `crash_at_1.95Mm` (1 radius beyond, code 5), two `newton_maxit` at 10 m (39 x code 4, 1 x code 5) — zero converged Si rows |

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

**Pending main-run completion.** The table lands in a follow-up commit on
this branch; at the pilot level (not population-weighted, n too small per
stratum) the direction is: ~9% of beyond-stop radii recover, ~8% of those
are snow-bearing, so added snow rows are in the hundreds against 474,075
published rows — deltas at the 0.0x pp level, consistent with the
predecessor's +0.05 pp maximum.

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

Does the re-run change the answer? Pilot: 0 converged Si rows beyond the
stop (4 runs). Main run: see section 4's table and
`main_snowfraction.json::si_only_admissible_snow_runs` (filled on
completion). Mechanistically the answer cannot change: an admissible Si row
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

- The 20/67 uncaught-`ValueError` crash class: a v1.6.0 robustness gap, not
  a physics result; route to lars-eriksson (bug) — not fixed here (read-only).
  Those runs contribute zero recoveries, biasing A and S low.
- 259/783 pre-stop rows that v1.0.5 converged but v1.6.0 does not: the
  "after" dataset is not published + additions; a true re-publication would
  change existing rows too. This note only adds rows (as the brief asked).
- Root non-uniqueness (1/95 rows): recovered rows depend on the start.
- Long-tail jobs cut at 1,200 s lose their upper radii (counted as zero).
- 7 strata with N_h < 10 and the pilot's per-stratum n: direction only.
- Same-code-family comparison; no independent oracle (rule 5).
