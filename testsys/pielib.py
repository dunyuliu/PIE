"""Shared fixtures/helpers for the PIE test suite (board item 28e/6: moved
out of testsys/conftest.py, which pytest requires to exist for fixture
discovery but which now only re-exports from this module -- see
testsys/conftest.py's own short docstring).

Import order matters here more than in most places, because pie's own
import graph has an environment trap that has nothing to do with the
physics:

pie/globalvar.py reads sys.argv at IMPORT time (argv[1]=code_mode,
argv[2]=CMR2, argv[3]=CMC, argv[4]=light_element, argv[5]=liquidus_eq,
optionally argv[6]=chi_Si_icb). Every other pie module imports globalvar
(directly or via planet_input/libCore), so nothing in pie can be imported
under pytest without a fake argv in place first. `sys_argv_p` below does
this per-test; `import_src` mutates sys.argv itself.

Two traps that used to live here no longer apply:
  - pie/libCore.py's TmFeSmelt.dat load is module-relative, not
    cwd-relative, since board item 28g -- `cwd_src` (still defined below,
    autouse) is kept anyway as a harmless, long-standing invariant (every
    test in this suite has always run with cwd == the package source
    directory) rather than removed as part of an unrelated packaging
    change; nothing currently in this suite depends on it, per a repo-wide
    grep (none of the test files reference cwd/chdir themselves).
  - pie is no longer reached by inserting a bare directory onto
    sys.path: it is installed (`uv pip install -e .`, board item 28e) and
    imported as the real package `pie`/`pie.<module>`, via
    `importlib.import_module`, same as production code (`pie/robust_runner.py`)
    already did for the one place it needs this.

A third trap used to live here (import order, not cwd): pre-pinned-venv,
the dev box's default `/usr/bin/python3` had two conflicting matplotlib
installs on sys.path (apt's python3-matplotlib under
/usr/lib/python3/dist-packages, and a pip --user install under
~/.local/lib/.../site-packages that sorted earlier and paired badly with
apt's mpl_toolkits). That no longer applies: PROJECT_RULES.md rule 3b/3c
requires running this suite under the pinned `.venv-py312` venv, whose own
interpreter has `site.ENABLE_USER_SITE == False` and no apt
dist-packages on sys.path by construction (confirmed via
`.venv-py312/bin/python3.12 -c "import sys, site;
print(site.ENABLE_USER_SITE, sys.path)"`) -- the user-site shadowing this
file used to filter for is impossible by construction once you're on the
required interpreter, so the sys.path filter was removed (2026-10-02,
owner ruling overriding an earlier narrowing). See
testsys/contract/test_gate_runs_in_pinned_venv.py for the test that gates
the claim "the suite actually runs under that interpreter."
"""
import os
import subprocess
import sys
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "pie"  # the installed package's source directory (board item 28e)

os.environ.setdefault("MPLBACKEND", "Agg")

# Defensive default, not a test input: pie/globalvar.py reads sys.argv[1:6]
# at IMPORT time (code_mode, CMR2, CMC, light_element, liquidus_eq). Every
# real test path overwrites sys.argv via _set_argv()/import_src() before
# solving anything. But under pytest-xdist, a ProcessPoolExecutor result
# can get unpickled on the CONTROLLER process's background listener THREAD
# (reconstructing a class instance defined in globalvar/libCore), which
# imports globalvar for the first time in a process whose sys.argv is
# xdist's own launch argv (too short) -- crashing with an unrelated
# IndexError far from any test. Padding here (once, at this module's own
# import -- triggered by testsys/conftest.py's own import of it, before any
# xdist worker or thread can race it) makes that first import succeed no
# matter which thread does it; _set_argv always replaces these values
# before any test-visible solve.
if len(sys.argv) < 6:
    sys.argv[:] = ["main.py", "p", "0.346", "0.424", "S", "Edmund"]


def pie_workers():
    """Single knob for how many OS processes PIE's own tests/tools may run
    at once on a SHARED machine (PROJECT_RULES.md: leave headroom for
    other users' jobs). One env var, `PIE_WORKERS`, drives both pytest-xdist
    (`testsys/run.py -n`) and every in-test `ProcessPoolExecutor` pool --
    never both at once: `pool_workers()` below collapses a pool to 1 when
    already running inside an xdist worker, so parallelism never multiplies
    (xdist workers x pool size).

    Default (unset): max(4, floor(free_cores / 2)), free_cores = nproc - 1 -
    (1-minute load average), capped at 24. Pins to 4 if the load/core
    numbers are unavailable (e.g. inside some CI sandboxes).
    """
    env = os.environ.get("PIE_WORKERS")
    if env:
        return max(1, int(env))
    try:
        cpu = os.cpu_count() or 4
        load1 = os.getloadavg()[0]
        free_cores = max(0, cpu - 1 - load1)
        return min(24, max(4, int(free_cores // 2)))
    except (OSError, AttributeError):
        return 4


def pool_workers(cap):
    """Workers for an in-test ProcessPoolExecutor, capped by `cap` (the
    pool's own prior hard-coded ceiling) and by pie_workers(). Total
    concurrent processes stay bounded at ~pie_workers() machine-wide: this
    DIVIDES the budget across active xdist workers rather than collapsing
    to 1 -- collapsing to 1 was measured to turn one module (a 14-case
    sequential sweep with its own pool, `test_v1_2_0_invariant.py`) into a
    15-minute serial long-pole that ate the whole xdist win (PIE_WORKERS=8,
    -n 8 + --dist=loadscope pins that whole module to ONE worker; a pool of
    1 inside it means its 14 cases run one at a time instead of in
    parallel with each other, same total work, no speedup). Dividing
    instead means that worker still gets a real pool (pie_workers() //
    worker_count, at least 1), while the total across all workers never
    exceeds pie_workers() x 1 pool each at full division -- i.e. the
    multiplication risk this exists to prevent is still bounded, just not
    by brute-force collapse."""
    n_workers = int(os.environ.get("PYTEST_XDIST_WORKER_COUNT", "0") or "0")
    budget = pie_workers() // n_workers if n_workers > 1 else pie_workers()
    return max(1, min(cap, budget))


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


_PIE_RELOAD_MODULES = ("pie.globalvar", "pie.planet_input", "pie.libCore",
                       "pie.solver", "pie.coreEos", "pie.shootp", "pie.driverp")


def _purge_pie_submodules(names=_PIE_RELOAD_MODULES):
    """Delete each `pie.<x>` from `sys.modules` AND from the `pie` package
    object's own `__dict__` -- deleting only `sys.modules` is NOT enough to
    force a real reimport of a package submodule reached via a package-
    relative import elsewhere (`from . import coreEos as eos`, as
    pie/planet_input.py, pie/libCore.py, pie/shootp.py etc. all do): CPython's
    import machinery (`importlib._bootstrap._handle_fromlist`) skips the
    actual import step for a `from package import name` statement whenever
    `name` is ALREADY an attribute of the `package` module object, even if
    it was just removed from `sys.modules` -- it never re-checks
    `sys.modules` in that case. Found while gating board item 28e's PR:
    under the pre-28e bare `src/`-on-sys.path layout there was no parent
    package object to carry such a stale attribute, so `del
    sys.modules[name]` alone was always sufficient there; it silently stops
    being sufficient the moment these modules become real package
    submodules, which is exactly what this packaging change does. Without
    this, `import_src`/`solve_full_model` below can hand back a STALE
    `pie.coreEos` (or similar) whose module-level globals were computed
    under a PREVIOUS test's `sys.argv`/mutated state, or can even leave
    `sys.modules` permanently missing that entry (observed as a `KeyError`
    on `sys.modules["pie.coreEos"]` in
    testsys/unit/test_perf_v1_3_3_gk21_quad.py, once an earlier, unrelated
    test sharing the same xdist worker process had already imported
    `pie.coreEos` once for real)."""
    import pie as _pie
    for full in names:
        sys.modules.pop(full, None)
        short = full.rsplit(".", 1)[-1]
        if short in vars(_pie):
            delattr(_pie, short)


def import_src(modname, CMR2=0.346, CMC=0.424, light_element="S",
                liquidus_eq="Edmund", chi_Si_icb=None):
    """Import (or re-import) a `pie.<modname>` module with a specific argv
    in place. `modname` is the bare submodule name (e.g. "globalvar",
    "shootp"), same as callers used before board item 28e; this now
    imports `pie.<modname>` (the installed package) instead of inserting
    `pie/` onto sys.path and importing the bare name.

    pie/globalvar.py computes several module-level constants (model_path,
    presentDataName, ...) from argv at import time, so a test that needs a
    DIFFERENT CMR2/CMC/light_element than a previously-imported test must
    force re-execution, not reuse the cached module (which would silently
    keep the FIRST test's argv baked into its globals).
    """
    import importlib
    _set_argv("p", CMR2, CMC, light_element, liquidus_eq, chi_Si_icb)
    _purge_pie_submodules()
    return importlib.import_module(f"pie.{modname}")


CONTINUOUS_FIELDS = [
    "rhom", "mass", "moi", "cmc", "Picb", "Tcmb", "chi_li_in", "chi_S_bulk",
    "Pcmb", "chi_li_eut_icb", "chi_li_eut_cmb", "rcmb", "core_mass",
    "chi_li_icb",
]
CATEGORICAL_FIELDS = ["isnow", "isnowcmb", "error_code"]
PROFILE_FIELDS = ["r", "rho", "P", "T", "Tad", "chi_li"]


def solve_full_model(CMR2, CMC, light_element, liquidus_eq, ricb_m,
                      chi_Si_icb=None):
    """One converged Newton+shoot solve at a single inner-core radius,
    computing EVERY quantity driverp.py writes per radius (all 19
    `presentday_columns`, not just the subset that happened to be cheap
    to wire up first) plus the full radial profile arrays (r, rho, P, T,
    Tad, chi_li) -- see src/driverp.py lines ~70-120 for the reference
    computation this mirrors line-for-line (moi/cmc via get_moi/get_ccc,
    chi_li_eut_* via the same Dumberry & Rivoldini 2015 eq.28 formula
    src/driverp.py itself uses).

    Deliberately does NOT go through main.py/driverp.py's file-writing
    loop (no h5/csv/figure I/O, no warm-start dependency on earlier
    radii) -- cold-start Newton from the same generic initial guess
    converges to the same answer regardless of radius (verified:
    matches published/warm-started values to ~1e-6-1e-7 relative,
    the solver's own xtol/ftol), so this is the FAST path to "one
    representative model" rather than paying for every radius before it
    in a sweep. `raises` on non-convergence (SystemExit from
    mynewtonSys's singular-Jacobian guard, or v is None) -- callers that
    are PROBING for which radii converge should catch that, not this
    function silently returning a sentinel.

    Picklable/module-level (not a closure) so it can be dispatched
    across a `concurrent.futures.ProcessPoolExecutor` for the wide,
    many-composition sweeps (testsys/e2e/, the probe scripts under
    testsys/reference/.../generate_*.py) -- each solve is ~15-20 s and
    independent, so wall time for N cases is ~N/nproc, not ~N serial.
    """
    import importlib
    _set_argv("p", CMR2, CMC, light_element, liquidus_eq, chi_Si_icb)
    _purge_pie_submodules()
    gv = importlib.import_module("pie.globalvar")
    planet_input = importlib.import_module("pie.planet_input")
    lc = importlib.import_module("pie.shootp")
    import numpy as np

    param = planet_input.planet("p", CMR2, light_element, liquidus_eq)
    scale = param["scale"]
    rhomean = param["rhomean"]
    rhocr, rh, rm = param["rhocr"], param["rh"], param["rm"]
    ricb_nd = ricb_m / scale["a"]

    v = lc.mynewtonSys(
        "J_mercmodel", param["v0"],
        [ricb_nd, rhocr, rh, param, scale],
        xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit, verbose=False,
    )
    if v is None:
        raise RuntimeError(
            f"Newton solve did not converge: CMR2={CMR2} CMC={CMC} "
            f"light={light_element} liquidus={liquidus_eq} ricb_m={ricb_m}")
    f, r, yy, fout, err = lc.shoot_mercmodel(v, ricb_nd, rhocr, rh, param, scale)

    r_phys = scale["a"] * r
    P_phys = scale["P"] * yy[0]
    g_phys = scale["ga"] * yy[1]
    T_phys = scale["T"] * yy[2]
    Tad_phys = scale["T"] * yy[3]
    rho_phys = rhomean * yy[4]
    chi_li = yy[5]

    rhom = v[3] * rhomean
    chi_li_icb = v[4]
    rcmb = v[2] * scale["a"]

    r_2 = np.append(r_phys, [rh * scale["a"], rm])
    rho_2 = np.append(rho_phys, [rhom, rhocr])
    moi = lc.get_moi(r_2, rho_2, rhomean)
    ccc = lc.get_ccc(r_2, rho_2, rhomean)
    cmc = 1 - ccc / moi
    mass = lc.get_mass_norm(r_2, rho_2, rhomean)
    core_mass = lc.get_mass_core(r_phys, rho_phys)

    Picb, Tcmb, isnow, isnowcmb, chi_li_in, gradTa, chi_S_bulk = fout
    Pcmb = P_phys[-1]
    chi_li_eut_icb = 0.11 + 0.187 * np.exp(-0.065 * Picb * 1e-9)
    chi_li_eut_cmb = 0.11 + 0.187 * np.exp(-0.065 * Pcmb * 1e-9)

    # error_code: derived from THIS solve's own status, mirroring
    # src/driverp.py's per-radius classification line-for-line (same
    # ErrorCode table, item 16) -- NOT a hard-coded 0.0. driverp.py's
    # sweep applies these three checks in this exact order, each later
    # one overwriting the previous: (1) the `err` flag shoot_mercmodel
    # returns (negative chi_li_icb at the trial root) ->
    # CHI_OUTSIDE_ADMISSIBLE_BOX; (2) the solved rcmb must lie strictly
    # outside the requested ricb -> RICB_GE_RCMB; (3) a negative value
    # ANYWHERE in the converged chi_li profile -> CHI_OUTSIDE_ADMISSIBLE_BOX
    # (final, highest priority, same as driverp.py's closing check).
    # A genuinely admissible, physically-valid converged solve still
    # gets CONVERGED (0) here, same as before this fix -- so every
    # existing admissible-case comparison against published/golden data
    # (which predates item 16's error codes and is also implicitly 0 in
    # that case) is unaffected; only the previously-impossible non-zero
    # path is now reachable.
    error_code = gv.ErrorCode.CONVERGED
    if err:
        error_code = gv.ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX
    if ricb_m >= rcmb:
        error_code = gv.ErrorCode.RICB_GE_RCMB
    if (chi_li < 0).any():
        error_code = gv.ErrorCode.CHI_OUTSIDE_ADMISSIBLE_BOX

    return {
        "CMR2": CMR2, "CMC": CMC, "light_element": light_element,
        "liquidus_eq": liquidus_eq, "ricb_m": ricb_m,
        "chi_Si_icb": chi_Si_icb if chi_Si_icb is not None else 0.0,
        # v1.3.0 additions (not compared against published references):
        # the converged unknown vector and the residual norm at it, for
        # assert_recovered_model_valid.
        "v": [float(x) for x in v], "resid_norm": float(np.linalg.norm(f)),
        "err_flag": bool(err),
        "normf_last": float(lc.last_solve_info.get("normf_last", float("nan"))),
        "normdx_last": float(lc.last_solve_info.get("normdx_last", float("nan"))),
        "xtol": float(gv.xtol),
        "max_Si": float(gv.max_Si_Steinbruegge2020 if liquidus_eq == "Steinbruegge" else gv.max_Si_Edmund2022),
        "ftol": float(gv.ftol),
        "scalars": {
            "rhom": float(rhom), "mass": float(mass), "moi": float(moi),
            "cmc": float(cmc), "Picb": float(Picb), "Tcmb": float(Tcmb),
            "isnow": float(isnow), "isnowcmb": float(isnowcmb),
            "chi_li_in": float(chi_li_in), "chi_S_bulk": float(chi_S_bulk),
            "Pcmb": float(Pcmb), "chi_li_eut_icb": float(chi_li_eut_icb),
            "chi_li_eut_cmb": float(chi_li_eut_cmb), "ricb": float(r_phys[0]),
            "rcmb": float(rcmb), "core_mass": float(core_mass),
            "chi_li_icb": float(chi_li_icb), "error_code": float(int(error_code)),
        },
        "profiles": {
            "r": r_phys.tolist(), "rho": rho_phys.tolist(),
            "P": P_phys.tolist(), "T": T_phys.tolist(),
            "Tad": Tad_phys.tolist(), "g": g_phys.tolist(),
            "chi_li": chi_li.tolist(),
        },
    }


def assert_scalars_match(computed, reference, rtol=1e-4, context="",
                          check_error_code=True):
    """Compare a `solve_full_model()`-shaped `scalars` dict against a
    reference dict with the same keys. Categorical fields (isnow,
    isnowcmb, error_code) compared for EXACT equality -- they are
    discrete classification labels, not continuous quantities.
    `not (diff > bound)`, never `diff <= bound`: a NaN diff must FAIL,
    not silently pass a comparison NaN always evaluates False for.

    `check_error_code=False`: `error_code` is derived from THIS solve's
    own status (PATHWAY_FORWARD.md item 23a, `solve_full_model` in this
    file) -- a reference generated/published BEFORE item 16 added error
    codes cannot carry a real one and always reads 0 regardless of
    whether that row is actually admissible, so comparing it against
    such a reference is comparing a real classification against a
    field the reference literally cannot represent, not a regression
    check. Callers against a pre-item-16 reference (e.g.
    test_mc_wide_parity.py's published Zenodo rows) pass this False and
    say so; every other caller (a reference this repo generated WITH
    the current error-code logic) keeps the default and gets the exact
    check."""
    for field in CATEGORICAL_FIELDS:
        if field == "error_code" and not check_error_code:
            continue
        c, r = computed[field], reference[field]
        assert c == pytest.approx(r, abs=1e-9), (
            f"{context}{field}: categorical field must match EXACTLY "
            f"(computed={c!r}, reference={r!r})"
        )
    for field in CONTINUOUS_FIELDS:
        c, r = computed[field], reference[field]
        diff = abs(c - r)
        # Absolute floor is the Newton solver's OWN xtol=ftol=1e-6
        # (globalvar.py), not an arbitrary loosening: fields that sit
        # near zero (e.g. chi_li_in right at the ICB, where it starts
        # at ~0) have relative bounds far tighter than the solver's own
        # convergence tolerance, which manufactures false failures on
        # noise the solver itself considers "converged". Confirmed by a
        # real case: chi_li_in=-1.358e-4 vs -1.358e-4, diff=2.5e-8,
        # rtol=1e-4-of-that-tiny-value = 1.4e-8 (tighter than the
        # solver's own tolerance) -- a 1e-6 floor covers it without
        # loosening the bound for any O(1)-or-larger quantity (core_mass
        # ~1e23, moi~0.3, etc. are governed by rtol either way).
        bound = max(rtol * abs(r), 1e-6)
        assert not (diff > bound), (
            f"{context}{field}: computed={c!r} reference={r!r} "
            f"diff={diff!r} exceeds rtol={rtol}"
        )


DISCONTINUOUS_PROFILE_FIELDS = ("rho", "chi_li")


def assert_profiles_match(computed, reference, rtol=1e-3, atol=1e-6,
                           context="", interpolate=False, boundary_slop=1):
    """Compare full radial profile arrays. `interpolate=True` (for
    cross-environment/published comparisons, where adaptive-step solver
    node placement can differ between scipy/BLAS versions) resamples
    the REFERENCE profile onto the computed run's own radius grid via
    linear interpolation before comparing, rather than requiring
    identical array lengths. `interpolate=False` (same-machine
    self-golden, deterministic solve_ivp/RK4 grid) requires exact shape
    match -- a length mismatch there is itself a regression, not
    something to paper over with resampling.

    `boundary_slop`: rho and chi_li are PHYSICALLY DISCONTINUOUS at the
    solid/liquid inner-core boundary (density jumps at freezing; chi_li
    is 0 throughout the solid inner core, non-zero from the ICB
    outward -- see src/shootp.py's `chi = np.concatenate((np.zeros(ns),
    chi_li))`). When `interpolate=True` and the two runs' solid-branch
    adaptive-solver node counts differ by even one point, linearly
    interpolating STRAIGHT ACROSS that jump manufactures a large
    "difference" at the one point nearest the boundary that is an
    artifact of resampling across a discontinuity, not a real
    divergence -- confirmed by inspection (this repo's own solve vs the
    published h5, ns=20/nc=51/71 total points, worst diff exactly at
    index 19 == the ICB). `boundary_slop` allows up to that many
    points to exceed tolerance, ONLY for `rho`/`chi_li`, ONLY when
    interpolating -- every other field, and every point outside that
    slop, is still a zero-tolerance regression.
    """
    import numpy as np
    r_c = np.asarray(computed["r"])
    r_r = np.asarray(reference["r"])
    if not interpolate:
        assert r_c.shape == r_r.shape, (
            f"{context}profile grid size changed: computed {r_c.shape} vs "
            f"reference {r_r.shape} -- regenerate the self-golden "
            f"deliberately if this is expected, don't silently resample"
        )
    for field in PROFILE_FIELDS:
        if field == "r" or field not in reference:
            continue
        c = np.asarray(computed[field])
        if interpolate:
            r = np.interp(r_c, r_r, np.asarray(reference[field]))
        else:
            r = np.asarray(reference[field])
        diff = np.abs(c - r)
        bound = rtol * np.maximum(np.abs(r), 1.0) + atol
        bad = diff > bound
        n_bad = int(bad.sum())
        allowed = boundary_slop if (interpolate and field in DISCONTINUOUS_PROFILE_FIELDS) else 0
        assert n_bad <= allowed, (
            f"{context}profile field '{field}': {n_bad}/{len(c)} points "
            f"exceed rtol={rtol}/atol={atol} (allowed={allowed} boundary "
            f"slop); worst diff={diff.max():.4g} at index {int(np.argmax(diff))}"
        )


def run_pie(*args, cwd, timeout=600, env_extra=None):
    """Run a src/*.py entry point as a real subprocess. PYTHONNOUSERSITE=1
    is kept here out of caution (not re-audited as part of the 2026-10-02
    filter removal -- see module docstring -- since this call spawns a
    NEW interpreter via `sys.executable` rather than reusing the
    already-isolated in-process one; whether that subprocess still needs
    it under the pinned venv is an open question, flagged to the project
    owner rather than decided here). MPLBACKEND=Agg so no test needs a
    display."""
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


def solver_converged(result):
    """mynewtonSys's own stop rule, unchanged since v1.0.5: return x when
    |f| < ftol OR |dx| < xtol at the current iterate. A row accepted on the
    |dx| criterion can carry |f| above ftol (observed: 6.8e-5 with ftol
    1e-6); it is a converged row by the solver's definition, so validity
    checks use that definition, not a re-invented one (rule 5)."""
    return (result["resid_norm"] < 10 * result["ftol"]) or (result["normdx_last"] < result["xtol"])


def is_admissible(result):
    """True when a converged solve is inside the admissible box driverp.py
    writes with error_code 0: chi_li_icb in [0, eutectic at P_icb] (S, S+Si)
    or [0, liquidus Si max] (Si) and no negative-chi err flag from the shoot.
    A converged solve outside it is what driverp.py records with
    error_code 4 -- the class 21.8% of the published converged rows belong
    to (chi_li_icb < 0). `scalars["error_code"]` in solve_full_model is
    derived from this solve's own status (PATHWAY_FORWARD.md item 23a) and
    will itself read 4 for such a row; published reference csvs predate the
    restored err flag and always carry error_code 0 regardless, so compare
    admissibility with this function, not a raw equality against a
    reference row's error_code field."""
    s = result["scalars"]
    chi_max = result["max_Si"] if result["light_element"] == "Si" else s["chi_li_eut_icb"]
    return (0.0 <= s["chi_li_icb"] <= chi_max) and not result.get("err_flag", False)


def check_converged_without_reference(result, context=""):
    """Gate for a solve that converged where the reference (published run /
    pre-v1.3.0 golden / v1.2.0) did not. Returns 'recovered' after the full
    validity gate when the model is admissible, or 'inadmissible' (finite,
    converged, but chi_li_icb outside [0, bound] -> error_code 4 in the
    csv) -- recorded, never a hard failure, never counted as recovered."""
    if is_admissible(result):
        assert_recovered_model_valid(result, context=context)
        return "recovered"
    import numpy as np
    assert solver_converged(result), f"{context}inadmissible solve is not even converged (|f|={result['resid_norm']:.2e}, |dx|={result['normdx_last']:.2e})"
    assert np.all(np.isfinite(result["v"])), f"{context}non-finite v"
    return "inadmissible"


def assert_recovered_model_valid(result, context=""):
    """Validity gate for a model that CONVERGES in the current code but has
    no reference (absent from the published data / a pre-v1.3.0 golden /
    v1.2.0): the line-search solver of v1.3.0 (PATHWAY_FORWARD.md item 17)
    recovers such models by design, so "it converged where the reference
    did not" is no longer a failure -- but the recovered model must be a
    physically admissible root, not a solver artefact. Checks (owner
    decision 2026-09-30): residual below the solver tolerance; chi_li_icb
    in [0, eutectic at P_icb] (S, S+Si) or in [0, liquidus Si max] (Si);
    ricb < rcmb; rho > 0 everywhere; finite profiles; error_code == 0.
    Smoothness in ricb is a sweep property, gated in
    testsys/integration/test_v1_2_0_invariant.py.
    """
    import numpy as np
    s = result["scalars"]
    assert solver_converged(result), (
        f"{context}recovered model not converged by the solver's own rule: "
        f"resid_norm={result['resid_norm']:.3e} (ftol {result['ftol']}), |dx|={result['normdx_last']:.3e} (xtol {result['xtol']})")
    chi = s["chi_li_icb"]
    chi_max = result["max_Si"] if result["light_element"] == "Si" else s["chi_li_eut_icb"]
    assert 0.0 <= chi <= chi_max, f"{context}recovered chi_li_icb={chi} outside [0, {chi_max}]"
    assert s["ricb"] < s["rcmb"], f"{context}recovered ricb={s['ricb']} >= rcmb={s['rcmb']}"
    rho = np.asarray(result["profiles"]["rho"])
    assert np.all(rho > 0), f"{context}recovered model has non-positive density"
    for k, prof in result["profiles"].items():
        assert np.all(np.isfinite(prof)), f"{context}recovered profile {k} has non-finite values"
    assert not result.get("err_flag", False), f"{context}recovered model raised the negative-chi err flag (error_code 4)"
