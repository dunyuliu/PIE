"""Crash/restart tests for src/robust_runner.py (PATHWAY_FORWARD.md item 22).

Real subprocesses, real SIGKILL, real resume -- against a stand-in
`main.py` instead of the Mercury solver (a real solve is ~minutes per job;
these tests are about process/resume mechanics, not physics). The stand-in
reproduces the parts of src/main.py's 'p' mode the runner depends on:
  * the argv contract `main.py p CMR2 CMC light_element liquidus_eq [chi]`;
  * output at globalvar.py's model_path / pMetaData_<chi>.csv;
  * the csv HEADER written before the sweep starts (src/main.py:146-149),
    then one row per radius with an `error_code` column -- so a job killed
    mid-sweep leaves a partial csv behind, exactly like the real code.
Every invocation appends a line to `invocations.log`, so a test can prove
a finished job was NOT re-run, not just that the runner said "skipped".

New file for a new module; edits no existing src/*.py or testsys/*.py.
"""
import json
import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

from pie import robust_runner as rr  # pie is installed via pyproject.toml (board item 28e)

RUNNER = Path(rr.__file__).resolve()

FAKE_MAIN = textwrap.dedent("""\
    # Stand-in for `python -m pie` 'p' mode -- see the test module
    # docstring. Lives at <fake src>/pie/__main__.py (board item 28e: the
    # runner now invokes `-m pie`, which resolves "pie" against a cwd-
    # inserted directory ahead of the real installed package -- see
    # pie/robust_runner.py:run_one_job), so __file__'s parent is
    # <fake src>/pie/, one level below where invocations.log/results
    # should land (<fake src>/, matched by this test module's `_invocations`
    # and `rr.Job.model_path`).
    import os, sys, time
    from pathlib import Path

    _, mode, CMR2, CMC, light, liquidus = sys.argv[:6]
    chi = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
    here = Path(__file__).resolve().parent.parent
    with open(here / "invocations.log", "a") as f:
        f.write(CMR2 + "\\n")

    model_path = Path("results") / "CMR2_{:.17f}_CMC_{:.17f}_{}_{}".format(
        float(CMR2), float(CMC), light, liquidus)
    model_path.mkdir(parents=True, exist_ok=True)
    csv_path = model_path / "pMetaData_{:.2f}.csv".format(chi)
    csv_path.write_text("chi_Si_icb,ricb,error_code\\n")       # header first, like main.py
    with open(csv_path, "a") as f:
        f.write("{},10.0,0\\n".format(chi))                       # first radius
    first_attempt = not (model_path / ".attempted").exists()
    (model_path / ".attempted").touch()

    if first_attempt and os.environ.get("TEST_CRASH_CMR2") == CMR2:
        os._exit(137)                                            # die mid-sweep
    if first_attempt and os.environ.get("TEST_HANG_CMR2") == CMR2:
        time.sleep(300)                                          # wait to be SIGKILLed

    with open(csv_path, "a") as f:
        f.write("{},50010.0,0\\n{},100010.0,5\\n".format(chi, chi))  # 5 = RICB_GE_RCMB
    """)


@pytest.fixture
def fake_src(tmp_path):
    src = tmp_path / "src"
    pkg = src / "pie"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "__main__.py").write_text(FAKE_MAIN)
    return src


def _invocations(src):
    p = src / "invocations.log"
    return p.read_text().split() if p.exists() else []


def _records(log):
    return [json.loads(l) for l in Path(log).read_text().splitlines()]


def test_crash_mid_sweep_then_resume_reruns_only_the_crashed_job(fake_src, monkeypatch):
    crashy = rr.Job(0.400, 0.424, "S", "Edmund")
    ok = rr.Job(0.346, 0.424, "S+Si", "Edmund", chi_Si_icb=0.05)
    monkeypatch.setenv("TEST_CRASH_CMR2", rr._fmt_float(crashy.CMR2))
    log = fake_src / "results" / "runner_status.jsonl"

    first = rr.run_local([crashy, ok], src_dir=fake_src, status_log_path=log,
                         workers=2, python_exe=sys.executable, run_id="attempt1")
    by_id = {r["job_id"]: r for r in first["results"]}
    assert by_id[crashy.job_id]["status"] == rr.RunnerStatus.PROCESS_CRASHED.value
    assert by_id[crashy.job_id]["returncode"] == 137
    # Per-job status in item 16's vocabulary: rows 0,0,5 -> RICB_GE_RCMB, counts kept.
    assert by_id[ok.job_id]["status"] == rr.ErrorCode.RICB_GE_RCMB.name
    assert by_id[ok.job_id]["error_code_counts"] == {"CONVERGED": 2, "RICB_GE_RCMB": 1}
    # The crashed job's partial csv IS on disk -- the old "csv exists" oracle
    # would call it done. The runner does not.
    assert crashy.pmetadata_file(fake_src).exists()
    assert not rr.already_done(crashy, fake_src)
    assert rr.already_done(ok, fake_src)
    ok_sentinel = rr.sentinel_path(ok, fake_src)
    ok_sentinel_bytes = ok_sentinel.read_bytes()

    second = rr.run_local([crashy, ok], src_dir=fake_src, status_log_path=log,
                          workers=2, python_exe=sys.executable, run_id="attempt2")
    assert second["skipped"] == 1
    assert [r["job_id"] for r in second["results"]] == [crashy.job_id]
    assert second["results"][0]["status"] == rr.ErrorCode.RICB_GE_RCMB.name
    assert rr.already_done(crashy, fake_src)

    # Proof the finished job was not re-run: main.py invoked once for it,
    # twice for the crashed one; its sentinel is byte-identical.
    inv = _invocations(fake_src)
    assert inv.count(rr._fmt_float(ok.CMR2)) == 1
    assert inv.count(rr._fmt_float(crashy.CMR2)) == 2
    assert ok_sentinel.read_bytes() == ok_sentinel_bytes
    # The crash re-run rewrote the csv from scratch (main.py opens it 'w'):
    assert rr.summarize_error_codes(crashy.pmetadata_file(fake_src))[0] == 3

    ends = [r for r in _records(log) if r["event"] == "end" and r["job_id"] == crashy.job_id]
    assert [(r["run_id"], r["status"]) for r in ends] == [
        ("attempt1", "PROCESS_CRASHED"), ("attempt2", "RICB_GE_RCMB")]
    sentinel = json.loads(rr.sentinel_path(crashy, fake_src).read_text())
    assert sentinel["run_id"] == "attempt2" and len(sentinel["git_sha"]) == 40


def test_sigkill_whole_runner_then_restart_finishes_only_missing_work(fake_src, tmp_path):
    fast = rr.Job(0.346, 0.424, "S", "Edmund")
    hangs = rr.Job(0.355, 0.424, "Si", "Edmund")
    manifest = tmp_path / "manifest.csv"
    rr.write_manifest(manifest, [fast, hangs])
    log = tmp_path / "status.jsonl"
    cmd = [sys.executable, str(RUNNER), "run", str(manifest), "--src-dir", str(fake_src),
           "--status-log", str(log), "--workers", "2"]
    env = dict(os.environ, TEST_HANG_CMR2=rr._fmt_float(hangs.CMR2))

    # Own session -> own process group: killpg hits the runner AND its
    # main.py children, like a node failure / scancel -9 would.
    proc = subprocess.Popen(cmd, env=env, start_new_session=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 60
    while time.time() < deadline:
        if rr.already_done(fast, fake_src) and rr._fmt_float(hangs.CMR2) in _invocations(fake_src):
            break
        assert proc.poll() is None, proc.communicate()
        time.sleep(0.1)
    else:
        os.killpg(proc.pid, signal.SIGKILL)
        pytest.fail("runner never reached the mid-run state")
    os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=10)
    assert proc.returncode == -signal.SIGKILL

    assert rr.already_done(fast, fake_src)
    assert hangs.pmetadata_file(fake_src).exists()      # partial csv left behind
    assert not rr.already_done(hangs, fake_src)

    # Restart: same manifest, same command, no hang this time.
    rerun = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    assert rerun.returncode == 0, rerun.stderr
    summary = json.loads(rerun.stdout)
    assert (summary["total"], summary["skipped"], summary["ran"]) == (2, 1, 1)
    assert summary["statuses"] == {"RICB_GE_RCMB": 1}
    assert rr.already_done(hangs, fake_src)

    inv = _invocations(fake_src)
    assert inv.count(rr._fmt_float(fast.CMR2)) == 1
    assert inv.count(rr._fmt_float(hangs.CMR2)) == 2
    # The killed attempt left a 'start' with no 'end'; the log is still
    # valid JSONL (no torn line) and the restart appended a full pair.
    recs = _records(log)
    hang_events = [r["event"] for r in recs if r["job_id"] == hangs.job_id]
    assert hang_events == ["start", "start", "end"]


def test_run_one_cli_is_what_a_tacc_launcher_line_executes(fake_src, tmp_path):
    jobs = [rr.Job(0.346, 0.424, "S", "Edmund"), rr.Job(0.346, 0.424, "Si", "Edmund")]
    manifest = tmp_path / "m.csv"
    rr.write_manifest(manifest, jobs)
    log = tmp_path / "status.jsonl"
    rr.write_tacc_launcher(jobs, manifest, src_dir=fake_src, status_log_path=log)
    lines = (fake_src / "commands_launcher").read_text().splitlines()
    assert len(lines) == 2

    # Execute the launcher lines the way LAUNCHER does (cwd = src/).
    for line in lines:
        r = subprocess.run(line, shell=True, cwd=fake_src, capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, r.stderr
    assert all(rr.already_done(j, fake_src) for j in jobs)

    # A resubmitted allocation re-running the same lines does no work.
    r = subprocess.run(lines[0], shell=True, cwd=fake_src, capture_output=True, text=True, timeout=60)
    assert json.loads(r.stdout)["status"] == "SKIPPED_ALREADY_DONE"
    assert len(_invocations(fake_src)) == 2
    # And a regenerated launcher is empty.
    assert rr.write_tacc_launcher(jobs, manifest, src_dir=fake_src)["written"] == 0
