"""Shared fixtures/helpers for the PIE test suite.

Import order matters here more than in most conftests, because src/'s own
import graph has two environment traps that have nothing to do with the
physics:

1. src/globalvar.py reads sys.argv at IMPORT time (argv[1]=code_mode,
   argv[2]=CMR2, argv[3]=CMC, argv[4]=light_element, argv[5]=liquidus_eq,
   optionally argv[6]=chi_Si_icb). Every other src module imports globalvar
   (directly or via planet_input/libCore), so nothing in src/ can be
   imported under pytest without a fake argv in place first. `sys_argv_p`
   below does this per-test; `import_src` mutates sys.argv itself.
2. src/libCore.py does `TmFeS = eos.meltingDataFromFile("TmFeSmelt.dat")`
   at import time, a path relative to the CURRENT WORKING DIRECTORY, not to
   the module file. Every test that imports libCore (or anything that
   imports libCore: solver, shootp, driverp, planet_input) must run with
   cwd == src/, which `cwd_src` (autouse) guarantees.

Neither of these is something a test file should have to know about --
that would be testing the loader, not the physics. They live here once.

There's a third trap this file removes only for ITSELF (import order, not
cwd): the dev box has two matplotlib installs on /usr/bin/python3's default
sys.path -- apt's python3-matplotlib 3.5.1 under
/usr/lib/python3/dist-packages, and a pip --user install of matplotlib
3.9.2 under ~/.local/lib/.../site-packages, which sorts EARLIER. `import
matplotlib` picks the pip one; `from mpl_toolkits.mplot3d import Axes3D`
(used unconditionally by src/visualization_present.py and
src/TEST_visualization_evolution.py, and so transitively by driverp.py,
shootp.py's caller chain, and main.py's `from drivere import *`) resolves
mpl_toolkits from the OTHER (apt) install, and that pairing is broken:
apt's mpl_toolkits.mplot3d.axes3d imports `docstring` from matplotlib,
which 3.9.2 removed years ago. Net effect: ANY import of driverp, shootp's
callers, or main.py raises ImportError, unconditionally, regardless of
code_mode -- this is a real project bug, reported in testsys/README.md
under "Findings", not fixed here (constraint: no src/ edits). Dropping the
'.local' entries from sys.path before src is ever imported makes both
mpl_toolkits and matplotlib resolve from the SAME (apt) install, which is
self-consistent, and is a test-harness-only decision (sys.path, not
src/). `testsys/run.py` does the equivalent for subprocess (e2e) runs via
PYTHONNOUSERSITE=1.
"""
import os
import subprocess
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

sys.path[:] = [p for p in sys.path if "/.local/" not in p]
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("MPLBACKEND", "Agg")


def _set_argv(code_mode, CMR2, CMC, light_element, liquidus_eq, chi_Si_icb=None):
    argv = ["main.py", code_mode, str(CMR2), str(CMC), light_element, liquidus_eq]
    if chi_Si_icb is not None:
        argv.append(str(chi_Si_icb))
    sys.argv[:] = argv


@pytest.fixture
def sys_argv_p(monkeypatch):
    """Set a valid present-day-mode argv (code_mode='p') before a test
    imports any src module. Yields the setter so a test can call it again
    with different CMR2/CMC/light_element before a fresh `import_src`."""
    def _apply(CMR2=0.346, CMC=0.424, light_element="S", liquidus_eq="Edmund",
               chi_Si_icb=None):
        _set_argv("p", CMR2, CMC, light_element, liquidus_eq, chi_Si_icb)
    _apply()
    yield _apply


@pytest.fixture(autouse=True, scope="session")
def cwd_src(monkeypatch_session):
    """libCore.py's meltingDataFromFile("TmFeSmelt.dat") load is relative to
    cwd, not to the module file -- every test needs cwd == src/.

    Session-scoped (not the usual function-scoped `monkeypatch.chdir`):
    module-scoped fixtures elsewhere (e.g. the shared solved-model
    fixture in testsys/integration/) run BEFORE any function-scoped
    autouse fixture of their module's first test, so a function-scoped
    chdir would be too late for them. No test in this suite needs a
    different cwd, so one process-wide chdir for the whole session is
    correct, not just convenient."""
    monkeypatch_session.chdir(SRC)


@pytest.fixture(scope="session")
def monkeypatch_session():
    # pytest's built-in `monkeypatch` fixture is function-scoped by
    # design (undo timing); this is the standard workaround for needing
    # the same undo-on-teardown behaviour at session scope.
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


def import_src(modname, CMR2=0.346, CMC=0.424, light_element="S",
                liquidus_eq="Edmund", chi_Si_icb=None):
    """Import (or re-import) a src/ module with a specific argv in place.

    src/globalvar.py computes several module-level constants (model_path,
    presentDataName, ...) from argv at import time, so a test that needs a
    DIFFERENT CMR2/CMC/light_element than a previously-imported test must
    force re-execution, not reuse the cached module (which would silently
    keep the FIRST test's argv baked into its globals).
    """
    import importlib
    _set_argv("p", CMR2, CMC, light_element, liquidus_eq, chi_Si_icb)
    for name in list(sys.modules):
        if name in ("globalvar", "planet_input", "libCore", "solver",
                     "coreEos", "shootp", "driverp"):
            del sys.modules[name]
    return importlib.import_module(modname)


@pytest.fixture
def margot_param(sys_argv_p):
    """A real `param` dict for CMR2=0.346, CMC=0.424, light_element='S',
    liquidus_eq='Edmund' -- the Margot present-day case named in the task
    brief. Session-scoped would be nice, but planet_input.planet() is cheap
    (no solve, just EOS object construction), so function-scope keeps each
    test's argv isolated with no measurable cost."""
    planet_input = import_src("planet_input", CMR2=0.346, CMC=0.424,
                               light_element="S", liquidus_eq="Edmund")
    return planet_input.planet("p", 0.346, 0.424, "S", "Edmund")


def run_pie(*args, cwd, timeout=600, env_extra=None):
    """Run a src/*.py entry point as a real subprocess: PYTHONNOUSERSITE=1
    so the two-matplotlib-installs conflict (see module docstring) can't
    reappear via a different sys.path assembly than the in-process
    workaround above, MPLBACKEND=Agg so no test needs a display."""
    env = dict(os.environ)
    env["PYTHONNOUSERSITE"] = "1"
    env["MPLBACKEND"] = "Agg"
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd, env=env, timeout=timeout,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
