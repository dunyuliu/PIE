"""Regression tests for PATHWAY_FORWARD.md item 26's three findings in
pie/robust_runner.py (lars-eriksson diagnosis, fixed here):

  (a) done-check/job-run race: two overlapping runs could both pass
      `already_done` (sentinel not written yet) and both launch
      `python -m pie` for the same job, each truncating the same
      pMetaData csv ('w' mode) -- second write wins. Fixed with an
      atomic (O_CREAT|O_EXCL) per-job lock file, acquired as the first
      thing `run_one_job` does; a caller that loses the race gets
      `RunnerStatus.SKIPPED_LOCKED` and never calls `subprocess.run`.
  (b) a bare `sys.exit()` in pie/main.py's `code_mode == 'plot'` branch,
      before the pMetaData csv is opened -- audited, not fixed: see this
      PR's description for why it is unreachable from the runner's
      actual argument space (Job.argv() hardcodes code_mode='p'; no
      manifest column, no caller anywhere in the repo, ever sets
      code_mode='plot' for pie.main).
  (c) `pie_workers()` silently defaulted to 4 on OSError/AttributeError
      (os.cpu_count()/os.getloadavg() unavailable) with no record of why
      -- a silent fallback (PROJECT_RULES.md rule 2), unlike the
      sibling `git_sha_error` pattern in `provenance()` which already
      records its own failure. Fixed: the fallback now prints the
      exception to stderr before returning 4.

New file for new/changed behavior; edits no existing testsys/*.py test.
"""
import os

import pytest

pytestmark = pytest.mark.unit

from pie import robust_runner as rr  # pie is installed via pyproject.toml (board item 28e)


def test_pie_workers_fallback_logs_reason(monkeypatch, capsys):
    monkeypatch.delenv("PIE_WORKERS", raising=False)

    def _boom():
        raise OSError("cpu_count unavailable (simulated)")
    monkeypatch.setattr(os, "cpu_count", _boom)

    result = rr.pie_workers()
    assert result == 4  # behavior unchanged -- it's the silence that was the bug
    captured = capsys.readouterr()
    assert "falling back to 4" in captured.err
    assert "cpu_count unavailable (simulated)" in captured.err


def test_acquire_lock_is_atomic(tmp_path):
    lock = tmp_path / "sub" / ".runner_lock_0.00.json"
    assert rr._acquire_lock(lock, {"who": "first"})
    assert lock.exists()
    # A second claimant must fail, not silently overwrite the first's lock.
    assert not rr._acquire_lock(lock, {"who": "second"})
    rr._release_lock(lock)
    assert not lock.exists()
    # Released -- a new claimant can now succeed.
    assert rr._acquire_lock(lock, {"who": "third"})
    rr._release_lock(lock)


def test_run_one_job_skips_without_racing_when_already_locked(tmp_path, monkeypatch):
    """Simulates the item 26a race directly: another process (or thread)
    has already claimed this job's lock when run_one_job is entered.
    Before the fix, run_one_job had no notion of a lock at all and would
    proceed straight to `subprocess.run`, truncating the pMetaData csv a
    second time -- this test fails on that old code because the
    monkeypatched subprocess.run raises if ever invoked."""
    job = rr.Job(0.346, 0.424, "S", "Edmund")
    lock = rr.lock_path(job, tmp_path)
    assert rr._acquire_lock(lock, {"holder": "other-process"})

    def _must_not_run(*a, **k):
        raise AssertionError("subprocess.run must not be called for a locked job")
    monkeypatch.setattr(rr.subprocess, "run", _must_not_run)

    result = rr.run_one_job(job, src_dir=tmp_path)

    assert result["status"] == rr.RunnerStatus.SKIPPED_LOCKED.value
    assert result["done"] is False
    assert not rr.sentinel_path(job, tmp_path).exists()
    assert not job.pmetadata_file(tmp_path).exists()
    # The OTHER holder's lock is untouched -- we must only ever release a
    # lock we ourselves acquired.
    assert lock.exists()


def test_acquire_lock_reclaims_stale_same_host_dead_pid_lock(tmp_path):
    """A lock from a crashed (SIGKILLed) runner on THIS host, naming a pid
    that no longer exists, must be reclaimable -- otherwise a restart
    after a crash would report every in-flight job as permanently locked
    instead of redoing it (the exact regression
    testsys/integration/test_robust_runner_crash_restart.py's
    sigkill-then-restart test caught: before this fix, the restart's
    formerly-hung job came back SKIPPED_LOCKED instead of CONVERGED)."""
    import json
    import socket
    lock = tmp_path / ".runner_lock_0.00.json"
    # A pid essentially guaranteed not to exist (the test's own process
    # group as a floor).
    dead_pid = os.getpid() + 1_000_000
    lock.write_text(json.dumps({"pid": dead_pid, "host": socket.gethostname()}))
    assert rr._acquire_lock(lock, {"who": "new-claimant"})
    assert '"new-claimant"' in lock.read_text()


def test_acquire_lock_does_not_reclaim_other_host_lock(tmp_path):
    """A lock recorded by a different host is never auto-reclaimed (no
    cross-host liveness channel) -- it blocks until released or --force,
    not silently stolen."""
    import json
    lock = tmp_path / ".runner_lock_0.00.json"
    lock.write_text(json.dumps({"pid": 1, "host": "some-other-node"}))
    assert not rr._acquire_lock(lock, {"who": "new-claimant"})


def test_run_one_job_releases_its_own_lock_after_running(tmp_path, monkeypatch):
    """A job that DOES get the lock must release it once done, so a later
    (non-overlapping) run isn't blocked forever by a stale claim."""
    job = rr.Job(0.346, 0.424, "S", "Edmund")

    class FakeCompleted:
        returncode = 1  # crash is fine here -- only the lock lifecycle is under test
        stderr = "boom"

    monkeypatch.setattr(rr.subprocess, "run", lambda *a, **k: FakeCompleted())
    result = rr.run_one_job(job, src_dir=tmp_path)
    assert result["status"] == rr.RunnerStatus.PROCESS_CRASHED.value
    assert not rr.lock_path(job, tmp_path).exists()
