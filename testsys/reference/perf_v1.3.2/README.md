# v1.3.2 perf fixture: real_solver_states.npz

Captured from one real Newton+shoot solve (CMR2=0.346, CMC=0.424, S,
Edmund, ricb=500010 m -- the same canonical case as
testsys/integration/test_present_day_solve.py) by monkeypatching
`libCore.getpotvsr`/`shootp.J_mercmodel` to record their real inputs
(the sparse sweep matrix `A` + rhs passed to `inv(A)*rhs`, and the dense
Jacobian `J` + residual `f` passed to `np.linalg.inv(J)@f`) without
changing any control flow.

Regenerate with:

```
PYTHONNOUSERSITE=1 MPLBACKEND=Agg .venv/bin/python3 \
    testsys/reference/perf_v1.3.2/generate_real_solver_states.py
```

(edit the hard-coded `SRC`/output path at the top of the script to point
at your checkout before running). `A` is stored as its 3 CSC arrays
(data/indices/indptr) + shape, not as a dense 799x799 array, to keep the
committed fixture small (~150KB vs ~15MB dense).

Used by testsys/unit/test_perf_v1_3_2_linear_solves.py.
