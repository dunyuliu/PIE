# Item 31c -- direct sampling of error_code 1/2 across the full matched-prestop population

Status: **analysis complete, read-only** (no `pie/` solver/policy code touched).
Follow-on to item31b (`item31b_nonbox_differential_2026-10-04.md`, PR #82,
AUDITED-PASS), which found error codes 1 (NEWTON_MAXIT) and 2
(SINGULAR_JACOBIAN) almost entirely absent from a 864-row matched-prestop
subset (1/864 code-1, 0/864 code-2). This note was commissioned to sample
~30 rows of each code directly from the *full* rerun population rather than
one subset, classify each against HEAD's own acceptance rules, and report the
paper's `sort_models` filter survival.

**Headline result:** the matched-prestop population (v1.0.5-converged roots
that also have a HEAD csv row at the same radius) contains **exactly 3
error_code==1 instances and 0 error_code==2 instances, full stop** -- this is
an **exhaustive census of all 306 compositions with `prestop_rerun_failed>0`**,
not a sample, so "sample ~30 per code" was structurally unreachable: there are
not 30 code-1 rows to draw from anywhere in this comparison method's domain.
All 3 code-1 instances classify as HEAD-over-constrains (type a); none survive
`sort_models`' filters (NaN diagnostics on non-converged rows, see below).

## Hard precondition: liquidus plumbing in the verifier

`verify_v105_root_v2.py` (item31, audited by lars-eriksson) hardcoded
`liquidus_eq='Edmund'`. Before any new sampling, built
`docs/notes/item31_v1.0.5_parity_pilot_2026-10-04_scripts/verify_v105_root_v3.py`
(new file, `v2` untouched) that:
- reads `liquidus_eq` per task row instead of hardcoding it,
- passes it through to `planet_input.planet(...)` and the v1.0.5 argv,
- selects `chi_max` for the Si-only case via
  `gv.max_Si_Steinbruegge2020 (0.15)` vs `gv.max_Si_Edmund2022 (0.12)` per
  `liquidus_eq`, matching `pie/shootp.py:348-355` (`mercmodel_box`) exactly,
- for S / S+Si keeps the liquidus-independent
  `chi_max = 0.11 + 0.187*exp(-0.065*Picb*1e-9)` (also from `shootp.py`),
- adds the S+Si-only pre-sweep gate `si_gate_pass` (HEAD's
  `driverp.py:137-149`: `si_max = Steinbruegge(0.15) if Steinbruegge else
  Edmund(0.12)`, rejects if `chi_Si_icb > si_max`) and folds it into
  `full_head_accept`.

Validated against `v2`'s own known case (same `normf`/`chi_max`/
`full_head_accept` for the one existing genova code-1 match) and against a
synthetic Steinbruegge task (confirmed `chi_max` switches 0.12 -> 0.15).

**Finding that closes the stratification question:** the actual rerun
population (`main_manifest.csv`, `design.py:108`) is **100% `liquidus_eq
= 'Edmund'`** -- there is no Steinbruegge-tagged row anywhere in the source
data to stratify against. `v3` is liquidus-correct and future-proof, but this
pilot could not and did not fabricate a Steinbruegge sample; reported as a
population-level fact, not a gap in the verifier.

## Task 1 -- source of the full population, sampling

Source: `docs/notes/item18a_population_rerun_2026-10-03_scripts/main_rerun_rows.json`
(item 18a's 1400-row rerun census), same provenance item 30/31 used. Filtered
to `prestop_rerun_failed > 0` -> **306 compositions**, the entire candidate
pool for "a v1.0.5-converged root with a corresponding non-zero-error_code
HEAD row at the same radius."

Rather than draw a partial sample and risk under-covering the 2-event
population, this pilot **exhaustively re-ran all 306 compositions** (reusing
item31b's already-completed 38: 20 from `select_sample_v2b.py` + 18 from
`select_sample_v2c.py`; newly run 268: 6-row trial for cost-estimation +
262-row full remainder via `select_sample_v3_full.py` /
`run_batch_v3.py` / `classify_v3.py`). Stratification across S/Si/S+Si was
inherited from the population's own composition (S+Si dominates -- see the
run log), not forced.

## Task 4 -- cost estimate (reported first, as required)

| Phase | Compositions | Workers | Wall start (CDT) | Wall end (CDT) | Wall time |
|---|---|---|---|---|---|
| Trial (cost probe) | 6 | 6 | 2026-10-04 17:38 | 2026-10-04 17:41:59 (4 of 6 fast) | ~17-80 s/composition (S, Si, small S+Si) |
| Trial, slow outliers | 2 (genova S+Si) | shared w/ full batch | -- | 2026-10-04 19:14:58 | confounded by concurrent full-batch contention; see full-batch genova timings instead |
| Full census | 262 | 28 | 2026-10-04 17:46 (approx, first completion 17:49:14) | 2026-10-04 19:15:07 | **~89 min wall** |
| Classification (full) | 262 runs -> 5717 candidates -> 2 sampled | 1 | 2026-10-04 19:15:07 | 2026-10-04 19:15:11 | ~4 s |

Per-composition cost, read directly off `run_batch_v3_full.log` (not
estimated): fast (S/Si, few-chi) compositions ~ 17-80 s each; slow (S+Si,
"genova", full chi-sweep) compositions ~ 320-400 s each (e.g.
`genova_S_0.00_912011`: 319.7 s; `margot_Si_0.00_732384`: 387.0 s). 2 of 262
compositions exceeded the 1200 s HEAD-subprocess timeout and are recorded as
`status="exception"` (indices 246, 253; 1441 s and 1465 s), excluded from
candidate counting by `prestop_candidates()`'s existing exception-skip, not a
new failure mode.

Extrapolated: the dominant cost is the full-population census itself (already
run, not a projection) at **~89 minutes wall / 262 compositions / 28-way
parallel** ~= **20.4 s/composition amortized**. Re-running the full item18a
1400-composition population (not just the 306 prestop-failing ones) at the
same rate would cost **~= 1400 x 20.4 s / parallelism ~= 8 hours wall at
28-way**, i.e. this 306-composition exhaustive census was already the
cost-bounded, representative option -- a further "~30/code" draw would have
added no information once the true population size (3 and 0) was known.

## Task 2/3 -- classification and sort_models survival, exhaustive (not sampled)

Combined across all three classification runs (`classification_v2b.json`,
`classification_v2c.json`, `classification_v3_full.json`):

| Source | Candidates (code!=0 matched-prestop rows) | code 1 | code 2 | code 4 |
|---|---|---|---|---|
| v2b (20 compositions) | 496 | 1 | 0 | 495 |
| v2c (18 compositions) | 368 | 0 | 0 | 368 |
| v3 full (262 compositions, + 6 trial folded in) | 5717 | 2 | 0 | 5715 |
| **Total (306 compositions, exhaustive)** | **6581** | **3** | **0** | **6578** |

**All 3 code-1 instances classify as HEAD-over-constrains (a)**: in every
case the v1.0.5 published root re-evaluated under HEAD's full acceptance
chain (`si_gate_pass` for S+Si, `mercmodel_box`'s finite/rcmb/chi_max checks,
`driverp.py:287-288` post-convergence chi>=0, `driverp.py:252` rs>=rcmb)
passes all of them (`full_head_accept=True`), yet HEAD's own csv row at that
radius carries `error_code=1`. No instance is classified (c) "tuning-only" --
this pilot did not capture per-iterate Newton trajectories for the new
batch (only item31b's single original case has that), so per the task's
explicit instruction, uncertainty is stated rather than (c) invented:

> "newton_iters=13 on the HEAD row at this radius (no per-iterate trajectory
> captured for this batch -- (c) not claimed without that evidence, per task
> instructions)"

Detail, all 3 instances:

| # | moi | light | chi_Si_icb | ricb_m | label | source |
|---|---|---|---|---|---|---|
| 1 | genova | S+Si | 0.09 | 1,650,010 | HEAD-over-constrains(a) | item31b original (v2b) |
| 2 | genova | S+Si | 0.10 | 1,650,010 | HEAD-over-constrains(a) | this pilot (v3 full) |
| 3 | genova | S+Si | 0.07 | 1,600,010 | HEAD-over-constrains(a) | this pilot (v3 full) |

All 3 are S+Si, two at the same radius as the item31b case with adjacent
`chi_Si_icb`, consistent with item31b's conclusion that this is a localized
line-search artifact (growth_max=100 cap) near a specific (moi, radius, chi)
neighborhood, not a broad algorithmic defect -- now reinforced by exhaustive
rather than partial coverage.

### sort_models survival (Task 3)

Read directly from the Zenodo bundle's
`Plotting and Analysis Scripts/For Monte Carlo Study/sort_models.py`
(paper-facing filter script, not part of `pie/`), not inferred:
- `"all"` filter applies **only to folders matching `*S+Si_Edmund`** by glob
  -- structurally inapplicable to S-only/Si-only rows (none of this pilot's 3
  code-1 rows are S-only/Si-only, so this doesn't matter here, but is noted
  for completeness).
- `sl`: `isnow in (1.0, 3.0)`.
- `goodTCMB`: `1700 <= Tcmb <= 2100`.
- `goodTCMB_sl`, `goodTCMB_goodchiS` (`chi_S_bulk < 0.02`) compose the above.

All 3 code-1 rows **fail every sort_models filter**, for a uniform, mechanical
reason: `isnow`, `Tcmb`, `chi_S_bulk` are all `NaN` on these rows, because
HEAD never wrote a converged downstream solve at this radius (`error_code=1`
means the row IS the failure point) -- `NaN` compared against any numeric
threshold is `False` in every predicate. This is not evidence of a parity gap
in sort_models; it is the expected consequence of filtering on diagnostics
that only exist for converged rows.

## Task 5 -- no solver/policy code touched

No change to `pie/shootp.py`, `pie/driverp.py`, or any production/solver
code. Everything new is: `verify_v105_root_v3.py` (parity-analysis script,
read-only against HEAD, re-executes v1.0.5's own physics),
`select_sample_v3.py`, `select_sample_v3_full.py`, `run_pair_v3.py`,
`run_batch_v3.py`, `classify_v3.py`, `aggregate_full_population_v3.py`, their
JSON/log outputs, and this note.

**Possible solver/policy change suggested by the evidence (NOT IMPLEMENTED,
for owner review only):** all 3 confirmed code-1 over-constraint cases are
S+Si, same `moi="genova"`, adjacent radii/chi, consistent with item31b's
diagnosis of a `growth_max=100` line-search-step cap being hit near this
(moi, radius, chi) neighborhood when the true root requires a larger
corrective step than the cap allows on that iteration. If the owner wants
this closed, the next step would be raising `growth_max` (or adding an
adaptive relaxation) specifically in that regime and re-running this same
exhaustive 306-composition census to confirm the 3 code-1 rows now converge
with `full_head_accept` unchanged, before considering a broader change. No
such change has been made.

## Deliverables

- `docs/notes/item31_v1.0.5_parity_pilot_2026-10-04_scripts/verify_v105_root_v3.py`
  (+ copy inside `v105_src_instrumented/` required by `classify_v3.py`'s
  subprocess invocation)
- `select_sample_v3.py`, `select_sample_v3_full.py`, `run_pair_v3.py`,
  `run_batch_v3.py`, `classify_v3.py`, `aggregate_full_population_v3.py`
- `item31c_trial_sample.json`, `item31c_full_sample.json`
- `classification_v3_trial.json`, `classification_v3_full.json`
- `results_v3_trial/`, `results_v3_full/` (raw per-composition run artifacts)
- `run_batch_v3_full.log`
- this note

All new/changed files grepped clean of machine-local paths per
`testsys/contract/test_repo_hygiene.py` / `.githooks/pre-commit`
(dev-box home dirs, scratch temp dirs).

## Caveat carried forward from item31b, unchanged

This comparison method only covers "root-comparable" (matched-prestop)
radii -- those where v1.0.5's own published sweep converged. The much larger
beyond-prestop tail (`beyond_error_codes` aggregate: 748 code-1, 36 code-2
out of 30,169 beyond-prestop rows across the full 1400-composition
population) has no v1.0.5 reference root to compare against; building a
cold-start v1.0.5 harness at beyond-prestop radii remains new, unscoped
engineering (flagged, not started, per item31b's original recommendation).

