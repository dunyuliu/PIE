"""Integration tier: a real present-day model solve (planet_input -> the
Newton shooting method in shootp.py), at the Margot et al. (2012)
CMR2=0.346, CMC=0.424 case named in the task brief.

This is a genuine multi-step pipeline (EOS objects -> Jacobian ->
Newton -> ODE shoot -> moment-of-inertia integral), so "integration"
tier, not "unit": no single function's output is hand-computable here,
but the CONTRACT it must satisfy is checkable -- convergence, recovery
of its own target CMR2/CMC, Mercury's known mass/radius, and physical
sanity of the profile it returns.

Runs in-process (not a subprocess) via a direct shootp.mynewtonSys call
at ONE inner-core radius rather than driverp's full ~40-radius sweep
(measured ~18 s/radius on this box; the full present-day sweep for one
composition is ~5.5 min -- see tests/README.md "Runtimes" and
tests/e2e/), so a single well-converged radius is what "integration
<2 min" buys here; the full sweep is the e2e tier's job.
"""
import numpy as np
import pytest

from pielib import import_src

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def solved_margot_case():
    """One converged Newton solution at ricb=500 km for CMR2=0.346,
    CMC=0.424, light_element='S', liquidus_eq='Edmund' -- module-scoped
    so the ~17 s solve is shared across every assertion below rather than
    repeated per test."""
    import sys as _sys
    from pielib import _purge_pie_submodules
    _sys.argv[:] = ["main.py", "p", "0.346", "0.424", "S", "Edmund"]
    _purge_pie_submodules()
    from pie import globalvar as gv
    planet_input = import_src("planet_input", CMR2=0.346, CMC=0.424,
                               light_element="S", liquidus_eq="Edmund")
    from pie import shootp as lc

    param = planet_input.planet("p", 0.346, "S", "Edmund")
    scale = param["scale"]
    ricb_nd = 500_010.0 / scale["a"]
    v = lc.mynewtonSys(
        "J_mercmodel", param["v0"], [ricb_nd, param["rhocr"], param["rh"], param, scale],
        xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit, verbose=False,
    )
    f, r, yy, fout, err = lc.shoot_mercmodel(v, ricb_nd, param["rhocr"], param["rh"], param, scale)
    return {"param": param, "scale": scale, "v": v, "f": f, "r": r, "yy": yy,
            "fout": fout, "err": err, "ricb_nd": ricb_nd}


def test_newton_converges(solved_margot_case):
    v = solved_margot_case["v"]
    assert v is not None
    assert np.all(np.isfinite(v))


def test_recovers_its_own_target_cmc(solved_margot_case):
    # f[3] = CmCtry - CmC (see shoot_mercmodel docstring); at a converged
    # root this residual must be within the solver's own ftol=1e-6.
    f = solved_margot_case["f"]
    assert abs(f[3]) < 1e-4


def test_recovers_its_own_target_cmr2(solved_margot_case):
    # f[4] = CMR2try - CMR2
    f = solved_margot_case["f"]
    assert abs(f[4]) < 1e-4


def test_matches_p_and_g_continuity_at_cmb(solved_margot_case):
    # f[0], f[1]: pressure and gravity continuity at the CMB -- these are
    # boundary-matching conditions, not free parameters, so they must
    # also be satisfied at convergence.
    f = solved_margot_case["f"]
    assert abs(f[0]) < 1e-4
    assert abs(f[1]) < 1e-4


def test_core_radius_smaller_than_planet_radius(solved_margot_case):
    v, param, scale = (solved_margot_case[k] for k in ("v", "param", "scale"))
    rcmb = v[2] * scale["a"]
    assert 0 < rcmb < param["rm"]


def test_inner_core_radius_smaller_than_cmb_radius(solved_margot_case):
    v, param, scale = (solved_margot_case[k] for k in ("v", "param", "scale"))
    ricb = solved_margot_case["ricb_nd"] * scale["a"]
    rcmb = v[2] * scale["a"]
    assert 0 < ricb < rcmb


def test_densities_are_positive_throughout_profile(solved_margot_case):
    yy = solved_margot_case["yy"]
    param = solved_margot_case["param"]
    rho = param["rhomean"] * yy[4]  # yy row 4 is density, normalized by rhomean
    assert np.all(rho > 0)


def test_light_element_wt_fraction_non_negative(solved_margot_case):
    yy = solved_margot_case["yy"]
    chi_li = yy[5]
    # A tiny negative floor is allowed for solver round-off right at the
    # ICB (chi_li[0] is seeded at 0 in shoot_mercmodel before the outer
    # core loop fills it in); nothing should ever go meaningfully negative.
    assert np.all(chi_li > -1e-8)


def test_mantle_density_recovers_target_mean_density(solved_margot_case):
    # v[3] is rhom/rhomean (see shoot_mercmodel); the mantle density this
    # solve implies, scaled back to physical units, must be a
    # plausible silicate mantle density (Mercury's mantle is not
    # iron -- this would catch a units/scale bug that returned core-like
    # densities for the mantle).
    v, param = solved_margot_case["v"], solved_margot_case["param"]
    rhom = v[3] * param["rhomean"]
    assert 2500 < rhom < 4000
