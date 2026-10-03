#!/usr/bin/env python3
"""One-command tiered test runner for PIE.

    /usr/bin/python3 testsys/run.py            # fast tiers (default): unit + contract + integration
    /usr/bin/python3 testsys/run.py unit
    /usr/bin/python3 testsys/run.py contract
    /usr/bin/python3 testsys/run.py integration
    /usr/bin/python3 testsys/run.py e2e        # opt-in: full scheduler.py sweep, minutes
    /usr/bin/python3 testsys/run.py all        # every tier, including e2e
    /usr/bin/python3 testsys/run.py -n 8 all   # xdist across test files, 8 workers
                                                # (default worker count: PIE_WORKERS,
                                                # see testsys/conftest.py:pie_workers();
                                                # -n 0 or PIE_WORKERS=1 disables xdist)

Sets MPLBACKEND=Agg (headless) and one BLAS thread per worker before
dispatching to pytest. PYTHONNOUSERSITE re-exec logic that used to live
here (to work around a two-matplotlib-installs conflict on the dev box's
default system Python) was removed 2026-10-02: PROJECT_RULES.md rule
3b/3c requires running this suite under the pinned `.venv-py312` venv,
whose own interpreter has `site.ENABLE_USER_SITE == False` by
construction (confirmed: `.venv-py312/bin/python3.12 -c "import site;
print(site.ENABLE_USER_SITE)"` -> False, with or without
PYTHONNOUSERSITE set) -- the conflict this re-exec compensated for is
impossible by construction on the required interpreter, so the
workaround no longer serves a purpose. See
testsys/contract/test_gate_runs_in_pinned_venv.py for the test that
gates "this is actually running under that interpreter."

Shared-machine note (PROJECT_RULES.md): `-n` drives pytest-xdist only;
every in-test ProcessPoolExecutor pool reads the SAME `PIE_WORKERS` knob
via conftest.py's `pool_workers()`, which collapses to 1 inside an xdist
worker so parallelism never multiplies (xdist workers x pool size).
"""
import os
import sys

TIERS = {
    "unit": ["-m", "unit"],
    "contract": ["-m", "contract"],
    "integration": ["-m", "integration"],
    "parity": ["-m", "parity"],
    "e2e": ["-m", "e2e"],
    "published_wide": ["-m", "published_wide"],
}
FAST_DEFAULT = ["unit", "contract", "integration"]


def _parse_n(args):
    """Pull an optional `-n WORKERS` out of args (anywhere); returns
    (remaining_args, workers_or_None). Mirrors pytest-xdist's own `-n` so
    `testsys/run.py -n 8 all` reads the same as `pytest -n 8`."""
    args = list(args)
    n = None
    for i, a in enumerate(args):
        if a == "-n" and i + 1 < len(args):
            n = args[i + 1]
            del args[i:i + 2]
            break
        if a.startswith("-n="):
            n = a[3:]
            del args[i]
            break
    return args, n


def main():
    args, n_arg = _parse_n(sys.argv[1:])
    args = args or FAST_DEFAULT
    if args == ["all"]:
        args = list(TIERS)
    unknown = [a for a in args if a not in TIERS]
    if unknown:
        print(f"unknown tier(s): {unknown}. Known tiers: {sorted(TIERS)} "
              f"(or 'all')", file=sys.stderr)
        return 2

    os.environ.setdefault("MPLBACKEND", "Agg")
    # Shared-machine headroom (PROJECT_RULES.md): one BLAS thread per
    # worker -- xdist/ProcessPoolExecutor already gives us process-level
    # parallelism, so a multi-threaded BLAS underneath would multiply it.
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    sys.path.insert(0, here)
    from conftest import pie_workers  # noqa: E402

    try:
        os.nice(10)  # shared-machine headroom; children inherit this niceness
    except (AttributeError, OSError):
        pass

    # Default xdist worker count is SMALLER than PIE_WORKERS, not equal to
    # it: several modules share a module-scoped ProcessPoolExecutor pool
    # (conftest.py:pool_workers()), capped by PIE_WORKERS // n_xdist_workers
    # so the TOTAL stays bounded. If n_xdist_workers == PIE_WORKERS, that
    # division is always 1 -- no in-test parallelism left, and the one
    # module with real internal work (test_v1_2_0_invariant.py, a 14-case
    # sweep) becomes a fully-serial long-pole that erases the whole xdist
    # win (measured: 421s at -n 4 + PIE_WORKERS//4=4-wide pools vs 760s
    # serial vs still ~750s at -n 8 + PIE_WORKERS//8=1-wide pools -- same
    # total process budget, very different wall time). max(2, //4) leaves
    # each worker a real pool while still spreading across modules.
    workers = n_arg if n_arg is not None else str(max(2, pie_workers() // 4))
    marker_expr = " or ".join(a for a in args if a != "all")
    cmd = [sys.executable, "-m", "pytest", here, "-m", marker_expr, "-v"]
    if workers not in ("0", "1"):
        # loadscope, not the default `load`: several test modules share a
        # module-scoped ProcessPoolExecutor fixture (test_v1_2_0_invariant,
        # test_mc_wide_parity, test_wide_self_consistency); under plain
        # `load`, xdist distributes their individual parametrized cases
        # across workers, and EACH worker that touches the module reruns
        # the whole fixture -- up to N_workers x duplicate compute.
        # `loadscope` keeps a module's tests on one worker, so the fixture
        # runs once. (Found by running this under -n 8: 8 processes each
        # independently recomputing the same first case.)
        cmd += ["-n", workers, "--dist=loadscope"]
    print("+", " ".join(cmd), f"(xdist -n {workers}, PIE_WORKERS={pie_workers()})")
    import subprocess
    return subprocess.call(cmd, cwd=repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
