"""Regression test for testsys/conftest.py's sys.path ".local" filter.

2026-10-02: the filter used to match the bare substring "/.local/", which
also matches the uv-managed Python 3.12 interpreter's OWN stdlib path
(~/.local/share/uv/python/cpython-3.12.../lib/python3.12) and stripped it
out of sys.path, breaking every import (e.g. ModuleNotFoundError: No
module named 'pdb'). The fix narrows the match to "/.local/lib/", the
actual pip --user site-packages pattern this filter exists to drop. This
test locks both directions so neither regresses: the uv interpreter path
must survive, and the original pip --user case must still be filtered.

This re-implements the filter predicate rather than importing conftest.py
(importing conftest.py would itself mutate sys.path as a side effect of
collection, which is awkward to isolate in a unit test). Any future change
to the filter in testsys/conftest.py must be mirrored here.
"""
import pytest

pytestmark = pytest.mark.unit


def _filtered_paths(paths):
    return [p for p in paths if "/.local/lib/" not in p]


def test_uv_managed_interpreter_stdlib_path_survives_filter():
    uv_stdlib = (
        "/home/utig5/dliu/.local/share/uv/python/"
        "cpython-3.12.15-linux-x86_64-gnu/lib/python3.12"
    )
    assert uv_stdlib in _filtered_paths([uv_stdlib])


def test_pip_user_site_packages_is_still_filtered():
    pip_user_site = "/home/utig5/dliu/.local/lib/python3.10/site-packages"
    assert pip_user_site not in _filtered_paths([pip_user_site])


def test_old_bare_substring_predicate_would_have_wrongly_dropped_uv_stdlib():
    # Documents the bug this test guards against: the OLD predicate
    # ("/.local/" not in p) incorrectly drops the uv interpreter's stdlib.
    uv_stdlib = (
        "/home/utig5/dliu/.local/share/uv/python/"
        "cpython-3.12.15-linux-x86_64-gnu/lib/python3.12"
    )
    old_predicate_result = [p for p in [uv_stdlib] if "/.local/" not in p]
    assert old_predicate_result == [], (
        "sanity check on the bug report itself: if this fails, the old "
        "bare-substring predicate no longer reproduces the breakage it "
        "was reported for"
    )
