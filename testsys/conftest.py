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
    for name in list(sys.modules):
        if name in ("globalvar", "planet_input", "libCore", "solver",
                     "coreEos", "shootp", "driverp"):
            del sys.modules[name]
    gv = importlib.import_module("globalvar")
    planet_input = importlib.import_module("planet_input")
    lc = importlib.import_module("shootp")
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

    return {
        "CMR2": CMR2, "CMC": CMC, "light_element": light_element,
        "liquidus_eq": liquidus_eq, "ricb_m": ricb_m,
        "chi_Si_icb": chi_Si_icb if chi_Si_icb is not None else 0.0,
        # v1.3.0 additions (not compared against published references):
        # the converged unknown vector and the residual norm at it, for
        # assert_recovered_model_valid.
        "v": [float(x) for x in v], "resid_norm": float(np.linalg.norm(f)),
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
            "chi_li_icb": float(chi_li_icb), "error_code": 0.0,
        },
        "profiles": {
            "r": r_phys.tolist(), "rho": rho_phys.tolist(),
            "P": P_phys.tolist(), "T": T_phys.tolist(),
            "Tad": Tad_phys.tolist(), "g": g_phys.tolist(),
            "chi_li": chi_li.tolist(),
        },
    }


def assert_scalars_match(computed, reference, rtol=1e-4, context=""):
    """Compare a `solve_full_model()`-shaped `scalars` dict against a
    reference dict with the same keys. Categorical fields (isnow,
    isnowcmb, error_code) compared for EXACT equality -- they are
    discrete classification labels, not continuous quantities.
    `not (diff > bound)`, never `diff <= bound`: a NaN diff must FAIL,
    not silently pass a comparison NaN always evaluates False for."""
    for field in CATEGORICAL_FIELDS:
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
    assert result["resid_norm"] < 10 * result["ftol"], (
        f"{context}recovered model residual {result['resid_norm']:.3e} not below solver tolerance")
    chi = s["chi_li_icb"]
    chi_max = result["max_Si"] if result["light_element"] == "Si" else s["chi_li_eut_icb"]
    assert 0.0 <= chi <= chi_max, f"{context}recovered chi_li_icb={chi} outside [0, {chi_max}]"
    assert s["ricb"] < s["rcmb"], f"{context}recovered ricb={s['ricb']} >= rcmb={s['rcmb']}"
    rho = np.asarray(result["profiles"]["rho"])
    assert np.all(rho > 0), f"{context}recovered model has non-positive density"
    for k, prof in result["profiles"].items():
        assert np.all(np.isfinite(prof)), f"{context}recovered profile {k} has non-finite values"
    assert s["error_code"] == 0, f"{context}recovered model carries error_code {s['error_code']}"
