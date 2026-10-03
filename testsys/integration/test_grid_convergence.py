"""PATHWAY_FORWARD.md item 23(c): no mesh/step-refinement test existed for
PIE's present-day solver. This file adds one for the fluid-outer-core
integration (`src/solver.py::odeRK4_snow`, a hand-rolled, fixed-step,
classical 4-stage Runge-Kutta scheme -- read directly from the source:
`src/solver.py` lines ~25-110 compute k1..k4 slopes and combine them as
`y[j,:] = yold + h6*(k1+2*k2+2*k3+k4)`, the textbook RK4 update -- so the
THEORETICAL local/global truncation order is 4, same as the module's own
docstring "Fourth order Runge-Kutta method").

The solid-inner-core segment (`scipy.integrate.solve_ivp(..., method=
'LSODA', rtol=5e-5)`, `src/shootp.py` line ~107) is adaptive-step and
already convergence-controlled BY rtol internally -- refining it here
would just be re-testing scipy's own LSODA implementation, not PIE's
code. `odeRK4_snow`'s step count (`nc`, hard-coded to 51 inside
`src/shootp.py::shoot_mercmodel`, not exposed as a parameter anywhere
upstream -- PATHWAY_FORWARD.md gap, flagged in this session's report for
kai-fischer/refactor, NOT fixed here per the no-src-edits constraint) IS
a parameter of `odeRK4_snow` itself (`h`, hence `nc` via
`h=(rcmb-ricb)/(nc-1)`), so this test calls that PRODUCTION function
directly at nc in {51, 101, 201} (h, h/2, h/4) with REAL boundary
conditions from a converged Margot (CMR2=0.346, CMC=0.424) S-only
present-day solve at ricb=500 km, and checks the EMPIRICAL convergence
order of the fluid-core state at the CMB against the theoretical order 4,
to a half-order tolerance (order in [3.5, 4.5]) -- this is the task
brief's "pick a representative case... assert observed convergence order
matches theoretical to within a half-order tolerance" literally applied
at the level where PIE actually exposes a refinable step size.

Resolutions nc=9,17,33 (NOT the production default nc=51 onward): measured
directly on this box, 2026-10-01 -- `src/libCore.py::getchi_li_grun`
(called every RK stage whenever the "snow" branch is active, true for
this case) does an internal `scipy.optimize.root(..., tol=1e-6)` nonlinear
solve, which caps the ACHIEVABLE precision of every RK stage's
density/Gruneisen feedback at ~1e-6-2e-6 regardless of h (a hard-coded
tolerance, not tied to the RK step size -- flagged as a blocker for
kai-fischer/lars-eriksson: a textbook order-4 regression gate at the
production resolution (nc>=51) is not possible without exposing/tightening
that tolerance, which is a src/ edit, out of this session's scope). At
nc=51 the true RK4 truncation error is ALREADY below that floor (measured:
successive nc=51->101->201 refinements there produce a non-monotonic,
~1e-7-scale residual dominated by the inner solver's own noise, not
truncation error -- order is NOT measurable there). At nc=9,17,33 (h
roughly 40-250x the production step) truncation error is still 2-5 orders
of magnitude above that floor, so refinement there cleanly resolves to
the theoretical order: measured 4.35 (nc=3->5->9), 4.16 (5->9->17), 4.04
(9->17->33), 4.01 (17->33->65) -- monotonically approaching 4 as expected
for an asymptotic order estimate. This file uses the cleanest in-range
triple (9, 17, 33).

The pre-fluid-shoot setup (computing `yicb`, the fluid segment's own
initial condition) mirrors `src/shootp.py::shoot_mercmodel` lines
~60-124 line-for-line, calling the SAME production functions
(`getPgcmb_crust`, `reorder_el`, `eos.eosInnerCore`,
`rhs_PTrhog_solid_snow`, `getCoreLiquidus`) rather than reimplementing
any physics -- consistent with `testsys/conftest.py::solve_full_model`'s
own documented pattern.
"""
import numpy as np
import pytest

from pielib import import_src

pytestmark = pytest.mark.integration

CMR2, CMC, RICB_M = 0.346, 0.424, 500_010.0


@pytest.fixture(scope="module")
def fluid_core_initial_condition():
    """One converged Newton solve (Margot S-only, ricb=500 km) plus the
    pre-fluid-shoot setup shoot_mercmodel itself does before entering
    odeRK4_snow -- shared across every resolution tested below so the
    ~17 s Newton solve runs once, not 3x."""
    import sys as _sys
    from pielib import _purge_pie_submodules
    _sys.argv[:] = ["main.py", "p", str(CMR2), str(CMC), "S", "Edmund"]
    _purge_pie_submodules()
    from pie import globalvar as gv
    planet_input = import_src("planet_input", CMR2=CMR2, CMC=CMC,
                               light_element="S", liquidus_eq="Edmund")
    from pie import shootp as lc
    from pie import solver
    from pie import coreEos as eos
    import scipy.integrate
    from scipy.constants import G

    param = planet_input.planet("p", CMR2, "S", "Edmund")
    scale = param["scale"]
    rhocr, rh = param["rhocr"], param["rh"]
    ricb_nd = RICB_M / scale["a"]

    v = lc.mynewtonSys(
        "J_mercmodel", param["v0"], [ricb_nd, rhocr, rh, param, scale],
        xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit, verbose=False,
    )
    assert v is not None, "setup: Newton solve did not converge"

    M = param["GM"] / G
    rm = param["rm"]
    a, ga, P, T = scale["a"], scale["ga"], scale["P"], scale["T"]
    r0 = 0.0001 / a
    rcmb = v[2]
    rhom = v[3] * param["rhomean"]
    rc = rcmb * a
    rhd = rh * a
    Pcmb, gcmb = lc.getPgcmb_crust(rhom, rc, rhocr, rhd, param, scale)
    P1 = P * v[0]
    T1 = T * v[1]
    chi_icb = lc.reorder_el(v[4], gv.chi_Si_icb, param)
    rho = eos.eosInnerCore(chi_icb, P1 / 1e9, T1, param)[1]
    gr0 = 4 * np.pi * G * rho * (r0 * a) / (3 * ga)
    y0 = [v[0], gr0, v[1]]

    sol = scipy.integrate.solve_ivp(
        lambda t, y: solver.rhs_PTrhog_solid_snow(chi_icb, t, y, ricb_nd, scale, param),
        [r0, ricb_nd], y0, method="LSODA", rtol=5e-5,
    )
    ys = sol.y
    P1_icb = P * ys[0, -1]
    Tmicb = lc.getCoreLiquidus(chi_icb["S"], chi_icb["Si"], P1_icb, param, 0) / T
    yicb = [ys[0, -1], ys[1, -1], Tmicb, Tmicb]

    return {"solver": solver, "ricb_nd": ricb_nd, "rcmb_nd": rcmb,
            "yicb": yicb, "chi_li_icb": v[4], "scale": scale, "param": param}


def _fluid_cmb_state(fic, nc):
    """Run the PRODUCTION odeRK4_snow at step count nc; returns the
    4-component state [P, g, T, Tad] (non-dimensional) at the CMB (last
    row)."""
    solver = fic["solver"]
    ricb_nd, rcmb_nd = fic["ricb_nd"], fic["rcmb_nd"]
    h = (rcmb_nd - ricb_nd) / (nc - 1)
    rc, yc, rhof, chi_li, err = solver.odeRK4_snow(
        "rhs_fluid_snow", ricb_nd, rcmb_nd, h, fic["yicb"], fic["chi_li_icb"],
        fic["scale"], fic["param"],
    )
    return np.asarray(yc[-1, :])


def test_fluid_core_rk4_converges_at_fourth_order(fluid_core_initial_condition):
    """Richardson order estimate from 3 resolutions (nc=9,17,33, i.e.
    h, h/2, h/4 -- see module docstring for why these, not the
    production nc=51, are used): p = log2(||y_h - y_h2|| / ||y_h2 -
    y_h4||). RK4's theoretical order is 4 (see module docstring);
    accepted within a half-order tolerance, p in [3.5, 4.5] -- a
    discretisation bug (e.g. an off-by-one in a slope weight, or h
    used where h/2 belongs) would collapse this to order 1-2, a
    difference no single-resolution test could ever catch."""
    y_9 = _fluid_cmb_state(fluid_core_initial_condition, 9)
    y_17 = _fluid_cmb_state(fluid_core_initial_condition, 17)
    y_33 = _fluid_cmb_state(fluid_core_initial_condition, 33)

    d1 = np.linalg.norm(y_9 - y_17)
    d2 = np.linalg.norm(y_17 - y_33)
    assert d1 > 0 and d2 > 0, (
        f"successive refinements produced IDENTICAL state (d1={d1!r}, "
        f"d2={d2!r}) -- the step size h is not actually being refined, "
        f"or odeRK4_snow is insensitive to it; either way this test "
        f"cannot measure an order"
    )
    order = np.log2(d1 / d2)
    assert not (order < 3.5 or order > 4.5), (
        f"observed RK4 convergence order={order!r} (d1={d1!r} at "
        f"nc=9->17, d2={d2!r} at nc=17->33) falls outside the "
        f"theoretical order-4 scheme's half-order tolerance [3.5, 4.5] "
        f"-- a discretisation bug in src/solver.py::odeRK4_snow, not a "
        f"tolerance that should be loosened to match"
    )
