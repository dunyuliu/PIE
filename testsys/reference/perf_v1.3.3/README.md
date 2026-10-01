# v1.3.3 perf fixture: real_quad_calls.npz

2000 real `(a, b, T)` triples (stratified random sample, fixed seed, out of
237057 captured), actually passed to
`integrate.quad(lambda x: self.volume(x,T), a, b)` inside
`eosAndersonGrueneisen.Gibbs` (`src/coreEos.py`) during real Newton+shoot
solves, captured by monkeypatching `Gibbs` to record its quad call's
`full_output=1` infodict without changing control flow -- same technique
as `testsys/reference/perf_v1.3.2/`.

Matrix: S / Si / S+Si light elements x Edmund / Steinbruegge liquidus x
ricb in {10 m, 500010 m (canonical Margot-fit), 1800000 m (near-rcmb
attempt)}.

Convergence notes (NOT a quad/GK21 issue -- pre-existing Newton-solver
boundary behaviour at CMR2=0.346/CMC=0.424, recorded here so a future
run doesn't re-diagnose the same thing):
- Every composition failed to converge at ricb=1,800,000 m
  (`CHI_OUTSIDE_ADMISSIBLE_BOX` or `NONFINITE_SHOOT`) -- this CMR2/CMC
  pair's admissible inner-core-radius range does not reach that far.
- Si/Edmund failed to converge at EVERY radius tried (10 m, 500010 m,
  1800000 m), same error class.
- All other (light, liquidus) x (10 m, 500010 m) combinations converged
  and contributed real quad calls (6 of 9 compositions x 2 radii = 12 of
  18 attempted cells).

Every one of the 237057 real captured calls has QUADPACK `last == 1`
(single Gauss-Kronrod panel, no subdivision) -- the single-panel claim
holds for the full real-solver matrix that converges. It does NOT hold
universally: a direct (non-solver) sweep of `eos.Gibbs`/`quad` over the
full admissible pressure domain (up to `pMax=200` GPa vs ~39 GPa reached
by any real Mercury-core solve above) shows subdivision (`last` in {2, 3})
once the integration interval gets wide enough. This is exactly why
`coreEos._gk21_or_quad`'s fallback is a per-call runtime check (replaying
`dqagse.f`'s own accept test), not a one-time global switch -- see that
function's docstring.

Regenerate with:

```
PYTHONNOUSERSITE=1 MPLBACKEND=Agg PYTHONWARNINGS=ignore \
    /home/utig5/dliu/PIE/.venv/bin/python3 \
    testsys/reference/perf_v1.3.3/generate_real_quad_calls.py
```

Used by testsys/unit/test_perf_v1_3_3_gk21_quad.py.
