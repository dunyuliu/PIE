"""Parity tier (integration subtest): current src/ vs published-paper
output for the SAME code.

Oracle: Dunnigan et al. (2026), JGR Planets, doi:10.1029/2025JE009368,
whose Zenodo code record (10.5281/zenodo.16929504) is byte-identical to
this repo's src/ (verified: `diff -rq` finds only src/VERSION differs --
see testsys/reference/zenodo_v1.0.5/PROVENANCE.md). That means their
published output is not "a similar model" -- it is the SAME code, on
different input, run by someone else, on a different machine. Agreement
here rules out platform/BLAS/numpy-version dependence; disagreement
would be a real, reportable divergence, not a tolerance-tuning problem.

This gives S+Si a published regression anchor (same v1.0.5 code as the
paper run, so reproducibility -- not independent correctness): both
published cases used here ARE S+Si (the composition that
combines both light elements and so has no simpler literature analogue).

Tolerance: rtol=1e-4 on continuous physical quantities. Measured
deviation between a fresh solve and the published value (chi_li_icb,
core_mass) was ~1e-7..1e-6 relative -- i.e. at the Newton solver's own
xtol=ftol=1e-6 (globalvar.py), not a platform artifact. 1e-4 is two
orders of magnitude above that measured worst case: catches a real
divergence (e.g. the get_mass_core missing-pi bug would show up as a
~214% relative error) while tolerant of solver-iteration-count noise.
Categorical fields (isnow, isnowcmb, error_code) are compared for EXACT
equality -- they are discrete classification labels, not continuous
quantities, and a tolerance-based comparison on a label is a silent
bug all its own (see class docstring below for the isnow convention).
"""
import csv
import pathlib

import h5py
import numpy as np
import pytest

from conftest import import_src

pytestmark = [pytest.mark.integration, pytest.mark.parity]

REF_ROOT = pathlib.Path(__file__).resolve().parent.parent / "reference" / "zenodo_v1.0.5"

CONTINUOUS_FIELDS = [
    "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "chi_li_in", "chi_S_bulk",
    "Pcmb", "chi_li_eut_icb", "chi_li_eut_cmb", "rcmb", "core_mass",
    "chi_li_icb",
]
CATEGORICAL_FIELDS = ["isnow", "isnowcmb", "error_code"]
RTOL = 1e-4


def _read_pmetadata_row(csv_path, ricb_target):
    with open(csv_path) as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        if abs(float(row["ricb"]) - ricb_target) < 1.0:
            return {k: float(v) for k, v in row.items()}
    raise ValueError(f"no row with ricb={ricb_target} in {csv_path}")


def _solve_one_radius(CMR2, CMC, light_element, chi_Si_icb, ricb_m):
    """One converged Newton solution at a single inner-core radius --
    the same shape of solve as testsys/integration/test_present_day_solve.py,
    parameterised for the parity cases (S+Si, non-default CMC, chi_Si_icb)."""
    import sys as _sys
    _sys.argv[:] = ["main.py", "p", str(CMR2), str(CMC), light_element,
                    "Edmund", str(chi_Si_icb)]
    for name in list(_sys.modules):
        if name in ("globalvar", "planet_input", "libCore", "solver",
                     "coreEos", "shootp", "driverp"):
            del _sys.modules[name]
    import globalvar as gv
    planet_input = import_src("planet_input", CMR2=CMR2, CMC=CMC,
                               light_element=light_element,
                               liquidus_eq="Edmund", chi_Si_icb=chi_Si_icb)
    import shootp as lc

    param = planet_input.planet("p", CMR2, light_element, "Edmund")
    scale = param["scale"]
    ricb_nd = ricb_m / scale["a"]
    v = lc.mynewtonSys(
        "J_mercmodel", param["v0"],
        [ricb_nd, param["rhocr"], param["rh"], param, scale],
        xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit, verbose=False,
    )
    assert v is not None, "Newton solve did not converge"
    f, r, yy, fout, err = lc.shoot_mercmodel(
        v, ricb_nd, param["rhocr"], param["rh"], param, scale)

    rhom = v[3] * param["rhomean"]
    chi_li = yy[5]
    chi_li_icb = v[4]
    chi_li_cmb = chi_li[-1]
    rcmb = v[2] * scale["a"]
    r_phys = scale["a"] * r
    rho_phys = param["rhomean"] * yy[4]
    core_mass = lc.get_mass_core(r_phys, rho_phys)

    Picb, Tcmb, isnow, isnowcmb, chi_li_in, gradTa, chi_S_bulk = fout
    return {
        "rhom": rhom, "moi": None, "cmc": None, "Picb": Picb, "Tcmb": Tcmb,
        "isnow": isnow, "isnowcmb": isnowcmb, "chi_li_in": chi_li_in,
        "chi_S_bulk": chi_S_bulk, "chi_li_eut_icb": None,
        "chi_li_eut_cmb": None, "rcmb": rcmb, "core_mass": core_mass,
        "chi_li_icb": chi_li_icb, "error_code": 0.0,
    }


def _assert_matches_reference(computed, reference):
    for field in CATEGORICAL_FIELDS:
        assert computed[field] == pytest.approx(reference[field], abs=1e-9), (
            f"{field}: categorical field must match EXACTLY "
            f"(computed={computed[field]!r}, reference={reference[field]!r})"
        )
    for field in CONTINUOUS_FIELDS:
        if computed.get(field) is None:
            continue  # not computed by this reduced single-radius solve
        c, r = computed[field], reference[field]
        # `not (... <= bound)` (never `... > bound`): a NaN diff must
        # FAIL this assertion, not silently pass a `>` comparison NaN
        # always evaluates False for.
        diff = abs(c - r)
        bound = RTOL * max(abs(r), 1e-12)
        assert not (diff > bound), (
            f"{field}: computed={c!r} reference={r!r} "
            f"diff={diff!r} exceeds rtol={RTOL}"
        )


@pytest.mark.parametrize("case,csv_name,h5_name,chi_si,ricb_m", [
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "pMetaData_0.01.csv",
     "DataSi%wt0.01_R0500.0.h5", 0.01, 500_010.0),
    ("CMR2_0.346_CMC_0.426_S+Si_Edmund", "pMetaData_0.06.csv",
     "DataSi%wt0.06_R0550.0.h5", 0.06, 550_010.0),
])
def test_matches_published_margot_s_plus_si_case(case, csv_name, h5_name, chi_si, ricb_m):
    reference = _read_pmetadata_row(REF_ROOT / case / csv_name, ricb_m)
    computed = _solve_one_radius(0.346, 0.426, "S+Si", chi_si, ricb_m)
    _assert_matches_reference(computed, reference)


def test_matches_published_genova_s_plus_si_case():
    case = "CMR2_0.333_CMC_0.443_S+Si_Edmund"
    h5_path = REF_ROOT / case / "DataSi%wt0.01_R0500.0.h5"
    reference = pd_misc_row(h5_path)
    computed = _solve_one_radius(0.333, 0.443, "S+Si", 0.01, 500_010.0)
    _assert_matches_reference(computed, reference)


def pd_misc_row(h5_path):
    import pandas as pd
    df = pd.read_hdf(h5_path, key="misc")
    return {k: float(df[k].iloc[0]) for k in df.columns}
