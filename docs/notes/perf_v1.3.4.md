# v1.3.4 performance: scalar-call sort-skip in meltingDataFromFile.__call__

Board item 27, re-profiling pass AFTER the v1.3.3 GK21 port landed (which,
per CHANGELOG.md v1.5.1, already shipped DEFAULT ON, not opt-in as the item
27 brief assumed -- the owner's 2026-10-02 ruling moved it from opt-in to
default-on with the divergence bounded by GK21_PORTABLE_RTOL=1e-14).

Canonical case: CMR2=0.346, CMC=0.424, light='S', liquidus='Edmund' (the
Margot fit), same as perf_v1.3.2.md/perf_v1.3.3.md. Pinned environment:
Python 3.12, numpy==2.5.3, scipy==1.18.1 (board item 28e's pie package,
uv-managed venv) -- NOT the numpy==1.21.5/scipy==1.8.0 environment the
earlier two perf notes used (the project migrated to py3.12/uv since,
v1.5.0). All timings on this box (dliu, shared).

## Re-profile finding

Single-radius solve (direct mynewtonSys+shoot_mercmodel call, same
mechanism as testsys/integration/test_present_day_solve.py, at
ricb=500010 m): 2.7 s wall (cProfile-instrumented run: 4.3 s; this note
reports real, non-instrumented wall time throughout -- cProfile adds
roughly 1.6x overhead on this call graph).

cProfile breakdown of the instrumented 4.3 s (cumulative time share):

| function | cumtime | share |
|---|---|---|
| solver.py odeRK4_snow | 3.65 s | 85% |
| libCore.py getchi_li_grun | 3.43 s | 80% |
| coreEos.py eos (eos/Gibbs/volume chain) | 2.30 s | 53% |
| coreEos.py _gk21_panel (vectorised GK21, own time) | 0.66 s | 15% (tottime) |
| coreEos.py volume (own time) | 0.27 s | 6% (tottime) |
| scipy.optimize.root (_root_hybr/hybrd) | 1.00 s | 23% |
| coreEos.py meltingDataFromFile.__call__ (TmFeS melting-curve lookup) | 1.06 s | 25% |
| of which np.sort+np.atleast_1d+np.atleast_2d+np.array wrapping (own time, not the FITPACK call) | 0.46 s | 11% |
| of which the real scipy.interpolate.RectBivariateSpline.__call__ | 0.34 s | 8% |

So post-GK21, the single biggest cost is still eos/Gibbs/GK21 (53%,
already optimized in v1.3.3), scipy.optimize.root's MINPACK hybrd call
(23%, a general N-D solver used for a 1-D scalar root), and -- the new
finding this pass turned up -- the melting-curve lookup wrapper
meltingDataFromFile.__call__ (25%), about 11 points of which is pure
Python call/dispatch overhead (np.sort, np.atleast_1d, np.atleast_2d,
np.array) wrapping a call that, in every real call site
(libCore.TmFeSSi, called both from inside getchi_li_grun's root-find and
from its own direct getCoreLiquidus call), passes SCALAR p and x -- i.e.
length-1 arrays after np.atleast_1d, for which np.sort is provably a
no-op (an array of length <= 1 has nothing to reorder).

Confirmed real-call composition: a spy on libCore.TmFeS.__call__ during a
real solve shows over 99% of real calls pass scalar x and scalar p (see
testsys/unit/test_perf_v1_3_4_melting_sort_skip.py's
TestRealCapturedCallsBitIdentical.test_patched_matches_reference_on_real_calls,
which asserts this fraction directly rather than assuming it).

## The fix

pie/coreEos.py meltingDataFromFile.__call__ (around line 603): skip the
np.sort() call when the (already np.atleast_1d-built) p or x array has
length <= 1, calling the exact same self.TF(...) with the exact same
array contents either way. This is NOT a vectorization/approximation
change like PIE_FAST_QUAD's GK21 port: no new numeric code path, no
reassociated floating-point operation, zero risk of the CubicSpline-style
array-vs-scalar divergence that forced GK21 to need a bounded tolerance --
sorting an array of length 0 or 1 cannot reorder anything, so the result
is bit-identical by construction on every environment, not just the
pinned one. No new env flag is needed or added; this ships default-on.

np.atleast_1d/np.atleast_2d/np.array wrapping (another roughly 0.2 s of
the 1.06 s) was NOT touched -- removing those would mean restructuring
the function's return-shape contract (the len(z)==1 branch depends on
them), a bigger, riskier diff for a smaller remaining win; left as a
documented, not-yet-closed finding below.

## Differential test

testsys/unit/test_perf_v1_3_4_melting_sort_skip.py: three test classes,
on REAL captured (x, p) pairs from an actual present-day Newton solve at
the canonical radius (testsys/pielib.py's own spy mechanism, not a
synthetic fixture):
- TestRealCapturedCallsBitIdentical: the patched __call__ vs a reference
  re-implementation of the exact pre-fix algorithm, on every real
  captured call from one solve (over 1000 calls) -- max diff 0.0 (exact
  equality, not a tolerance).
- TestLengthGreaterThanOneStillSorts: a synthetic length-3,
  descending-order x array still comes back in ascending (sorted) order,
  matching a reference call that explicitly pre-sorts -- proves the skip
  only fires for length <= 1, real np.sort still runs otherwise.
- TestEmptyArrayNoOp: length-0 arrays (the other shape[0] <= 1 case)
  don't crash.

All 3 pass at exact equality (no tolerance loosened, no flag).

## Timing: before / after

Single radius (canonical case, same machine, 3 repeats each):
- Before: 2.71 s, 2.75 s, 2.69 s (mean 2.72 s)
- After: 2.55 s, 2.56 s, 2.56 s (mean 2.56 s)
- Speedup: 1.06x (about 6%)

Small real sweep (5 radii, same canonical composition, ricb in 100, 300,
500.01, 700, 900 km -- the 900 km radius fails its Newton line search on
both before/after, an unrelated pre-existing solver-boundary issue, not a
regression; see PATHWAY_FORWARD.md item 17):
- Before: 18.97 s
- After: 17.96 s
- Speedup: 1.06x (about 5%)

Consistent with the roughly-11-point-of-53% share measured by cProfile
(cProfile overhead itself inflates the wrapping-overhead's apparent share
relative to real wall-clock, since each skipped np.sort/np.atleast_1d
call also carries its own profiler-dispatch cost that the real,
non-instrumented run doesn't pay).

## Full gate: before / after

PYTHONNOUSERSITE=1 MPLBACKEND=Agg PIE_WORKERS=8 .venv/bin/python3.12 testsys/run.py all
(py3.12/uv-managed .venv, pins matching requirements.txt/pyproject.toml):

- Before (unmodified tree, item 9's PR #50 head da0a2d0): 315 passed, 15
  skipped, 3 xfailed, 0 failed (per PATHWAY_FORWARD.md item 9's own
  closing gate run).
- After (this change, src/test edits present but uncommitted at run
  time): 318 passed (315 + 3 new differential tests), 15 skipped, 3
  xfailed, 1 failed -- the 1 failure is
  testsys/contract/test_repo_hygiene.py::test_src_tree_is_unmodified_by_the_test_suite,
  which asserts git status --porcelain -- pie is empty; true before any
  commit (this task's own pie/coreEos.py edit is, correctly, an
  uncommitted modification at the time the gate ran), same resolution
  pattern perf_v1.3.2.md documented for its own analogous run. 598.56s.

## What was NOT done, and why

- scipy.optimize.root (hybrd, 23% of the profiled single-radius solve): a
  general N-D nonlinear solver used here for a 1-D scalar root. A
  dedicated scalar method (bounded Newton, brentq) would very likely be
  faster per call, but its converged value is NOT guaranteed bit-identical
  to hybrd's at the existing tol=1e-6 (different iteration path means a
  different point within the tolerance ball, same class of risk as a
  GK21-style algorithm swap, which needed its own 237057-call differential
  matrix and still had to ship bounded-not-eliminated off the pinned
  environment). Swapping it would need the same scale of validation GK21
  got and an owner ruling on whether a bounded (not bit-identical)
  divergence is acceptable here too -- out of scope for this pass;
  flagged as a finding only, per this porter's own Pattern-4 discipline
  (branch/root-find-dependent code is not safely swapped without that
  validation).
- coreEos.py's CubicSpline.__call__ overhead inside eos()/volume() (the
  other call site with meaningful per-call Python dispatch overhead): NOT
  touched. This is the exact call path whose array-vs-scalar divergence
  broke fast-latest CI during GK21's first default-on attempt
  (docs/notes/perf_v1.3.3.md) -- any change to how this function is
  called reopens that exact landmine and would need the same
  bounded-divergence validation GK21 needed. Left untouched.
- meltingDataFromFile.__call__'s remaining atleast_1d/atleast_2d/np.array
  wrapping (about 0.2 s of the profiled 1.06 s): would need restructuring
  the function's shape-handling contract for a smaller marginal win than
  the sort-skip; not done this pass.
