"""E2E tier: run `python -m pie` exactly the way scheduler.py invokes it
for one composition (board item 28e: formerly `python main.py`), end-to-
end, in a tmp dir, as a real subprocess -- then diff its output against a
committed golden.

Scope: ONE full composition (S, Edmund, CMR2=0.346, CMC=0.424 -- the
exact case named in the task brief), not scheduler.py's full 18-way
sweep. Measured: one composition takes ~5.5 min wall time on this box
(runs to inner-core-radius convergence failure around ricb~850 km, 18
of the ~40 possible dr=50km steps -- this early stop is itself
reproduced by the golden, not worked around). The full scheduler.py
sweep (16 S+Si chi_Si_icb values + S + Si = 18 compositions) would be
~1.5-2 h and is deliberately NOT run here -- see tests/README.md
"Runtimes" for the measurement and the reasoning.

Golden: tests/reference/self_v1.0.5/CMR2_0.346_CMC_0.424_S_Edmund/
pMetaData_0.00.csv, generated from THIS repo's current HEAD (there is
no independent published oracle at CMC=0.424 specifically -- see
tests/integration/test_zenodo_parity.py for the published-paper
oracle at the neighbouring CMC=0.426). Regeneration command is in
tests/README.md.
"""
import csv
import pathlib
import subprocess
import sys

import pytest

from pielib import run_pie

pytestmark = pytest.mark.e2e

GOLDEN = (pathlib.Path(__file__).resolve().parent.parent / "reference"
          / "self_v1.0.5" / "CMR2_0.346_CMC_0.424_S_Edmund" / "pMetaData_0.00.csv")
RTOL = 1e-4
CATEGORICAL_FIELDS = ["isnow", "isnowcmb", "error_code"]


def _read_rows(path, converged_only=True):
    """Since v1.3.0 every ATTEMPTED radius has a csv row; failed radii
    carry error_code != 0 and NaN physics. The golden predates that and
    holds converged rows only, so comparisons filter error_code == 0."""
    with open(path) as f:
        rows = list(csv.DictReader(f))
    if converged_only:
        rows = [r for r in rows if float(r["error_code"]) == 0.0]
    return rows


def test_failed_radii_have_nan_physics_and_no_h5(full_run):
    rows = _read_rows(next(full_run.glob("pMetaData_*.csv")), converged_only=False)
    failed = [r for r in rows if float(r["error_code"]) != 0.0]
    ok = [r for r in rows if float(r["error_code"]) == 0.0]
    assert len(list(full_run.glob("*.h5"))) == len(ok), "one .h5 per CONVERGED radius, none for failures"
    physical = [c for c in rows[0] if c not in ("chi_Si_icb", "ricb", "error_code", "start", "newton_iters", "resid_norm")]
    for r in failed:
        assert all(r[c] == "nan" or r[c] == "" or r[c] != r[c] or float(r[c]) != float(r[c]) for c in physical), (
            f"failed radius ricb={r['ricb']} carries non-NaN physics: "
            f"{[(c, r[c]) for c in physical if r[c] not in ('nan', '')]}")
        assert r["start"] in ("warm", "cold", "")
    for r in ok:
        assert r["start"] in ("warm", "cold")
        assert int(float(r["newton_iters"])) >= 1
        assert float(r["resid_norm"]) < 1e-5


@pytest.fixture(scope="module")
def full_run(tmp_path_factory):
    workdir = tmp_path_factory.mktemp("pie_e2e")
    (workdir / "results").mkdir()
    # No symlinking of pie/*.py into workdir (board item 28e): pie is an
    # installed package now, resolved via `-m pie` regardless of cwd, not
    # a flat directory of scripts that has to be physically present next
    # to the output. The symlink approach also could not have worked once
    # pie's sibling modules use package-relative imports: a symlinked
    # main.py run as a bare script has no `__package__` for `from
    # .globalvar import ...` to resolve against.

    # v1.3.0 sweep policy: all 40 radii are attempted (v1.2.0 stopped at the
    # first failure), and every failed radius costs a warm + a cold Newton
    # attempt (~90 s each on this shared box under load) -- the 900 s budget
    # of v1.2.0 timed out; measured wall is recorded in
    # docs/dev/notes/solver_v1.3.0.md sec. 4.
    result = run_pie("-m", "pie", "p", "0.346", "0.424", "S", "Edmund",
                      cwd=str(workdir), timeout=5400)
    assert result.returncode == 0, (
        f"pie exited {result.returncode}:\n{result.stdout[-4000:]}"
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
        "regenerating (see tests/README.md)"
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
