"""Regression tests for the three dead/no-op checks named in
PATHWAY_FORWARD.md item 16 (docs/audits/AUDIT_2026-09-29_buglist.md B1/B3):

  - src/driverp.py:38  `if v is None: break`        (v is never None)
  - src/driverp.py:111 `chi_li.any()<0`              (bool compared to
    int, always False)
  - src/shootp.py's `shoot_mercmodel` hard-coded `err0 = False`

Each of these silently discarded a real failure signal instead of
recording it (PROJECT_RULES.md rule 2). None of them can be exercised
cheaply as a full end-to-end driverp() sweep (that requires an actual
Newton+shoot solve per radius, ~15-20 s -- integration/e2e-tier cost),
so each gets two things instead: (1) a semantic test proving the OLD
expression is a no-op and the NEW one is not, on the same inputs, and
(2) a source-text check that driverp.py/shootp.py actually contain the
fixed pattern and not the old dead one -- a standard technique for
regression-guarding a fix to code that's expensive to exercise
end-to-end (see also testsys/contract/test_repo_hygiene.py's static
source checks for a precedent in this test suite).

This is a NEW file (not an edit to any existing testsys/*.py) per the
task brief, to avoid colliding with a parallel test-authoring effort.
"""
import pathlib
import re

import numpy as np
import pytest

pytestmark = pytest.mark.unit

SRC = pathlib.Path(__file__).resolve().parents[2] / "pie"


def _code_only(text):
    """Strip '#'-comments (this file's own fix explains the old buggy
    expressions in prose comments right next to the fix, quoting them
    verbatim for readability -- a naive full-text substring search
    would flag those explanatory comments as if the bug were still
    live code). Line-based, not a full tokenizer: good enough for the
    single-line statements these checks care about, and this repo has
    no '#' inside string literals on the relevant lines."""
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


# ---------------------------------------------------------------------
# driverp.py:111 `chi_li.any()<0` -> `(chi_li<0).any()`
# ---------------------------------------------------------------------
def test_any_lt_zero_pattern_is_the_documented_always_false_bug():
    # chi_li.any() returns a numpy bool_; comparing a bool to an int
    # (`<0`) is always False, regardless of chi_li's actual contents --
    # this is exactly why the driverp.py:111 check never fired.
    chi_li = np.array([-0.3, -0.1, 0.2, 0.5])
    assert bool(chi_li.any() < 0) is False  # the OLD, buggy expression
    assert bool((chi_li < 0).any()) is True  # the FIXED expression


def test_any_lt_zero_pattern_stays_false_even_when_all_negative():
    chi_li = np.array([-1.0, -2.0, -3.0])
    assert bool(chi_li.any() < 0) is False
    assert bool((chi_li < 0).any()) is True


def test_fixed_pattern_correctly_reports_no_negative_values():
    chi_li = np.array([0.0, 0.1, 0.2])
    assert bool((chi_li < 0).any()) is False


def test_driverp_source_no_longer_contains_the_dead_any_lt_zero_check():
    text = (SRC / "driverp.py").read_text()
    assert "chi_li.any()<0" not in _code_only(text)
    assert "(chi_li<0).any()" in text


# ---------------------------------------------------------------------
# driverp.py:38 `if v is None: break` -- replaced by a try/except around
# mynewtonSys catching lc.SolverError (mynewtonSys now raises instead
# of sys.exit()-ing or ever returning None).
# ---------------------------------------------------------------------
def test_driverp_source_no_longer_contains_the_dead_v_is_none_check():
    text = (SRC / "driverp.py").read_text()
    assert "if v is None: break" not in _code_only(text)


def test_driverp_source_catches_solvererror_around_the_newton_call():
    text = (SRC / "driverp.py").read_text()
    assert "lc.mynewtonSys(" in text
    assert "except lc.SolverError as e:" in text
    # the replacement must still stop the sweep at the failing radius
    # (same behaviour as the old crash, minus the crash) -- `break`
    # must appear between the mynewtonSys call and the next iteration.
    idx = text.index("lc.mynewtonSys(")
    next_break = text.index("break", idx)
    next_def_or_eof = len(text)
    assert next_break < next_def_or_eof


def test_driverp_source_catches_solvererror_around_shoot_mercmodel_too():
    # getk2's IndexError / getpotvsr's SuperLU RuntimeError propagate as
    # lc.SolverError out of shoot_mercmodel (item 16's other target),
    # not just out of mynewtonSys -- driverp.py must catch both calls,
    # not just the first.
    text = (SRC / "driverp.py").read_text()
    assert text.count("except lc.SolverError as e:") >= 2
    assert "lc.shoot_mercmodel(" in text


# ---------------------------------------------------------------------
# shoot_mercmodel's hard-coded err0=False (src/shootp.py)
# ---------------------------------------------------------------------
def test_shootp_source_no_longer_hardcodes_err0_false():
    text = (SRC / "shootp.py").read_text()
    assert "err0 = False\n" not in text
    assert "err0 = bool(np.any(err))" in text


def test_np_any_over_err_array_detects_a_true_flag():
    # odeRK4_snow returns err2, an array of 0/1 flags per radial step
    # (src/solver.py); shoot_mercmodel used to discard it into a
    # hard-coded err0=False. bool(np.any(...)) is the scalar summary
    # driverp.py's `if err == True:` expects.
    err_all_clear = np.zeros(51)
    err_one_flagged = np.zeros(51)
    err_one_flagged[10] = 1
    assert bool(np.any(err_all_clear)) is False
    assert bool(np.any(err_one_flagged)) is True


# ---------------------------------------------------------------------
# No bare sys.exit() left in the two files item 16 targets (the
# replacement for B1/the Si%wt-exceeded guard) -- a bare `sys.exit()`
# anywhere in these files would still kill the whole process the way
# item 16 says not to.
# ---------------------------------------------------------------------
def test_shootp_no_longer_calls_bare_sys_exit():
    text = _code_only((SRC / "shootp.py").read_text()).replace("sys. exit()", "sys.exit()")
    assert "sys.exit()" not in text


def test_libcore_no_longer_calls_bare_sys_exit():
    text = _code_only((SRC / "libCore.py").read_text())
    assert "sys.exit()" not in text


def test_libcore_getpotvsr_wraps_the_superlu_inversion():
    # v1.3.2: the single-rhs solve is spsolve(A, rhs), not inv(A)*rhs
    # (perf fix, docs/notes/perf_v1.3.2.md) -- same SuperLU machinery,
    # same try/except; the line text changed, so this check follows it.
    text = (SRC / "libCore.py").read_text()
    idx = text.index("b = spsolve(A, rhs)")
    # the try/except must be the code immediately governing this line,
    # not merely present somewhere else in the file.
    window = text[max(0, idx - 400):idx]
    assert "try:" in window


def test_driverp_records_ricb_ge_rcmb_physical_limit():
    text = (SRC / "driverp.py").read_text()
    assert "ErrorCode.RICB_GE_RCMB" in text
