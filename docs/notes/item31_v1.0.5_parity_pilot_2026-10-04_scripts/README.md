# item31 pilot harness

Reproduces the item31 v1.0.5-vs-HEAD parity pilot (see
`../item31_v1.0.5_parity_pilot_2026-10-04.md`).

## Setup (one-time)
```
python3 -m venv v105_venv
./v105_venv/bin/pip install "numpy<2" "scipy<1.14,>=1.8" pandas tables matplotlib
```
v1.0.5's `coreEos.py::meltingDataFromFile` calls `scipy.interpolate.interp2d`
directly, an API removed in scipy>=1.14. HEAD's pinned venv (scipy 1.18.1)
therefore cannot even import v1.0.5 -- this legacy venv is scoped to this
diagnostic only and must never be substituted for HEAD's own (already
verified, bit-identical) `RectBivariateSpline` port.

`v105_src_instrumented/` is a scratch copy of the Zenodo 16459292 `src/`
(never the read-only original), with `shootp.py::mynewtonSys` instrumented
to emit JSONL convergence records to `$PIE105_DEBUG_LOG`, and a new
`verify_v105_root.py` standalone root-residual/admissibility verifier. The
Newton algorithm itself is byte-identical to the vendored original; only
debug I/O was added.

## Run
```
python3 run_batch.py <n_workers>     # -> results/run_*.json (14 samples)
python3 classify.py <n_sample> <seed>  # -> classification.json
```
`run_pair.py` runs v1.0.5 (legacy venv) and HEAD (`<machine-local-path-redacted>
each in its own subprocess/cwd on the same composition args, never importing
v1.0.5 into the HEAD process. `classify.py` matches v1.0.5-converged radii to
HEAD's `pMetaData_*.csv` rows at the same `ricb` (meters; `dr=50e3` grid and
`scale['a']=2439360.0` are identical in both codebases, so no interpolation
is needed), flags HEAD rows with `error_code!=0`, and independently
re-verifies each sampled v1.0.5 root via `verify_v105_root.py` using
**HEAD's own `mercmodel_box` admissibility rule** (`pie/shootp.py:317-358`:
finite f/fout, `rcmb>ricb`, `chi<=chi_max`, **no** `chi>=0` floor --
`CHI_MIN=None` by design) -- not item18a's broader admissible-set definition,
which also required `chi>=0`. Using the broader definition here would
misclassify ~97% of candidates as "HEAD-correctly-rejects" when HEAD's own
live code would not have rejected them on that basis.
