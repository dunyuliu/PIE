# Monte Carlo ensemble

```bash
python util/run/monteCarlo.run.py
```

Generates a suite of Mercury present-day interior models fitting a set of
CMR2 and CMC values randomly drawn from an assigned mean CMR2 and its
standard deviation.

!!! note "Resume behaviour"
    `monteCarlo.run.py`'s resume check skips a draw if the draw's `S+Si`
    `pMetaData_*.csv` exists -- but `pie.main` creates that csv (header
    row) before the sweep starts, so a draw killed mid-run is skipped as
    if finished. For anything that needs reliable resume, prefer
    [`robust_runner.py`](robust-runner.md).

## Legacy launcher (TACC LS6 / knox)

```bash
cd util/run
python TACC.LS6.create.parallel.launcher.py   # writes commands_launcher
nice -n 10 xargs -P "${PIE_WORKERS:-4}" -I{} sh -c '{}' < commands_launcher
```

Must be run with `cwd == util/run/` (where `monteCarlo.run.py` lives and
where its `./results/` output lands, board item 28b). Its resume check is
the same weaker one described above.
