"""Regression tests for PATHWAY_FORWARD.md items 15/16: the error-code
table (src/globalvar.py's ErrorCode), the SolverError type + structured
JSONL logging (src/libCore.py's SolverError/write_solver_log), and the
call sites that used to call sys.exit()/crash uncaught instead of
raising/recording it (src/shootp.py's mynewtonSys and shoot_mercmodel's
getk2 wrap, src/libCore.py's getpotvsr SuperLU guard and
getchi_li_grun's Si%wt-above-liquidus-max guard).

Per PROJECT_RULES.md rule 10 ("every bug gets a regression test before
the fix ships"), added in the same change as the fix. This is a NEW
file (not an edit to any existing testsys/*.py) per the task brief, to
avoid colliding with a parallel test-authoring effort.

Deliberately avoids a full Newton/shoot solve for a real Mercury model
(~15-20 s each, integration-tier cost, see testsys/README.md
"Runtimes") -- these tests exercise the failure-handling/logging PATH
in isolation, via toy Jacobians (like testsys/unit/test_solver.py) and
monkeypatched internals, which is exactly what changed: the Newton
step's own math (item 17's scope) is untouched.
"""
import json

import numpy as np
import pytest

pytestmark = pytest.mark.unit

from conftest import import_src


@pytest.fixture
def globalvar(sys_argv_p):
    return import_src("globalvar")


@pytest.fixture
def libcore(sys_argv_p):
    return import_src("libCore")


@pytest.fixture
def shootp(sys_argv_p):
    return import_src("shootp")


# ---------------------------------------------------------------------
# The error-code table itself
# ---------------------------------------------------------------------
def test_error_code_table_has_the_seven_documented_values(globalvar):
    # These ints are also written to the pMetaData csv 'error_code'
    # column (see testsys/contract/test_output_schema.py) -- pin the
    # exact values so a future edit can't silently renumber them out
    # from under downstream consumers.
    EC = globalvar.ErrorCode
    assert EC.CONVERGED == 0
    assert EC.NEWTON_MAXIT == 1
    assert EC.SINGULAR_JACOBIAN == 2
    assert EC.NONFINITE_SHOOT == 3
    assert EC.CHI_OUTSIDE_ADMISSIBLE_BOX == 4
    assert EC.RICB_GE_RCMB == 5
    assert EC.SI_ABOVE_LIQUIDUS_MAX == 6


def test_every_error_code_has_a_description(globalvar):
    EC = globalvar.ErrorCode
    for code in EC:
        assert code in globalvar.ERROR_CODE_DESCRIPTIONS
        assert isinstance(globalvar.ERROR_CODE_DESCRIPTIONS[code], str)
        assert globalvar.ERROR_CODE_DESCRIPTIONS[code]


# ---------------------------------------------------------------------
# SolverError: SystemExit subclass (old `except BaseException`/
# `pytest.raises(SystemExit)` call sites keep working uncaught), but
# carries a structured error_code + context so a caller that DOES catch
# it (src/driverp.py) can record instead of crash.
# ---------------------------------------------------------------------
def test_solver_error_is_a_systemexit_subclass(libcore):
    assert issubclass(libcore.SolverError, SystemExit)


def test_solver_error_carries_code_and_context(libcore, globalvar):
    err = libcore.SolverError(globalvar.ErrorCode.NEWTON_MAXIT, "boom",
                               context={"maxit": 12})
    assert err.error_code == globalvar.ErrorCode.NEWTON_MAXIT
    assert err.context == {"maxit": 12}
    assert "boom" in str(err)


def test_solver_error_survives_pickle_round_trip(libcore):
    # Regression: BaseException's default __reduce__ reconstructs via
    # type(self)(*self.args), and self.args is only (message,) --
    # dropping error_code/context and raising "missing required
    # positional argument" on unpickling. This is exercised for real
    # by testsys/e2e/test_wide_full_sweep.py and
    # testsys/integration/test_wide_self_consistency.py, which send a
    # caught SolverError back across a ProcessPoolExecutor boundary
    # (pickled); without a __reduce__ override this breaks the whole
    # worker pool (BrokenProcessPool), not just one test.
    #
    # Uses libcore.ErrorCode (star-imported from globalvar into
    # libCore's own namespace), NOT a separately-fixtured `globalvar`
    # module: conftest.import_src's reload deletes globalvar/libCore/
    # etc. from sys.modules on EVERY call, so requesting a second
    # `import_src`-based fixture in the same test can leave this
    # fixture's `libcore` module object orphaned from sys.modules
    # under its own name, which breaks pickling by reference (not a
    # SolverError bug, a fixture-ordering trap -- avoided by only
    # ever importing one such module per test here).
    import pickle
    err = libcore.SolverError(libcore.ErrorCode.NEWTON_MAXIT, "boom",
                               context={"maxit": 12, "newton_history": [{"k": 1}]})
    restored = pickle.loads(pickle.dumps(err))
    assert restored.error_code == libcore.ErrorCode.NEWTON_MAXIT
    assert restored.message == "boom"
    assert restored.context == {"maxit": 12, "newton_history": [{"k": 1}]}
    assert isinstance(restored, SystemExit)


def test_solver_error_default_context_is_empty_dict_not_shared(libcore, globalvar):
    # No silent fallback trap: two instances must not share one mutable
    # default dict.
    a = libcore.SolverError(globalvar.ErrorCode.SINGULAR_JACOBIAN, "a")
    b = libcore.SolverError(globalvar.ErrorCode.SINGULAR_JACOBIAN, "b")
    a.context["x"] = 1
    assert b.context == {}


# ---------------------------------------------------------------------
# write_solver_log: structured JSONL next to the run's own outputs
# ---------------------------------------------------------------------
def test_write_solver_log_appends_jsonl_lines(libcore, tmp_path):
    log_path = str(tmp_path / "solverLog_0.00.jsonl")
    libcore.write_solver_log(log_path, {"kind": "a", "x": 1})
    libcore.write_solver_log(log_path, {"kind": "b", "x": 2})
    with open(log_path) as f:
        lines = [json.loads(l) for l in f]
    assert len(lines) == 2
    assert lines[0]["kind"] == "a" and lines[0]["x"] == 1
    assert lines[1]["kind"] == "b" and lines[1]["x"] == 2
    assert "t" in lines[0]  # timestamp auto-added


def test_write_solver_log_serializes_numpy_and_errorcode(libcore, globalvar, tmp_path):
    log_path = str(tmp_path / "solverLog_0.00.jsonl")
    libcore.write_solver_log(log_path, {
        "code": globalvar.ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX,
        "v": np.array([1.0, 2.0]),
        "detJ": np.float64(0.0),
        "k": np.int64(3),
    })
    with open(log_path) as f:
        rec = json.loads(f.readline())
    # ErrorCode is an IntEnum, so the stdlib json encoder serializes it
    # as its plain int value directly (matching the pMetaData csv's
    # own `error_code` column convention) without ever needing
    # write_solver_log's `default=` hook -- that hook exists for the
    # genuinely non-JSON-native types below (numpy scalars/arrays).
    assert rec["code"] == 4
    assert rec["v"] == [1.0, 2.0]
    assert rec["detJ"] == 0.0
    assert rec["k"] == 3


def test_write_solver_log_none_path_is_an_explicit_noop(libcore, tmp_path):
    # No silent fallback (PROJECT_RULES.md rule 2): None is the
    # documented opt-out (existing call sites with no run directory),
    # not a swallowed write failure -- it must not create anything or
    # raise.
    libcore.write_solver_log(None, {"kind": "should not be written"})
    assert list(tmp_path.iterdir()) == []


def test_write_solver_log_creates_missing_parent_directory(libcore, tmp_path):
    log_path = str(tmp_path / "nested" / "solverLog_0.00.jsonl")
    libcore.write_solver_log(log_path, {"kind": "a"})
    assert (tmp_path / "nested" / "solverLog_0.00.jsonl").is_file()


# ---------------------------------------------------------------------
# mynewtonSys: sys.exit() -> SolverError, with iterate history attached
# (docs/audits/AUDIT_2026-09-29_buglist.md B1)
# ---------------------------------------------------------------------
def test_mynewtonSys_raises_solvererror_not_systemexit_bare_on_singular_jacobian(shootp, globalvar):
    def toy_singular(x, varargin):
        J = np.array([[1.0, 1.0], [1.0, 1.0]])  # singular
        f = np.array([1.0, 1.0])
        return J, f
    shootp.toy_singular = toy_singular

    with pytest.raises(shootp.SolverError) as exc_info:
        shootp.mynewtonSys("toy_singular", [0.0, 0.0], [], xtol=1e-10, ftol=1e-10, maxit=5)
    err = exc_info.value
    assert err.error_code == globalvar.ErrorCode.SINGULAR_JACOBIAN
    assert isinstance(err, SystemExit)  # existing `pytest.raises(SystemExit)`
                                        # callers (testsys/unit/test_solver.py)
                                        # still catch this uncaught
    assert len(err.context["newton_history"]) == 1
    entry = err.context["newton_history"][0]
    assert {"k", "v", "normf", "normdx", "detJ", "condJ", "alpha"} <= set(entry)  # v1.3.0 adds condJ/alpha
    assert entry["detJ"] == 0.0


def test_mynewtonSys_raises_solvererror_on_maxit_with_full_history(shootp, globalvar):
    def never_converges(x, varargin):
        J = np.array([[1.0]])
        f = np.array([1.0 + abs(x[0])])  # never shrinks below any tol
        return J, f
    shootp.never_converges = never_converges

    maxit = 4
    with pytest.raises(shootp.SolverError) as exc_info:
        shootp.mynewtonSys("never_converges", [0.0], [], xtol=1e-12, ftol=1e-12, maxit=maxit)
    err = exc_info.value
    assert err.error_code == globalvar.ErrorCode.NEWTON_MAXIT
    history = err.context["newton_history"]
    assert len(history) == maxit + 1  # k goes 1..maxit+1 before the loop exits
    for entry in history:
        assert np.isfinite(entry["normf"])
        assert entry["normdx"] is None or np.isfinite(entry["normdx"])


def test_mynewtonSys_still_converges_and_returns_bare_root(shootp):
    # Backward-compatible: existing callers (testsys/conftest.py's
    # solve_full_model, testsys/integration/test_present_day_solve.py)
    # do `v = lc.mynewtonSys(...)` and use v directly -- the success
    # return type/value must be completely unchanged.
    def toy_jac(x, varargin):
        J = np.array([[2.0 * x[0]]])
        f = np.array([x[0] ** 2 - 9.0])
        return J, f
    shootp.toy_jac = toy_jac
    root = shootp.mynewtonSys("toy_jac", [5.0], [], xtol=1e-10, ftol=1e-10, maxit=50)
    assert root[0] == pytest.approx(3.0, abs=1e-6)


def test_mynewtonSys_logs_newton_history_on_success(shootp, tmp_path):
    def toy_jac(x, varargin):
        J = np.array([[2.0 * x[0]]])
        f = np.array([x[0] ** 2 - 9.0])
        return J, f
    shootp.toy_jac = toy_jac
    log_path = str(tmp_path / "solverLog_0.00.jsonl")
    shootp.mynewtonSys("toy_jac", [5.0], [], xtol=1e-10, ftol=1e-10, maxit=50,
                        log_path=log_path, log_context={"k_radius": 3, "ricb_m": 500000.0})
    with open(log_path) as f:
        records = [json.loads(l) for l in f]
    assert len(records) == 1
    rec = records[0]
    assert rec["status_name"] == "CONVERGED"
    assert rec["k_radius"] == 3 and rec["ricb_m"] == 500000.0
    assert len(rec["history"]) >= 1
    assert all({"k", "v", "normf", "normdx", "detJ"} <= set(h) for h in rec["history"])


def test_mynewtonSys_logs_failure_before_raising(shootp):
    def toy_singular(x, varargin):
        J = np.array([[1.0, 1.0], [1.0, 1.0]])
        f = np.array([1.0, 1.0])
        return J, f
    shootp.toy_singular = toy_singular

    import tempfile, os
    log_path = tempfile.mktemp(suffix=".jsonl")
    try:
        with pytest.raises(shootp.SolverError):
            shootp.mynewtonSys("toy_singular", [0.0, 0.0], [], xtol=1e-10, ftol=1e-10,
                                maxit=5, log_path=log_path)
        with open(log_path) as f:
            rec = json.loads(f.readline())
        assert rec["status_name"] == "SINGULAR_JACOBIAN"
    finally:
        if os.path.exists(log_path):
            os.remove(log_path)


def test_mynewtonSys_log_path_none_is_still_the_default(shootp):
    # Every pre-existing call site (toy Jacobians in
    # testsys/unit/test_solver.py, real solves via mynewtonSys without
    # log_path=...) must be unaffected: no log_path kwarg -> no file
    # I/O attempted at all.
    import inspect
    sig = inspect.signature(shootp.mynewtonSys)
    assert sig.parameters["log_path"].default is None
    assert sig.parameters["log_context"].default is None


# ---------------------------------------------------------------------
# libCore.getchi_li_grun: sys.exit() -> SolverError(SI_ABOVE_LIQUIDUS_MAX)
# (docs/audits/AUDIT_2026-09-29_buglist.md item 16's error-code table)
# ---------------------------------------------------------------------
def test_getchi_li_grun_raises_on_si_above_edmund_max(sys_argv_p, globalvar):
    sys_argv_p(light_element="S+Si", liquidus_eq="Edmund", chi_Si_icb=0.20)
    libcore = import_src("libCore", light_element="S+Si", liquidus_eq="Edmund", chi_Si_icb=0.20)
    planet_input = import_src("planet_input", light_element="S+Si", liquidus_eq="Edmund", chi_Si_icb=0.20)
    param = planet_input.planet("p", 0.346, "S+Si", "Edmund")
    scale = param["scale"]

    # yT small enough that T1 << any liquidus at this P -> forces the
    # root-solve branch that checks chi_Si_icb against the max.
    with pytest.raises(libcore.SolverError) as exc_info:
        libcore.getchi_li_grun(0.1, 0.4, 0.05, scale, param)
    err = exc_info.value
    assert err.error_code == globalvar.ErrorCode.SI_ABOVE_LIQUIDUS_MAX
    assert err.context["chi_Si_icb"] == pytest.approx(0.20)
    assert err.context["max_Si_allowed"] == pytest.approx(globalvar.max_Si_Edmund2022)


def test_getchi_li_grun_does_not_raise_when_si_within_bounds(sys_argv_p, globalvar):
    sys_argv_p(light_element="S+Si", liquidus_eq="Edmund", chi_Si_icb=0.05)
    libcore = import_src("libCore", light_element="S+Si", liquidus_eq="Edmund", chi_Si_icb=0.05)
    planet_input = import_src("planet_input", light_element="S+Si", liquidus_eq="Edmund", chi_Si_icb=0.05)
    param = planet_input.planet("p", 0.346, "S+Si", "Edmund")
    scale = param["scale"]
    # Should not raise -- chi_Si_icb=0.05 is well within max_Si_Edmund2022=0.12.
    chi_li, rho, grun, KS, err = libcore.getchi_li_grun(0.1, 0.4, 0.05, scale, param)
    assert np.isfinite(chi_li)
    assert err is False


# ---------------------------------------------------------------------
# libCore.getpotvsr: uncaught SuperLU RuntimeError -> SolverError
# (docs/audits/AUDIT_2026-09-29_buglist.md B2, libCore.py:266)
# ---------------------------------------------------------------------
def test_getpotvsr_wraps_superlu_singular_matrix(libcore, globalvar, monkeypatch):
    # v1.3.2: the single-rhs linear solve is spsolve(A, rhs), not
    # inv(A)*rhs (perf fix, docs/notes/perf_v1.3.2.md) -- same SuperLU
    # machinery underneath, same try/except governing the call, so the
    # monkeypatch target moves from `inv` to `spsolve` but the protection
    # being tested (a SuperLU singular-matrix RuntimeError becomes a
    # SolverError) is unchanged.
    nr = 400
    rnd = np.linspace(1e-3, 1.0, nr)
    rhond = np.full(nr, 5.0)
    gnd = np.linspace(0.01, 1.0, nr)

    def _raise_singular(A, rhs):
        raise RuntimeError("Factor is exactly singular")
    monkeypatch.setattr(libcore, "spsolve", _raise_singular)

    with pytest.raises(libcore.SolverError) as exc_info:
        libcore.getpotvsr(nr, 1.0, rnd, rhond, gnd)
    err = exc_info.value
    assert err.error_code == globalvar.ErrorCode.NONFINITE_SHOOT
    assert "superlu_error" in err.context


def test_getpotvsr_raises_on_nonfinite_solution(libcore, globalvar, monkeypatch):
    # v1.3.2: spsolve(A, rhs) returns the solution vector `b` directly
    # (no `* rhs` matvec needed, unlike inv(A)*rhs) -- the nonfinite-
    # solution guard this test exercises is on `b` itself.
    nr = 400
    rnd = np.linspace(1e-3, 1.0, nr)
    rhond = np.full(nr, 5.0)
    gnd = np.linspace(0.01, 1.0, nr)

    monkeypatch.setattr(libcore, "spsolve", lambda A, rhs: np.full(2 * nr - 1, np.nan))

    with pytest.raises(libcore.SolverError) as exc_info:
        libcore.getpotvsr(nr, 1.0, rnd, rhond, gnd)
    assert exc_info.value.error_code == globalvar.ErrorCode.NONFINITE_SHOOT


def test_getpotvsr_unaffected_on_the_normal_path(libcore):
    # Regression guard for byte-identical numeric output on the
    # already-passing path: wrapping the call in try/except must not
    # change anything when inv() succeeds and returns finite values.
    nr = 20
    rnd = np.linspace(1e-3, 1.0, nr)
    rhond = np.linspace(9000.0, 3000.0, nr)  # monotonic, PREM-like
    gnd = np.linspace(0.01, 1.0, nr)
    pot = libcore.getpotvsr(nr, 1.0, rnd, rhond, gnd)
    assert np.all(np.isfinite(pot))
    assert len(pot) == nr
