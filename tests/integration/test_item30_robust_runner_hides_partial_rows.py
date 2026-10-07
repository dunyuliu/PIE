"""Regression test for PATHWAY_FORWARD.md item 30, bug #3 (board item 30):

pie/robust_runner.py::run_one_job only calls `summarize_error_codes(csv_path)`
(which sets the real row count `n_rows`) `if returncode == 0`. On a non-zero
return code -- exactly what item 30's bug #1/#2 produces: a sweep job that
crashes mid-run with an uncaught ValueError after writing several good csv
rows -- `n_rows` stays at its hard-coded default 0 regardless of how many
rows the crashed process actually wrote before it died. This hides real
partial output from monitoring/resume logic (an operator watching
`runner_status.jsonl` or a status summary has no way to see "this crashed
job still salvaged N rows").

This test uses the same FAKE_MAIN stand-in pattern as
tests/integration/test_robust_runner_crash_restart.py (a real subprocess
mimicking `python -m pie`'s csv-writing contract), but writes several good
rows BEFORE crashing, then asserts the returned `n_rows` reflects the rows
actually on disk.

Current (buggy) behaviour: `n_rows == 0` even though the csv has real rows
on disk -- this test FAILS on current HEAD.

Expected (fixed) behaviour: `run_one_job` reads the csv (if present) even on
a non-zero return code and reports the true row count.
"""
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from pie import robust_runner as rr  # pie is installed via pyproject.toml (board item 28e)

N_ROWS_BEFORE_CRASH = 4

FAKE_MAIN_CRASH_AFTER_ROWS = textwrap.dedent(f"""\
    # Stand-in for `python -m pie` 'p' mode that writes {N_ROWS_BEFORE_CRASH}
    # good csv rows (as real radii would converge) and THEN dies with an
    # uncaught exception mid-sweep -- reproducing item 30 bug #1/#2's
    # observable effect on robust_runner (the exit code and partial csv),
    # without re-running the real Mercury solver (see
    # test_robust_runner_crash_restart.py's module docstring for why a
    # stand-in is used here).
    import sys
    from pathlib import Path

    _, mode, CMR2, CMC, light, liquidus = sys.argv[:6]
    chi = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0

    model_path = Path("results") / "CMR2_{{:.17f}}_CMC_{{:.17f}}_{{}}_{{}}".format(
        float(CMR2), float(CMC), light, liquidus)
    model_path.mkdir(parents=True, exist_ok=True)
    csv_path = model_path / "pMetaData_{{:.2f}}.csv".format(chi)
    with open(csv_path, "w") as f:
        f.write("chi_Si_icb,ricb,error_code\\n")
        for k in range({N_ROWS_BEFORE_CRASH}):
            f.write("{{}},{{}},0\\n".format(chi, 10.0 + k * 50000.0))

    raise ValueError("All components of the initial state y0 must be finite.")
    """)


@pytest.fixture
def fake_src(tmp_path):
    src = tmp_path / "src"
    pkg = src / "pie"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(FAKE_MAIN_CRASH_AFTER_ROWS)
    return src


def test_crashed_job_still_reports_the_rows_actually_written(fake_src):
    job = rr.Job(0.346, 0.424, "S", "Edmund")

    result = rr.run_one_job(job, src_dir=fake_src, status_log=None, run_id="attempt1",
                            python_exe=sys.executable, timeout=60)

    assert result["status"] == rr.RunnerStatus.PROCESS_CRASHED.value
    assert result["returncode"] != 0

    csv_path = job.pmetadata_file(fake_src)
    assert csv_path.exists(), "the crashed job's partial csv must be on disk"
    n_rows_on_disk, _ = rr.summarize_error_codes(csv_path)
    assert n_rows_on_disk == N_ROWS_BEFORE_CRASH, "fixture sanity check: the csv itself must carry the rows"

    # This is the actual regression check: on current HEAD, run_one_job
    # never reads the csv when returncode != 0, so it reports n_rows == 0
    # even though N_ROWS_BEFORE_CRASH real rows are sitting on disk.
    assert result["n_rows"] == N_ROWS_BEFORE_CRASH, (
        f"run_one_job must report the rows actually written before a "
        f"mid-sweep crash (found {N_ROWS_BEFORE_CRASH} on disk), not "
        f"silently report 0 just because returncode != 0 (item 30 bug #3)"
    )

