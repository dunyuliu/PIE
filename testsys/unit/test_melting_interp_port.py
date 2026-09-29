"""Regression guard for the interp2d -> RectBivariateSpline port of
src/coreEos.py `meltingDataFromFile` (PATHWAY_FORWARD.md item 14).

scipy's interp2d (removed in 1.14) on a regular grid fits with FITPACK
regrid_smth (kx=ky=3 for kind='cubic', s=0) and evaluates with bispev;
RectBivariateSpline uses the same two routines, so the port must be
bit-for-bit. This test rebuilds the legacy interp2d interpolator from the
same TmFeSmelt.dat table and compares it with the ported class on a dense
grid inside the table and on points outside it (FITPACK clamps both the
same way). It runs wherever interp2d is still callable (the pinned CI
environment, scipy 1.8.0) and skips on scipy >= 1.14.
"""
import numpy as np
import pytest

import coreEos as eos

pytestmark = pytest.mark.unit


def _legacy_interp2d_or_skip():
    from scipy.interpolate import interp2d
    try:
        interp2d([0.0, 1.0], [0.0, 1.0], np.zeros((2, 2)))
    except NotImplementedError:
        pytest.skip("scipy >= 1.14: interp2d removed; legacy reference unavailable")
    return interp2d


def _read_table(filename="TmFeSmelt.dat"):
    with open(filename) as f:
        f.readline(); f.readline()
        xMin, xMax, nX, pMin, pMax, nP = map(int, f.readline().split())
        T = np.zeros((nX, nP))
        p = np.linspace(pMin, pMax, nP)
        x = np.linspace(xMin, xMax, nX) / 100
        for i in range(nX):
            for j in range(nP):
                T[i, j] = f.readline().split()[2]
    return x, p, T


def test_port_matches_legacy_interp2d_bit_for_bit():
    interp2d = _legacy_interp2d_or_skip()
    x, p, T = _read_table()
    legacy = interp2d(p, x, T, kind="cubic")
    ported = eos.meltingDataFromFile("TmFeSmelt.dat")

    xs = np.concatenate([np.linspace(x[0], x[-1], 41), [x[0] - 0.05, x[-1] + 0.05]])
    ps = np.concatenate([np.linspace(p[0], p[-1], 41), [p[0] - 5.0, p[-1] + 5.0]])
    worst = 0.0
    for xi in xs:
        for pi in ps:
            old = legacy(pi, xi)[0]
            new = ported(xi, pi)
            assert np.shape(new) == np.shape(old)
            worst = max(worst, abs(float(new) - float(old)))
    assert worst == 0.0, f"port differs from interp2d by up to {worst!r} K"


def test_port_returns_scalar_for_scalar_query():
    tm = eos.meltingDataFromFile("TmFeSmelt.dat")
    v = tm(0.1, 20.0)
    assert np.ndim(v) == 0 and np.isfinite(v)
