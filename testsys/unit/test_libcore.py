"""Unit tests for src/libCore.py's pure numerical helpers.

These need globalvar (argv shim, via conftest.sys_argv_p) because
libCore.py does `from globalvar import *` at import time, but the
functions under test here (get_mass_core, get_moi, get_mass_norm,
reorder_el, TmFeSSi*) take no globalvar STATE as input -- they're pure
functions of their arguments, which is exactly what "unit test" means.
"""
import numpy as np
import pytest

pytestmark = pytest.mark.unit

from conftest import import_src


@pytest.fixture
def libcore(sys_argv_p):
    return import_src("libCore")


@pytest.fixture
def libcore_ssi(sys_argv_p):
    # reorder_el's 'S+Si' branch reads the MODULE-LEVEL chi_Si_icb
    # (from `from globalvar import *`), not the `chi_Si_constant`
    # argument passed to it -- every real call site (getchi_li_grun,
    # shoot_mercmodel) happens to pass chi_Si_icb itself as that
    # argument, so the shadowing has no observable effect in
    # production, but it does mean a test must set the GLOBAL to get
    # a non-zero Si value, not just pass one as an argument.
    return import_src("libCore", light_element="S+Si", chi_Si_icb=0.07)


# ---------------------------------------------------------------------
# get_mass_core: regression test for the missing-pi bug fixed in
# bb37b0a ("fix missing pi in get_mass_core"). Before that fix the
# accumulated shell mass was rho*(4/3)*(dr^3) with NO pi factor, i.e.
# short by a factor of exactly pi -- this test would have failed against
# the pre-fix formula (0.997/pi vs 0.997, a ~3.14x discrepancy, nowhere
# near any float tolerance).
# ---------------------------------------------------------------------
def test_get_mass_core_matches_uniform_sphere_analytic_mass(libcore):
    R = 1_200_000.0  # m, arbitrary core-sized radius
    rho0 = 7000.0     # kg/m3, arbitrary uniform density
    n = 4000
    # r[0] deliberately tiny (not exactly 0): this mirrors the real
    # call sites (shootp.py/driverp.py always start integration at
    # r0=0.0001/a, i.e. a few tens of microns), where the function's
    # first accumulator term (a leftover, differently-normalised
    # expression -- see testsys/README.md "Findings") is negligible.
    r = np.linspace(1e-3, R, n)
    rho = np.full(n, rho0)

    mass = libcore.get_mass_core(r, rho)
    expected = (4.0 / 3.0) * np.pi * rho0 * R ** 3
    assert mass == pytest.approx(expected, rel=1e-3)


def test_get_mass_core_scales_with_pi_not_without_it(libcore):
    # Mutation-style check in the test itself: if the pi factor were
    # ever dropped again, computed/expected would sit at 1/pi (~0.318),
    # not within 1e-3 of 1. This asserts we are far from that ratio.
    R, rho0, n = 1_000_000.0, 5000.0, 2000
    r = np.linspace(1e-3, R, n)
    rho = np.full(n, rho0)
    mass = libcore.get_mass_core(r, rho)
    expected_with_pi = (4.0 / 3.0) * np.pi * rho0 * R ** 3
    ratio = mass / expected_with_pi
    assert ratio == pytest.approx(1.0, rel=1e-3)
    assert abs(ratio - 1 / np.pi) > 0.5  # nowhere near the pre-fix answer


# ---------------------------------------------------------------------
# get_moi: a UNIFORM-density sphere has moment-of-inertia factor
# C/(M R^2) = 0.4 exactly -- the textbook solid-sphere result, and
# exactly the CMR2 sanity check named in the task brief.
# ---------------------------------------------------------------------
def test_get_moi_of_uniform_sphere_is_two_fifths(libcore):
    n = 5000
    r = np.linspace(1e-3, 1.0, n)  # normalized radius, 0..1
    rho_mean = 1.0
    rho = np.full(n, rho_mean)
    cmr2 = libcore.get_moi(r, rho, rho_mean)
    assert cmr2 == pytest.approx(0.4, rel=1e-3)


def test_get_moi_smaller_for_core_concentrated_mass(libcore):
    # A body with the same total mass but density concentrated toward
    # the centre must have a SMALLER moment-of-inertia factor than the
    # uniform-sphere 0.4 -- this is the physical basis for using CMR2 to
    # infer core size in the first place (Mercury's CMR2=0.346 < 0.4
    # implies a dense core). Build a simple two-density-shell model with
    # the same total mass fraction as uniform.
    n = 4000
    r = np.linspace(1e-3, 1.0, n)
    rho_mean = 1.0
    # Dense inner 50% by radius, light outer 50%, mass-fraction-matched
    # is not required for get_moi (it normalises internally by
    # rho_mean via the r^3/r_max^3 weights) -- just confirm the
    # DIRECTION of the effect for a core-heavy body.
    rho = np.where(r < 0.5, 3.0, 0.2)
    cmr2 = libcore.get_moi(r, rho, rho_mean)
    assert cmr2 < 0.4


# ---------------------------------------------------------------------
# get_mass_norm: for a uniform-density body, the normalized mass
# integral (rho/rho_mean weighted by r^3/r_max^3 shells) must sum to 1.
# ---------------------------------------------------------------------
def test_get_mass_norm_uniform_density_sums_to_one(libcore):
    n = 3000
    r = np.linspace(1e-3, 1.0, n)
    rho_mean = 4500.0
    rho = np.full(n, rho_mean)
    assert libcore.get_mass_norm(r, rho, rho_mean) == pytest.approx(1.0, rel=1e-6)


# ---------------------------------------------------------------------
# reorder_el: pure dict-shape function, exercised for all 3 light
# element combinations the CLI (globalvar.py) accepts.
# ---------------------------------------------------------------------
@pytest.mark.parametrize("el,v,chi_si,expected", [
    ("S", 0.05, 0.0, {"Si": 0, "S": 0.05}),
    ("Si", 0.08, 0.0, {"Si": 0.08, "S": 0}),
])
def test_reorder_el(libcore, el, v, chi_si, expected):
    param = {"li_el": el}
    assert libcore.reorder_el(v, chi_si, param) == expected


def test_reorder_el_s_plus_si_uses_module_level_chi_si_icb(libcore_ssi):
    # See libcore_ssi fixture docstring: the 2nd positional argument is
    # dead for this branch, so this exercises the real (global-driven)
    # behaviour rather than the documented signature.
    param = {"li_el": "S+Si"}
    assert libcore_ssi.reorder_el(0.03, 0.07, param) == {"Si": 0.07, "S": 0.03}


def test_reorder_el_s_plus_si_uses_argument_not_global(libcore_ssi):
    # Regression test for the reorder_el('S+Si') bug (PATHWAY_FORWARD.md
    # item 12b): the branch used to read the module-level chi_Si_icb
    # global instead of its own chi_Si_constant argument. The fixture
    # above can't catch this because every real call site happens to
    # pass chi_Si_icb itself as the argument, making global and argument
    # identical (0.07 == 0.07) -- a bug there is unobservable.
    #
    # Here the global (chi_Si_icb=0.07, set via the libcore_ssi fixture)
    # and the argument (chi_Si_constant=0.03) are deliberately DIFFERENT.
    # Pre-fix code returns {"Si": 0.07, ...} (the global); post-fix code
    # returns {"Si": 0.03, ...} (the argument) -- this assertion only
    # holds for the fixed code.
    param = {"li_el": "S+Si"}
    assert libcore_ssi.reorder_el(0.03, 0.03, param) == {"Si": 0.03, "S": 0.03}


# ---------------------------------------------------------------------
# Liquidus formulas (TmFeSSi / TmFeSSi_Steinbruegge2020): physical
# behaviour checks -- monotonic increase with pressure, and the x->0
# (pure Fe) limit reduces to the Anzellini (2013) Fe liquidus term.
# ---------------------------------------------------------------------
def test_edmund_liquidus_pure_fe_limit_matches_anzellini_term(libcore):
    P = 30e9  # Pa
    P1 = P * 1e-9
    TmFe = 495.4969600595926 * (22.19 + P1) ** 0.42016806722689076
    assert libcore.TmFeSSi(0.0, 0.0, P) == pytest.approx(TmFe, rel=1e-12)


def test_edmund_liquidus_increases_with_pressure_at_fixed_composition(libcore):
    xS, xSi = 0.05, 0.02
    Tm_low = libcore.TmFeSSi(xS, xSi, 10e9)
    Tm_high = libcore.TmFeSSi(xS, xSi, 60e9)
    assert Tm_high > Tm_low


def test_edmund_liquidus_decreases_with_light_element_content(libcore):
    # Adding S or Si to Fe DEPRESSES the melting point (eutectic
    # behaviour) -- this is the entire physical premise of the "iron
    # snow" freezing-from-the-top mechanism the paper studies.
    P = 30e9
    Tm_pure = libcore.TmFeSSi(0.0, 0.0, P)
    Tm_with_s = libcore.TmFeSSi(0.05, 0.0, P)
    assert Tm_with_s < Tm_pure


def test_steinbruegge_liquidus_pure_fe_limit_matches_anzellini_term(libcore):
    P = 25e9
    P1 = P * 1e-9
    TmFe = 495.4969600595926 * (22.19 + P1) ** 0.42016806722689076
    assert libcore.TmFeSSi_Steinbruegge2020(0.0, 0.0, P) == pytest.approx(TmFe, rel=1e-12)
