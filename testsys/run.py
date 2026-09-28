#!/usr/bin/env python3
"""One-command tiered test runner for PIE.

    /usr/bin/python3 testsys/run.py            # fast tiers (default): unit + contract + integration
    /usr/bin/python3 testsys/run.py unit
    /usr/bin/python3 testsys/run.py contract
    /usr/bin/python3 testsys/run.py integration
    /usr/bin/python3 testsys/run.py e2e        # opt-in: full scheduler.py sweep, minutes
    /usr/bin/python3 testsys/run.py all        # every tier, including e2e

Re-execs itself with PYTHONNOUSERSITE=1 and MPLBACKEND=Agg so the two
conflicting matplotlib installs on this box's default sys.path (see
testsys/conftest.py's module docstring and testsys/README.md
"Findings") can never leak into a subprocess-based (e2e) run the way
conftest.py's in-process sys.path fixup cannot reach. PYTHONNOUSERSITE
only takes effect at interpreter STARTUP, hence the re-exec rather than
just setting os.environ before importing pytest.
"""
import os
import sys

TIERS = {
    "unit": ["-m", "unit"],
    "contract": ["-m", "contract"],
    "integration": ["-m", "integration"],
    "parity": ["-m", "parity"],
    "e2e": ["-m", "e2e"],
}
FAST_DEFAULT = ["unit", "contract", "integration"]


def main():
    args = sys.argv[1:] or FAST_DEFAULT
    if args == ["all"]:
        args = list(TIERS)
    unknown = [a for a in args if a not in TIERS]
    if unknown:
        print(f"unknown tier(s): {unknown}. Known tiers: {sorted(TIERS)} "
              f"(or 'all')", file=sys.stderr)
        return 2

    if os.environ.get("PYTHONNOUSERSITE") != "1":
        env = dict(os.environ)
        env["PYTHONNOUSERSITE"] = "1"
        env.setdefault("MPLBACKEND", "Agg")
        os.execvpe(sys.executable, [sys.executable, __file__, *sys.argv[1:]], env)

    here = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(here)
    marker_expr = " or ".join(a for a in args if a != "all")
    cmd = [sys.executable, "-m", "pytest", here, "-m", marker_expr, "-v"]
    print("+", " ".join(cmd))
    import subprocess
    return subprocess.call(cmd, cwd=repo_root)


if __name__ == "__main__":
    raise SystemExit(main())
