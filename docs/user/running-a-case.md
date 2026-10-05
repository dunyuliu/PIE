# Running a Case

Every entry point below ultimately calls `pie`'s present-day solver once
per composition: `python -m pie p CMR2 CMC light_element liquidus_eq
[chi_Si_icb]` (the `pie p ...` console command is equivalent). `CMR2`/`CMC`
are the normalized polar moment of inertia and moment of inertia factor
constraints; `light_element` is `S`, `Si`, or `S+Si`; `liquidus_eq` is
`Steinbruegge` (Steinbruegge et al. 2020) or `Edmund` (Edmund et al. 2022);
`chi_Si_icb` (Si weight fraction at the inner-core boundary, required only
for `S+Si`) is held fixed while the solver fits everything else.

## A single case

```
mkdir -p results
pie p 0.346 0.424 S Edmund
```

For the Margot et al. constraints, `CMR2 = 0.346`, `CMC = 0.424`.

## Sweeping compositions: `scheduler.py`

```
python util/run/scheduler.py CMR2 CMC
```

Loops over light-element choice (S, Si, S+Si), liquidus equation
(Steinbruegge, Edmund), and -- for S+Si specifically -- `chi_Si_icb` from
0% to 15% Si in 1% increments, invoking `pie p ...` once per composition
(18 compositions total). Run from the repo root: `scheduler.py` is an
operational script, not part of the installed `pie` package, so it is
invoked by path.

## Monte Carlo ensemble around a mean CMR2/CMC

```
python util/run/monteCarlo.run.py
```

Generates a suite of present-day models fitting (CMR2, CMC) pairs drawn
randomly around an assigned mean and standard deviation.

## Large, resumable ensembles: `robust_runner.py`

For batches too large to babysit (knox or TACC Lonestar6), `pie/robust_runner.py`
runs any list of jobs from one manifest file, resumable and provenance-tracked:

```
# 1. Write a manifest by hand (columns CMR2,CMC,light_element,liquidus_eq,
#    chi_Si_icb[,seed]; chi_Si_icb only for S+Si), or generate a seeded
#    Monte Carlo ensemble (same draw as monteCarlo.run.py, same compositions
#    as scheduler.py: S+Si x 16 chi_Si_icb, S, Si):
python3 pie/robust_runner.py make-mc-manifest mc.csv --n 1024 --seed-base 20260930

# 2a. knox / any shared box: PIE_WORKERS-capped pool, nice 10, 1 BLAS thread/job
python3 pie/robust_runner.py run mc.csv

# 2b. Lonestar6: writes a launcher of pending jobs only, then the
#     project's own slurm script runs it under LAUNCHER
python3 pie/robust_runner.py run mc.csv --backend tacc
sbatch util/run/TACC.LS6.parallel.run.slurm
```

A job counts as done only when its sentinel file exists, written after
`python -m pie` exits 0 and its csv reads back; a killed job's partial csv
does not count. Re-running the same command resumes; `--force` re-runs
finished jobs. Every record and sentinel carries provenance: git SHA and
whether `pie/` was dirty, the dependency pins and the versions actually
installed, host, interpreter, run id, start/end time.

`PIE_WORKERS` caps parallelism on a shared machine (default `max(4, floor(free
cores/2))`); check `uptime`/`who` first and set it explicitly on a loaded box.

### Legacy recipe

`util/run/TACC.LS6.create.parallel.launcher.py` (run with the working
directory set to `util/run/`) writes a `commands_launcher` file of 1024
`monteCarlo.run.py <seed>` lines, for LAUNCHER on LS6 or a plain `xargs`
pool on knox:

```
cd util/run
python TACC.LS6.create.parallel.launcher.py
nice -n 10 xargs -P "${PIE_WORKERS:-4}" -I{} sh -c '{}' < commands_launcher
```

Its resume check is weaker than `robust_runner.py`'s: it skips a draw if
that draw's S+Si metadata csv already exists, and that csv is created
(header row only) before the sweep starts -- so a draw killed mid-run looks
finished. Prefer `robust_runner.py` for anything you need to trust the
resume behaviour of.
