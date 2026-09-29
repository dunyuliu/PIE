"""Contract tier: mechanical guard that running this suite never leaves
src/ modified. Session-scoped `cwd_src` chdirs into src/ for the whole
run (needed for libCore's relative TmFeSmelt.dat load); this is the
check that nothing UPSTREAM of that convenience ever writes there.
"""
import pathlib
import subprocess

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def test_src_tree_is_unmodified_by_the_test_suite():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "src"],
        cwd=ROOT, stdout=subprocess.PIPE, text=True,
    )
    assert result.stdout == "", (
        "src/ was modified by running the test suite (or by something "
        "else before it) -- testsys must never write into src/:\n"
        f"{result.stdout}"
    )


def test_testsys_test_files_never_open_a_path_under_src_for_writing():
    """Static check: no test file should construct an output path rooted
    at the src/ tree (as opposed to tmp_path or testsys/reference/,
    which are fine). Looks for the specific pattern this repo's own
    production code uses for writing results (os.mkdir/open/to_hdf on a
    'model_path'-shaped string), which would land in src/results/ given
    the session-wide chdir."""
    import re
    suspect = re.compile(r"os\.mkdir\(model_path\)|to_hdf\(root")
    offenders = []
    for path in (ROOT / "testsys").rglob("test_*.py"):
        text = path.read_text()
        if suspect.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, (
        f"these test files call src/'s own file-writing helpers directly "
        f"while cwd==src/: {offenders} -- run them in a tmp_path instead"
    )
