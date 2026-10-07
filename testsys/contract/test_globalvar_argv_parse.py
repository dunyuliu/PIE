"""Contract tier: board item 28f -- pie/globalvar.py's CLI argv parsing
must not run as an IMPORT-time side effect. Before this fix, `import
pie.globalvar` ran `sys.argv[1]`..`sys.argv[6]` unconditionally at module
load, crashing (IndexError/ValueError) any unrelated process that
imports it with a foreign argv -- pytest's own, or
`pie/robust_runner.py`'s own CLI (`run m.csv --workers 2 ...`). Parsing
is now the explicit `globalvar.parse_argv(argv=None)` function, called
once by the real entrypoint (`pie/main.py`) before anything else imports
its argv-derived names.

These tests import `pie.globalvar` fresh (never relying on a previously
cached module, so a stale import from an earlier test in this same
process cannot hide a regression) with an argv that would have crashed
the old import-time parser, and confirm the import itself survives;
`parse_argv()` is then exercised directly to confirm it still does the
real parsing work, still raises loudly on malformed input, and still
derives every name consumers rely on.
"""
import importlib
import sys

import pytest

from pielib import _purge_pie_submodules

pytestmark = pytest.mark.contract


def _fresh_import_globalvar():
    _purge_pie_submodules(names=("pie.globalvar",))
    return importlib.import_module("pie.globalvar")


def test_bare_import_survives_too_short_argv(monkeypatch):
    # Shorter than the old code's sys.argv[1]..sys.argv[5] minimum --
    # under the pre-28f code this IndexError'd at import time.
    monkeypatch.setattr(sys, "argv", ["pytest"])
    gv = _fresh_import_globalvar()
    # Not parsed yet (no argv-seeded call happened) -- no silent default,
    # per the "don't silently default" constraint; the name simply isn't
    # there until something calls parse_argv().
    assert not hasattr(gv, "code_mode")


def test_bare_import_survives_a_foreign_but_plausible_length_argv(monkeypatch):
    # Long enough (6 entries) to pass the old n==6-or-7 check and then
    # crash on float(sys.argv[2]) -- this is robust_runner.py's own real
    # CLI argv shape (`run m.csv --workers 2`), the exact case that forced
    # testsys/pielib.py's and robust_runner.py's argv-faking workarounds.
    monkeypatch.setattr(sys, "argv", ["robust_runner.py", "run", "m.csv", "--workers", "2", "extra"])
    gv = _fresh_import_globalvar()
    assert not hasattr(gv, "CMR2")


def test_parse_argv_populates_every_consumer_facing_attribute():
    gv = _fresh_import_globalvar()
    gv.parse_argv(["main.py", "p", "0.346", "0.424", "S", "Edmund"])
    assert gv.code_mode == "p"
    assert gv.CMR2 == pytest.approx(0.346)
    assert gv.CMC == pytest.approx(0.424)
    assert gv.light_element == "S"
    assert gv.liquidus_eq == "Edmund"
    assert gv.chi_Si_icb == 0.0  # not S+Si -> ignored/defaulted to 0.0, same as before
    expected_model_path = (
        "./results/CMR2_" + "{:.17f}".format(0.346) + "_CMC_" + "{:.17f}".format(0.424)
        + "_S_Edmund/"
    )
    assert gv.model_path == expected_model_path
    assert gv.presentFigureName == expected_model_path + "FigSi%wt0.00_"
    assert gv.presentDataName == expected_model_path + "DataSi%wt0.00_"
    assert gv.pMetaDataFileName == "pMetaData_0.00.csv"
    assert gv.path_to_present_day_models == expected_model_path


def test_parse_argv_s_plus_si_takes_the_7th_argv_as_chi_si_icb():
    gv = _fresh_import_globalvar()
    gv.parse_argv(["main.py", "p", "0.346", "0.424", "S+Si", "Edmund", "0.05"])
    assert gv.chi_Si_icb == pytest.approx(0.05)
    assert gv.pMetaDataFileName == "pMetaData_0.05.csv"


def test_parse_argv_raises_loudly_on_malformed_argv_instead_of_defaulting():
    gv = _fresh_import_globalvar()
    with pytest.raises(ValueError):
        gv.parse_argv(["main.py", "p", "0.346"])  # too short
    with pytest.raises(ValueError):
        gv.parse_argv(["main.py", "p", "0.346", "0.424", "S", "Edmund", "0.05", "extra"])  # too long
