# Large ensembles: `robust_runner.py`

`pie/robust_runner.py` runs any list of present-day jobs on knox (local)
or TACC Lonestar6 from one manifest file (`PATHWAY_FORWARD.md` item 22).
One job = one `python -m pie p CMR2 CMC light_element liquidus_eq
[chi_Si_icb]` call. It is resumable and kept inside the `pie` package
(not moved to `util/run/`) because `testsys/` imports it directly as
`from pie import robust_runner`.

## 1. Build a manifest

Write one by hand (CSV columns `CMR2,CMC,light_element,liquidus_eq,
chi_Si_icb[,seed]`; `chi_Si_icb` only for S+Si), or generate the seeded
Monte Carlo ensemble (same draw as `util/run/monteCarlo.run.py`, same
compositions as `scheduler.py`: S+Si x 16 `chi_Si_icb`, S, Si):

```bash
python3 pie/robust_runner.py make-mc-manifest mc.csv --n 1024 --seed-base 20260930
```

## 2a. Run on knox / any shared box

```bash
python3 pie/robust_runner.py run mc.csv
```

A `PIE_WORKERS`-capped pool, niced to 10, 1 BLAS thread per job.

## 2b. Run on TACC Lonestar6

```bash
python3 pie/robust_runner.py run mc.csv --backend tacc
sbatch util/run/TACC.LS6.parallel.run.slurm
```

This writes `pie/commands_launcher` (pending jobs only), then the
existing slurm script runs it under LAUNCHER.

## Resume, status, and provenance

- **Resume**: re-run the same command. A job counts as done only when its
  sentinel `results/<model dir>/.runner_done_<chi>.json` exists, written
  after `python -m pie` exits 0 and its csv reads back. A killed job's
  partial csv does not count. `--force` re-runs finished jobs.
- **Status**: `<src-dir>/results/runner_status.jsonl` (`--status-log`),
  one `start` and one `end` record per attempt. A finished job's status
  is an `ErrorCode` name: `CONVERGED` if every radius converged, else the
  most frequent failure code with per-code row counts. A job that never
  finished is `PROCESS_CRASHED` or `INCOMPLETE_OUTPUT`. Exit code 0 only
  if every attempted job finished.
- **Provenance** (every record and every sentinel): git SHA and whether
  `pie/` was dirty, `requirements.txt` pins and the versions actually
  installed, host, interpreter, run id, start/end time.
- **Workers**: `PIE_WORKERS`, default `max(4, floor(free cores/2))` --
  check `uptime`/`who` first and set it explicitly on a loaded box.
- The ricb grid is not a manifest field: it is fixed in `pie/main.py`.
