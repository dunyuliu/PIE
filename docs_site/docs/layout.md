# Project layout

- **`pie/`** -- the installable Python package (`uv pip install -e .`,
  `pyproject.toml` at root). `main.py` is the entry point (`pie/cli.py` +
  `pie/__main__.py` wrap it as the `pie` console script / `python -m pie`);
  `driverp.py`/`shootp.py` drive the present-day model, `drivere.py`/
  `shoote.py` the evolution model (under development, parked); `libCore.py`
  + `coreEos.py` hold the physics; `globalvar.py`/`planet_input.py` hold
  shared state.
- **`util/plot/`** -- `summaryPlot.py`, `visualization_present.py`,
  `read_plot_datah5.py`, `plotAll.py`/`plotAll.sh`.
- **`util/run/`** -- `scheduler.py`, `monteCarlo.run.py`,
  `TACC.LS6.create.parallel.launcher.py` + its slurm script, `postp.slurm`.
  `robust_runner.py` deliberately stays in `pie/`, not here -- see
  [Large ensembles](running/robust-runner.md).
- **`historical_versions/`** -- frozen zip/tar snapshots of prior versions.
  Read-only.
- **`testsys/`** -- the test suite (unit, contract, integration, e2e,
  published-paper parity). See `testsys/README.md` for tier definitions.
- **`docs/notes/`** -- working engineering/science notes (not this site;
  kept separate deliberately).
- **`CHANGELOG.md`** -- per-release change list; git tags are the version
  source of truth.
- **`PATHWAY_FORWARD.md`** -- the living internal engineering board. Not
  republished here verbatim; see [Project status](status.md) for a short
  summary of recently closed milestones.

## Parameter / data flow

A present-day run is a 5-unknown shooting problem (pressure and
temperature at the centre, core radius, mantle density, light-element
fraction at the inner-core boundary) solved by Newton's method with a
finite-difference Jacobian (`pie/shootp.py`, `mynewtonSys`). See the
README's "Solver" section for the bounded line-search details added in
v1.3.0.
