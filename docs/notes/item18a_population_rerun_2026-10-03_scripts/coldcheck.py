"""Item 18(a) methodology bridge -- re-solve every admissible row the
robust_runner re-run recovered beyond the published stop with the COLD-start
single-radius solver used by the 2026-10-03 note
(testsys/pielib.py::solve_full_model), and compare isnow / chi_li_icb / rcmb.

Why: the production path (pie/robust_runner.py -> pie.main -> driverp sweep)
is warm-first/cold-fallback (v1.3.0 policy). The predecessor note's 39
recoveries were cold-start solves. This shows whether the two methodologies
agree on the recovered rows, so the before/after table (warm-first) is
comparable with the predecessor's.

Usage: python3 coldcheck.py <name> [workers]   (reads <name>_rerun_rows.json,
writes <name>_coldcheck.json). Workers default 4 -- the PROJECT_RULES rule-15
floor -- because this is normally run while the main re-run occupies the
worker budget.
"""
import json
import os
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

NAME = sys.argv[1] if len(sys.argv) > 1 else "pilot"
WORKERS = int(sys.argv[2]) if len(sys.argv) > 2 else 4
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "testsys"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT / "pie")


def _solve(t):
    from pielib import solve_full_model, is_admissible
    t0 = time.time()
    out = dict(t)
    try:
        r = solve_full_model(t["CMR2"], t["CMC"], t["light"], "Edmund", t["ricb_m"], chi_Si_icb=t["chi_Si_icb"])
        s = r["scalars"]
        out.update(status="ok", cold_isnow=int(s["isnow"]), cold_chi_li_icb=float(s["chi_li_icb"]),
                   cold_rcmb=float(s["rcmb"]), cold_admissible=bool(is_admissible(r)))
    except BaseException as e:  # SystemExit from the singular-Jacobian guard included
        out.update(status="failed", exc=type(e).__name__, message=str(e)[:300])
    out["dt_s"] = time.time() - t0
    return out


def main():
    rows = json.load(open(HERE / f"{NAME}_rerun_rows.json"))["rows"]
    tasks = []
    for r in rows:
        if r.get("status") != "done" or r.get("rerun_crashed"):
            continue
        for ricb_km, chi, isnow in zip(r["beyond_admissible_ricb_km"], r["beyond_admissible_chi"], r["beyond_admissible_isnow"]):
            tasks.append(dict(moi=r["moi"], CMR2=float(r["CMR2"]), CMC=float(r["CMC"]), light=r["light"],
                              chi_Si_icb=float(r["chi_Si_icb"]) if r["light"] == "S+Si" else None,
                              composition=r["composition"], ricb_m=ricb_km * 1e3, warm_chi_li_icb=chi, warm_isnow=isnow))
    import numpy, scipy
    prov = dict(git_sha=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip(),
                python=platform.python_version(), numpy=numpy.__version__, scipy=scipy.__version__,
                host=platform.node(), workers=WORKERS, load_at_start=os.getloadavg(), cpu_count=os.cpu_count(),
                solver="testsys/pielib.py::solve_full_model, cold start", n_rows=len(tasks))
    res = []
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        for f in as_completed([ex.submit(_solve, t) for t in tasks]):
            res.append(f.result())
    ok = [x for x in res if x["status"] == "ok"]
    summ = dict(n=len(res), cold_ok=len(ok), cold_failed=len(res) - len(ok),
                isnow_agree=sum(x["cold_isnow"] == x["warm_isnow"] for x in ok),
                isnow_disagree=[dict(moi=x["moi"], comp=x["composition"], ricb_km=x["ricb_m"] / 1e3,
                                     warm=x["warm_isnow"], cold=x["cold_isnow"]) for x in ok if x["cold_isnow"] != x["warm_isnow"]],
                cold_inadmissible=sum(not x["cold_admissible"] for x in ok),
                max_abs_dchi=max((abs(x["cold_chi_li_icb"] - x["warm_chi_li_icb"]) for x in ok), default=None),
                failed=[dict(moi=x["moi"], comp=x["composition"], ricb_km=x["ricb_m"] / 1e3, exc=x["exc"]) for x in res if x["status"] != "ok"],
                mean_dt_s=sum(x["dt_s"] for x in res) / max(1, len(res)))
    json.dump(dict(provenance=prov, summary=summ, rows=res), open(HERE / f"{NAME}_coldcheck.json", "w"), indent=1, default=str)
    print(json.dumps(dict(provenance=prov, summary=summ), indent=1, default=str))


if __name__ == "__main__":
    main()
