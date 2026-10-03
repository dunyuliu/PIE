"""Regression tests for PATHWAY_FORWARD.md item 29(a): the stale-lock
reclaim in pie/robust_runner.py was not atomic.

Old sequence in `_acquire_lock` on FileExistsError: `_lock_is_stale` ->
`_release_lock` (unconditional os.remove) -> O_EXCL create. Two
reclaimers A and B could both pass the staleness check on the same
dead-pid lock; A removes+recreates it, then B's unconditional remove
deletes A's FRESH lock and B's O_EXCL succeeds -- both now believe they
hold the job (the double-truncation item 26 built the lock to prevent).
`run_one_job`'s `finally: _release_lock(lock)` had the same flaw: it
removed whatever was at the path, including a lock it never wrote.

Fix: reclaim happens under an flock'd per-lock mutex with the staleness
check REPEATED inside, and swaps the file in with `os.replace` (path is
never absent); every lock carries a per-claimant `token`, and
`_release_lock(path, token)` is compare-then-delete.

The race test below forces the exact interleaving deterministically with
two real forked processes (not a timing lottery): B is held after its
first staleness check until A has fully reclaimed the lock and is still
alive; only then does B continue. On the old code both return a claim
(red); on the new code exactly one does (green).

New file for new/changed behavior; edits no existing testsys/*.py test.
"""
import json
import multiprocessing
import os
import socket

import pytest

pytestmark = pytest.mark.unit

from pie import robust_runner as rr  # pie is installed via pyproject.toml (board item 28e)


def _dead_pid():
    # A pid essentially guaranteed not to exist (same floor as item 26's test).
    return os.getpid() + 1_000_000


def _write_stale_lock(lock):
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(json.dumps({"pid": _dead_pid(), "host": socket.gethostname(),
                                "token": "crashed-runner"}))


def _reclaimer(lock, role, q, b_checked, a_done, exit_ok):
    """Child body (fork start method; `rr` is inherited already imported).
    role 'slow': the FIRST staleness check in this process signals the
    parent and then blocks until A has finished reclaiming -- i.e. B has
    already decided 'stale' before A touched the file, which is the
    interleaving item 29a describes. role 'fast': no hook."""
    if role == "slow":
        real = rr._lock_is_stale
        state = {"first": True}

        def hooked(path):
            result = real(path)
            if state["first"]:
                state["first"] = False
                b_checked.set()
                assert a_done.wait(30), "A never finished -- test harness fault"
            return result
        rr._lock_is_stale = hooked
    try:
        token = rr._acquire_lock(lock, {"pid": os.getpid(), "host": socket.gethostname(),
                                        "who": role})
        q.put((role, token))
    except BaseException as e:  # make the parent fail loudly, not hang
        q.put((role, "EXC:{!r}".format(e)))
        raise
    # Stay alive until told: a holder that exits here would (legitimately)
    # look dead to the other reclaimer and void the test.
    exit_ok.wait(60)


def test_two_reclaimers_racing_on_one_dead_pid_lock_yield_exactly_one_holder(tmp_path):
    ctx = multiprocessing.get_context("fork")
    lock = tmp_path / "model" / ".runner_lock_0.00.json"
    _write_stale_lock(lock)

    q = ctx.Queue()
    b_checked, a_done, exit_ok = ctx.Event(), ctx.Event(), ctx.Event()
    procs = []
    try:
        b = ctx.Process(target=_reclaimer, args=(lock, "slow", q, b_checked, a_done, exit_ok))
        b.start(); procs.append(b)
        assert b_checked.wait(30), "B never reached its staleness check"

        a = ctx.Process(target=_reclaimer, args=(lock, "fast", q, b_checked, a_done, exit_ok))
        a.start(); procs.append(a)
        role, a_token = q.get(timeout=30)
        assert role == "fast"
        assert a_token and not str(a_token).startswith("EXC:"), a_token
        a_done.set()  # A holds the lock and is alive -- now let B continue

        role, b_token = q.get(timeout=30)
        assert role == "slow"
        assert not str(b_token).startswith("EXC:"), b_token

        claims = [t for t in (a_token, b_token) if t]
        assert len(claims) == 1, (
            "both reclaimers believe they hold the lock (item 29a): A={!r} B={!r}"
            .format(a_token, b_token))
        on_disk = json.loads(lock.read_text())
        assert on_disk["token"] == a_token
        assert on_disk["who"] == "fast"
    finally:
        exit_ok.set()
        for p in procs:
            p.join(30)
            if p.is_alive():
                p.kill()


def test_acquire_lock_returns_token_recorded_in_file(tmp_path):
    lock = tmp_path / ".runner_lock_0.00.json"
    token = rr._acquire_lock(lock, {"who": "me"})
    assert isinstance(token, str) and token
    assert json.loads(lock.read_text())["token"] == token
    assert rr._acquire_lock(lock, {"who": "other"}) is None


def test_release_lock_with_token_is_compare_then_delete(tmp_path):
    """A releaser must never remove a lock it did not write -- after a
    reclaim replaced ours, our token no longer matches and the file stays."""
    lock = tmp_path / ".runner_lock_0.00.json"
    mine = rr._acquire_lock(lock, {"who": "me"})
    lock.write_text(json.dumps({"who": "reclaimer", "token": "someone-else"}))
    assert rr._release_lock(lock, mine) is False
    assert lock.exists()
    assert json.loads(lock.read_text())["token"] == "someone-else"
    # Matching token: removed.
    lock.write_text(json.dumps({"who": "me", "token": mine}))
    assert rr._release_lock(lock, mine) is True
    assert not lock.exists()
    # Unconditional form (--force) still works, and is a no-op on a missing file.
    assert rr._release_lock(lock) is False


def test_reclaim_replaces_stale_lock_without_absent_window(tmp_path):
    lock = tmp_path / ".runner_lock_0.00.json"
    _write_stale_lock(lock)
    ino_before = lock.stat().st_ino
    token = rr._acquire_lock(lock, {"who": "new-claimant"})
    assert token
    body = json.loads(lock.read_text())
    assert body["token"] == token and body["who"] == "new-claimant"
    assert lock.stat().st_ino != ino_before  # swapped in by rename, not rewritten in place
    assert not list(tmp_path.glob("*.tmp"))  # no scratch left behind


def test_run_one_job_finally_does_not_remove_a_lock_it_did_not_write(tmp_path, monkeypatch):
    """`run_one_job`'s finally used to os.remove whatever sat at the lock
    path. If a reclaimer had replaced our lock mid-run (it can only do so
    if it judged us dead -- but the release must still be defensive), the
    finally would delete THEIR lock and open the door to a third runner."""
    job = rr.Job(0.346, 0.424, "S", "Edmund")
    lock = rr.lock_path(job, tmp_path)

    class FakeCompleted:
        returncode = 1
        stderr = "boom"

    def _run_and_steal(*a, **k):
        assert lock.exists()
        lock.write_text(json.dumps({"who": "reclaimer", "token": "not-ours"}))
        return FakeCompleted()

    monkeypatch.setattr(rr.subprocess, "run", _run_and_steal)
    result = rr.run_one_job(job, src_dir=tmp_path)
    assert result["status"] == rr.RunnerStatus.PROCESS_CRASHED.value
    assert lock.exists(), "finally removed a lock written by someone else"
    assert json.loads(lock.read_text())["token"] == "not-ours"
