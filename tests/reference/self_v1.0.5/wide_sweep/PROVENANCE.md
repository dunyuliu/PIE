# Provenance: wide self-consistency sweep (self-golden)

Generated from THIS repo's current HEAD (src/ == the byte-identical
Zenodo v1.0.5 code record, see
`tests/reference/zenodo_v1.0.5/PROVENANCE.md`) via
`generate_wide_sweep.py` in this directory. Not an independent oracle
(same code that's being tested generated it) -- it is the wide
BREADTH-of-physics regression net: 2 MOI configs (Margot
CMR2=0.346/CMC=0.426, Genova CMR2=0.333/CMC=0.443) x 6 compositions (S,
Si, S+Si x Edmund, Steinbruegge liquidus) x 3 inner-core radii (150,
400, 650 km), computed via `tests.conftest.solve_full_model` (cold-start
Newton + shoot, NOT the full driverp.py sweep -- see that function's
docstring for why cold-start reproduces warm-started/published values).

36 (CMR2, CMC, light_element, liquidus_eq, ricb_m) cases; 33 converge,
3 do not (CMR2=0.346/CMC=0.426, light_element='Si', liquidus_eq='Edmund',
all 3 radii tried, plus ricb=10 m and 50010 m in a follow-up probe --
see tests/README.md "Findings": this looks like a genuine
no-solution-from-a-generic-initial-guess case for that one
composition/MOI/liquidus combination, not a bug -- production code
never hits it because driverp.py always warm-starts from a converged
smaller-radius solution, which this generator deliberately does NOT do
(to stay fast and radius-independent)). Both outcomes are committed:
convergence itself, not just the converged VALUES, is part of the
regression contract (a case that used to fail to converge and starts
converging, or vice versa, is exactly the kind of change this guards).

Each entry carries the full scalar set (all 19 `presentday_columns`,
not a subset) and the full radial profile arrays (r, rho, P, T, Tad, g,
chi_li -- same shape as the real per-radius .h5 files main.py writes,
just JSON instead of h5 to keep this small: 512 KB total for all 36
cases, vs ~39 KB PER .h5 file the real pipeline writes x 36 would be
~1.4 MB of binary. Kept as JSON deliberately.

## Regenerating

```
PYTHONNOUSERSITE=1 MPLBACKEND=Agg /usr/bin/python3 \
    tests/reference/self_v1.0.5/wide_sweep/generate_wide_sweep.py
```

Takes ~55 s wall time (36 solves, parallelized across available cores
via `concurrent.futures.ProcessPoolExecutor`). Only regenerate
deliberately (a changed golden is either "fix the bug" or "intended
behaviour change" -- say which, in the commit message).

## If/when a published slice becomes available

The user is separately extracting a wider sample of the published
Zenodo `work.tar` MC results (S/Si endmembers, not just S+Si). If/when
that lands, promote the OVERLAPPING (CMR2, CMC, light_element,
liquidus_eq, ricb) cases from `self_v1.0.5/wide_sweep/` to a new
`zenodo_v1.0.5/wide_sweep/` directory following the same entry schema,
and re-point `test_wide_self_consistency.py`/`test_wide_full_sweep.py`
at whichever of the two is the stronger oracle for each case (published
where available, self-golden elsewhere) -- see
`tests/reference/zenodo_v1.0.5/extract_zenodo_slice.py` for the
established extract-and-checksum pattern to follow.
