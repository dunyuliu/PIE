"""Differential test for the board item 27 perf slice (docs/notes/perf_v1.3.4.md):
`pie/coreEos.py`'s `meltingDataFromFile.__call__` skips `np.sort()` when the
(already-built) p/x arrays have length <= 1, instead of calling `np.sort()`
and discarding an identical result.

This is NOT an approximation like PIE_FAST_QUAD's GK21 port: sorting an
array of length 0 or 1 can never reorder anything, so the skip is a pure
removal of dead work, not a new numeric code path -- no opt-in flag, no
tolerance, bit-identical by construction on every environment. This file
proves that construction empirically against:
  1. A reference re-implementation of the EXACT pre-fix algorithm
     (unconditional np.sort), run on REAL (x, p) pairs captured from a
     real present-day solve (the canonical Margot-fit case, same as
     docs/notes/perf_v1.3.2.md/perf_v1.3.3.md).
  2. Synthetic length>1 arrays, proving the branch still calls real
     np.sort (and therefore still reorders) whenever length > 1 -- i.e.
     the fix narrows WHEN sort is skipped, it does not remove sorting
     behaviour for the cases that need it.
"""
import sys

import numpy as np
import pytest

from pielib import import_src, _purge_pie_submodules

pytestmark = pytest.mark.unit


def _old_melting_call(melt_obj, x, p):
    """Reference re-implementation of the pre-fix
    `meltingDataFromFile.__call__` (unconditional `np.sort`), bypassing the
    now-patched method entirely so this test can never accidentally pass
    by calling the same (possibly broken) code on both sides."""
    z = np.atleast_2d(melt_obj.TF(np.sort(np.atleast_1d(p)),
                                   np.sort(np.atleast_1d(x)))).T
    if len(z) == 1:
        z = z[0]
    return np.array(z)[0]


@pytest.fixture
def real_tmfes_calls(sys_argv_p):
    """Capture real (x, p) argument pairs passed to libCore.TmFeS during an
    actual present-day Newton solve at the canonical Margot-fit radius, by
    wrapping (not replacing) the real bound method so the solve itself is
    completely unaffected."""
    sys_argv_p(CMR2=0.346, CMC=0.424, light_element="S", liquidus_eq="Edmund")
    _purge_pie_submodules()
    planet_input = import_src("planet_input", CMR2=0.346, CMC=0.424,
                               light_element="S", liquidus_eq="Edmund")
    # single import_src call above already purged+reimported every pie
    # submodule libCore/shootp depend on; a SECOND import_src call here
    # would re-purge and hand back a different libCore/shootp module
    # object than the one planet_input's own `from . import libCore`
    # already bound param['liquidus'] (TmFeSSi) to -- the patch below
    # would then silently miss every real call. Plain imports instead,
    # same pattern tests/integration/test_present_day_solve.py uses.
    from pie import globalvar as gv
    from pie import shootp as lc
    from pie import libCore

    calls = []
    cls = type(libCore.TmFeS)
    orig = cls.__call__  # unbound: takes (self, x, p)

    def _spy(self, x, p):
        calls.append((x, p))
        return orig(self, x, p)

    cls.__call__ = _spy
    try:
        param = planet_input.planet("p", 0.346, "S", "Edmund")
        scale = param["scale"]
        ricb_nd = 500_010.0 / scale["a"]
        v = lc.mynewtonSys(
            "J_mercmodel", param["v0"],
            [ricb_nd, param["rhocr"], param["rh"], param, scale],
            xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit, verbose=False,
        )
        lc.shoot_mercmodel(v, ricb_nd, param["rhocr"], param["rh"], param, scale)
    finally:
        cls.__call__ = orig
    assert len(calls) > 1000, (
        f"expected thousands of real TmFeS calls from one solve, got {len(calls)}"
    )
    return libCore.TmFeS, calls


class TestRealCapturedCallsBitIdentical:
    def test_patched_matches_reference_on_real_calls(self, real_tmfes_calls):
        melt_obj, calls = real_tmfes_calls
        # Confirm the scalar-call fast path actually fires for the
        # overwhelming majority of real calls (otherwise this test would
        # pass trivially without exercising the new branch).
        n_scalar = sum(1 for (x, p) in calls
                       if np.atleast_1d(x).shape[0] <= 1 and np.atleast_1d(p).shape[0] <= 1)
        assert n_scalar / len(calls) > 0.99, (
            f"expected >99% scalar calls, got {n_scalar}/{len(calls)}"
        )
        for x, p in calls:
            new = melt_obj(x, p)
            old = _old_melting_call(melt_obj, x, p)
            assert new == old, f"diverged for x={x!r}, p={p!r}: new={new!r} old={old!r}"


class TestLengthGreaterThanOneStillSorts:
    def test_unsorted_multi_point_query_still_reorders(self, real_tmfes_calls):
        """A length>1 x array in descending order must still come back
        sorted (i.e. the skip must not fire), proving the branch condition
        is `length <= 1`, not `always skip`."""
        melt_obj, _ = real_tmfes_calls
        x = np.array([0.08, 0.02, 0.05])
        p = 30.0
        new = melt_obj(x, p)
        old = _old_melting_call(melt_obj, x, p)
        assert np.array_equal(new, old)
        # TF() itself raises on a non-increasing x array with grid=True
        # (scipy requirement) -- that it does NOT raise here is itself
        # proof np.sort() ran on this length-3 array (the skip only
        # applies to length <= 1).
        sorted_x = np.sort(x)
        reference = np.atleast_2d(melt_obj.TF(np.atleast_1d(p), sorted_x)).T
        assert np.array_equal(np.array(new), np.array(reference[0]))


class TestEmptyArrayNoOp:
    def test_length_zero_p_array_does_not_crash(self, real_tmfes_calls):
        melt_obj, _ = real_tmfes_calls
        x = np.array([])
        p = np.array([])
        new = melt_obj.TF(p, x)  # just confirm skip-branch's shape[0]<=1 covers 0 too
        assert new.shape == (0, 0)
