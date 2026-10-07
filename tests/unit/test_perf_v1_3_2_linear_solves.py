"""Differential tests for the v1.3.2 performance port (PATHWAY_FORWARD.md
perf item, docs/notes/perf_v1.3.2.md): two dense-inverse-for-a-single-rhs
call sites replaced with a direct linear solve, no algorithm/matrix change.

Profiling (cProfile, one Newton solve at the canonical Margot-fit radius,
CMR2=0.346/CMC=0.424, S, Edmund, ricb=500010 m) found:
  - src/libCore.py:getpotvsr's `b = inv(A)*rhs` (scipy.sparse.linalg.inv)
    computed the FULL dense inverse of a 799x799 sparse SuperLU-factored
    matrix to multiply it by ONE rhs vector: ~8.6s of an 18.4s single-radius
    solve (47%). Replaced with `scipy.sparse.linalg.spsolve(A, rhs)`, same
    A, same rhs -- single-radius cost for this call site drops to ~0.17s
    (28 calls; getpotvsr's own loop overhead, not the solve, dominates
    what's left).
  - src/shootp.py:mynewtonSys's `dx = np.dot(np.linalg.inv(J), f)` is the
    same anti-pattern on a dense 5x5 Jacobian (negligible wall-clock on
    its own, but same bug class) -- replaced with `np.linalg.solve(J, f)`.
  - src/shootp.py:getk2's and src/solver.py:odeRK4_snow's Python loops
    (the brief's other named candidates) were profiled and NOT touched:
    getk2's own loop tottime is ~0.04s of the 9.6s post-fix single-radius
    total (<0.5%); odeRK4_snow is a sequential RK4 stepper whose stages
    depend on each other and on a root-find (scipy.optimize.root) and
    adaptive quadrature (scipy.integrate.quad) inside coreEos.py, not a
    loop over independent grid points -- not a "straightforward,
    behaviour-preserving" vectorization target, and it is now the
    dominant remaining cost (~7.9s of 9.6s, 82%); see the Numba proposal
    in docs/notes/perf_v1.3.2.md.

This file is the parity gate for the two solves that WERE changed: both
the optimized (current src/) and a reference re-implementation of the
EXACT pre-v1.3.2 algorithm (dense inverse) are called on the SAME real
solver states -- captured from an actual Newton solve at the canonical
radius above (tests/reference/perf_v1.3.2/real_solver_states.npz;
regeneration script: tests/reference/perf_v1.3.2/README.md) -- and must
agree to 1e-12.
"""
import pathlib

import numpy as np
import pytest
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import inv as sparse_inv

pytestmark = pytest.mark.unit

from pielib import import_src

FIXTURE = (pathlib.Path(__file__).resolve().parent.parent / "reference"
           / "perf_v1.3.2" / "real_solver_states.npz")


@pytest.fixture(scope="module")
def states():
    assert FIXTURE.exists(), (
        f"{FIXTURE}: missing real-solver-state fixture -- regenerate per "
        f"tests/reference/perf_v1.3.2/README.md, do not skip silently"
    )
    return np.load(FIXTURE)


def _sparse_matrices(states):
    n = int(states["n_A"])
    mats = []
    for i in range(n):
        data = states[f"A{i}_data"]
        indices = states[f"A{i}_indices"]
        indptr = states[f"A{i}_indptr"]
        shape = tuple(states[f"A{i}_shape"])
        from scipy.sparse import csc_matrix as _csc
        A = _csc((data, indices, indptr), shape=shape)
        rhs = states[f"rhs{i}"]
        mats.append((A, rhs))
    return mats


def _dense_jacobians(states):
    n = int(states["n_J"])
    return [(states[f"J{i}"], states[f"f{i}"]) for i in range(n)]


# ---------------------------------------------------------------------
# getpotvsr's linear solve: reference = pre-v1.3.2 `inv(A)*rhs`
# ---------------------------------------------------------------------

def _reference_dense_inverse_solve(A, rhs):
    """The EXACT pre-v1.3.2 algorithm: scipy.sparse.linalg.inv(A) (full
    dense inverse via SuperLU factor + ndim back-substitutions) times rhs.
    Kept here, not in src/, as the parity oracle for the optimized solve."""
    return sparse_inv(A) * rhs


@pytest.fixture
def libcore(sys_argv_p):
    return import_src("libCore")


def test_getpotvsr_linear_solve_matches_dense_inverse_reference(states):
    """spsolve(A, rhs) (current src/libCore.py) vs inv(A)*rhs (reference),
    on 3 REAL A/rhs pairs captured mid-solve (not synthetic): the fluid-
    core grid potential solves at 3 different Newton/line-search trial
    iterates of the canonical Margot-fit radius."""
    from scipy.sparse.linalg import spsolve
    for i, (A, rhs) in enumerate(_sparse_matrices(states)):
        b_new = spsolve(A, rhs)
        b_ref = _reference_dense_inverse_solve(A, rhs)
        b_ref = np.asarray(b_ref).ravel()
        b_new = np.asarray(b_new).ravel()
        assert b_new.shape == b_ref.shape
        scale = np.maximum(np.abs(b_ref), 1e-12)
        reldiff = np.abs(b_new - b_ref) / scale
        assert np.all(reldiff < 1e-12), (
            f"pair {i}: max rel diff {reldiff.max():.3e} between spsolve "
            f"and the dense-inverse reference exceeds 1e-12"
        )


def test_getpotvsr_end_to_end_matches_with_reference_solve_monkeypatched(
    states, libcore, monkeypatch
):
    """Stronger check than the bare linear-algebra comparison above: run
    the ACTUAL getpotvsr function twice on the same (nr, bigGnd, rnd, rhond,
    gnd) -- once with the current spsolve, once with the dense-inverse
    reference monkeypatched in via libCore's own `inv` import -- and
    diff the returned potential array `pot`."""
    import scipy.sparse.linalg as spla

    nr = 400
    rnd = np.linspace(1e-3, 1.0, nr)
    rhond = np.linspace(8000.0, 3000.0, nr)
    gnd = np.linspace(0.1, 3.7, nr)
    bigGnd = 1.0

    pot_new = libcore.getpotvsr(nr, bigGnd, rnd, rhond, gnd)

    real_spsolve = spla.spsolve

    def reference_spsolve(A, rhs):
        return np.asarray(sparse_inv(A) * rhs).ravel()

    monkeypatch.setattr(libcore, "spsolve", reference_spsolve)
    pot_ref = libcore.getpotvsr(nr, bigGnd, rnd, rhond, gnd)
    monkeypatch.setattr(libcore, "spsolve", real_spsolve)

    scale = np.maximum(np.abs(pot_ref), 1e-12)
    reldiff = np.abs(pot_new - pot_ref) / scale
    assert np.all(reldiff < 1e-12), f"max rel diff {reldiff.max():.3e}"


# ---------------------------------------------------------------------
# mynewtonSys's Newton step: reference = pre-v1.3.2 `inv(J) @ f`
# ---------------------------------------------------------------------

def test_newton_step_solve_matches_dense_inverse_reference(states):
    """np.linalg.solve(J, f) (current src/shootp.py) vs the pre-v1.3.2
    np.dot(np.linalg.inv(J), f), on REAL 5x5 Jacobians/residuals captured
    across 4 Newton iterations of the canonical Margot-fit radius solve."""
    for i, (J, f) in enumerate(_dense_jacobians(states)):
        dx_new = np.linalg.solve(J, f)
        dx_ref = np.dot(np.linalg.inv(J), f)
        scale = np.maximum(np.abs(dx_ref), 1e-12)
        reldiff = np.abs(dx_new - dx_ref) / scale
        assert np.all(reldiff < 1e-12), (
            f"iteration {i}: max rel diff {reldiff.max():.3e} between "
            f"np.linalg.solve and the dense-inverse reference exceeds 1e-12"
        )
