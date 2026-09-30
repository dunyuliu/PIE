#!/usr/bin/env python3
"""Fixed-sample radius sweeps for testsys/integration/test_v1_2_0_invariant.py
and for the v1.3.0 recovery measurements (docs/notes/solver_v1.3.0.md).

    /usr/bin/python3 generate_sweeps.py --src /path/to/src --out sweeps.json
                     [--policy stop|continue] [--adaptive] [--extra-radii N] [--workers 8] [--partial-dir DIR]

Replicates src/driverp.py's radius loop (same grid, same warm start) WITHOUT
csv/h5/figure I/O and records per radius the unknown vector v (full repr),
residual f, fout, error code, which start converged, Newton iterations and
the final residual norm, so two versions of src/ can be compared row by row.

Policies
  stop      v1.2.0 behaviour: the first failure ends the sweep (used to
            generate the committed v1_2_0_sweeps.json from src/ at 18cf78a).
  continue  v1.3.0 behaviour: a failed radius is recorded and the sweep goes
            on, warm-starting from the last converged solution, with one
            cold start from the generic v0 if the warm start fails -- via
            src/driverp.py's solve_radius, so the harness cannot drift from
            the shipped policy. Default when the src has solve_radius.
  --adaptive  measurement only (never shipped): on the first two failures
            of a sweep, try an adaptive continuation from the last converged
            solution (radius step halved 25, 12.5, ... down to ~1.5 km, the
            output grid unchanged) and record whether it recovers the failed
            radius. The result is NOT fed back into the sweep.
  --extra-radii N  cap each case at (rows in the committed v1.2.0 fixture
            + N) radii instead of the case's max_ricb_m (keeps the
            integration-tier test bounded).

The committed fixture `v1_2_0_sweeps.json` was generated from src/ at v1.2.0
(git 18cf78a) on the pinned environment (numpy 1.21.5, scipy 1.8.0,
/usr/bin/python3 3.10.12); its header records that provenance.
PYTHONDONTWRITEBYTECODE is set so importing a read-only checkout writes
nothing into it.
"""
import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent

_CHILD = r'''
import sys, os, json, time, io, contextlib
src = sys.argv[1]; case = json.loads(sys.argv[2]); policy = sys.argv[3]; adaptive = sys.argv[4] == "1"
sys.path[:] = [p for p in sys.path if "/.local/" not in p]
sys.path.insert(0, src); os.chdir(src)
sys.argv[:] = ["main.py", "p", repr(case["CMR2"]), repr(case["CMC"]), case["light"], case["liquidus"], repr(case["chi_Si_icb"])]
import numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    import globalvar as gv, planet_input, shootp as lc
    driverp = None
    if policy == "continue":
        import driverp
    param = planet_input.planet("p", case["CMR2"], case["light"], case["liquidus"])
scale = param["scale"]; rhocr, rh = param["rhocr"], param["rh"]
rs = np.arange(1e1, 2e6, gv.dr); rs = rs[rs <= case["max_ricb_m"]]
if case.get("max_rows"): rs = rs[:case["max_rows"]]
SolverError = getattr(lc, "SolverError", SystemExit)
EC = getattr(gv, "ErrorCode", None)
si_max = gv.max_Si_Steinbruegge2020 if case["liquidus"] == "Steinbruegge" else gv.max_Si_Edmund2022
v_cold = list(param["v0"]); v_last = None; last_r = None; rows = []; n_adaptive = 0

def newton(v0, ricb, start):
    kw = {}
    if "log_path" in lc.mynewtonSys.__code__.co_varnames: kw["log_path"] = None
    with contextlib.redirect_stdout(io.StringIO()):
        return lc.mynewtonSys("J_mercmodel", v0, [ricb, rhocr, rh, param, scale], xtol=gv.xtol, ftol=gv.ftol, maxit=gv.maxit, verbose=False, **kw)

def adaptive_continuation(r_prev, v_prev, r_target):
    """report-only: halve the radius step from the last converged solution."""
    step = 25e3; r = r_prev; v = list(v_prev); n = 0; min_step = step
    while r < r_target - 1.0:
        tgt = min(r + step, r_target); n += 1
        try:
            v = newton(v, tgt / scale["a"], "adaptive"); r = tgt
        except BaseException:
            step *= 0.5; min_step = min(min_step, step)
            if step < 1.5e3:
                return dict(tried=True, recovered=False, n_solves=n, min_step_km=min_step / 1e3)
    return dict(tried=True, recovered=True, n_solves=n, min_step_km=min_step / 1e3, v=[float(x) for x in v])

for k, r in enumerate(rs):
    ricb = r / scale["a"]; t0 = time.time()
    row = {"k": k, "ricb_m": float(r)}
    try:
        if policy == "continue" and driverp is not None and hasattr(driverp, "solve_radius"):
            with contextlib.redirect_stdout(io.StringIO()):
                v, start = driverp.solve_radius(k, r, ricb, v_last, v_cold, rhocr, rh, param, scale, None)
        else:
            v0 = v_last if v_last is not None else v_cold
            v = newton(v0, ricb, "warm" if v_last is not None else "cold"); start = "warm" if v_last is not None else "cold"
        info = dict(getattr(lc, "last_solve_info", {}))
        with contextlib.redirect_stdout(io.StringIO()):
            f, rr, yy, fout, err = lc.shoot_mercmodel(v, ricb, rhocr, rh, param, scale)
        row.update(status="ok", error_code=0, start=start, newton_iters=info.get("n_iterations"),
                   resid_norm=float(np.linalg.norm(f)), v=[float(x) for x in v], f=[float(x) for x in f],
                   fout=[float(x) for x in fout], err_flag=bool(err), rcmb_m=float(v[2] * scale["a"]),
                   chi_li_icb=float(v[4]), chi_max=float(si_max if case["light"] == "Si" else 0.11 + 0.187 * np.exp(-0.065 * fout[0] * 1e-9)),
                   n_profile=int(len(rr)), rho_min=float(np.min(yy[4])), profile_finite=bool(np.all(np.isfinite(yy))))
        v_last = v; last_r = r
    except SolverError as e:
        ec = getattr(e, "error_code", None); info = dict(getattr(lc, "last_solve_info", {}))
        row.update(status="failed", error_code=int(ec) if ec is not None else -1, error_name=getattr(ec, "name", "SystemExit"),
                   message=str(getattr(e, "message", e))[:300], start=getattr(e, "context", {}).get("start"),
                   newton_iters=info.get("n_iterations"), resid_norm=info.get("normf_last"))
        if adaptive and v_last is not None and n_adaptive < 2:
            n_adaptive += 1; ta = time.time()
            row["adaptive"] = adaptive_continuation(last_r, v_last, r); row["adaptive"]["dt_s"] = time.time() - ta
    except Exception as e:
        row.update(status="failed", error_code=-1, error_name=type(e).__name__, message=str(e)[:300])
    row["dt_s"] = time.time() - t0
    rows.append(row)
    if row["status"] != "ok" and (policy == "stop" or row.get("error_code") == 6):
        break
print(json.dumps(rows))
'''


def _run_case(case, src, policy, adaptive):
    env = dict(os.environ, PYTHONNOUSERSITE="1", MPLBACKEND="Agg", OMP_NUM_THREADS="1",
               OPENBLAS_NUM_THREADS="1", PYTHONDONTWRITEBYTECODE="1")
    p = subprocess.run(["nice", "-n", "10", sys.executable, "-c", _CHILD, str(src), json.dumps(case), policy, "1" if adaptive else "0"],
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=4 * 3600)
    if p.returncode != 0:
        raise RuntimeError(f"{case['name']}: subprocess failed\n{p.stderr[-3000:]}")
    return json.loads(p.stdout.strip().splitlines()[-1])


def detect_policy(src):
    return "continue" if "def solve_radius(" in open(pathlib.Path(src) / "driverp.py").read() else "stop"


def generate(src, workers=8, cases=None, policy=None, adaptive=False, extra_radii=None, verbose=True, partial_dir=None):
    """partial_dir: when given, each finished case is written to
    <partial_dir>/<case name>.json as soon as it completes and cases whose
    file already exists are not re-run -- an interrupted run resumes."""
    src = pathlib.Path(src).resolve()
    cases = cases if cases is not None else json.load(open(HERE / "sample.json"))
    policy = policy or detect_policy(src)
    if extra_radii is not None:
        fixture = json.load(open(HERE / "v1_2_0_sweeps.json"))["cases"]
        cases = [dict(c, max_rows=sum(r["status"] == "ok" for r in fixture[c["name"]]["rows"]) + extra_radii) for c in cases]
    sha = subprocess.run(["git", "-C", str(src), "rev-parse", "--short", "HEAD"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(src), "status", "--porcelain", "--", "."], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip() != ""
    import numpy, scipy
    out = {"provenance": {"src": str(src), "git_sha": sha + ("-dirty" if dirty else ""), "policy": policy, "adaptive": adaptive,
                          "python": sys.version.split()[0], "numpy": numpy.__version__, "scipy": scipy.__version__,
                          "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
                          "grid": "np.arange(1e1, 2e6, 50e3) capped at case max_ricb_m / max_rows"},
           "cases": {}}
    t0 = time.time()
    todo = []
    for c in cases:
        if partial_dir and (pathlib.Path(partial_dir) / (c["name"] + ".json")).is_file():
            out["cases"][c["name"]] = json.load(open(pathlib.Path(partial_dir) / (c["name"] + ".json")))
        else:
            todo.append(c)
    if partial_dir:
        pathlib.Path(partial_dir).mkdir(parents=True, exist_ok=True)
    with cf.ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_run_case, c, src, policy, adaptive): c for c in todo}
        for fut in cf.as_completed(futs):
            c = futs[fut]
            rows = fut.result()
            out["cases"][c["name"]] = {"case": c, "rows": rows, "provenance": out["provenance"]}
            if partial_dir:
                json.dump(out["cases"][c["name"]], open(pathlib.Path(partial_dir) / (c["name"] + ".json"), "w"), indent=0)
            if verbose:
                print(c["name"], "rows ok:", sum(r["status"] == "ok" for r in rows), "of", len(rows), flush=True)
    out["provenance"]["wall_s"] = time.time() - t0
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--policy", choices=["stop", "continue"], default=None)
    ap.add_argument("--adaptive", action="store_true")
    ap.add_argument("--extra-radii", type=int, default=None)
    ap.add_argument("--cases", default=None, help="alternative cases json (same schema as sample.json)")
    ap.add_argument("--partial-dir", default=None, help="per-case results dir; makes the run resumable")
    a = ap.parse_args()
    cases = json.load(open(a.cases)) if a.cases else None
    res = generate(a.src, a.workers, cases=cases, policy=a.policy, adaptive=a.adaptive, extra_radii=a.extra_radii, partial_dir=a.partial_dir)
    json.dump(res, open(a.out, "w"), indent=0)
    print("wrote", a.out, "policy", res["provenance"]["policy"], "wall", round(res["provenance"]["wall_s"]), "s")
