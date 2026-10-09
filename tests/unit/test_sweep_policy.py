"""Unit tests for the v1.3.0 per-radius sweep policy in src/driverp.py
(owner decision 2026-09-30, PATHWAY_FORWARD.md item 17), with the Newton
solver monkeypatched so no Mercury shoot runs:

1. warm start from the last converged solution; converged -> start='warm'
2. warm fails and warm != default v0 -> one cold retry from v0 -> start='cold'
3. both fail -> SolverError with the LAST attempt's code; the warm-start
   error is kept in the context; the csv gets a failure row with NaN
   physics and the new columns; no h5
4. a failed radius is never used as a start (the next radius warm-starts
   from the last CONVERGED solution)
5. code 6 (Si above the liquidus cap) is checked before the sweep: one row,
   composition ends, the solver is never called
and the consequence: a non-code-6 composition's csv has exactly len(rs)
rows, failures included (gated end-to-end in
tests/e2e/test_full_composition_sweep.py).
"""
import csv
import math

import numpy as np
import pytest

pytestmark = pytest.mark.unit

from pielib import import_src

V0 = [0.8, 1.0, 0.8, 0.7, 0.05]


def _param(light="S", liquidus="Edmund", CMR2=0.346, chi_Si_icb=None):
    planet_input = import_src("planet_input", light_element=light, liquidus_eq=liquidus, chi_Si_icb=chi_Si_icb)
    return planet_input.planet("p", CMR2, light, liquidus)


def _solver_stub(shootp, outcomes):
    """outcomes: list of callables consumed per mynewtonSys call; each takes
    (v0, start) and returns a vector or raises SolverError."""
    calls = []

    def fake(Jfun, x0, varargin, xtol=None, ftol=None, maxit=None, verbose=False, log_path=None, log_context=None, **kw):
        start = (log_context or {}).get("start")
        calls.append((list(map(float, x0)), start))
        shootp.last_solve_info.clear()
        shootp.last_solve_info.update({"status": 0, "n_iterations": 3, "normf_last": 1e-9})
        return outcomes.pop(0)(x0, start)
    return fake, calls


def test_solve_radius_warm_then_cold_then_failure(sys_argv_p, monkeypatch):
    driverp = import_src("driverp")
    shootp = driverp.lc
    EC = driverp.ErrorCode
    param = _param(); scale = param["scale"]
    args = (0, 10.0, 10.0 / scale["a"], None, list(V0), param["rhocr"], param["rh"], param, scale, None)

    # 1. no last converged solution -> single cold attempt
    fake, calls = _solver_stub(shootp, [lambda v0, s: np.array(v0) * 1.01])
    monkeypatch.setattr(shootp, "mynewtonSys", fake)
    v, start = driverp.solve_radius(*args)
    assert start == "cold" and calls == [(V0, "cold")]

    # 1./2. warm start converges -> start='warm', cold never tried
    v_last = [0.9, 1.1, 0.79, 0.69, 0.02]
    fake, calls = _solver_stub(shootp, [lambda v0, s: np.array(v0)])
    monkeypatch.setattr(shootp, "mynewtonSys", fake)
    a2 = list(args); a2[3] = v_last
    v, start = driverp.solve_radius(*a2)
    assert start == "warm" and calls == [(v_last, "warm")]

    # 2. warm fails -> cold retry from V0 converges -> start='cold'
    def fail_maxit(v0, s):
        raise shootp.SolverError(EC.NEWTON_MAXIT, "maxit", context={})
    fake, calls = _solver_stub(shootp, [fail_maxit, lambda v0, s: np.array(v0)])
    monkeypatch.setattr(shootp, "mynewtonSys", fake)
    v, start = driverp.solve_radius(*a2)
    assert start == "cold" and [c[1] for c in calls] == ["warm", "cold"] and calls[1][0] == V0

    # 3. both fail -> the LAST attempt's code, warm error kept in context
    def fail_box(v0, s):
        raise shootp.SolverError(EC.CHI_OUTSIDE_ADMISSIBLE_BOX, "box", context={})
    fake, calls = _solver_stub(shootp, [fail_maxit, fail_box])
    monkeypatch.setattr(shootp, "mynewtonSys", fake)
    with pytest.raises(shootp.SolverError) as ei:
        driverp.solve_radius(*a2)
    assert ei.value.error_code == EC.CHI_OUTSIDE_ADMISSIBLE_BOX
    assert ei.value.context["start"] == "cold"
    assert ei.value.context["warm_start_error"]["error_code"] == int(EC.NEWTON_MAXIT)

    # warm start equal to the default v0 -> no duplicate cold attempt
    fake, calls = _solver_stub(shootp, [fail_maxit])
    monkeypatch.setattr(shootp, "mynewtonSys", fake)
    a3 = list(args); a3[3] = list(V0)
    with pytest.raises(shootp.SolverError):
        driverp.solve_radius(*a3)
    assert [c[1] for c in calls] == ["warm"]

    # code 6 inside an attempt is re-raised immediately (no cold retry)
    def fail_si(v0, s):
        raise shootp.SolverError(EC.SI_ABOVE_LIQUIDUS_MAX, "si", context={})
    fake, calls = _solver_stub(shootp, [fail_si, lambda v0, s: np.array(v0)])
    monkeypatch.setattr(shootp, "mynewtonSys", fake)
    with pytest.raises(shootp.SolverError) as ei:
        driverp.solve_radius(*a2)
    assert ei.value.error_code == EC.SI_ABOVE_LIQUIDUS_MAX and len(calls) == 1


def _redirect_outputs(driverp, tmp_path):
    driverp.model_path = str(tmp_path) + "/"
    driverp.csvfiles_path = str(tmp_path) + "/"
    driverp.presentDataName = str(tmp_path) + "/DataSi%wt0.00_"
    driverp.presentFigureName = str(tmp_path) + "/FigSi%wt0.00_"
    with open(tmp_path / driverp.pMetaDataFileName, "w") as f:
        csv.writer(f).writerow(driverp.presentday_columns)


def test_failure_row_has_nan_physics_and_new_columns(sys_argv_p, tmp_path):
    driverp = import_src("driverp")
    _redirect_outputs(driverp, tmp_path)
    driverp.lc.last_solve_info.clear()
    driverp.lc.last_solve_info.update({"status": 1, "n_iterations": 13, "normf_last": 0.0123})
    driverp.write_failure_row(50010.0, driverp.ErrorCode.NEWTON_MAXIT, "cold")
    rows = list(csv.DictReader(open(tmp_path / driverp.pMetaDataFileName)))
    assert len(rows) == 1
    r = rows[0]
    assert set(r) == set(driverp.presentday_columns)
    assert float(r["ricb"]) == 50010.0 and float(r["error_code"]) == 1.0
    assert r["start"] == "cold" and int(float(r["newton_iters"])) == 13 and float(r["resid_norm"]) == 0.0123
    for c in driverp.presentday_columns:
        if c in ("chi_Si_icb", "ricb", "error_code", "start", "newton_iters", "resid_norm", "check_solution_bounds_enabled"):
            continue
        assert math.isnan(float(r[c])), f"{c} should be NaN on a failed radius, got {r[c]!r}"
    assert not list(tmp_path.glob("*.h5"))


def test_failure_row_check_solution_bounds_enabled_reflects_actual_flag(sys_argv_p, tmp_path, monkeypatch):
    """item 40c: check_solution_bounds_enabled must be read off the module
    attribute the solver actually consumes (driverp.lc.PIE_CHECK_SOLUTION_BOUNDS,
    i.e. shootp.PIE_CHECK_SOLUTION_BOUNDS) at write time, not a literal baked
    into write_failure_row -- flip the attribute both ways in the same test
    process and assert the csv column follows it, so a hardcoded True/False
    (the item-23a tautology-bug class) would fail this test either way."""
    driverp = import_src("driverp")
    _redirect_outputs(driverp, tmp_path)
    driverp.lc.last_solve_info.clear()
    driverp.lc.last_solve_info.update({"status": 1, "n_iterations": 1, "normf_last": 1.0})

    monkeypatch.setattr(driverp.lc, "PIE_CHECK_SOLUTION_BOUNDS", True)
    driverp.write_failure_row(1.0, driverp.ErrorCode.NEWTON_MAXIT, "cold")
    monkeypatch.setattr(driverp.lc, "PIE_CHECK_SOLUTION_BOUNDS", False)
    driverp.write_failure_row(2.0, driverp.ErrorCode.NEWTON_MAXIT, "cold")

    rows = list(csv.DictReader(open(tmp_path / driverp.pMetaDataFileName)))
    assert len(rows) == 2
    assert rows[0]["check_solution_bounds_enabled"] == "True"
    assert rows[1]["check_solution_bounds_enabled"] == "False"


def test_sweep_continues_after_failure_and_never_starts_from_a_failed_radius(sys_argv_p, tmp_path, monkeypatch):
    driverp = import_src("driverp")
    shootp = driverp.lc
    EC = driverp.ErrorCode
    _redirect_outputs(driverp, tmp_path)
    param = _param(); scale = param["scale"]
    rs = np.array([10.0, 50010.0, 100010.0])
    sol0 = np.array([0.81, 1.02, 0.79, 0.68, 0.04])

    def fail_nonfinite(v0, s):
        raise shootp.SolverError(EC.NONFINITE_SHOOT, "nan", context={})
    # radius 0: cold converges; radius 1: warm fails, cold fails; radius 2: warm from sol0 (NOT from radius 1)
    outcomes = [lambda v0, s: sol0.copy(), fail_nonfinite, fail_nonfinite, lambda v0, s: np.array(v0) + 0.001]
    fake, calls = _solver_stub(shootp, outcomes)
    monkeypatch.setattr(shootp, "mynewtonSys", fake)
    # shoot_mercmodel and the plot are not under test here: stub them with finite, schema-shaped output
    n = 8
    yy = np.vstack([np.linspace(0.9, 0.1, n), np.linspace(0, 1, n), np.ones(n), np.ones(n), np.full(n, 1.5), np.full(n, 0.04)])

    def fake_shoot(v, ricb, rhocr, rh, p, sc):
        r = np.linspace(ricb, v[2], n)
        return [1e-9] * 5, r, yy, [3e10, 1900.0, 0, 0, 0.04, 0.0, 0.04], False
    monkeypatch.setattr(shootp, "shoot_mercmodel", fake_shoot)
    monkeypatch.setattr(driverp.vis, "plot_isnow", lambda *a, **k: a[-1])
    monkeypatch.setattr(driverp.pd.Series, "to_hdf", lambda *a, **k: None)
    monkeypatch.setattr(driverp.pd.DataFrame, "to_hdf", lambda *a, **k: None)

    driverp.driverp(param, rs)
    starts = [c[1] for c in calls]
    assert starts == ["cold", "warm", "cold", "warm"]
    assert calls[1][0] == list(map(float, sol0)) and calls[3][0] == list(map(float, sol0)), "warm start must be the last CONVERGED solution"
    rows = list(csv.DictReader(open(tmp_path / driverp.pMetaDataFileName)))
    assert len(rows) == len(rs), "one csv row per attempted radius"
    assert [float(r["error_code"]) for r in rows] == [0.0, 3.0, 0.0]
    assert [r["start"] for r in rows] == ["cold", "cold", "warm"]
    assert math.isnan(float(rows[1]["rcmb"])) and not math.isnan(float(rows[2]["rcmb"]))


def test_si_above_liquidus_cap_writes_one_row_and_ends_before_any_solve(sys_argv_p, tmp_path, monkeypatch):
    driverp = import_src("driverp", light_element="S+Si", chi_Si_icb=0.13)
    shootp = driverp.lc
    _redirect_outputs(driverp, tmp_path)
    driverp.presentDataName = str(tmp_path) + "/DataSi%wt0.13_"
    monkeypatch.setattr(shootp, "mynewtonSys", lambda *a, **k: pytest.fail("solver must not be called for code 6"))
    param = _param("S+Si", chi_Si_icb=0.13)
    driverp.driverp(param, np.arange(1e1, 2e6, 50e3))
    rows = list(csv.DictReader(open(tmp_path / driverp.pMetaDataFileName)))
    assert len(rows) == 1 and float(rows[0]["error_code"]) == 6.0 and float(rows[0]["ricb"]) == 10.0
    assert float(rows[0]["chi_Si_icb"]) == 0.13
    log = (tmp_path / driverp.pSolverLogFileName).read_text()
    assert "SI_ABOVE_LIQUIDUS_MAX" in log
