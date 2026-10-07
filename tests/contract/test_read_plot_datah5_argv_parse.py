"""Contract tier: board item 35 -- `scripts/plot/read_plot_datah5.py` must
parse its own argv into `pie.globalvar` (via `globalvar.parse_argv(sys.argv)`)
BEFORE its `from pie.planet_input import planet` import, exactly the
pattern `pie/main.py` and `scripts/plot/summaryPlot.py` already follow.

Regression history: PR #95 (board item 28f) turned `pie/globalvar.py`'s
argv parsing from an import-time side effect into the explicit
`parse_argv(argv=None)` function, called only by the real entrypoints.
`util/plot/read_plot_datah5.py` (then, now `scripts/plot/read_plot_datah5.py`
after board item 39) was NOT updated at the time, so
`pie.planet_input` (which reads `globalvar.CMC` etc. at its own import
time) crashed with `ImportError: cannot import name 'CMC' from
'pie.globalvar'` the moment this script was run standalone. PR #101
fixed it by adding the same `from pie import globalvar;
globalvar.parse_argv(sys.argv)` call used elsewhere, right before the
`planet_input` import -- see the comment block in
`scripts/plot/read_plot_datah5.py` above that call. That fix shipped
verified only by one manual interactive run quoted in the PR #101 commit
message; this test is the automated regression lock the board flagged
missing (item 35).

This runs the script as a REAL subprocess (not an in-process import) --
`read_plot_datah5.py` is a bare script, not a package module, so
mimicking its actual invocation (`python read_plot_datah5.py p CMR2 CMC
light_element liquidus_eq`) is the only way to exercise the exact
import-before-parse ordering bug that PR #101 fixed. The script's own
`filename` variable (the .h5 it reads) is hard-coded to a path that does
not exist in this checkout -- deliberately NOT provided here; the script
is expected to run past every import, reach the `pd.read_hdf(filename,
...)` call, and fail there with `FileNotFoundError`. Only the import/
argv-parse path is being locked in, per the board item 35 task scope.
"""
import pathlib

import pytest

from pielib import run_pie

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
SCRIPT = ROOT / "scripts" / "plot" / "read_plot_datah5.py"


def test_read_plot_datah5_survives_import_and_fails_only_on_missing_data_file():
    # CLI contract per the script's own module-level `cmd` string / board
    # item 35 task brief: [prog, code_mode, CMR2, CMC, light_element,
    # liquidus_eq, chi_Si_icb?]. "p"/0.346/0.424/S/Edmund is the same
    # representative case used throughout tests/ (e.g.
    # tests/contract/test_globalvar_argv_parse.py).
    result = run_pie(str(SCRIPT), "p", "0.346", "0.424", "S", "Edmund", cwd=str(ROOT))

    assert "ImportError" not in result.stdout, (
        "read_plot_datah5.py raised an ImportError -- the pre-PR#101 "
        "regression (globalvar.parse_argv(sys.argv) not called before "
        "`from pie.planet_input import planet`) is back. Full output:\n"
        f"{result.stdout}"
    )
    assert "NameError" not in result.stdout, (
        "read_plot_datah5.py raised a NameError during its import chain. "
        f"Full output:\n{result.stdout}"
    )

    # The script must get far enough to attempt reading its (deliberately
    # absent here) hard-coded .h5 data file -- confirming it ran past
    # every import and argv-parse step, not merely that no exception
    # mentions "ImportError" by name.
    assert result.returncode != 0, (
        "read_plot_datah5.py exited 0 with no data file present -- "
        f"expected it to fail downstream at pd.read_hdf(). Output:\n{result.stdout}"
    )
    assert "FileNotFoundError" in result.stdout and "read_hdf" in result.stdout, (
        "expected the script to fail downstream in pandas' read_hdf() "
        "(no .h5 fixture is provided to this test -- only the import/"
        f"argv-parse path is in scope for board item 35). Full output:\n{result.stdout}"
    )
