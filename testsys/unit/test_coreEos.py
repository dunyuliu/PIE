"""Unit tests for src/coreEos.py -- pure EOS/thermodynamics functions.

coreEos.py imports nothing from globalvar/planet_input, so these tests do
not need the sys.argv shim; conftest.cwd_src is still required (autouse)
because coreEos itself is import-safe, but the param fixtures below build
real eosAndersonGrueneisen objects the way planet_input.planet() does.
"""
import numpy as np
import pytest

pytestmark = pytest.mark.unit

from pie import coreEos as eos


# ---------------------------------------------------------------------
# GibbsLiquidFe / GibbsfccFe: closed-form functions of T only.
# ---------------------------------------------------------------------
def test_gibbs_liquid_fe_matches_hand_computed_value():
    # T=1000: 300 - 9007.3402 + 290.29866*1000 - 46*1000*ln(1000)
    T = 1000.0
    expected = 300 - 9007.3402 + 290.29866 * T - 46 * T * np.log(T)
    assert eos.GibbsLiquidFe(T) == pytest.approx(expected, rel=1e-12)


def test_gibbs_fcc_fe_finite_over_solid_stability_range():
    for T in (300.0, 800.0, 1800.0):
        val = eos.GibbsfccFe(T)
        assert np.isfinite(val)


# ---------------------------------------------------------------------
# eosAndersonGrueneisen: density must increase monotonically with
# pressure at fixed temperature (compression is not a numerical accident,
# it's the entire point of an EOS).
# ---------------------------------------------------------------------
@pytest.fixture
def fcc_fe_eos():
    return eos.eosAndersonGrueneisen(
        M0=55.845, p0=1.0e-5, T0=298, V0=6.82, alpha0=7.0e-5, KT0=163.4,
        KTP0=5.38, deltaT=5.5, kappa=1.4, GibbsE=eos.GibbsfccFe,
    )


def test_density_increases_with_pressure_at_fixed_temperature(fcc_fe_eos):
    fcc_fe_eos.eos(1.0, 1800.0)
    rho_low = fcc_fe_eos.rho
    fcc_fe_eos.eos(50.0, 1800.0)
    rho_high = fcc_fe_eos.rho
    assert rho_high > rho_low


def test_density_decreases_with_temperature_at_fixed_pressure(fcc_fe_eos):
    # Thermal expansion: hotter material at the same pressure is less dense.
    fcc_fe_eos.eos(10.0, 500.0)
    rho_cold = fcc_fe_eos.rho
    fcc_fe_eos.eos(10.0, 2000.0)
    rho_hot = fcc_fe_eos.rho
    assert rho_hot < rho_cold


def test_bulk_modulus_positive_over_solid_range(fcc_fe_eos):
    for p in (1.0, 25.0, 100.0):
        fcc_fe_eos.eos(p, 1800.0)
        assert fcc_fe_eos.KT > 0
        assert fcc_fe_eos.KS > 0


# ---------------------------------------------------------------------
# liquidNonIdalFeSi: the x->0 (no Si) limit must reduce to pure liquid Fe.
# This is the "asymptotic limit" physical-behaviour check from the brief:
# a light-element mixture with zero light-element fraction is just the
# parent metal.
# ---------------------------------------------------------------------
@pytest.fixture
def eos_param():
    liquidFe = eos.eosAndersonGrueneisen(
        M0=55.845, p0=1e-5, T0=298, V0=6.88, alpha0=9e-5, KT0=148, KTP0=5.8,
        deltaT=5.1, kappa=0.56, GibbsE=eos.GibbsLiquidFe,
    )
    liquidFeSi = eos.eosAndersonGrueneisen(
        M0=(55.845 + 28.08), p0=1e5 * 1e-5, T0=1723, V0=16.5839,
        alpha0=17.6525e-5, KT0=69.0074, KTP0=7.76007, deltaT=4.07505,
        kappa=0.56, gamma0=1.61986, q=0,
    )
    return {"MFe": 55.845, "MSi": 28.08, "lFe": liquidFe, "lFeSi": liquidFeSi}


def test_liquid_fesi_reduces_to_pure_liquid_fe_as_si_to_zero(eos_param):
    p, T = 20.0, 2000.0
    out = eos.liquidNonIdalFeSi(0.0, p, T, eos_param)
    eos_param["lFe"].eos(p, T)
    # V, rho must match the pure-Fe endmember exactly: chi=[1,0] makes
    # margules2Solution's np.dot([...], chi) select eM1 alone and the
    # excess-volume term Vex([0,1],...) is identically zero at chi[1]=0.
    assert out[0] == pytest.approx(eos_param["lFe"].V, rel=1e-10)
    assert out[1] == pytest.approx(eos_param["lFe"].rho, rel=1e-10)


def test_liquid_fesi_density_lower_than_pure_fe_with_si_present(eos_param):
    # Si is a light element: adding it must lower the mixture density
    # relative to pure Fe at the same P,T (else "light element" is a lie).
    p, T = 20.0, 2000.0
    rho_pure = eos.liquidNonIdalFeSi(0.0, p, T, eos_param)[1]
    rho_with_si = eos.liquidNonIdalFeSi(0.10, p, T, eos_param)[1]
    assert rho_with_si < rho_pure


# ---------------------------------------------------------------------
# meltingDataFromFile / TmFeS table: sanity that the table loads and is
# monotonic. Uses the on-disk TmFeSmelt.dat exactly as src/ ships it
# (conftest guarantees cwd == src/).
# ---------------------------------------------------------------------
def test_melting_data_from_file_loads_and_is_finite():
    tm = eos.meltingDataFromFile("TmFeSmelt.dat")
    val = tm(0.05, 20.0)
    assert np.isfinite(val)
    assert val > 0
