"""Contract tier: mechanical guard that running this suite never leaves
pie/ modified. Session-scoped `cwd_src` chdirs into pie/ for the whole
run (a long-standing invariant kept across board item 28e's rename, even
though libCore's TmFeSmelt.dat load is module-relative, not cwd-relative,
since item 28g); this is the check that nothing ever writes there.
"""
import pathlib
import subprocess

import pytest

pytestmark = pytest.mark.contract

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent


def test_src_tree_is_unmodified_by_the_test_suite():
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", "pie"],
        cwd=ROOT, stdout=subprocess.PIPE, text=True,
    )
    assert result.stdout == "", (
        "pie/ was modified by running the test suite (or by something "
        "else before it) -- tests must never write into pie/:\n"
        f"{result.stdout}"
    )


def test_testsys_test_files_never_open_a_path_under_src_for_writing():
    """Static check: no test file should construct an output path rooted
    at the pie/ tree (as opposed to tmp_path or tests/reference/,
    which are fine). Looks for the specific pattern this repo's own
    production code uses for writing results (os.mkdir/open/to_hdf on a
    'model_path'-shaped string), which would land in pie/results/ given
    the session-wide chdir."""
    import re
    suspect = re.compile(r"os\.mkdir\(model_path\)|to_hdf\(root")
    offenders = []
    for path in (ROOT / "tests").rglob("test_*.py"):
        text = path.read_text()
        if suspect.search(text):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, (
        f"these test files call pie/'s own file-writing helpers directly "
        f"while cwd==pie/: {offenders} -- run them in a tmp_path instead"
    )


def test_no_machine_local_paths_in_tracked_files():
    """The repo is public: no absolute home/scratch paths from a dev box in
    tracked files (they leak local layout and break for anyone else).
    `update_log` is frozen history (PROJECT_RULES.md rule 1a) and exempt."""
    import re
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, stdout=subprocess.PIPE,
                           text=True, check=True).stdout.split()
    pat = re.compile(r"/home/(utig5|staff)/|/tmp/claude-\d")
    offenders = []
    for rel in files:
        if rel == "update_log":
            continue
        try:
            text = (ROOT / rel).read_text(errors="ignore")
        except (IsADirectoryError, FileNotFoundError):
            continue
        if pat.search(text):
            offenders.append(rel)
    assert not offenders, f"machine-local paths in: {offenders}"
