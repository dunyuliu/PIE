# Output Files

Each run writes its files under `results/CMR2_<CMR2>_CMC_<CMC>_<light_element>_<liquidus_eq>/`,
one set per `chi_Si_icb` value (0 for S-only/Si-only runs).

## Metadata: `pMetaData_<chi_Si>.csv`

One row per attempted trial inner-core radius (40 rows for the default
radius grid, `rs = arange(10 m, 2e6 m, 50e3 m)`) -- a composition that
fails to converge at every radius still has 40 rows, not an empty file.
Columns (`pie/globalvar.py`'s `presentday_columns`):

`chi_Si_icb, rhom, mass, moi, cmc, Picb, Tcmb, isnow, isnowcmb, chi_li_in,
chi_S_bulk, Pcmb, chi_li_eut_icb, chi_li_eut_cmb, ricb, rcmb, core_mass,
chi_li_icb, error_code, start, newton_iters, resid_norm`

A **converged** row (`error_code == 0`) has every physical column filled
and a corresponding `.h5` profile file (below). A **failed** row has
`ricb`, `chi_Si_icb`, `error_code`, `start`, `newton_iters`, and
`resid_norm` set, every physical column `NaN`, and no `.h5` file. Consumers
must filter to converged rows before using the physical columns, e.g.
`df[df.error_code == 0]` -- the project's own plotting scripts do this.
`start` records which initial guess converged (or was last tried):
`warm` (from the previous converged radius) or `cold` (the generic
initial guess, tried once if the warm start fails).

See [Troubleshooting](troubleshooting.md) for what each `error_code` means.

## Structured solver log: `solverLog_<chi_Si>.jsonl`

One JSON object per line: either a per-radius Newton iteration record
(iterate history -- trial value, `|f|`, `|dx|`, Jacobian condition, step
length and whether a trial was rejected by the bounded line search) or a
failure-context record (non-finite counts encountered while shooting,
`chi_li` against the eutectic/admissible-box bounds). Written alongside
the csv, same `chi_Si_icb`-suffixed naming convention.

## Radial profiles: `Data*_R<ricb>.h5`

One file per **converged** radius, named by that radius in metres. Holds
the full radial profile arrays the shoot integrated: radius, density,
pressure, temperature, adiabatic temperature, gravity, and light-element
concentration, from the centre out to the solved outer boundary.

## Figures

The scheduler and single-case runs also produce summary figures (profile
plots, contour plots over the sweep) under the same `results/` tree via
`scripts/plot/summaryPlot.py` / `scripts/plot/visualization_present.py`.

## Robust-runner provenance

`pie/robust_runner.py` additionally writes, per job, a sentinel file
`.runner_done_<chi>.json` (present only once the job's own csv has been
read back after a clean exit) and appends to a shared
`results/runner_status.jsonl`: one `start` and one `end` record per
attempt, each carrying the git SHA, whether `pie/` was dirty, the pinned
vs. actually-installed dependency versions, host, interpreter, run id, and
timestamps. A finished job's status is an `ErrorCode` name: `CONVERGED` if
every radius converged, else the most frequent failure code with per-code
row counts; a job that never finished is `PROCESS_CRASHED` or
`INCOMPLETE_OUTPUT`.
