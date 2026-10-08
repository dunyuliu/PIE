# v1.3.2 performance pass: profile findings, fixes, numbers

Canonical case used throughout: CMR2=0.346, CMC=0.424, light='S',
liquidus='Edmund' (the Margot fit) -- same inputs as
testsys/integration/test_present_day_solve.py (single radius,
ricb=500010 m) and testsys/e2e/test_full_composition_sweep.py (full
~40-radius sweep). All timings on this box (dliu, shared; load average
~12-20 throughout this session).

## Profile findings (baseline, current main / v1.3.1, cProfile on one
Newton solve + final shoot at ricb=500010 m)

Single-radius solve: **18.37 s** wall.

| function | cumtime | share of 18.37s |
|---|---|---|
| `scipy.sparse.linalg.inv(A)` (-> internal SuperLU `spsolve` against all 799 unit rhs) | 8.627 s | 47% |
| of which `SuperLU.solve` itself | 3.537 s | 19% |
| of which sparse-matrix bookkeeping around it (`_compressed.__init__`, `check_format`, `_major_index_fancy`, `.toarray()`, `prune`, `get_index_dtype`) | ~3.0 s | 16% |
| `coreEos.py` `eos`/`volume`/`Gibbs` (via `scipy.integrate.quad`) | 7.3 s | 40% (overlaps with the next row) |
| `scipy.interpolate._interpolate.__call__` | 3.76 s | 20% |

`libCore.getpotvsr`'s own Python loop (building the sparse matrix's
row/col/s triplets, nr=400) and `shootp.getk2`'s own Python loops
(radial grid / rho / g arrays, nr=400) are cheap standalone: 0.156 s
and 0.044 s tottime respectively (<1% each of 18.37 s).

Root cause in `getpotvsr`: `scipy.sparse.linalg.inv(A)` factorizes A
once via SuperLU and back-substitutes against ALL 799 unit columns of
the identity to form the full dense inverse -- but the code only ever
needs `inv(A) @ rhs` for ONE rhs vector. Exactly the task brief's named
"inv(A)*rhs" anti-pattern. The same anti-pattern, much smaller in
absolute cost, is in `shootp.mynewtonSys`'s Newton step:
`dx = np.dot(np.linalg.inv(J), f)` on the dense 5x5 Jacobian.

## Fixes applied (same matrix/Jacobian, only the solve method changed)

1. `src/libCore.py:getpotvsr`: `b = inv(A)*rhs` -> `b = spsolve(A, rhs)`.
2. `src/shootp.py:mynewtonSys`: `dx = np.dot(np.linalg.inv(J), f)` ->
   `dx = np.linalg.solve(J, f)`.

Neither `A`/`rhs` (matrix construction) nor `J`/`f` (Jacobian
construction) was touched -- only the linear-solve call.

## getk2 / shoot-routine loops: profiled, NOT vectorized

Re-profiling after fix #1 above (single radius now 9.62 s) shows
`getk2`'s own Python loops cost 0.043 s tottime over 28 calls per
radius -- under 0.5% of the new 9.62 s total. The brief's named
candidate did not pan out once the dominant cost (spsolve fix) was
removed; vectorizing it would buy negligible wall-clock while risking
the bit-identical recurrence in its `g[k] = ... + g[k-1]*(...)**2`
accumulation (and a documented bit-identical-recompute quirk at the
nrs+1 boundary) for no measured benefit. Not done, by design, per the
brief's own "confirm with your own profile before changing anything."

The new dominant cost post-fix is `solver.py:odeRK4_snow` (7.92 s of
9.62 s, 82%) -- a sequential RK4 ODE stepper whose 4 stages each depend
on the previous stage's state through `libCore.getchi_li_grun`
(`scipy.optimize.root` + `coreEos.py`'s Gibbs-free-energy integral via
`scipy.integrate.quad`). This is not a loop over independent grid
points; it is a genuinely sequential, branch- and root-find-dependent
algorithm (Pattern 4 in this porter's own discipline notes) and
vectorizing it would require an algorithm change, not a straightforward
rewrite -- out of scope. See the Numba proposal below.

## Timings: before / after

Single radius (same canonical case, same machine):
- Before: 18.37 s
- After: 9.62 s (1.91x)

Full sweep, one composition (CMR2=0.346/CMC=0.424/S/Edmund, all 40
radii attempted per the v1.3.0 sweep policy -- untouched here):
- Before: 1675 s (27m55s), launched 2026-09-30 23:50:05, finished
  2026-10-01 00:18:00 (wall time via process-exit timestamp).
- After: 921 s (15m21s), launched 2026-09-30 23:33:56, finished
  2026-09-30 23:49:17.
- Speedup: 1.82x.
- The per-radius ratio (1.91x) is slightly higher than the full-sweep
  ratio (1.82x) because several radii fail fast (RICB_GE_RCMB,
  singular Jacobian) before ever reaching getpotvsr, diluting the win
  on those rows.
- Full-sweep output csv rows are IDENTICAL row-for-row in error_code,
  start ('warm'/'cold'), newton_iters, and isnow/isnowcmb between
  before/after; every continuous physical field (rhom, Picb, Tcmb,
  chi_li_in, ...) agrees to 1e-8 to 1e-10 relative -- solver-noise
  level from the floating-point reassociation in the SuperLU
  single-rhs-vs-all-rhs solve path, not a correctness regression
  (diffed directly, not inferred: see
  testsys/e2e/test_full_composition_sweep.py's own golden tolerance of
  rtol=1e-4 for comparison, 2-6 orders of magnitude looser than what
  was actually measured here).

## Differential parity test (1e-12)

`testsys/unit/test_perf_v1_3_2_linear_solves.py`: compares the
optimized `spsolve`/`np.linalg.solve` call sites against a reference
re-implementation of the exact pre-v1.3.2 `inv(A)*rhs` / `inv(J)@f`
algorithm, on REAL solver states captured mid-solve from the canonical
Margot-fit radius (`testsys/reference/perf_v1.3.2/real_solver_states.npz`,
regenerate via `testsys/reference/perf_v1.3.2/generate_real_solver_states.py`,
see its README). Measured max relative difference:
- `spsolve` vs `inv(A)*rhs` (sparse, 3 real A/rhs pairs): **0.0** (bit-identical).
- `np.linalg.solve` vs `inv(J)@f` (dense 5x5, 4 real Jacobian/residual
  pairs across one Newton solve): max 5.7e-14.

All 3 tests pass at the full 1e-12 tolerance (no loosening needed).

## Full gate: before / after

`PYTHONNOUSERSITE=1 MPLBACKEND=Agg PIE_WORKERS=8 .venv/bin/python3 testsys/run.py all`

- Before (baseline, unmodified v1.3.1 src/): **251 passed, 14 skipped,
  3 xfailed, 0 failed**, 2029.52 s (33m49s).
- After (src/ changes + new differential test file, uncommitted):
  **253 passed, 14 skipped, 3 xfailed, 1 failed**, 1092.94 s (18m12s).
  The 1 failure is `testsys/contract/test_repo_hygiene.py::
  test_src_tree_is_unmodified_by_the_test_suite`, which asserts
  `git status --porcelain -- src` is empty -- true before any commit,
  since this task's own src/ edits are, correctly, uncommitted
  modifications at the time the gate ran. Resolves on commit (verified:
  the 2 unit tests that monkeypatched the OLD `inv` name
  (`test_getpotvsr_wraps_superlu_singular_matrix`,
  `test_getpotvsr_raises_on_nonfinite_solution`) and the 1 source-text
  check tied to the literal `"b = inv(A)*rhs"` string
  (`test_libcore_getpotvsr_wraps_the_superlu_inversion`) were updated
  in the same commit to target `spsolve` / the new line, preserving
  their original protective intent -- not weakened, not deleted).
  253 = 251 (unaffected baseline tests, including the 3 updated ones,
  still passing) + 3 (new differential tests) - 1 (hygiene test flips
  passed->failed because of the pending commit, not a regression).
  Full gate run twice total before any commit was made (not reused from
  a stale run): see the two full `testsys/run.py all` invocations this
  session, timestamped in the shell history this note was written
  from.

## Numba proposal (not implemented, per owner constraint)

`solver.py:odeRK4_snow` and the `coreEos.py` EOS functions it calls are
now the dominant cost (82% of a single-radius solve) and are NOT
loop-over-independent-grid-points code (see above) -- not a
"straightforward, behaviour-preserving" vectorization target under
this task's scope. A `numba.njit` JIT on `coreEos.py`'s inner scalar
functions (`eos`/`volume`/`Gibbs`: 548604 calls, 2.56 s tottime in the
`volume` function alone) might close part of the gap, since they are
simple arithmetic with no scipy calls -- but the actual bottleneck one
level up is `scipy.integrate.quad`'s adaptive subdivision (`_qagse`,
6.4 s cumtime across 26124 calls), whose C internals cannot be
JIT-compiled from the Python side. A real win would mean replacing
adaptive quadrature with a fixed-order rule amenable to vectorized/
JIT batching -- an ALGORITHM change requiring its own parity
re-derivation against the current adaptive-quadrature reference, well
outside "same matrix, faster solve." Flagged as a finding only, per
the owner's explicit "Numba is a proposal, not an action" constraint --
no numba dependency or code added.

## What was NOT done, and why

- `shootp.py:getk2`'s per-point loops: profiled, confirmed cheap
  (<0.5% of post-fix single-radius time); not vectorized (see above).
- `solver.py:odeRK4_snow`: sequential RK4 + root-find + adaptive
  quadrature, not a grid loop; not vectorized (see Numba proposal).
- No process-parallel Jacobian shoots: not attempted, per explicit
  owner constraint.
- No change to the warm/cold-start sweep policy in `driverp.py`: not
  touched, per explicit owner constraint (confirmed: `driverp.py` has
  no diff in this change).
