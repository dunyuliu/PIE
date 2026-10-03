#!/usr/bin/env python3
"""Regenerate testsys/reference/perf_v1.3.3/real_quad_calls.npz: real
(a, b, T) triples actually passed to `integrate.quad(lambda x:
self.volume(x,T), a, b)` inside eosAndersonGrueneisen.Gibbs during real
Newton+shoot solves (monkeypatching Gibbs to record its quad call's
full_output=1 infodict -- a, b, T, and QUADPACK's own `neval`/`last` for
that call -- without changing control flow), across the verification
matrix in the v1.3.3 perf brief: S/Si/S+Si x Edmund/Steinbruegge x a
small-ricb (10 m) and the canonical Margot-fit radius (500010 m).

A near-rcmb radius (1,800,000 m, ~92% of rcmb at this CMR2/CMC) was
attempted for every composition and did NOT converge for any of them
(SolverError: CHI_OUTSIDE_ADMISSIBLE_BOX / NONFINITE_SHOOT) -- this is a
pre-existing Newton-solver boundary limitation at CMR2=0.346/CMC=0.424,
unrelated to quad/GK21, and is NOT part of this perf port's scope to fix.
Si/Edmund failed to converge at EVERY radius tried (10 m, 500010 m,
1800000 m) for the same reason -- also pre-existing, also out of scope.
See docs/notes/perf_v1.3.3.md for how the near-rcmb / high-pressure gap in
this matrix was closed instead: a DIRECT (non-solver) sweep of
eos.Gibbs/quad over the full admissible pressure domain, which is what
shows the single-panel claim does NOT hold universally (and why
coreEos._gk21_or_quad's per-call fallback is mandatory, not optional).

Regenerate with:

    PYTHONNOUSERSITE=1 MPLBACKEND=Agg PYTHONWARNINGS=ignore \
        .venv/bin/python3 \
        testsys/reference/perf_v1.3.3/generate_real_quad_calls.py

(run from the repo root; edit ROOT below if your checkout differs).

Only a' + b/T triples are kept (not every intermediate v/profile array) --
all this fixture needs to prove is: (1) QUADPACK's `last` is 1 (no
subdivision) for every real call in the matrix, and (2) replaying each
(a, b, T) through both scipy.integrate.quad and coreEos._gk21_or_quad
(with the actual eos object's `volume` method) gives bit-identical
results. The fixture is downsampled (stratified random sample, fixed
seed) from the full captured set (237057 real calls) to keep the
committed file small; the full-set check (all 237057, every one bit-
identical, max diff 0.0) is recorded in docs/notes/perf_v1.3.3.md, not
re-run by the test suite every CI run.
"""
import contextlib
import importlib
import io
import os
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
OUT = pathlib.Path(__file__).resolve().parent / "real_quad_calls.npz"

# `pie` is an installed package (board item 28e, `uv pip install -e .`),
# not a bare `src/`-on-sys.path directory -- no sys.path insert needed,
# imported below as `pie.<module>` via importlib, same as testsys/pielib.py.
os.environ.setdefault("MPLBACKEND", "Agg")


def _set_argv(CMR2, CMC, light, liq, chi=None):
    argv = ["main.py", "p", str(CMR2), str(CMC), light, liq]
    if chi is not None:
        argv.append(str(chi))
    sys.argv[:] = argv


def _fresh(*names):
    """Force a real reimport of each `pie.<name>` submodule. Deleting only
    sys.modules is not enough once these are real package submodules
    reached via package-relative imports elsewhere (`from . import X`) --
    CPython skips the reimport if `name` is already an attribute of the
    `pie` package object. Same fix as testsys/pielib.py's
    `_purge_pie_submodules` (board item 28e), duplicated here rather than
    imported so this standalone regen script has no pytest dependency."""
    import pie as _pie_pkg
    for name in names:
        sys.modules.pop(f"pie.{name}", None)
        _pie_pkg.__dict__.pop(name, None)


CASES = [
    # (CMR2, CMC, light_element, liquidus_eq, chi_Si_icb)
    (0.346, 0.424, "S", "Edmund", None),
    (0.346, 0.424, "S", "Steinbruegge", None),
    (0.346, 0.424, "Si", "Edmund", None),
    (0.346, 0.424, "Si", "Steinbruegge", None),
    (0.346, 0.424, "S+Si", "Edmund", 0.05),
    (0.346, 0.424, "S+Si", "Steinbruegge", 0.05),
]
RADII_M = [10.0, 500010.0, 1800000.0]


def main():
    from scipy import integrate

    all_a, all_b, all_T, all_neval, all_last = [], [], [], [], []
    case_labels = []

    for CMR2, CMC, light, liq, chi in CASES:
        for ricb in RADII_M:
            _set_argv(CMR2, CMC, light, liq, chi)
            _fresh("globalvar", "planet_input", "libCore", "solver",
                   "coreEos", "shootp", "driverp")
            gv = importlib.import_module("pie.globalvar")
            planet_input = importlib.import_module("pie.planet_input")
            shootp = importlib.import_module("pie.shootp")
            coreEos = importlib.import_module("pie.coreEos")

            param = planet_input.planet("p", CMR2, light, liq)
            scale = param["scale"]
            rhocr, rh = param["rhocr"], param["rh"]
            ricb_nd = ricb / scale["a"]

            calls = []
            orig_Gibbs = coreEos.eosAndersonGrueneisen.Gibbs

            def patched_Gibbs(self, p, T, _orig=orig_Gibbs, _calls=calls):
                if p > self.p0:
                    a = self.p0 / self.pMax
                    b = p / self.pMax
                    _, _, info = integrate.quad(
                        lambda x: self.volume(x, T), a, b, full_output=1
                    )[:3]
                    _calls.append((a, b, T, info["neval"], info["last"]))
                return _orig(self, p, T)

            coreEos.eosAndersonGrueneisen.Gibbs = patched_Gibbs
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    v = shootp.mynewtonSys(
                        "J_mercmodel", param["v0"],
                        [ricb_nd, rhocr, rh, param, scale],
                        xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit,
                        verbose=False,
                    )
            except BaseException as e:
                print(f"NOCONV {light}/{liq} chi={chi} ricb={ricb}: {e!r}")
                continue
            finally:
                coreEos.eosAndersonGrueneisen.Gibbs = orig_Gibbs

            if v is None:
                print(f"NOCONV {light}/{liq} chi={chi} ricb={ricb}: v is None")
                continue

            print(f"case {light}/{liq} chi={chi} ricb={ricb}: "
                  f"{len(calls)} quad calls")
            label = f"{light}|{liq}|{chi}|{ricb}"
            for a, b, T, neval, last in calls:
                all_a.append(a); all_b.append(b); all_T.append(T)
                all_neval.append(neval); all_last.append(last)
                case_labels.append(label)

    all_a = np.array(all_a); all_b = np.array(all_b); all_T = np.array(all_T)
    all_neval = np.array(all_neval); all_last = np.array(all_last)
    print(f"total real quad calls captured: {len(all_a)}")
    print(f"distinct 'last' values: {sorted(set(all_last.tolist()))}")
    print(f"distinct neval values: {sorted(set(all_neval.tolist()))}")
    assert set(all_last.tolist()) == {1}, (
        "single-panel claim does NOT hold for one of these real calls -- "
        "stop, do not downsample/commit, diagnose before building the "
        "GK21 fast path any further"
    )

    rng = np.random.default_rng(1234567)
    n_keep = min(2000, len(all_a))
    keep = rng.choice(len(all_a), size=n_keep, replace=False)
    keep.sort()

    np.savez(
        OUT,
        a=all_a[keep], b=all_b[keep], T=all_T[keep],
        neval=all_neval[keep], last=all_last[keep],
        case_label=np.array(case_labels)[keep],
        n_total_captured=len(all_a),
    )
    print(f"wrote {OUT} ({n_keep} of {len(all_a)} real calls, stratified "
          f"by random sample, fixed seed)")


if __name__ == "__main__":
    main()
