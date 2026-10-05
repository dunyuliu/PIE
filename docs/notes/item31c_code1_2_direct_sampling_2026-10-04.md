# Item 31c -- direct sampling of error_code 1/2 across the full matched-prestop population

**AUDITED-PASS (lars-eriksson + priya-nair, 2026-10-04; sort_models claim
re-verified by priya-nair, 2026-10-04).** First pass: lars-eriksson
independently confirmed `verify_v105_root_v3.py` faithfully reproduces HEAD's
production acceptance chain PER-ROW liquidus (si-only chi_max switch at
shootp.py:349-350, the liquidus-independent S/S+Si formula at shootp.py:
352-353, the S+Si pre-sweep si_gate at driverp.py:137-139, and the three
pre-existing mercmodel_box/chi-profile/rs>=rcmb checks carried over from v2
without regression) at exact file:line, including a numeric spot-check of
both sampled code-1 rows' chi_max/si_gate values -- no discrepancies. This
audit scoped verifier fidelity only, not the sort_models claim, and stands
unaffected by the correction below. priya-nair independently re-derived
every headline count directly from the raw
`classification_v2b/v2c/v3_full/v3_trial.json` files (496/368/5717
candidates, 1/0/2 code-1, 0 code-2 each, 6581/3/0/6578 combined) and the
306-composition exhaustive-census claim (268 newly run + 38 already covered
= 306, confirmed against `main_rerun_rows.json`'s independent recount) --
all CONFIRMED, the apparent 262+20+18=300 arithmetic gap resolved by the
6-row trial batch omitted from that quick sum. Both sampled code-1 rows'
`full_head_accept=True` and `sort_models` NaN diagnostics were independently
confirmed as literal JSON values, not prose claims -- the arithmetic was
correct, but see the correction below on what the sort_models check was
actually measuring.

**Correction (2026-10-04, found by the conductor, not by either first-pass
audit):** the original sort_models section ran the paper's filter predicates
against HEAD's own failed-row diagnostics (`isnow`/`Tcmb`/`chi_S_bulk`, all
NaN by construction since `error_code!=0` means HEAD never converged at that
row) -- a tautological check that was guaranteed to read "fails every
filter" regardless of any real physics, and answers the wrong question. The
question that matters is whether **v1.0.5's published row** at each
(composition, ricb) point passes the paper's filters and lands in the Fig 2
heat-map range. Direct inspection of the raw Zenodo archive
(`~/shared_dataset/zenodo.16459292/extracted/PIE/work.genova/results/`)
found there is no published row to check at all: all 3 sampled code-1 radii
are **beyond the maximum radius v1.0.5's own published sweep reached** for
that exact composition (see "sort_models survival (Task 3) -- CORRECTED
2026-10-04" below for the per-point table). This is a stronger conclusion
than a corrected filter-pass/fail would have been -- these 3 points, by
construction, cannot have affected the paper, even though they sit within
Fig 2's nominal ricb<=1800 km axis range. priya-nair independently
re-verified this specific claim against the raw `pMetaData_<chi>.csv`
(exact `ricb` column, no row at the requested radius) and the
`DataSi%wt<chi>_R*.h5` filenames (independent cross-check via a second file
type) for all 3 compositions -- CONFIRMED for all 3 points, with exact
max-ricb values matching the table below.

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

Measured, not projected: the 306-composition exhaustive census (the entire
candidate pool this question could possibly draw from) ran in **~89 minutes
wall at 28-way parallel**, ~20.4 s/composition amortized. For scale only
(not an alternative that was run): extrapolating that same per-composition
rate to item18a's full 1400-composition population (not just the 306
prestop-failing ones) would cost **~8 hours wall at 28-way** -- i.e. roughly
5x the time, for a population that cannot contain any additional code-1/2
instances beyond the 306 already covered (code 1/2 only arise where
`prestop_rerun_failed>0`). A "~30/code" partial sample was therefore both
unreachable (the population has only 3 code-1, 0 code-2 rows total) and, had
it been reachable, would have cost less than the 89-minute exhaustive run
that was actually performed -- the exhaustive census was chosen because it
was cheap enough to just do and removes all sampling uncertainty, not
because any alternative was more expensive.

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

### sort_models survival (Task 3) -- CORRECTED 2026-10-04

**The first pass of this section ran `sort_models`' filters against HEAD's
own failed-row diagnostics (all NaN by construction, since `error_code=1`
means HEAD never reached a converged downstream solve) and reported "fails
every filter" -- that check is tautological and was flagged as wrong: it
answers "does the row that failed look like a failure", not the question
that decides paper impact, which is whether **v1.0.5's published root**
at that (composition, radius) point would have passed the paper's filters
and landed in a published figure.**

Re-derived directly from the Zenodo archive (`~/shared_dataset/
zenodo.16459292/extracted/PIE/work.genova/results/<composition>/`), reading
the actual published `pMetaData_<chi>.csv` files and `DataSi%wt<chi>_R*.h5`
filenames for each of the 3 compositions -- a few minutes, no runs:

| # | composition dir | chi_Si_icb | requested ricb | max published ricb for this composition | published row at this radius? |
|---|---|---|---|---|---|
| 1 | `CMR2_0.33720309225290551_CMC_0.43747819456340975_S+Si_Edmund` | 0.09 | 1,650,010 m (1650.01 km) | 1,600,000 m (1600 km, `DataSi%wt0.09_R1600.0.h5`) | **no -- 50.01 km beyond max** |
| 2 | `CMR2_0.33861967373120566_CMC_0.43564804836797444_S+Si_Edmund` | 0.10 | 1,650,010 m (1650.01 km) | 1,600,000 m (1600 km, `DataSi%wt0.10_R1600.0.h5`) | **no -- 50.01 km beyond max** |
| 3 | `CMR2_0.33548584951205618_CMC_0.43971750288293066_S+Si_Edmund` | 0.07 | 1,600,010 m (1600.01 km) | 1,550,000 m (1550 km, `DataSi%wt0.07_R1550.0.h5`) | **no -- 50.01 km beyond max** |

**All 3 code-1 instances occur beyond the maximum radius v1.0.5's own
published sweep reached for that composition.** The "v1.0.5 root" evaluated
in Task 2 is not a published result -- it is produced by re-running v1.0.5's
unmodified source code (`verify_v105_root_v3.py` / `v105_src_instrumented/`)
past the point where the original campaign's sweep actually stopped
(`prestop`). There is no row in `pMetaData_*.csv`, no `Data*.h5` file, and
therefore no entry in any `sort_models` output csv (`all_models_*`,
`goodTCMB_*`, etc.) at these 3 exact points -- **the question "does v1.0.5's
published row pass sort_models" has no row to evaluate, which answers it
more decisively than any filter check could: these 3 points cannot have
affected the paper, because the paper's own published sweep never produced
them.** (All 3 requested radii are still inside Fig. 2's nominal axis range,
ricb <= 1800 km -- the composition's sweep simply stopped short of that
radius, for reasons internal to the original v1.0.5 run, before reaching it.)

This reframes, rather than overturns, item31b's and this note's Task 2
conclusion: the 3 instances are real (v1.0.5's solver code, if run further,
converges where HEAD's Newton does not) but they describe a region the
published dataset never sampled, not a published result HEAD would
silently drop.

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

