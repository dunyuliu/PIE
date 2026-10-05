# Troubleshooting

## Per-radius error codes

<!-- BEGIN ERROR CODES (generated from pie/globalvar.py's ErrorCode enum by docs/user/gen_params.py; do not edit by hand) -->

PIE does not stop a sweep on the first failed radius: each trial
inner-core radius either converges or fails with one of the codes below,
recorded in that radius's row of `pMetaData_<chi_Si>.csv`
(`error_code` column) and in `solverLog_<chi_Si>.jsonl`. See
[Output Files](outputs.md) for the full row/column layout. Only code 6
(Si above the liquidus cap) is a radius-independent, by-design stop that
ends the whole composition rather than just that radius.

| code | name | meaning |
|-----:|------|---------|
| 0 | `CONVERGED` | Newton converged within `xtol`/`ftol` -- see [Parameters](parameters.md) |
| 1 | `NEWTON_MAXIT` | Newton hit `maxit` without meeting `xtol`/`ftol`; try a different radius grid, or accept this radius as unresolved |
| 2 | `SINGULAR_JACOBIAN` | the Newton Jacobian is numerically singular (`cond(J) > 1e12`, e.g. a light-element fraction clamped at the eutectic); often marks the edge of the solvable radius range for this composition |
| 3 | `NONFINITE_SHOOT` | a NaN/Inf, or an uncaught indexing/solve error, while integrating density/gravity/structure outward from the centre |
| 4 | `CHI_OUTSIDE_ADMISSIBLE_BOX` | the light-element fraction went negative or above the eutectic/liquidus bound during the solve, even after line-search backtracking |
| 5 | `RICB_GE_RCMB` | the trial inner-core radius reached or exceeded the solved core-mantle-boundary radius -- outside the model's physical domain for this trial |
| 6 | `SI_ABOVE_LIQUIDUS_MAX` | `chi_Si_icb` is above the liquidus table's maximum Si weight percent -- an intentional, by-design stop checked once before the sweep starts, not a solver bug; lower `chi_Si_icb` |
| 7 | `NONFINITE_ICB_DENSITY` | the inner-core equation of state returned a non-finite density at the centre/inner-core boundary for this Newton trial iterate; caught before integration starts, so it is a per-radius failure like the others, not a crash |

<!-- END ERROR CODES -->

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
