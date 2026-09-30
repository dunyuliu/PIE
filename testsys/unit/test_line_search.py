"""Unit tests for the v1.3.0 solver changes (PATHWAY_FORWARD.md item 17):
the bounded backtracking line search in shootp.mynewtonSys, the Mercury
admissible-box test (shootp.mercmodel_box), the cond(J) singularity test
that replaces the exact det(J)==0 float compare, and the getk2 nrs=0
index fix (bug B5). Toy Jacobians only -- no Mercury shoot -- except the
getk2 grid test, which calls the real getk2 with polynomial densities.

Design reference: docs/notes/solver_v1.3.0.md. The identity invariant
("every v1.2.0-converged row is unchanged") is gated at integration
tier by testsys/integration/test_v1_2_0_invariant.py, not here.
"""
import numpy as np
import pytest

pytestmark = pytest.mark.unit

from conftest import import_src


@pytest.fixture
def shootp(sys_argv_p):
    return import_src("shootp")


@pytest.fixture
def globalvar(sys_argv_p):
    return import_src("globalvar")


# ---------------------------------------------------------------------
# Line search on toy problems (trial_fun / box_fun supplied explicitly:
# for a non-Mercury Jfun the solver has no trial function of its own).
# ---------------------------------------------------------------------
def _linear(shootp):
    # f(x) = x - 0.3 with a deliberately WRONG Jacobian (0.25 instead of
    # 1) so the Newton step dx = f/0.25 overshoots by 4x: from x0=0 the
    # alpha=1 trial lands at 1.2, alpha=0.5 at 0.6, alpha=0.25 at 0.3 =
    # the root.
    def jf(x, varargin):
        return np.array([[0.25]]), np.array([x[0] - 0.3])
    shootp.toy_overshoot = jf
    return jf


def test_alpha_one_accepted_when_in_box_matches_v120_step_exactly(shootp):
    # Well-behaved toy: alpha=1 is always in the box, so the line-search
    # path must produce bit-identical iterates to line_search=False.
    def toy(x, varargin):
        return np.array([[2.0 * x[0]]]), np.array([x[0] ** 2 - 9.0])
    shootp.toy_quad = toy
    trial = lambda x: (np.array([x[0] ** 2 - 9.0]), [])
    box = lambda x, f, fout: (True, None, "")
    a = shootp.mynewtonSys("toy_quad", [5.0], [], xtol=1e-12, ftol=1e-12, maxit=50,
                           line_search=False)
    b = shootp.mynewtonSys("toy_quad", [5.0], [], xtol=1e-12, ftol=1e-12, maxit=50,
                           line_search=True, trial_fun=trial, box_fun=box)
    assert np.array_equal(np.asarray(a), np.asarray(b))
    assert a[0] == pytest.approx(3.0, abs=1e-9)


def test_growth_guard_halves_alpha_until_residual_stops_exploding(shootp, globalvar):
    _linear(shootp)
    # trial residual is inflated 1e4x beyond x=0.5: alpha=1 (x=1.2) and
    # alpha=0.5 (x=0.6) violate growth_max=100; alpha=0.25 hits the root.
    trial = lambda x: (np.array([(x[0] - 0.3) * (1e4 if x[0] > 0.5 else 1.0)]), [])
    box = lambda x, f, fout: (True, None, "")
    log = {}
    x = shootp.mynewtonSys("toy_overshoot", [0.0], [], xtol=1e-12, ftol=1e-12, maxit=20,
                           trial_fun=trial, box_fun=box, log_path=None)
    assert x[0] == pytest.approx(0.3, abs=1e-12)


def test_box_rejection_halves_alpha_and_records_it(shootp, globalvar, tmp_path):
    _linear(shootp)
    trial = lambda x: (np.array([x[0] - 0.3]), [])
    # box: x must stay below 0.7 -> alpha=1 (1.2) rejected, alpha=0.5 (0.6) accepted
    box = lambda x, f, fout: ((x[0] < 0.7), globalvar.ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX, "x too large")
    log = tmp_path / "log.jsonl"
    x = shootp.mynewtonSys("toy_overshoot", [0.0], [], xtol=1e-12, ftol=1e-12, maxit=20,
                           trial_fun=trial, box_fun=box, log_path=str(log))
    assert x[0] == pytest.approx(0.3, abs=1e-12)
    import json
    rec = json.loads(log.read_text().splitlines()[-1])
    assert rec["line_search"] is True
    first = rec["history"][0]
    assert first["alpha"] == 0.5 and first["n_rejected"] == 1
    assert "condJ" in first and "detJ" in first


def test_alpha_floor_raises_with_the_box_error_code(shootp, globalvar):
    _linear(shootp)
    trial = lambda x: (np.array([x[0] - 0.3]), [])
    # box excludes everything the step can reach: x must stay <= 0 -> every
    # halving is rejected; after alpha < alpha_min the solve must fail with
    # the box's code, not loop or return a bogus root.
    box = lambda x, f, fout: ((x[0] <= 0.0), globalvar.ErrorCode.RICB_GE_RCMB, "outside")
    with pytest.raises(shootp.SolverError) as ei:
        shootp.mynewtonSys("toy_overshoot", [0.0], [], xtol=1e-12, ftol=1e-12, maxit=20,
                           trial_fun=trial, box_fun=box)
    e = ei.value
    assert e.error_code == globalvar.ErrorCode.RICB_GE_RCMB
    assert e.context["alpha"] < shootp.ALPHA_MIN
    assert e.context["n_rejected"] >= 10


def test_trial_solvererror_is_a_rejection_except_by_design_si_stop(shootp, globalvar):
    _linear(shootp)
    calls = []

    def trial(x):
        calls.append(x[0])
        if x[0] > 0.5:
            raise shootp.SolverError(globalvar.ErrorCode.NONFINITE_SHOOT, "nan in shoot")
        return np.array([x[0] - 0.3]), []
    box = lambda x, f, fout: (True, None, "")
    x = shootp.mynewtonSys("toy_overshoot", [0.0], [], xtol=1e-12, ftol=1e-12, maxit=20,
                           trial_fun=trial, box_fun=box)
    assert x[0] == pytest.approx(0.3, abs=1e-12)
    assert calls[:3] == pytest.approx([1.2, 0.6, 0.3])

    def trial_si(x):
        raise shootp.SolverError(globalvar.ErrorCode.SI_ABOVE_LIQUIDUS_MAX, "by design")
    with pytest.raises(shootp.SolverError) as ei:
        shootp.mynewtonSys("toy_overshoot", [0.0], [], xtol=1e-12, ftol=1e-12, maxit=20,
                           trial_fun=trial_si, box_fun=box)
    assert ei.value.error_code == globalvar.ErrorCode.SI_ABOVE_LIQUIDUS_MAX


def test_converging_final_step_is_returned_before_any_trial(shootp):
    # v1.2.0 returned x - dx as soon as |f| < ftol (evaluated at the
    # current iterate) WITHOUT evaluating anything at the new point. The
    # line search must keep that order, or converged rows would change.
    called = []
    def jf(x, varargin):
        return np.array([[1.0]]), np.array([x[0] - 1.0])
    shootp.toy_lin1 = jf
    def trial(x):
        called.append(x[0]); return np.array([x[0] - 1.0]), []
    box = lambda x, f, fout: (False, None, "would reject everything")
    x = shootp.mynewtonSys("toy_lin1", [1.0 + 1e-9], [], xtol=1e-12, ftol=1e-6, maxit=5,
                           trial_fun=trial, box_fun=box)
    assert x[0] == pytest.approx(1.0, abs=1e-15)
    assert called == []


# ---------------------------------------------------------------------
# Singular-Jacobian test: cond(J) > COND_MAX, not det(J) == 0.0 exactly
# ---------------------------------------------------------------------
def test_near_singular_jacobian_is_caught_by_condition_number(shootp, globalvar):
    def jf(x, varargin):
        return np.array([[1.0, 1.0], [1.0, 1.0 + 1e-14]]), np.array([1.0, 1.0])
    shootp.toy_near_singular = jf
    with pytest.raises(shootp.SolverError) as ei:
        shootp.mynewtonSys("toy_near_singular", [0.0, 0.0], [], maxit=3)
    assert ei.value.error_code == globalvar.ErrorCode.SINGULAR_JACOBIAN
    assert ei.value.context["condJ"] > shootp.COND_MAX
    # the same J is accepted when the threshold is raised above its cond
    with pytest.raises(shootp.SolverError) as ei2:
        shootp.mynewtonSys("toy_near_singular", [0.0, 0.0], [], maxit=2, cond_max=1e20)
    assert ei2.value.error_code == globalvar.ErrorCode.NEWTON_MAXIT


def test_zero_column_jacobian_reports_infinite_condition_number(shootp, globalvar):
    # The Mercury det(J)==0 death: a finite-difference column identically
    # zero (chi_li_icb clamped at the eutectic).
    def jf(x, varargin):
        J = np.eye(3); J[:, 2] = 0.0
        return J, np.array([1.0, 1.0, 1.0])
    shootp.toy_zero_col = jf
    with pytest.raises(shootp.SolverError) as ei:
        shootp.mynewtonSys("toy_zero_col", [0.0, 0.0, 0.0], [], maxit=3)
    assert ei.value.error_code == globalvar.ErrorCode.SINGULAR_JACOBIAN
    assert not np.isfinite(ei.value.context["condJ"])


# ---------------------------------------------------------------------
# mercmodel_box: the Mercury admissible box
# ---------------------------------------------------------------------
def _args(shootp, light):
    planet_input = import_src("planet_input", light_element=light)
    param = planet_input.planet("p", 0.346, light, "Edmund")
    return [1e4 / param["scale"]["a"], param["rhocr"], param["rh"], param, param["scale"]]


def test_box_accepts_a_typical_iterate_and_rejects_each_violation(sys_argv_p, globalvar):
    shootp = import_src("shootp")
    args = _args(shootp, "S")
    f = np.zeros(5); fout = [30e9, 1900.0, 0, 0, 0.05, 0.0, 0.05]  # Picb = 30 GPa
    eut = 0.11 + 0.187 * np.exp(-0.065 * 30.0)
    ok, code, _ = shootp.mercmodel_box(np.array([0.8, 1.0, 0.8, 0.7, 0.05]), f, fout, args)
    assert ok and code is None
    # slightly negative chi (as 21.8% of published converged rows have) passes
    ok, code, _ = shootp.mercmodel_box(np.array([0.8, 1.0, 0.8, 0.7, -0.003]), f, fout, args)
    assert ok
    ok, code, _ = shootp.mercmodel_box(np.array([0.8, 1.0, 0.8, 0.7, -0.02]), f, fout, args)
    assert not ok and code == globalvar.ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX
    ok, code, _ = shootp.mercmodel_box(np.array([0.8, 1.0, 0.8, 0.7, eut + 1e-3]), f, fout, args)
    assert not ok and code == globalvar.ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX
    ok, code, _ = shootp.mercmodel_box(np.array([0.8, 1.0, args[0] * 0.5, 0.7, 0.05]), f, fout, args)
    assert not ok and code == globalvar.ErrorCode.RICB_GE_RCMB
    ok, code, _ = shootp.mercmodel_box(np.array([0.8, 1.0, 0.8, 0.7, 0.05]), np.array([np.nan] * 5), fout, args)
    assert not ok and code == globalvar.ErrorCode.NONFINITE_SHOOT


def test_box_uses_liquidus_si_max_for_si_only(sys_argv_p, globalvar):
    shootp = import_src("shootp", light_element="Si")
    args = _args(shootp, "Si")
    f = np.zeros(5); fout = [30e9, 1900.0, 0, 0, 0.05, 0.0, 0.05]
    ok, _, _ = shootp.mercmodel_box(np.array([0.8, 1.0, 0.8, 0.7, 0.119]), f, fout, args)
    assert ok
    ok, code, _ = shootp.mercmodel_box(np.array([0.8, 1.0, 0.8, 0.7, 0.121]), f, fout, args)
    assert not ok and code == globalvar.ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX


# ---------------------------------------------------------------------
# getk2 at nrs=0 (ricb = 10 m): no index wrap-around (bug B5)
# ---------------------------------------------------------------------
def test_getk2_constant_density_gravity_is_linear_in_r_including_first_shell(sys_argv_p):
    shootp = import_src("shootp")
    args = _args(shootp, "S")
    param, scale = args[3], args[4]
    # constant non-dimensional density 1 in both inner and outer core:
    # g(r) = (4 pi G_nd / 3) r exactly, for every grid point including
    # r[0] -- the point the old code built from r[-1] and unset g[-1].
    rhos = [0.0, 0.0, 0.0, 1.0]; rhof = [0.0, 0.0, 0.0, 1.0]
    captured = {}
    orig = shootp.getpotvsr

    def spy(nr, bigGnd, r, rho, g):
        captured.update(r=r.copy(), rho=rho.copy(), g=g.copy(), bigGnd=bigGnd)
        return orig(nr, bigGnd, r, rho, g)
    shootp.getpotvsr = spy
    try:
        rs = 10.0 / scale["a"]              # the 10-m first radius -> nrs = 0
        k2, xi = shootp.getk2(rs, 0.8, 0.7, rhos, rhof, param, scale)
    finally:
        shootp.getpotvsr = orig
    r, g, rho = captured["r"], captured["g"], captured["rho"]
    f4piG = 4 * np.pi * captured["bigGnd"] / 3
    assert np.all(np.isfinite(g)) and np.all(np.isfinite(rho))
    assert g[0] == pytest.approx(f4piG * r[0], rel=1e-12)
    assert np.allclose(g, f4piG * r, rtol=1e-9)
    assert np.isfinite(k2)
    assert xi == 0.0   # no inner-core shell in the grid: BsAs = 0 exactly


def test_getk2_ricb_at_or_beyond_rcmb_raises_physical_limit_not_indexerror(sys_argv_p, globalvar):
    shootp = import_src("shootp")
    args = _args(shootp, "S")
    param, scale = args[3], args[4]
    rhos = [0.0, 0.0, 0.0, 1.0]; rhof = [0.0, 0.0, 0.0, 1.0]
    with pytest.raises(shootp.SolverError) as ei:
        shootp.getk2(0.81, 0.8, 0.7, rhos, rhof, param, scale)
    assert ei.value.error_code == globalvar.ErrorCode.RICB_GE_RCMB
    with pytest.raises(shootp.SolverError) as ei:
        shootp.getk2(0.7995, 0.8, 0.7, rhos, rhof, param, scale)   # ratio 0.99937 -> nrs = 400
    assert ei.value.error_code == globalvar.ErrorCode.RICB_GE_RCMB
