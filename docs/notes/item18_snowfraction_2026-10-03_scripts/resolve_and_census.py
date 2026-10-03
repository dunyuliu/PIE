"""Item 18 snow-fraction step (docs/notes/item18_snowfraction_2026-10-03.md).

Three stages, each writing its own JSON into OUT (= this script's directory):

  census   -- re-derive the 892/218/39/16 split from the raw
              docs/notes/solver_v1.3.0_measurement/measure36_partial/*.json
              using pielib.is_admissible verbatim; emit the admissible triples.
  resolve  -- re-solve every admissible triple fresh with
              testsys/pielib.py::solve_full_model (current pie/ code), record
              isnow/isnowcmb/error_code or the exception. Parallel, capped.
  published-- per (moi, light, chi_Si_icb) snow fractions from the published
              Zenodo CSVs (read-only), two denominators: all rows, and rows
              passing the same is_admissible rule.
  table    -- join the three into the before/after/delta table (markdown).

Usage:  python3 resolve_and_census.py census|resolve|published|table|all
"""
import glob
import json
import os
import sys
import csv
import platform
import subprocess
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "testsys"))
sys.path.insert(0, str(ROOT))
os.chdir(ROOT / "pie")  # pie modules read data files relative to cwd (pielib cwd_src fixture)

MEASURE = ROOT / "docs/notes/solver_v1.3.0_measurement/measure36_partial"
ZENODO = Path(os.path.expanduser("~/shared_dataset/zenodo.16459292/extracted/PIE"))
OUT = HERE
WORKERS = int(os.environ.get("PIE_WORKERS", "12"))


def comp_key(moi, light, chi):
    return f"{moi}/{light}" + (f"_{chi:.2f}" if light == "S+Si" else "")


def row_admissible(row, light):
    from pielib import is_admissible
    if row.get("status") != "ok" or "chi_li_icb" not in row:
        return False
    return is_admissible({
        "scalars": {"chi_li_icb": row["chi_li_icb"], "chi_li_eut_icb": row.get("chi_max")},
        "max_Si": row.get("chi_max"), "light_element": light,
        "err_flag": row.get("err_flag", False)})


def stage_census():
    files = sorted(MEASURE.glob("*.json"))
    tot = dict(cases=len(files), beyond=0, converged=0, admissible=0, cases_with_adm=0)
    per_comp, triples = {}, []
    for fp in files:
        d = json.load(open(fp))
        m = d["case"]
        beyond = [r for r in d["rows"] if r["k"] >= m["published_rows"]]
        tot["beyond"] += len(beyond)
        n_adm = 0
        for r in beyond:
            if r.get("status") == "ok":
                tot["converged"] += 1
            if row_admissible(r, m["light"]):
                n_adm += 1
                triples.append(dict(
                    case=m["name"], moi=m["moi"], CMR2=m["CMR2"], CMC=m["CMC"], light=m["light"],
                    liquidus=m["liquidus"], chi_Si_icb=m["chi_Si_icb"] if m["light"] == "S+Si" else None,
                    ricb_m=r["ricb_m"], k=r["k"], published_class=m["published_class"],
                    m36_chi_li_icb=r["chi_li_icb"], m36_chi_max=r["chi_max"], m36_v=r["v"],
                    m36_start=r.get("start"), m36_fout=r.get("fout")))
        tot["admissible"] += n_adm
        tot["cases_with_adm"] += n_adm >= 1
        key = comp_key(m["moi"], m["light"], m["chi_Si_icb"])
        per_comp[key] = per_comp.get(key, 0) + n_adm
    res = dict(totals=tot, per_composition=per_comp, triples=triples)
    json.dump(res, open(OUT / "census_measure36.json", "w"), indent=1)
    print(json.dumps(tot), json.dumps(per_comp, indent=1))
    return res


def _solve(t):
    from pielib import solve_full_model, is_admissible
    import time
    t0 = time.time()
    out = dict(t)
    try:
        r = solve_full_model(t["CMR2"], t["CMC"], t["light"], t["liquidus"], t["ricb_m"],
                             chi_Si_icb=t["chi_Si_icb"])
        s = r["scalars"]
        out.update(status="ok", isnow=int(s["isnow"]), isnowcmb=int(s["isnowcmb"]),
                   error_code=int(s["error_code"]), chi_li_icb=s["chi_li_icb"],
                   chi_li_eut_icb=s["chi_li_eut_icb"], rcmb=s["rcmb"], resid_norm=r["resid_norm"],
                   err_flag=r["err_flag"], v=r["v"], admissible_fresh=bool(is_admissible(r)),
                   max_abs_dv_vs_m36=max(abs(a - b) for a, b in zip(r["v"], t["m36_v"])))
    except BaseException as e:  # SystemExit from the singular-Jacobian guard included
        out.update(status="failed", exc=type(e).__name__, message=str(e)[:500])
    out["dt_s"] = time.time() - t0
    return out


def provenance():
    import numpy, scipy
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return dict(git_sha=sha, python=platform.python_version(), numpy=numpy.__version__,
                scipy=scipy.__version__, host=platform.node(), workers=WORKERS,
                generated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                load_at_start=os.getloadavg(), cpu_count=os.cpu_count(),
                solver="testsys/pielib.py::solve_full_model, cold start")


def stage_resolve():
    triples = json.load(open(OUT / "census_measure36.json"))["triples"]
    prov = provenance()
    results = []
    with ProcessPoolExecutor(max_workers=WORKERS) as ex:
        futs = [ex.submit(_solve, t) for t in triples]
        for f in as_completed(futs):
            r = f.result()
            results.append(r)
            print(r["case"], r["ricb_m"], r["status"], r.get("isnow"), r.get("exc", ""), f"{r['dt_s']:.0f}s", flush=True)
    results.sort(key=lambda r: (r["case"], r["k"]))
    json.dump(dict(provenance=prov, results=results), open(OUT / "resolve39.json", "w"), indent=1)
    n_ok = sum(r["status"] == "ok" for r in results)
    print("resolved", n_ok, "/", len(results))


def stage_published():
    from pielib import is_admissible
    import re
    agg = {}
    nfiles = 0
    for moi in ("margot", "genova"):
        for d in sorted(glob.glob(f"{ZENODO}/work.{moi}/results/CMR2_*")):
            m = re.match(r"CMR2_([0-9.]+)_CMC_([0-9.]+)_(S\+Si|S|Si)_(\w+)", os.path.basename(d))
            light, liq = m.group(3), m.group(4)
            for cf in sorted(glob.glob(d + "/pMetaData_*.csv")):
                nfiles += 1
                chi = float(os.path.basename(cf)[10:14])
                key = comp_key(moi, light, chi)
                a = agg.setdefault(key, dict(liquidus=set(), draws=set(), n_rows=0, n_snow=0, n_snowcmb=0,
                                              n_adm=0, n_snow_adm=0, n_ec_nonzero=0, isnow_hist={}))
                a["liquidus"].add(liq)
                a["draws"].add(d)
                for row in csv.DictReader(open(cf)):
                    isnow = int(float(row["isnow"]))
                    a["n_rows"] += 1
                    a["n_snow"] += isnow > 0
                    a["n_snowcmb"] += int(float(row["isnowcmb"])) > 0
                    a["n_ec_nonzero"] += float(row["error_code"]) != 0
                    a["isnow_hist"][isnow] = a["isnow_hist"].get(isnow, 0) + 1
                    adm = is_admissible({"scalars": {"chi_li_icb": float(row["chi_li_icb"]),
                                                     "chi_li_eut_icb": float(row["chi_li_eut_icb"])},
                                         # Si-only: published csv has no max_Si; use pie globalvar's value
                                         "max_Si": _max_si(liq), "light_element": light, "err_flag": False})
                    a["n_adm"] += adm
                    a["n_snow_adm"] += adm and isnow > 0
    for a in agg.values():
        a["liquidus"] = sorted(a["liquidus"]); a["draws"] = len(a["draws"])
    total = sum(a["n_rows"] for a in agg.values())
    json.dump(dict(n_csv_files=nfiles, total_rows=total, zenodo=str(ZENODO), per_composition=agg),
              open(OUT / "published_census.json", "w"), indent=1)
    print("published csv files", nfiles, "total rows", total)
    for k, a in sorted(agg.items()):
        print(k, a["draws"], a["n_rows"], a["n_snow"], (f"{a['n_snow']/a['n_rows']:.4f}" if a["n_rows"] else "n/a"), a["n_adm"], a["isnow_hist"])


_MAXSI = {}
def _max_si(liq):
    if liq not in _MAXSI:
        import importlib
        from pielib import _set_argv, _purge_pie_submodules
        _set_argv("p", 0.346, 0.424, "Si", liq)
        _purge_pie_submodules()
        gv = importlib.import_module("pie.globalvar")
        _MAXSI[liq] = float(gv.max_Si_Steinbruegge2020 if liq == "Steinbruegge" else gv.max_Si_Edmund2022)
    return _MAXSI[liq]


def stage_table():
    pub = json.load(open(OUT / "published_census.json"))["per_composition"]
    res = json.load(open(OUT / "resolve39.json"))["results"]
    add = {}
    for r in res:
        key = comp_key(r["moi"], r["light"], r["chi_Si_icb"])
        a = add.setdefault(key, dict(n_triples=0, n_ok=0, n_adm_fresh=0, n_snow=0, isnow=[]))
        a["n_triples"] += 1
        if r["status"] == "ok":
            a["n_ok"] += 1
            if r["admissible_fresh"]:
                a["n_adm_fresh"] += 1
                a["n_snow"] += r["isnow"] > 0
                a["isnow"].append(r["isnow"])
    lines = ["| moi/composition | published rows | before isnow>0 | added (admissible fresh / triples) | added isnow>0 | after | delta (pp) | before (adm-only denom) | after (adm-only) | delta (pp) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(pub):
        p = pub[key]; a = add.get(key, dict(n_triples=0, n_ok=0, n_adm_fresh=0, n_snow=0, isnow=[]))
        if p["n_rows"] == 0: continue
        b = p["n_snow"] / p["n_rows"]
        af = (p["n_snow"] + a["n_snow"]) / (p["n_rows"] + a["n_adm_fresh"])
        b2 = p["n_snow_adm"] / p["n_adm"] if p["n_adm"] else float("nan")
        af2 = (p["n_snow_adm"] + a["n_snow"]) / (p["n_adm"] + a["n_adm_fresh"]) if p["n_adm"] + a["n_adm_fresh"] else float("nan")
        lines.append(f"| {key} | {p['n_rows']} | {b:.4f} | {a['n_adm_fresh']}/{a['n_triples']} | {a['n_snow']} | {af:.4f} | {100*(af-b):+.3f} | {b2:.4f} | {af2:.4f} | {100*(af2-b2):+.3f} |")
    txt = "\n".join(lines)
    open(OUT / "table.md", "w").write(txt + "\n")
    print(txt)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("census", "all"): stage_census()
    if stage in ("resolve", "all"): stage_resolve()
    if stage in ("published", "all"): stage_published()
    if stage in ("table", "all"): stage_table()
