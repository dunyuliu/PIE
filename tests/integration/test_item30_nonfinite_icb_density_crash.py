"""Regression test for PATHWAY_FORWARD.md item 30, bug #1/#2 (board item 30,
found during the item-18a population re-run,
docs/notes/item18a_population_rerun_2026-10-03.md):

pie/shootp.py::shoot_mercmodel builds the ODE initial state
`y0 = [v[0], gr0, v[1]]` from `rho = eos.eosInnerCore(...)[1]`. When a
Newton trial iterate pushes eosInnerCore to return a non-finite density,
`gr0` (and so `y0`) is non-finite and `scipy.integrate.solve_ivp` raises an
uncaught `ValueError: All components of the initial state y0 must be
finite.` pie/driverp.py's per-radius try/except (solve_radius's
lc.SolverError handler and the shoot_mercmodel call in driverp()) catches
only `lc.SolverError`, not a bare `ValueError`, so this exception escapes
`driverp()` entirely and kills the rest of the sweep -- every radius after
the crash is lost, even ones that would otherwise have converged. Observed
on 326/1400 sampled sweep jobs at ricb ~1.55-1.85 Mm (radius index 31-37)
in the item-18a re-run; this test reproduces the same failure MODE with a
minimal, deterministic trigger (a monkeypatched `eosInnerCore` returning a
NaN density on one call) rather than the exact composition/radius, since
the real trigger condition (a specific Newton trial iterate landing outside
`eosInnerCore`'s domain) is not something a fast test should depend on
reproducing exactly.

Current (buggy) behaviour: `driverp.driverp(...)` itself raises
`ValueError`, so this test ERRORS on current HEAD.

Expected (fixed) behaviour, once the surface owner adds a catch for this
`ValueError` symmetric to the existing `lc.SolverError` handling (item 30):
the sweep records a failure row for the radius that hit the non-finite
density and CONTINUES to the remaining radii, exactly like every other
per-radius failure in pie/driverp.py's v1.3.0 policy
(tests/unit/test_sweep_policy.py) -- one csv row per attempted radius,
no exception escapes driverp().
"""
import csv
import math

import numpy as np
import pytest

pytestmark = pytest.mark.integration

from pielib import import_src


def _param(light="S", liquidus="Edmund", CMR2=0.346, chi_Si_icb=None):
    planet_input = import_src("planet_input", light_element=light, liquidus_eq=liquidus, chi_Si_icb=chi_Si_icb)
    return planet_input.planet("p", CMR2, light, liquidus)


def _redirect_outputs(driverp, tmp_path):
    driverp.model_path = str(tmp_path) + "/"
    driverp.csvfiles_path = str(tmp_path) + "/"
    driverp.presentDataName = str(tmp_path) + "/DataSi%wt0.00_"
    driverp.presentFigureName = str(tmp_path) + "/FigSi%wt0.00_"
    with open(tmp_path / driverp.pMetaDataFileName, "w") as f:
        csv.writer(f).writerow(driverp.presentday_columns)


def test_nonfinite_icb_density_mid_sweep_does_not_crash_the_whole_job(sys_argv_p, tmp_path, monkeypatch):
    driverp = import_src("driverp")
    shootp = driverp.lc
    _redirect_outputs(driverp, tmp_path)
    param = _param()

    rs = np.array([10.0, 50010.0, 100010.0, 150010.0])

    # Poison exactly ONE call to eosInnerCore (the first one any shoot
    # makes, to build y0 -- see pie/shootp.py:103-107) so the very first
    # radius's first shoot attempt gets a non-finite y0, while every
    # other call returns the real physics unmodified. This is the
    # documented trigger mechanism (a trial iterate pushing eosInnerCore
    # non-finite), not a stand-in SolverError/ValueError raised directly
    # -- solve_ivp's own finite-state guard is what actually raises here,
    # same as the real bug.
    real_eos = shootp.eos.eosInnerCore
    calls = {"n": 0}

    def poison_first_call(chi, p, T, param_):
        calls["n"] += 1
        fcc = real_eos(chi, p, T, param_)
        if calls["n"] == 1:
            fcc = list(fcc)
            fcc[1] = float("nan")
        return fcc

    monkeypatch.setattr(shootp.eos, "eosInnerCore", poison_first_call)

    # The sweep's post-convergence bookkeeping (plot + hdf snapshot) touches
    # a real './results/<case>/' directory and real HDF5 writes, neither of
    # which this fast test should depend on -- stub them out exactly as
    # tests/unit/test_sweep_policy.py:159-161 does for the same reason.
    monkeypatch.setattr(driverp.vis, "plot_isnow", lambda *a, **k: a[-1])
    monkeypatch.setattr(driverp.pd.Series, "to_hdf", lambda *a, **k: None)
    monkeypatch.setattr(driverp.pd.DataFrame, "to_hdf", lambda *a, **k: None)

    # This call currently raises `ValueError: All components of the
    # initial state y0 must be finite.` out of scipy.integrate.solve_ivp,
    # uncaught by driverp()/solve_radius -- i.e. this test ERRORS on
    # current HEAD. Once item 30 is fixed, driverp() must swallow it into
    # a per-radius failure row and continue, same as any other
    # lc.SolverError.
    driverp.driverp(param, rs)

    rows = list(csv.DictReader(open(tmp_path / driverp.pMetaDataFileName)))
    assert len(rows) == len(rs), (
        "every requested radius must get a csv row even when one radius's "
        "shoot hits a non-finite ICB density -- the sweep must not die "
        "mid-job and silently drop the remaining radii (item 30)"
    )
    # The poisoned radius must be recorded as a FAILURE (NaN physics, a
    # non-zero error_code), never a fabricated/garbage converged row.
    first = rows[0]
    assert float(first["error_code"]) != 0.0, (
        "the radius that hit the non-finite density must be recorded as "
        "a failed radius (error_code != 0), not CONVERGED"
    )
    for c in driverp.presentday_columns:
        if c in ("chi_Si_icb", "ricb", "error_code", "start", "newton_iters", "resid_norm"):
            continue
        assert math.isnan(float(first[c])), f"{c} should be NaN on the failed first radius, got {first[c]!r}"

