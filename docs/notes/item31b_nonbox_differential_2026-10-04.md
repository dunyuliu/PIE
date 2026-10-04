# Item 31(b) — non-box differential: the error_code 1/2 ("not code 4") share of the regressed population — 2026-10-04

**Follow-up to item 31** (`docs/notes/item31_v1.0.5_parity_pilot_2026-10-04.md`,
PR #79, conductor-corrected). That note's corrected verdict stands and is
**not re-opened here**; this is a separate investigation into the part of
the 6,964-radius regressed population the original pilot explicitly said it
said nothing about: the ~61% that is NOT error_code 4
(CHI_OUTSIDE_ADMISSIBLE_BOX), principally code 1 (NEWTON_MAXIT) and code 2
(SINGULAR_JACOBIAN). Scope: pilot only (68 compositions re-run total across
three attempts, not the full population). Read-only diagnosis; no solver
code was modified (the instrumented v1.0.5 scratch copy got one additive
debug-dump line, documented below). Harness:
`item31_v1.0.5_parity_pilot_2026-10-04_scripts/` (same directory as item 31,
new `*_v2*` files).

## 0. Corrected verifier (task 1)

The original pilot's `verify_v105_root.py` reproduced only
`pie/shootp.py::mercmodel_box` (mid-solve trial rejection). This follow-up's
`verify_v105_root_v2.py` reproduces **all three** of HEAD's production
acceptance checks on a v1.0.5 root:

1. `mercmodel_box` (`pie/shootp.py:319-358`): finite `f` **and** finite
   `fout` (the original verifier checked only `f`; lars-eriksson's finding,
   now closed), `rcmb_nd > ricb_nd`, `chi_li_icb <= chi_max`, `CHI_MIN=None`.
2. `pie/driverp.py:287-288`: `(chi_li < 0).any()` over the **full converged
   radial profile** `yy[5]`, not just the ICB value `v[4]`.
3. `pie/driverp.py:252`: `rs[k] >= rcmb` on the final dimensional values
   (a separate code path from check 1's non-dimensional mid-solve test,
   even though on a converged root they should agree to roundoff).

`full_head_accept = box_pass and not chi_profile_negative and not
ricb_ge_rcmb_final`. Only `full_head_accept == True` counts as "HEAD's
production code would have accepted this v1.0.5 root."

## 1. Candidate population: a structural finding before any classification

**Attempt 1** (`select_sample_v2.py`, `results_v2/`, 30 compositions):
selected compositions by HEAD's **run-level aggregate** `beyond_error_codes`
(item 18a's census field, counting error codes on radii *beyond* where each
composition's own fresh v1.0.5 re-run stopped). This produced 327 code-0,
684 code-4, 47 code-3, **29 code-1, 11 code-2**, 22 code-5 rows in HEAD's
csvs -- plenty of code-1/2 material -- but when matched against the
radii where **v1.0.5 itself converged** (the only population where a
v1.0.5 reference root exists to test), the overlap was **zero**: all 29
code-1 and all 11 code-2 rows sit at `ricb` strictly beyond the largest
`ricb` v1.0.5's own fresh sweep ever reached in that composition (it
crashed/stopped earlier). `classification_v2.json` records this (0
candidates for code 1/2, sampled 8 of 180 code-4 candidates for
continuity).

**This is itself the first finding**: NEWTON_MAXIT and SINGULAR_JACOBIAN
cluster at large `ricb` near the geometric limit -- exactly the radii
v1.0.5's own un-line-searched Newton (`sys.exit()` on its first failure)
typically never got to attempt, because it stopped even earlier in the
same sweep. There is structurally no v1.0.5 root to compare against in
that zone; "did HEAD wrongly reject a v1.0.5-valid root" is not a
well-posed question there.

**Attempts 2 and 3** (`select_sample_v2b.py` + `select_sample_v2c.py`,
`results_v2b/` + `results_v2c/`, 20 + 18 = 38 compositions) instead
selected by item 18a's own `prestop_rerun_failed` field -- compositions
where HEAD's rerun **failed to reproduce a radius v1.0.5's published run
actually converged on**. This is the correct, population-matching
selection (`prestop_rerun_failed` sums to exactly 6,964 across all 1,400
census runs -- the prompt's target population). Across these 38
compositions, matching v1.0.5-converged radii to HEAD's csv rows gave
**864 candidate radii total: 863 code 4, 1 code 1, 0 code 2**
(`classification_v2b.json` + `classification_v2c.json`, `by_head_error_code`
sections).

With 864 matched candidates and only 1 code-1 hit, a true population rate
anywhere near item 30's board-row "~10%" figure for code 1 is excluded at
very high confidence (binomial: P(<=1 success in 864 draws | p=0.10) is
astronomically small). **Conclusion: item 30's ~39%/~10%/<0.5% breakdown is
almost certainly computed over the FULL rerun's error_code column
(prestop + beyond-prestop radii combined), not isolated to the
root-comparable "regressed" subset** -- the actual NEWTON_MAXIT/
SINGULAR_JACOBIAN instances are concentrated almost entirely in the
beyond-prestop tail, where (per the above) there is no v1.0.5 reference
root at all, so the over-constraint-vs-correctly-rejects framework this
item exists to test does not apply to them.

## 2. Classification (task 4) -- corrected 3-check verifier, 131 verified radii

| head_error_code | sampled (verified) | HEAD-correctly-rejects | HEAD-over-constrains | inconclusive |
|---|---|---|---|---|
| 4 (CHI_OUTSIDE_ADMISSIBLE_BOX) | 130 (8+92+30 across 3 batches) | **130 (100%)** | 0 | 0 |
| 1 (NEWTON_MAXIT) | 1 (the only matched instance found) | 0 | **1 (100%)** | 0 |
| 2 (SINGULAR_JACOBIAN) | 0 (none found in the matched-prestop population) | -- | -- | -- |

All 130 sampled code-4 radii fail check 2 (`driverp.py:287-288`'s
post-convergence `chi>=0` test) -- every one of them passes `mercmodel_box`
(check 1) but has a negative value somewhere in its converged `chi_li`
profile. **This sharpens item 31's original corrected verdict from
"confounded/undetermined" to a definitive "HEAD-correctly-rejects": the
code-4 regressed population is not a Newton-robustness artifact at all,
it is the deliberate v1.2.0 chi>=0 admissibility policy operating exactly
as documented, on every sampled case.**

The single matched code-1 case (`genova`, S+Si, `chi_Si_icb=0.09`,
CMR2=0.3372030922529055, `ricb_m=1,650,010`) passes **all three** of
HEAD's own checks (`full_head_accept: true`, `box_pass: true,
chi_profile_negative: false, ricb_ge_rcmb_final: false`, residual
`normf=1.0e-11`) -- a genuine, unconfounded HEAD-over-constrains instance.
Raw verify dict: `classification_v2b.json`, sample entry with
`head_error_code: 1.0`.

## 3. NEWTON_MAXIT trajectory comparison (task 3)

For the one matched code-1 case, both trajectories were read off logs each
code already writes in its own natural sweep (v1.0.5's `debug.jsonl`, newly
instrumented per-iterate via one additive line in
`v105_src_instrumented/shootp.py::mynewtonSys`; HEAD's own
`solverLog_<chi>.jsonl`, unchanged, already written by
`pie/shootp.py::mynewtonSys`'s `log_path`). **Caveat**: this is the natural
trajectory each code took in its own sweep, not a controlled re-solve from
an identical isolated `x0` forced on both -- a stronger isolation would
re-run both solvers from a hand-fixed `x0` at just this radius; out of
scope for this pilot, flagged as a follow-up below.

| k | v1.0.5 normf (pre-step) | HEAD-warm normf (pre-step) | HEAD-warm alpha | HEAD-warm condJ |
|---|---|---|---|---|
| 1 | 4.050e-03 | 4.050e-03 | 1.0 | 6.6e+02 |
| 2 | 2.563e-03 | 2.564e-03 | 1.0 | 2.3e+03 |
| 3 | 1.265e-02 | 1.252e-02 | 1.0 | 2.2e+03 |
| 4 | 9.538e-04 | 9.829e-04 | 1.0 | 2.3e+04 |
| 5 | 1.878e-02 | 1.990e-02 | 1.0 | 8.7e+02 |
| ... | (both tracking, within ~5-10%) | | | |
| 10 | 1.151e-02 | 2.159e-03 | 1.0 | 2.7e+03 |
| 11 | 3.213e-04 | 1.058e-03 | **0.5 (1 rejected)** | 3.3e+04 |
| 12 | 1.483e-07 (**converged**) | 1.390e-02 | 1.0 | 8.2e+01 |
| 13 | -- | 2.309e-04 (**NEWTON_MAXIT**, normf/normdx still ~230x/770x over 1e-6 tol) | 1.0 | 8.7e+01 |

Both start from the **bit-identical warm-start `x0`** (`k=1` normf agrees to
the last printed digit), ruling out an upstream warm-start-value bug as the
proximate cause. The two trajectories visibly decohere starting at `k=3`
(1.265e-2 vs 1.252e-2) -- well before any line-search rejection -- on a
Jacobian whose condition number is already in the 1e3 range and climbs to
3.3e4 by `k=11`. This is consistent with ordinary ULP-level divergence
(plausibly from `pie/shootp.py`'s v1.3.2 perf change,
`np.linalg.solve(J,f)` vs v1.0.5's `np.dot(np.linalg.inv(J),f)` --
"same dx to roundoff" per that commit's own docstring, not bit-identical)
being amplified by an ill-conditioned Jacobian, i.e. **this specific radius
is numerically sensitive, not specifically mis-handled**.

The proximate trigger of the failure is HEAD's `k=11` line-search: the
full Newton step there is a trial that grows `|f|` by **122.25x**, just
over `growth_max=100`'s threshold (`pie/shootp.py:304`, chosen with "5x
margin" over the largest growth measured on v1.2.0-converging paths,
18.6x), so it is rejected and a half-step (`alpha=0.5`) is substituted.
v1.0.5, with no line search at all, takes the analogous (not bit-identical,
but numerically similar) full step unconditionally and it turns out to be
self-correcting: `normf` drops from 3.2e-4 to 1.5e-7 in the very next
iterate. HEAD's half-step alternative instead walks the iterate further
from the root (`k=12` normf jumps to 1.4e-2) and the solve runs out of its
12-iteration budget (`maxit=12`, identical constant in both codebases,
`pie/globalvar.py:76` / `v105_src_instrumented/globalvar.py:69`) without
recovering.

**This is a real, mechanistically-identified instance of the over-
constraint lars-eriksson originally hypothesized** -- the v1.3.0
`growth_max=100` guard, calibrated on v1.2.0-identical paths, rejects a
large-but-correcting step once the trajectory has already drifted (for
ordinary floating-point reasons) off the exact v1.2.0/v1.0.5 path on an
ill-conditioned radius. But with n=1 confirmed instance against 863
code-4 and 0 code-2 in the same 864-candidate sample, **it cannot be
generalized as the dominant mechanism behind the ~10% NEWTON_MAXIT share
of the full regressed population** -- that share lives almost entirely in
radii with no v1.0.5 reference root at all (section 1), where this
root-comparison method cannot even be applied.

## 4. Recommendation

1. **Code 4 (~39% of the full regressed population): close as
   correctly-rejects.** 130/130 sampled radii fail HEAD's own
   `driverp.py:287-288` chi>=0 post-check -- this is the documented,
   deliberate v1.2.0 policy operating as designed, not a Newton-robustness
   question. Item 31's corrected verdict (section on code 4) is now fully
   resolved, not merely "undetermined."
2. **Code 1/2 (~10%/<0.5%): the root-comparison method used by item 31/31b
   cannot test the great majority of this population**, because it
   structurally sits beyond the radii v1.0.5's own sweep ever reached (no
   reference root exists there to call "valid"). Testing that population
   requires a DIFFERENT experiment: cold-starting v1.0.5's *own* unguarded
   Newton (not HEAD's) at those specific beyond-prestop radii, to get an
   independent v1.0.5-equivalent root there to compare against -- not
   assumed free; see cost estimate below.
3. **The one matched NEWTON_MAXIT instance is a genuine, mechanistically-
   traced HEAD-over-constrains case** (growth_max=100 line-search guard
   rejecting a self-correcting large step on an ill-conditioned radius,
   after ordinary roundoff divergence from v1.3.2's linear-solve change).
   If the owner wants this fixed rather than just understood: raising
   `growth_max` (e.g. to 150-200) or adding a fallback that accepts the
   full step when the half-step alternative itself fails to make progress
   within a few iterations are both testable, bounded changes -- scope for
   a follow-up, not this diagnostic.
4. **Papercut (not blocking, logged to `~/code/papercuts.md`)**: the
   landed `run_pair.py`/`classify.py` (item 31, PR #79) reference a
   `v105_src` scratch directory that was never created under that name
   (the actual instrumented copy is `v105_src_instrumented/`) -- confirmed
   via `git log` that this was never exercised in the committed form;
   anyone literally following that README's one-time-setup recipe hits a
   `FileNotFoundError`. Fix recommended before this is reproduced again.

## Cost estimate for scaling beyond this pilot (not executed)

Extrapolating this pilot's per-composition wall time (~230-460 s per
composition for the v1.0.5+HEAD pair, 14-way parallel on this 64-core
host, contended load ~11-13): a full re-run targeting all 306
`prestop_rerun_failed>0` compositions (to raise the code-1/2 matched-
-prestop sample size materially above n=1) would take roughly
306/38 * (38 compositions' wall time, ~35 min total across 3 batches at
14-way parallelism) =~ 4.8 h wall at the same concurrency, plus a
separate, not-yet-designed "cold v1.0.5 at beyond-prestop radii" harness
(section 4 point 2) to get any reference root at all for the >90% of the
NEWTON_MAXIT/SINGULAR_JACOBIAN population that sits beyond v1.0.5's own
reach -- that second piece is new engineering, not just more pilot scale,
and should be scoped separately if the owner wants it.

## Deliverables

- `item31_v1.0.5_parity_pilot_2026-10-04_scripts/verify_v105_root_v2.py`
  (+ copy at `v105_src_instrumented/verify_v105_root_v2.py`): corrected
  3-check verifier (task 1).
- `v105_src_instrumented/shootp.py`: one additive per-iterate debug-dump
  line in `mynewtonSys` (no algorithm change) enabling the trajectory
  comparison (task 3).
- `select_sample_v2.py` / `select_sample_v2b.py` / `select_sample_v2c.py`,
  `run_pair_v2.py`, `run_batch_v2*.py`, `classify_v2*.py`: harness
  extensions (task 2).
- `item31b_sample.json` / `item31b_sample_v2b.json` /
  `item31b_sample_v2c.json`: the three composition samples actually run.
- `results_v2/`, `results_v2b/`, `results_v2c/`: raw per-composition
  run_pair_v2 output (v1.0.5 debug log incl. new per-iterate records, HEAD
  csv rows, HEAD's full structured solver log) for all 68 compositions
  executed.
- `classification_v2.json` / `classification_v2b.json` /
  `classification_v2c.json`: raw per-candidate verify dicts (not just
  labels) for all 131 verified radii, per the instruction that raw output
  must be independently re-checkable.

Wall time: ~55 min total execution (venv build ~2 min, batch 1 ~15 min,
batch 2 ~12 min, batch 3 ~10 min, 3x classify passes ~5 min combined,
remainder investigation/analysis). Tool calls: ~55.
