"""E2E tier: run src/main.py exactly the way scheduler.py invokes it for
one composition, end-to-end, in a tmp dir, as a real subprocess -- then
diff its output against a committed golden.

Scope: ONE full composition (S, Edmund, CMR2=0.346, CMC=0.424 -- the
exact case named in the task brief), not scheduler.py's full 18-way
sweep. Measured: one composition takes ~5.5 min wall time on this box
(runs to inner-core-radius convergence failure around ricb~850 km, 18
of the ~40 possible dr=50km steps -- this early stop is itself
reproduced by the golden, not worked around). The full scheduler.py
sweep (16 S+Si chi_Si_icb values + S + Si = 18 compositions) would be
~1.5-2 h and is deliberately NOT run here -- see testsys/README.md
"Runtimes" for the measurement and the reasoning.

Golden: testsys/reference/self_v1.0.5/CMR2_0.346_CMC_0.424_S_Edmund/
pMetaData_0.00.csv, generated from THIS repo's current HEAD (there is
no independent published oracle at CMC=0.424 specifically -- see
testsys/integration/test_zenodo_parity.py for the published-paper
oracle at the neighbouring CMC=0.426). Regeneration command is in
testsys/README.md.
"""
import csv
import pathlib
import subprocess
import sys

import pytest

from conftest import run_pie

pytestmark = pytest.mark.e2e

SRC = pathlib.Path(__file__).resolve().parent.parent.parent / "src"
GOLDEN = (pathlib.Path(__file__).resolve().parent.parent / "reference"
          / "self_v1.0.5" / "CMR2_0.346_CMC_0.424_S_Edmund" / "pMetaData_0.00.csv")
RTOL = 1e-4
CATEGORICAL_FIELDS = ["isnow", "isnowcmb", "error_code"]


def _read_rows(path):
    with open(path) as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("pie_e2e")
    for py in SRC.glob("*.py"):
        (workdir / py.name).symlink_to(py)
    (workdir / "TmFeSmelt.dat").symlink_to(SRC / "TmFeSmelt.dat")
    (workdir / "results").mkdir()

    result = run_pie("main.py", "p", "0.346", "0.424", "S", "Edmund",
                      cwd=str(workdir), timeout=900)
    assert result.returncode == 0, (
        f"main.py exited {result.returncode}:\n{result.stdout[-4000:]}"
    )

    out_dirs = list((workdir / "results").glob("CMR2_*"))
    assert len(out_dirs) == 1, f"expected exactly one output dir, got {out_dirs}"
    return out_dirs[0]


def test_output_directory_and_csv_appear(full_run):
    csvs = list(full_run.glob("pMetaData_*.csv"))
    assert len(csvs) == 1


def test_h5_and_figure_files_appear(full_run):
    assert list(full_run.glob("*.h5")), "no per-radius .h5 files were written"
    assert list(full_run.glob("*.pdf")), "no per-radius figure .pdf files were written"


def test_row_count_matches_golden(full_run):
    computed = _read_rows(next(full_run.glob("pMetaData_*.csv")))
    golden = _read_rows(GOLDEN)
    assert len(computed) == len(golden), (
        "different number of inner-core-radius steps converged than the "
        "golden -- either a convergence regression or the golden needs "
        "regenerating (see testsys/README.md)"
    )


def test_scalar_fields_match_golden_within_tolerance(full_run):
    computed = _read_rows(next(full_run.glob("pMetaData_*.csv")))
    golden = _read_rows(GOLDEN)
    for i, (c_row, g_row) in enumerate(zip(computed, golden)):
        for field in g_row:
            c, g = float(c_row[field]), float(g_row[field])
            if field in CATEGORICAL_FIELDS:
                assert c == pytest.approx(g, abs=1e-9), (
                    f"row {i} field {field}: categorical mismatch "
                    f"computed={c} golden={g}"
                )
            else:
                diff = abs(c - g)
                bound = RTOL * max(abs(g), 1e-12)
                assert not (diff > bound), (
                    f"row {i} field {field}: computed={c} golden={g} "
                    f"diff={diff} exceeds rtol={RTOL}"
                )
