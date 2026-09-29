"""Unit tests for src/planet_input.py's planet() and src/globalvar.py's
argv-derived parameters.
"""
import numpy as np
import pytest

pytestmark = pytest.mark.unit

from conftest import import_src


def test_planet_present_day_sets_requested_cmr2_cmc(sys_argv_p):
    planet_input = import_src("planet_input", CMR2=0.346, CMC=0.424,
                               light_element="S", liquidus_eq="Edmund")
    h = planet_input.planet("p", 0.346, "S", "Edmund")
    assert h["CMR2"] == pytest.approx(0.346)
    assert h["CmC"] == pytest.approx(0.424)
    assert h["li_el"] == "S"


def test_planet_rhomean_matches_gm_and_radius(sys_argv_p):
    # rhomean = 3*M/(4*pi*rm^3), M = GM/G -- exact analytic identity,
    # not something the model fits; a direct hand-computable check.
    from scipy.constants import G
    planet_input = import_src("planet_input", CMR2=0.346, CMC=0.424,
                               light_element="S", liquidus_eq="Edmund")
    h = planet_input.planet("p", 0.346, "S", "Edmund")
    M = h["GM"] / G
    expected_rhomean = 3 * M / (4 * np.pi * h["rm"] ** 3)
    assert h["rhomean"] == pytest.approx(expected_rhomean, rel=1e-12)


def test_planet_edmund_vs_steinbruegge_select_different_liquidus(sys_argv_p):
    planet_input = import_src("planet_input", CMR2=0.346, CMC=0.424,
                               light_element="S", liquidus_eq="Edmund")
    h_edmund = planet_input.planet("p", 0.346, "S", "Edmund")
    h_steinbruegge = planet_input.planet("p", 0.346, "S", "Steinbruegge")
    P = 30e9
    assert h_edmund["liquidus"](0.05, 0.0, P) != pytest.approx(
        h_steinbruegge["liquidus"](0.05, 0.0, P), rel=1e-6)


@pytest.mark.xfail(
    strict=True, reason=(
        "real bug, not fixed (constraint: no src/ edits): "
        "src/planet_input.py:119 `elif mod_type == 'e':` references an "
        "undefined name (should be `code_mode`, matching the `if "
        "code_mode == 'p':` branch above it at line 62) -- calling "
        "planet('e', ...) always raises NameError, so the evolution-model "
        "branch of planet() is unreachable dead code. Report: "
        "lars-eriksson/kai-fischer."
    ))
def test_planet_evolution_mode_would_ideally_work(sys_argv_p):
    planet_input = import_src("planet_input", CMR2=0.346, CMC=0.424,
                               light_element="S", liquidus_eq="Edmund")
    h = planet_input.planet("e", 0.346, "S", "Edmund")
    assert h["li_el"] == "S"


def test_globalvar_chi_si_icb_defaults_to_zero_unless_s_plus_si(sys_argv_p):
    globalvar = import_src("globalvar", light_element="S", liquidus_eq="Edmund")
    assert globalvar.chi_Si_icb == 0.0


def test_globalvar_chi_si_icb_takes_cli_value_for_s_plus_si(sys_argv_p):
    globalvar = import_src("globalvar", light_element="S+Si",
                            liquidus_eq="Edmund", chi_Si_icb=0.09)
    assert globalvar.chi_Si_icb == pytest.approx(0.09)


def test_globalvar_max_si_depends_on_liquidus_choice(sys_argv_p):
    edmund = import_src("globalvar", liquidus_eq="Edmund")
    # The two documented ceilings differ (12% Edmund vs 15% Steinbruegge);
    # this is the "every documented config key changes behaviour" check.
    assert edmund.max_Si_Edmund2022 == pytest.approx(0.12)
    assert edmund.max_Si_Steinbruegge2020 == pytest.approx(0.15)
