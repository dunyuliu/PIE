# Troubleshooting

## Per-radius error codes

<!-- BEGIN ERROR CODES (generated from pie/globalvar.py's ErrorCode enum and ERROR_CODE_DESCRIPTIONS by docs/user/gen_params.py; do not edit by hand) -->

PIE does not stop a sweep on the first failed radius: each trial inner-core radius either converges or fails with one of the codes below, recorded in that radius's row of `pMetaData_<chi_Si>.csv` (`error_code` column) and in `solverLog_<chi_Si>.jsonl`. See [Output Files](outputs.md) for the full row/column layout.

| code | name | meaning |
|-----:|------|---------|
| 0 | `CONVERGED` | converged |
| 1 | `NEWTON_MAXIT` | Newton solver: maxit reached without convergence |
| 2 | `SINGULAR_JACOBIAN` | Newton solver: singular Jacobian |
| 3 | `NONFINITE_SHOOT` | shoot: non-finite result or uncaught exception (A/rho/g) |
| 4 | `CHI_OUTSIDE_ADMISSIBLE_BOX` | chi_li outside admissible box (negative or > eutectic) |
| 5 | `RICB_GE_RCMB` | ricb >= rcmb: outside physical domain |
| 6 | `SI_ABOVE_LIQUIDUS_MAX` | chi_Si_icb above liquidus max Si%wt (by design) |
| 7 | `NONFINITE_ICB_DENSITY` | shoot: non-finite ICB density from eosInnerCore (y0 non-finite) |

<!-- END ERROR CODES -->

## What to try for each code (hand-written, not generated)

* **0 `CONVERGED`** -- nothing to do; this radius solved.
* **1 `NEWTON_MAXIT`** -- Newton hit `maxit` without meeting `xtol`/`ftol`
  (see [Parameters](parameters.md)); try a different radius grid, or accept
  this radius as unresolved.
* **2 `SINGULAR_JACOBIAN`** -- the Jacobian is numerically singular (e.g. a
  light-element fraction clamped at the eutectic); often marks the edge of
  the solvable radius range for this composition, not a bug to fix.
* **3 `NONFINITE_SHOOT`** -- a NaN/Inf, or an uncaught indexing/solve error,
  while integrating density/gravity/structure outward from the centre.
* **4 `CHI_OUTSIDE_ADMISSIBLE_BOX`** -- the light-element fraction went
  negative or above the eutectic/liquidus bound during the solve, even
  after line-search backtracking.
* **5 `RICB_GE_RCMB`** -- the trial inner-core radius reached or exceeded
  the solved core-mantle-boundary radius -- outside the model's physical
  domain for this trial.
* **6 `SI_ABOVE_LIQUIDUS_MAX`** -- `chi_Si_icb` is above the liquidus
  table's maximum Si weight percent -- an intentional, by-design stop
  checked once before the sweep starts, not a solver bug; lower
  `chi_Si_icb`. This is the one code that ends the whole composition
  rather than just one radius.
* **7 `NONFINITE_ICB_DENSITY`** -- the inner-core equation of state
  returned a non-finite density at the centre/inner-core boundary for this
  Newton trial iterate; caught before integration starts, so it is a
  per-radius failure like the others, not a crash.

## The solver rejects a converged iterate outside its physical bounds

The solver already checks every intermediate trial step of a radius's
Newton solve against its physical limits -- non-finite residual, `rcmb >
ricb`, `chi_li_icb` at or below the eutectic/Si cap -- via the bounded
line search. By default, it now also checks its *starting guess* and its
*converged answer* against those same limits, so an impossible converged
model (e.g. `chi_li_icb` above the Edmund Si cap of 0.12) is recorded as
a failed row (`error_code` 4 or 5, see above) instead of being silently
saved as if it were physically admissible.

This is controlled by `PIE_CHECK_SOLUTION_BOUNDS` (env var): unset, or
set to anything other than `0`/`false`/`no`/`off`, means the check runs
(default, since v1.8.0). Set it to one of those four falsy spellings to
restore the pre-v1.8.0 behaviour (no check on `x0` or the converged
iterate). The older name, `PIE_BOX_CHECK_FINAL`, is a deprecated alias:
if `PIE_CHECK_SOLUTION_BOUNDS` is unset but `PIE_BOX_CHECK_FINAL` is set,
PIE honours the old variable's own truthy/falsy spellings (`1`/`true`/
`yes`/`on` vs. anything else) and emits a `DeprecationWarning` -- set the
new name instead. Every run's `pMetaData_<chi_Si>.csv` records which way
this resolved in its `check_solution_bounds_enabled` column (see
[Output Files](outputs.md)), so the setting travels with the csv rather
than being invisible in the output.

## A sweep stops partway through its radius grid

This is expected, not a bug: the csv has one row per attempted radius
(see [Output Files](outputs.md)), and a composition that stops converging
past some radius still has a full 40-row file with the remaining rows
marked failed. Filter to `error_code == 0` before using the physical
columns. See [Benchmarks](benchmarks.md#known-documented-non-convergence)
for two specific, already-documented cases of this.

## `S+Si` results need qualification

Before reporting an `S+Si` (two-light-element) result, state explicitly
whether it is regression-anchored (matches the prior code family's output)
or independently verified (matches a check outside that family) -- see
[Model overview](model-overview.md#regression-anchored-vs-independently-verified).
Today, no `S+Si` result is independently verified beyond its own
self-consistency limits.

## A large ensemble job is reported `PROCESS_CRASHED` or `INCOMPLETE_OUTPUT`

These are `robust_runner.py` statuses, not `ErrorCode` values -- they mean
the job's process exited without ever producing a readable, complete csv
(as opposed to `CONVERGED`/a failure-code name, which mean the job ran to
completion and its csv was read back). Re-run with `robust_runner.py run
<manifest> --force` for just that job, or inspect
`results/runner_status.jsonl` for its `start`/`end` provenance records to
see what was running when it stopped.

## Environment issues

PIE supports exactly one environment: Python 3.12 with the exact pins in
`requirements.txt`, installed via `uv` as in
[Getting Started](getting-started.md). An unpinned or "latest" install is
not a lighter-weight alternative -- it is untested, and divergent results
on it are not a PIE bug report by themselves.
