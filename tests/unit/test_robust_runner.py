"""Unit tests for src/robust_runner.py (PATHWAY_FORWARD.md item 22): Job
validation/identity/paths, the ErrorCode-based per-job status label, the
Monte Carlo manifest generator, and the PIE_WORKERS cap formula. No file
I/O, no subprocess, no physics solve -- the CSV/launcher/sentinel checks
are in tests/contract/test_robust_runner_manifest.py, the real-subprocess
crash/restart proof in tests/integration/test_robust_runner_crash_restart.py.

New file for a new module; edits no existing src/*.py or tests/*.py.
"""
import os
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

from pie import robust_runner as rr  # pie is installed via pyproject.toml (board item 28e)

SRC = Path(rr.__file__).resolve().parent
# monteCarlo.run.py/scheduler.py moved out of pie/ to util/run/ (board item
# 28b) -- they are operational scripts with no pie-internal imports, unlike
# robust_runner.py (imported as pie.robust_runner by this test, self-locating
# its results dir to the package directory); globalvar.py stays read from SRC.
RUN_SCRIPTS = Path(__file__).resolve().parent.parent.parent / "util" / "run"


def test_error_code_is_imported_from_globalvar_not_copied():
    # Requirement 3: reuse pie/globalvar.py's ErrorCode, not a copy. (Not an
    # `is` check: pielib.import_src re-imports globalvar per test, which
    # makes a new class object with the same members.)
    from pie import globalvar
    assert rr.ErrorCode.__module__ == "pie.globalvar"
    assert {m.name: m.value for m in rr.ErrorCode} == {m.name: m.value for m in globalvar.ErrorCode}
    assert "class ErrorCode" not in (SRC / "robust_runner.py").read_text()


def test_runner_statuses_do_not_collide_with_error_code_names():
    assert not set(s.value for s in rr.RunnerStatus) & set(rr.ErrorCode.__members__)


def test_job_validation():
    with pytest.raises(ValueError, match="requires chi_Si_icb"):
        rr.Job(0.346, 0.424, "S+Si", "Edmund")
    with pytest.raises(ValueError, match="only used for S\\+Si"):
        rr.Job(0.346, 0.424, "S", "Edmund", chi_Si_icb=0.05)
    with pytest.raises(ValueError, match="light_element"):
        rr.Job(0.346, 0.424, "Fe", "Edmund")
    with pytest.raises(ValueError, match="liquidus_eq"):
        rr.Job(0.346, 0.424, "S", "edmund")


def test_job_id_is_stable_ignores_seed_and_distinguishes_inputs():
    a = rr.Job(0.346, 0.424, "S", "Edmund")
    assert a.job_id == rr.Job(0.346, 0.424, "S", "Edmund", seed=7).job_id
    assert a.job_id != rr.Job(0.346, 0.424, "Si", "Edmund").job_id
    assert a.job_id != rr.Job(0.3460000001, 0.424, "S", "Edmund").job_id
    assert re.fullmatch(r"[0-9a-f]{12}", a.job_id)


def test_argv_includes_chi_only_for_s_plus_si():
    assert rr.Job(0.346, 0.424, "S", "Edmund").argv() == \
        ["main.py", "p", "0.346", "0.424", "S", "Edmund"]
    assert rr.Job(0.346, 0.424, "S+Si", "Edmund", 0.05).argv() == \
        ["main.py", "p", "0.346", "0.424", "S+Si", "Edmund", "0.05"]


def test_paths_match_globalvar_formulas(tmp_path):
    # model_path + pMetaData name are where main.py writes; if they drift
    # from src/globalvar.py the sentinel lands in the wrong directory.
    # Pin against globalvar's own source text, not a re-typed copy.
    text = (SRC / "globalvar.py").read_text()
    assert "model_path              = './results/CMR2_'+\"{:.17f}\".format(CMR2)+'_CMC_'+\"{:.17f}\".format(CMC)+'_'+light_element+'_'+liquidus_eq+'/'" in text
    assert "pMetaDataFileName           = 'pMetaData_'+\"{:.2f}\".format(chi_Si_icb)+'.csv'" in text

    job = rr.Job(0.346, 0.424, "S+Si", "Edmund", chi_Si_icb=0.08)
    assert job.model_path(tmp_path) == tmp_path / "results" / (
        "CMR2_{:.17f}_CMC_{:.17f}_S+Si_Edmund".format(0.346, 0.424))
    assert job.pmetadata_file(tmp_path).name == "pMetaData_0.08.csv"
    assert rr.sentinel_path(job, tmp_path).parent == job.model_path(tmp_path)
    # S/Si: globalvar.py hard-codes chi_Si_icb = 0.0.
    assert rr.Job(0.346, 0.424, "S", "Edmund").pmetadata_file(tmp_path).name == "pMetaData_0.00.csv"


def test_job_status_label_uses_error_code_names():
    E = rr.ErrorCode
    assert rr.job_status_from_codes({E.CONVERGED.name: 40}) == "CONVERGED"
    assert rr.job_status_from_codes(
        {E.CONVERGED.name: 30, E.RICB_GE_RCMB.name: 8, E.NEWTON_MAXIT.name: 2}) == "RICB_GE_RCMB"
    # tie -> lower ErrorCode value wins (deterministic)
    assert rr.job_status_from_codes(
        {E.RICB_GE_RCMB.name: 3, E.NEWTON_MAXIT.name: 3}) == "NEWTON_MAXIT"
    assert rr.job_status_from_codes({E.SI_ABOVE_LIQUIDUS_MAX.name: 1}) == "SI_ABOVE_LIQUIDUS_MAX"


def test_mc_jobs_matches_monte_carlo_script_constants_and_scheduler_grid():
    # mc_jobs re-expresses monteCarlo.run.py + scheduler.py as a manifest;
    # pin its defaults to those scripts' literal constants so they can't drift.
    mc = (RUN_SCRIPTS / "monteCarlo.run.py").read_text()
    assert re.search(r"^meanCMR2 = 0\.346$", mc, re.M)
    assert re.search(r"^stdCMR2  = 0\.014$", mc, re.M)
    assert re.search(r"^CMC0      = 0\.426$", mc, re.M)
    assert "rng.normal(meanCMR2, stdCMR2, 1)" in mc and "CMC = CMC0*meanCMR2/CMR2" in mc
    assert "np.linspace(0.0, 0.15, 16)" in (RUN_SCRIPTS / "scheduler.py").read_text()

    import numpy as np
    jobs = rr.mc_jobs(2, seed_base=100)
    assert len(jobs) == 2 * (16 + 2)
    first = jobs[0]
    want = float(np.random.default_rng(100).normal(0.346, 0.014, 1)[0])
    assert first.CMR2 == want and first.CMC == 0.426 * 0.346 / want and first.seed == 100
    assert [j.light_element for j in jobs[:18]] == ["S+Si"] * 16 + ["S", "Si"]
    assert jobs[18].seed == 101 and jobs[18].CMR2 != first.CMR2
    assert len({j.job_id for j in jobs}) == len(jobs)


def test_pie_workers_env_override(monkeypatch):
    monkeypatch.setenv("PIE_WORKERS", "3")
    assert rr.pie_workers() == 3
    monkeypatch.setenv("PIE_WORKERS", "0")
    assert rr.pie_workers() == 1


@pytest.mark.parametrize("cpu,load,expected", [(16, 2.0, 6), (64, 1.0, 24), (8, 7.5, 4)])
def test_pie_workers_matches_conftest(monkeypatch, cpu, load, expected):
    # The formula is copied from tests/conftest.py:pie_workers() (production
    # must not import tests); this pins the two together under fixed inputs.
    monkeypatch.delenv("PIE_WORKERS", raising=False)
    monkeypatch.setattr(os, "cpu_count", lambda: cpu)
    monkeypatch.setattr(os, "getloadavg", lambda: (load, load, load))
    from pielib import pie_workers as conftest_pie_workers
    assert rr.pie_workers() == conftest_pie_workers() == expected
